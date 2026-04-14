"""Auth command handlers."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from zog.config import (
    DEFAULT_ACCOUNTS_URL,
    DEFAULT_API_URL,
    StoredToken,
    import_legacy_credentials,
    list_account_emails,
    load_account_token,
    remove_account_token,
    save_account_token,
    set_default_account,
)
from zog.errors import AuthError
from zog.output import print_mapping, print_rows
from zog.providers.zoho.app import get_client_id, get_client_secret
from zog.providers.zoho.auth import (
    exchange_grant_code,
    print_self_client_instructions,
    read_client_credentials,
    scopes_for_services,
)
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.mail import get_account
from zog.providers.zoho.oauth_flow import (
    ZohoOAuthFlowError,
    run_loopback_flow,
    run_oob_flow,
)

AUTH_COLUMNS = [
    ("EMAIL", "email"),
    ("DEFAULT", "default"),
    ("ACCOUNT_ID", "accountId"),
    ("API_URL", "apiUrl"),
]


def handle_add(args) -> int:
    """Add Zoho credentials for an account."""

    scopes = scopes_for_services(getattr(args, "services", []))

    if getattr(args, "self_client", False):
        return _handle_add_self_client(args, scopes)

    if getattr(args, "oob", False) or getattr(args, "no_browser", False):
        return _handle_add_oob(args, scopes)

    return _handle_add_loopback(args, scopes)


def _handle_add_loopback(args, scopes: list[str]) -> int:
    client_id = getattr(args, "client_id", None) or get_client_id()
    client_secret = get_client_secret()
    if not client_secret:
        print("Error: No client secret available.", file=sys.stderr)
        return 1

    port = getattr(args, "port", None)
    open_browser = not getattr(args, "no_browser", False)

    print("Opening browser...", flush=True)
    try:
        print("Waiting for authorization...", flush=True)
        payload = run_loopback_flow(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            port=port,
            open_browser=open_browser,
        )
    except ZohoOAuthFlowError as exc:
        err_msg = str(exc)
        if "Unable to bind" in err_msg or "None of the local ports" in err_msg:
            print(
                f"Local callback server unavailable ({err_msg}). Falling back to out-of-band flow.\n",
                file=sys.stderr,
            )
            return _handle_add_oob(args, scopes)
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    print("Authorized.")
    return _save_token_and_finish(args, payload, client_id, client_secret, "oauth_code")


def _handle_add_oob(args, scopes: list[str]) -> int:
    client_id = getattr(args, "client_id", None) or get_client_id()
    client_secret = get_client_secret()
    if not client_secret:
        print("Error: No client secret available.", file=sys.stderr)
        return 1

    try:
        payload = run_oob_flow(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
    except ZohoOAuthFlowError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    print("Authorized.")
    return _save_token_and_finish(args, payload, client_id, client_secret, "oauth_code")


def _handle_add_self_client(args, scopes: list[str]) -> int:
    client_id, client_secret = read_client_credentials()
    if getattr(args, "client_id", None):
        client_id = args.client_id
    print_self_client_instructions(scopes)
    grant_code = input("Grant Code: ").strip()
    try:
        payload = exchange_grant_code(
            accounts_url=DEFAULT_ACCOUNTS_URL,
            client_id=client_id,
            client_secret=client_secret,
            grant_code=grant_code,
        )
    except AuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return _save_token_and_finish(args, payload, client_id, client_secret, "self_client")


def _save_token_and_finish(
    args,
    payload: dict,
    client_id: str,
    client_secret: str | None,
    auth_method: str,
) -> int:
    token = StoredToken.from_mapping(
        {
            "auth_method": auth_method,
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
