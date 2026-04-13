"""WorkDrive command handlers."""

from __future__ import annotations

from zog.config import resolve_account
from zog.output import print_mapping, print_rows
from zog.providers.zoho.client import ZohoClient
from zog.providers.zoho.workdrive import (
    get_file,
    list_files,
    upload_file,
)

FILE_COLUMNS = [
    ("FILE_ID", "fileId"),
    ("NAME", "name"),
    ("TYPE", "type"),
]


def handle_files_list(args) -> int:
    """List files for the selected account."""

    client = _client_from_args(args)
    rows = list_files(client)
    print_rows(rows, FILE_COLUMNS, args, empty_message="No files found.")
    return 0


def handle_files_get(args) -> int:
    """Fetch a single file."""

    client = _client_from_args(args)
    file_info = get_file(client, args.file_id)
    print_mapping(file_info, args, fields=FILE_COLUMNS)
    return 0


def handle_upload(args) -> int:
    """Upload a file to WorkDrive."""

    client = _client_from_args(args)
    result = upload_file(client, args.path, folder_id=args.folder)
    print_mapping(result, args)
    return 0


def _client_from_args(args) -> ZohoClient:
    account = resolve_account(args.account)
    return ZohoClient(account, verbose=args.verbose)


__all__ = [
    "handle_files_get",
    "handle_files_list",
    "handle_upload",
]
