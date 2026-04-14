"""OAuth 2.0 Authorization Code flow for Zoho (local loopback + OOB)."""

from __future__ import annotations

import socket
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import requests

from zog.errors import AuthError

AUTH_URL = "https://accounts.zoho.com/oauth/v2/auth"
TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"


class ZohoOAuthFlowError(AuthError):
    """Raised when the OAuth flow fails or is aborted."""


def _pick_free_port(candidates: list[int] | None = None) -> int:
    """Return the first available port from *candidates*."""
    if candidates is None:
        candidates = [8765, 8766, 8767]
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise ZohoOAuthFlowError(
        f"None of the local ports {candidates} are available. "
        "Use --no-browser to switch to the out-of-band flow."
    )


def _build_auth_url(
    client_id: str,
    scopes: list[str],
    redirect_uri: str | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    """Build the Zoho authorization URL."""
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": client_id,
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
    }
    if redirect_uri is not None:
        params["redirect_uri"] = redirect_uri
    if extra:
        params.update(extra)
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def _exchange_code(
    code: str,
    redirect_uri: str | None,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """POST the captured authorization code to Zoho's token endpoint."""
    data: dict[str, str] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
    }
    if redirect_uri is not None:
        data["redirect_uri"] = redirect_uri
    response = requests.post(TOKEN_URL, data=data, timeout=30)
    try:
        payload = response.json()
    except ValueError as exc:
        raise ZohoOAuthFlowError(
            f"Zoho returned invalid JSON: {response.text}"
        ) from exc
    if not isinstance(payload, dict):
        raise ZohoOAuthFlowError("Unexpected OAuth response payload.")
    if response.status_code >= 400 or "error" in payload:
        raise ZohoOAuthFlowError(
            payload.get("error_description")
            or payload.get("error")
            or f"Token exchange failed ({response.status_code})."
        )
    return payload


def _make_callback_handler(code_event: threading.Event, result: dict[str, Any]):
    """Factory for the loopback HTTP request handler."""

    class _CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            # suppress default stderr logging
            pass

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            code = query.get("code", [None])[0]
            error = query.get("error", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()

            if code:
                result["code"] = code
                self.wfile.write(
                    b"<!DOCTYPE html>"
                    b"<html><head><title>Authorized</title></head>"
                    b"<body><p>Authorization successful. You can close this tab.</p></body></html>"
                )
                code_event.set()
            elif error:
                result["error"] = error
                self.wfile.write(
                    f"<!DOCTYPE html>"
                    f"<html><head><title>Authorization Error</title></head>"
                    f"<body><p>Authorization failed: {error}</p></body></html>"
                    .encode("utf-8")
                )
                code_event.set()
            else:
                self.wfile.write(
                    b"<!DOCTYPE html>"
                    b"<html><head><title>Waiting</title></head>"
                    b"<body><p>Waiting for authorization...</p></body></html>"
                )

    return _CallbackHandler


def run_loopback_flow(
    client_id: str,
    client_secret: str,
    scopes: list[str],
    port: int | None = None,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Run the local-loopback Authorization Code flow.

    Returns the token dict on success. Raises ``ZohoOAuthFlowError`` on failure.
    """
    if port is None:
        port = _pick_free_port()

    redirect_uri = f"http://localhost:{port}/callback"
    auth_url = _build_auth_url(client_id, scopes, redirect_uri=redirect_uri)

    code_event = threading.Event()
    result: dict[str, Any] = {}
    handler = _make_callback_handler(code_event, result)

    try:
        server = HTTPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        raise ZohoOAuthFlowError(
            f"Unable to bind to localhost:{port}: {exc}."
        ) from exc
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception:
                pass

        # Wait up to 5 minutes for the callback
        if not code_event.wait(timeout=300):
            raise ZohoOAuthFlowError(
                "Authorization timed out. Please run `zog auth add` again."
            )

        if "error" in result:
            raise ZohoOAuthFlowError(
                f"Authorization failed: {result['error']}"
            )

        return _exchange_code(
            result["code"],
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    except KeyboardInterrupt:
        raise ZohoOAuthFlowError("Authorization interrupted.")
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def run_oob_flow(
    client_id: str,
    client_secret: str,
    scopes: list[str],
) -> dict[str, Any]:
    """Run the out-of-band Authorization Code flow (copy-paste).

    Returns the token dict on success. Raises ``ZohoOAuthFlowError`` on failure.
    """
    auth_url = _build_auth_url(client_id, scopes, redirect_uri=None)
    print(f"Open this URL in your browser:\n{auth_url}\n")

    try:
        code = input("Paste the authorization code here: ").strip()
    except EOFError:
        raise ZohoOAuthFlowError("Unable to read authorization code from stdin.")
    except KeyboardInterrupt:
        raise ZohoOAuthFlowError("Authorization interrupted.")

    if not code:
        raise ZohoOAuthFlowError("Authorization code is required.")

    return _exchange_code(
        code,
        redirect_uri=None,
        client_id=client_id,
        client_secret=client_secret,
    )


__all__ = [
    "ZohoOAuthFlowError",
    "run_loopback_flow",
    "run_oob_flow",
    "_build_auth_url",
    "_exchange_code",
    "_pick_free_port",
]
