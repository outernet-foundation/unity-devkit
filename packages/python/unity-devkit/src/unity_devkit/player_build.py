import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

from bashrun.bash import CalledProcessError, bash, bash_pipe

from .projects import ProjectEntry, discover_projects


class PlatformConfig(TypedDict):
    build_target: str
    unityci_image_module: str


PLATFORM_CONFIGS: dict[str, PlatformConfig] = {
    "AndroidMobile": {"build_target": "Android", "unityci_image_module": "android"},
    "MagicLeap2": {"build_target": "Android", "unityci_image_module": "android"},
    "Linux": {"build_target": "StandaloneLinux64", "unityci_image_module": "linux-il2cpp"},
    "Windows": {"build_target": "Win64", "unityci_image_module": "windows-mono"},
}

UNITYCI_IMAGE_REVISION = "3"
LICENSE_IMAGE_MODULE = "linux-il2cpp"
PLAYERBUILD_ENTRY = "Outernet.PlayerBuild.Entry"

# Pinned to the v2026.07.21 tag of dotnet/install-scripts (raw at the commit SHA, which
# is immutable, unlike the moving https://dot.net/v1/dotnet-install.sh redirect).
DOTNET_INSTALL_SCRIPT_COMMIT = "da3ce11ba63f3dbb0fb835d41bda2665d5c48e84"
DOTNET_INSTALL_SCRIPT_URL = (
    f"https://raw.githubusercontent.com/dotnet/install-scripts/{DOTNET_INSTALL_SCRIPT_COMMIT}/src/dotnet-install.sh"
)
DOTNET_SDK_VERSION = "8.0.421"

# Unity exits 0 while reporting fatal package-manager errors only in the editor log. Every
# Unity invocation goes through run_unity_batchmode, which scans the captured log for these
# signatures and fails regardless of the exit code. Extend the tuple as new silent failures
# are discovered.
QUIET_FAILURE_SIGNATURES = ("An error occurred while resolving packages:",)


def run_unity_batchmode(
    project_path: Path,
    extra_flags: str = "",
    *,
    nographics: bool = True,
    auto_quit: bool = True,
    strict_exit: bool = True,
    extra_failure_signatures: Sequence[str] = (),
    env: dict[str, str] | None = None,
) -> Path:
    log_path = Path(tempfile.mkdtemp(prefix="unity-devkit-")) / "editor.log"
    editor = str(find_editor_for_version(read_editor_version(project_path)))
    # Player builds need a real GfxDevice: Unity 6 compresses Android textures (ASTC/ETC2) on the
    # GPU, and under -nographics the Null device falls back to a path that produces corrupt textures.
    # xvfb-run (added below) supplies the display the dropped -nographics would otherwise stand in for.
    graphics_flag = " -nographics" if nographics else ""
    quit_flag = " -quit" if auto_quit else ""
    command = f"{editor} -batchmode{graphics_flag}{quit_flag} -projectPath {project_path.resolve()}"
    if sys.platform != "win32":
        if shutil.which("xvfb-run"):
            command = f"xvfb-run {command}"
        # Unity runs `adb kill-server` on Android build teardown; strip the
        # env var so the kill lands on a local daemon, not whatever
        # ADB_SERVER_SOCKET points at.
        command = f"env -u ADB_SERVER_SOCKET {command}"
    command = f"{command} {extra_flags}".strip()
    command = f"{command} -logFile /dev/stdout"
    returncode = 0
    try:
        if shutil.which("tee"):
            bash_pipe(command, f"tee {log_path}", env=env)
        else:
            bash(command, log_path=log_path, env=env)
    except CalledProcessError as error:
        returncode = error.returncode

    signatures = QUIET_FAILURE_SIGNATURES + tuple(extra_failure_signatures)
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    failure_block = None
    for index, line in enumerate(lines):
        if not any(signature in line for signature in signatures):
            continue
        block: list[str] = []
        for candidate in lines[index : index + 20]:
            if block and not candidate.strip():
                break
            block.append(candidate)
        failure_block = "\n".join(block)
        break

    if failure_block is not None:
        raise SystemExit(f"Unity reported a silent failure (exit code {returncode}):\n{failure_block}")
    if returncode != 0 and strict_exit:
        raise SystemExit(f"Unity exited {returncode}; full editor log at {log_path}")
    if returncode != 0:
        print(f"  WARNING: Unity exited {returncode}; no package-manager failure found — full editor log at {log_path}")
    return log_path


