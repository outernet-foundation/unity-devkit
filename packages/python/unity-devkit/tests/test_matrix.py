import json
from pathlib import Path

import pytest

from unity_devkit import matrix


def write_repository(tmp_path: Path, builds: list[str] | None = None) -> None:
    project = tmp_path / "apps" / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    config: dict[str, object] = {"name": "tool"}
    if builds is not None:
        config["platforms"] = {platform: {} for platform in builds}
    (project / "unity-devkit.json").write_text(json.dumps(config))


def test_matrix_emits_entries_from_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_repository(tmp_path, builds=["Linux"])
    monkeypatch.chdir(tmp_path)

    matrix.build_matrix()

    legs = json.loads(capsys.readouterr().out)
    assert legs == [
        {
            "project": "tool",
            "platform": "Linux",
            "editor-image": "unityci/editor:6000.0.66f1-linux-il2cpp-3",
        }
    ]


def test_matrix_fails_without_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="No projects with builds declared"):
        matrix.build_matrix()


def test_matrix_project_filter_scopes_to_one_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_repository(tmp_path, builds=["Linux"])
    other = tmp_path / "apps" / "Other"
    (other / "ProjectSettings").mkdir(parents=True)
    (other / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (other / "unity-devkit.json").write_text(json.dumps({"name": "other", "platforms": {"Linux": {}}}))
    monkeypatch.chdir(tmp_path)

    matrix.build_matrix(project="other")

    legs = json.loads(capsys.readouterr().out)
    assert [entry["project"] for entry in legs] == ["other"]


def test_matrix_project_filter_fails_on_unknown_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, builds=["Linux"])
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Unknown project 'missing'"):
        matrix.build_matrix(project="missing")


def test_check_matrix_includes_path_only_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    matrix.compile_check_matrix()

    legs = json.loads(capsys.readouterr().out)
    assert legs == [{"project": "tool", "editor-image": "unityci/editor:6000.0.66f1-linux-il2cpp-3"}]


def test_check_matrix_project_filter_scopes_to_one_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_repository(tmp_path)
    other = tmp_path / "apps" / "Other"
    (other / "ProjectSettings").mkdir(parents=True)
    (other / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (other / "unity-devkit.json").write_text(json.dumps({"name": "other"}))
    monkeypatch.chdir(tmp_path)

    matrix.compile_check_matrix(project="other")

    legs = json.loads(capsys.readouterr().out)
    assert legs == [{"project": "other", "editor-image": "unityci/editor:6000.0.66f1-linux-il2cpp-3"}]
