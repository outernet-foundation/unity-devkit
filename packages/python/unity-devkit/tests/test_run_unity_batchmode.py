import functools
from pathlib import Path

import pytest

from unity_devkit import player_build


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
    monkeypatch.setattr(player_build, "read_editor_version", fake_editor_version)
    monkeypatch.setattr(player_build, "find_editor_for_version", functools.partial(editor_at, script))


def test_compile_error_fails_despite_zero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "Foo.cs(12,34): error CS0246: type not found", 0))

    with pytest.raises(SystemExit, match="silent failure"):
        player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_script_updater_noise_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    noise = (
        "[Script Updater] Library/PackageCache/com.cysharp.r3/Runtime/UnityXR.cs(9,89): error CS0246: type not found"
    )
    patch_editor(monkeypatch, write_fake_editor(tmp_path, noise, 0))

    player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_compile_error_after_script_updater_noise_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    noise = (
        "[Script Updater] Library/PackageCache/com.cysharp.r3/Runtime/UnityXR.cs(9,89): error CS0246: type not found"
    )
    real_error = "Assets/Foo.cs(1,1): error CS1002: ; expected"
    patch_editor(monkeypatch, write_fake_editor(tmp_path, f"{noise}\n{real_error}", 0))

    with pytest.raises(SystemExit, match="silent failure"):
        player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_clean_log_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "DisplayProgressbar: renewal", 0))

    player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))


def test_nonzero_exit_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "DisplayProgressbar: renewal", 3))

    with pytest.raises(SystemExit, match="Unity exited 3"):
        player_build.run_unity_batchmode(tmp_path)


def test_package_manager_signature_still_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = write_fake_editor(tmp_path, "An error occurred while resolving packages: nope", 0)
    patch_editor(monkeypatch, script)

    with pytest.raises(SystemExit, match="silent failure"):
        player_build.run_unity_batchmode(tmp_path)


def test_compile_error_dedups_into_one_annotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    line = "Assets/Foo.cs(12,34): error CS0246: type not found"
    patch_editor(monkeypatch, write_fake_editor(tmp_path, f"{line}\n{line}", 0))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    with pytest.raises(SystemExit, match="silent failure"):
        player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))

    captured = capfd.readouterr()
    assert captured.out.count("::error file=Assets/Foo.cs,line=12") == 1
    assert "title=CS0246 x2" in captured.out


def test_compile_error_reports_distinct_list_locally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    patch_editor(monkeypatch, write_fake_editor(tmp_path, "Assets/Foo.cs(12,34): error CS0246: type not found", 0))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    with pytest.raises(SystemExit, match="silent failure"):
        player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))

    captured = capfd.readouterr()
    assert "CS0246" in captured.err
    assert "::error" not in captured.out


def test_script_updater_noise_not_annotated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    noise = (
        "[Script Updater] Library/PackageCache/com.cysharp.r3/Runtime/UnityXR.cs(9,89): error CS0246: type not found"
    )
    patch_editor(monkeypatch, write_fake_editor(tmp_path, noise, 0))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))

    captured = capfd.readouterr()
    assert "::error" not in captured.out


def test_annotations_capped_at_ten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    log = "\n".join(f"Assets/F{i}.cs({i},1): error CS0246: gone" for i in range(1, 15))
    patch_editor(monkeypatch, write_fake_editor(tmp_path, log, 0))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    with pytest.raises(SystemExit, match="silent failure"):
        player_build.run_unity_batchmode(tmp_path, extra_failure_signatures=("error CS",))

    captured = capfd.readouterr()
    assert captured.out.count("::error file=") == 10
    assert "...and 4 more distinct compile errors" in captured.out
