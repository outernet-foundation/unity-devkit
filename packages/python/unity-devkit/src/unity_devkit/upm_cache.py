from __future__ import annotations

import hashlib
from pathlib import Path

from ci_devkit.cache import restore, save

UPM_CACHE_NAME = "unity-upm"
UPM_CACHE_DIRECTORY = Path.home() / ".cache" / "Unity" / "upm"
UPM_MANIFESTS = ("manifest.json", "packages-lock.json")


def restore_upm_cache(project_path: Path, registry: str) -> None:
    UPM_CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    restore(registry, UPM_CACHE_NAME, upm_cache_tag(project_path), UPM_CACHE_DIRECTORY)


def save_upm_cache(project_path: Path, registry: str) -> None:
    UPM_CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    save(registry, UPM_CACHE_NAME, upm_cache_tag(project_path), UPM_CACHE_DIRECTORY, ["."])


# A never-resolved project has no packages-lock.json yet; hashing it as empty keeps the
# tag computable, and the lock written by that run produces the tag the next run restores.
def upm_cache_tag(project_path: Path) -> str:
    digest = hashlib.sha256()
    for name in UPM_MANIFESTS:
        manifest = project_path / "Packages" / name
        digest.update(manifest.read_bytes() if manifest.exists() else b"")
    return digest.hexdigest()