def read_editor_version(project_path: Path) -> str:
    version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"
    version = editor_version(project_path)
    if version is not None:
        return version
    if not version_file.exists():
        raise SystemExit(f"Cannot find {version_file} — is this a Unity project?")
    raise SystemExit(f"Cannot parse editor version from {version_file}")


def find_editor_for_version(version: str) -> Path:
    path_editor = shutil.which("unity-editor")
    if path_editor:
        return Path(path_editor)

    if sys.platform == "win32":
        candidates = [Path(f"C:/Program Files/Unity/Hub/Editor/{version}/Editor/Unity.exe")]
    else:
        candidates = [
            Path(f"/opt/unity/{version}/Editor/Unity"),
            Path.home() / f"Unity/Hub/Editor/{version}/Editor/Unity",
        ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise ValueError(f"Cannot find Unity {version} editor. Searched: {searched}")


def editor_version(project_path: Path) -> str | None:
    version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"
    if not version_file.exists():
        return None
    for line in version_file.read_text().splitlines():
        if line.startswith("m_EditorVersion:"):
            return line.split(":", 1)[1].strip()
    return None


def resolve_unity_project(project: str) -> ProjectEntry:
    projects = discover_projects()
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")
    return projects[project]


def prepare_unity_project(project_path: Path) -> None:
    stale_lockfile = project_path / "Temp" / "UnityLockfile"
    if stale_lockfile.exists():
        stale_lockfile.unlink()

    # NuGetForUnity restore applies only to NuGet consumers (Assets/packages.config is
    # their manifest); elsewhere it would demand the dotnet SDK + tool manifest and
    # litter Assets/ with NuGet.config/packages.config/Packages.meta scaffolding.
    if (project_path / "Assets" / "packages.config").exists():
        # The unityci editor containers ship no dotnet CLI; provision the pinned SDK on
        # demand into ~/.dotnet (persisting across runs on self-hosted runners).
        env: dict[str, str] = {}
        if not shutil.which("dotnet"):
            install_dir = Path.home() / ".dotnet"
            if not (install_dir / "dotnet").exists():
                script_path = Path(tempfile.gettempdir()) / "dotnet-install.sh"
                bash(f"curl -fsSL {DOTNET_INSTALL_SCRIPT_URL} -o {script_path}")
                bash(f"bash {script_path} --version {DOTNET_SDK_VERSION} --install-dir {install_dir}")
            env = {"PATH": f"{install_dir}{os.pathsep}{os.environ['PATH']}", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
        bash("dotnet tool restore", env=env)
        bash(f"dotnet nugetforunity restore {project_path}", env=env)


def parse_environment_fields(entries: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for entry in entries:
        line = entry.strip()
        if not line:
            continue
        path, separator, value = line.partition("=")
        if not separator or not path:
            raise SystemExit(f"Invalid environment field entry (expected path=value): {entry!r}")
        fields[path] = value
    return fields


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
    project_config = resolve_unity_project(project)
    valid_builds = project_config.builds or []
    if not valid_builds:
        raise SystemExit(
            f"Project '{project}' declares no builds — add platform keys to its unity-devkit.json 'platforms' map"
        )
    if build not in valid_builds:
        raise SystemExit(f"Unknown build '{build}' for project '{project}'. Valid: {', '.join(valid_builds)}")
    if build not in PLATFORM_CONFIGS:
        raise SystemExit(f"No platform config for build '{build}'. Valid: {', '.join(PLATFORM_CONFIGS)}")

    project_path = project_config.path
    build_target = PLATFORM_CONFIGS[build]["build_target"]
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

    env: dict[str, str] = {"PLATFORM": build, "DEVELOPMENT": "true" if development else "false"}
    if environment_preset:
        env["ENVIRONMENT"] = environment_preset
    if environment_fields:
        env["ENVIRONMENT_FIELDS"] = json.dumps(environment_fields)
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
