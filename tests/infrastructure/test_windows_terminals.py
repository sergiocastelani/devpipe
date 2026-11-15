"""Integration tests: open real PowerShell windows (they flash on screen).

Opt-in: set DEVPIPE_TERMINAL_TESTS=1. Windows only.
"""

import os
import sys
import time

import pytest

from devpipe.models.terminal import TerminalError
from devpipe.infrastructure.windows_terminals import (
    TERMINAL_CLOSED_MESSAGE,
    WindowsTerminals,
    default_shell,
)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Windows only"),
    pytest.mark.skipif(
        os.environ.get("DEVPIPE_TERMINAL_TESTS") != "1",
        reason="opens real windows; set DEVPIPE_TERMINAL_TESTS=1",
    ),
]

TIMEOUT_SECONDS = 20
# No profile, and PSReadLine saves nothing: the typed test commands must not end up
# in the user's PowerShell history (ConsoleHost_history.txt).
TEST_SHELL = (
    *default_shell(), "-NoProfile",
    "-Command", "Set-PSReadLineOption -HistorySaveStyle SaveNothing",
)


def _wait_for_text(path, expected: str) -> str:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if path.exists():
            content = path.read_text(encoding="utf-8-sig").strip()
            if content == expected:
                return content
        time.sleep(0.2)
    return path.read_text(encoding="utf-8-sig").strip() if path.exists() else "<missing>"


@pytest.fixture
def terminals():
    terminals = WindowsTerminals(shell=TEST_SHELL)
    opened = []
    original_open = terminals.open

    def tracking_open(cwd):
        terminal = original_open(cwd)
        opened.append(terminal)
        return terminal

    terminals.open = tracking_open
    yield terminals
    for terminal in opened:
        terminals.close(terminal)


def test_runs_a_command_in_the_cwd(terminals, tmp_path):
    terminal = terminals.open(tmp_path)

    terminals.send_text(terminal, "(Get-Location).Path | Out-File -Encoding utf8 out.txt")

    assert _wait_for_text(tmp_path / "out.txt", str(tmp_path)) == str(tmp_path)


def test_answers_a_prompt(terminals, tmp_path):
    terminal = terminals.open(tmp_path)

    terminals.send_text(terminal, "$a = Read-Host 'name'; \"got $a\" | Out-File -Encoding utf8 out.txt")
    time.sleep(1)  # let Read-Host start waiting
    terminals.send_text(terminal, "Bob & Ünïcode {x}")

    assert _wait_for_text(tmp_path / "out.txt", "got Bob & Ünïcode {x}") == "got Bob & Ünïcode {x}"


def test_shell_does_not_inherit_the_module_path(terminals, tmp_path, monkeypatch):
    foreign = str(tmp_path / "foreign-modules")
    monkeypatch.setenv("PSModulePath", foreign)
    terminal = terminals.open(tmp_path)

    terminals.send_text(
        terminal,
        f"($env:PSModulePath -split ';' -contains '{foreign}') | Out-File -Encoding utf8 out.txt",
    )

    assert _wait_for_text(tmp_path / "out.txt", "False") == "False"


def test_send_to_closed_terminal_raises(terminals, tmp_path):
    terminal = terminals.open(tmp_path)
    terminals.send_text(terminal, "exit")
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while terminals.is_open(terminal) and time.monotonic() < deadline:
        time.sleep(0.2)

    assert terminals.is_open(terminal) is False
    with pytest.raises(TerminalError, match=TERMINAL_CLOSED_MESSAGE):
        terminals.send_text(terminal, "dir")
