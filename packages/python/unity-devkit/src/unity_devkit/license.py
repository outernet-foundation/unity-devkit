from __future__ import annotations

from typing import Annotated

import typer

from build_artifact_registry.setup_oras import install_oras
from .license_restore import activate_license, restore_or_activate_license

activate_app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@activate_app.command()
def activate_main(
    oras_push: Annotated[
        bool, typer.Option(help="Restore from the ORAS cache on miss and push the activated ULF back")
    ] = False,
    registry: Annotated[str, typer.Option(help="OCI registry namespace for the license cache")] = "",
) -> None:
    install_oras()
    if oras_push:
        if not registry:
            raise SystemExit("--oras-push requires --registry")
        restore_or_activate_license(registry)
    else:
        activate_license()
