import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import sys
import json
import io

spec = importlib.util.spec_from_file_location(
    "asr", Path(__file__).resolve().parents[1] / "scripts/asr_qwen.py"
)
asr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asr)


class ASRTests(unittest.TestCase):
    def test_payload_and_local_rejection(self):
        p = asr.build_payload("https://example.org/audio.wav")
        self.assertEqual(
            p["input"]["messages"][0]["content"][0]["input_audio"]["data"],
            "https://example.org/audio.wav",
        )
        self.assertEqual(p["parameters"]["sample_rate"], "16000")
        with self.assertRaises(ValueError):
            asr.build_payload("/tmp/local.wav")

    def test_success_does_not_invent_timestamps(self):
        response = {
            "request_id": "test",
            "output": {"choices": [{"message": {"content": [{"text": "测试台词"}]}}]},
        }

        class Opener:
            def open(self, req, timeout):
                self.request = req
                return io.BytesIO(json.dumps(response).encode())

        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "result.json"
            with patch.dict(
                "os.environ", {"DASHSCOPE_API_KEY": "test-placeholder"}
            ), patch.object(
                sys,
                "argv",
                [
                    "asr",
                    "--audio-url",
                    "https://example.org/audio.wav",
                    "--output",
                    str(target),
                ],
            ), patch.object(
                asr.urllib.request, "build_opener", return_value=Opener()
            ):
                asr.main()
            result = json.loads(target.read_text())
            self.assertEqual(result["text"], "测试台词")
            self.assertEqual(result["alignment_status"], "not_aligned")
            self.assertNotIn("segments", result)

    def test_unknown_shape_not_silently_text(self):
        self.assertEqual(asr.extract_text({"output": {"new_schema": "text"}}), "")


if __name__ == "__main__":
    unittest.main()
