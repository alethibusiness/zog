from __future__ import annotations

from unittest.mock import Mock

import pytest

from zog.config import StoredToken, save_account_token
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.workdrive import get_file, list_files, upload_file


def _response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    return response


@pytest.fixture(autouse=True)
def _seed_token():
    save_account_token(
        "admin@example.com",
        StoredToken(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            access_token="token",
            access_token_expires_at=4_102_444_800,
        ),
    )


def test_list_files(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        return_value=_response(
            200,
            {
                "data": [
                    {"id": "f1", "name": "Report.pdf", "type": "file"},
                    {"id": "f2", "name": "Docs", "type": "folder"},
                ]
            },
        ),
    )
    client = ZohoClient("admin@example.com")
    files = list_files(client)
    assert len(files) == 2
    assert files[0]["fileId"] == "f1"
    assert files[0]["name"] == "Report.pdf"
    assert files[1]["type"] == "folder"


def test_get_file(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        return_value=_response(
            200,
            {
                "data": {"id": "f1", "name": "Report.pdf", "type": "file"},
            },
        ),
    )
    client = ZohoClient("admin@example.com")
    file_info = get_file(client, "f1")
    assert file_info["fileId"] == "f1"
    assert file_info["name"] == "Report.pdf"


def test_upload_file_stub_raises():
    client = ZohoClient("admin@example.com")
    with pytest.raises(NotImplementedError) as exc_info:
        upload_file(client, "/tmp/foo.txt")
    assert "not yet implemented" in str(exc_info.value)
