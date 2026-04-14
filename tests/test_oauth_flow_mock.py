from __future__ import annotations

import socket
import threading
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from zog.providers.zoho.oauth_flow import (
    ZohoOAuthFlowError,
    _build_auth_url,
    _exchange_code,
    _pick_free_port,
    run_loopback_flow,
    run_oob_flow,
)


def _response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    return response


def test_build_auth_url_includes_redirect_uri():
    url = _build_auth_url("cid", ["s1", "s2"], redirect_uri="http://localhost:8765/callback")
    assert url.startswith("https://accounts.zoho.com/oauth/v2/auth?")
    assert "response_type=code" in url
    assert "client_id=cid" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url


def test_build_auth_url_omits_redirect_uri_when_none():
    url = _build_auth_url("cid", ["s1", "s2"], redirect_uri=None)
    assert "redirect_uri" not in url


def test_pick_free_port_finds_available():
    # Find a free port by binding to 0, then release it and verify _pick_free_port can find it
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    result = _pick_free_port([port])
    assert result == port


def test_pick_free_port_fallback_to_second():
    # Bind two ports, leaving the third free
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s1:
        s1.bind(("127.0.0.1", 0))
        p1 = s1.getsockname()[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
            s2.bind(("127.0.0.1", 0))
            p2 = s2.getsockname()[1]

            # Choose a third port that should be free
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s3:
                s3.bind(("127.0.0.1", 0))
                p3 = s3.getsockname()[1]

            result = _pick_free_port([p1, p2, p3])
            assert result == p3


def test_pick_free_port_raises_when_all_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s1:
        s1.bind(("127.0.0.1", 0))
        p1 = s1.getsockname()[1]
        with pytest.raises(ZohoOAuthFlowError, match="None of the local ports"):
            _pick_free_port([p1])


def test_exchange_code_success():
    with patch(
        "zog.providers.zoho.oauth_flow.requests.post",
        return_value=_response(200, {"access_token": "at", "refresh_token": "rt"}),
    ) as mock_post:
        result = _exchange_code("code123", "http://localhost/cb", "cid", "csec")

    assert result["access_token"] == "at"
    assert result["refresh_token"] == "rt"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["data"]["code"] == "code123"
    assert call_kwargs["data"]["redirect_uri"] == "http://localhost/cb"
    assert call_kwargs["data"]["client_id"] == "cid"
    assert call_kwargs["data"]["client_secret"] == "csec"


def test_exchange_code_without_redirect_uri():
    with patch(
        "zog.providers.zoho.oauth_flow.requests.post",
        return_value=_response(200, {"access_token": "at", "refresh_token": "rt"}),
    ) as mock_post:
        result = _exchange_code("code123", None, "cid", "csec")

    assert "redirect_uri" not in mock_post.call_args.kwargs["data"]


def test_exchange_code_error_raises():
    with patch(
        "zog.providers.zoho.oauth_flow.requests.post",
        return_value=_response(400, {"error": "invalid_code", "error_description": "Bad code"}),
    ):
        with pytest.raises(ZohoOAuthFlowError, match="Bad code"):
            _exchange_code("bad", "http://cb", "cid", "csec")


def test_loopback_happy_path():
    """Simulate the browser callback by making an HTTP request to the local server."""
    import urllib.request

    token_payload = {"access_token": "atoken", "refresh_token": "rtoken"}

    def simulate_browser(port):
        # Give the server a moment to start
        import time
        time.sleep(0.2)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/callback?code=AUTH123")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass

    with patch(
        "zog.providers.zoho.oauth_flow.requests.post",
        return_value=_response(200, token_payload),
    ) as mock_post:
        with patch("zog.providers.zoho.oauth_flow.webbrowser.open"):
            # Pick a free port
            port = _pick_free_port()
            browser_thread = threading.Thread(target=simulate_browser, args=(port,), daemon=True)
            browser_thread.start()
            result = run_loopback_flow("cid", "csec", ["s1"], port=port, open_browser=False)

    assert result["access_token"] == "atoken"
    assert result["refresh_token"] == "rtoken"
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["data"]["code"] == "AUTH123"


def test_loopback_callback_error():
    """Simulate an error callback from the browser."""
    import urllib.request

    def simulate_browser(port):
        import time
        time.sleep(0.2)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/callback?error=access_denied")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass

    with patch("zog.providers.zoho.oauth_flow.webbrowser.open"):
        port = _pick_free_port()
        browser_thread = threading.Thread(target=simulate_browser, args=(port,), daemon=True)
        browser_thread.start()
        with pytest.raises(ZohoOAuthFlowError, match="access_denied"):
            run_loopback_flow("cid", "csec", ["s1"], port=port, open_browser=False)


def test_loopback_port_fallback_when_first_taken():
    """If the requested port is taken, run_loopback_flow should bubble the bind error."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        taken_port = sock.getsockname()[1]

        with pytest.raises(ZohoOAuthFlowError, match="Unable to bind"):
            run_loopback_flow("cid", "csec", ["s1"], port=taken_port, open_browser=False)


def test_oob_happy_path(monkeypatch):
    monkeypatch.setattr("sys.stdin", StringIO("CODE123\n"))
    with patch(
        "zog.providers.zoho.oauth_flow.requests.post",
        return_value=_response(200, {"access_token": "at", "refresh_token": "rt"}),
    ) as mock_post:
        result = run_oob_flow("cid", "csec", ["s1"])

    assert result["access_token"] == "at"
    assert result["refresh_token"] == "rt"
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["data"]["code"] == "CODE123"
    assert "redirect_uri" not in mock_post.call_args.kwargs["data"]


def test_oob_empty_code(monkeypatch):
    monkeypatch.setattr("sys.stdin", StringIO("\n"))
    with pytest.raises(ZohoOAuthFlowError, match="Authorization code is required"):
        run_oob_flow("cid", "csec", ["s1"])
