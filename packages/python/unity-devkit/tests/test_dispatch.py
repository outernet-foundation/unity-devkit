import json
from pathlib import Path

import pytest
import yaml

from unity_devkit.dispatch import (
    EnvironmentDump,
    EnvironmentFieldDump,
    extract_environment_dump,
    render_dispatch_workflow,
)
from unity_devkit.unity import playerbuild_environment, parse_environment_fields

FIXTURE_DUMP = Path(__file__).parent / "fixtures" / "environment-dump.json"
PINNED_BUILD_WORKFLOW = (
    "outernet-foundation/unity-devkit/.github/workflows/unity-build.yml@cfd487e0e19b3d98046a2680a210137ec0d32832"
)


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


def test_render_maps_field_types_to_dispatch_inputs() -> None:
    workflow = render_fixture_workflow()

    assert 'username:\n        description: "environment field username (string)' in workflow
    assert 'verboseLogging:\n        description: "environment field verboseLogging (bool)' in workflow
    assert "type: number" in workflow
    assert "localConfig-apiUrl" in workflow
    assert "inputs['localConfig-apiUrl']" in workflow


def test_render_flags_enum_is_text_not_choice() -> None:
    workflow = render_fixture_workflow()

    assert "comma-separated names" in workflow
    capabilities_choice = "capabilities:\n        description:"
    assert capabilities_choice in workflow
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
        "localConfig-apiUrl",
        "localConfig-portNumber",
    ]
    assert document["jobs"]["build"]["uses"] == PINNED_BUILD_WORKFLOW
    assert document["jobs"]["build"]["secrets"] == "inherit"
    with_block = document["jobs"]["build"]["with"]
    assert with_block["environment-preset"] == "__EXPR_OPEN__ inputs['environment-preset'] __EXPR_CLOSE__"
    assert with_block["development"] == "__EXPR_OPEN__ inputs.development __EXPR_CLOSE__"


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


def test_playerbuild_environment_carries_the_entry_contract() -> None:
    env = playerbuild_environment(
        "AndroidMobile", development=True, environment_preset="airgapped", fields={"username": "bot"}
    )

    assert env == {
        "PLATFORM": "AndroidMobile",
        "DEVELOPMENT": "true",
        "ENVIRONMENT": "airgapped",
        "ENVIRONMENT_FIELDS": '{"username": "bot"}',
    }


def test_playerbuild_environment_without_preset_is_platform_and_development_only() -> None:
    env = playerbuild_environment("Linux", development=False, environment_preset="", fields={})

    assert env == {"PLATFORM": "Linux", "DEVELOPMENT": "false"}
