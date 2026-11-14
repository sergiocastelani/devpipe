"""New worktree panel: groups of (source project, worktree parent) folders and Create."""

from functools import partial
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from devpipe.models.worktree import WorktreeRequest, WorktreeResult

SOURCE_LABEL_TEXT = "Source project folder"
PARENT_LABEL_TEXT = "Worktree parent folder"
SOURCE_PICKER_TOOLTIP = "Choose source project folder"
PARENT_PICKER_TOOLTIP = "Choose worktree parent folder"
PICKER_TEXT = "..."
ADD_TEXT = "+"
ADD_TOOLTIP = "Add worktree"
REMOVE_TEXT = "-"
REMOVE_TOOLTIP = "Remove worktree"
CREATE_TEXT = "Create"
GROUP_TITLE = "Worktree {n}"  # n is the 1-based display position
NO_START_DIRECTORY = ""  # lets the OS dialog pick its default folder
RETRY_TEXT = "Retry"
CREATED_DESCRIPTION = "Created: {target}"
FAILED_DESCRIPTION = "Failed: {error}"
ERROR_ENTRY = "{source} \u2192 {target}: {error}"  # "→"
ERROR_BOX_ACCESSIBLE_NAME = "Worktree errors"
ERROR_BOX_MAX_HEIGHT = 120  # px; keeps the groups visible above it
PROGRESS_ACCESSIBLE_NAME = "Creating worktrees"
SUCCESS_BORDER_COLOR = "#2e7d32"  # green
FAILURE_BORDER_COLOR = "#c62828"  # red
RESULT_STYLE = (
    "QGroupBox {{ border: 2px solid {color}; border-radius: 4px;"
    " margin-top: 1.5ex; padding-top: 1ex; }}"
    " QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 3px; }}"
)


