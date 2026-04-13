"""Argument parsing and CLI dispatch."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from zog import __version__
from zog.commands import auth as auth_commands
from zog.commands import mail as mail_commands
from zog.errors import ZogError


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""

    globals_parent = _build_global_parent()
    parser = argparse.ArgumentParser(prog="zog", description="Zoho Mail CLI.")
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
    auth_add.add_argument("--services", choices=["mail"], default="mail")
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


__all__ = ["build_parser", "main"]

