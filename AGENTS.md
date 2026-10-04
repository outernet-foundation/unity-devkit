# unity-devkit

## What this is

`unity-devkit` is the Unity build toolkit: per-project discovery, local builds, CI builds, license activation, the `install` command (download-or-build then install onto a device), and the ORAS cache/setup helpers those need. Consumers take this package as a **dev-group project dependency under their committed `uv.lock`** — the version surface is the consumer's lock, not a workflow env pin — and inline the Unity CI jobs directly in their own `integrate.yml` (template below). License handling and the UPM package cache live verb-internally: every leg's Setup restores the Unity license from the ORAS cache (activating via the in-container `unity-editor` on a miss, with jittered re-restore retries when sibling legs race a cold activation) and restores the UPM cache keyed to the project's `Packages/manifest.json` + `packages-lock.json`. Every Unity invocation runs in a `unityci/editor` container image composed from the project's `ProjectVersion.txt` (the runners supply Docker, not an installed editor).

This repo also develops and publishes the **`org.outernet.playerbuild`** UPM editor package (npm) — the inside-of-Unity half of app builds: platform-fact application from a C# table, the batchmode build entry, the editor configure window, and build-time environment materialization. Its source lives in `packages/unity/PlayerBuild/Assets/Package/`, developed inside the `packages/unity/PlayerBuild/` Unity harness project (discovered via a stub `unity-devkit.json` carrying only `name` — no `platforms`, no `environment_config`); CI's `compile-check-unity` job is its compile gate.

The PyPI identity: `unity-devkit`'s version tags start at `0.1.0`; the terminal `unity-buildkit` distributions (≤0.1.1) are deprecation signposts pointing here, not this package's history.

## Release flow

release-devkit's `AGENTS.md` owns the three-workflow contract. Repo-specific facts: CI self-consumes — `integrate.yml`'s `get-unity-matrix` + `compile-check-unity` jobs (behind the `preflight` ∥ `validate-release-plan` roots) run the verbs from source (`uv run compile-check-unity-matrix`, `uv run compile-check-unity`), exercising unreleased code. Both packages publish from the one `release` job: `release-devkit.yaml` declares `unity-devkit` (PyPI, path `packages/python/unity-devkit`, `unity-devkit-v*` tags) and `playerbuild` (npm `org.outernet.playerbuild`, path `packages/unity/PlayerBuild/Assets/Package`, `playerbuild-v*` tags), each gated by its own path-diff. The PyPI and npm trusted publishers are both bound to `release.yml` — npm allows one trusted publisher per package, bound to a single workflow filename: **never rename that file**.

## Consumer CI template

The compile-check shape, verbatim (player-build repos swap `compile-check-unity-matrix`/`compile-check-unity` for `build-unity-matrix`/`ci-build-unity`):

```yaml
get-unity-matrix:
  needs: [preflight, validate-release-plan]
  runs-on: ubuntu-latest
  outputs:
    matrix: ${{ steps.matrix.outputs.matrix }}
    license-tag: ${{ steps.matrix.outputs.license-tag }}
  steps:
    - *checkout
    - *uv-restore
    - id: matrix
      run: uv run compile-check-unity-matrix >> "$GITHUB_OUTPUT"

preflight-unity:
  needs: [get-unity-matrix]
  permissions: {contents: read, packages: write}
  runs-on: [self-hosted, unity]
  container: ${{ matrix.editor-image }}
  strategy:
    fail-fast: false
    matrix: ${{ fromJson(needs.get-unity-matrix.outputs.matrix) }}
  steps:
    - name: Wipe workspace
      run: |
        find "$GITHUB_WORKSPACE" -mindepth 1 -delete
        rm -rf ~/.cache/Unity
    - *checkout
    - *uv-restore
    - run: uv run compile-check-unity --project ${{ matrix.project-name }}
      env:
        CI_REGISTRY_TOKEN: ${{ github.token }}
        CI_REGISTRY_USERNAME: ${{ github.actor }}
        GITHUB_TOKEN: ${{ github.token }}
        LICENSE_CACHE_TAG: ${{ needs.get-unity-matrix.outputs.license-tag }}
        CACHE_REGISTRY: ghcr.io/${{ github.repository }}/cache
        UNITY_EMAIL: ${{ secrets.UNITY_EMAIL }}
        UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
        UNITY_SERIAL: ${{ secrets.UNITY_SERIAL }}
```

