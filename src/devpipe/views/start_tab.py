"""Content of a new tab: the two big start buttons.

What each button does is not decided yet.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class StartTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.open_button = self._big_button("Open a pipeline")
        self.create_button = self._big_button("Create a pipeline")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.addWidget(self.open_button)
        layout.addWidget(self.create_button)

    @staticmethod
    def _big_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumSize(320, 90)
        font = button.font()
        font.setPointSize(16)
        button.setFont(font)
        return button
