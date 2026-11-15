import pytest

from devpipe.models.terminal import TerminalError, TerminalId
from devpipe.services.terminal_service import (
    FOLDER_MISSING_MESSAGE,
    NO_TERMINAL_MESSAGE,
    TerminalService,
)


class FakeTerminals:
    """Issues TerminalId("1"), ("2"), ...; records sends and terminals brought to front;
    `closed` simulates the user closing a window."""

    def __init__(self):
        self.opened: list = []
        self.sent: list[tuple[TerminalId, str, bool]] = []
        self.fronted: list[TerminalId] = []
        self.closed: set[TerminalId] = set()

    def open(self, cwd):
        self.opened.append(cwd)
        return TerminalId(str(len(self.opened)))

    def send_text(self, terminal, text, enter=True):
        self.sent.append((terminal, text, enter))

    def is_open(self, terminal):
        return terminal not in self.closed

    def close(self, terminal):
        self.closed.add(terminal)

    def bring_to_front(self, terminal):
        self.fronted.append(terminal)


def test_open_opens_one_terminal_per_key(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)

    assert service.open("tab-a", tmp_path) is True
    assert service.open("tab-a", tmp_path) is False
    assert service.open("tab-b", tmp_path) is True

    assert fake.opened == [tmp_path, tmp_path]
    assert service.is_open("tab-a") and service.is_open("tab-b")


def test_open_rejects_missing_folder(tmp_path):
    fake = FakeTerminals()

    with pytest.raises(TerminalError, match=FOLDER_MISSING_MESSAGE):
        TerminalService(fake).open("tab-a", tmp_path / "missing")
    assert fake.opened == []


def test_send_goes_to_the_terminal_of_the_key(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    service.open("tab-a", tmp_path)
    service.open("tab-b", tmp_path)

    service.send("tab-b", "git status")
    service.send("tab-a", "y", enter=False)

    assert fake.sent == [(TerminalId("2"), "git status", True), (TerminalId("1"), "y", False)]


def test_send_without_terminal_raises(tmp_path):
    with pytest.raises(TerminalError, match=NO_TERMINAL_MESSAGE):
        TerminalService(FakeTerminals()).send("tab-a", "dir")


def test_terminal_closed_by_user_is_forgotten_and_can_be_reopened(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    service.open("tab-a", tmp_path)
    fake.closed.add(TerminalId("1"))

    assert service.is_open("tab-a") is False
    with pytest.raises(TerminalError, match=NO_TERMINAL_MESSAGE):
        service.send("tab-a", "dir")
    assert service.open("tab-a", tmp_path) is True
    assert fake.opened == [tmp_path, tmp_path]


def test_close_closes_and_forgets(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    service.open("tab-a", tmp_path)

    service.close("tab-a")
    service.close("tab-a")  # second call is a no-op

    assert fake.closed == {TerminalId("1")}
    assert service.is_open("tab-a") is False


def test_open_console_reuses_the_open_console_of_the_folder(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)

    assert service.open_console(tmp_path) == TerminalId("1")
    assert service.open_console(tmp_path) == TerminalId("1")

    assert fake.opened == [tmp_path]
    assert fake.fronted == [TerminalId("1")]
    assert service.open("tab-a", tmp_path) is True  # keyed terminals are unaffected


def test_open_console_matches_the_folder_not_its_spelling(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    (tmp_path / "a").mkdir()

    service.open_console(tmp_path)
    assert service.open_console(tmp_path / "a" / "..") == TerminalId("1")
    assert fake.fronted == [TerminalId("1")]


def test_open_console_opens_one_console_per_folder(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()

    assert service.open_console(a) == TerminalId("1")
    assert service.open_console(b) == TerminalId("2")
    assert service.open_console(a) == TerminalId("1")

    assert fake.opened == [a, b]
    assert fake.fronted == [TerminalId("1")]


def test_open_console_reopens_a_console_closed_by_the_user(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    service.open_console(tmp_path)
    fake.closed.add(TerminalId("1"))

    assert service.open_console(tmp_path) == TerminalId("2")
    assert service.open_console(tmp_path) == TerminalId("2")

    assert fake.opened == [tmp_path, tmp_path]
    assert fake.fronted == [TerminalId("2")]


def test_open_console_ignores_keyed_terminals(tmp_path):
    fake = FakeTerminals()
    service = TerminalService(fake)
    service.open("tab-a", tmp_path)

    assert service.open_console(tmp_path) == TerminalId("2")
    assert fake.fronted == []


def test_open_console_rejects_missing_folder(tmp_path):
    fake = FakeTerminals()

    with pytest.raises(TerminalError, match=FOLDER_MISSING_MESSAGE):
        TerminalService(fake).open_console(tmp_path / "missing")
    assert fake.opened == []
