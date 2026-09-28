from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Annotated

import typer
from bashrun.bash import bash, bash_check, bash_handoff, bash_output

from .projects import discover_projects
from .player_build import build_player

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
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch to pull the build from (default: current git branch)"),
    ] = None,
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
                "linux executable. Skips the OCI pull; --branch / --run are ignored."
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

    package_name = f"{project_name}-{target_name}".lower()

    if list_tags:
        _require_oras()
        reference_base = _resolve_reference_base(package_name)
        _login_ghcr()
        if bash_check(f"oras repo tags {reference_base}"):
            output = bash_output(f"oras repo tags {reference_base}")
            if output.strip():
                print(f"Available tags for {reference_base}:")
                print(output, end="")
            else:
                print(f"No tags found for {reference_base}")
        else:
            print(f"No tags found for {reference_base}")
        return

    if build_locally:
        if branch or run:
            print("Warning: --branch / --run are ignored when --build is set")
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
        resolved_branch = branch
        if not resolved_branch:
            resolved_branch = bash_output("git rev-parse --abbrev-ref HEAD").strip()
            if resolved_branch == "HEAD":
                raise typer.BadParameter("HEAD is detached; pass --branch explicitly")

        tag = f"run-{run}" if run else resolved_branch.replace("/", "-")

        reference_base = _resolve_reference_base(package_name)
        reference = f"{reference_base}:{tag}"
        cache_path = CACHE_ROOT / tag / package_name

        if dry_run:
            print(f"Would pull: {reference}")
            print(f"Cache: {cache_path}")
            if target_name in ADB_TARGETS:
                serial_part = f" -s {serial}" if serial else ""
                print(f"Would install: adb{serial_part} install <apk>")
            elif target_name == "Linux":
                print("Would extract build.tar and launch the executable")
            return

        _require_oras()
        _login_ghcr()

        if cache_path.is_dir() and any(cache_path.iterdir()):
            print(f"Using cached build: {cache_path}")
        else:
            cache_path.mkdir(parents=True, exist_ok=True)
            bash(f"oras pull {reference} -o {cache_path}")
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


def _require_oras() -> None:
    if not shutil.which("oras"):
        print("Error: oras is not on PATH. Install it:")
        print("  macOS:  brew install oras")
        print("  Linux:  https://oras.land/docs/install")
        print("  Windows: scoop install oras")
        raise SystemExit(1)


def _resolve_reference_base(package_name: str) -> str:
    owner_repo = bash_output("gh repo view --json nameWithOwner --jq .nameWithOwner").strip()
    return f"ghcr.io/{owner_repo}/builds/{package_name}".lower()


def _login_ghcr() -> None:
    token = bash_output("gh auth token").strip()
    bash("oras login ghcr.io --username oauth2 --password-stdin", stdin_text=token)
