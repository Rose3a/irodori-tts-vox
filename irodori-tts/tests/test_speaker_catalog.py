import base64
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wrapper"))

from speaker_catalog import FALLBACK_ICON_PATH, portrait_for, speaker_catalog, thumbnail_for


class SpeakerCatalogTests(unittest.TestCase):
    def test_existing_raster_sidecar_wins_over_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            embedding = root / "speaker.safetensors"
            raster = root / "speaker.png"
            embedding.write_bytes(b"embedding")
            raster.write_bytes(b"png-payload")

            self.assertEqual(thumbnail_for(embedding), ("image/png", base64.b64encode(b"png-payload").decode("ascii")))
            self.assertEqual(portrait_for(embedding), ("image/png", base64.b64encode(b"png-payload").decode("ascii")))

    def test_recursive_external_speaker_uses_default_icon_and_portrait(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            embedding = root / "nested" / "external.speaker.safetensors"
            embedding.parent.mkdir()
            embedding.write_bytes(b"embedding")
            expected = base64.b64encode(FALLBACK_ICON_PATH.read_bytes()).decode("ascii")

            catalog = dict(speaker_catalog([root]))

            self.assertEqual(catalog["external"], ("image/png", expected))
            self.assertEqual(portrait_for(embedding), ("image/png", expected))


if __name__ == "__main__":
    unittest.main()
