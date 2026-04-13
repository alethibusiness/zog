"""Zoho endpoint helpers."""

from __future__ import annotations


def oauth_token(accounts_url: str) -> str:
    return f"{accounts_url.rstrip('/')}/oauth/v2/token"


def accounts(api_url: str) -> str:
    return f"{api_url.rstrip('/')}/api/accounts"


def folders(api_url: str, account_id: str) -> str:
    return f"{api_url.rstrip('/')}/api/accounts/{account_id}/folders"


def messages_view(api_url: str, account_id: str) -> str:
    return f"{api_url.rstrip('/')}/api/accounts/{account_id}/messages/view"


def message_content(api_url: str, account_id: str, folder_id: str, message_id: str) -> str:
    return (
        f"{api_url.rstrip('/')}/api/accounts/{account_id}/folders/{folder_id}"
        f"/messages/{message_id}/content"
    )


def message_header(api_url: str, account_id: str, folder_id: str, message_id: str) -> str:
    return (
        f"{api_url.rstrip('/')}/api/accounts/{account_id}/folders/{folder_id}"
        f"/messages/{message_id}/header"
    )


def send_message(api_url: str, account_id: str) -> str:
    return f"{api_url.rstrip('/')}/api/accounts/{account_id}/messages"


__all__ = [
    "accounts",
    "folders",
    "message_content",
    "message_header",
    "messages_view",
    "oauth_token",
    "send_message",
]

