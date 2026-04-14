"""Zoho app defaults for the zog CLI."""

from __future__ import annotations

import os

DEFAULT_CLIENT_ID = "PLACEHOLDER_ZOG_CLIENT_ID"


def get_client_id() -> str:
    """Return the active OAuth client ID.

    Prefers the ``ZOG_CLIENT_ID`` environment variable, otherwise falls
    back to the embedded default.
    """
    return os.environ.get("ZOG_CLIENT_ID") or DEFAULT_CLIENT_ID


__all__ = ["DEFAULT_CLIENT_ID", "get_client_id"]
