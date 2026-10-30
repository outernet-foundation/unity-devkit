import json
from pathlib import Path

import pytest
import typer

from unity_devkit.check_unity_lock import check_project_lock, check_unity_lock

MANIFEST = {
    "dependencies": {
        "com.unity.xr.management": "4.5.3",
        "org.outernet.lbetoolkit": "https://github.com/outernet-foundation/lbe-toolkit.git?path=/Core#3783af528365f8dfc98d3fff0f0717fa5e7019",
    }
}

MATCHING_LOCK = {
    "dependencies": {
        "com.unity.xr.management": {"version": "4.5.3", "depth": 0, "source": "registry"},
        "com.unity.mathematics": {"version": "1.3.2", "depth": 1, "source": "registry"},
        "org.outernet.lbetoolkit": {
            "version": "https://github.com/outernet-foundation/lbe-toolkit.git?path=/Core#3783af528365f8dfc98d3fff0f0717fa5e7019",
            "depth": 0,
            "source": "git",
            "hash": "3783af528365f8dfc98d3fff0f0717fa5e7019",
        },
    }
}


def write_packages(
    tmp_path: Path,
    manifest: str = json.dumps(MANIFEST),
    lock: str | None = json.dumps(MATCHING_LOCK),
) -> Path:
    packages = tmp_path / "Packages"
    packages.mkdir(parents=True)
    (packages / "manifest.json").write_text(manifest, encoding="utf-8")

    if lock is not None:
        (packages / "packages-lock.json").write_text(lock, encoding="utf-8")

    return tmp_path


def test_matching_lock_reports_nothing(tmp_path: Path) -> None:
    write_packages(tmp_path)

    assert check_project_lock("tool", tmp_path) == []


def test_ignores_lock_entries_without_manifest_dependencies(tmp_path: Path) -> None:
    assert check_project_lock("tool", write_packages(tmp_path, manifest=json.dumps({"dependencies": {}}))) == []


def test_version_mismatch_is_reported(tmp_path: Path) -> None:
    stale = json.loads(json.dumps(MATCHING_LOCK))
    stale["dependencies"]["org.outernet.lbetoolkit"] = {"version": "1.1.0-dev.39", "depth": 0, "source": "registry"}
    write_packages(tmp_path, lock=json.dumps(stale))

    failures = check_project_lock("tool", tmp_path)

    assert len(failures) == 1
    assert "org.outernet.lbetoolkit" in failures[0]
    assert "1.1.0-dev.39" in failures[0]
    assert "3783af528365f8dfc98d3fff0f0717fa5e7019" in failures[0]


def test_manifest_dependency_absent_from_lock_is_reported(tmp_path: Path) -> None:
    stale = json.loads(json.dumps(MATCHING_LOCK))
    del stale["dependencies"]["com.unity.xr.management"]
    write_packages(tmp_path, lock=json.dumps(stale))

    failures = check_project_lock("tool", tmp_path)

    assert len(failures) == 1
    assert "com.unity.xr.management" in failures[0]
    assert "4.5.3" in failures[0]


def test_missing_lock_file_is_reported(tmp_path: Path) -> None:
    write_packages(tmp_path, lock=None)

    failures = check_project_lock("tool", tmp_path)

    assert len(failures) == 1
    assert "lock-unity" in failures[0]


def test_missing_manifest_is_reported(tmp_path: Path) -> None:
    project = write_packages(tmp_path)
    (project / "Packages" / "manifest.json").unlink()

    assert check_project_lock("tool", tmp_path) == [f"tool: {project / 'Packages' / 'manifest.json'} does not exist"]


def test_unparseable_lock_is_reported(tmp_path: Path) -> None:
    write_packages(tmp_path, lock="{")

    failures = check_project_lock("tool", tmp_path)

    assert len(failures) == 1
    assert "unparseable" in failures[0]


def test_cli_passes_when_every_project_agrees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (project / "unity-devkit.json").write_text(json.dumps({"name": "Tool", "platforms": {"Linux": {}}}))
    packages = project / "Packages"
    packages.mkdir()
    (packages / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (packages / "packages-lock.json").write_text(json.dumps(MATCHING_LOCK), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    check_unity_lock(project=None)


def test_cli_exits_non_zero_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (project / "unity-devkit.json").write_text(json.dumps({"name": "Tool", "platforms": {"Linux": {}}}))
    packages = project / "Packages"
    packages.mkdir()
    (packages / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="lock-unity"):
        check_unity_lock(project=None)


def test_cli_rejects_unknown_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ProjectSettings").mkdir()
    (tmp_path / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (tmp_path / "unity-devkit.json").write_text(json.dumps({"name": "Tool"}))

    with pytest.raises(typer.BadParameter):
        check_unity_lock(project="other")
