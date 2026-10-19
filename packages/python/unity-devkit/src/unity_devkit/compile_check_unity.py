from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer

from build_artifact_registry.cache import restore, save
from build_artifact_registry.setup_oras import install_oras
from .identity import cache_key, cache_registry
from .license_restore import restore_or_activate_license
from .player_build import prepare_unity_project, resolve_unity_project, run_unity_batchmode
from .upm_cache import restore_upm_cache, save_upm_cache

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

COMPILE_ERROR_SIGNATURES = ("error CS",)
COMPILE_CACHE_SCOPE = "compile"


@app.command()
def compile_check_unity(
    project: Annotated[str, typer.Option(help="Unity project name (the 'name' field of its unity-devkit.json)")],
    pr_number: Annotated[
        str, typer.Option(help="Pull-request number; empty on non-PR runs selects the dev library-cache scope")
    ] = "",
    license_cache_key: Annotated[
        str,
        typer.Option("--license-cache-key", help="ORAS tag the license cache restores under; empty uses today's tag"),
    ] = "",
    registry: Annotated[str, typer.Option(help="OCI registry root; the verb derives the cache namespace")] = "",
) -> None:
    if not registry:
        raise SystemExit("compile-check needs --registry (the OCI registry root)")
    project_path = resolve_unity_project(project).path
    cache_namespace = cache_registry(registry)
    parsed_pr_number = int(pr_number) if pr_number else None
    library_cache_key = cache_key(project, COMPILE_CACHE_SCOPE, parsed_pr_number)

    install_oras()
    restore_or_activate_license(cache_namespace, license_cache_key or None)
    restore_upm_cache(project_path, cache_namespace)
    restore(
        cache_namespace,
        "unity-library",
        library_cache_key,
        Path("."),
        fallback_tags=[cache_key(project, COMPILE_CACHE_SCOPE, None)] if parsed_pr_number is not None else None,
    )

    print(f"Compile-checking {project}...")
    prepare_unity_project(project_path)
    run_unity_batchmode(project_path, extra_failure_signatures=COMPILE_ERROR_SIGNATURES)

    package_cache = project_path / "Library" / "PackageCache"
    if package_cache.exists():
        shutil.rmtree(package_cache)
    relative_project_path = project_path.relative_to(Path.cwd())
    save(cache_namespace, "unity-library", library_cache_key, Path("."), [f"{relative_project_path}/Library/"])
    save_upm_cache(project_path, cache_namespace)
    print("  Compiles clean")
