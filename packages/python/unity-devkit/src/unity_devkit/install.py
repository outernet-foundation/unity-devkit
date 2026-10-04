from __future__ import annotations

import os
from pathlib import Path
from subprocess import CalledProcessError
from typing import Annotated

import typer
from bashrun.bash import bash, bash_handoff, bash_output

from ci_devkit.builds import build_reference, build_repository, list_build_tags, pull_build
from ci_devkit.setup_oras import install_oras

from .identity import builds_registry, cache_key
from .player_build import build_player
from .projects import discover_projects

INSTALLABLE_TARGETS = {"AndroidMobile", "MagicLeap2", "Linux"}
ADB_TARGETS = {"AndroidMobile", "MagicLeap2"}
CACHE_ROOT = Path.home() / ".unity-devkit" / "builds"

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def main(
    project: Annotated[str, typer.Option("--project", "-p", help="Unity project name")],
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="Device target (AndroidMobile, MagicLeap2, Linux)"),
    ] = None,
    pr_number: Annotated[
        str,
        typer.Option("--pr-number", help="Pull-request number; empty (outside PRs) selects the dev cache-key tag"),
    ] = "",
    run: Annotated[
        int | None,
        typer.Option("--run", "-r", help="Specific CI run number (github.run_number) to pull"),
    ] = None,
    serial: Annotated[str | None, typer.Option("--serial", "-s", help="adb device serial")] = None,
    build_locally: Annotated[
        bool,
        typer.Option(
            "--build",
            "-B",
            help=(
                "Build the project locally via `build-unity` and install the produced APK / "
                "linux executable. Skips the OCI pull; --pr-number / --run are ignored."
            ),
        ),
    ] = False,
    list_tags: Annotated[
        bool,
        typer.Option("--list", help="List available build tags for (project, target) and exit"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print what would be fetched/installed without doing it"),
    ] = False,
) -> None:
    projects = discover_projects()

    project_name = next((name for name in projects if name.lower() == project.lower()), None)
    if project_name is None:
        valid = ", ".join(projects.keys())
        raise typer.BadParameter(f"Unknown project '{project}'. Valid projects: {valid}")

    project_config = projects[project_name]
    installable = [build for build in (project_config.builds or []) if build in INSTALLABLE_TARGETS]
    if target is None:
        if len(installable) != 1:
            valid = ", ".join(installable) if installable else "(none)"
            raise typer.BadParameter(
                f"--target is required for {project_name} (multiple installable targets). Valid targets: {valid}"
            )
        target_name = installable[0]
    else:
        target_name = next((build for build in installable if build.lower() == target.lower()), None)
        if target_name is None:
            valid = ", ".join(installable)
            raise typer.BadParameter(f"No installable target '{target}' for {project_name}. Valid targets: {valid}")

    if serial and target_name not in ADB_TARGETS:
        print(f"Warning: --serial is ignored for target '{target_name}'")

    if list_tags:
        install_oras()
        registry = _builds_registry()
        username, token = _registry_credentials()
        tags = list_build_tags(registry, project_name, target_name, registry_username=username, registry_token=token)
        if tags:
            print(f"Available tags for {build_repository(registry, project_name, target_name)}:")
            for available_tag in tags:
                print(available_tag)
        return

    if build_locally:
        if pr_number or run:
            print("Warning: --pr-number / --run are ignored when --build is set")
        if dry_run:
            print(f"Would build {project_name} [{target_name}] locally")
            if target_name in ADB_TARGETS:
                serial_part = f" -s {serial}" if serial else ""
                print(f"Would install: adb{serial_part} install <apk>")
            elif target_name == "Linux":
                print("Would launch the produced executable")
            return
        produced = build_player(project_name, target_name)
        apks = [path for path in produced if path.suffix == ".apk"]
        executables = [path for path in produced if path.suffix in {".exe", ".x86_64"}]
    else:
        parsed_pr_number = int(pr_number) if pr_number else None
        tag = f"run-{run}" if run else cache_key(project_name, target_name, parsed_pr_number)

        registry = _builds_registry()
        reference = build_reference(registry, project_name, target_name, tag)
        cache_path = CACHE_ROOT / tag / f"{project_name}-{target_name}".lower()

        if dry_run:
            print(f"Would pull: {reference}")
            print(f"Cache: {cache_path}")
            if target_name in ADB_TARGETS:
                serial_part = f" -s {serial}" if serial else ""
                print(f"Would install: adb{serial_part} install <apk>")
            elif target_name == "Linux":
                print("Would extract build.tar and launch the executable")
            return

        install_oras()
        username, token = _registry_credentials()

        if cache_path.is_dir() and any(cache_path.iterdir()):
            print(f"Using cached build: {cache_path}")
        else:
            cache_path.mkdir(parents=True, exist_ok=True)
            pull_build(
                registry,
                project_name,
                target_name,
                tag,
                cache_path,
                registry_username=username,
                registry_token=token,
            )
            if target_name == "Linux":
                tar_path = cache_path / "build.tar"
                if tar_path.exists():
                    bash(f"tar -xf {tar_path} -C {cache_path}")
                    tar_path.unlink()

        apks = sorted(cache_path.rglob("*.apk"))

        executables = []
        if target_name == "Linux":
            executable = next(
                (
                    item
                    for item in cache_path.iterdir()
                    if item.is_file() and (cache_path / f"{item.stem}_Data").is_dir()
                ),
                None,
            )
            if executable is None:
                print("No Linux executable found in artifact (expected a file with a matching _Data/ directory)")
                raise SystemExit(1)
            executables = [executable]

    if target_name in ADB_TARGETS:
        if not apks:
            print("No .apk found in install source")
            raise SystemExit(1)

        print(f"Installing: {apks[0].name}")
        adb_prefix = f"adb -s {serial}" if serial else "adb"
        bash(f"{adb_prefix} install {apks[0]}")
        print("Done.")
    else:
        if not executables:
            print("No linux executable found in install source")
            raise SystemExit(1)
        executable = executables[0]
        os.chmod(executable, executable.stat().st_mode | 0o755)
        print(f"Launching: {executable.name}")
        bash_handoff(str(executable))


def _builds_registry() -> str:
    owner_repo = bash_output("gh repo view --json nameWithOwner --jq .nameWithOwner").strip()
    return builds_registry(f"ghcr.io/{owner_repo}")


def _registry_credentials() -> tuple[str | None, str | None]:
    try:
        token = bash_output("gh auth token").strip()
    except CalledProcessError:
        print("gh CLI not authenticated; falling back to ambient registry credentials")
        return None, None
    return "oauth2", token
