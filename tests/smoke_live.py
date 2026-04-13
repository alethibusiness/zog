from __future__ import annotations

from pathlib import Path

import pytest

from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.mail import search_messages


@pytest.mark.live
def test_live_search_latest_messages():
    token_path = Path.home() / ".config" / "zogcli" / "keyring" / "token" / "admin@alethiconsulting.com.json"
    if not token_path.exists():
        pytest.skip("Live Zoho credentials are not available.")

    client = ZohoClient("admin@alethiconsulting.com")
    rows = search_messages(client, "from:cloudflare", limit=3)
    assert len(rows) <= 3

