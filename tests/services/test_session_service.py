from pathlib import Path

import pytest

from devpipe.models.control_files import DevpipeStage, feature_folder
from devpipe.models.tab_state import TabState
from devpipe.persistence.config_repository import ConfigRepository
from devpipe.services.session_service import SessionService
from devpipe.services.window_state_service import WindowStateService


class FakeControlFiles:
    def __init__(self, existing: set[Path] | None = None, texts: dict[Path, str] | None = None) -> None:
        self.existing = existing or set()
        self.texts = texts or {}

    def file_exists(self, path: Path) -> bool:
        return path in self.existing or path in self.texts

    def read_text(self, path: Path) -> str | None:
        return self.texts.get(path)


def contract(*statuses: str) -> str:
    rows = "".join(f"| S{n:02} | step {n} | {status} | - |\n" for n, status in enumerate(statuses, 1))
    return "# Design Contract\n\n| Step | Title | Status | File |\n|------|-------|--------|------|\n" + rows


def make_service(tmp_path, control_files=None):
    config = ConfigRepository(tmp_path / "config.json")
    return SessionService(config, control_files or FakeControlFiles()), config


def test_start_folder_defaults_to_home(tmp_path):
    service, _ = make_service(tmp_path)
    assert service.start_folder() == Path.home()


def test_remember_folder_stores_parent(tmp_path):
    service, config = make_service(tmp_path)
    folder = tmp_path / "states"
    folder.mkdir()
    service.remember_folder(folder / "x.json")
    assert service.start_folder() == folder
    assert config.load().last_state_folder == folder


def test_start_folder_falls_back_to_home_when_folder_is_gone(tmp_path):
    service, _ = make_service(tmp_path)
    folder = tmp_path / "states"
    folder.mkdir()
    service.remember_folder(folder / "x.json")
    folder.rmdir()
    assert service.start_folder() == Path.home()


def test_start_folder_falls_back_to_home_when_value_is_a_file(tmp_path):
    service, _ = make_service(tmp_path)
    not_a_folder = tmp_path / "file"
    not_a_folder.write_text("", encoding="utf-8")
    service.remember_folder(not_a_folder / "x.json")
    assert service.start_folder() == Path.home()


def test_remember_folder_keeps_other_settings(tmp_path):
    service, config = make_service(tmp_path)
    WindowStateService(config).remember_maximized(True)
    service.remember_folder(tmp_path / "x.json")
    assert config.load().window_maximized is True


def test_session_defaults_to_empty(tmp_path):
    service, _ = make_service(tmp_path)
    assert service.open_files() == []
    assert service.active_file() is None


def test_remember_session_round_trips(tmp_path):
    service, _ = make_service(tmp_path)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    service.remember_session([a, b], b)
    assert service.open_files() == [a, b]
    assert service.active_file() == b


def test_remember_session_without_active(tmp_path):
    service, _ = make_service(tmp_path)
    service.remember_session([tmp_path / "a.json"], None)
    assert service.active_file() is None


def test_remember_session_stores_absolute_paths(tmp_path):
    service, _ = make_service(tmp_path)
    service.remember_session([Path("x.json")], Path("x.json"))
    assert service.open_files() == [Path("x.json").absolute()]
    assert service.active_file() == Path("x.json").absolute()


def test_remember_session_keeps_other_settings(tmp_path):
    service, config = make_service(tmp_path)
    WindowStateService(config).remember_maximized(True)
    service.remember_folder(tmp_path / "states" / "x.json")
    a = tmp_path / "a.json"
    service.remember_session([a], a)
    assert config.load().window_maximized is True
    assert config.load().last_state_folder == tmp_path / "states"


def test_remember_folder_keeps_session(tmp_path):
    service, _ = make_service(tmp_path)
    a = tmp_path / "a.json"
    service.remember_session([a], a)
    service.remember_folder(tmp_path / "states" / "x.json")
    assert service.open_files() == [a]
    assert service.active_file() == a


@pytest.mark.parametrize(
    ("files", "contract_text", "stage"),
    [
        (set(), None, DevpipeStage.CREATE),
        ({"plan.md"}, contract("approved"), DevpipeStage.CREATE),
        ({"feature-spec.md"}, None, DevpipeStage.PLAN),
        ({"feature-spec.md"}, contract("approved"), DevpipeStage.PLAN),
        ({"feature-spec.md", "plan.md"}, None, DevpipeStage.STEPS),
        ({"feature-spec.md", "plan.md"}, contract("approved", "draft"), DevpipeStage.STEPS),
        ({"feature-spec.md", "plan.md"}, contract("approved", "pending"), DevpipeStage.STEPS),
        ({"feature-spec.md", "plan.md"}, contract("approved", "approved"), DevpipeStage.IMPLEMENTATION),
        ({"feature-spec.md", "plan.md"}, "", DevpipeStage.IMPLEMENTATION),
    ],
)
def test_devpipe_stage_follows_control_files(tmp_path, files, contract_text, stage):
    main = Path("main")
    folder = feature_folder(main, "feat")
    texts = {} if contract_text is None else {folder / "design-contract.md": contract_text}
    service, _ = make_service(tmp_path, FakeControlFiles({folder / name for name in files}, texts))
    assert service.devpipe_stage(TabState("feat", worktrees=[main, Path("other")])) is stage


def test_devpipe_stage_reads_only_the_main_worktree(tmp_path):
    other = feature_folder(Path("other"), "feat")
    store = FakeControlFiles({other / "feature-spec.md", other / "plan.md"})
    service, _ = make_service(tmp_path, store)
    assert service.devpipe_stage(TabState("feat", worktrees=[Path("main"), Path("other")])) is DevpipeStage.CREATE


def test_devpipe_stage_is_create_without_worktree_or_feature_name(tmp_path):
    folder = feature_folder(Path("main"), "")
    service, _ = make_service(tmp_path, FakeControlFiles({folder / "feature-spec.md"}))
    assert service.devpipe_stage(TabState("feat")) is DevpipeStage.CREATE
    assert service.devpipe_stage(TabState("", worktrees=[Path("main")])) is DevpipeStage.CREATE
