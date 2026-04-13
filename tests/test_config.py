from __future__ import annotations

import stat

from zog.config import (
    AppConfig,
    StoredToken,
    get_storage_paths,
    load_account_token,
    load_config,
    save_account_token,
    save_config,
    token_file,
)


def test_config_roundtrip_and_permissions():
    config = AppConfig(default_account="admin@example.com")
    save_config(config)

    loaded = load_config()
    assert loaded.default_account == "admin@example.com"

    path = get_storage_paths().config_file
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_token_roundtrip_and_permissions():
    token = StoredToken(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        access_token="access-token",
        access_token_expires_at=123,
        scopes=["ZohoMail.messages.ALL"],
        account_id="acc-1",
    )
    save_account_token("admin@example.com", token)

    loaded = load_account_token("admin@example.com")
    assert loaded.client_id == "client-id"
    assert loaded.account_id == "acc-1"
    assert loaded.scopes == ["ZohoMail.messages.ALL"]

    path = token_file("admin@example.com")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
