import json
from pathlib import Path

import pytest

from unity_devkit.unity import resolve_unity_build


def write_repository(tmp_path: Path, entry: dict[str, object]) -> None:
    project = tmp_path / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (tmp_path / "unity-devkit.json").write_text(json.dumps({"tool": entry}))


def test_unknown_project_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, {"path": "Tool", "builds": ["Linux"]})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Unknown project 'nope'"):
        resolve_unity_build("nope", "Linux")


def test_project_without_builds_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, {"path": "Tool"})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="declares no builds"):
        resolve_unity_build("tool", "Linux")


def test_unknown_build_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, {"path": "Tool", "builds": ["Linux"]})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Unknown build 'win64'"):
        resolve_unity_build("tool", "win64")


def test_resolve_returns_build_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, {"path": "Tool", "builds": ["Linux"]})
    monkeypatch.chdir(tmp_path)

    project_config, build_target = resolve_unity_build("tool", "Linux")

    assert project_config.path == Path.cwd() / "Tool"
    assert build_target == "StandaloneLinux64"
