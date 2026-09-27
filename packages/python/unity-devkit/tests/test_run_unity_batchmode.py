from pathlib import Path

import pytest

from unity_devkit import unity


class FakeEditorCommand:
    def __init__(self, command: str) -> None:
        self.command = command

    def __call__(self, project_path: Path, nographics: bool = True, *, auto_quit: bool = True) -> str:
        return self.command


def write_fake_editor(directory: Path, output: str, exit_code: int) -> FakeEditorCommand:
    script = directory / "fake-unity"
    script.write_text(f"#!/bin/bash\ncat <<'LOG'\n{output}\nLOG\nexit {exit_code}\n")
    script.chmod(0o755)
    return FakeEditorCommand(str(script))


def test_compile_error_fails_despite_zero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        unity, "unity_batchmode_command", write_fake_editor(tmp_path, "Foo.cs(12,34): error CS0246: type not found", 0)
    )

    with pytest.raises(SystemExit, match="silent failure"):
        unity.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_clean_log_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(unity, "unity_batchmode_command", write_fake_editor(tmp_path, "DisplayProgressbar: renewal", 0))

    unity.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_nonzero_exit_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(unity, "unity_batchmode_command", write_fake_editor(tmp_path, "DisplayProgressbar: renewal", 3))

    with pytest.raises(SystemExit, match="Unity exited 3"):
        unity.run_unity_batchmode(tmp_path)


def test_package_manager_signature_still_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        unity,
        "unity_batchmode_command",
        write_fake_editor(tmp_path, "An error occurred while resolving packages: nope", 0),
    )

    with pytest.raises(SystemExit, match="silent failure"):
        unity.run_unity_batchmode(tmp_path)
