from devpipe.views.main_window import MainWindow
from devpipe.views.start_tab import StartTab


def test_main_window_opens_with_a_start_tab(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.tabs.count() == 1
    assert isinstance(window.tabs.widget(0), StartTab)


def test_start_tab_has_the_two_buttons(qtbot):
    tab = StartTab()
    qtbot.addWidget(tab)
    assert tab.open_button.text() == "Open a pipeline"
    assert tab.create_button.text() == "Create a pipeline"
