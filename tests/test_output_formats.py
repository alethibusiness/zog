from __future__ import annotations

import json

from zog.output import format_json, format_plain_rows, format_pretty_rows


def test_json_output_envelope():
    payload = json.loads(format_json([{"id": "1"}]))
    assert payload["status"] == "ok"
    assert payload["data"] == [{"id": "1"}]


def test_plain_output_is_tsv_without_header():
    text = format_plain_rows(
        [{"id": "1", "subject": "Hello", "labels": "Inbox"}],
        [("ID", "id"), ("SUBJECT", "subject"), ("LABELS", "labels")],
    )
    assert text == "1\tHello\tInbox"


def test_pretty_output_contains_headers_and_values():
    text = format_pretty_rows(
        [{"id": "1", "subject": "Hello", "labels": "Inbox"}],
        [("ID", "id"), ("SUBJECT", "subject"), ("LABELS", "labels")],
        use_color=False,
    )
    assert "ID" in text
    assert "SUBJECT" in text
    assert "Hello" in text

