"""Zoho Mail operations."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zog.config import load_account_token, save_account_token
from zog.errors import ApiError, ConfigError
from zog.providers.zoho import endpoints
from zog.providers.zoho.client import ZohoClient

SKIP_FOLDER_TYPES = {"Drafts", "Templates", "Outbox"}


def get_account(client: ZohoClient) -> dict[str, Any]:
    """Load the Zoho account matching the CLI email."""

    token = load_account_token(client.email)
    if token.account_id:
        response = client.get(endpoints.accounts(token.api_url))
        account = _match_account(response.get("data", []), client.email)
        if account is None:
            raise ConfigError(f"Unable to find Zoho account for {client.email}")
        return account

    response = client.get(endpoints.accounts(token.api_url))
    account = _match_account(response.get("data", []), client.email)
    if account is None:
        raise ConfigError(f"Unable to find Zoho account for {client.email}")
    token.account_id = str(account["accountId"])
    save_account_token(client.email, token)
    return account


def list_accounts(client: ZohoClient) -> list[dict[str, Any]]:
    """Return normalized accounts for the current principal."""

    token = load_account_token(client.email)
    response = client.get(endpoints.accounts(token.api_url))
    accounts = []
    for raw in response.get("data", []):
        accounts.append(
            {
                "email": raw.get("primaryEmailAddress") or raw.get("mailboxAddress"),
                "accountId": str(raw.get("accountId", "")),
                "displayName": raw.get("displayName") or raw.get("accountDisplayName") or "",
                "apiUrl": token.api_url,
            }
        )
    return accounts


def list_folders(client: ZohoClient) -> list[dict[str, Any]]:
    """Return normalized folders for the active account."""

    token = load_account_token(client.email)
    account = get_account(client)
    response = client.get(endpoints.folders(token.api_url, str(account["accountId"])))
    folders = []
    for raw in response.get("data", []):
        folders.append(
            {
                "id": str(raw.get("folderId", "")),
                "name": str(raw.get("folderName", "")),
                "type": str(raw.get("folderType", "")),
                "path": str(raw.get("path", "")),
                "raw": raw,
            }
        )
    return folders


def search_messages(client: ZohoClient, query: str, *, limit: int) -> list[dict[str, Any]]:
    """Search messages across user folders."""

    token = load_account_token(client.email)
    account = get_account(client)
    folders = list_folders(client)
    results_by_id: dict[str, dict[str, Any]] = {}

    for folder in folders:
        if folder["type"] in SKIP_FOLDER_TYPES:
            continue
        response = client.get(
            endpoints.messages_view(token.api_url, str(account["accountId"])),
            params={
                "folderId": folder["id"],
                "limit": max(limit, 1),
                "start": 1,
                "searchKey": query,
            },
        )
        for raw in response.get("data", []) or []:
            normalized = _normalize_message_summary(raw, folder_name=folder["name"])
            results_by_id.setdefault(normalized["id"], normalized)

    results = sorted(
        results_by_id.values(),
        key=lambda item: item["timestamp"],
        reverse=True,
    )
    return results[:limit]


def get_message(client: ZohoClient, message_id: str) -> dict[str, Any]:
    """Fetch a single message body by scanning available folders."""

    token = load_account_token(client.email)
    account = get_account(client)
    last_error: ApiError | None = None
    for folder in list_folders(client):
        try:
            response = client.get(
                endpoints.message_content(
                    token.api_url,
                    str(account["accountId"]),
                    folder["id"],
                    message_id,
                )
            )
        except ApiError as exc:
            last_error = exc
            if exc.status_code in {400, 404}:
                continue
            continue
        data = response.get("data", {})
        return {
            "messageId": str(data.get("messageId", message_id)),
            "folderId": folder["id"],
            "folderName": folder["name"],
            "content": str(data.get("content", "")),
        }
    if last_error is not None:
        raise ConfigError(f"Message {message_id} was not found in any folder.")
    raise ConfigError(f"Message {message_id} was not found.")


def get_thread(client: ZohoClient, thread_id: str) -> list[dict[str, Any]]:
    """Fetch all messages for a thread."""

    token = load_account_token(client.email)
    account = get_account(client)
    response = client.get(
        endpoints.messages_view(token.api_url, str(account["accountId"])),
        params={"threadId": thread_id},
    )
    return [_normalize_message_summary(raw, folder_name="") for raw in response.get("data", []) or []]


def send_message(
    client: ZohoClient,
    *,
    to_address: str,
    subject: str,
    body: str | None = None,
    body_file: str | None = None,
    body_html: str | None = None,
    cc_address: str | None = None,
    bcc_address: str | None = None,
    from_address: str | None = None,
    reply_to_message_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Send or dry-run a message through Zoho Mail."""

    token = load_account_token(client.email)
    account = get_account(client)
    content = resolve_body(body=body, body_file=body_file, body_html=body_html)
    payload = {
        "fromAddress": from_address or client.email,
        "toAddress": to_address,
        "subject": subject,
        "content": content,
        "mailFormat": "html" if body_html is not None else "plaintext",
        "askReceipt": "no",
    }
    if cc_address:
        payload["ccAddress"] = cc_address
    if bcc_address:
        payload["bccAddress"] = bcc_address
    if reply_to_message_id:
        payload["inReplyTo"] = reply_to_message_id

    if dry_run:
        return {
            "dryRun": True,
            "accountId": str(account["accountId"]),
            "payload": payload,
        }

    response = client.post(
        endpoints.send_message(token.api_url, str(account["accountId"])),
        json_body=payload,
    )
    data = response.get("data", {})
    return {
        "dryRun": False,
        "accountId": str(account["accountId"]),
        "messageId": str(data.get("messageId", "")),
        "status": response.get("status", {}).get("description", "success"),
    }


def resolve_body(
    *,
    body: str | None,
    body_file: str | None,
    body_html: str | None,
) -> str:
    """Resolve body content from CLI flags."""

    if body_html is not None:
        return body_html
    if body_file is not None:
        return Path(body_file).expanduser().read_text(encoding="utf-8")
    if body is not None:
        return body
    raise ConfigError("One of --body, --body-file, or --body-html is required.")


def _match_account(accounts: list[dict[str, Any]], email: str) -> dict[str, Any] | None:
    target = email.lower()
    for account in accounts:
        candidates = {
            str(account.get("primaryEmailAddress", "")).lower(),
            str(account.get("mailboxAddress", "")).lower(),
        }
        for alias in account.get("emailAddress", []) or []:
            if isinstance(alias, dict):
                candidates.add(str(alias.get("mailId", "")).lower())
        if target in candidates:
            return account
    return None


def _normalize_message_summary(raw: dict[str, Any], *, folder_name: str) -> dict[str, Any]:
    timestamp_raw = raw.get("receivedTime") or raw.get("sentDateInGMT") or 0
    timestamp = int(timestamp_raw)
    return {
        "id": str(raw.get("messageId", "")),
        "date": _format_timestamp(timestamp),
        "from": html.unescape(str(raw.get("fromAddress") or raw.get("sender") or "")),
        "subject": html.unescape(str(raw.get("subject") or "")),
        "labels": folder_name or "",
        "thread": str(raw.get("threadId", "")),
        "folderId": str(raw.get("folderId", "")),
        "summary": html.unescape(str(raw.get("summary") or "")),
        "timestamp": timestamp,
    }


def _format_timestamp(value: int) -> str:
    seconds = value / 1000 if value > 10_000_000_000 else value
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


__all__ = [
    "get_account",
    "get_message",
    "get_thread",
    "list_accounts",
    "list_folders",
    "resolve_body",
    "search_messages",
    "send_message",
]
