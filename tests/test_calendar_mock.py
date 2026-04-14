from __future__ import annotations

from unittest.mock import Mock

import pytest

from zog.config import StoredToken, save_account_token
from zog.providers.zoho.calendar import (
    create_event,
    get_event,
    list_calendars,
    list_events,
)
from zog.providers.zoho.client import ZohoClient


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


def test_list_calendars(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        return_value=_response(
            200,
            {
                "calendars": [
                    {"uid": "cal1", "name": "Primary", "calendarType": "primary"},
                    {"uid": "cal2", "name": "Work", "calendarType": "personal"},
                ]
            },
        ),
    )
    client = ZohoClient("admin@example.com")
    calendars = list_calendars(client)
    assert len(calendars) == 2
    assert calendars[0]["id"] == "cal1"
    assert calendars[0]["name"] == "Primary"
    assert calendars[1]["type"] == "personal"


def test_list_events(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        side_effect=[
            _response(
                200,
                {
                    "calendars": [
                        {"uid": "cal1", "name": "Primary", "calendarType": "primary"},
                    ]
                },
            ),
            _response(
                200,
                {
                    "events": [
                        {"uid": "evt1", "title": "Meeting", "dateandtime": {"start": "2026-04-15T10:00:00Z", "end": "2026-04-15T11:00:00Z"}},
                    ]
                },
            ),
        ],
    )
    client = ZohoClient("admin@example.com")
    events = list_events(client, limit=10)
    assert len(events) == 1
    assert events[0]["eventId"] == "evt1"
    assert events[0]["title"] == "Meeting"


def test_get_event(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        side_effect=[
            _response(
                200,
                {
                    "calendars": [
                        {"uid": "cal1", "name": "Primary", "calendarType": "primary"},
                    ]
                },
            ),
            _response(
                200,
                {
                    "events": [
                        {"uid": "evt1", "title": "Standup", "dateandtime": {"start": "2026-04-15T09:00:00Z", "end": "2026-04-15T09:30:00Z"}},
                    ]
                },
            ),
        ],
    )
    client = ZohoClient("admin@example.com")
    event = get_event(client, "evt1")
    assert event["eventId"] == "evt1"
    assert event["title"] == "Standup"


def test_create_event(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        side_effect=[
            _response(
                200,
                {
                    "calendars": [
                        {"uid": "cal1", "name": "Primary", "calendarType": "primary", "timezone": "UTC"},
                    ]
                },
            ),
            _response(
                200,
                {
                    "events": [
                        {"uid": "evt99", "title": "Demo", "dateandtime": {"start": "2026-04-15T14:00:00Z", "end": "2026-04-15T15:00:00Z"}},
                    ]
                },
            ),
        ],
    )
    client = ZohoClient("admin@example.com")
    result = create_event(
        client,
        title="Demo",
        start="2026-04-15T14:00:00Z",
        end="2026-04-15T15:00:00Z",
        description="Team demo",
        location="Room A",
        attendees=["a@b.com", "c@d.com"],
    )
    assert result["eventId"] == "evt99"
    assert result["status"] == "success"
