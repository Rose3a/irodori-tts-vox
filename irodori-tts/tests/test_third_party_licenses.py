import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wrapper"))
from third_party_licenses import dependency_licenses


class LicenseTests(unittest.TestCase):
    def test_engine_help_includes_asr_and_runtime_notices(self):
        entries = dependency_licenses()
        self.assertTrue(any("口パク ASR" in item["name"] and item["license"] == "CC BY 4.0" for item in entries))
        names = {item["name"] for item in entries}
        self.assertTrue({"sherpa-onnx", "dacvae", "soundfile"} <= names)
        self.assertTrue(all(item["text"].strip() for item in entries))


if __name__ == "__main__":
    unittest.main()
