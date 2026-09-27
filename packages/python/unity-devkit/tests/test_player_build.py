import json
from pathlib import Path

import pytest

from unity_devkit import player_build

PROJECT_SETTINGS = """PlayerSettings:
  m_ObjectHideFlags: 0
  productGUID: 26c3d6c0f3f2e6d4d9a5e3f4a1b2c3d4
  AndroidBundleVersionCode: 1
  AndroidTargetArchitectures: 3
  bundleVersion: 0.1.0
"""


def write_repository(tmp_path: Path, project_settings: str) -> Path:
    project = tmp_path / "apps" / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectSettings.asset").write_text(project_settings)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (tmp_path / "unity-devkit.json").write_text(
        json.dumps({"tool": {"path": "apps/Tool", "builds": ["AndroidMobile"]}})
    )
    return project


def fake_unity_build_producing(project_path: Path, extra_flags: str, *, nographics: bool, env: dict[str, str]) -> Path:
    build_directory = project_path / "Build"
    build_directory.mkdir(exist_ok=True)
    (build_directory / "Tool.apk").write_bytes(b"apk")
    return Path("unused-editor.log")


def fake_unity_build_silent(project_path: Path, extra_flags: str, *, nographics: bool, env: dict[str, str]) -> Path:
    return Path("unused-editor.log")


def test_build_player_stamps_version_and_returns_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_repository(tmp_path, PROJECT_SETTINGS)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    produced = player_build.build_player("tool", "AndroidMobile", version="0.2.7-dev+42", run_number=42)

    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  AndroidBundleVersionCode: 42\n" in rewritten
    assert "  bundleVersion: 0.2.7-dev+42\n" in rewritten
    assert "0.1.0" not in rewritten
    assert produced == [project / "Build" / "Tool.apk"]


def test_build_player_treats_the_version_string_as_opaque(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_repository(tmp_path, PROJECT_SETTINGS)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    player_build.build_player("tool", "AndroidMobile", version="release-2026-09-27", run_number=7)

    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  bundleVersion: release-2026-09-27\n" in rewritten


def test_build_player_refuses_to_stamp_a_missing_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, PROJECT_SETTINGS.replace("  AndroidBundleVersionCode: 1\n", ""))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    with pytest.raises(SystemExit, match="AndroidBundleVersionCode"):
        player_build.build_player("tool", "AndroidMobile", version="0.2.7-dev+42", run_number=42)


def test_build_player_fails_when_no_artifact_was_produced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_repository(tmp_path, PROJECT_SETTINGS)
    (project / "Build").mkdir()
    (project / "Build" / "Tool.apk").write_bytes(b"stale")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_silent)

    with pytest.raises(SystemExit, match="stale artifact"):
        player_build.build_player("tool", "AndroidMobile")
