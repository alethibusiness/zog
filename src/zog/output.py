"""Output helpers for pretty, plain, and JSON modes."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from typing import Any

ANSI_BOLD_CYAN = "\033[1;36m"
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"
ColumnSpec = Sequence[tuple[str, str]]


def determine_mode(args: Any) -> str:
    """Resolve the active output mode from argparse flags."""

    if getattr(args, "json", False):
        return "json"
    if getattr(args, "plain", False):
        return "plain"
    return "pretty"


def json_envelope(data: Any, *, next_page_token: str | None = None) -> dict[str, Any]:
    """Wrap command data in the standard JSON envelope."""

    payload: dict[str, Any] = {
        "status": "ok",
        "data": data,
    }
    if next_page_token is not None:
        payload["nextPageToken"] = next_page_token
    return payload


def format_json(data: Any, *, next_page_token: str | None = None) -> str:
    """Serialize data as JSON output."""

    return json.dumps(json_envelope(data, next_page_token=next_page_token), indent=2)


def format_plain_rows(rows: Sequence[dict[str, Any]], columns: ColumnSpec) -> str:
    """Render rows as tab-separated values without a header."""

    if not rows:
        return ""
    lines = []
    for row in rows:
        lines.append("\t".join(_plain_value(row.get(key, "")) for _, key in columns))
    return "\n".join(lines)


def format_plain_mapping(mapping: dict[str, Any], fields: ColumnSpec | None = None) -> str:
    """Render a single mapping as a tab-separated record."""

    if fields is None:
        values = mapping.values()
    else:
        values = [mapping.get(key, "") for _, key in fields]
    return "\t".join(_plain_value(value) for value in values)


def format_pretty_rows(
    rows: Sequence[dict[str, Any]],
    columns: ColumnSpec,
    *,
    use_color: bool | None = None,
) -> str:
    """Render rows in an aligned table."""

    if not rows:
        return ""

    color = supports_color() if use_color is None else use_color
    rendered_rows: list[list[str]] = []
    widths: list[int] = [len(header) for header, _ in columns]
    for row in rows:
        rendered = []
        for index, (header, key) in enumerate(columns):
            value = _truncate(_display_value(row.get(key, "")), max_width_for_header(header))
            rendered.append(value)
            widths[index] = max(widths[index], len(value))
        rendered_rows.append(rendered)

    header_cells = []
    for width, (header, _) in zip(widths, columns):
        padded = header.ljust(width)
        header_cells.append(_style(padded, ANSI_BOLD_CYAN, color=color))
    lines = ["  ".join(header_cells)]
    for rendered in rendered_rows:
        lines.append("  ".join(value.ljust(width) for value, width in zip(rendered, widths)))
    return "\n".join(lines)


def format_pretty_mapping(
    mapping: dict[str, Any],
    fields: ColumnSpec | None = None,
    *,
    use_color: bool | None = None,
) -> str:
    """Render a mapping as aligned key/value lines."""

    color = supports_color() if use_color is None else use_color
    items: list[tuple[str, Any]]
    if fields is None:
        items = [(key, value) for key, value in mapping.items()]
    else:
        items = [(label, mapping.get(key, "")) for label, key in fields]
    width = max((len(label) for label, _ in items), default=0)
    lines = []
    for label, value in items:
        rendered_label = _style(label.ljust(width), ANSI_BOLD, color=color)
        lines.append(f"{rendered_label}  {_display_value(value)}")
    return "\n".join(lines)


def print_rows(
    rows: Sequence[dict[str, Any]],
    columns: ColumnSpec,
    args: Any,
    *,
    empty_message: str = "",
    next_page_token: str | None = None,
) -> None:
    """Print a row-oriented payload in the requested output mode."""

    mode = determine_mode(args)
    if mode == "json":
        print(format_json(list(rows), next_page_token=next_page_token))
        return
    if mode == "plain":
        text = format_plain_rows(rows, columns)
        if text:
            print(text)
        return
    text = format_pretty_rows(rows, columns)
    if text:
        print(text)
    elif empty_message:
        print(empty_message)


def print_mapping(
    mapping: dict[str, Any],
    args: Any,
    *,
    fields: ColumnSpec | None = None,
) -> None:
    """Print a single mapping in the requested output mode."""

    mode = determine_mode(args)
    if mode == "json":
        print(format_json(mapping))
        return
    if mode == "plain":
        print(format_plain_mapping(mapping, fields))
        return
    print(format_pretty_mapping(mapping, fields))


def supports_color() -> bool:
    """Return whether ANSI color output should be used."""

    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


def max_width_for_header(header: str) -> int:
    """Return a reasonable max width for known columns."""

    if header == "SUBJECT":
        return 60
    if header == "FROM":
        return 36
    if header == "LABELS":
        return 20
    if header == "THREAD":
        return 20
    return 30


def _style(text: str, ansi: str, *, color: bool) -> str:
    if not color:
        return text
    return f"{ansi}{text}{ANSI_RESET}"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 1:
        return value[:limit]
    return f"{value[: limit - 1]}…"


def _display_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _plain_value(value: Any) -> str:
    return _display_value(value).replace("\t", " ").replace("\n", "\\n")


__all__ = [
    "ColumnSpec",
    "determine_mode",
    "format_json",
    "format_plain_mapping",
    "format_plain_rows",
    "format_pretty_mapping",
    "format_pretty_rows",
    "json_envelope",
    "print_mapping",
    "print_rows",
    "supports_color",
]

