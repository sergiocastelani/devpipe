"""Devpipe plan panel: shown once the feature's control folder exists. Empty for now."""

from PySide6.QtWidgets import QVBoxLayout, QWidget


class DevpipePlanPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addStretch()
