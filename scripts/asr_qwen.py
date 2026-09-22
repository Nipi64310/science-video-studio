"""Qwen Filetrans：提交一次、续查任务、下载结果，导出秒级时间轴与待校对 SRT。"""

import argparse
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

MODEL = "qwen-audio-3.1-asr-flash-filetrans"
BASE = "https://maas.qianwenaiapi.com/api/v1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("接口重定向已停止，未转发认证头")


def save(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def build_payload(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError("请提供服务端可访问的 HTTP(S) 音频 URL")
    return {
        "model": MODEL,
        "input": {"file_urls": [url]},
        "parameters": {"channel_id": [0]},
    }


def api(path, key, payload=None):
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if payload is not None:
        headers["X-DashScope-Async"] = "enable"
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            failure = json.loads(e.read())
        except ValueError:
            failure = {}
        raise RuntimeError(
            f"HTTP {e.code}; code={failure.get('code')}; request_id={failure.get('request_id')}"
        ) from None


def result_url(status):
    out = status["output"]
    items = out.get("results") or [out.get("result", out)]
    # 本入口一次只提交一个文件。
    if len(items) != 1:
        raise ValueError("预期单文件结果，实际结果数量不符")
    item = items[0]
    if item.get("subtask_status", "SUCCEEDED") != "SUCCEEDED":
        raise RuntimeError("音频子任务未成功")
    url = item.get("transcription_url")
    if not url or urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise ValueError("结果缺少有效 transcription_url")
    return url


def download(url):
    # 独立下载，不携带 API Key。
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def normalize(raw):
    tracks = [t for t in raw.get("transcripts", []) if t.get("channel_id") == 0]
    if len(tracks) != 1 or not tracks[0].get("sentences"):
        raise ValueError("结果缺少声道 0 的句级时间戳")
    duration = raw.get("properties", {}).get("original_duration_in_milliseconds")

    def interval(obj):
        a, b = obj.get("begin_time"), obj.get("end_time")
        if (
            not all(isinstance(x, (int, float)) and math.isfinite(x) for x in (a, b))
            or not 0 <= a < b
        ):
            raise ValueError("时间戳无效")
        if duration is not None and b > duration:
            raise ValueError("时间戳超过音频长度")
        return a / 1000, b / 1000

    segments = []
    last = -1
    for s in tracks[0]["sentences"]:
        start, end = interval(s)
        if start < last:
            raise ValueError("句级时间倒序")
        last = start
        words = []
        prev = start
        for w in s.get("words", []):
            a, b = interval(w)
            if a < prev or a < start or b > end:
                raise ValueError("词级时间顺序或范围异常")
            prev = a
            words.append(
                {"text": w["text"] + w.get("punctuation", ""), "start": a, "end": b}
            )
        segments.append({"start": start, "end": end, "text": s["text"], "words": words})
    return segments


def srt(segments):
    def stamp(t):
        ms = round(t * 1000)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    return (
        "\n\n".join(
            f"{i}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['text']}"
            for i, s in enumerate(segments, 1)
        )
        + "\n"
    )


def execute(out, url=None, resume=False, task_id=None, max_wait=300, poll_interval=5):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    task = out / "task.json"
    rawpath = out / "result_private.json"
    if not resume and (
        task.exists() or (out / "submission_started.json").exists() or rawpath.exists()
    ):
        raise ValueError("目录已使用；请用 --resume 继续，或更换目录")
    if task_id:
        if not resume:
            raise ValueError("--task-id 仅配合 --resume")
        if (
            task.exists()
            and json.loads(task.read_text())["output"]["task_id"] != task_id
        ):
            raise ValueError("task-id 与缓存不一致")
        save(task, {"output": {"task_id": task_id}})
    if not rawpath.exists():
        key = os.environ.get("DASHSCOPE_API_KEY")
        if not key:
            raise ValueError("请设置 DASHSCOPE_API_KEY")
        if not task.exists():
            if resume:
                raise ValueError(
                    "没有缓存 task_id；提交结果不明时不得自动重提，可用 --task-id 恢复"
                )
            payload = build_payload(url or "")
            save(
                out / "submission_started.json",
                {"model": MODEL, "started_at": time.time()},
            )
            submitted = api("/services/audio/asr/transcription", key, payload)
            save(task, submitted)
        tid = json.loads(task.read_text())["output"]["task_id"]
        if not isinstance(tid, str) or not all(c.isalnum() or c == "-" for c in tid):
            raise ValueError("无效 task_id")
        print("task_id:", tid, flush=True)
        statuspath = out / "status_private.json"
        status = json.loads(statuspath.read_text()) if statuspath.exists() else {}
        deadline = time.monotonic() + max_wait
        while status.get("output", {}).get("task_status") != "SUCCEEDED":
            state = status.get("output", {}).get("task_status")
            if state in ("FAILED", "CANCELED", "UNKNOWN"):
                raise RuntimeError(f"任务结束：{state}；检查 status_private.json")
            if time.monotonic() >= deadline:
                raise TimeoutError("等待超时；使用同一目录 --resume 续查，不重新提交")
            status = api("/tasks/" + tid, key)
            save(statuspath, status)
            state = status.get("output", {}).get("task_status")
            print("状态:", state, flush=True)
            if state in ("PENDING", "RUNNING"):
                time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))
            elif state not in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
                raise RuntimeError("未知响应状态")
        save(rawpath, download(result_url(status)))
    segments = normalize(json.loads(rawpath.read_text()))
    save(out / "alignment.json", segments)
    (out / "subtitles.draft.srt").write_text(srt(segments), encoding="utf-8")
    (out / "transcript.txt").write_text(
        "\n".join(s["text"] for s in segments), encoding="utf-8"
    )
    summary = {
        "model": MODEL,
        "sentences": len(segments),
        "words": sum(len(s["words"]) for s in segments),
        "timestamp_unit": "seconds",
        "review_status": "needs_review",
    }
    save(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return segments


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group()
    source.add_argument("--audio-url")
    source.add_argument("--response-file", type=Path, help="Next response_private.json")
    p.add_argument("--run-dir", type=Path, required=True, help="例如 runs/asr_01")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--task-id", help="恢复已知任务，必须配合 --resume")
    p.add_argument("--max-wait", type=float, default=300)
    a = p.parse_args()
    if a.max_wait <= 0 or not math.isfinite(a.max_wait):
        p.error("--max-wait 必须为正数")
    if a.resume and (a.audio_url or a.response_file):
        p.error("--resume 使用缓存，不接受新的音频来源")
    if not a.resume and not (a.audio_url or a.response_file):
        p.error("请提供 --audio-url 或 --response-file")
    try:
        url = a.audio_url or (
            json.loads(a.response_file.read_text())["output"]["audio"]["url"]
            if a.response_file
            else None
        )
        execute(a.run_dir, url, a.resume, a.task_id, a.max_wait)
    except (ValueError, RuntimeError, TimeoutError, KeyError, OSError) as e:
        p.exit(1, f"{type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
