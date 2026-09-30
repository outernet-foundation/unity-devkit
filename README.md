# unity-devkit

Unity build, license, and CI tooling. Projects are discovered via a per-project `unity-devkit.json` at each Unity project root: each carries a stable `name` (the workflow contract: matrix, artifacts, `--project`) and an optional `platforms` map whose keys are the build targets. File presence is the opt-in — a project without one is never touched — and `ProjectSettings/ProjectVersion.txt` inside each project remains the editor-version truth. Consumers inline the Unity CI jobs in their own `ci-cd.yml` (see [Consuming from another repo](#consuming-from-another-repo)); unity-devkit is consumed as a `uvx` tool, never a project dependency.

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
| `build-unity-matrix` | Emit the CI build matrix plus the license cache tag (CI-only; two `key=value` lines for `$GITHUB_OUTPUT`; `--project` scopes to one project). |
| `ci-build-unity` | CI build with license/UPM/library-cache restore-save; stamps the caller-supplied `--version` when given (CI-only). |

Every command accepts `--help`.

## Consuming from another repo

Unity CI is inline: no reusable workflows, no SHA pins. Pin the package version in your workflow `env:` and call the verbs via `uvx` — unity-devkit is a tool, not a consumer project dependency, so no `dependencies` entry is needed. The compile-check shape (player builds swap `compile-check-unity-matrix`/`compile-check-unity` for `build-unity-matrix`/`ci-build-unity`):

```yaml
env:
  UNITY_DEVKIT_VERSION: 0.1.21

jobs:
  unity-matrix:
    if: github.ref != 'refs/heads/main'
    needs: [check]
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.matrix.outputs.matrix }}
      license-tag: ${{ steps.matrix.outputs.license-tag }}
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v7
        with: {enable-cache: true, save-cache: "false"}
      - id: matrix
        run: uvx --from unity-devkit==${UNITY_DEVKIT_VERSION} compile-check-unity-matrix >> "$GITHUB_OUTPUT"

  unity-check:
    if: github.ref != 'refs/heads/main'
    needs: [unity-matrix]
    permissions: {contents: read, packages: write}
    runs-on: [self-hosted, unity]
    container: ${{ matrix.editor-image }}
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.unity-matrix.outputs.matrix) }}
    steps:
      - name: Wipe workspace
        run: |
          find "$GITHUB_WORKSPACE" -mindepth 1 -delete
          rm -rf ~/.cache/Unity
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v7
        with: {enable-cache: true, save-cache: "false"}
      - run: >-
          uvx --from unity-devkit==${UNITY_DEVKIT_VERSION} compile-check-unity
          --project ${{ matrix.project-name }}
        env:
          GITHUB_TOKEN: ${{ github.token }}
          LICENSE_CACHE_TAG: ${{ needs.unity-matrix.outputs.license-tag }}
          CACHE_REGISTRY: ghcr.io/${{ github.repository }}/cache
          UNITY_EMAIL: ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
          UNITY_SERIAL: ${{ secrets.UNITY_SERIAL }}
```

The license restore/activation and the UPM package cache are handled inside the verbs — the leg only supplies the env above. Runner self-hosted labels beyond `self-hosted` need an [actionlint config](https://github.com/rhysd/actionlint/blob/main/docs/config.md) declaring them (`.github/actionlint.yaml`).

For local dev, invoke the same entry points via `uvx --from unity-devkit build-unity`, `uvx --from unity-devkit install`, etc. Each Unity project carries a `unity-devkit.json` with a `name` and (where buildable) a `platforms` map. To test an unreleased change, pin a git ref: `uvx --from git+https://github.com/outernet-foundation/unity-devkit.git@<sha> build-unity`.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run pytest
```

The C# half (`packages/unity/PlayerBuild/Assets/Package/`, the `org.outernet.playerbuild` UPM package) compiles through `uv run compile-check-unity --project PlayerBuild` and formats with CSharpier (`csharpier format packages/unity/PlayerBuild/Assets/Package`).