`*checkout` / `*uv-restore` are the file-level whole-step anchors every canonical `integrate.yml` defines (`checkout` = head-pinned ref, shallow, credentials not persisted; `uv-restore` = setup-uv cache restore, `save-cache: "false"` — `preflight` owns the one saver). The unity env block is the sanctioned `CI_REGISTRY_*` niche: its consumer is ci-devkit's neutral floor, not release-devkit. License restore/activation and the UPM package cache are verb-internal — the leg supplies only the env above. The wipe step exists because the self-hosted `unity` runners reuse the workspace directory; runner labels beyond `self-hosted` need an [actionlint config](https://github.com/rhysd/actionlint/blob/main/docs/config.md) declaring them (`.github/actionlint.yaml`). Untrusted or multiline expressions reach `run:` blocks only via step `env:` indirection.

## Shape

One flat module per concern under `packages/python/unity-devkit/src/unity_devkit/`:

| `uv run` command | Module | Notes |
|---|---|---|
| `build-unity` | `build_unity.py` | Local Unity build (APK or platform binary, suitable for `adb install`). Required flags: `--project <name>` and `--build <target>`, where the project's `unity-devkit.json` declares `platforms` (whose keys are the build targets). Streams the editor log, prints output paths under `<project>/Build/`. `--version <string>` stamps the given version into `ProjectSettings.asset` before the run (derivation is the caller's — unity-devkit computes no versions); `--run-number` sets the `bundleVersionCode`. `--development` selects the column, `--environment-preset <name>` + repeatable `--environment-field path=value` carry build-time environment intent to the playerbuild entry. |
| `compile-check-unity` | `compile_check_unity.py` | Compile gate: batchmode open+quit (`-nographics`, no executeMethod) failing on non-zero exit or any `error CS` in the log — Unity exits 0 on a plain open+quit despite script compile errors, so the log scan is the authoritative signal. Path-only (needs no `builds`); the gate for package/harness repos that own editor code but build no players. Owns its Setup (`ci_step`): git config, ORAS install, license restore-or-activate, UPM cache restore — the env it needs (`GITHUB_TOKEN`, `CACHE_REGISTRY`, `LICENSE_CACHE_TAG`, `UNITY_*`) comes from the leg's step env — and saves the UPM cache after the session. Two optional flags turn it into a build-free method driver: `--execute-method Class.Method` runs a static method after load (one editor session per invocation — the vehicle for committed-generated-asset regeneration, where each pass needs a fresh session) and `--build-target <target>` forces the startup build target for sessions that must open on a non-default platform. Player builds must not ride this verb (`-nographics` + `-quit` cannot build players); use `build-unity`. |
| `install` | `install.py` | Install a Unity build onto an `adb`-connected device or launch a linux executable. Default: pull the build artifact for `(project, target)` from ghcr via ci-devkit's `pull_build` into `~/.unity-devkit/builds/{tag}/{project}-{target}/`, then `adb install` the APK (or `bash_handoff` the Linux executable). `--branch` overrides the branch tag; `--run N` pulls `:run-N` (N is `github.run_number`, not the Actions run ID); `--list` shows available tags (`list_build_tags`); `--dry-run` prints the plan without acting. ORAS is auto-provisioned (`install_oras`); registry auth prefers an explicit `gh auth token` credential and otherwise falls back to ci-devkit's neutral chain (`CI_REGISTRY_*` env, ambient docker config). With `--build` / `-B`, skips the OCI pull and calls `build-unity` locally instead. |
| `lock-unity` | `lock_unity.py` | Lock Unity package versions for reproducible builds. |
| `test-unity` | `test_unity.py` | Run Unity editmode / playmode tests. |
| `activate-unity-license` | `license.py` | Activate the Unity Editor license (locally, or with `--oras-push` for the CI cache — restore-or-activate with retry, the same door the CI verbs use internally). |
| `unity-license-tag` | `license_restore.py` | Print the license cache tag (CI pins it via `LICENSE_CACHE_TAG`; the matrix verbs emit it as `license-tag=`). |
| `build-unity-matrix` | `matrix.py` | Emit the CI build matrix (CI-only): `matrix=<JSON with an include array>` + `license-tag=<daily tag>` `$GITHUB_OUTPUT` lines; `--project` scopes the matrix to one discovered project (multi-app repos). |
| `compile-check-unity-matrix` | `matrix.py` | Emit the CI compile-check matrix (CI-only): one entry per discovered project — platform-less entries included, no `platforms` needed — each carrying a `linux-il2cpp` editor image composed from that project's `ProjectVersion.txt`, plus the `license-tag=` line; `--project` scopes like above. |
| `ci-build-unity` | `ci_build_unity.py` | CI build with license/UPM/library cache restore-save and build-output push to ghcr (CI-only; assumes `GITHUB_WORKSPACE`, OCI registry, runner environment). `--registry` points at the library cache namespace; `--builds-registry` at the build outputs namespace. `--version <string>` stamps the given version into `ProjectSettings.asset` when supplied (empty builds unversioned); the `bundleVersionCode` is always the run number. Environment transport mirrors `build-unity`: `--environment-preset`, `--development` (bool flag), `--environment-fields` (newline-separated `path=value`). `BuildReport.json` files ride the build-output push as extra layers on both tags. |

