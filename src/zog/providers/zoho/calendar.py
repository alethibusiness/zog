"""Zoho Calendar operations."""

from __future__ import annotations

from typing import Any

from zog.providers.zoho.client import ZohoClient

CALENDAR_API_URL = "https://calendar.zoho.com/api/v1"


def _endpoint(path: str) -> str:
    return f"{CALENDAR_API_URL.rstrip('/')}/{path.lstrip('/')}"


def list_calendars(client: ZohoClient) -> list[dict[str, Any]]:
    """Return normalized calendars for the active account."""

    response = client.get(_endpoint("calendars"))
    calendars = []
    for raw in response.get("data", []) or []:
        calendars.append(
            {
                "id": str(raw.get("calendarId", raw.get("uid", ""))),
                "name": str(raw.get("name", "")),
                "type": str(raw.get("calendarType", "")),
                "raw": raw,
            }
        )
    return calendars


def list_events(
    client: ZohoClient,
    calendar_id: str | None = None,
    *,
    start: str | None = None,
    end: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return normalized events for the selected calendar."""

    if calendar_id is None:
        calendars = list_calendars(client)
        if not calendars:
            return []
        calendar_id = calendars[0]["id"]

    params: dict[str, Any] = {"limit": max(limit, 1)}
    if start:
        params["startDate"] = start
    if end:
        params["endDate"] = end

    response = client.get(_endpoint(f"calendars/{calendar_id}/events"), params=params)
    events = []
    for raw in response.get("data", []) or []:
        events.append(_normalize_event(raw))
    return events[:limit]


def get_event(client: ZohoClient, event_id: str) -> dict[str, Any]:
    """Fetch a single event by ID."""

    response = client.get(_endpoint(f"events/{event_id}"))
    return _normalize_event(response.get("data", {}) or {})


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

    if calendar_id is None:
        calendars = list_calendars(client)
        if not calendars:
            raise RuntimeError("No calendars available.")
        calendar_id = calendars[0]["id"]

    payload: dict[str, Any] = {
        "title": title,
        "start": start,
        "end": end,
    }
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location
    if attendees:
        payload["attendees"] = [{"email": email} for email in attendees]

    response = client.post(_endpoint(f"calendars/{calendar_id}/events"), json_body=payload)
    data = response.get("data", {}) or {}
    return {
        "eventId": str(data.get("eventId", "")),
        "title": title,
        "start": start,
        "end": end,
        "status": response.get("status", {}).get("description", "success"),
    }


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "eventId": str(raw.get("eventId", raw.get("uid", ""))),
        "title": str(raw.get("title", "")),
        "start": str(raw.get("start", "")),
        "end": str(raw.get("end", "")),
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
