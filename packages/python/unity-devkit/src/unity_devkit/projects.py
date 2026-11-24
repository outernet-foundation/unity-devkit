import os
from collections.abc import Iterator
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

BUILD_CONFIG_FILENAME = "unity-devkit.json"
PROJECT_MARKER = Path("ProjectSettings") / "ProjectVersion.txt"
PRUNE_DIRECTORIES = {".git", "Library", "Temp", "obj", "Build", "node_modules", "__pycache__"}


class PlatformConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    render_pipeline: str = ""


class BuildConfigFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    entry: str | None = None
    platforms: dict[str, PlatformConfig] | None = None

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("unity-devkit.json 'name' must be a non-empty string")
        return value

    @model_validator(mode="after")
    def entry_required_with_platforms(self) -> Self:
        if self.platforms and not self.entry:
            raise ValueError(
                "unity-devkit.json declares 'platforms' — an 'entry' executeMethod is required "
                "(a public static parameterless method the build invokes)"
            )
        return self


class ProjectEntry(BaseModel):
    path: Path
    entry: str | None = None
    platforms: dict[str, PlatformConfig] | None = None

    @property
    def builds(self) -> list[str] | None:
        return list(self.platforms) if self.platforms else None


def discover_projects() -> dict[str, ProjectEntry]:
    root = Path.cwd()
    discovered: dict[str, ProjectEntry] = {}
    first_seen: dict[str, Path] = {}

    for directory in visible_directories(root):
        config_path = directory / BUILD_CONFIG_FILENAME
        if not config_path.is_file():
            continue
        if not (directory / PROJECT_MARKER).is_file():
            raise SystemExit(
                f"{config_path} sits in {directory}, which is not a Unity project: missing {PROJECT_MARKER}"
            )
        parsed = BuildConfigFile.model_validate_json(config_path.read_text(encoding="utf-8"))
        if parsed.name in discovered:
            raise SystemExit(
                f"Duplicate project name '{parsed.name}' — declared at {config_path} "
                f"and previously at {first_seen[parsed.name]}"
            )
        first_seen[parsed.name] = config_path
        discovered[parsed.name] = ProjectEntry(path=directory, entry=parsed.entry, platforms=parsed.platforms)

    if not discovered:
        raise SystemExit(
            f"No {BUILD_CONFIG_FILENAME} found under {root} — declare Unity projects with a "
            f"{BUILD_CONFIG_FILENAME} per project root (carrying a 'name' field; 'platforms' "
            "keys are the build targets)"
        )
    return discovered


def visible_directories(root: Path) -> Iterator[Path]:
    for directory, subdirectories, _filenames in os.walk(root):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in PRUNE_DIRECTORIES and not name.startswith(".")
        )
        yield Path(directory)


def directories_containing(root: Path, filename: str) -> list[Path]:
    return [directory for directory in visible_directories(root) if (directory / filename).is_file()]
