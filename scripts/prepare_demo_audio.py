"""从已发布的 MP4 案例提取工作音轨，无在线调用。"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for example in ["jev_60s", "jev_3min"]:
    source = ROOT / "media" / f"{example}.mp4"
    output = ROOT / "local_media" / example / "master.wav"
    if output.exists():
        print(f"保留已有音轨：{output}")
        continue
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-n",
            "-v",
            "error",
            "-i",
            str(source),
            "-vn",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output),
        ],
        check=True,
    )
    print(output)
