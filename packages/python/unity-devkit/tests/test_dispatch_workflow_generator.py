import json
from pathlib import Path

import pytest
import yaml

from unity_devkit.dispatch_workflow_generator import (
    EnvironmentDump,
    EnvironmentFieldDump,
    extract_environment_dump,
    render_dispatch_workflow,
)
from unity_devkit.player_build import parse_environment_fields

FIXTURE_DUMP = Path(__file__).parent / "fixtures" / "environment-dump.json"
PINNED_BUILD_WORKFLOW = "outernet-foundation/unity-devkit/.github/workflows/build-unity-internal.yml@cfd487e0e19b3d98046a2680a210137ec0d32832"


def load_fixture_dump() -> EnvironmentDump:
    return EnvironmentDump.model_validate(json.loads(FIXTURE_DUMP.read_text(encoding="utf-8")))


def render_fixture_workflow() -> str:
    return render_dispatch_workflow(
        load_fixture_dump(),
        project="PlayerBuild",
        output=".github/workflows/build.yml",
        build_workflow=PINNED_BUILD_WORKFLOW,
    )


def test_render_modes_are_deduped_into_the_preset_choice() -> None:
    workflow = render_fixture_workflow()

    assert "configMode:" not in workflow
    assert 'options:\n          - ""\n          - "Airgapped"' in workflow


def test_render_defaults_the_preset_choice_to_the_first_map_key() -> None:
    document = yaml.safe_load(render_fixture_workflow().replace("${{", "__EXPR_OPEN__").replace("}}", "__EXPR_CLOSE__"))

    trigger = document.get("on", document[True])
    preset = trigger["workflow_dispatch"]["inputs"]["environment-preset"]
    assert preset["options"] == ["", "Airgapped"]
    assert preset["default"] == "Airgapped"


def test_render_states_the_override_law_once_on_the_preset_input() -> None:
    workflow = render_fixture_workflow()

    assert "environment field" not in workflow
    assert "empty keeps the preset value" not in workflow
    assert "checked overrides the preset value" not in workflow
    assert workflow.count("description:") == 5


def test_render_maps_field_types_to_dispatch_inputs_without_descriptions() -> None:
    workflow = render_fixture_workflow()

    assert "\n      username:\n        type: string" in workflow
    assert "\n      verboseLogging:\n        type: boolean" in workflow
    assert "\n      pollIntervalSeconds:\n        type: number" in workflow


def test_render_uses_leaf_names_as_input_ids_when_unique() -> None:
    workflow = render_fixture_workflow()

    assert "\n      apiUrl:" in workflow
    assert "\n      portNumber:" in workflow
    assert "localConfig-apiUrl" not in workflow
    assert "${{ inputs['apiUrl'] != '' && format('localConfig.apiUrl={0}', inputs['apiUrl']) || '' }}" in workflow


def test_render_falls_back_to_dashed_paths_on_leaf_collision() -> None:
    dump = load_fixture_dump()
    dump.fields.append(EnvironmentFieldDump(path="remoteConfig.apiUrl", field_type="String"))

    workflow = render_dispatch_workflow(
        dump, project="PlayerBuild", output=".github/workflows/build.yml", build_workflow=PINNED_BUILD_WORKFLOW
    )

    assert "\n      apiUrl:" not in workflow
    assert "\n      localConfig-apiUrl:" in workflow
    assert "\n      remoteConfig-apiUrl:" in workflow


def test_render_falls_back_to_dashed_paths_on_control_id_collision() -> None:
    dump = load_fixture_dump()
    dump.fields.append(EnvironmentFieldDump(path="misc.development", field_type="Boolean"))

    workflow = render_dispatch_workflow(
        dump, project="PlayerBuild", output=".github/workflows/build.yml", build_workflow=PINNED_BUILD_WORKFLOW
    )

    assert "\n      misc-development:" in workflow
    assert workflow.split("jobs:")[0].count("\n      development:") == 1


def test_render_flags_enum_is_text_not_choice() -> None:
    workflow = render_fixture_workflow()

    assert 'description: "comma-separated: None, Capture, Stream, Analyze"' in workflow
    assert "\n      capabilities:\n        description:" in workflow
    assert "\n      capabilities:\n        type: string" not in workflow
    assert "type: choice" in workflow


def test_render_transports_booleans_only_when_checked() -> None:
    workflow = render_fixture_workflow()

    assert "${{ inputs['verboseLogging'] && format('verboseLogging={0}', inputs['verboseLogging']) || '' }}" in workflow


def test_render_transports_empty_as_unset() -> None:
    workflow = render_fixture_workflow()

    assert "${{ inputs['username'] != '' && format('username={0}', inputs['username']) || '' }}" in workflow


