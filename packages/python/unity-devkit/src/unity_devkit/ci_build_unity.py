from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer
from bashrun.bash import bash
from pydantic_settings import BaseSettings

from ci_devkit.cache import restore, save
from ci_devkit.ci_step import ci_step
from ci_devkit.setup import configure_git, install_dotnet
from ci_devkit.setup_oras import install_oras
from .license_restore import restore_or_activate_license
from .player_build import build_player, parse_environment_fields, resolve_unity_project
from .upm_cache import restore_upm_cache, save_upm_cache


class Settings(BaseSettings):
    github_workspace: str


app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def ci_build_unity(
    project: Annotated[str, typer.Option(help="Project name")],
    platform: Annotated[str, typer.Option(help="Target platform")],
    cache_key: Annotated[str, typer.Option(help="Cache key prefix")],
    registry: Annotated[str, typer.Option(help="OCI registry path for the library cache")],
    builds_registry: Annotated[str, typer.Option(help="OCI registry path for build artifacts")],
    run_number: Annotated[int, typer.Option(help="CI run number")] = 0,
    branch: Annotated[str, typer.Option(help="Git branch name")] = "dev",
    environment_preset: Annotated[
        str, typer.Option(help="Environment preset name; empty leaves the workspace untouched")
    ] = "",
    development: Annotated[bool, typer.Option("--development", help="Development build column")] = False,
    environment_fields: Annotated[
        str, typer.Option(help="Newline-separated path=value environment field overrides")
    ] = "",
    version: Annotated[
        str, typer.Option(help="Version string to stamp into ProjectSettings.asset; empty builds unversioned")
    ] = "",
) -> None:
    settings = Settings.model_validate({})
    fields = parse_environment_fields(environment_fields.splitlines())

    with ci_step("Setup"):
        configure_git(settings.github_workspace)
        install_dotnet("8.0")
        install_oras()
        restore_or_activate_license()
        project_path = resolve_unity_project(project).path
        restore_upm_cache(project_path)

    branch_slug = branch.replace("/", "-")
    tag = f"{cache_key}-{platform}-{branch_slug}"
    fallback_branch = "dev"
    fallback_tags = [f"{cache_key}-{platform}-{fallback_branch}"] if branch_slug != fallback_branch else None

    with ci_step("Restore library cache"):
        restore(registry, "unity-library", tag, Path("."), fallback_tags=fallback_tags)

    with ci_step(f"Build {project} [{platform}]"):
        build_player(
            project,
            platform,
            version=version,
            run_number=run_number,
            development=development,
            environment_preset=environment_preset,
            environment_fields=fields,
        )

    with ci_step("Save library cache"):
        # PackageCache (~1.6 GiB) is redundant with the shared UPM cache at ~/.cache/Unity/upm/
        package_cache = project_path / "Library" / "PackageCache"
        if package_cache.exists():
            shutil.rmtree(package_cache)

        relative_project_path = project_path.relative_to(Path.cwd())
        save(registry, "unity-library", tag, Path("."), [f"{relative_project_path}/Library/"])

    with ci_step("Save UPM cache"):
        save_upm_cache(project_path)

    with ci_step("Collect build artifacts"):
        build_directory = project_path / "Build"
        if build_directory.is_dir():
            artifact_directory = Path("/tmp/unity-builds")
            artifact_directory.mkdir(parents=True, exist_ok=True)
            if platform == "Linux":
                shutil.copytree(build_directory, artifact_directory, dirs_exist_ok=True)
            else:
                for file in build_directory.rglob("*"):
                    if file.suffix in {".apk", ".exe"}:
                        shutil.copy2(file, artifact_directory / file.name)
                for report in build_directory.rglob("BuildReport.json"):
                    destination = artifact_directory / report.relative_to(build_directory)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(report, destination)

    with ci_step("Push build artifacts"):
        artifact_directory = Path("/tmp/unity-builds")
        if not artifact_directory.is_dir() or not any(artifact_directory.iterdir()):
            print("No build artifacts to push")
        else:
            reference_base = f"{builds_registry}/{project}-{platform}".lower()
            tags = (branch_slug, f"run-{run_number}")
            if platform == "Linux":
                staging = Path("/tmp/unity-builds-push")
                staging.mkdir(parents=True, exist_ok=True)
                tar_path = staging / "build.tar"
                bash(f"tar -cf {tar_path} -C {artifact_directory} .")
                try:
                    for build_tag in tags:
                        bash(f"oras push {reference_base}:{build_tag} build.tar", cwd=staging)
                finally:
                    tar_path.unlink(missing_ok=True)
            else:
                joined = " ".join(
                    sorted(
                        str(path.relative_to(artifact_directory))
                        for path in artifact_directory.rglob("*")
                        if path.is_file()
                    )
                )
                for build_tag in tags:
                    bash(f"oras push {reference_base}:{build_tag} {joined}", cwd=artifact_directory)
            print(f"Pushed build artifacts: {reference_base} ({', '.join(tags)})")
