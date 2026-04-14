"""Zoho app defaults for the zog CLI."""

from __future__ import annotations

import os

DEFAULT_CLIENT_ID = "1000.KJQSBYOTNAT2V25WQP72EHUOAIXDEB"
DEFAULT_CLIENT_SECRET = "60770b81e08f0e54a5c80d42a411bc88622b9612b6"


def get_client_id() -> str:
    """Return the active OAuth client ID.

    Prefers the ``ZOG_CLIENT_ID`` environment variable, otherwise falls
    back to the embedded default.
    """
    return os.environ.get("ZOG_CLIENT_ID") or DEFAULT_CLIENT_ID


def get_client_secret() -> str | None:
    """Return the active OAuth client secret.

    Prefers the ``ZOG_CLIENT_SECRET`` environment variable, otherwise falls
    back to the embedded default.
    """
    return os.environ.get("ZOG_CLIENT_SECRET") or DEFAULT_CLIENT_SECRET


__all__ = ["DEFAULT_CLIENT_ID", "DEFAULT_CLIENT_SECRET", "get_client_id", "get_client_secret"]
