from pathlib import Path

import pytest

from unity_devkit.versioning import stamp_build_version

PROJECT_SETTINGS = """PlayerSettings:
  m_ObjectHideFlags: 0
  productGUID: 26c3d6c0f3f2e6d4d9a5e3f4a1b2c3d4
  AndroidBundleVersionCode: 1
  AndroidTargetArchitectures: 3
  bundleVersion: 0.1.0
"""


def write_project(tmp_path: Path, project_settings: str) -> Path:
    project = tmp_path / "Project"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectSettings.asset").write_text(project_settings)
    return project


def test_stamp_writes_version_and_code(tmp_path: Path) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS)

    stamped = stamp_build_version(project, "0.2.7-dev+42", 42)

    assert stamped == "0.2.7-dev+42"
    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  AndroidBundleVersionCode: 42\n" in rewritten
    assert "  bundleVersion: 0.2.7-dev+42\n" in rewritten
    assert "0.1.0" not in rewritten


def test_stamp_is_opaque_to_the_version_string(tmp_path: Path) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS)

    stamped = stamp_build_version(project, "release-2026-09-27", 7)

    assert stamped == "release-2026-09-27"
    rewritten = (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert "  bundleVersion: release-2026-09-27\n" in rewritten


def test_stamp_missing_field_refuses(tmp_path: Path) -> None:
    project = write_project(tmp_path, PROJECT_SETTINGS.replace("  AndroidBundleVersionCode: 1\n", ""))

    with pytest.raises(SystemExit, match="AndroidBundleVersionCode"):
        stamp_build_version(project, "0.2.7-dev+42", 42)
