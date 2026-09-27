from typing import Annotated

import typer

from .player_build import build_player, parse_environment_fields

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def build_unity(
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
    for artifact in build_player(
        project,
        build,
        version=version,
        run_number=run_number,
        development=development,
        environment_preset=environment_preset,
        environment_fields=fields,
    ):
        print(f"Built: {artifact}")
