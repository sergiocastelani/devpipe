from devpipe.persistence.control_files import ControlFiles


def test_existing_file(tmp_path):
    file = tmp_path / "file"
    file.write_text("x", encoding="utf-8")
    assert ControlFiles().file_exists(file)


def test_missing_file(tmp_path):
    assert not ControlFiles().file_exists(tmp_path / "missing")


def test_a_folder_is_not_a_file(tmp_path):
    assert not ControlFiles().file_exists(tmp_path)


def test_read_text_returns_the_content(tmp_path):
    file = tmp_path / "design-contract.md"
    file.write_text("| S01 | ação | draft |", encoding="utf-8")
    assert ControlFiles().read_text(file) == "| S01 | ação | draft |"


def test_read_text_of_missing_file_is_none(tmp_path):
    assert ControlFiles().read_text(tmp_path / "missing") is None


def test_read_text_of_a_folder_is_none(tmp_path):
    assert ControlFiles().read_text(tmp_path) is None


def test_read_text_of_non_utf8_file_is_none(tmp_path):
    file = tmp_path / "bad.md"
    file.write_bytes(b"\xff\xfe\xfa")
    assert ControlFiles().read_text(file) is None
