import re
from pathlib import Path


def stamp_build_version(project_path: Path, version: str, run_number: int) -> str:
    settings_path = project_path / "ProjectSettings" / "ProjectSettings.asset"
    rewritten = replace_serialized_field(
        replace_serialized_field(
            settings_path.read_text(encoding="utf-8"), "AndroidBundleVersionCode", str(run_number)
        ),
        "bundleVersion",
        version,
    )
    settings_path.write_text(rewritten, encoding="utf-8")
    return version


def replace_serialized_field(text: str, field_name: str, value: str) -> str:
    pattern = re.compile(rf"^(?P<indent>[ \t]*){field_name}:.*$", re.MULTILINE)
    rewritten, count = pattern.subn(lambda match: f"{match.group('indent')}{field_name}: {value}", text)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one '{field_name}:' field in ProjectSettings.asset, found {count} — "
            "the serialized shape changed; refusing to stamp"
        )
    return rewritten
