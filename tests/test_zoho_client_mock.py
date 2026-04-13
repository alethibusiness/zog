from __future__ import annotations

from unittest.mock import Mock

from zog.config import StoredToken, load_account_token, save_account_token
from zog.providers.zoho.client import ZohoClient


def _response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    return response


def test_zoho_client_refreshes_and_retries_on_invalid_oauth_token(mocker):
    save_account_token(
        "admin@example.com",
        StoredToken(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            access_token="stale-token",
            access_token_expires_at=4_102_444_800,
        ),
    )
    request_mock = mocker.patch(
        "zog.providers.zoho.client.requests.request",
        side_effect=[
            _response(401, {"status": {"code": 401, "description": "INVALID_OAUTHTOKEN"}}),
            _response(200, {"status": {"code": 200, "description": "success"}, "data": {"ok": True}}),
        ],
    )
    refresh_mock = mocker.patch(
        "zog.providers.zoho.client.refresh_access_token",
        side_effect=lambda token: StoredToken(
            client_id=token.client_id,
            client_secret=token.client_secret,
            refresh_token=token.refresh_token,
            access_token="fresh-token",
            access_token_expires_at=4_102_444_800,
            scopes=token.scopes,
            account_id=token.account_id,
            api_url=token.api_url,
            accounts_url=token.accounts_url,
        ),
    )

    client = ZohoClient("admin@example.com")
    payload = client.get("https://mail.zoho.com/api/accounts")

    assert payload["data"] == {"ok": True}
    assert request_mock.call_count == 2
    assert refresh_mock.call_count == 1
    assert load_account_token("admin@example.com").access_token == "fresh-token"

