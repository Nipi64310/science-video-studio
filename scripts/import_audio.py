"""从原工程 ZIP 提取 master.wav；不解压其余内容。"""

import argparse, zipfile, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("example", choices=["jev_60s", "jev_3min"])
p.add_argument("archive", type=Path)
a = p.parse_args()
with zipfile.ZipFile(a.archive) as z:
    names = [n for n in z.namelist() if n.endswith("/audio/master.wav")]
    if len(names) != 1:
        raise SystemExit("压缩包中必须有唯一的 audio/master.wav")
    target = ROOT / "local_media" / a.example / "master.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    with z.open(names[0]) as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    print(target)
