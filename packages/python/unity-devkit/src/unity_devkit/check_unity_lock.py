import json
from pathlib import Path
from typing import Annotated, Any

import typer

from .projects import discover_projects

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def check_unity_lock(project: Annotated[str | None, typer.Option(help="Limit to a specific project.")] = None) -> None:
    config = discover_projects()

    if project is not None and project not in config:
        raise typer.BadParameter(f"Unknown project '{project}'. Valid: {', '.join(config)}")

    projects = {project: config[project]} if project else config
    failures: list[str] = []

    for name, project_config in projects.items():
        print(f"Checking {name} ({project_config.path / 'Packages' / 'packages-lock.json'})...")
        failures.extend(check_project_lock(name, project_config.path))

    if failures:
        for failure in failures:
            print(f"  {failure}")

        raise SystemExit(
            "packages-lock.json disagrees with Packages/manifest.json — run 'uv run lock-unity' "
            "to regenerate the lock, then commit it."
        )

    print("Every packages-lock.json agrees with its manifest.")


def check_project_lock(name: str, project_path: Path) -> list[str]:
    packages_directory = project_path / "Packages"
    manifest_path = packages_directory / "manifest.json"
    lock_path = packages_directory / "packages-lock.json"

    if not manifest_path.is_file():
        return [f"{name}: {manifest_path} does not exist"]

    if not lock_path.is_file():
        return [f"{name}: {lock_path} does not exist — run 'uv run lock-unity' to generate it."]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{name}: unparseable manifest/lock JSON: {error.msg} at line {error.lineno}"]

    requirements: dict[str, Any] = manifest.get("dependencies", {})
    locked: dict[str, Any] = lock.get("dependencies", {})

    failures: list[str] = []

    for package, requirement in sorted(requirements.items()):
        entry = locked.get(package)

        if entry is None:
            failures.append(f"{name}: '{package}' ({requirement}) is absent from packages-lock.json")
        elif entry.get("version") != requirement:
            failures.append(f"{name}: '{package}' manifest wants {requirement}, lock recorded {entry.get('version')}")

    return failures
