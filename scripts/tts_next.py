"""Next HTTP 生成/续下载。密钥仅从环境读取，失败不自动重新生成。"""

import argparse, base64, hashlib, json, os, re, urllib.request, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("接口发生重定向，已停止，未转发认证头")


def repair_wav(source, target):
    with wave.open(str(source), "rb") as w:
        ch, sw, sr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        pcm = w.readframes(w.getnframes())
    if not pcm or len(pcm) % (ch * sw):
        raise ValueError("WAV 数据为空或末尾帧不完整")
    with wave.open(str(target), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(sr)
        w.writeframes(pcm)
    return {
        "sample_rate": sr,
        "channels": ch,
        "duration": len(pcm) / (sr * ch * sw),
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
    }


def execute(prompt, reference, out, model="qwen-audio-3.1-tts-next", resume=False):
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "response_private.json"
    if (out / "master.wav").exists():
        raise ValueError("目录已有 master.wav，请另选输出目录，避免误覆盖")
    if cache.exists():
        response = json.loads(cache.read_text())
    else:
        if resume:
            raise ValueError("没有已缓存响应，无法仅续下载")
        key = os.environ.get("DASHSCOPE_API_KEY")
        workspace = os.environ.get("SFM_WORKSPACE_ID") or os.environ.get("WORKSPACE_ID")
        if not key or not workspace:
            raise ValueError("请设置 DASHSCOPE_API_KEY 和 SFM_WORKSPACE_ID")
        if not re.fullmatch(r"[A-Za-z0-9-]+", workspace):
            raise ValueError("业务空间 ID 格式不正确")
        text = prompt.read_text(encoding="utf-8")
        body = {
            "model": model,
            "input": {
                "text_prompt": text,
                "format": "wav",
                "sample_rate": 48000,
                "channels": 2,
            },
        }
        if reference:
            raw = reference.read_bytes()
            body["input"]["references"] = [
                {
                    "audio_data": "data:audio/wav;base64,"
                    + base64.b64encode(raw).decode()
                }
            ]
        summary = {
            "model": model,
            "prompt": text,
            "reference_sha256": (
                hashlib.sha256(reference.read_bytes()).hexdigest()
                if reference
                else None
            ),
        }
        (out / "request_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2)
        )
        req = urllib.request.Request(
            f"https://{workspace}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
            },
        )
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=360) as r:
            response = json.load(r)
        cache.write_text(json.dumps(response, ensure_ascii=False, indent=2))
        cache.chmod(0o600)
    url = response.get("output", {}).get("audio", {}).get("url")
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise ValueError("响应没有有效音频 URL；已保存原始响应")
    # 新请求不携带生成接口的认证头。下载失败保留 cache，下次只续下载。
    with urllib.request.urlopen(url, timeout=120) as r:
        raw = r.read()
    original = out / "original.wav"
    original.write_bytes(raw)
    info = repair_wav(original, out / "master.wav")
    info["request_id"] = response.get("request_id")
    (out / "result.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    return info


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--reference", type=Path)
    p.add_argument(
        "--run", required=True, help="本地运行名称，只能含字母数字横线下划线"
    )
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", a.run):
        p.error("--run 格式无效")
    print(
        json.dumps(
            execute(a.prompt, a.reference, ROOT / "runs" / a.run, resume=a.resume),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
