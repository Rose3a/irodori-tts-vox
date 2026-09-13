"""Regression checks for environments without a usable TorchCodec backend."""
import unittest
from unittest.mock import patch

from prepare import verify_audio_io


class AudioIOTest(unittest.TestCase):
    def test_installed_backend(self):
        verify_audio_io()

    def test_unavailable_torchcodec(self):
        import torchaudio

        for error in (
            ImportError('TorchCodec is required for save_with_torchcodec'),
            RuntimeError('Could not load libtorchcodec'),
        ):
            with self.subTest(error=type(error).__name__):
                with patch.object(torchaudio, 'save', side_effect=error), patch.object(
                    torchaudio, 'load', side_effect=error
                ):
                    verify_audio_io()


if __name__ == '__main__':
    unittest.main()
