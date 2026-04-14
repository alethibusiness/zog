"""Zoho Calendar operations."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from zog.providers.zoho.client import ZohoClient

CALENDAR_API_URL = "https://calendar.zoho.com/api/v1"


def _endpoint(path: str) -> str:
    return f"{CALENDAR_API_URL.rstrip('/')}/{path.lstrip('/')}"


def _default_calendar(client: ZohoClient) -> dict[str, Any]:
    """Return the default (or first) calendar."""
    calendars = list_calendars(client)
    if not calendars:
        raise RuntimeError("No calendars available.")
    return calendars[0]


def _calendar_uid(calendar_id: str | None, client: ZohoClient) -> str:
    """Resolve a calendar identifier to its UID."""
    if calendar_id:
        return calendar_id
    return _default_calendar(client)["uid"]


def list_calendars(client: ZohoClient) -> list[dict[str, Any]]:
    """Return normalized calendars for the active account."""

    response = client.get(_endpoint("calendars"))
    calendars = []
    for raw in response.get("calendars", []) or response.get("data", []) or []:
        uid = str(raw.get("uid", raw.get("id", "")))
        calendars.append(
            {
                "id": uid,
                "uid": uid,
                "name": str(raw.get("name", "")),
                "type": str(raw.get("calendarType", raw.get("type", ""))),
                "raw": raw,
            }
        )
    return calendars


def _fmt_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if len(value) == 8 and value.isdigit():
        return value
    if len(value) >= 8 and value[:8].isdigit():
        # yyyyMMddTHHMMSSZ or similar – truncate to date portion
        return value[:8]
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y%m%d")
    except ValueError:
        pass
    return value


def _build_range(start: str | None, end: str | None) -> str:
    if start:
        s = _fmt_date(start)
    else:
        s = datetime.now(timezone.utc).strftime("%Y%m%d")
    if end:
        e = _fmt_date(end)
    else:
        e = (datetime.strptime(s, "%Y%m%d") + timedelta(days=30)).strftime("%Y%m%d")
    return json.dumps({"start": s, "end": e})


def list_events(
    client: ZohoClient,
    calendar_id: str | None = None,
    *,
    start: str | None = None,
    end: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return normalized events for the selected calendar."""

    uid = _calendar_uid(calendar_id, client)
    range_param = _build_range(start, end)
    response = client.get(
        _endpoint(f"calendars/{uid}/events"),
        params={"range": range_param},
    )
    events = []
    for raw in response.get("events", []) or response.get("data", []) or []:
        if isinstance(raw, dict) and ("uid" in raw or "eventId" in raw or "id" in raw):
            events.append(_normalize_event(raw))
    return events[:limit]


def get_event(client: ZohoClient, event_id: str) -> dict[str, Any]:
    """Fetch a single event by ID."""

    uid = _calendar_uid(None, client)
    response = client.get(_endpoint(f"calendars/{uid}/events/{event_id}"))
    events = response.get("events", []) or response.get("data", []) or []
    if events and isinstance(events, list):
        return _normalize_event(events[0])
    if isinstance(events, dict):
        return _normalize_event(events)
    return _normalize_event(response)


def create_event(
    client: ZohoClient,
    *,
    title: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    calendar_id: str | None = None,
) -> dict[str, Any]:
    """Create an event in the selected calendar."""

    if calendar_id:
        uid = calendar_id
        tz = "UTC"
    else:
        cal = _default_calendar(client)
        uid = cal["uid"]
        tz = cal.get("raw", {}).get("timezone") or tz

    def _fmt_datetime(value: str) -> str:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y%m%dT%H%M%SZ")
        except ValueError:
            return value

    payload: dict[str, Any] = {
        "title": title,
        "dateandtime": {
            "start": _fmt_datetime(start),
            "end": _fmt_datetime(end),
            "timezone": tz,
        },
    }
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location
    if attendees:
        payload["attendees"] = [{"email": email, "status": "NEEDS-ACTION"} for email in attendees]

    response = client.post(
        _endpoint(f"calendars/{uid}/events"),
        data={"eventdata": json.dumps(payload)},
    )
    events = response.get("events", []) or response.get("data", []) or []
    if events and isinstance(events, list):
        data = events[0]
    elif isinstance(events, dict):
        data = events
    else:
        data = response
    return {
        "eventId": str(data.get("eventId", data.get("uid", ""))),
        "title": title,
        "start": start,
        "end": end,
        "status": response.get("status", {}).get("description", "success"),
    }


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    dt = raw.get("dateandtime", {})
    return {
        "eventId": str(raw.get("eventId", raw.get("uid", raw.get("id", "")))),
        "title": str(raw.get("title", "")),
        "start": str(dt.get("start", raw.get("start", ""))),
        "end": str(dt.get("end", raw.get("end", ""))),
        "location": str(raw.get("location", "")),
        "description": str(raw.get("description", "")),
        "raw": raw,
    }


__all__ = [
    "create_event",
    "get_event",
    "list_calendars",
    "list_events",
]
