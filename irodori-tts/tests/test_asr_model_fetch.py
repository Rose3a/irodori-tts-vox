import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wrapper"))
import asr_timeline


class AsrModelFetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.files = {"model.int8.onnx": 8, "tokens.txt": 3}

    def _write(self, name, size):
        (self.folder / name).write_bytes(b"x" * size)

    def test_ready_when_all_sizes_match(self):
        for name, size in self.files.items():
            self._write(name, size)
        self.assertTrue(asr_timeline.model_ready(self.folder, self.files))
        state = asr_timeline.ensure_asr_model(folder=self.folder, files=self.files)
        self.assertTrue(state["ready"])
        self.assertFalse(state["pending"])
        self.assertIsNone(state["error"])

    def test_truncated_file_is_not_ready(self):
        self._write("model.int8.onnx", 7)
        self._write("tokens.txt", 3)
        self.assertFalse(asr_timeline.model_ready(self.folder, self.files))

    def test_missing_files_are_downloaded_from_the_pinned_revision(self):
        calls = []

        def fake_download(repo, name, revision=None, local_dir=None):
            calls.append((repo, name, revision, Path(local_dir)))
            Path(local_dir, name).write_bytes(b"x" * self.files[name])
            return str(Path(local_dir, name))

        stages = []
        module = types.SimpleNamespace(hf_hub_download=fake_download)
        with patch.dict(sys.modules, {"huggingface_hub": module}):
            state = asr_timeline.ensure_asr_model(
                progress=lambda *args: stages.append(args), log=lambda _line: None,
                wait_seconds=10, folder=self.folder, files=self.files)

        self.assertTrue(state["ready"])
        self.assertEqual([call[1] for call in calls], list(self.files))
        self.assertTrue(all(call[2] == asr_timeline.ASR_REVISION for call in calls))
        self.assertTrue(all(call[3] == self.folder for call in calls))
        self.assertTrue(any("取得中" in str(stage[0]) for stage in stages))

    def test_failed_download_reports_the_error(self):
        def failing_download(*args, **kwargs):
            raise RuntimeError("network down")

        module = types.SimpleNamespace(hf_hub_download=failing_download)
        with patch.dict(sys.modules, {"huggingface_hub": module}):
            state = asr_timeline.ensure_asr_model(
                wait_seconds=10, folder=self.folder, files=self.files)

        self.assertFalse(state["ready"])
        self.assertFalse(state["pending"])
        self.assertIn("network down", state["error"] or "")

    def test_download_stops_on_size_mismatch(self):
        def short_download(repo, name, revision=None, local_dir=None):
            Path(local_dir, name).write_bytes(b"x")  # 想定より小さい
            return str(Path(local_dir, name))

        module = types.SimpleNamespace(hf_hub_download=short_download)
        with patch.dict(sys.modules, {"huggingface_hub": module}):
            state = asr_timeline.ensure_asr_model(
                wait_seconds=10, folder=self.folder, files=self.files)

        self.assertFalse(state["ready"])
        self.assertIn("サイズが想定と違います", state["error"] or "")


if __name__ == "__main__":
    unittest.main()
