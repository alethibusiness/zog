from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from zog.providers.zoho.device_flow import (
    ZohoDeviceFlowError,
    initiate_device_flow,
    poll_for_token,
)


def _response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    return response


def test_initiate_returns_parsed_response():
    mock_payload = {
        "device_code": "dev-code-123",
        "user_code": "USER-1234",
        "verification_uri": "https://accounts.zoho.com/oauth/v2/device",
        "verification_uri_complete": "https://accounts.zoho.com/oauth/v2/device?user_code=USER-1234",
        "interval": 5,
        "expires_in": 600,
    }
    with patch(
        "zog.providers.zoho.device_flow.requests.post",
        return_value=_response(200, mock_payload),
    ) as mock_post:
        result = initiate_device_flow("client-id", ["scope1", "scope2"])

    assert result["device_code"] == "dev-code-123"
    assert result["user_code"] == "USER-1234"
    assert result["verification_uri"] == "https://accounts.zoho.com/oauth/v2/device"
    assert result["interval"] == 5
    assert result["expires_in"] == 600
    mock_post.assert_called_once()


def test_poll_authorization_pending_then_success(monkeypatch):
    sleeps = []
    monkeypatch.setattr(
        "zog.providers.zoho.device_flow.time.sleep", lambda s: sleeps.append(s)
    )
    monkeypatch.setattr(
        "zog.providers.zoho.device_flow.time.time",
        lambda: 1000.0 + sum(sleeps),
    )

    responses = [
        _response(400, {"error": "authorization_pending"}),
        _response(400, {"error": "authorization_pending"}),
        _response(400, {"error": "authorization_pending"}),
        _response(200, {"access_token": "atoken", "refresh_token": "rtoken"}),
    ]

    with patch(
        "zog.providers.zoho.device_flow.requests.post",
        side_effect=responses,
    ):
        result = poll_for_token("client-id", "dev-code", interval=5, expires_in=60)

    assert result["access_token"] == "atoken"
    assert result["refresh_token"] == "rtoken"
    assert len(sleeps) == 3
    assert all(s == 5 for s in sleeps)


def test_poll_slow_down_increases_interval(monkeypatch):
    sleeps = []
    monkeypatch.setattr(
        "zog.providers.zoho.device_flow.time.sleep", lambda s: sleeps.append(s)
    )
    monkeypatch.setattr(
        "zog.providers.zoho.device_flow.time.time",
        lambda: 1000.0 + sum(sleeps),
    )

    responses = [
        _response(400, {"error": "slow_down"}),
        _response(200, {"access_token": "atoken", "refresh_token": "rtoken"}),
    ]

    with patch(
        "zog.providers.zoho.device_flow.requests.post",
        side_effect=responses,
    ):
        result = poll_for_token("client-id", "dev-code", interval=5, expires_in=60)

    assert result["access_token"] == "atoken"
    assert sleeps == [10]


def test_poll_expired_token_raises():
    with patch(
        "zog.providers.zoho.device_flow.requests.post",
        return_value=_response(400, {"error": "expired_token"}),
    ):
        with pytest.raises(ZohoDeviceFlowError, match="expired"):
            poll_for_token("client-id", "dev-code", interval=5, expires_in=60)


def test_poll_access_denied_raises():
    with patch(
        "zog.providers.zoho.device_flow.requests.post",
        return_value=_response(400, {"error": "access_denied"}),
    ):
        with pytest.raises(ZohoDeviceFlowError, match="denied"):
            poll_for_token("client-id", "dev-code", interval=5, expires_in=60)


def test_poll_respects_expires_in_deadline(monkeypatch):
    sleeps = []
    monkeypatch.setattr(
        "zog.providers.zoho.device_flow.time.sleep", lambda s: sleeps.append(s)
    )
    base_time = [1000.0]

    def fake_time():
        return base_time[0] + sum(sleeps)

    monkeypatch.setattr("zog.providers.zoho.device_flow.time.time", fake_time)

    with patch(
        "zog.providers.zoho.device_flow.requests.post",
        return_value=_response(400, {"error": "authorization_pending"}),
    ):
        with pytest.raises(ZohoDeviceFlowError, match="expired"):
            poll_for_token("client-id", "dev-code", interval=5, expires_in=15)

    assert sum(sleeps) >= 15
