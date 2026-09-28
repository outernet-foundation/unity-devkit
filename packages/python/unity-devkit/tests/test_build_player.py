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

RECEIVED_SESSIONS: list[tuple[str, dict[str, str]]] = []


def write_repository(tmp_path: Path, project_settings: str, *, builds: list[str] | None = None) -> Path:
    project = tmp_path / "apps" / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectSettings.asset").write_text(project_settings)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    config: dict[str, object] = {"name": "tool"}
    if builds is not None:
        config["platforms"] = {platform: {} for platform in builds}
    (project / "build-config.json").write_text(json.dumps(config))
    return project


def fake_unity_build_producing(project_path: Path, extra_flags: str, *, nographics: bool, env: dict[str, str]) -> Path:
    RECEIVED_SESSIONS.append((extra_flags, env))
    build_directory = project_path / "Build"
    build_directory.mkdir(exist_ok=True)
    (build_directory / "Tool.apk").write_bytes(b"apk")
    return Path("unused-editor.log")


def fake_unity_build_silent(project_path: Path, extra_flags: str, *, nographics: bool, env: dict[str, str]) -> Path:
    return Path("unused-editor.log")


def test_build_player_stamps_version_and_returns_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    RECEIVED_SESSIONS.clear()
    project = write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    produced = player_build.build_player("tool", "AndroidMobile", version="0.2.7-dev+42", run_number=42)

    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  AndroidBundleVersionCode: 42\n" in rewritten
    assert "  bundleVersion: 0.2.7-dev+42\n" in rewritten
    assert "0.1.0" not in rewritten
    assert produced == [project / "Build" / "Tool.apk"]
    assert RECEIVED_SESSIONS[0][0] == "-buildTarget Android -executeMethod Outernet.PlayerBuild.Entry"


def test_build_player_treats_the_version_string_as_opaque(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    player_build.build_player("tool", "AndroidMobile", version="release-2026-09-27", run_number=7)

    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  bundleVersion: release-2026-09-27\n" in rewritten


def test_build_player_refuses_to_stamp_a_missing_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(
        tmp_path, PROJECT_SETTINGS.replace("  AndroidBundleVersionCode: 1\n", ""), builds=["AndroidMobile"]
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    with pytest.raises(SystemExit, match="AndroidBundleVersionCode"):
        player_build.build_player("tool", "AndroidMobile", version="0.2.7-dev+42", run_number=42)


def test_build_player_fails_when_no_artifact_was_produced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    (project / "Build").mkdir()
    (project / "Build" / "Tool.apk").write_bytes(b"stale")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_silent)

    with pytest.raises(SystemExit, match="stale artifact"):
        player_build.build_player("tool", "AndroidMobile")


def test_unknown_project_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Unknown project 'nope'"):
        player_build.build_player("nope", "AndroidMobile")


def test_project_without_builds_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, PROJECT_SETTINGS)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="declares no builds"):
        player_build.build_player("tool", "AndroidMobile")


def test_unknown_build_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Unknown build 'win64'"):
        player_build.build_player("tool", "win64")


def test_build_without_platform_config_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile", "SteamDeck"])
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="No platform config for build 'SteamDeck'"):
        player_build.build_player("tool", "SteamDeck")


def test_build_player_environment_carries_the_entry_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    RECEIVED_SESSIONS.clear()
    write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    player_build.build_player(
        "tool",
        "AndroidMobile",
        development=True,
        environment_preset="airgapped",
        environment_fields={"localConfig.apiUrl": "http://tool.local"},
    )

    assert RECEIVED_SESSIONS[0][1] == {
        "PLATFORM": "AndroidMobile",
        "DEVELOPMENT": "true",
        "ENVIRONMENT": "airgapped",
        "ENVIRONMENT_FIELDS": '{"localConfig.apiUrl": "http://tool.local"}',
    }


def test_build_player_without_environment_sends_platform_and_development_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    RECEIVED_SESSIONS.clear()
    write_repository(tmp_path, PROJECT_SETTINGS, builds=["AndroidMobile"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(player_build, "run_unity_batchmode", fake_unity_build_producing)

    player_build.build_player("tool", "AndroidMobile")

    assert RECEIVED_SESSIONS[0][1] == {"PLATFORM": "AndroidMobile", "DEVELOPMENT": "false"}
