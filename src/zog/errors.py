"""Project error types."""

from __future__ import annotations


class ZogError(Exception):
    """Base class for expected CLI errors."""


class ConfigError(ZogError):
    """Raised for configuration and credential storage issues."""


class AuthError(ZogError):
    """Raised for OAuth failures."""


class ApiError(ZogError):
    """Raised when the Zoho API returns an error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        payload: object | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.payload = payload

