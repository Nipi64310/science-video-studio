"""统一视频入口；默认只使用本地音轨，不调用模型。"""

import argparse, importlib.util, json, math, subprocess, sys, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_renderer(name):
    folder = ROOT / "examples" / name
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location(
        "video_renderer", folder / "renderer.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("example", choices=["jev_60s", "jev_3min"])
    p.add_argument(
        "--audio", type=Path, help="本地 WAV 路径；默认 local_media/实例名/master.wav"
    )
    p.add_argument(
        "--output", type=Path, help="输出文件路径；默认 outputs/实例名/video.mp4"
    )
    p.add_argument("--start", type=float, default=0, help="起点秒数，默认 0")
    p.add_argument("--duration", type=float, help="片段秒数，默认到片尾")
    p.add_argument(
        "--width", type=int, default=1920, help="输出宽度像素，默认 1920，高度按 16:9"
    )
    p.add_argument("--still", type=float, help="仅输出该秒画面，无需音频")
    a = p.parse_args()
    m = load_renderer(a.example)
    if a.width < 320 or a.width % 32:
        p.error("--width 需为不小于 320 的 32 倍数，例如 960、1920")
    folder = ROOT / "outputs" / a.example
    folder.mkdir(parents=True, exist_ok=True)
    if a.still is not None:
        if not 0 <= a.still < m.DATA["duration"]:
            p.error("截图时间超出视频")
        out = a.output or folder / "preview.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        m.frame(a.still).im.save(out)
        print(out)
        return
    audio = a.audio or ROOT / "local_media" / a.example / "master.wav"
    if not audio.is_file():
        p.error(
            f"缺少本地音轨 {audio}；按 README 导入既有工程音轨或传 --audio。不会自动调用接口。"
        )
    length = min(
        a.duration if a.duration is not None else m.DATA["duration"] - a.start,
        m.DATA["duration"] - a.start,
    )
    if a.start < 0 or length <= 0:
        p.error("起点或时长无效")
    with wave.open(str(audio), "rb") as w:
        available = len(w.readframes(w.getnframes())) / (
            w.getnchannels() * w.getsampwidth() * w.getframerate()
        )
    if available + 0.05 < a.start + length:
        p.error("音频短于当前时间轴；新配音必须重新对齐")
    out = a.output or folder / "video.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    h = a.width * 9 // 16
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{a.width}x{h}",
        "-r",
        "30",
        "-i",
        "-",
        "-ss",
        str(a.start),
        "-i",
        str(audio),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-b:a",
        "192k",
        "-t",
        str(length),
        "-movflags",
        "+faststart",
        str(out),
    ]
    if a.example == "jev_60s":
        cmd[-1:-1] = ["-af", "loudnorm=I=-16:TP=-1:LRA=11"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(math.ceil(length * 30)):
            image = m.frame(a.start + n / 30).im
            if a.width != 1920:
                image = image.resize((a.width, h))
            proc.stdin.write(image.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("FFmpeg 编码失败")
    except BaseException:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        raise
    print(out)


if __name__ == "__main__":
    main()
