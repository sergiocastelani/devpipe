from devpipe.persistence.control_files import ControlFiles


def test_existing_file(tmp_path):
    file = tmp_path / "file"
    file.write_text("x", encoding="utf-8")
    assert ControlFiles().file_exists(file)


def test_missing_file(tmp_path):
    assert not ControlFiles().file_exists(tmp_path / "missing")


def test_a_folder_is_not_a_file(tmp_path):
    assert not ControlFiles().file_exists(tmp_path)