Supporting modules: `projects.py` (per-project discovery via `unity-devkit.json`, and the pruned tree walk that is cross-repo API), `player_build.py` (the Unity machinery's single document: editor lookup, platform configs, the batchmode runner — command composition, live log streaming, quiet-failure scanning, env overlay — project/build resolution, environment-field parsing, and `build_player`, the player-build core every build door and `install --build` call: resolve, prepare, version stamping, the entry run, and the stale-artifact guard that fails a build Unity silently no-opped), `license_restore.py` (`restore_or_activate_license` — the ORAS license door the CI verbs and `activate-unity-license --oras-push` share, with jittered retry arbitrating cold-activation races between sibling legs; plus the daily `license_cache_tag`), and `upm_cache.py` (the ORAS-backed UPM package cache: tag = sha256 of the project's `Packages/manifest.json` + `packages-lock.json`, restored in Setup and saved after the work by both CI verbs — the `actions/cache` step is dead). The CI-floor modules (step wrapper, runner provisioning, ORAS artifact cache, build-artifact I/O) live in [`ci-devkit`](https://github.com/outernet-foundation/ci-devkit) (a runtime dependency); unity-devkit owns only Unity concerns.

The `packages/unity/PlayerBuild/` harness is this repo's one discovered Unity project: a minimal Unity `6000.0.66f1` host (no scenes, no XR settings asset — its `unity-devkit.json` carries only `name`, so player-build attempts fail loudly on the missing environment class / platform while compile-check discovers it) whose job is compiling and developing `Assets/Package/` and hosting the environment reflection fixture under `Assets/Editor/` (`FixtureEnv.cs` + a committed preset asset + the `EnvironmentFixtureSelfTest` driver that CI's execute-method door runs — harness test tooling, deliberately outside the shipped npm package). C# style: namespace `Outernet` flat, no unit tests ever (the compile gate is the test surface), `.meta` files committed alongside. CSharpier (`.csharpierrc.json` at the repo root, 120 cols) formats `packages/unity/PlayerBuild/Assets/Package/**/*.cs` — run `csharpier format` before committing C# changes.

## Constraints

**Every Unity invocation goes through `player_build.run_unity_batchmode`, which does not trust the editor's exit code.** Unity exits 0 while reporting fatal package-manager errors (unresolvable dependencies, invalid package.json versions) only in the editor log — a resolver failure therefore surfaces as a stale `packages-lock.json` and nothing else. The runner streams the log live through `tee` into a captured file and afterwards scans it for `QUIET_FAILURE_SIGNATURES`; a match fails the invocation with the matched log block regardless of exit code. New Unity verbs must call the runner rather than invoking the editor directly, and newly discovered silent-failure log lines get added to the signature tuple. Verb-local signatures ride the same scan via `extra_failure_signatures`: `compile-check-unity` passes `("error CS",)` because a plain open+quit exits 0 despite script compile errors — the signature stays verb-local because `lock-unity` intentionally tolerates them. Exit-code strictness is per-verb: build/test verbs fail on non-zero (`strict_exit=True`, the default), while `lock-unity` passes `strict_exit=False` — it judges resolution, not compilation, so a project whose scripts fail to compile (resolution already done, lock written) produces a warning, not a failure. `-runTests` invocations pass `auto_quit=False` (the test runner owns exit timing).

