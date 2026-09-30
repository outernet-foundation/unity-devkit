import os
import shutil
import tempfile
from functools import partial
from pathlib import Path

import pytest

from unity_devkit import player_build

Call = tuple[tuple[str, ...], dict[str, str]]


def test_prepare_skips_nuget_restore_without_packages_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Call] = []
    monkeypatch.setattr(player_build, "bash", partial(record_call, calls))
    (tmp_path / "Assets").mkdir()

    player_build.prepare_unity_project(tmp_path)

    assert calls == []


def test_prepare_runs_nuget_restore_for_nuget_consumer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Call] = []
    monkeypatch.setattr(player_build, "bash", partial(record_call, calls))
    monkeypatch.setattr(shutil, "which", present_tool)
    (tmp_path / "Assets").mkdir()
    (tmp_path / "Assets" / "packages.config").write_text('<?xml version="1.0"?>\n')

    player_build.prepare_unity_project(tmp_path)

    assert calls == [
        (("dotnet tool restore",), {}),
        ((f"dotnet nugetforunity restore {tmp_path}",), {}),
    ]


def test_prepare_provisions_dotnet_sdk_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Call] = []
    monkeypatch.setattr(player_build, "bash", partial(record_call, calls))
    monkeypatch.setattr(shutil, "which", absent_tool)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / "Assets").mkdir()
    (tmp_path / "Assets" / "packages.config").write_text('<?xml version="1.0"?>\n')

    player_build.prepare_unity_project(tmp_path)

    script_path = Path(tempfile.gettempdir()) / "dotnet-install.sh"
    install_dir = tmp_path / ".dotnet"
    assert calls[0] == ((f"curl -fsSL {player_build.DOTNET_INSTALL_SCRIPT_URL} -o {script_path}",), {})
    expected_install = f"bash {script_path} --version {player_build.DOTNET_SDK_VERSION} --install-dir {install_dir}"
    assert calls[1] == ((expected_install,), {})
    expected_env = {"PATH": f"{install_dir}{os.pathsep}{os.environ['PATH']}", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
    assert calls[2] == (("dotnet tool restore",), expected_env)
    assert calls[3] == ((f"dotnet nugetforunity restore {tmp_path}",), expected_env)


def test_prepare_clears_stale_unity_lockfile(tmp_path: Path) -> None:
    lockfile = tmp_path / "Temp" / "UnityLockfile"
    lockfile.parent.mkdir()
    lockfile.write_text("")

    player_build.prepare_unity_project(tmp_path)

    assert not lockfile.exists()


def record_call(calls: list[Call], command: str, env: dict[str, str] | None = None) -> None:
    calls.append(((command,), env or {}))


def absent_tool(_name: str) -> str | None:
    return None


def present_tool(name: str) -> str:
    return f"/usr/bin/{name}"
