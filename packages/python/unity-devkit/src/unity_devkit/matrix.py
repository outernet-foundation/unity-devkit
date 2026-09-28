import json
from pathlib import Path

from .projects import discover_projects
from .player_build import LICENSE_IMAGE_MODULE, PLATFORM_CONFIGS, UNITYCI_IMAGE_REVISION, read_editor_version


def build_matrix() -> None:
    projects = discover_projects()
    matrix: list[dict[str, str]] = []
    editor_versions: set[str] = set()

    for name, project in projects.items():
        if not project.builds:
            continue
        version = read_editor_version(project.path)
        editor_versions.add(version)
        for platform in project.builds:
            image_module = PLATFORM_CONFIGS[platform]["unityci_image_module"]
            matrix.append({
                "project": str(project.path.relative_to(Path.cwd())),
                "project-name": name,
                "cache-key": name.lower(),
                "platform": platform,
                "unityci-image-module": image_module,
                "editor-image": f"unityci/editor:{version}-{image_module}-{UNITYCI_IMAGE_REVISION}",
            })

    if not editor_versions:
        raise SystemExit(
            "No projects with builds declared — build-unity-matrix needs at least one unity-devkit.json with a non-empty 'platforms' map"
        )
    license_version = max(editor_versions)
    print(f"matrix={json.dumps({'include': matrix})}")
    print(f"license-image=unityci/editor:{license_version}-{LICENSE_IMAGE_MODULE}-{UNITYCI_IMAGE_REVISION}")


def compile_check_matrix() -> None:
    projects = discover_projects()
    matrix: list[dict[str, str]] = []
    editor_versions: set[str] = set()

    for name, project in projects.items():
        version = read_editor_version(project.path)
        editor_versions.add(version)
        matrix.append({
            "project-name": name,
            "editor-image": f"unityci/editor:{version}-{LICENSE_IMAGE_MODULE}-{UNITYCI_IMAGE_REVISION}",
        })

    print(f"matrix={json.dumps({'include': matrix})}")
    print(f"license-image=unityci/editor:{max(editor_versions)}-{LICENSE_IMAGE_MODULE}-{UNITYCI_IMAGE_REVISION}")
