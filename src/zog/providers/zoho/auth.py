"""Zoho OAuth helpers."""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from getpass import getpass
from typing import Any

import requests

from zog.config import StoredToken
from zog.errors import AuthError
from zog.providers.zoho import endpoints

DEFAULT_SCOPES = [
    "ZohoMail.messages.ALL",
    "ZohoMail.accounts.READ",
    "ZohoMail.folders.READ",
]


def read_client_credentials() -> tuple[str, str]:
    """Prompt for OAuth client credentials unless env vars are set."""

    client_id = os.environ.get("ZOHO_CLIENT_ID") or input("Zoho Client ID: ").strip()
    client_secret = os.environ.get("ZOHO_CLIENT_SECRET") or getpass("Zoho Client Secret: ").strip()
    if not client_id or not client_secret:
        raise AuthError("Client ID and Client Secret are required.")
    return client_id, client_secret


def print_self_client_instructions(scopes: Sequence[str] = DEFAULT_SCOPES) -> None:
    """Print the Zoho Self Client instructions from the spec."""

    print("Open https://api-console.zoho.com/")
    print("Create or select a Self Client, then open the Generate Code tab.")
    print(f"Scopes: {','.join(scopes)}")
    print("Duration: 10 min")
    print("Paste the grant code below when prompted.")


def exchange_grant_code(
    *,
    accounts_url: str,
    client_id: str,
    client_secret: str,
    grant_code: str,
) -> dict[str, Any]:
    """Exchange a Zoho grant code for refresh and access tokens."""

    response = requests.post(
        endpoints.oauth_token(accounts_url),
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": grant_code,
        },
        timeout=30,
    )
    payload = _decode_response(response)
    if response.status_code >= 400 or "error" in payload:
        raise AuthError(payload.get("error_description") or payload.get("error") or "OAuth exchange failed.")
    return payload


def refresh_access_token(token: StoredToken) -> StoredToken:
    """Refresh a Zoho access token from a refresh token."""

    response = requests.post(
        endpoints.oauth_token(token.accounts_url),
        data={
            "refresh_token": token.refresh_token,
            "client_id": token.client_id,
            "client_secret": token.client_secret,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    payload = _decode_response(response)
    if response.status_code >= 400 or "error" in payload:
        raise AuthError(payload.get("error_description") or payload.get("error") or "Token refresh failed.")
    expires_in = int(payload.get("expires_in", 3600))
    token.access_token = str(payload["access_token"])
    token.access_token_expires_at = int(time.time()) + max(expires_in - 60, 0)
    if payload.get("scope"):
        token.scopes = [item for item in str(payload["scope"]).replace(",", " ").split() if item]
    return token


def _decode_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthError(f"Zoho returned invalid JSON: {response.text}") from exc
    if not isinstance(payload, dict):
        raise AuthError("Unexpected OAuth response payload.")
    return payload


__all__ = [
    "DEFAULT_SCOPES",
    "exchange_grant_code",
    "print_self_client_instructions",
    "read_client_credentials",
    "refresh_access_token",
]