class WorktreeGroup(QGroupBox):
    """One (source project folder, worktree parent folder) pair."""

    changed = Signal()  # an input's text changed, or the lock state changed
    remove_requested = Signal()  # '-' was clicked

    def __init__(self) -> None:
        super().__init__()
        self._locked = False
        self._removable = False

        self.source_input = QLineEdit()
        self.parent_input = QLineEdit()
        self.source_picker = self._tool_button(PICKER_TEXT, SOURCE_PICKER_TOOLTIP)
        self.parent_picker = self._tool_button(PICKER_TEXT, PARENT_PICKER_TOOLTIP)
        self.remove_button = self._tool_button(REMOVE_TEXT, REMOVE_TOOLTIP)
        source_label = QLabel(SOURCE_LABEL_TEXT)
        source_label.setBuddy(self.source_input)
        parent_label = QLabel(PARENT_LABEL_TEXT)
        parent_label.setBuddy(self.parent_input)

        header = QHBoxLayout()
        header.addStretch(1)
        header.addWidget(self.remove_button)

        rows = QGridLayout()
        rows.addWidget(source_label, 0, 0)
        rows.addWidget(self.source_input, 0, 1)
        rows.addWidget(self.source_picker, 0, 2)
        rows.addWidget(parent_label, 1, 0)
        rows.addWidget(self.parent_input, 1, 1)
        rows.addWidget(self.parent_picker, 1, 2)
        rows.setColumnStretch(1, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(rows)

        self.source_input.textChanged.connect(lambda _text: self.changed.emit())
        self.parent_input.textChanged.connect(lambda _text: self.changed.emit())
        self.source_picker.clicked.connect(
            lambda: self._choose_folder(self.source_input, SOURCE_PICKER_TOOLTIP)
        )  # drop the `checked` argument
        self.parent_picker.clicked.connect(
            lambda: self._choose_folder(self.parent_input, PARENT_PICKER_TOOLTIP)
        )  # drop the `checked` argument
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit())  # drop the `checked` argument
        self._refresh_controls()

    def set_locked(self, locked: bool) -> None:
        """Lock (read-only inputs, disabled pickers, no '-') or unlock the group; always emits `changed`."""
        self._locked = locked
        self._refresh_controls()
        self.changed.emit()

    def is_locked(self) -> bool:
        return self._locked

    def set_removable(self, removable: bool) -> None:
        """Whether '-' may be shown (the panel passes False for the first group)."""
        self._removable = removable
        self._refresh_controls()

    def is_filled(self) -> bool:
        """Both inputs are non-empty after trimming."""
        return bool(self.source_input.text().strip()) and bool(self.parent_input.text().strip())

    def request(self) -> WorktreeRequest:
        """The group's request from the trimmed inputs. Precondition: `is_filled()`."""
        return WorktreeRequest(
            Path(self.source_input.text().strip()),
            Path(self.parent_input.text().strip()),
        )

    def _choose_folder(self, line_edit: QLineEdit, caption: str) -> None:
        """Ask for a folder, starting in the input's folder when it exists; cancelling changes nothing."""
        current = line_edit.text().strip()
        start = current if current and Path(current).is_dir() else NO_START_DIRECTORY
        chosen = QFileDialog.getExistingDirectory(self, caption, start)
        if not chosen:
            return
        line_edit.setText(str(Path(chosen)))

    def _refresh_controls(self) -> None:
        self.source_input.setReadOnly(self._locked)
        self.parent_input.setReadOnly(self._locked)
        self.source_picker.setEnabled(not self._locked)
        self.parent_picker.setEnabled(not self._locked)
        self.remove_button.setVisible(self._removable and not self._locked)

    @staticmethod
    def _tool_button(text: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        return button


class NewWorktreePanel(QWidget):
    """Edits a list of worktree groups and asks to create the unlocked ones."""

    create_requested = Signal(list)  # list[WorktreeRequest] of editable_groups(), in order

    def __init__(self) -> None:
        super().__init__()
        self._busy = False
        self._groups: list[WorktreeGroup] = []

        groups_widget = QWidget()
        self._groups_layout = QVBoxLayout(groups_widget)
        self._groups_layout.addStretch(1)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(groups_widget)

        self.add_button = QPushButton(ADD_TEXT)
        self.add_button.setToolTip(ADD_TOOLTIP)
        self.add_button.setAccessibleName(ADD_TOOLTIP)
        self.create_button = QPushButton(CREATE_TEXT)
        self.error_box = QPlainTextEdit()
        self.error_box.setReadOnly(True)
        self.error_box.setAccessibleName(ERROR_BOX_ACCESSIBLE_NAME)
        self.error_box.setMaximumHeight(ERROR_BOX_MAX_HEIGHT)
        self.error_box.hide()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setAccessibleName(PROGRESS_ACCESSIBLE_NAME)
        self.progress_bar.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self._scroll, 1)
        layout.addWidget(self.add_button)
        layout.addWidget(self.error_box)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.create_button)

        self.add_button.clicked.connect(lambda: self._add_group())  # drop the `checked` argument
        self.create_button.clicked.connect(self._on_create_clicked)
        self.reset()

    def groups(self) -> list[WorktreeGroup]:
        """All groups in display order (a new list)."""
        return list(self._groups)

    def editable_groups(self) -> list[WorktreeGroup]:
        """Unlocked groups in display order."""
        return [group for group in self._groups if not group.is_locked()]

    def reset(self) -> None:
        """Start fresh: one empty unlocked group, no errors, "Create", not busy."""
        for group in self._groups:
            self._discard(group)
        self._groups.clear()
        self._add_group()
        self._show_errors([])
        self.create_button.setText(CREATE_TEXT)
        self.set_busy(False)

    def set_busy(self, busy: bool) -> None:
        """Disable (True) or restore (False) the groups, '+' and Create, and show the progress bar while busy."""
        self._busy = busy
        self._scroll.setEnabled(not busy)  # locked groups keep their own disabled pickers
        self.add_button.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        self._refresh_create_enabled()

    def show_results(self, results: list[WorktreeResult]) -> None:
        """Show `results[i]` on `editable_groups()[i]` (read once, at call time) and list the failures."""
        groups = self.editable_groups()
        if len(results) != len(groups):
            raise ValueError(f"expected {len(groups)} results, got {len(results)}")
        for group, result in zip(groups, results):
            self._show_group_result(group, result)
        failed = [result for result in results if not result.ok]
        self._show_errors(failed)
        if failed:
            self.create_button.setText(RETRY_TEXT)  # stays until reset()

    def _add_group(self) -> WorktreeGroup:
        group = WorktreeGroup()
        group.changed.connect(self._refresh_create_enabled)
        group.remove_requested.connect(partial(self._remove_group, group))
        self._groups_layout.insertWidget(len(self._groups), group)
        self._groups.append(group)
        self._renumber()
        self._refresh_create_enabled()
        return group

    def _remove_group(self, group: WorktreeGroup) -> None:
        if group not in self._groups or group is self._groups[0]:
            return  # the first group has no '-'
        self._groups.remove(group)
        self._discard(group)
        self._renumber()
        self._refresh_create_enabled()

    def _discard(self, group: WorktreeGroup) -> None:
        self._groups_layout.removeWidget(group)
        group.setParent(None)
        group.deleteLater()

    def _renumber(self) -> None:
        for number, group in enumerate(self._groups, start=1):
            group.setTitle(GROUP_TITLE.format(n=number))
            group.set_removable(number > 1)

    def _refresh_create_enabled(self) -> None:
        self.create_button.setEnabled(
            not self._busy and all(group.is_filled() for group in self.editable_groups())
        )

    def _show_group_result(self, group: WorktreeGroup, result: WorktreeResult) -> None:
        if result.ok:
            text = CREATED_DESCRIPTION.format(target=result.target)
            color = SUCCESS_BORDER_COLOR
            group.set_locked(True)
        else:
            text = FAILED_DESCRIPTION.format(error=result.error)
            color = FAILURE_BORDER_COLOR  # stays editable
        group.setStyleSheet(RESULT_STYLE.format(color=color))
        group.setToolTip(text)
        group.setAccessibleDescription(text)

    def _show_errors(self, failed: list[WorktreeResult]) -> None:
        entries = [
            ERROR_ENTRY.format(source=result.request.source, target=result.target, error=result.error)
            for result in failed
        ]
        self.error_box.setPlainText("\n".join(entries))  # replaces the previous call's errors
        self.error_box.setVisible(bool(entries))

    def _on_create_clicked(self) -> None:
        self.create_requested.emit([group.request() for group in self.editable_groups()])
