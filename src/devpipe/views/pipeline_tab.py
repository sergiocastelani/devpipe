"""One pipeline tab: a stack of panels, exactly one shown at a time.

New panels are added to `stack`; the start panel is always the first one.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from devpipe.views.start_panel import StartPanel

NEW_TAB_TITLE = "New pipeline"


class PipelineTab(QWidget):
    identity_changed = Signal()  # emitted after title() or tooltip() change

    def __init__(self) -> None:
        super().__init__()
        self.stack = QStackedWidget()
        self.start_panel = StartPanel()
        self.stack.addWidget(self.start_panel)
        self.stack.setCurrentWidget(self.start_panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def title(self) -> str:
        """Text of this tab in the tab bar."""
        return NEW_TAB_TITLE

    def tooltip(self) -> str:
        """Tooltip of this tab in the tab bar."""
        return ""