**Every runtime dependency must be PyPI-resolvable.** This package publishes to and is consumed from PyPI, and a registry consumer resolves the whole graph transitively by name — any dependency that is not on PyPI breaks every consumer's install. [`bashrun`](https://github.com/outernet-foundation/bashrun) is on PyPI like the rest; git-source pins are a scratch-branch-only vehicle for testing unreleased changes.

**Unity projects are discovered via per-project `unity-devkit.json`.** A pruned walk from the repo root finds every `unity-devkit.json`; each carries a `name` (the stable project key, decoupled from its directory — the workflow contract: `matrix.project-name`, artifact names, `--project` everywhere) and an optional `platforms` map whose keys are the build targets (`builds` is derived from them; absent for compile-only projects). The C#-owned fields in the same file (`environment_config`, `platforms` values) are ignored by the Python side — strict field partition: Python reads `name` + `platforms` keys, the playerbuild package reads `environment_config` + `platforms` values; the cross-file contract is just "file exists, `name` string, `platforms` dict". File presence is the opt-in: a Unity project without one is never touched, so vendored or nested projects need no prune list (the walk's `PRUNE_DIRECTORIES` still skips `Library`/`Temp`/`Build`/dot-dirs). `ProjectSettings/ProjectVersion.txt` beside each file remains the editor-version truth; a `unity-devkit.json` in a directory lacking the marker fails at load, as does no file found anywhere, or a duplicate `name` across two files. Run commands from the repo root. The pruned walk (`projects.directories_containing`) remains as cross-repo API.

**`build-unity-matrix` / `compile-check-unity-matrix` print `$GITHUB_OUTPUT`-format lines, not bare JSON.** Stdout is two `key=value` lines — `matrix=<JSON with an include array>` and `license-tag=<tag>` — so the workflow step is exactly `uv run compile-check-unity-matrix >> "$GITHUB_OUTPUT"` with no shell logic. Each matrix entry carries an `editor-image` tag composed from the project's `ProjectSettings/ProjectVersion.txt` editor version, the platform's unityci module, and the `UNITYCI_IMAGE_REVISION` constant in `player_build.py`; `license-tag` is the daily `v-YYYY-MM-DD` tag (UTC), which the fan-out legs receive as `LICENSE_CACHE_TAG` so one run pins one license tag at zero extra jobs — a run straddling midnight UTC may activate twice; self-healing, accepted. Nothing else pins an editor version: upgrading a project's editor in `ProjectVersion.txt` automatically switches its CI container.

**Entry-point names are the workflow contract.** Consumers invoke the verbs by name from their locked dev group (`uv run <verb>` — the caller's venv supplies the package, version-sourced by the consumer's `uv.lock`); unity-devkit is never a runtime dependency of a shipped package, only a dev tooling dependency of the repo that builds with it. No consumer references a unity-devkit workflow file, so there is no workflow-SHA lockstep: entry-point names and flags are the public API, and spending a change is a package publish + consumer floor-bump/relock. Verbs stay CI-agnostic — no ambient-env absorption of CI facts beyond the documented env contract (`CI_REGISTRY_*` credentials via ci-devkit's neutral chain, `CACHE_REGISTRY`, `LICENSE_CACHE_TAG`, `UNITY_*` credentials); everything else arrives as explicit flags.

**The environment transport is the playerbuild entry contract, owned here.** The Unity-side entry reads `PLATFORM`, `DEVELOPMENT`, `ENVIRONMENT`, and `ENVIRONMENT_FIELDS` (JSON object) from its process environment; `player_build.build_player` constructs that environment through `run_unity_batchmode`'s `env` parameter (a bashrun overlay, never `os.environ` mutation, so nothing leaks to sessions that shouldn't see it). Build names ARE platform names — the `unity-devkit.json` `platforms` keys, the workflow matrix `platform` values, and the C# `Platform.Table` keys are one spelling (`AndroidMobile`, `MagicLeap2`; `Linux`/`Windows` reserve their future table names — consumer-owned entries ignore `PLATFORM`, and an Entry pointed at a name the table lacks fails loudly on its own). Unset environment is an ambient no-op: empty means the door sends no `ENVIRONMENT`/`ENVIRONMENT_FIELDS` at all.

