import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from bashrun.bash import CalledProcessError, bash, bash_pipe

from .projects import ProjectEntry, discover_projects


UNITYCI_IMAGE_MODULES: dict[str, str] = {
    "Android": "android",
    "StandaloneLinux64": "linux-il2cpp",
    "Win64": "windows-mono",
}

PLATFORM_BUILD_TARGETS: dict[str, str] = {
    "AndroidMobile": "Android",
    "MagicLeap2": "Android",
}

UNITYCI_IMAGE_REVISION = "3"
LICENSE_IMAGE_MODULE = "linux-il2cpp"


def platform_build_target(platform: str) -> str:
    build_target = PLATFORM_BUILD_TARGETS.get(platform)
    if build_target is None:
        raise SystemExit(
            f"No build target known for platform '{platform}' — add it to PLATFORM_BUILD_TARGETS "
            "beside the matching SharedSpecs factory"
        )
    return build_target


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

COMPILE_ERROR_PATTERN = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<column>\d+)\): error (?P<code>CS\d+): (?P<message>.+)$"
)
ANNOTATION_LIMIT = 10


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
        # The API-updater side-pass parses candidate scripts without honoring #if guards or
        # asmdef references, so it reports CS errors against code excluded from compilation;
        # the compiler itself logs real errors unprefixed.
        if line.startswith("[Script Updater]"):
            continue
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
        report_compile_errors(lines)
        raise SystemExit(f"Unity reported a silent failure (exit code {returncode}):\n{failure_block}")
    if returncode != 0 and strict_exit:
        report_compile_errors(lines)
        raise SystemExit(f"Unity exited {returncode}; full editor log at {log_path}")
    if returncode != 0:
        print(f"  WARNING: Unity exited {returncode}; no package-manager failure found — full editor log at {log_path}")
    return log_path


def report_compile_errors(lines: list[str]) -> None:
    counts: dict[tuple[str, int, str, str], int] = {}
    for line in lines:
        if line.startswith("[Script Updater]"):
            continue
        match = COMPILE_ERROR_PATTERN.match(line)
        if match is None:
            continue
        key = (match["file"], int(match["line"]), match["code"], match["message"].strip())
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return

    print(f"Unity compile errors ({len(counts)} distinct):", file=sys.stderr)
    for (file, line_number, code, message), count in counts.items():
        print(f"  {code} x{count} {file}:{line_number} {message}", file=sys.stderr)

    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    for (file, line_number, code, message), count in list(counts.items())[:ANNOTATION_LIMIT]:
        title = escape_annotation_property(f"{code} x{count}")
        body = escape_annotation_data(f"{code}: {message}")
        print(f"::error file={escape_annotation_property(file)},line={line_number},title={title}::{body}")
    beyond_limit = len(counts) - ANNOTATION_LIMIT
    if beyond_limit > 0:
        print(f"::error::{escape_annotation_data(f'...and {beyond_limit} more distinct compile errors')}")


def escape_annotation_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_annotation_property(value: str) -> str:
    return escape_annotation_data(value).replace(":", "%3A").replace(",", "%2C")


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


def unityci_image_module(build_target: str) -> str:
    module = UNITYCI_IMAGE_MODULES.get(build_target)
    if module is None:
        raise SystemExit(
            f"Unknown build target '{build_target}' — supported: {', '.join(sorted(UNITYCI_IMAGE_MODULES))}"
        )
    return module


def build_player(
    project: str,
    build: str,
    *,
    version: str = "",
    commit_count: int = 0,
    development: bool = False,
) -> list[Path]:
    project_config = resolve_unity_project(project)
    platforms = project_config.platforms
    if not platforms:
        raise SystemExit(
            f"Project '{project}' declares no builds — add platform keys to its unity-devkit.json 'platforms' map"
        )
    if build not in platforms:
        raise SystemExit(f"Unknown build '{build}' for project '{project}'. Valid: {', '.join(sorted(platforms))}")

    project_path = project_config.path
    build_target = platform_build_target(build)
    entry = project_config.entry
    if not entry:
        raise SystemExit(
            f"Project '{project}' declares platforms but no 'entry' executeMethod in its unity-devkit.json"
        )
    prepare_unity_project(project_path)

    if version:
        bundle_version = f"{version}+{commit_count}"
        settings_path = project_path / "ProjectSettings" / "ProjectSettings.asset"
        rewritten = settings_path.read_text(encoding="utf-8")
        for field_name, value in (("AndroidBundleVersionCode", str(commit_count)), ("bundleVersion", bundle_version)):
            rewritten = replace_serialized_field(rewritten, field_name, value)
        settings_path.write_text(rewritten, encoding="utf-8")
        print(f"Stamped bundleVersion {bundle_version} (AndroidBundleVersionCode={commit_count}) into ProjectSettings")

    build_directory = project_path / "Build"
    before = snapshot_artifacts(build_directory)

    env: dict[str, str] = {"PLATFORM": build, "DEVELOPMENT": "true" if development else "false"}
    run_unity_batchmode(
        project_path,
        f"-buildTarget {build_target} -executeMethod {entry}",
        nographics=False,
        env=env,
    )

    verify_platform_record(project_path, build, development)

    after = snapshot_artifacts(build_directory)
    produced = sorted(path for path, modification_time in after.items() if before.get(path) != modification_time)
    if not produced:
        raise SystemExit(
            "Unity exited 0 but no .apk/.exe/.x86_64 under Build/ was produced or updated — "
            "the incremental build served a stale artifact. Delete the existing "
            "output under Build/ and the project's Library/Bee/.../build/ tree, then retry."
        )
    return produced


def verify_platform_record(project_path: Path, build: str, development: bool) -> None:
    record_path = project_path / "Assets" / "_LocalWorkspace" / "platform.json"
    if not record_path.is_file():
        raise SystemExit(
            f"No platform record at {record_path} — the project entry never ran the playerbuild Apply step"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("platform") != build:
        raise SystemExit(
            f"Platform record says '{record.get('platform')}' but '{build}' was requested — "
            "the entry applied the wrong spec"
        )
    if record.get("development") != development:
        raise SystemExit(
            f"Platform record says development={record.get('development')} but the build ran "
            f"with development={development}"
        )


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
