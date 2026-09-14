import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import browser_session


def _response(body: bytes = b"{}", status: int = 200):
    response = unittest.mock.MagicMock()
    response.__enter__.return_value = response
    response.status = status
    response.read.return_value = body
    return response


def _token_response(token: str = "test-token"):
    return _response(json.dumps({"token": token}).encode())


def _forbidden(path: str):
    return urllib.error.HTTPError(
        f"http://{browser_session.ENGINE_HOST}:{browser_session.ENGINE_PORT}{path}",
        403, "Forbidden", {},
        io.BytesIO(b'{"detail": "invalid local origin/session"}'))


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

    def test_engine_ready_authenticates_the_settings_probe(self):
        """設定の口は認証が要るので、トークンを付けないと 200 にならない。"""
        settings = _response()

        with patch.object(browser_session.urllib.request, "urlopen",
                          side_effect=[_token_response(), settings]) as urlopen:
            self.assertTrue(browser_session.engine_ready())

        probe = urlopen.call_args_list[1].args[0]
        self.assertEqual(
            probe.full_url,
            f"http://{browser_session.ENGINE_HOST}:{browser_session.ENGINE_PORT}/irodori/settings")
        sent = {key.lower(): value for key, value in probe.headers.items()}
        self.assertEqual(sent.get("origin"), browser_session.BROWSER_URL)
        self.assertEqual(sent.get("x-irodori-session"), "test-token")

    def test_engine_ready_false_when_the_engine_is_down(self):
        with patch.object(browser_session.urllib.request, "urlopen",
                          side_effect=urllib.error.URLError("connection refused")):
            self.assertFalse(browser_session.engine_ready())

    def test_engine_ready_surfaces_a_rejected_session(self):
        """403 を URLError と一緒に握ると、起動待ちが90秒タイムアウトになるだけになる。"""
        with patch.object(browser_session.urllib.request, "urlopen",
                          side_effect=[_token_response(), _forbidden("/irodori/settings")]):
            with self.assertRaises(browser_session.EngineAuthError):
                browser_session.engine_ready()

    def test_shutdown_engine_authenticates_the_identifying_probe(self):
        with patch.object(browser_session.urllib.request, "urlopen",
                          side_effect=[_token_response(), _response(), _token_response(),
                                       _response(), urllib.error.URLError("engine is down")]) as urlopen:
            self.assertTrue(browser_session.shutdown_engine())

        probe = urlopen.call_args_list[1].args[0]
        sent = {key.lower(): value for key, value in probe.headers.items()}
        self.assertEqual(sent.get("x-irodori-session"), "test-token")

    def test_shutdown_engine_false_when_the_engine_is_down(self):
        with patch.object(browser_session.urllib.request, "urlopen",
                          side_effect=urllib.error.URLError("connection refused")):
            self.assertFalse(browser_session.shutdown_engine())


if __name__ == "__main__":
    unittest.main()
