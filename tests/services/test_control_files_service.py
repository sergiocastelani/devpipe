from pathlib import Path

from devpipe.services.control_files_service import ControlFilesService

SPEC = Path("wt") / ".devpipe" / "feat" / "feature-spec.md"


class FakeStore:
    def __init__(self, existing: set[Path]) -> None:
        self.existing = existing
        self.checked: list[Path] = []

    def file_exists(self, path: Path) -> bool:
        self.checked.append(path)
        return path in self.existing


def test_checks_the_feature_spec_in_the_control_folder():
    store = FakeStore({SPEC})
    assert ControlFilesService(store).feature_spec_exists(Path("wt"), "feat")
    assert store.checked == [SPEC]


def test_missing_feature_spec():
    assert not ControlFilesService(FakeStore(set())).feature_spec_exists(Path("wt"), "feat")


def test_empty_feature_name_is_never_found():
    store = FakeStore({Path("wt") / ".devpipe" / "feature-spec.md"})
    assert not ControlFilesService(store).feature_spec_exists(Path("wt"), "")
    assert store.checked == []
