from __future__ import annotations

from typing import Annotated

import typer
from pydantic_settings import BaseSettings

from ci_devkit.ci_step import ci_step
from ci_devkit.setup import configure_git
from ci_devkit.setup_oras import install_oras
from .license_restore import restore_or_activate_license
from .player_build import prepare_unity_project, resolve_unity_project, run_unity_batchmode
from .upm_cache import restore_upm_cache, save_upm_cache


class Settings(BaseSettings):
    github_workspace: str


app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

COMPILE_ERROR_SIGNATURES = ("error CS",)


@app.command()
def compile_check_unity(
    project: Annotated[str, typer.Option(help="Unity project name (the 'name' field of its unity-devkit.json)")],
    execute_method: Annotated[
        str | None,
        typer.Option(help="Static method to run after load (Class.Method) — one editor session per invocation"),
    ] = None,
    build_target: Annotated[
        str | None,
        typer.Option(help="Startup build target (e.g. Android) for sessions that must open on a non-default platform"),
    ] = None,
) -> None:
    settings = Settings.model_validate({})
    project_path = resolve_unity_project(project).path

    with ci_step("Setup"):
        configure_git(settings.github_workspace)
        install_oras()
        restore_or_activate_license()
        restore_upm_cache(project_path)

    extra_flags = ""
    if build_target:
        extra_flags += f" -buildTarget {build_target}"
    if execute_method:
        extra_flags += f" -executeMethod {execute_method}"
    print(f"Compile-checking {project}...")
    prepare_unity_project(project_path)
    run_unity_batchmode(project_path, extra_flags, extra_failure_signatures=COMPILE_ERROR_SIGNATURES)
    save_upm_cache(project_path)
    print("  Compiles clean")
