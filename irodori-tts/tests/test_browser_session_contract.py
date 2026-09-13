import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import browser_session


class BrowserSessionAuthTests(unittest.TestCase):
    def test_session_token_bootstrap_sends_browser_origin(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"token": "test-token"}).encode()

        with patch.object(browser_session.urllib.request, "urlopen", return_value=response) as urlopen:
            self.assertEqual(browser_session._session_token(), "test-token")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Origin"), browser_session.BROWSER_URL)
        self.assertIsNone(request.get_header("Host"))


if __name__ == "__main__":
    unittest.main()
