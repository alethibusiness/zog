"""Zoho Contacts operations."""

from __future__ import annotations

from typing import Any

from zog.providers.zoho.client import ZohoClient

CONTACTS_API_URL = "https://contacts.zoho.com/api/v1"


def _endpoint(path: str) -> str:
    return f"{CONTACTS_API_URL.rstrip('/')}/{path.lstrip('/')}"


def list_contacts(client: ZohoClient, *, limit: int = 50) -> list[dict[str, Any]]:
    """Return normalized contacts for the active account."""

    response = client.get(_endpoint("accounts/self/contacts"))
    contacts = []
    for raw in response.get("contacts", []) or response.get("data", []) or []:
        contacts.append(_normalize_contact(raw))
    return contacts[:limit]


def get_contact(client: ZohoClient, contact_id: str) -> dict[str, Any]:
    """Fetch a single contact by ID."""

    response = client.get(_endpoint(f"accounts/self/contacts/{contact_id}"))
    raw = response.get("contacts", {}) or response.get("data", {}) or {}
    return _normalize_contact(raw)


def create_contact(
    client: ZohoClient,
    *,
    name: str,
    email: str,
    phone: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """Create a new contact."""

    first_name, last_name = _split_name(name)
    payload: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "emails": [{"email_id": email}],
    }
    if phone:
        payload["phones"] = [{"number": phone, "type": "mobile"}]
    if company:
        payload["company"] = company

    response = client.post(
        _endpoint("accounts/self/contacts?source=zog"),
        json_body={"contacts": payload},
    )
    data = response.get("contacts", {}) or response.get("data", {}) or {}
    return {
        "contactId": str(data.get("contact_id", data.get("contactId", ""))),
        "name": name,
        "email": email,
        "status": response.get("status", {}).get("description", "success"),
    }


def _normalize_contact(raw: dict[str, Any]) -> dict[str, Any]:
    contact_id = str(raw.get("contact_id", raw.get("id", "")))
    first_name = str(raw.get("first_name", ""))
    last_name = str(raw.get("last_name", ""))
    name = f"{first_name} {last_name}".strip()
    emails = raw.get("emails", []) or raw.get("email", []) or []
    email = ""
    if isinstance(emails, list) and emails:
        email = emails[0].get("email_id", emails[0].get("email", ""))
    phones = raw.get("phones", []) or raw.get("phone", []) or []
    phone = ""
    if isinstance(phones, list) and phones:
        phone = phones[0].get("number", phones[0].get("phone", ""))
    return {
        "contactId": contact_id,
        "name": name,
        "email": email,
        "phone": phone,
        "company": str(raw.get("company", "")),
        "raw": raw,
    }


def _split_name(name: str) -> tuple[str, str]:
    parts = name.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


__all__ = [
    "create_contact",
    "get_contact",
    "list_contacts",
]
