from pathlib import Path

from devpipe.services.skills_service import SkillsService


class RecordingStore:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def copy_contents(self, source: Path, destination: Path) -> None:
        self.calls.append((source, destination))


def test_install_copies_the_skills_folder_into_the_destination():
    store = RecordingStore()
    SkillsService(store, Path("skills")).install(Path("dest"))
    assert store.calls == [(Path("skills"), Path("dest"))]
