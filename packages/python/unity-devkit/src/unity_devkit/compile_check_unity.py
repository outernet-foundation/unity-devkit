from typing import Annotated

import typer

from .unity import prepare_unity_project, resolve_unity_project, run_unity_batchmode

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

COMPILE_ERROR_SIGNATURES = ("error CS",)


@app.command()
def compile_check_unity(
    project: Annotated[str, typer.Option(help="Unity project name (catalog key in unity-devkit.json)")],
    execute_method: Annotated[
        str | None,
        typer.Option(help="Static method to run after load (Class.Method) — one editor session per invocation"),
    ] = None,
    build_target: Annotated[
        str | None,
        typer.Option(help="Startup build target (e.g. Android) for sessions that must open on a non-default platform"),
    ] = None,
) -> None:
    project_path = resolve_unity_project(project).path
    extra_flags = ""
    if build_target:
        extra_flags += f" -buildTarget {build_target}"
    if execute_method:
        extra_flags += f" -executeMethod {execute_method}"
    print(f"Compile-checking {project}...")
    prepare_unity_project(project_path)
    run_unity_batchmode(project_path, extra_flags, extra_failure_signatures=COMPILE_ERROR_SIGNATURES)
    print("  Compiles clean")
