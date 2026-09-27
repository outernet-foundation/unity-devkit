from pathlib import Path

import pytest

from unity_devkit import player_build


def test_prepare_skips_nuget_restore_without_packages_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(player_build, "bash", calls.append)
    (tmp_path / "Assets").mkdir()

    player_build.prepare_unity_project(tmp_path)

    assert calls == []


def test_prepare_runs_nuget_restore_for_nuget_consumer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(player_build, "bash", calls.append)
    (tmp_path / "Assets").mkdir()
    (tmp_path / "Assets" / "packages.config").write_text('<?xml version="1.0"?>\n')

    player_build.prepare_unity_project(tmp_path)

    assert calls == ["dotnet tool restore", f"dotnet nugetforunity restore {tmp_path}"]


def test_prepare_clears_stale_unity_lockfile(tmp_path: Path) -> None:
    lockfile = tmp_path / "Temp" / "UnityLockfile"
    lockfile.parent.mkdir()
    lockfile.write_text("")

    player_build.prepare_unity_project(tmp_path)

    assert not lockfile.exists()
