"""Zoho Contacts operations."""

from __future__ import annotations

from typing import Any

from zog.providers.zoho.client import ZohoClient

CONTACTS_API_URL = "https://contacts.zoho.com/api/v1"


def _endpoint(path: str) -> str:
    return f"{CONTACTS_API_URL.rstrip('/')}/{path.lstrip('/')}"


def list_contacts(client: ZohoClient, *, limit: int = 50) -> list[dict[str, Any]]:
    """Return normalized contacts for the active account."""

    response = client.get(_endpoint("contacts"), params={"limit": max(limit, 1)})
    contacts = []
    for raw in response.get("data", []) or []:
        contacts.append(_normalize_contact(raw))
    return contacts[:limit]


def get_contact(client: ZohoClient, contact_id: str) -> dict[str, Any]:
    """Fetch a single contact by ID."""

    response = client.get(_endpoint(f"contacts/{contact_id}"))
    return _normalize_contact(response.get("data", {}) or {})


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
        "firstName": first_name,
        "lastName": last_name,
        "email": [{"email": email}],
    }
    if phone:
        payload["phone"] = [{"phone": phone}]
    if company:
        payload["company"] = company

    response = client.post(_endpoint("contacts"), json_body=payload)
    data = response.get("data", {}) or {}
    return {
        "contactId": str(data.get("contactId", "")),
        "name": name,
        "email": email,
        "status": response.get("status", {}).get("description", "success"),
    }


def _normalize_contact(raw: dict[str, Any]) -> dict[str, Any]:
    contact_id = str(raw.get("contactId", raw.get("id", "")))
    first_name = str(raw.get("firstName", ""))
    last_name = str(raw.get("lastName", ""))
    name = f"{first_name} {last_name}".strip()
    emails = raw.get("email", []) or []
    email = emails[0].get("email", "") if isinstance(emails, list) and emails else ""
    phones = raw.get("phone", []) or []
    phone = phones[0].get("phone", "") if isinstance(phones, list) and phones else ""
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
