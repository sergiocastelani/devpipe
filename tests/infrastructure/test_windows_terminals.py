"""Integration tests: open real PowerShell windows (they flash on screen).

Opt-in: set DEVPIPE_TERMINAL_TESTS=1. Windows only.
"""

import os
import sys
import time

import pytest

from devpipe.models.terminal import TerminalError
from devpipe.infrastructure.windows_terminals import (
    CONSOLE_WINDOW_SCRIPT,
    GA_ROOTOWNER,
    TERMINAL_CLOSED_MESSAGE,
    WindowsTerminals,
    _run_helper,
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
SW_MINIMIZE = 6
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


def _user32():
    import ctypes

    user32 = ctypes.WinDLL("user32")
    user32.GetAncestor.restype = ctypes.c_void_p
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.IsIconic.argtypes = [ctypes.c_void_p]
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return user32


def _console_root_window(terminal) -> int:
    output = _run_helper(CONSOLE_WINDOW_SCRIPT, [terminal.value], b"", "{reason}")
    return _user32().GetAncestor(int(output), GA_ROOTOWNER)


def test_bring_to_front_restores_and_activates_the_window(terminals, tmp_path):
    user32 = _user32()
    terminal = terminals.open(tmp_path)
    time.sleep(2)  # let the window appear
    window = _console_root_window(terminal)
    user32.ShowWindow(window, SW_MINIMIZE)
    assert user32.IsIconic(window)

    terminals.bring_to_front(terminal)

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while user32.GetAncestor(user32.GetForegroundWindow(), GA_ROOTOWNER) != window:
        if time.monotonic() > deadline:
            break
        time.sleep(0.2)
    assert not user32.IsIconic(window)
    assert user32.GetAncestor(user32.GetForegroundWindow(), GA_ROOTOWNER) == window


def _selected_tab_name(window: int) -> str | None:
    import comtypes.client

    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as uia

    automation = comtypes.client.CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
    condition = automation.CreateAndCondition(
        automation.CreatePropertyCondition(uia.UIA_ControlTypePropertyId, uia.UIA_TabItemControlTypeId),
        automation.CreatePropertyCondition(uia.UIA_SelectionItemIsSelectedPropertyId, True),
    )
    tab = automation.ElementFromHandle(window).FindFirst(uia.TreeScope_Descendants, condition)
    return tab.CurrentName if tab else None


def test_bring_to_front_selects_the_windows_terminal_tab(terminals, tmp_path):
    first = terminals.open(tmp_path)
    terminals.send_text(first, "$Host.UI.RawUI.WindowTitle = 'devpipe-test-first'")
    second = terminals.open(tmp_path)
    time.sleep(2)  # let both appear; the second one is selected
    window = _console_root_window(first)
    if _console_root_window(second) != window:
        pytest.skip("consoles are not tabs of one Windows Terminal window")
    assert _selected_tab_name(window) != "devpipe-test-first"

    terminals.bring_to_front(first)

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while _selected_tab_name(window) != "devpipe-test-first" and time.monotonic() < deadline:
        time.sleep(0.2)
    assert _selected_tab_name(window) == "devpipe-test-first"

def test_bring_to_front_of_closed_terminal_raises(terminals, tmp_path):
    terminal = terminals.open(tmp_path)
    terminals.send_text(terminal, "exit")
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while terminals.is_open(terminal) and time.monotonic() < deadline:
        time.sleep(0.2)

    with pytest.raises(TerminalError, match=TERMINAL_CLOSED_MESSAGE):
        terminals.bring_to_front(terminal)
