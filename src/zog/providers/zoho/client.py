"""HTTP client wrapper for the Zoho API."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from zog.config import load_account_token, save_account_token
from zog.errors import ApiError
from zog.providers.zoho.auth import refresh_access_token

LOGGER = logging.getLogger(__name__)


class ZohoClient:
    """Small Zoho API client with automatic refresh-and-retry."""

    def __init__(self, email: str, *, verbose: bool = False) -> None:
        self.email = email
        self.verbose = verbose

    def get(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("GET", url, params=params)

    def post(self, url: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", url, json_body=json_body)

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retry_on_auth_error: bool = True,
    ) -> dict[str, Any]:
        """Perform an authenticated API request."""

        token = self._ensure_access_token(load_account_token(self.email))
        response = self._perform_request(method, url, token.access_token or "", params=params, json_body=json_body)
        if response.status_code == 401 and retry_on_auth_error and self._is_invalid_oauth_token(response):
            LOGGER.debug("Zoho access token expired for %s; refreshing and retrying once.", self.email)
            token = refresh_access_token(token)
            save_account_token(self.email, token)
            response = self._perform_request(
                method,
                url,
                token.access_token or "",
                params=params,
                json_body=json_body,
            )
        payload = self._decode_payload(response)
        self._raise_for_error(response, payload)
        return payload

    def _ensure_access_token(self, token: Any) -> Any:
        expires_at = getattr(token, "access_token_expires_at", None)
        if token.access_token and (expires_at is None or expires_at > int(time.time())):
            return token
        token = refresh_access_token(token)
        save_account_token(self.email, token)
        return token

    def _perform_request(
        self,
        method: str,
        url: str,
        access_token: str,
        *,
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
    ) -> requests.Response:
        if self.verbose:
            LOGGER.debug("%s %s params=%s", method.upper(), url, params)
        return requests.request(
            method.upper(),
            url,
            headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
            params=params,
            json=json_body,
            timeout=30,
        )

    def _decode_payload(self, response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError(
                f"Zoho returned invalid JSON (HTTP {response.status_code}).",
                status_code=response.status_code,
                payload=response.text,
            ) from exc
        if not isinstance(payload, dict):
            raise ApiError(
                "Unexpected Zoho API response payload.",
                status_code=response.status_code,
                payload=payload,
            )
        return payload

    def _raise_for_error(self, response: requests.Response, payload: dict[str, Any]) -> None:
        status = payload.get("status")
        status_code = response.status_code
        error_code = None
        message = None

        if isinstance(status, dict):
            error_code = _string_or_none(status.get("description"))
            if "code" in status:
                status_code = int(status["code"])

        if response.status_code >= 400 or (status_code and status_code >= 400):
            message = self._extract_error_message(payload) or f"Zoho API request failed ({status_code})."
            raise ApiError(message, status_code=status_code, error_code=error_code, payload=payload)

    def _is_invalid_oauth_token(self, response: requests.Response) -> bool:
        try:
            payload = response.json()
        except ValueError:
            return False
        if not isinstance(payload, dict):
            return False
        error_values = {
            _string_or_none(payload.get("error")),
            _string_or_none(payload.get("code")),
        }
        status = payload.get("status")
        if isinstance(status, dict):
            error_values.add(_string_or_none(status.get("description")))
            if status.get("code") is not None:
                error_values.add(str(status["code"]))
        data = payload.get("data")
        if isinstance(data, dict):
            error_values.add(_string_or_none(data.get("errorCode")))
            error_values.add(_string_or_none(data.get("description")))
        return "INVALID_OAUTHTOKEN" in {value for value in error_values if value}

    def _extract_error_message(self, payload: dict[str, Any]) -> str | None:
        status = payload.get("status")
        if isinstance(status, dict):
            for key in ("description", "message"):
                if status.get(key):
                    return str(status[key])
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("description", "message", "errorCode"):
                if data.get(key):
                    return str(data[key])
        for key in ("message", "error", "description"):
            if payload.get(key):
                return str(payload[key])
        return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = ["ZohoClient"]
