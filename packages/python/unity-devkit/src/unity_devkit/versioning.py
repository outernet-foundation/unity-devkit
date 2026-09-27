import re
from pathlib import Path

from bashrun.bash import bash_output


def stamp_build_version(project_path: Path, tag_prefix: str, run_number: int, *, release: bool) -> str:
    version = latest_tag_version(f"{tag_prefix}-v") or "0.0.0"
    full_version = f"{version}+{run_number}" if release else f"{version}-dev+{run_number}"
    settings_path = project_path / "ProjectSettings" / "ProjectSettings.asset"
    rewritten = replace_serialized_field(
        replace_serialized_field(
            settings_path.read_text(encoding="utf-8"), "AndroidBundleVersionCode", str(run_number)
        ),
        "bundleVersion",
        full_version,
    )
    settings_path.write_text(rewritten, encoding="utf-8")
    return full_version


def latest_tag_version(prefix: str) -> str | None:
    output = bash_output(f'git tag --list "{prefix}*" --sort=-v:refname').strip()
    if not output:
        return None
    return output.splitlines()[0][len(prefix) :]


def replace_serialized_field(text: str, field_name: str, value: str) -> str:
    pattern = re.compile(rf"^(?P<indent>[ \t]*){field_name}:.*$", re.MULTILINE)
    rewritten, count = pattern.subn(lambda match: f"{match.group('indent')}{field_name}: {value}", text)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one '{field_name}:' field in ProjectSettings.asset, found {count} — "
            "the serialized shape changed; refusing to stamp"
        )
    return rewritten
