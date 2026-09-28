import json
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel, ConfigDict

from .compile_check_unity import COMPILE_ERROR_SIGNATURES
from .projects import discover_projects
from .player_build import prepare_unity_project, run_unity_batchmode

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

DUMP_EXECUTE_METHOD = "Outernet.PlayerBuild.DumpEnvironment"
DISPATCH_INPUT_CAP = 25
RESERVED_INPUT_IDS = frozenset({"environment-preset", "development"})
NUMERIC_FIELD_TYPES = {
    "Byte",
    "SByte",
    "Int16",
    "UInt16",
    "Int32",
    "UInt32",
    "Int64",
    "UInt64",
    "Single",
    "Double",
    "Decimal",
}


class EnvironmentEnum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    values: list[str]
    flags: bool


class EnvironmentFieldDump(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    field_type: str


class EnvironmentDump(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: str
    mode_field: str
    target_path: str
    presets: dict[str, str]
    enums: list[EnvironmentEnum]
    fields: list[EnvironmentFieldDump]


@app.command()
def unity_dispatch(
    project: Annotated[str, typer.Option(help="Unity project name (the 'name' field of its unity-devkit.json)")],
    output: Annotated[Path, typer.Option(help="Workflow file to write (or check with --check)")],
    build_workflow: Annotated[
        str,
        typer.Option(
            help="The build job's uses: value — the consumer's pinned build-unity-internal.yml reference "
            "(owner/repo/.github/workflows/build-unity-internal.yml@sha, or ./.github/workflows/build-unity-internal.yml inside unity-devkit)"
        ),
    ],
    environment_config_class: Annotated[
        str | None,
        typer.Option(help="Env class file path override (defaults to unity-devkit.json's environment_config)"),
    ] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Compare against the existing file instead of writing; fail on drift")
    ] = False,
) -> None:
    projects = discover_projects()
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")

    project_path = projects[project].path
    env = {"ENVIRONMENT_CONFIG_CLASS": environment_config_class} if environment_config_class else None
    print(f"Dumping environment of {project}...")
    prepare_unity_project(project_path)
    log_path = run_unity_batchmode(
        project_path,
        f"-executeMethod {DUMP_EXECUTE_METHOD}",
        extra_failure_signatures=COMPILE_ERROR_SIGNATURES,
        env=env,
    )
    dump = extract_environment_dump(log_path)
    workflow = render_dispatch_workflow(dump, project=project, output=output.as_posix(), build_workflow=build_workflow)

    if check:
        if not output.is_file():
            raise SystemExit(f"Dispatch workflow drift: {output} does not exist — generate it")
        committed = output.read_text(encoding="utf-8")
        if committed != workflow:
            raise SystemExit(
                f"Dispatch workflow drift: {output} differs from the environment class — regenerate with "
                f"'{regen_command(project, output.as_posix(), build_workflow)}'"
            )
        print(f"  {output} matches the environment class")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(workflow, encoding="utf-8")
    print(f"  wrote {output}")


def extract_environment_dump(log_path: Path) -> EnvironmentDump:
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "class_name" in payload:
            return EnvironmentDump.model_validate(payload)

    raise SystemExit(f"No environment dump JSON found in the editor log at {log_path}")


def render_dispatch_workflow(dump: EnvironmentDump, *, project: str, output: str, build_workflow: str) -> str:
    enums_by_name = {environment_enum.name: environment_enum for environment_enum in dump.enums}
    emitted_fields = [field for field in dump.fields if field.path != dump.mode_field]
    leaf_counts = Counter(field.path.rsplit(".", 1)[-1] for field in emitted_fields)
    input_ids: dict[str, str] = {}
    for field in emitted_fields:
        leaf = field.path.rsplit(".", 1)[-1]
        input_ids[field.path] = (
            leaf if leaf_counts[leaf] == 1 and leaf not in RESERVED_INPUT_IDS else field.path.replace(".", "-")
        )
    default_preset = next(iter(dump.presets), "")
    input_blocks: list[tuple[str, str | None, list[str], str | None]] = [
        (
            "environment-preset",
            "Preset to apply — blank leaves the workspace untouched; leave fields empty to keep the preset's values",
            ["type: choice", "options:", *indent_lines([*(f'- "{preset}"' for preset in ("", *dump.presets))], 2)],
            f'default: "{default_preset}"',
        ),
        ("development", "Development build (debug symbols)", ["type: boolean"], "default: false"),
    ]
    for field in emitted_fields:
        input_blocks.append(field_input_block(field, input_ids[field.path], enums_by_name))

    input_count = len(input_blocks)
    if input_count > DISPATCH_INPUT_CAP:
        raise SystemExit(
            f"Dispatch panel would carry {input_count} inputs — GitHub's workflow_dispatch cap is {DISPATCH_INPUT_CAP}. "
            "Shrink the env class or move configuration out of it."
        )

    transport_lines = [field_transport_line(field, input_ids[field.path]) for field in emitted_fields]
    header = (
        f"# Generated by '{regen_command(project, output, build_workflow)}' from the environment class "
        f"{dump.class_name} —"
    )

    workflow_call_input_blocks: list[tuple[str, str | None, list[str], str | None]] = [
        ("runner-labels", "JSON-encoded runs-on value", ["type: string"], "default: '\"ubuntu-latest\"'"),
        ("version", "Version string to stamp; empty builds unversioned", ["type: string"], "default: ''"),
    ]

    lines = [
        header,
        "# edit the class, then regenerate this workflow.",
        "name: Unity Dispatch Build",
        "",
        "on:",
        "  workflow_dispatch:",
        "    inputs:",
        *indent_lines([line for block in input_blocks for line in build_input_block(block)], 6),
        "  workflow_call:",
        "    inputs:",
        *indent_lines([line for block in workflow_call_input_blocks for line in build_input_block(block)], 6),
        "",
        "jobs:",
        "  build:",
        f"    uses: {build_workflow}",
        "    with:",
        "      runner-labels: ${{ inputs.runner-labels || '\"ubuntu-latest\"' }}",
        "      version: ${{ inputs.version || '' }}",
        "      environment-preset: ${{ inputs['environment-preset'] || '' }}",
        "      development: ${{ inputs.development || false }}",
    ]
    if transport_lines:
        lines.append("      environment-fields: |-")
        lines.extend(indent_lines(transport_lines, 8))
    else:
        lines.append("      environment-fields: ''")
    lines.append("    secrets: inherit")
    return "\n".join(lines) + "\n"


def regen_command(project: str, output: str, build_workflow: str) -> str:
    return f"uv run unity-dispatch --project {project} --output {output} --build-workflow {build_workflow}"


def field_input_block(
    field: EnvironmentFieldDump, input_id: str, enums_by_name: dict[str, EnvironmentEnum]
) -> tuple[str, str | None, list[str], str | None]:
    if field.field_type == "Boolean":
        return (input_id, None, ["type: boolean"], "default: false")

    if field.field_type in enums_by_name:
        environment_enum = enums_by_name[field.field_type]
        if environment_enum.flags:
            return (
                input_id,
                f"comma-separated: {', '.join(environment_enum.values)}",
                ["type: string"],
                'default: ""',
            )
        return (
            input_id,
            None,
            [
                "type: choice",
                "options:",
                *indent_lines([*(f'- "{value}"' for value in ("", *environment_enum.values))], 2),
            ],
            'default: ""',
        )

    if field.field_type == "String":
        return (input_id, None, ["type: string"], 'default: ""')

    if field.field_type in NUMERIC_FIELD_TYPES:
        return (input_id, None, ["type: number"], None)

    raise SystemExit(
        f"Environment field '{field.path}' has type '{field.field_type}' — no dispatch input type maps to it "
        "(arrays and object references self-exclude from the dump; this is contract drift)"
    )


def field_transport_line(field: EnvironmentFieldDump, input_id: str) -> str:
    guard = "" if field.field_type == "Boolean" else " != ''"
    return (
        "${{ inputs['"
        + input_id
        + "']"
        + guard
        + " && format('"
        + field.path
        + "={0}', inputs['"
        + input_id
        + "']) || '' }}"
    )


def build_input_block(input_block: tuple[str, str | None, list[str], str | None]) -> list[str]:
    input_id, description, type_lines, default_line = input_block
    lines = [f"{input_id}:"]
    if description is not None:
        lines.append(f'  description: "{description}"')
    lines.extend(f"  {line}" for line in type_lines)
    if default_line is not None:
        lines.append(f"  {default_line}")
    return lines


def indent_lines(lines: list[str], spaces: int) -> list[str]:
    return [f"{' ' * spaces}{line}" if line else line for line in lines]
