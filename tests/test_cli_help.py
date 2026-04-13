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


def test_mail_help_exits_successfully(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["mail", "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "search" in output
    assert "get" in output
    assert "folders" in output

