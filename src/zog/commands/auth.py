"""Auth command handlers."""

from __future__ import annotations

import sys
import time
import webbrowser
from pathlib import Path

from zog.config import (
    DEFAULT_ACCOUNTS_URL,
    DEFAULT_API_URL,
    StoredToken,
    import_legacy_credentials,
    list_account_emails,
    load_config,
    load_account_token,
    remove_account_token,
    save_account_token,
    set_default_account,
)
from zog.errors import AuthError
from zog.output import print_mapping, print_rows
from zog.providers.zoho.app import get_client_id
from zog.providers.zoho.auth import (
    exchange_grant_code,
    print_self_client_instructions,
    read_client_credentials,
    scopes_for_services,
)
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.device_flow import (
    ZohoDeviceFlowError,
    initiate_device_flow,
    poll_for_token,
)
from zog.providers.zoho.mail import get_account

AUTH_COLUMNS = [
    ("EMAIL", "email"),
    ("DEFAULT", "default"),
    ("ACCOUNT_ID", "accountId"),
    ("API_URL", "apiUrl"),
]


def handle_add(args) -> int:
    """Add Zoho credentials for an account."""

    scopes = scopes_for_services(getattr(args, "services", []))
    auth_method = "self_client" if getattr(args, "self_client", False) else "device_flow"

    if auth_method == "device_flow":
        return _handle_add_device_flow(args, scopes)
    return _handle_add_self_client(args, scopes)


def _handle_add_device_flow(args, scopes: list[str]) -> int:
    client_id = getattr(args, "client_id", None) or get_client_id()

    print("Requesting device authorization from Zoho...")
    try:
        device_info = initiate_device_flow(
            client_id=client_id,
            scopes=scopes,
            accounts_url=DEFAULT_ACCOUNTS_URL,
        )
    except ZohoDeviceFlowError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Device flow is unavailable right now. Use `zog auth add <email> --self-client` to authenticate with a Zoho Self Client instead.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Device flow is unavailable right now. Use `zog auth add <email> --self-client` to authenticate with a Zoho Self Client instead.",
            file=sys.stderr,
        )
        return 1

    user_code = device_info.get("user_code", "")
    verification_uri = device_info.get("verification_uri", "")
    verification_uri_complete = device_info.get("verification_uri_complete", "")
    device_code = device_info.get("device_code", "")
    interval = int(device_info.get("interval", 5))
    expires_in = int(device_info.get("expires_in", 600))

    print(f"To authorize zog, visit: {verification_uri}")
    print(f"Enter code: {user_code}")
    if verification_uri_complete:
        print(f"(or open the pre-filled link: {verification_uri_complete})")

    if getattr(args, "open_browser", False) and sys.stdin.isatty() and verification_uri_complete:
        try:
            webbrowser.open(verification_uri_complete)
        except Exception:
            pass

    expires_min = expires_in // 60
    print(f"\nWaiting for authorization (expires in {expires_min} min)...", end="", flush=True)

    try:
        payload = poll_for_token(
            client_id=client_id,
            device_code=device_code,
            interval=interval,
            expires_in=expires_in,
            accounts_url=DEFAULT_ACCOUNTS_URL,
        )
    except ZohoDeviceFlowError as exc:
        print()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(" ✓")

    token = StoredToken.from_mapping(
        {
            "auth_method": "device_flow",
            "client_id": client_id,
            "refresh_token": payload["refresh_token"],
            "access_token": payload.get("access_token"),
            "access_token_expires_at": (
                int(time.time()) + max(int(payload.get("expires_in", 3600)) - 60, 0)
                if payload.get("access_token")
                else None
            ),
            "scope": payload.get("scope"),
            "api_url": DEFAULT_API_URL,
            "accounts_url": DEFAULT_ACCOUNTS_URL,
        }
    )
    save_account_token(args.email, token)
    client = ZohoClient(args.email, verbose=args.verbose)
    account = get_account(client)
    stored = load_account_token(args.email)
    stored.account_id = str(account["accountId"])
    save_account_token(args.email, stored)
    set_default_account(args.email)
    print_mapping(
        {
            "email": args.email,
            "accountId": str(account["accountId"]),
            "status": "added",
        },
        args,
        fields=[("EMAIL", "email"), ("ACCOUNT_ID", "accountId"), ("STATUS", "status")],
    )
    return 0


def _handle_add_self_client(args, scopes: list[str]) -> int:
    client_id, client_secret = read_client_credentials()
    if getattr(args, "client_id", None):
        client_id = args.client_id
    print_self_client_instructions(scopes)
    grant_code = input("Grant Code: ").strip()
    payload = exchange_grant_code(
        accounts_url=DEFAULT_ACCOUNTS_URL,
        client_id=client_id,
        client_secret=client_secret,
        grant_code=grant_code,
    )
    token = StoredToken.from_mapping(
        {
            "auth_method": "self_client",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": payload["refresh_token"],
            "access_token": payload.get("access_token"),
            "access_token_expires_at": (
                int(time.time()) + max(int(payload.get("expires_in", 3600)) - 60, 0)
                if payload.get("access_token")
                else None
            ),
            "scope": payload.get("scope"),
            "api_url": DEFAULT_API_URL,
            "accounts_url": DEFAULT_ACCOUNTS_URL,
        }
    )
    save_account_token(args.email, token)
    client = ZohoClient(args.email, verbose=args.verbose)
    account = get_account(client)
    stored = load_account_token(args.email)
    stored.account_id = str(account["accountId"])
    save_account_token(args.email, stored)
    set_default_account(args.email)
    print_mapping(
        {
            "email": args.email,
            "accountId": str(account["accountId"]),
            "status": "added",
        },
        args,
        fields=[("EMAIL", "email"), ("ACCOUNT_ID", "accountId"), ("STATUS", "status")],
    )
    return 0


def handle_list(args) -> int:
    """List stored accounts."""

    emails = list_account_emails()
    default_account = load_config().default_account
    rows = []
    for email in emails:
        token = load_account_token(email)
        rows.append(
            {
                "email": email,
                "default": "yes" if email == default_account else "",
                "accountId": token.account_id or "",
                "apiUrl": token.api_url,
            }
        )
    print_rows(rows, AUTH_COLUMNS, args, empty_message="No accounts configured.")
    return 0


def handle_remove(args) -> int:
    """Remove stored credentials for an account."""

    removed = remove_account_token(args.email)
    print_mapping(
        {
            "email": args.email,
            "removed": removed,
        },
        args,
        fields=[("EMAIL", "email"), ("REMOVED", "removed")],
    )
    return 0


def handle_import_legacy(args) -> int:
    """Import a legacy credential file."""

    email = args.account or "admin@alethiconsulting.com"
    imported = import_legacy_credentials(Path(args.path), email=email, overwrite=True, set_default=True)
    client = ZohoClient(email, verbose=args.verbose)
    account = None
    try:
        account = get_account(client)
    except Exception:
        account = None
    print_mapping(
        {
            "email": email,
            "imported": imported,
            "accountId": "" if account is None else str(account["accountId"]),
        },
        args,
        fields=[("EMAIL", "email"), ("IMPORTED", "imported"), ("ACCOUNT_ID", "accountId")],
    )
    return 0


__all__ = [
    "handle_add",
    "handle_import_legacy",
    "handle_list",
    "handle_remove",
]
