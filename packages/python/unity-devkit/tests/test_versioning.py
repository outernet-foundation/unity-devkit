from pathlib import Path

import pytest
from bashrun.bash import bash

from unity_devkit.versioning import stamp_build_version

PROJECT_SETTINGS = """PlayerSettings:
  m_ObjectHideFlags: 0
  productGUID: 26c3d6c0f3f2e6d4d9a5e3f4a1b2c3d4
  AndroidBundleVersionCode: 1
  AndroidTargetArchitectures: 3
  bundleVersion: 0.1.0
"""


def write_project(tmp_path: Path, project_settings: str) -> Path:
    project = tmp_path / "Project"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectSettings.asset").write_text(project_settings)
    return project


def init_tag_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, versions: list[str]) -> None:
    monkeypatch.chdir(tmp_path)
    bash("git init -q")
    bash("git config user.email test@example.com")
    bash("git config user.name test")
    bash("git commit --allow-empty -m init -q")
    for version in versions:
        bash(f"git tag app-v{version}")


def test_stamp_rewrites_both_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS)
    init_tag_repository(tmp_path, monkeypatch, ["0.2.3", "0.2.7"])

    stamped = stamp_build_version(project, "app", 42, release=False)

    assert stamped == "0.2.7-dev+42"
    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  AndroidBundleVersionCode: 42\n" in rewritten
    assert "  bundleVersion: 0.2.7-dev+42\n" in rewritten
    assert "0.1.0" not in rewritten


def test_stamp_release_drops_dev_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS)
    init_tag_repository(tmp_path, monkeypatch, ["0.2.7"])

    assert stamp_build_version(project, "app", 7, release=True) == "0.2.7+7"


def test_stamp_without_tags_falls_back_to_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS)
    init_tag_repository(tmp_path, monkeypatch, [])

    assert stamp_build_version(project, "app", 1, release=False) == "0.0.0-dev+1"


def test_stamp_missing_field_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS.replace("  AndroidBundleVersionCode: 1\n", ""))
    init_tag_repository(tmp_path, monkeypatch, ["0.2.7"])

    with pytest.raises(SystemExit, match="AndroidBundleVersionCode"):
        stamp_build_version(project, "app", 42, release=False)
