"""Terminals for Windows: PowerShell in a new console window, typed into via
WriteConsoleInputW (no Qt). Importable on any OS; only works on Windows."""

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from devpipe.models.terminal import TerminalError, TerminalId

PWSH_SHELL = ("pwsh.exe", "-NoExit", "-NoLogo")  # PowerShell 7, preferred
WINDOWS_POWERSHELL_SHELL = ("powershell.exe", "-NoExit", "-NoLogo")  # 5.1, built into Windows
CONSOLE_INPUT_SCRIPT = Path(__file__).with_name("console_input.py")
SEND_TIMEOUT_SECONDS = 10
EXIT_CANNOT_ATTACH = 2  # same value as console_input.EXIT_CANNOT_ATTACH
# Not inherited by the shell: this variable lists the module folders of the
# PowerShell devpipe was started from, which may be another PowerShell version
# than the shell (e.g. 5.1 loading PowerShell 7's PSReadLine prompts "run software
# from this untrusted publisher?"). Without it, each PowerShell builds its own.
SHELL_ENV_EXCLUDED = ("PSModulePath",)

UNKNOWN_TERMINAL_MESSAGE = "unknown terminal"
TERMINAL_CLOSED_MESSAGE = "terminal is closed"
CANNOT_OPEN_MESSAGE = "cannot open terminal: {reason}"
CANNOT_SEND_MESSAGE = "cannot send text: {reason}"


class WindowsTerminals:
    """The Windows Terminals. A TerminalId's value is the shell's process id.

    Each window is a new console (CREATE_NEW_CONSOLE), so it is hosted by conhost
    or, when it is the default terminal, by Windows Terminal. Text is injected by
    a short-lived helper process (console_input.py) so this process never leaves
    its own console. Thread-safe.
    """

    def __init__(self, shell: tuple[str, ...] | None = None) -> None:
        """`shell` is the command line to start; None means default_shell()."""
        self._shell = shell if shell is not None else default_shell()
        self._processes: dict[TerminalId, subprocess.Popen[bytes]] = {}
        self._lock = threading.Lock()

    def open(self, cwd: Path) -> TerminalId:
        """See Terminals.open."""
        try:
            process = subprocess.Popen(
                list(self._shell),
                cwd=cwd,
                env=_shell_env(),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        except OSError as exc:
            raise TerminalError(CANNOT_OPEN_MESSAGE.format(reason=exc.strerror or exc)) from exc
        terminal = TerminalId(str(process.pid))
        with self._lock:
            self._processes[terminal] = process
        return terminal

    def send_text(self, terminal: TerminalId, text: str, enter: bool = True) -> None:
        """See Terminals.send_text."""
        if not self.is_open(terminal):
            raise TerminalError(TERMINAL_CLOSED_MESSAGE)
        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(CONSOLE_INPUT_SCRIPT), terminal.value, "1" if enter else "0"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=SEND_TIMEOUT_SECONDS,
                creationflags=subprocess.DETACHED_PROCESS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TerminalError(CANNOT_SEND_MESSAGE.format(reason=exc)) from exc
        if completed.returncode == EXIT_CANNOT_ATTACH:
            raise TerminalError(TERMINAL_CLOSED_MESSAGE)
        if completed.returncode != 0:
            reason = completed.stderr.decode("utf-8", "replace").strip() or (
                f"helper exited with code {completed.returncode}"
            )
            raise TerminalError(CANNOT_SEND_MESSAGE.format(reason=reason))

    def is_open(self, terminal: TerminalId) -> bool:
        """See Terminals.is_open. Raises TerminalError for an id it did not issue."""
        return self._process(terminal).poll() is None

    def close(self, terminal: TerminalId) -> None:
        """See Terminals.close."""
        process = self._process(terminal)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=SEND_TIMEOUT_SECONDS)
        with self._lock:
            self._processes.pop(terminal, None)

    def _process(self, terminal: TerminalId) -> subprocess.Popen[bytes]:
        with self._lock:
            process = self._processes.get(terminal)
        if process is None:
            raise TerminalError(UNKNOWN_TERMINAL_MESSAGE)
        return process


def default_shell() -> tuple[str, ...]:
    """PowerShell 7 when pwsh.exe is on PATH, otherwise Windows PowerShell 5.1."""
    return PWSH_SHELL if shutil.which(PWSH_SHELL[0]) else WINDOWS_POWERSHELL_SHELL


def _shell_env() -> dict[str, str]:
    """This process's environment minus SHELL_ENV_EXCLUDED (case-insensitive, as on Windows)."""
    excluded = {name.upper() for name in SHELL_ENV_EXCLUDED}
    return {name: value for name, value in os.environ.items() if name.upper() not in excluded}
