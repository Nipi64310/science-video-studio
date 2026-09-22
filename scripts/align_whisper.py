"""给新音频产生词级时间戳；这不是自动校对或最终字幕。"""

import argparse, json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("audio", type=Path)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--model", default="small")
a = p.parse_args()
from faster_whisper import WhisperModel

m = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=4)
segments, _ = m.transcribe(
    str(a.audio),
    language="zh",
    word_timestamps=True,
    condition_on_previous_text=False,
    vad_filter=True,
)
data = []
for s in segments:
    data.append(
        {
            "start": s.start,
            "end": s.end,
            "text": s.text,
            "words": [
                {"text": w.word, "start": w.start, "end": w.end} for w in s.words or []
            ],
        }
    )
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(data, ensure_ascii=False, indent=2))
print(a.output)
