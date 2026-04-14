"""Argument parsing and CLI dispatch."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from zog import __version__
from zog.commands import auth as auth_commands
from zog.commands import calendar as calendar_commands
from zog.commands import contacts as contacts_commands
from zog.commands import mail as mail_commands
from zog.commands import workdrive as workdrive_commands
from zog.errors import ZogError


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""

    globals_parent = _build_global_parent()
    parser = argparse.ArgumentParser(prog="zog", description="Zoho CLI.")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    auth_parser = subparsers.add_parser("auth", help="Manage Zoho credentials.", parents=[globals_parent])
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

    auth_add = auth_subparsers.add_parser(
        "add",
        help="Add an account with the Zoho OAuth grant-code flow.",
        parents=[globals_parent],
    )
    auth_add.add_argument("email")
    auth_add.add_argument(
        "--services",
        type=_services_csv,
        default="mail,calendar,contacts,workdrive",
        help="Comma-separated services to authorize (mail,calendar,contacts,workdrive).",
    )
    auth_add.add_argument(
        "--device",
        action="store_true",
        help="Use OAuth 2.0 Device Flow (default).",
    )
    auth_add.add_argument(
        "--self-client",
        action="store_true",
        help="Use Self Client grant-code flow instead of device flow.",
    )
    auth_add.add_argument(
        "--client-id",
        dest="client_id",
        help="Override the default OAuth client ID.",
    )
    auth_add.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="Open the verification URL in a web browser (TTY only).",
    )
    auth_add.set_defaults(func=auth_commands.handle_add)

    auth_list = auth_subparsers.add_parser("list", help="List stored accounts.", parents=[globals_parent])
    auth_list.set_defaults(func=auth_commands.handle_list)

    auth_remove = auth_subparsers.add_parser(
        "remove",
        help="Remove stored credentials.",
        parents=[globals_parent],
    )
    auth_remove.add_argument("email")
    auth_remove.set_defaults(func=auth_commands.handle_remove)

    auth_import = auth_subparsers.add_parser(
        "import-legacy",
        help="Import a legacy Zoho credential file.",
        parents=[globals_parent],
    )
    auth_import.add_argument("path")
    auth_import.set_defaults(func=auth_commands.handle_import_legacy)

    mail_parser = subparsers.add_parser("mail", help="Zoho Mail operations.", parents=[globals_parent])
    mail_subparsers = mail_parser.add_subparsers(dest="mail_command")

    search_parser = mail_subparsers.add_parser("search", help="Search messages.", parents=[globals_parent])
    search_parser.add_argument("query")
    search_parser.add_argument("--max", dest="max_results", type=_positive_int, default=10)
    search_parser.set_defaults(func=mail_commands.handle_search)

    get_parser = mail_subparsers.add_parser("get", help="Fetch a single message.", parents=[globals_parent])
    get_parser.add_argument("message_id")
    get_parser.set_defaults(func=mail_commands.handle_get)

    thread_parser = mail_subparsers.add_parser("thread", help="Thread operations.", parents=[globals_parent])
    thread_subparsers = thread_parser.add_subparsers(dest="thread_command")
    thread_get = thread_subparsers.add_parser("get", help="Fetch a thread.", parents=[globals_parent])
    thread_get.add_argument("thread_id")
    thread_get.set_defaults(func=mail_commands.handle_thread_get)

    send_parser = mail_subparsers.add_parser("send", help="Send a message.", parents=[globals_parent])
    send_parser.add_argument("--to", required=True)
    send_parser.add_argument("--subject", required=True)
    body_group = send_parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body")
    body_group.add_argument("--body-file")
    body_group.add_argument("--body-html")
    send_parser.add_argument("--cc")
    send_parser.add_argument("--bcc")
    send_parser.add_argument("--reply-to-message-id")
    send_parser.add_argument("--from", dest="from_address")
    send_parser.add_argument("--dry-run", action="store_true")
    send_parser.set_defaults(func=mail_commands.handle_send)

    folders_parser = mail_subparsers.add_parser("folders", help="List folders.", parents=[globals_parent])
    folders_parser.set_defaults(func=mail_commands.handle_folders)

    calendar_parser = subparsers.add_parser("calendar", help="Zoho Calendar operations.", parents=[globals_parent])
    calendar_subparsers = calendar_parser.add_subparsers(dest="calendar_command")

    cal_list = calendar_subparsers.add_parser("list", help="List available calendars.", parents=[globals_parent])
    cal_list.set_defaults(func=calendar_commands.handle_calendars_list)

    events_parser = calendar_subparsers.add_parser("events", help="Calendar event operations.")
    events_subparsers = events_parser.add_subparsers(dest="events_command")

    events_list = events_subparsers.add_parser("list", help="List events.", parents=[globals_parent])
    events_list.add_argument("--calendar-id")
    events_list.add_argument("--start")
    events_list.add_argument("--end")
    events_list.add_argument("--max", dest="max_results", type=_positive_int, default=50)
    events_list.set_defaults(func=calendar_commands.handle_events_list)

    events_get = events_subparsers.add_parser("get", help="Fetch a single event.", parents=[globals_parent])
    events_get.add_argument("event_id")
    events_get.set_defaults(func=calendar_commands.handle_events_get)

    events_create = events_subparsers.add_parser("create", help="Create an event.", parents=[globals_parent])
    events_create.add_argument("--calendar-id")
    events_create.add_argument("--title", required=True)
    events_create.add_argument("--start", required=True)
    events_create.add_argument("--end", required=True)
    events_create.add_argument("--description")
    events_create.add_argument("--location")
    events_create.add_argument("--attendees")
    events_create.set_defaults(func=calendar_commands.handle_events_create)

    contacts_parser = subparsers.add_parser("contacts", help="Zoho Contacts operations.", parents=[globals_parent])
    contacts_subparsers = contacts_parser.add_subparsers(dest="contacts_command")

    contacts_list = contacts_subparsers.add_parser("list", help="List contacts.", parents=[globals_parent])
    contacts_list.add_argument("--max", dest="max_results", type=_positive_int, default=50)
    contacts_list.set_defaults(func=contacts_commands.handle_list)

    contacts_get = contacts_subparsers.add_parser("get", help="Fetch a single contact.", parents=[globals_parent])
    contacts_get.add_argument("contact_id")
    contacts_get.set_defaults(func=contacts_commands.handle_get)

    contacts_create = contacts_subparsers.add_parser("create", help="Create a contact.", parents=[globals_parent])
    contacts_create.add_argument("--name", required=True)
    contacts_create.add_argument("--email", required=True)
    contacts_create.add_argument("--phone")
    contacts_create.add_argument("--company")
    contacts_create.set_defaults(func=contacts_commands.handle_create)

    workdrive_parser = subparsers.add_parser("workdrive", help="Zoho WorkDrive operations.", parents=[globals_parent])
    workdrive_subparsers = workdrive_parser.add_subparsers(dest="workdrive_command")

    wd_files = workdrive_subparsers.add_parser("files", help="WorkDrive file operations.")
    wd_files_subparsers = wd_files.add_subparsers(dest="workdrive_files_command")

    wd_files_list = wd_files_subparsers.add_parser("list", help="List files in root.", parents=[globals_parent])
    wd_files_list.set_defaults(func=workdrive_commands.handle_files_list)

    wd_files_get = wd_files_subparsers.add_parser("get", help="Fetch a single file.", parents=[globals_parent])
    wd_files_get.add_argument("file_id")
    wd_files_get.set_defaults(func=workdrive_commands.handle_files_get)

    wd_upload = workdrive_subparsers.add_parser("upload", help="Upload a file.", parents=[globals_parent])
    wd_upload.add_argument("path")
    wd_upload.add_argument("--folder")
    wd_upload.set_defaults(func=workdrive_commands.handle_upload)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    logging.basicConfig(level=logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING, format="%(message)s")
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except ZogError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _build_global_parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("-j", "--json", action="store_true", help="Emit JSON output.")
    output_group.add_argument("-p", "--plain", action="store_true", help="Emit plain TSV output.")
    parser.add_argument("-a", "--account", help="Stored account email.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    return parser


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--max must be greater than zero")
    return parsed


def _services_csv(value: str) -> list[str]:
    services = [item.strip().lower() for item in value.split(",") if item.strip()]
    allowed = {"mail", "calendar", "contacts", "workdrive"}
    invalid = [svc for svc in services if svc not in allowed]
    if invalid:
        raise argparse.ArgumentTypeError(f"invalid services: {', '.join(invalid)}; allowed: {', '.join(sorted(allowed))}")
    return services


__all__ = ["build_parser", "main"]
