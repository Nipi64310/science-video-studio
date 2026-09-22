import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import json

spec = importlib.util.spec_from_file_location(
    "asr", Path(__file__).resolve().parents[1] / "scripts/asr_qwen.py"
)
asr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asr)
RAW = {
    "properties": {"original_duration_in_milliseconds": 2000},
    "transcripts": [
        {
            "channel_id": 0,
            "sentences": [
                {
                    "begin_time": 960,
                    "end_time": 1280,
                    "text": "最近。",
                    "words": [
                        {
                            "begin_time": 960,
                            "end_time": 1280,
                            "text": "最近",
                            "punctuation": "。",
                        }
                    ],
                }
            ],
        }
    ],
}
SUCCESS = {
    "output": {
        "task_status": "SUCCEEDED",
        "results": [
            {
                "subtask_status": "SUCCEEDED",
                "transcription_url": "https://example.org/result.json",
            }
        ],
    }
}


class ASRTests(unittest.TestCase):
    def test_payload(self):
        p = asr.build_payload("https://example.org/audio.wav")
        self.assertEqual(p["input"], {"file_urls": ["https://example.org/audio.wav"]})
        self.assertEqual(p["parameters"], {"channel_id": [0]})
        with self.assertRaises(ValueError):
            asr.build_payload("/tmp/local.wav")

    def test_normalization_and_srt(self):
        s = asr.normalize(RAW)
        self.assertEqual(s[0]["words"][0]["start"], 0.96)
        self.assertIn("00:00:00,960 --> 00:00:01,280", asr.srt(s))
        with self.assertRaises(ValueError):
            asr.normalize({"transcripts": []})
        invalid = json.loads(json.dumps(RAW))
        invalid["transcripts"][0]["sentences"][0]["words"][0]["end_time"] = 9999
        with self.assertRaises(ValueError):
            asr.normalize(invalid)

    def test_submit_poll_export(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(
            "os.environ", {"DASHSCOPE_API_KEY": "placeholder"}
        ), patch.object(
            asr, "api", side_effect=[{"output": {"task_id": "abc"}}, SUCCESS]
        ) as api, patch.object(
            asr, "download", return_value=RAW
        ):
            asr.execute(d, "https://example.org/a.wav")
            self.assertEqual(api.call_count, 2)
            self.assertTrue((Path(d) / "subtitles.draft.srt").exists())
            with self.assertRaises(ValueError):
                asr.execute(d, "https://example.org/a.wav")

    def test_resume_download_without_post(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(
            "os.environ", {"DASHSCOPE_API_KEY": "placeholder"}
        ), patch.object(asr, "api") as api, patch.object(
            asr, "download", return_value=RAW
        ):
            asr.save(Path(d) / "task.json", {"output": {"task_id": "abc"}})
            asr.save(Path(d) / "status_private.json", SUCCESS)
            asr.execute(d, resume=True)
            api.assert_not_called()

    def test_failed_and_unknown_submission_never_resubmitted(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(
            "os.environ", {"DASHSCOPE_API_KEY": "placeholder"}
        ), patch.object(asr, "api") as api:
            asr.save(Path(d) / "submission_started.json", {})
            with self.assertRaises(ValueError):
                asr.execute(d, resume=True)
            asr.save(Path(d) / "task.json", {"output": {"task_id": "abc"}})
            asr.save(
                Path(d) / "status_private.json", {"output": {"task_status": "FAILED"}}
            )
            with self.assertRaises(RuntimeError):
                asr.execute(d, resume=True)
            api.assert_not_called()

    def test_timeout_resume_keeps_task(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(
            "os.environ", {"DASHSCOPE_API_KEY": "placeholder"}
        ), patch.object(asr, "api") as api:
            asr.save(Path(d) / "task.json", {"output": {"task_id": "abc"}})
            with self.assertRaises(TimeoutError):
                asr.execute(d, resume=True, max_wait=0)
            api.assert_not_called()

    def test_result_variants(self):
        url = "https://example.org/result.json"
        for out in [
            {"transcription_url": url},
            {"result": {"transcription_url": url}},
            SUCCESS["output"],
        ]:
            self.assertEqual(asr.result_url({"output": out}), url)


if __name__ == "__main__":
    unittest.main()
