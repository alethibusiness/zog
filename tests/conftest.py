from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("ZOG_DISABLE_BOOTSTRAP", "1")
    monkeypatch.delenv("ZOHO_CLIENT_ID", raising=False)
    monkeypatch.delenv("ZOHO_CLIENT_SECRET", raising=False)
    yield
