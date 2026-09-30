from __future__ import annotations

from typing import Annotated

import typer
from pydantic_settings import BaseSettings

from ci_devkit.setup import configure_git
from ci_devkit.setup_oras import install_oras
from .license_restore import activate_license, restore_or_activate_license


class Settings(BaseSettings):
    github_workspace: str


settings = Settings.model_validate({})
activate_app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@activate_app.command()
def activate_main(
    oras_push: Annotated[
        bool, typer.Option(help="Restore from the ORAS cache on miss and push the activated ULF back")
    ] = False,
) -> None:
    configure_git(settings.github_workspace)
    install_oras()
    if oras_push:
        restore_or_activate_license()
    else:
        activate_license()
