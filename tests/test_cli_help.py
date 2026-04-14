from __future__ import annotations

import pytest

from zog.cli import main


def test_root_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "auth" in output
    assert "mail" in output
    assert "calendar" in output
    assert "contacts" in output
    assert "workdrive" in output


def test_mail_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["mail", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "search" in output
    assert "get" in output
    assert "folders" in output


def test_calendar_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["calendar", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "list" in output
    assert "events" in output


def test_calendar_events_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["calendar", "events", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "list" in output
    assert "get" in output
    assert "create" in output


def test_contacts_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["contacts", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "list" in output
    assert "get" in output
    assert "create" in output


def test_workdrive_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["workdrive", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "files" in output
    assert "upload" in output


def test_workdrive_files_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["workdrive", "files", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "list" in output
    assert "get" in output


def test_auth_add_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["auth", "add", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "--device" in output
    assert "--self-client" in output