def test_render_rejects_unknown_field_type() -> None:
    dump = load_fixture_dump()
    dump.fields.append(EnvironmentFieldDump(path="weird", field_type="Byte[]"))

    with pytest.raises(SystemExit, match="no dispatch input type maps"):
        render_dispatch_workflow(
            dump, project="PlayerBuild", output=".github/workflows/build.yml", build_workflow=PINNED_BUILD_WORKFLOW
        )


def test_render_enforces_the_dispatch_input_cap() -> None:
    dump = load_fixture_dump()
    dump.fields.extend(EnvironmentFieldDump(path=f"extra{index}", field_type="String") for index in range(25))

    with pytest.raises(SystemExit, match="cap is 25"):
        render_dispatch_workflow(
            dump, project="PlayerBuild", output=".github/workflows/build.yml", build_workflow=PINNED_BUILD_WORKFLOW
        )


def test_render_is_deterministic() -> None:
    assert render_fixture_workflow() == render_fixture_workflow()


def test_rendered_workflow_is_valid_yaml() -> None:
    document = yaml.safe_load(render_fixture_workflow().replace("${{", "__EXPR_OPEN__").replace("}}", "__EXPR_CLOSE__"))

    trigger = document.get("on", document[True])
    inputs = trigger["workflow_dispatch"]["inputs"]
    assert list(inputs) == [
        "environment-preset",
        "development",
        "username",
        "password",
        "verboseLogging",
        "pollIntervalSeconds",
        "capabilities",
        "apiUrl",
        "portNumber",
    ]
    call_inputs = trigger["workflow_call"]["inputs"]
    assert list(call_inputs) == ["runner-labels", "version"]
    assert call_inputs["runner-labels"]["type"] == "string"
    assert call_inputs["runner-labels"]["default"] == '"ubuntu-latest"'
    assert call_inputs["version"]["type"] == "string"
    assert call_inputs["version"]["default"] == ""
    assert document["jobs"]["build"]["uses"] == PINNED_BUILD_WORKFLOW
    assert document["jobs"]["build"]["secrets"] == "inherit"
    with_block = document["jobs"]["build"]["with"]
    assert with_block["runner-labels"] == "__EXPR_OPEN__ inputs.runner-labels || '\"ubuntu-latest\"' __EXPR_CLOSE__"
    assert with_block["version"] == "__EXPR_OPEN__ inputs.version || '' __EXPR_CLOSE__"
    assert with_block["environment-preset"] == "__EXPR_OPEN__ inputs['environment-preset'] || '' __EXPR_CLOSE__"
    assert with_block["development"] == "__EXPR_OPEN__ inputs.development || false __EXPR_CLOSE__"


def test_render_with_block_uses_or_defaults_for_dual_trigger_support() -> None:
    workflow = render_fixture_workflow()

    assert "runner-labels: ${{ inputs.runner-labels || '\"ubuntu-latest\"' }}" in workflow
    assert "version: ${{ inputs.version || '' }}" in workflow
    assert "environment-preset: ${{ inputs['environment-preset'] || '' }}" in workflow
    assert "development: ${{ inputs.development || false }}" in workflow


def test_render_header_embeds_the_full_regen_command() -> None:
    header = render_fixture_workflow().splitlines()[0]

    assert (
        f"uv run unity-dispatch --project PlayerBuild --output .github/workflows/build.yml "
        f"--build-workflow {PINNED_BUILD_WORKFLOW}" in header
    )


def test_extract_from_log_text(tmp_path: Path) -> None:
    log_path = tmp_path / "editor.log"
    log_path.write_text(
        "Refreshing native plugins\n"
        '{"class_name":"Outernet.FixtureEnv","mode_field":"configMode","target_path":"t","presets":{},'
        '"enums":[],"fields":[]}\n'
        "at Outernet.EnvironmentConfig.Dump () [0x00000]\n",
        encoding="utf-8",
    )

    dump = extract_environment_dump(log_path)

    assert dump.class_name == "Outernet.FixtureEnv"
    assert dump.presets == {}


def test_extract_fails_loudly_without_payload(tmp_path: Path) -> None:
    log_path = tmp_path / "editor.log"
    log_path.write_text("nothing to see here\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="No environment dump JSON"):
        extract_environment_dump(log_path)


def test_parse_environment_fields_splits_on_first_equals() -> None:
    fields = parse_environment_fields(["username=bot", "localConfig.apiUrl=https://x/?a=b", "", "  "])

    assert fields == {"username": "bot", "localConfig.apiUrl": "https://x/?a=b"}


def test_parse_environment_fields_rejects_bare_path() -> None:
    with pytest.raises(SystemExit, match="expected path=value"):
        parse_environment_fields(["username"])
