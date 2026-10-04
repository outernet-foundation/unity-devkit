from __future__ import annotations

import json
from typing import Annotated

import typer

from .license_restore import license_cache_tag
from .player_build import LICENSE_IMAGE_MODULE, PLATFORM_CONFIGS, UNITYCI_IMAGE_REVISION, read_editor_version
from .projects import ProjectEntry, discover_projects

build_app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)
compile_check_app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@build_app.command()
def build_matrix(
    project: Annotated[
        str | None, typer.Option(help="Restrict the matrix to one project (dispatch scoping in multi-app repos)")
    ] = None,
) -> None:
    projects = filtered_projects(project)
    matrix: list[dict[str, str]] = []

    for name, entry in projects.items():
        if not entry.builds:
            continue
        version = read_editor_version(entry.path)
        for platform in entry.builds:
            image_module = PLATFORM_CONFIGS[platform]["unityci_image_module"]
            matrix.append({
                "project-name": name,
                "platform": platform,
                "unityci-image-module": image_module,
                "editor-image": f"unityci/editor:{version}-{image_module}-{UNITYCI_IMAGE_REVISION}",
            })

    if not matrix:
        raise SystemExit(
            "No projects with builds declared — build-unity-matrix needs at least one unity-devkit.json "
            "with a non-empty 'platforms' map"
        )
    print(f"matrix={json.dumps({'include': matrix})}")
    print(f"license={license_cache_tag()}")


@compile_check_app.command()
def compile_check_matrix(
    project: Annotated[
        str | None, typer.Option(help="Restrict the matrix to one project (dispatch scoping in multi-app repos)")
    ] = None,
) -> None:
    projects = filtered_projects(project)
    matrix: list[dict[str, str]] = []

    for name, entry in projects.items():
        version = read_editor_version(entry.path)
        matrix.append({
            "project-name": name,
            "editor-image": f"unityci/editor:{version}-{LICENSE_IMAGE_MODULE}-{UNITYCI_IMAGE_REVISION}",
        })

    print(f"matrix={json.dumps({'include': matrix})}")
    print(f"license={license_cache_tag()}")


def filtered_projects(project: str | None) -> dict[str, ProjectEntry]:
    projects = discover_projects()
    if project is None:
        return projects
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")
    return {project: projects[project]}
