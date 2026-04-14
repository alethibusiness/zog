"""OAuth 2.0 Device Authorization Grant (RFC 8628) for Zoho."""

from __future__ import annotations

import time
from typing import Any

import requests

from zog.errors import AuthError

DEVICE_CODE_URL = "https://accounts.zoho.com/oauth/v2/device/code"
TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"


class ZohoDeviceFlowError(AuthError):
    """Raised when the device flow fails or is aborted."""


def initiate_device_flow(
    client_id: str,
    scopes: list[str],
    accounts_url: str = "https://accounts.zoho.com",
) -> dict[str, Any]:
    """Request a device code from Zoho.

    Returns a dict with ``device_code``, ``user_code``, ``verification_uri``,
    ``interval``, and ``expires_in``.
    """
    response = requests.post(
        f"{accounts_url.rstrip('/')}/oauth/v2/device/code",
        data={
            "client_id": client_id,
            "scope": " ".join(scopes),
        },
        timeout=30,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ZohoDeviceFlowError(
            f"Zoho returned invalid JSON: {response.text}"
        ) from exc
    if not isinstance(payload, dict):
        raise ZohoDeviceFlowError("Unexpected OAuth response payload.")
    if response.status_code >= 400 or "error" in payload:
        raise ZohoDeviceFlowError(
            payload.get("error_description")
            or payload.get("error")
            or f"Device flow initiation failed ({response.status_code})."
        )
    return payload


def poll_for_token(
    client_id: str,
    device_code: str,
    interval: int,
    expires_in: int,
    accounts_url: str = "https://accounts.zoho.com",
) -> dict[str, Any]:
    """Poll the Zoho token endpoint until the user authorizes the device.

    Returns the token dict on success. Raises ``ZohoDeviceFlowError`` on
    terminal errors (``expired_token``, ``access_denied``, timeout).
    """
    deadline = time.time() + expires_in
    current_interval = interval

    while True:
        if time.time() >= deadline:
            raise ZohoDeviceFlowError(
                "Device authorization expired. Please run `zog auth add` again."
            )

        response = requests.post(
            f"{accounts_url.rstrip('/')}/oauth/v2/token",
            data={
                "client_id": client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "code": device_code,
            },
            timeout=30,
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ZohoDeviceFlowError(
                f"Zoho returned invalid JSON: {response.text}"
            ) from exc

        if not isinstance(payload, dict):
            raise ZohoDeviceFlowError("Unexpected OAuth response payload.")

        if response.status_code == 200 and "access_token" in payload:
            return payload

        error = payload.get("error")
        if error == "authorization_pending":
            time.sleep(current_interval)
            continue
        if error == "slow_down":
            current_interval += 5
            time.sleep(current_interval)
            continue
        if error == "expired_token":
            raise ZohoDeviceFlowError(
                "Device code expired. Please run `zog auth add` again."
            )
        if error == "access_denied":
            raise ZohoDeviceFlowError(
                "Authorization denied. Please run `zog auth add` again if you wish to continue."
            )

        raise ZohoDeviceFlowError(
            payload.get("error_description")
            or payload.get("error")
            or f"Unexpected error during device authorization ({response.status_code})."
        )


__all__ = [
    "ZohoDeviceFlowError",
    "initiate_device_flow",
    "poll_for_token",
]
