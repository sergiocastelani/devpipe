"""Helper script (Windows only): type text into another process's console.

Run as `python -I console_input.py <pid> <enter 0|1> [<soft_newlines 0|1>]` with
the text as UTF-8 on stdin. With soft_newlines 1, each "\\n" in the text is typed
as Ctrl+J (a new line in the input, not a submit); the Enter added by `enter` is
always a plain Enter. It is a separate process because AttachConsole first
requires leaving the caller's own console, which the devpipe process must keep.

Exit codes: 0 written, 2 cannot attach (process gone or has no console),
1 any other failure (message on stderr).
"""

import ctypes
import sys
from ctypes import wintypes

KEY_EVENT = 0x0001
SHIFT_PRESSED = 0x0010
LEFT_CTRL_PRESSED = 0x0008
VK_RETURN = 0x0D
VK_J = 0x4A
VK_PACKET = 0xE7  # "a Unicode character with no key of its own"
GENERIC_READ_WRITE = 0x80000000 | 0x40000000
FILE_SHARE_READ_WRITE = 0x1 | 0x2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
EXIT_CANNOT_ATTACH = 2


class _Char(ctypes.Union):
    _fields_ = [("UnicodeChar", wintypes.WCHAR), ("AsciiChar", wintypes.CHAR)]


class _KeyEventRecord(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", _Char),
        ("dwControlKeyState", wintypes.DWORD),
    ]


class _Event(ctypes.Union):
    # KEY_EVENT_RECORD is the largest member of the real union, so it sets the size.
    _fields_ = [("KeyEvent", _KeyEventRecord)]


class _InputRecord(ctypes.Structure):
    _fields_ = [("EventType", wintypes.WORD), ("Event", _Event)]


def _key_records(text: str, user32: ctypes.WinDLL, soft_newlines: bool = False) -> list[_InputRecord]:
    """A key-down and a key-up record per character; "\\n" becomes Enter, or
    Ctrl+J when `soft_newlines`.

    Why Ctrl+J and not Shift+Enter: console programs that read characters, such
    as Node ones (Claude Code), get Shift+Enter as "\\r", the same as Enter, so it
    submits. Ctrl+J carries a line feed ("\\n"), their "new line" key.

    Virtual key codes matter: PowerShell's line editor (PSReadLine) reads keys,
    not just characters. Characters the keyboard layout can only type with
    Ctrl/Alt (AltGr) or not at all are sent as VK_PACKET without modifiers.
    """
    records: list[_InputRecord] = []
    for char in text.replace("\r\n", "\n"):
        if char == "\n" and soft_newlines:
            vk, state = VK_J, LEFT_CTRL_PRESSED  # char stays "\n"
        elif char == "\n":
            char, vk, state = "\r", VK_RETURN, 0
        else:
            scan = user32.VkKeyScanW(char)
            shift_bits = (scan >> 8) & 0xFF
            if scan == -1 or shift_bits & ~0x01:
                vk, state = VK_PACKET, 0
            else:
                vk, state = scan & 0xFF, SHIFT_PRESSED if shift_bits & 0x01 else 0
        scan_code = user32.MapVirtualKeyW(vk, 0) if vk != VK_PACKET else 0
        for down in (True, False):
            record = _InputRecord()
            record.EventType = KEY_EVENT
            key = record.Event.KeyEvent
            key.bKeyDown = down
            key.wRepeatCount = 1
            key.wVirtualKeyCode = vk
            key.wVirtualScanCode = scan_code
            key.uChar.UnicodeChar = char
            key.dwControlKeyState = state
            records.append(record)
    return records


def main(argv: list[str]) -> int:
    pid, enter = int(argv[1]), argv[2] == "1"
    soft_newlines = len(argv) > 3 and argv[3] == "1"
    text = sys.stdin.buffer.read().decode("utf-8")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.WriteConsoleInputW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_InputRecord), wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.VkKeyScanW.restype = ctypes.c_short
    user32.VkKeyScanW.argtypes = [wintypes.WCHAR]

    kernel32.FreeConsole()  # started detached, but be sure
    if not kernel32.AttachConsole(pid):
        return EXIT_CANNOT_ATTACH
    handle = kernel32.CreateFileW(
        "CONIN$", GENERIC_READ_WRITE, FILE_SHARE_READ_WRITE, None, OPEN_EXISTING, 0, None
    )
    if handle in (None, INVALID_HANDLE_VALUE):
        print(f"cannot open console input (error {ctypes.get_last_error()})", file=sys.stderr)
        return 1
    try:
        records = _key_records(text, user32, soft_newlines)
        if enter:
            records += _key_records("\n", user32)  # always a plain Enter: submits
        array = (_InputRecord * len(records))(*records)
        base = ctypes.addressof(array)
        record_size = ctypes.sizeof(_InputRecord)
        written = wintypes.DWORD(0)
        offset = 0
        while offset < len(records):
            ok = kernel32.WriteConsoleInputW(
                handle,
                ctypes.cast(base + offset * record_size, ctypes.POINTER(_InputRecord)),
                len(records) - offset,
                ctypes.byref(written),
            )
            if not ok or written.value == 0:
                print(f"write failed (error {ctypes.get_last_error()})", file=sys.stderr)
                return 1
            offset += written.value
        return 0
    finally:
        kernel32.CloseHandle(handle)
        kernel32.FreeConsole()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
