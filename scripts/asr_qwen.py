"""Qwen ASR 转写。只保存服务端返回，不把纯文字伪造成字幕时间轴。"""

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

MODEL = "qwen-audio-3.1-asr-flash-message"
ENDPOINT = "https://maas.qianwenaiapi.com/api/v1/services/aigc/multimodal-generation/generation"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("接口重定向已停止，未转发认证头")


def build_payload(url, model=MODEL, sample_rate=16000, protocol="message"):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("请提供服务端可访问的 HTTP(S) 音频 URL")
    content = (
        {"type": "input_audio", "input_audio": {"data": url}}
        if protocol == "message"
        else {"audio": url}
    )
    return {
        "model": model,
        "input": {"messages": [{"role": "user", "content": [content]}]},
        "parameters": {"format": "wav", "sample_rate": str(sample_rate)},
    }


def extract_text(response):
    choices = response.get("output", {}).get("choices", [])
    parts = []
    for choice in choices[:1]:
        content = choice.get("message", {}).get("content", [])
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(
                x["text"]
                for x in content
                if isinstance(x, dict) and isinstance(x.get("text"), str)
            )
    return "\n".join(parts)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--audio-url", help="公网可访问的 WAV URL，不支持本地文件路径")
    source.add_argument(
        "--response-file",
        type=Path,
        help="读取 Next 的本地 response_private.json 中 output.audio.url",
    )
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--model", default=MODEL)
    p.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="按输入实际采样率填写；此参数不会重采样",
    )
    p.add_argument(
        "--protocol",
        choices=["message", "dashscope"],
        default="message",
        help="message 沿用接入示例；dashscope 使用官方通用 audio 字段。失败不自动切换",
    )
    a = p.parse_args()
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        p.error("请设置 DASHSCOPE_API_KEY")
    if a.output.exists():
        p.error("输出文件已存在，请换一个路径")
    url = (
        a.audio_url or json.loads(a.response_file.read_text())["output"]["audio"]["url"]
    )
    payload = build_payload(url, a.model, a.sample_rate, a.protocol)
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable",
        },
    )
    print(
        f"请求模型：{a.model}；协议：{a.protocol}；只请求一次，不自动重试；不打印音频 URL"
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=180) as r:
            response = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            failure = json.loads(e.read())
        except (ValueError, UnicodeError):
            failure = {}
        # 不打印服务器可能回显的 URL 或认证信息。
        print(
            json.dumps(
                {
                    "http_status": e.code,
                    "code": failure.get("code"),
                    "request_id": failure.get("request_id"),
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(
            "ASR 请求失败，未生成转写或时间轴。请核对协议、模型权限和音频 URL。"
        )
    text = extract_text(response)
    result = {
        "model": a.model,
        "request_id": response.get("request_id"),
        "text": text,
        "alignment_status": "not_aligned",
        "response": response,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"响应已保存：{a.output}；未生成字幕时间戳。")
    if not text.strip():
        raise SystemExit("未识别到已支持结构中的转写文字，请检查保存的响应。")
    print(text)


if __name__ == "__main__":
    main()
