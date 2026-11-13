from devpipe.views.start_tab import StartTab


def test_start_tab_has_the_two_buttons(qtbot):
    tab = StartTab()
    qtbot.addWidget(tab)
    assert tab.open_button.text() == "Open a pipeline"
    assert tab.create_button.text() == "Create a pipeline"
