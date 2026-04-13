"""Calendar command handlers."""

from __future__ import annotations

from zog.config import resolve_account
from zog.output import print_mapping, print_rows
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.calendar import (
    create_event as create_calendar_event,
    get_event,
    list_calendars,
    list_events,
)

CALENDAR_COLUMNS = [
    ("ID", "id"),
    ("NAME", "name"),
    ("TYPE", "type"),
]

EVENT_COLUMNS = [
    ("EVENT_ID", "eventId"),
    ("TITLE", "title"),
    ("START", "start"),
    ("END", "end"),
    ("LOCATION", "location"),
]

EVENT_FIELDS = [
    ("EVENT_ID", "eventId"),
    ("TITLE", "title"),
    ("START", "start"),
    ("END", "end"),
    ("LOCATION", "location"),
    ("DESCRIPTION", "description"),
]

CREATE_FIELDS = [
    ("EVENT_ID", "eventId"),
    ("TITLE", "title"),
    ("START", "start"),
    ("END", "end"),
    ("STATUS", "status"),
]


def handle_calendars_list(args) -> int:
    """List calendars for the selected account."""

    client = _client_from_args(args)
    rows = list_calendars(client)
    print_rows(rows, CALENDAR_COLUMNS, args, empty_message="No calendars found.")
    return 0


def handle_events_list(args) -> int:
    """List events for the selected account."""

    client = _client_from_args(args)
    rows = list_events(
        client,
        calendar_id=args.calendar_id,
        start=args.start,
        end=args.end,
        limit=args.max_results,
    )
    print_rows(rows, EVENT_COLUMNS, args, empty_message="No events found.")
    return 0


def handle_events_get(args) -> int:
    """Fetch a single event."""

    client = _client_from_args(args)
    event = get_event(client, args.event_id)
    print_mapping(event, args, fields=EVENT_FIELDS)
    return 0


def handle_events_create(args) -> int:
    """Create a calendar event."""

    client = _client_from_args(args)
    attendees = [email.strip() for email in args.attendees.split(",")] if args.attendees else None
    result = create_calendar_event(
        client,
        calendar_id=args.calendar_id,
        title=args.title,
        start=args.start,
        end=args.end,
        description=args.description,
        location=args.location,
        attendees=attendees,
    )
    print_mapping(result, args, fields=CREATE_FIELDS)
    return 0


def _client_from_args(args) -> ZohoClient:
    account = resolve_account(args.account)
    return ZohoClient(account, verbose=args.verbose)


__all__ = [
    "handle_calendars_list",
    "handle_events_create",
    "handle_events_get",
    "handle_events_list",
]
