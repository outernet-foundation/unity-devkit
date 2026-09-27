import functools
from pathlib import Path

import pytest

from unity_devkit import unity


def write_fake_editor(directory: Path, output: str, exit_code: int) -> Path:
    script = directory / "fake-unity"
    script.write_text(f"#!/bin/bash\ncat <<'LOG'\n{output}\nLOG\nexit {exit_code}\n")
    script.chmod(0o755)
    return script


def fake_editor_version(project_path: Path) -> str:
    return "6000.0.66f1"


def editor_at(script: Path, version: str) -> Path:
    return script


def patch_editor(monkeypatch: pytest.MonkeyPatch, script: Path) -> None:
    monkeypatch.setattr(unity, "read_editor_version", fake_editor_version)
    monkeypatch.setattr(unity, "find_editor_for_version", functools.partial(editor_at, script))


def test_compile_error_fails_despite_zero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "Foo.cs(12,34): error CS0246: type not found", 0))

    with pytest.raises(SystemExit, match="silent failure"):
        unity.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_clean_log_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "DisplayProgressbar: renewal", 0))

    unity.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_nonzero_exit_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "DisplayProgressbar: renewal", 3))

    with pytest.raises(SystemExit, match="Unity exited 3"):
        unity.run_unity_batchmode(tmp_path)


def test_package_manager_signature_still_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = write_fake_editor(tmp_path, "An error occurred while resolving packages: nope", 0)
    patch_editor(monkeypatch, script)

    with pytest.raises(SystemExit, match="silent failure"):
        unity.run_unity_batchmode(tmp_path)
