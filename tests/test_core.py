import io, json, sys, tempfile, unittest, wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_repo import scan
from tts_next import repair_wav, execute


def wavbytes():
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\0\0" * 800)
    return b.getvalue()


class CoreTests(unittest.TestCase):
    def test_wav_placeholder_header_preserves_pcm(self):
        raw = bytearray(wavbytes())
        raw[4:8] = (2147483647).to_bytes(4, "little")
        raw[40:44] = (2147483600).to_bytes(4, "little")
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.wav"
            b = Path(d) / "b.wav"
            a.write_bytes(raw)
            info = repair_wav(a, b)
            self.assertAlmostEqual(info["duration"], 0.1)
            self.assertEqual(b.read_bytes()[44:], raw[44:])

    def test_secret_and_media_detection(self):
        self.assertIn("API key", scan("x.py", ("sk-" + "x" * 32).encode()))
        self.assertIn(
            "signed URL", scan("x.json", ("OSSAccessKeyId" + "=dummy").encode())
        )
        self.assertTrue(scan("local_media/reference.wav", b""))
        self.assertFalse(scan(".env.example", b"DASHSCOPE_API_KEY=\n"))

    def test_cached_response_only_downloads_without_auth(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "response_private.json").write_text(
                json.dumps(
                    {"output": {"audio": {"url": "https://example.test/audio.wav"}}}
                )
            )
            with patch(
                "tts_next.urllib.request.urlopen", return_value=io.BytesIO(wavbytes())
            ) as download, patch("tts_next.urllib.request.build_opener") as generate:
                info = execute(root / "unused.txt", None, root, resume=True)
                generate.assert_not_called()
                self.assertEqual(
                    download.call_args.args, ("https://example.test/audio.wav",)
                )
                self.assertAlmostEqual(info["duration"], 0.1)


if __name__ == "__main__":
    unittest.main()
