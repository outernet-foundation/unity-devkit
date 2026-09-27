import re
from pathlib import Path

from .unity import (
    PLAYERBUILD_ENTRY,
    playerbuild_environment,
    prepare_unity_project,
    resolve_unity_build,
    run_unity_batchmode,
)


def build_player(
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
        settings_path = project_path / "ProjectSettings" / "ProjectSettings.asset"
        rewritten = settings_path.read_text(encoding="utf-8")
        for field_name, value in (("AndroidBundleVersionCode", str(run_number)), ("bundleVersion", version)):
            rewritten = replace_serialized_field(rewritten, field_name, value)
        settings_path.write_text(rewritten, encoding="utf-8")
        print(f"Stamped bundleVersion {version} (bundleVersionCode={run_number}) into ProjectSettings")

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
            "Unity exited 0 but no .apk/.exe/.x86_64 under Build/ was produced or updated — "
            "the incremental build served a stale artifact. Delete the existing "
            "output under Build/ and the project's Library/Bee/.../build/ tree, then retry."
        )
    return produced


def replace_serialized_field(text: str, field_name: str, value: str) -> str:
    pattern = re.compile(rf"^(?P<indent>[ \t]*){field_name}:.*$", re.MULTILINE)
    rewritten, count = pattern.subn(lambda match: f"{match.group('indent')}{field_name}: {value}", text)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one '{field_name}:' field in ProjectSettings.asset, found {count} — "
            "the serialized shape changed; refusing to stamp"
        )
    return rewritten


def snapshot_artifacts(build_directory: Path) -> dict[Path, int]:
    if not build_directory.is_dir():
        return {}
    return {
        path: path.stat().st_mtime_ns
        for suffix in (".apk", ".exe", ".x86_64")
        for path in build_directory.rglob(f"*{suffix}")
    }
