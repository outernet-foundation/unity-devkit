import hashlib
from pathlib import Path

from unity_devkit.upm_cache import upm_cache_tag


def write_packages(project_path: Path, manifest: str, lock: str | None) -> None:
    packages = project_path / "Packages"
    packages.mkdir(parents=True)
    (packages / "manifest.json").write_text(manifest)
    if lock is not None:
        (packages / "packages-lock.json").write_text(lock)


def test_tag_hashes_both_manifests(tmp_path: Path) -> None:
    write_packages(tmp_path, '{"a":1}', '{"b":2}')

    expected = hashlib.sha256(b'{"a":1}{"b":2}').hexdigest()

    assert upm_cache_tag(tmp_path) == expected


def test_tag_changes_when_either_manifest_changes(tmp_path: Path) -> None:
    write_packages(tmp_path, '{"a":1}', '{"b":2}')
    before = upm_cache_tag(tmp_path)

    (tmp_path / "Packages" / "packages-lock.json").write_text('{"b":3}')

    assert upm_cache_tag(tmp_path) != before


def test_tag_treats_missing_lock_as_empty(tmp_path: Path) -> None:
    write_packages(tmp_path, '{"a":1}', None)

    expected = hashlib.sha256(b'{"a":1}').hexdigest()

    assert upm_cache_tag(tmp_path) == expected
