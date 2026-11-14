"""The start panel's "Install/Update skills" flow: folder dialog, copy, result box."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from devpipe.persistence.skills_files import SkillsFiles
from devpipe.services.skills_service import SkillsService
from devpipe.views.start_panel import StartPanel


@pytest.fixture
def boxes(monkeypatch):
    """(kind, title, text) of every QMessageBox.warning / information call."""
    shown = []

    def recorder(kind):
        def fake(parent, title, text, *args):
            shown.append((kind, title, text))
            return QMessageBox.StandardButton.Ok

        return fake

    monkeypatch.setattr(QMessageBox, "warning", recorder("warning"))
    monkeypatch.setattr(QMessageBox, "information", recorder("information"))
    return shown


@pytest.fixture
def panel(qtbot, tmp_path):
    """A StartPanel whose skills folder holds skill-a/SKILL.md = "new"."""
    source = tmp_path / "ai-skills"
    (source / "skill-a").mkdir(parents=True)
    (source / "skill-a" / "SKILL.md").write_text("new", encoding="utf-8")
    panel = StartPanel(SkillsService(SkillsFiles(), source))
    qtbot.addWidget(panel)
    return panel


def answer_folder(monkeypatch, answer: str) -> list:
    """Fake QFileDialog.getExistingDirectory: records calls, returns `answer` ("" cancels)."""
    calls = []

    def fake(*args, **kwargs):
        calls.append(args)
        return answer

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake)
    return calls


def click_install(qtbot, panel) -> None:
    qtbot.mouseClick(panel.install_skills_button, Qt.MouseButton.LeftButton)


def test_chosen_folder_receives_the_skills_replacing_existing(qtbot, panel, monkeypatch, boxes, tmp_path):
    destination = tmp_path / "agent-skills"
    (destination / "skill-a").mkdir(parents=True)
    (destination / "skill-a" / "SKILL.md").write_text("old", encoding="utf-8")
    calls = answer_folder(monkeypatch, str(destination))
    click_install(qtbot, panel)
    assert len(calls) == 1
    assert (destination / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "new"
    assert [kind for kind, _title, _text in boxes] == ["information"]
    assert str(destination) in boxes[0][2]


def test_works_before_the_tab_is_saved_and_after(qtbot, panel, monkeypatch, boxes, tmp_path):
    answer_folder(monkeypatch, str(tmp_path / "dest"))
    panel.show_saved("x")
    click_install(qtbot, panel)
    assert (tmp_path / "dest" / "skill-a" / "SKILL.md").is_file()


def test_cancelled_dialog_copies_nothing(qtbot, panel, monkeypatch, boxes, tmp_path):
    answer_folder(monkeypatch, "")
    click_install(qtbot, panel)
    assert boxes == []


def test_failed_copy_shows_a_warning(qtbot, panel, monkeypatch, boxes, tmp_path):
    not_a_folder = tmp_path / "file.txt"
    not_a_folder.write_text("", encoding="utf-8")
    answer_folder(monkeypatch, str(not_a_folder))
    click_install(qtbot, panel)
    assert [(kind, title) for kind, title, _text in boxes] == [("warning", "Cannot install skills")]
