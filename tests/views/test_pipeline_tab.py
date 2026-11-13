from PySide6.QtWidgets import QStackedWidget

from devpipe.views.pipeline_tab import PipelineTab
from devpipe.views.start_panel import StartPanel


def make_tab(qtbot):
    tab = PipelineTab()
    qtbot.addWidget(tab)
    return tab


def test_tab_shows_start_panel_in_a_stack(qtbot):
    tab = make_tab(qtbot)
    assert isinstance(tab.stack, QStackedWidget)
    assert tab.stack.count() == 1
    assert tab.stack.widget(0) is tab.start_panel
    assert tab.stack.currentWidget() is tab.start_panel
    assert isinstance(tab.start_panel, StartPanel)


def test_new_tab_identity(qtbot):
    tab = make_tab(qtbot)
    assert tab.title() == "New pipeline"
    assert tab.tooltip() == ""


def test_new_tab_start_panel_is_unsaved(qtbot):
    tab = make_tab(qtbot)
    panel = tab.start_panel
    assert not panel.save_button.isEnabled()
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()
