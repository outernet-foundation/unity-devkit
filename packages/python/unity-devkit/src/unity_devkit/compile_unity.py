from pathlib import Path
from typing import Annotated

import typer

from .unity import (
    PLAYERBUILD_ENTRY,
    playerbuild_environment,
    parse_environment_fields,
    prepare_unity_project,
    resolve_unity_build,
    run_unity_batchmode,
)
from .versioning import stamp_build_version

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def compile_unity(
    project: Annotated[str, typer.Option(help="Unity project name (catalog key in unity-devkit.json)")],
    build: Annotated[str, typer.Option(help="Build target from the project's builds list (e.g. AndroidMobile)")],
    version: Annotated[
        str,
        typer.Option(help="Version string to stamp into ProjectSettings.asset; empty builds unversioned"),
    ] = "",
    run_number: Annotated[int, typer.Option(help="bundleVersionCode to stamp; local builds default to 0")] = 0,
    development: Annotated[bool, typer.Option(help="Development build column")] = False,
    environment_preset: Annotated[
        str,
        typer.Option(
            help="Environment preset name (the env class's Presets key); unset leaves the workspace untouched"
        ),
    ] = "",
    environment_field: Annotated[
        list[str] | None,
        typer.Option("--environment-field", help="Environment field override as path=value (repeatable)"),
    ] = None,
) -> None:
    fields = parse_environment_fields(environment_field or [])
    for artifact in build_unity_project(
        project,
        build,
        version=version,
        run_number=run_number,
        development=development,
        environment_preset=environment_preset,
        environment_fields=fields,
    ):
        print(f"Built: {artifact}")


def build_unity_project(
    project: str,
    build: str,
    *,
    version: str = "",
    run_number: int = 0,
    development: bool = False,
    environment_preset: str = "",
    environment_fields: dict[str, str] | None = None,
) -> list[Path]:
    project_config, build_target = resolve_unity_build(project, build)
    project_path = project_config.path
    prepare_unity_project(project_path)

    if version:
        stamped = stamp_build_version(project_path, version, run_number)
        print(f"Stamped bundleVersion {stamped} (bundleVersionCode={run_number}) into ProjectSettings")

    build_directory = project_path / "Build"
    before = snapshot_artifacts(build_directory)

    env = playerbuild_environment(build, development, environment_preset, environment_fields or {})
    run_unity_batchmode(
        project_path,
        f"-buildTarget {build_target} -executeMethod {PLAYERBUILD_ENTRY}",
        nographics=False,
        env=env,
    )

    after = snapshot_artifacts(build_directory)
    produced = sorted(path for path, modification_time in after.items() if before.get(path) != modification_time)
    if not produced:
        raise SystemExit(
            "Unity exited 0 but no .apk/.exe under Build/ was produced or updated — "
            "the incremental build served a stale artifact. Delete the existing "
            "output under Build/ and the project's Library/Bee/.../build/ tree, then retry."
        )
    return produced


def snapshot_artifacts(build_directory: Path) -> dict[Path, int]:
    if not build_directory.is_dir():
        return {}
    return {
        path: path.stat().st_mtime_ns for suffix in (".apk", ".exe") for path in build_directory.rglob(f"*{suffix}")
    }
