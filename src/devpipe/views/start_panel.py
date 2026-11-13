"""First panel of a pipeline tab: feature name, Save, and the start buttons.

What "Open a pipeline" and "Create a pipeline" do is not decided yet.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from devpipe.models.feature_name import normalize_feature_name

NAME_PLACEHOLDER = "Feature name"
SAVE_TEXT = "Save"
OPEN_TEXT = "Open a pipeline"
CREATE_TEXT = "Create a pipeline"
BIG_BUTTON_MIN_WIDTH = 320
BIG_BUTTON_MIN_HEIGHT = 90
BIG_BUTTON_POINT_SIZE = 16
BIG_BUTTON_SPACING = 24
SLUG_FONT_POINT_DELTA = -1


class StartPanel(QWidget):
    save_requested = Signal(str)  # emitted with the current slug when Save is clicked

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
        self.open_button = self._big_button(OPEN_TEXT)
        self.create_button = self._big_button(CREATE_TEXT)
        self.open_button.setEnabled(False)
        self.create_button.setEnabled(False)

        name_row = QHBoxLayout()
        name_row.addWidget(self.name_input, 1)
        name_row.addWidget(self.save_button, 0)

        buttons = QVBoxLayout()
        buttons.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons.setSpacing(BIG_BUTTON_SPACING)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.create_button)

        layout = QVBoxLayout(self)
        layout.addLayout(name_row)
        layout.addWidget(self.slug_label)
        layout.addLayout(buttons, 1)

        self.name_input.textChanged.connect(self._on_name_changed)
        self.save_button.clicked.connect(self._on_save_clicked)
        self._refresh_save_enabled()

    def show_saved(self, feature_name: str) -> None:
        """Switch to saved mode (one-way): name fixed, Open and Create enabled."""
        self._saved = True
        self.name_input.setText(feature_name)
        self.name_input.setEnabled(False)
        self.save_button.setEnabled(False)
        self.open_button.setEnabled(True)
        self.create_button.setEnabled(True)

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
