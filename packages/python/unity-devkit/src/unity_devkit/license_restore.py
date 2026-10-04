from __future__ import annotations

import random
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
from bashrun.bash import CalledProcessError, bash
from pydantic_settings import BaseSettings

from ci_devkit.cache import restore, save


class Settings(BaseSettings):
    unity_email: str
    unity_password: str
    unity_serial: str


tag_app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

LICENSE_CACHE_NAME = "unity-license"
ACTIVATION_ATTEMPTS = 3
RETRY_JITTER_SECONDS = (30.0, 120.0)


@tag_app.command()
def tag_main() -> None:
    print(license_cache_tag())


def restore_or_activate_license(registry: str, license_tag: str | None = None) -> None:
    license_directory = Path.home() / ".local" / "share" / "unity3d" / "Unity"
    license_directory.mkdir(parents=True, exist_ok=True)
    tag = license_tag or license_cache_tag()

    for attempt in range(1, ACTIVATION_ATTEMPTS + 1):
        if restore(registry, LICENSE_CACHE_NAME, tag, license_directory):
            return
        if license_activated():
            save(registry, LICENSE_CACHE_NAME, tag, license_directory, ["Unity_lic.ulf"])
            return
        if attempt == ACTIVATION_ATTEMPTS:
            break
        wait = random.SystemRandom().uniform(*RETRY_JITTER_SECONDS)
        print(
            f"License activation rejected (attempt {attempt}/{ACTIVATION_ATTEMPTS}) — "
            f"waiting {wait:.0f}s, then re-restoring and retrying"
        )
        time.sleep(wait)

    raise SystemExit(
        f"Unity license activation failed after {ACTIVATION_ATTEMPTS} attempts — "
        "check UNITY_EMAIL/UNITY_PASSWORD/UNITY_SERIAL and the license seat"
    )


def activate_license() -> None:
    settings = Settings.model_validate({})
    bash(
        f'unity-editor -batchmode -nographics -quit -serial "{settings.unity_serial}"'
        f' -username "{settings.unity_email}" -password "{settings.unity_password}" -logFile /dev/stdout'
    )


def license_activated() -> bool:
    try:
        activate_license()
    except CalledProcessError:
        return False
    return True


# A whole CI run pins one tag (the matrix verb's license output, passed as
# --license) so a run straddling midnight UTC does not save/restore-miss itself.
def license_cache_tag() -> str:
    return f"v-{datetime.now(UTC).strftime('%Y-%m-%d')}"
