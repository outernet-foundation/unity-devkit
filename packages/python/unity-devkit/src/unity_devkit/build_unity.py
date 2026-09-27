from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer
from pydantic_settings import BaseSettings

from ci_devkit.cache import restore, save
from ci_devkit.ci_step import ci_step
from .license_restore import restore_license
from ci_devkit.setup import configure_git, install_dotnet
from ci_devkit.setup_oras import install_oras
from .unity import (
    child_environment,
    parse_environment_fields,
    prepare_unity_project,
    resolve_unity_build,
    run_unity_batchmode,
)
from .versioning import stamp_build_version


class Settings(BaseSettings):
    github_workspace: str


app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def main(
    project: Annotated[str, typer.Option(help="Project name")],
    project_path: Annotated[Path, typer.Option(help="Path to Unity project")],
    platform: Annotated[str, typer.Option(help="Target platform")],
    cache_key: Annotated[str, typer.Option(help="Cache key prefix")],
    registry: Annotated[str, typer.Option(help="OCI registry path")],
    run_number: Annotated[int, typer.Option(help="CI run number")] = 0,
    branch: Annotated[str, typer.Option(help="Git branch name")] = "dev",
    environment_preset: Annotated[
        str, typer.Option(help="Environment preset name; empty leaves the workspace untouched")
    ] = "",
    development: Annotated[str, typer.Option(help="Development build column: 'true' or 'false'")] = "false",
    environment_fields: Annotated[
        str, typer.Option(help="Newline-separated path=value environment field overrides")
    ] = "",
) -> None:
    settings = Settings.model_validate({})

    if development not in ("true", "false"):
        raise SystemExit(f"--development must be 'true' or 'false' — got '{development}'")
    fields = parse_environment_fields(environment_fields.splitlines())

    with ci_step("Setup"):
        configure_git(settings.github_workspace)
        install_dotnet("8.0")
        install_oras()
        restore_license()

    branch_slug = branch.replace("/", "-")
    tag = f"{cache_key}-{platform}-{branch_slug}"
    fallback_branch = "dev"
    fallback_tags = [f"{cache_key}-{platform}-{fallback_branch}"] if branch_slug != fallback_branch else None

    with ci_step("Restore library cache"):
        restore(registry, "unity-library", tag, Path("."), fallback_tags=fallback_tags)

    with ci_step("Prepare build"):
        project_config, build_flag, execute_method, playerbuild_platform = resolve_unity_build(project, platform)
        unity_project_path = project_config.path
        if unity_project_path.resolve() != project_path.resolve():
            raise SystemExit(
                f"--project-path {project_path} does not match catalog entry '{project}' at {unity_project_path}"
            )

    with ci_step("Prepare project"):
        prepare_unity_project(unity_project_path)

    with ci_step(f"Build {project} [{platform}]"):
        tag_prefix = project_config.tag_prefix
        if tag_prefix:
            full_version = stamp_build_version(unity_project_path, tag_prefix, run_number, release=(branch == "main"))
            print(f"Stamped bundleVersion {full_version} (bundleVersionCode={run_number}) into ProjectSettings")

        env = child_environment(playerbuild_platform, development == "true", environment_preset, fields)
        run_unity_batchmode(
            unity_project_path, f"{build_flag} -executeMethod {execute_method}", nographics=False, env=env
        )

    with ci_step("Save library cache"):
        # PackageCache (~1.6 GiB) is redundant with the shared UPM cache at ~/.cache/Unity/upm/
        package_cache = project_path / "Library" / "PackageCache"
        if package_cache.exists():
            shutil.rmtree(package_cache)

        save(registry, "unity-library", tag, Path("."), [f"{project_path}/Library/"])

    with ci_step("Collect build artifacts"):
        build_directory = project_path / "Build"
        if build_directory.is_dir():
            artifact_directory = Path("/tmp/unity-builds")
            artifact_directory.mkdir(parents=True, exist_ok=True)
            if platform == "linux64":
                shutil.copytree(build_directory, artifact_directory, dirs_exist_ok=True)
            else:
                for file in build_directory.rglob("*"):
                    if file.suffix in {".apk", ".exe"}:
                        shutil.copy2(file, artifact_directory / file.name)
