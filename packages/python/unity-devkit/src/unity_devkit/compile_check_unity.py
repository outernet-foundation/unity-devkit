from __future__ import annotations

from typing import Annotated

import typer

from build_artifact_registry.setup_oras import install_oras
from .identity import cache_registry
from .license_restore import restore_or_activate_license
from .player_build import prepare_unity_project, resolve_unity_project, run_unity_batchmode
from .upm_cache import restore_upm_cache, save_upm_cache

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

COMPILE_ERROR_SIGNATURES = ("error CS",)


@app.command()
def compile_check_unity(
    project: Annotated[str, typer.Option(help="Unity project name (the 'name' field of its unity-devkit.json)")],
    license_cache_key: Annotated[
        str,
        typer.Option("--license-cache-key", help="ORAS tag the license cache restores under; empty uses today's tag"),
    ] = "",
    registry: Annotated[str, typer.Option(help="OCI registry root; the verb derives the cache namespace")] = "",
    execute_method: Annotated[
        str | None,
        typer.Option(help="Static method to run after load (Class.Method) — one editor session per invocation"),
    ] = None,
    build_target: Annotated[
        str | None,
        typer.Option(help="Startup build target (e.g. Android) for sessions that must open on a non-default platform"),
    ] = None,
) -> None:
    if not registry:
        raise SystemExit("compile-check needs --registry (the OCI registry root)")
    project_path = resolve_unity_project(project).path
    cache_namespace = cache_registry(registry)

    install_oras()
    restore_or_activate_license(cache_namespace, license_cache_key or None)
    restore_upm_cache(project_path, cache_namespace)

    extra_flags = ""
    if build_target:
        extra_flags += f" -buildTarget {build_target}"
    if execute_method:
        extra_flags += f" -executeMethod {execute_method}"
    print(f"Compile-checking {project}...")
    prepare_unity_project(project_path)
    run_unity_batchmode(project_path, extra_flags, extra_failure_signatures=COMPILE_ERROR_SIGNATURES)
    save_upm_cache(project_path, cache_namespace)
    print("  Compiles clean")
