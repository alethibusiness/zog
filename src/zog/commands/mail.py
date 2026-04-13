"""Mail command handlers."""

from __future__ import annotations

from zog.config import resolve_account
from zog.output import print_mapping, print_rows
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.mail import (
    get_message,
    get_thread,
    list_folders,
    search_messages,
    send_message,
)

SEARCH_COLUMNS = [
    ("ID", "id"),
    ("DATE", "date"),
    ("FROM", "from"),
    ("SUBJECT", "subject"),
    ("LABELS", "labels"),
    ("THREAD", "thread"),
]

FOLDER_COLUMNS = [
    ("ID", "id"),
    ("NAME", "name"),
    ("TYPE", "type"),
    ("PATH", "path"),
]

MESSAGE_FIELDS = [
    ("MESSAGE_ID", "messageId"),
    ("FOLDER_ID", "folderId"),
    ("FOLDER_NAME", "folderName"),
    ("CONTENT", "content"),
]

SEND_FIELDS = [
    ("DRY_RUN", "dryRun"),
    ("ACCOUNT_ID", "accountId"),
    ("MESSAGE_ID", "messageId"),
    ("STATUS", "status"),
]


def handle_search(args) -> int:
    """Search mail for the selected account."""

    client = _client_from_args(args)
    rows = search_messages(client, args.query, limit=args.max_results)
    print_rows(rows, SEARCH_COLUMNS, args, empty_message="No messages found.")
    return 0


def handle_get(args) -> int:
    """Fetch a single message."""

    client = _client_from_args(args)
    message = get_message(client, args.message_id)
    print_mapping(message, args, fields=MESSAGE_FIELDS)
    return 0


def handle_thread_get(args) -> int:
    """Fetch a mail thread."""

    client = _client_from_args(args)
    rows = get_thread(client, args.thread_id)
    print_rows(rows, SEARCH_COLUMNS, args, empty_message="No messages found for that thread.")
    return 0


def handle_send(args) -> int:
    """Send or dry-run a mail message."""

    client = _client_from_args(args)
    result = send_message(
        client,
        to_address=args.to,
        subject=args.subject,
        body=args.body,
        body_file=args.body_file,
        body_html=args.body_html,
        cc_address=args.cc,
        bcc_address=args.bcc,
        from_address=args.from_address,
        reply_to_message_id=args.reply_to_message_id,
        dry_run=args.dry_run,
    )
    print_mapping(result, args, fields=SEND_FIELDS)
    return 0


def handle_folders(args) -> int:
    """List folders for the selected account."""

    client = _client_from_args(args)
    rows = list_folders(client)
    print_rows(rows, FOLDER_COLUMNS, args, empty_message="No folders found.")
    return 0


def _client_from_args(args) -> ZohoClient:
    account = resolve_account(args.account)
    return ZohoClient(account, verbose=args.verbose)


__all__ = [
    "handle_folders",
    "handle_get",
    "handle_search",
    "handle_send",
    "handle_thread_get",
]

