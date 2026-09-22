"""检查 Git 暂存快照中的秘密和媒体；只报告路径/规则，不打印命中内容。"""

import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    ("API key", rb"sk-[A-Za-z0-9_-]{16,}"),
    ("GitHub token", rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ("signed URL", rb"(?:OSSAccessKeyId|X-Amz-Signature|X-Goog-Signature)="),
    ("private key", rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


APPROVED_MEDIA = {
    "media/jev_60s.mp4",
    "media/jev_3min.mp4",
    "media/jev_60s.mp3",
    "media/jev_3min.mp3",
}


def scan(name, data):
    issues = []
    parts = Path(name).parts
    if any(x in parts for x in ["local_media", "runs", "outputs", ".private"]):
        issues.append("private directory")
    if Path(name).suffix.lower() in [".wav", ".mp3", ".mp4", ".zip", ".pem", ".key"]:
        if name not in APPROVED_MEDIA:
            issues.append("private/media file")
    if Path(name).name.startswith(".env") and Path(name).name != ".env.example":
        issues.append("environment file")
    if "response_private" in name or "audio_url" in name:
        issues.append("private response")
    for label, pat in PATTERNS:
        if re.search(pat, data):
            issues.append(label)
    return issues


def main():
    names = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    bad = []
    for name in filter(None, names):
        data = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
        issues = scan(name, data)
        if issues:
            bad.append((name, issues))
    for name, issues in bad:
        print(name, ":", ", ".join(issues))
    print(
        "检查失败"
        if bad
        else "暂存快照检查通过：未发现所覆盖的密钥模式、临时签名链接或媒体文件"
    )
    return bool(bad)


if __name__ == "__main__":
    sys.exit(main())
