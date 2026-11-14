"""First panel of a pipeline tab: feature name, Save, and the start buttons, and,
at the bottom, the tab's worktree folders (double-click opens one in the file explorer).

"Create new worktree" asks the tab to open the New worktree panel. What "Open a pipeline" and "Create a pipeline" do is not decided yet.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from devpipe.models.feature_name import normalize_feature_name

NAME_PLACEHOLDER = "Feature name"
SAVE_TEXT = "Save"
NEW_WORKTREE_TEXT = "Create new worktree"
OPEN_TEXT = "Open a pipeline"
CREATE_TEXT = "Create a pipeline"
BIG_BUTTON_MIN_WIDTH = 320
BIG_BUTTON_MIN_HEIGHT = 90
BIG_BUTTON_POINT_SIZE = 16
BIG_BUTTON_SPACING = 24
SLUG_FONT_POINT_DELTA = -1
WORKTREES_LABEL_TEXT = "Worktrees"
FOLDER_NOT_FOUND_TITLE = "Folder not found"
FOLDER_NOT_FOUND_TEXT = "Folder not found: {path}"
CANNOT_OPEN_FOLDER_TITLE = "Cannot open folder"
CANNOT_OPEN_FOLDER_TEXT = "Cannot open folder: {path}"


class StartPanel(QWidget):
    save_requested = Signal(str)  # emitted with the current slug when Save is clicked
    new_worktree_requested = Signal()  # emitted when "Create new worktree" is clicked

    def __init__(self) -> None:
        super().__init__()
        self._saved = False
        self._slug = ""

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(NAME_PLACEHOLDER)
        self.save_button = QPushButton(SAVE_TEXT)
        self.slug_label = QLabel()
        font = self.slug_label.font()
        font.setPointSize(font.pointSize() + SLUG_FONT_POINT_DELTA)
        self.slug_label.setFont(font)
        self.new_worktree_button = self._big_button(NEW_WORKTREE_TEXT)
        self.open_button = self._big_button(OPEN_TEXT)
        self.create_button = self._big_button(CREATE_TEXT)
        self.new_worktree_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.create_button.setEnabled(False)
        self.worktrees_label = QLabel(WORKTREES_LABEL_TEXT)
        self.worktrees_list = QListWidget()
        self.worktrees_list.setAccessibleName(WORKTREES_LABEL_TEXT)
        self.worktrees_label.setBuddy(self.worktrees_list)

        name_row = QHBoxLayout()
        name_row.addWidget(self.name_input, 1)
        name_row.addWidget(self.save_button, 0)

        buttons = QVBoxLayout()
        buttons.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons.setSpacing(BIG_BUTTON_SPACING)
        buttons.addWidget(self.new_worktree_button)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.create_button)

        layout = QVBoxLayout(self)
        layout.addLayout(name_row)
        layout.addWidget(self.slug_label)
        layout.addLayout(buttons, 1)
        layout.addWidget(self.worktrees_label)
        layout.addWidget(self.worktrees_list)

        self.name_input.textChanged.connect(self._on_name_changed)
        self.save_button.clicked.connect(self._on_save_clicked)
        self.new_worktree_button.clicked.connect(lambda: self.new_worktree_requested.emit())
        self.worktrees_list.itemDoubleClicked.connect(self._on_worktree_double_clicked)
        self._refresh_save_enabled()
        self.show_worktrees([])

    def show_saved(self, feature_name: str) -> None:
        """Switch to saved mode (one-way): name fixed, the big buttons enabled."""
        self._saved = True
        self.name_input.setText(feature_name)
        self.name_input.setEnabled(False)
        self.save_button.setEnabled(False)
        self.new_worktree_button.setEnabled(True)
        self.open_button.setEnabled(True)
        self.create_button.setEnabled(True)

    def show_worktrees(self, paths: list[Path]) -> None:
        """Replace the worktree list with `paths` (shown as str(path)), in order.

        The label and the list are shown when `paths` is non-empty, hidden otherwise.
        May be called any number of times; `paths` is not kept or modified.
        """
        self.worktrees_list.clear()
        for path in paths:
            self.worktrees_list.addItem(str(path))
        visible = bool(paths)
        self.worktrees_label.setVisible(visible)
        self.worktrees_list.setVisible(visible)

    def _on_worktree_double_clicked(self, item: QListWidgetItem) -> None:
        """Open the entry's folder in the file explorer; warn when it does not exist or the OS cannot open it."""
        path = Path(item.text())
        if not path.is_dir():
            QMessageBox.warning(self, FOLDER_NOT_FOUND_TITLE, FOLDER_NOT_FOUND_TEXT.format(path=path))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, CANNOT_OPEN_FOLDER_TITLE, CANNOT_OPEN_FOLDER_TEXT.format(path=path))

    def _on_name_changed(self, text: str) -> None:
        self._slug = normalize_feature_name(text)
        self.slug_label.setText(self._slug)
        self._refresh_save_enabled()

    def _on_save_clicked(self) -> None:
        if self._slug:
            self.save_requested.emit(self._slug)

    def _refresh_save_enabled(self) -> None:
        self.save_button.setEnabled(not self._saved and bool(self._slug))

    @staticmethod
    def _big_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumSize(BIG_BUTTON_MIN_WIDTH, BIG_BUTTON_MIN_HEIGHT)
        font = button.font()
        font.setPointSize(BIG_BUTTON_POINT_SIZE)
        button.setFont(font)
        return button
