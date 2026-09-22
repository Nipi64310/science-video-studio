"""兼容旧入口：词级对齐仍使用可选的本地 Whisper；Qwen 转写用 asr_qwen.py。"""

import runpy
from pathlib import Path

if __name__ == "__main__":
    print("词级对齐入口；Qwen ASR 转写请使用 scripts/asr_qwen.py。")
    runpy.run_path(
        str(Path(__file__).with_name("align_whisper.py")), run_name="__main__"
    )
