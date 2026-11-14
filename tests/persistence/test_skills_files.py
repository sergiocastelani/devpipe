import pytest

from devpipe.models.skills import SkillsInstallError
from devpipe.persistence.skills_files import SkillsFiles


@pytest.fixture
def source(tmp_path):
    source = tmp_path / "ai-skills"
    (source / "skill-a" / "refs").mkdir(parents=True)
    (source / "skill-a" / "SKILL.md").write_text("a", encoding="utf-8")
    (source / "skill-a" / "refs" / "x.md").write_text("x", encoding="utf-8")
    (source / "README.md").write_text("readme", encoding="utf-8")
    return source


def test_copies_all_files_and_folders_into_a_new_destination(tmp_path, source):
    destination = tmp_path / "dest" / "skills"
    SkillsFiles().copy_contents(source, destination)
    assert (destination / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "a"
    assert (destination / "skill-a" / "refs" / "x.md").read_text(encoding="utf-8") == "x"
    assert (destination / "README.md").read_text(encoding="utf-8") == "readme"
    assert not (destination / "ai-skills").exists()


def test_replaces_same_named_entries_and_keeps_others(tmp_path, source):
    destination = tmp_path / "dest"
    (destination / "skill-a").mkdir(parents=True)
    (destination / "skill-a" / "SKILL.md").write_text("old", encoding="utf-8")
    (destination / "skill-a" / "stale.md").write_text("stale", encoding="utf-8")
    (destination / "README.md").write_text("old", encoding="utf-8")
    (destination / "other-skill").mkdir()
    SkillsFiles().copy_contents(source, destination)
    assert (destination / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "a"
    assert not (destination / "skill-a" / "stale.md").exists()
    assert (destination / "README.md").read_text(encoding="utf-8") == "readme"
    assert (destination / "other-skill").is_dir()


def test_replaces_a_file_with_a_folder_of_the_same_name(tmp_path, source):
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "skill-a").write_text("a file", encoding="utf-8")
    SkillsFiles().copy_contents(source, destination)
    assert (destination / "skill-a" / "SKILL.md").is_file()


def test_skips_pycache(tmp_path, source):
    (source / "__pycache__").mkdir()
    (source / "skill-a" / "__pycache__").mkdir()
    destination = tmp_path / "dest"
    SkillsFiles().copy_contents(source, destination)
    assert not (destination / "__pycache__").exists()
    assert not (destination / "skill-a" / "__pycache__").exists()


def test_missing_source_raises(tmp_path):
    with pytest.raises(SkillsInstallError) as error:
        SkillsFiles().copy_contents(tmp_path / "missing", tmp_path / "dest")
    assert error.value.path == tmp_path / "missing"


@pytest.mark.parametrize("inside", ["", "skill-a"])
def test_destination_inside_source_raises_and_changes_nothing(source, inside):
    with pytest.raises(SkillsInstallError):
        SkillsFiles().copy_contents(source, source / inside)
    assert (source / "skill-a" / "SKILL.md").read_text(encoding="utf-8") == "a"


def test_os_error_becomes_skills_install_error(tmp_path, source):
    destination = tmp_path / "a-file"
    destination.write_text("", encoding="utf-8")
    with pytest.raises(SkillsInstallError) as error:
        SkillsFiles().copy_contents(source, destination)
    assert error.value.path == destination
