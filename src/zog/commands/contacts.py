"""Contacts command handlers."""

from __future__ import annotations

from zog.config import resolve_account
from zog.output import print_mapping, print_rows
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.contacts import (
    create_contact,
    get_contact,
    list_contacts,
)

CONTACT_COLUMNS = [
    ("CONTACT_ID", "contactId"),
    ("NAME", "name"),
    ("EMAIL", "email"),
    ("PHONE", "phone"),
    ("COMPANY", "company"),
]

CREATE_FIELDS = [
    ("CONTACT_ID", "contactId"),
    ("NAME", "name"),
    ("EMAIL", "email"),
    ("STATUS", "status"),
]


def handle_list(args) -> int:
    """List contacts for the selected account."""

    client = _client_from_args(args)
    rows = list_contacts(client, limit=args.max_results)
    print_rows(rows, CONTACT_COLUMNS, args, empty_message="No contacts found.")
    return 0


def handle_get(args) -> int:
    """Fetch a single contact."""

    client = _client_from_args(args)
    contact = get_contact(client, args.contact_id)
    print_mapping(contact, args, fields=CONTACT_COLUMNS)
    return 0


def handle_create(args) -> int:
    """Create a new contact."""

    client = _client_from_args(args)
    result = create_contact(
        client,
        name=args.name,
        email=args.email,
        phone=args.phone,
        company=args.company,
    )
    print_mapping(result, args, fields=CREATE_FIELDS)
    return 0


def _client_from_args(args) -> ZohoClient:
    account = resolve_account(args.account)
    return ZohoClient(account, verbose=args.verbose)


__all__ = [
    "handle_create",
    "handle_get",
    "handle_list",
]
