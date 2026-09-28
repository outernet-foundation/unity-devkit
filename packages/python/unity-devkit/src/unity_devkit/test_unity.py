from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .projects import discover_projects
from .player_build import run_unity_batchmode

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def main(
    project: Annotated[str, typer.Option(help="Unity project name (the 'name' field of its build-config.json)")],
    test_platform: Annotated[str, typer.Option(help="Unity test platform (EditMode or PlayMode)")] = "EditMode",
    results: Annotated[Path, typer.Option(help="Output path for NUnit XML results")] = Path(
        "artifacts/unity-test-results.xml"
    ),
) -> None:
    projects = discover_projects()
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")

    project_path = projects[project].path
    results.parent.mkdir(parents=True, exist_ok=True)

    run_unity_batchmode(
        project_path, f"-runTests -testPlatform {test_platform} -testResults {results.resolve()}", auto_quit=False
    )
