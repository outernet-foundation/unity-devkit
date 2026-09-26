from typing import Annotated

import typer

from .projects import load_catalog
from .unity import prepare_unity_project, run_unity_batchmode

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

COMPILE_ERROR_SIGNATURES = ("error CS",)


@app.command()
def check_unity(
    project: Annotated[str, typer.Option(help="Unity project name (catalog key in unity-devkit.json)")],
) -> None:
    projects = load_catalog()
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")

    project_path = projects[project].path
    print(f"Compile-checking {project}...")
    prepare_unity_project(project_path)
    run_unity_batchmode(project_path, extra_failure_signatures=COMPILE_ERROR_SIGNATURES)
    print("  Compiles clean")
