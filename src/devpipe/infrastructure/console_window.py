"""Helper script (Windows only): find the window of another process's console and,
under Windows Terminal, select the console's tab.

Run as `python -I console_window.py <pid>`. Prints, in decimal, the handle that
GetConsoleWindow returns for the process's console: the conhost window or, under
Windows Terminal, its pseudo window (owned by the Windows Terminal window). It
is a separate process because AttachConsole first requires leaving the caller's
own console, which the devpipe process must keep.

Windows Terminal has no API to select a tab, but shows its tabs to UI Automation,
named by their console title. The helper gives the console a unique title for a
moment, selects the tab with that name and puts the old title back. Selecting
the tab is best effort: the handle is printed even when the tab is not found
(e.g. a profile that ignores the title the application sets).

Exit codes: 0 printed, 2 cannot attach (process gone or has no console),
1 the console has no window (message on stderr).
"""

import ctypes
import sys
import time
import uuid

EXIT_CANNOT_ATTACH = 2  # same value as console_input.EXIT_CANNOT_ATTACH
GA_ROOTOWNER = 3
WINDOWS_TERMINAL_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"
TITLE_BUFFER_SIZE = 4096
TAB_SEARCH_SECONDS = 2
TAB_SEARCH_INTERVAL_SECONDS = 0.05


def _root_window(user32: ctypes.WinDLL, window: int) -> int:
    return user32.GetAncestor(window, GA_ROOTOWNER) or window


def _is_windows_terminal(user32: ctypes.WinDLL, window: int) -> bool:
    name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(window, name, len(name))
    return name.value == WINDOWS_TERMINAL_CLASS


def _select_tab(window: int, title: str) -> None:
    """Select the tab named `title` in the Windows Terminal `window`, waiting up to
    TAB_SEARCH_SECONDS for the tab to show the title. No-op when it never does."""
    import comtypes.client

    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as uia

    automation = comtypes.client.CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
    root = automation.ElementFromHandle(window)
    condition = automation.CreateAndCondition(
        automation.CreatePropertyCondition(uia.UIA_ControlTypePropertyId, uia.UIA_TabItemControlTypeId),
        automation.CreatePropertyCondition(uia.UIA_NamePropertyId, title),
    )
    deadline = time.monotonic() + TAB_SEARCH_SECONDS
    while True:
        tab = root.FindFirst(uia.TreeScope_Descendants, condition)
        if tab:
            pattern = tab.GetCurrentPattern(uia.UIA_SelectionItemPatternId)
            pattern.QueryInterface(uia.IUIAutomationSelectionItemPattern).Select()
            return
        if time.monotonic() > deadline:
            return
        time.sleep(TAB_SEARCH_INTERVAL_SECONDS)


def _select_own_tab(kernel32: ctypes.WinDLL, window: int) -> None:
    """Select the attached console's tab in the Windows Terminal `window` (see module doc)."""
    old_title = ctypes.create_unicode_buffer(TITLE_BUFFER_SIZE)
    kernel32.GetConsoleTitleW(old_title, TITLE_BUFFER_SIZE)
    marker = f"devpipe-{uuid.uuid4().hex}"
    if not kernel32.SetConsoleTitleW(marker):
        return
    try:
        _select_tab(window, marker)
    except Exception:  # noqa: BLE001 - best effort: the window is still brought to front
        pass
    finally:
        kernel32.SetConsoleTitleW(old_title.value)


def main(argv: list[str]) -> int:
    pid = int(argv[1])
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32.GetConsoleWindow.restype = ctypes.c_void_p
    kernel32.GetConsoleTitleW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
    kernel32.SetConsoleTitleW.argtypes = [ctypes.c_wchar_p]
    user32.GetAncestor.restype = ctypes.c_void_p
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

    kernel32.FreeConsole()  # started detached, but be sure
    if not kernel32.AttachConsole(pid):
        return EXIT_CANNOT_ATTACH
    try:
        window = kernel32.GetConsoleWindow()
        if window:
            root = _root_window(user32, window)
            if _is_windows_terminal(user32, root):
                _select_own_tab(kernel32, root)
    finally:
        kernel32.FreeConsole()
    if not window:
        print("console has no window", file=sys.stderr)
        return 1
    print(window)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