**The environment-lookup helpers are cross-repo Python API.** `player_build.find_editor_for_version` (editor ladder: `unity-editor` on PATH → `/opt/unity/<version>` → `~/Unity/Hub/Editor/<version>`; raises `ValueError` listing every searched path on a miss), `player_build.editor_version` (`ProjectVersion.txt` parse; `None` for a missing file or unparseable content), and `projects.directories_containing` (+ `PRUNE_DIRECTORIES`) are imported by registry consumers — prepo's `sync` verb. Their signatures and miss behavior are contract, not internals. The `SystemExit`-raising wrapper `read_editor_version` exists for unity-devkit's own CLI paths and delegates to the core helper; the batchmode runner consumes the `ValueError`-raising `find_editor_for_version` and `read_editor_version` directly, so a missing editor surfaces as the raw `ValueError`.

**Version stamping is caller-supplied and writes `ProjectSettings.asset` directly.** When `--version <string>` is passed, the build verbs stamp `bundleVersion` (the given string, verbatim — no parsing, no composition) and `AndroidBundleVersionCode` (the run number) as two scalar line edits in `ProjectSettings/ProjectSettings.asset` — no Unity API, no executeMethod contract — before batchmode; without it the project builds unversioned. unity-devkit never derives versions: no tag queries, no tag-prefix facts, no knowledge of where the string came from. Consumers bridge the gap in their own workflows — the version is fetched from the repo's release tooling (`get-app-version`) and passed to the leg as `--version` via step-env indirection. Precondition: Unity not running on the project.

**Build outputs live in ghcr as OCI artifacts, separate from the library cache.** `ci-build-unity` pushes build outputs through ci-devkit's `push_build` (ORAS CLI knowledge lives only in ci-devkit) to `ghcr.io/{owner}/{repo}/builds/{project}-{target}:{tag}` — one package per `(project, target)`, dual-tagged `{branch-slug}` and `run-{N}`. Build outputs are raw file layers (`.apk`/`.exe` as individual layers; Linux `exe + _Data/` as a plain `.tar` — no zstd, unlike the library cache's `tar.zst` wrapper which is CI-only since the runner has zstd but local-dev pull machines may not; the Linux tar shape stays Unity-side knowledge, passed to `push_build` as its file list). `install` pulls from the same composed reference via `pull_build` — `.apk` lands ready for `adb install` (Android); `build.tar` + `tar -xf` (Linux). The shelf address is composed by `build_reference` (lowercased end-to-end; `gh repo view` returns mixed-case), so the pull side cannot drift from the push side. `--run N` pulls `:run-N` where N is `github.run_number`, not the Actions run ID.

**ghcr Container registry storage is separately free — it does not count against the Actions+Packages quota.** Actions artifact storage and non-container Packages share one pooled allowance (500 MB on GitHub Free for Orgs); the Container registry (ghcr OCI) is a separate backend, currently free. `actions/upload-artifact` checks the pooled quota and blocks at cap; `oras push` to ghcr does not. Build outputs and the library cache live in ghcr for that reason. Deleting a ghcr image frees zero Actions quota.

**The ORAS cache media type identifies the wrapper package, not the consuming repo.** `cache.save()` pushes with `application/vnd.ci-devkit.cache.v1+zstd` (owned by ci-devkit — the `vnd.unity-devkit.*` prefix was stale). Restore doesn't filter on media type, so older manifests still pull. Build outputs push via `builds.push_build` with `application/vnd.ci-devkit.build.v1+raw`; pull doesn't filter on media type either, so manifests written by the old direct-oras dialect (default layer types) still pull.

## See also

- `plan.md` — the org.outernet.playerbuild initiative record; the remaining phases are active work.
- [`bashrun`](https://github.com/outernet-foundation/bashrun) — the shell-exec helpers this package uses everywhere (`bash`, `bash_output`, `bash_check`, `bash_handoff`).
