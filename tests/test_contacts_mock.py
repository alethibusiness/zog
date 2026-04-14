from __future__ import annotations

from unittest.mock import Mock

import pytest

from zog.config import StoredToken, save_account_token
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.contacts import create_contact, get_contact, list_contacts


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


def test_list_contacts(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        return_value=_response(
            200,
            {
                "contacts": [
                    {"contact_id": "c1", "first_name": "Alice", "last_name": "Smith", "emails": [{"email_id": "alice@example.com"}], "phones": [{"number": "555-1234", "type": "mobile"}], "company": "Acme"},
                    {"contact_id": "c2", "first_name": "Bob", "last_name": "Jones", "emails": [{"email_id": "bob@example.com"}]},
                ]
            },
        ),
    )
    client = ZohoClient("admin@example.com")
    contacts = list_contacts(client, limit=10)
    assert len(contacts) == 2
    assert contacts[0]["contactId"] == "c1"
    assert contacts[0]["name"] == "Alice Smith"
    assert contacts[0]["email"] == "alice@example.com"
    assert contacts[0]["phone"] == "555-1234"
    assert contacts[0]["company"] == "Acme"


def test_get_contact(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        return_value=_response(
            200,
            {
                "contacts": {"contact_id": "c1", "first_name": "Alice", "last_name": "Smith", "emails": [{"email_id": "alice@example.com"}]},
            },
        ),
    )
    client = ZohoClient("admin@example.com")
    contact = get_contact(client, "c1")
    assert contact["contactId"] == "c1"
    assert contact["name"] == "Alice Smith"
    assert contact["email"] == "alice@example.com"


def test_create_contact(mocker):
    mocker.patch(
        "zog.providers.zoho.client.requests.request",
        return_value=_response(
            200,
            {
                "contacts": {"contact_id": "c99"},
                "status": {"code": 200, "description": "success"},
            },
        ),
    )
    client = ZohoClient("admin@example.com")
    result = create_contact(
        client,
        name="Charlie Brown",
        email="charlie@example.com",
        phone="555-9999",
        company="Peanuts",
    )
    assert result["contactId"] == "c99"
    assert result["name"] == "Charlie Brown"
    assert result["email"] == "charlie@example.com"
    assert result["status"] == "success"
