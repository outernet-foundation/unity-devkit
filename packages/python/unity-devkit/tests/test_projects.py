import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from unity_devkit.projects import directories_containing, discover_projects


def create_unity_project(root: Path, relative: str) -> Path:
    project = root / relative
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    return project


def write_build_config(project_dir: Path, config: dict[str, object]) -> Path:
    config_path = project_dir / "unity-devkit.json"
    config_path.write_text(json.dumps(config))
    return config_path


def test_discovers_project_with_platforms_keys_as_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = create_unity_project(tmp_path, "Alpha")
    write_build_config(project, {"name": "Alpha", "platforms": {"Linux": {}, "AndroidMobile": {}}})
    monkeypatch.chdir(tmp_path)

    projects = discover_projects()

    assert set(projects) == {"Alpha"}
    assert projects["Alpha"].path == project
    assert projects["Alpha"].builds == ["Linux", "AndroidMobile"]


def test_name_is_decoupled_from_directory_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = create_unity_project(tmp_path, "apps/capture-tool")
    write_build_config(project, {"name": "capture"})
    monkeypatch.chdir(tmp_path)

    projects = discover_projects()

    assert set(projects) == {"capture"}
    assert projects["capture"].path == project


def test_path_only_project_has_no_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = create_unity_project(tmp_path, "Harness")
    write_build_config(project, {"name": "Harness"})
    monkeypatch.chdir(tmp_path)

    projects = discover_projects()

    assert set(projects) == {"Harness"}
    assert projects["Harness"].builds is None


def test_no_build_config_found_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match=r"No unity-devkit\.json found"):
        discover_projects()


def test_config_outside_unity_project_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    not_a_project = tmp_path / "not-a-project"
    not_a_project.mkdir()
    write_build_config(not_a_project, {"name": "broken"})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="not a Unity project"):
        discover_projects()


def test_duplicate_project_name_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = create_unity_project(tmp_path, "apps/one")
    write_build_config(first, {"name": "dup"})
    second = create_unity_project(tmp_path, "apps/two")
    write_build_config(second, {"name": "dup"})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Duplicate project name 'dup'"):
        discover_projects()


def test_ignores_csharp_owned_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = create_unity_project(tmp_path, "App")
    write_build_config(
        project,
        {
            "name": "App",
            "environment_config": "Assets/App/UnityEnv.cs",
            "platforms": {"AndroidMobile": {"render_pipeline": "Assets/Settings/Android.asset"}},
        },
    )
    monkeypatch.chdir(tmp_path)

    projects = discover_projects()

    assert projects["App"].builds == ["AndroidMobile"]


def test_missing_name_field_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = create_unity_project(tmp_path, "Alpha")
    write_build_config(project, {"platforms": {"Linux": {}}})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        discover_projects()


def test_directories_containing_honors_prune_list(tmp_path: Path) -> None:
    vendored = tmp_path / "vendor" / "Library" / "SomeProject"
    (vendored / "ProjectSettings").mkdir(parents=True)
    (vendored / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    real = create_unity_project(tmp_path, "Real")

    settings_directories = directories_containing(tmp_path, "ProjectVersion.txt")

    assert real / "ProjectSettings" in settings_directories
    assert vendored / "ProjectSettings" not in settings_directories
