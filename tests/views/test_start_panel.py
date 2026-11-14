from PySide6.QtCore import Qt

from devpipe.views.start_panel import StartPanel


def make_panel(qtbot):
    panel = StartPanel()
    qtbot.addWidget(panel)
    return panel


def test_new_panel_is_unsaved_and_empty(qtbot):
    panel = make_panel(qtbot)
    assert panel.name_input.text() == ""
    assert panel.name_input.isEnabled()
    assert panel.slug_label.text() == ""
    assert not panel.save_button.isEnabled()
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()
    assert panel.save_button.text() == "Save"
    assert panel.open_button.text() == "Open a pipeline"
    assert panel.create_button.text() == "Create a pipeline"


def test_typing_a_name_previews_slug_and_enables_only_save(qtbot):
    panel = make_panel(qtbot)
    qtbot.keyClicks(panel.name_input, "New Feature")
    assert panel.slug_label.text() == "new-feature"
    assert panel.save_button.isEnabled()
    assert not panel.open_button.isEnabled()
    assert not panel.create_button.isEnabled()


def test_accented_name_previews_slug(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("Nová Feature_X")
    assert panel.slug_label.text() == "nova-feature-x"
    assert panel.save_button.isEnabled()


def test_name_without_slug_keeps_save_disabled(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("!!!")
    assert panel.slug_label.text() == ""
    assert not panel.save_button.isEnabled()


def test_clearing_the_name_disables_save(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("abc")
    assert panel.save_button.isEnabled()
    panel.name_input.clear()
    assert not panel.save_button.isEnabled()
    assert panel.slug_label.text() == ""


def test_save_click_emits_slug(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("Nová Feature_X")
    with qtbot.waitSignal(panel.save_requested) as blocker:
        qtbot.mouseClick(panel.save_button, Qt.MouseButton.LeftButton)
    assert blocker.args == ["nova-feature-x"]
    assert panel.name_input.isEnabled()


def test_show_saved_switches_to_saved_mode(qtbot):
    panel = make_panel(qtbot)
    panel.name_input.setText("New Feature")
    panel.show_saved("new-feature")
    assert panel.name_input.text() == "new-feature"
    assert not panel.name_input.isEnabled()
    assert panel.slug_label.text() == "new-feature"
    assert not panel.save_button.isEnabled()
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
    assert not panel.name_input.isHidden()
    assert not panel.save_button.isHidden()


def test_saved_mode_keeps_save_disabled(qtbot):
    panel = make_panel(qtbot)
    panel.show_saved("x")
    panel.name_input.setText("other")
    assert not panel.save_button.isEnabled()
    panel.show_saved("x")
    assert not panel.save_button.isEnabled()
    assert panel.open_button.isEnabled()
    assert panel.create_button.isEnabled()
