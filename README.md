# unity-devkit

Unity build, license, and CI tooling. Projects are discovered via a per-project `unity-devkit.json` at each Unity project root: each carries a stable `name` (the workflow contract: matrix, artifacts, `--project`) and an optional `platforms` map whose keys are the build targets. File presence is the opt-in — a project without one is never touched — and `ProjectSettings/ProjectVersion.txt` inside each project remains the editor-version truth. Paired with two reusable GitHub Actions workflows hosted here — [`build-unity-internal.yml`](https://github.com/outernet-foundation/unity-devkit/blob/main/.github/workflows/build-unity-internal.yml) (player builds) and [`compile-check-unity.yml`](https://github.com/outernet-foundation/unity-devkit/blob/main/.github/workflows/compile-check-unity.yml) (compile gate) — consumers call them cross-repo pinned to a pushed SHA with `secrets: inherit`.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Commands

Run from a repo root whose Unity projects each carry a `unity-devkit.json` (with at least a `name`; `platforms` keys where build intent is needed).

| `uv run <name>` | What it does |
|---|---|
| `build-unity --project <name> --build <target>` | Local Unity build (APK or platform binary) suitable for `adb install`; `--version <string>` stamps the version into `ProjectSettings.asset` (caller-supplied — unity-devkit derives nothing); `--development`, `--environment-preset <name>`, and repeatable `--environment-field path=value` carry environment intent to the playerbuild entry. |
| `compile-check-unity --project <name>` | Compile gate — batchmode open+quit that fails on compile errors; for repos that own editor code but build no players. |
| `install --project <name>` | Download the latest CI artifact and `adb install` (or launch, for `Linux`); with `--build`, compile locally first. |
| `lock-unity` | Lock Unity package versions. |
| `test-unity --project <name>` | Run editmode / playmode tests. |
| `activate-unity-license` | Activate the Unity Editor license (locally or with `--oras-push`). |
| `unity-license-tag` | Print the license cache tag. |
| `build-unity-matrix` | Emit the CI build matrix (CI-only; two `key=value` lines for `$GITHUB_OUTPUT`). |
| `unity-dispatch --project <name> --output <file> --build-workflow <owner/repo/.github/workflows/build-unity-internal.yml@sha>` | Generate the consumer's `workflow_dispatch` build workflow from the live environment class (preset choice, development toggle, one input per simple-typed field); `--check` is the drift gate for consumer CI. |
| `ci-build-unity` | CI build with library-cache restore/save; stamps the caller-supplied `--version` when given (CI-only). |

Every command accepts `--help`.

## Consuming from another repo

CI uses the hosted `build-unity-internal.yml` / `compile-check-unity.yml` workflows (pinned to a pushed SHA with `secrets: inherit`). Those workflows invoke unity-devkit via `uvx --from unity-devkit==${UNITY_DEVKIT_VERSION}` — unity-devkit is a tool, not a consumer project dependency, so no `dependencies` entry is needed.

For local dev, invoke the same entry points via `uvx --from unity-devkit build-unity`, `uvx --from unity-devkit install`, etc. Each Unity project carries a `unity-devkit.json` with a `name` and (where buildable) a `platforms` map. To test an unreleased change, pin a git ref: `uvx --from git+https://github.com/outernet-foundation/unity-devkit.git@<sha> build-unity`.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run pytest
```

The C# half (`packages/unity/PlayerBuild/Assets/Package/`, the `org.outernet.playerbuild` UPM package) compiles through `uv run compile-check-unity --project PlayerBuild` and formats with CSharpier (`csharpier format packages/unity/PlayerBuild/Assets/Package`).
