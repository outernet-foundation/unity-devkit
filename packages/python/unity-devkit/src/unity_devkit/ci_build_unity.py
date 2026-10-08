from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer
from bashrun.bash import bash, bash_output
from pydantic_settings import BaseSettings

from ci_devkit.builds import build_repository, push_build
from ci_devkit.cache import restore, save
from ci_devkit.ci_step import ci_step
from ci_devkit.setup import configure_git, install_dotnet
from ci_devkit.setup_oras import install_oras
from .identity import builds_registry, cache_key, cache_registry
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
    version_code: Annotated[
        int, typer.Option(help="Android bundleVersionCode (the per-app commit count from get-app-version)")
    ],
    registry: Annotated[str, typer.Option(help="OCI registry root; the verb derives the cache and builds namespaces")],
    pr_number: Annotated[
        str, typer.Option(help="Pull-request number; empty on non-PR runs selects the dev cache scope")
    ] = "",
    license_pin: Annotated[
        str,
        typer.Option(
            "--license", help="License cache pin for this run (the matrix verb's license output; empty uses today's)"
        ),
    ] = "",
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
    parsed_pr_number = int(pr_number) if pr_number else None
    derived_cache_key = cache_key(project, platform, parsed_pr_number)
    library_cache_registry = cache_registry(registry)
    builds_namespace = builds_registry(registry)

    with ci_step("Setup"):
        configure_git(settings.github_workspace)
        install_dotnet("8.0")
        install_oras()
        restore_or_activate_license(library_cache_registry, license_pin or None)
        project_path = resolve_unity_project(project).path
        restore_upm_cache(project_path, library_cache_registry)

    with ci_step("Restore library cache"):
        restore(library_cache_registry, "unity-library", derived_cache_key, Path("."))

    with ci_step(f"Build {project} [{platform}]"):
        build_player(
            project,
            platform,
            version=version,
            version_code=version_code,
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
        save(
            library_cache_registry, "unity-library", derived_cache_key, Path("."), [f"{relative_project_path}/Library/"]
        )

    with ci_step("Save UPM cache"):
        save_upm_cache(project_path, library_cache_registry)

    with ci_step("Collect build artifacts"):
        build_directory = project_path / "Build"
        if build_directory.is_dir():
            artifact_directory = Path("/tmp/unity-builds")
            shutil.rmtree(artifact_directory, ignore_errors=True)
            artifact_directory.mkdir(parents=True)
            report_directory = Path("/tmp/unity-build-reports")
            shutil.rmtree(report_directory, ignore_errors=True)
            if platform == "Linux":
                shutil.copytree(build_directory, artifact_directory, dirs_exist_ok=True)
            else:
                binaries = [file for file in build_directory.rglob("*") if file.suffix in {".apk", ".exe"}]
                if len(binaries) != 1:
                    raise SystemExit(
                        f"build for ({project}, {platform}) must produce exactly one binary, "
                        f"found {len(binaries)} ({', '.join(file.name for file in binaries)})"
                    )
                shutil.copy2(binaries[0], artifact_directory / binaries[0].name)
                for report in build_directory.rglob("BuildReport.json"):
                    destination = report_directory / report.relative_to(build_directory)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(report, destination)

    with ci_step("Push build artifacts"):
        artifact_directory = Path("/tmp/unity-builds")
        if not artifact_directory.is_dir() or not any(artifact_directory.iterdir()):
            print("No build artifacts to push")
        else:
            head_sha = bash_output("git rev-parse HEAD").strip()
            tags = (derived_cache_key, f"sha-{head_sha}")
            if platform == "Linux":
                staging = Path("/tmp/unity-builds-push")
                staging.mkdir(parents=True, exist_ok=True)
                tar_path = staging / "build.tar"
                bash(f"tar -cf {tar_path} -C {artifact_directory} .")
                try:
                    for build_tag in tags:
                        push_build(builds_namespace, project, platform, build_tag, staging, ["build.tar"])
                finally:
                    tar_path.unlink(missing_ok=True)
            else:
                paths = sorted(
                    str(path.relative_to(artifact_directory))
                    for path in artifact_directory.rglob("*")
                    if path.is_file()
                )
                for build_tag in tags:
                    push_build(builds_namespace, project, platform, build_tag, artifact_directory, paths)

                report_directory = Path("/tmp/unity-build-reports")
                if report_directory.is_dir():
                    report_paths = sorted(
                        str(path.relative_to(report_directory)) for path in report_directory.rglob("BuildReport.json")
                    )
                    for build_tag in tags:
                        push_build(
                            builds_namespace, project, f"{platform}-report", build_tag, report_directory, report_paths
                        )
            repository = build_repository(builds_namespace, project, platform)
            print(f"Pushed build artifacts: {repository} ({', '.join(tags)})")
