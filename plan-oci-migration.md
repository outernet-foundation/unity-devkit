# plan-oci-migration.md — build artifacts to ghcr OCI + install script once-over

This is an execution plan, not a status doc. A session with no prior context should be
able to execute it top to bottom. The §4 review gate has passed; the owner authorized
implementation. Per §6, the plan was updated to reflect the resolved decisions before any
code edits, then yielded to the owner.

This plan does not touch `plan.md` (the org.outernet.playerbuild initiative record).

## 1. Why this exists

A Make-it-Sing-fork CI run (36393741757, 2026-09-28) failed at `Upload Build Artifacts`
with:

> `Failed to CreateArtifact: Artifact storage quota has been hit. Unable to upload any new
> artifacts. Usage is recalculated every 6-12 hours.`

The org is on GitHub Free for Organizations: 500 MB Actions+Packages storage, 2,000
minutes. Billing page showed `0.5 GB used / 0.5 GB included`, reset in 3 days. The 0.5 GB
is **accrued GB-hours this billing cycle, not a live snapshot** — mid-cycle deletion stops
future accrual but does not reduce the accrued figure, and the cycle reset is what zeroes
it. The owner wants to avoid adding a payment method / spending limit to the org.

### Verified facts (do not re-derive — proof points attached)

1. **ghcr.io Container registry storage is currently free.** GitHub's Packages billing
   docs: "Container image storage and bandwidth for the Container registry is currently
   free. If you use Container registry, you'll be informed at least one month in advance of
   any change to this policy." Proof at scale: Homebrew distributes ~0.5 PB/month of
   binary "bottles" to ghcr as OCI artifacts via ORAS — the exact pattern this plan adopts.
   This is current as of 2026-09; verify the docs note still reads "currently free" before
   relying on it.
2. **Actions artifact storage and non-container Packages (npm/maven/rubygems/nuget) share
   one pooled allowance.** The org has zero non-container Packages (verified via
   `gh api /orgs/.../packages?package_type={npm,maven,rubygems,nuget}` — all empty). So
   the only thing counting against the 0.5 GB is private-repo Actions artifacts.
3. **Public repos' Actions usage (minutes AND artifact storage) is free — does not count.**
   Confirmed via GitHub Actions billing docs: "GitHub Actions usage is free for … public
   repositories." This is why `placeframe` (public) and `placeframe-capture-tool` (public)
   artifacts don't trip the quota but `Make-it-Sing-fork` (private) does.
4. **Actions cache (`actions/cache`) is a separate 10 GB/repo allowance**, not in the
   shared pool. Do not conflate with artifact storage.
5. **The quota block is enforced per-storage-system, not org-wide across all storage.**
   `actions/upload-artifact` checks the Actions+Packages quota and is blocked when at cap.
   `oras push` / `docker push` to ghcr does NOT check that quota — it goes to the Container
   registry, a separate backend. **Replacing the `upload-artifact` step with an `oras push`
   unblocks builds immediately, today — not on the 6–12h recalc, not on the cycle reset.**
   The accrued 0.5 GB on the billing page becomes irrelevant the moment the workflow stops
   calling `upload-artifact`; it sits as a number until the cycle resets, then zeroes.
6. **The prior-session confusion to avoid repeating:** a previous session told the owner
   that "Docker images count against the Actions quota." This is wrong for ghcr — the
   Container registry is separately free. The owner spent a night nuking a `unity-library`
   ghcr cache image expecting it to free Actions quota; it freed zero. The correct framing:
   *Actions artifacts and non-container Packages share a quota; ghcr container/OCI storage
   is currently free and doesn't count.*

## 2. Current state

### Push side — `unity-devkit/.github/workflows/build-unity.yml`

The two `actions/upload-artifact` steps that consume Actions storage:

- `build-unity.yml:107–113` — `Upload Build Artifacts`: name
  `${{ matrix.project-name }}-${{ matrix.platform }}`, path `/tmp/unity-builds/`,
  `if: success()`, `if-no-files-found: ignore`.
- `build-unity.yml:115–121` — `Upload Build Report`: name
  `${{ matrix.project-name }}-${{ matrix.platform }}-build-report`, path
  `${{ matrix.project }}/Build/**/BuildReport.json`, `if: always()`,
  `if-no-files-found: ignore`.

Build output is collected by `ci_build_unity.py:88–98` ("Collect build artifacts" step):
copies `*.apk`/`*.exe` files (or the whole build dir for Linux) into `/tmp/unity-builds/`.
The `unity-library` cache is already pushed to ghcr via ORAS at `ci_build_unity.py:80–86`
using `ci_devkit.cache.save(registry, "unity-library", tag, ...)` — that is the push
template to copy for build outputs.

### Pull side — `unity-devkit/packages/python/unity-devkit/src/unity_devkit/install.py`

Entry point `install` (`install.py:21`, 150 lines total). Surface area:

| flag | purpose | default |
|---|---|---|
| `--project` / `-p` | Unity project name (required) | — |
| `--target` / `-t` | `AndroidMobile`, `MagicLeap2`, or `Linux` | auto-select if exactly one installable target; required otherwise |
| `--branch` / `-b` | branch to find latest run | current git branch; fails if HEAD detached |
| `--run` / `-r` | specific GitHub Actions run ID | branch-latest logic |
| `--serial` / `-s` | adb device serial | single-device `adb` default |
| `--build` / `-B` | skip CI fetch, call `build-unity` locally | false |

Default flow (`install.py:78–142`): construct `artifact_name = f"{project}-{target}"`,
resolve branch, find run via `gh api repos/{owner_repo}/actions/artifacts -f name={artifact_name}
-f per_page=10` picking the first whose `workflow_run.head_branch` matches (`install.py:89–102`),
cache at `~/.unity-devkit/builds/{run_id}/{artifact_name}/` (`install.py:110`), `gh run download`
on miss (`install.py:115`), then `adb install` the APK (`install.py:141`) or `chmod +x` +
`bash_handoff` the Linux executable (`install.py:147–150`). `--build` path (`install.py:71–76`)
calls `build_player` locally and funnels through the same install step — unaffected by this
migration.

`INSTALLABLE_TARGETS = {"AndroidMobile", "MagicLeap2", "Linux"}` (`install.py:14`); `Windows`
is buildable but not installable.

### Blast radius

Only **repos with `platforms` in a `unity-devkit.json`** do player builds and are affected
by the build-artifact migration:

- **`Make-it-Sing-fork`** (private, has `MakeItSing-Unity/unity-devkit.json` with platforms)
  — the quota-motivated repo. Pins `unity-devkit/.github/workflows/build-unity.yml@69e621f5`
  via a generated `build-dispatch.yml`.
- **`placeframe-capture-tool`** (public, has `apps/CaptureTool/unity-devkit.json` with
  platforms) — public, so NOT quota-motivated, but migrate for consistency. Pins
  `build-unity.yml@b61dc729` via generated `build-dispatch.yml`. Additionally: its `ci.yml`
  has a dead `Upload images.lock` step (`ci.yml:141–146`, artifact `images-lock-zed`) with
  no consumer anywhere in the workspace or `release-devkit` (verified by grep) — the
  canonical `workloads/images.lock` is committed to git and regenerated by `uv run build
  --lock-only`, so the artifact is a stale snapshot nobody reads. Delete the step as part
  of this migration.
- **`Make-it-Sing`** (private) — **out of scope** per owner decision. Investigated: it
  references `build-unity.yml` and has a `unity-devkit.json`, but the manifest is in a
  legacy format (`builds` array + `execute_methods` dict, not the current `platforms`
  map) and its `ci.yml` workflow pin is a malformed 79-char string, not a 40-char SHA —
  not a clean third consumer. Recorded so it's not rediscovered; not pulled into this
  migration.

The other 6 repos that reference unity-devkit (`Nessle`, `ObserveThing`, `StatefulUnity`,
`extruded-text`, `lbe-toolkit`, `placeframe`) use only `compile-check-unity.yml` — no
player builds, no install, no artifacts. **Untouched by this migration.**

The `unity-devkit` change is centralized: one workflow file (`build-unity.yml`) and one
package module (`install.py`) are edited; both consumer repos pick up the workflow change
via pin bump and the package change via PyPI version bump. The `build-dispatch.yml` files
are generated by `unity-dispatch` (`dispatch_workflow_generator.py`) — confirm whether
regenerating picks up the new `unity-devkit` SHA automatically or whether each consumer
bumps its pin manually.

## 3. The migration

### Push side — replace `upload-artifact` with `oras push`

In `build-unity.yml`, replace the two `actions/upload-artifact` steps (`:107–121`) with
ORAS push steps. The build output (`/tmp/unity-builds/`) becomes an OCI artifact in ghcr;
the `BuildReport.json` stays as a tiny Actions artifact with `retention-days: 1` (Q4
decision) — keeps it one-click from the Actions UI for post-build debugging without
pulling the whole build, and the build-output OCI artifact carries only the build outputs.

**Tagging (dual-tag, mirrors `ci_build_unity.py:54–57`):** every push tags the
same manifest twice — `{branch-slug}` (mutable, latest-on-branch) and `run-{github.run_number}`
(immutable, specific-run). This preserves `install.py`'s `--branch` and `--run` flags 1:1.

- Package: `ghcr.io/{owner}/{repo}/builds/{project}-{target}` (one package per
  `(project, target)`, matching the current artifact-name contract at `install.py:78`).
- Tags: `:{branch-slug}` and `:run-{github.run_number}`.
- Build outputs push via **direct `oras push` (NOT `ci_devkit.cache.save`)**. `save()` wraps
  content in tar.zst, dragging a zstd dependency onto the pull side (zstd is not on macOS/
  Windows by default; macOS's bsdtar only handles zstd if libarchive was built with it).
  Build outputs push as raw OCI file layers instead: Android's `.apk` as a single file layer
  (`application/octet-stream`); Linux's `exe + _Data/` as a plain `.tar` (no zstd — `tar`
  ships everywhere, incl. Windows 10+). `oras pull -o` then writes the `.apk` directly
  (Android) or the `.tar`, extracted with `tar -xf` (Linux). The library cache
  (`ci_build_unity.py:86`) keeps `save()` — it's CI-only and the runner has zstd; the
  raw-file approach is specific to build outputs' local-dev pull path. Dual-tag: one
  `oras push` per tag (CLI doesn't multi-tag here); the second push is manifest-only since
  blobs dedupe by digest. Q5's wrapper-media-type question is superseded — raw file layers
  use `application/octet-stream`, and `oras pull` doesn't filter on it.
- Workflow `permissions:` already has `packages: write` (`build-unity.yml:49–51`); no
  permission change needed.

### Pull side — rewrite `install.py` fetch path

Replace `install.py:78–115` (the Actions-artifact lookup + `gh run download`) with ORAS
pull. The `--build` path (`:71–76`) and the install/launch step (`:134–150`) are
untouched.

- Default / `--branch foo`: `oras pull ghcr.io/{owner}/{repo}/builds/{project}-{target}:{branch-slug}`
  into `~/.unity-devkit/builds/{branch-slug}/{project}-{target}/`.
- `--run N`: `oras pull ghcr.io/{owner}/{repo}/builds/{project}-{target}:run-N` into
  `~/.unity-devkit/builds/run-N/{project}-{target}/`.
- Cache key changes from `{run_id}` to the tag itself (`{branch-slug}` or `run-{N}`).
- **Reference lowercasing (contract):** the full OCI reference
  `ghcr.io/{owner}/{repo}/builds/{package}:{tag}` must be lowercased end-to-end — OCI repo
  names are lowercase, but `gh repo view` returns mixed-case `owner/repo` and
  `{project}-{target}` is mixed-case. `{package}` = `f"{project}-{target}".lower()`. Mirror
  what `cache.py:23/62` does for the registry and extend it to the package name (those
  helpers lowercase the registry only, not the name — so the caller lowercases the name).
  The push side (`ci_build_unity.py`) and pull side (`install.py`) must lowercase
  identically or push/pull miss each other.
- **`--run` semantic shift:** the old flag took a GitHub Actions **run ID** (a large int
  like 36393741757); under OCI `--run N` pulls `:run-N` where N is `github.run_number`
  (the sequential per-repo number the push side tags with). The flag's help text and the
  cache dir (`~/.unity-devkit/builds/run-N/`) follow run_number, not run_id.
- Format on pull: `oras pull -o {dir}` writes raw file layers directly — the `.apk`
  lands in the cache dir ready for `adb install` (Android); for Linux it writes
  `build.tar`, then `tar -xf build.tar -C {dir}` extracts the `exe + _Data/` (no zstd).
  The downstream apk/executable detection (`install.py:117–132`) is unchanged.

### Auth and prerequisites — new local surface

`gh run download` uses `gh` auth transparently; `oras pull` does not. Two new local
prerequisites, both checked at the top of the fetch path:

- **oras presence (Q8):** the script checks `oras` on PATH; if missing, errors with
  platform install pointers (brew/scoop/curl) and exits. No auto-provisioning — the dev
  already needs `gh` installed and authenticated, so requiring oras alongside is
  acceptable. (CI is unaffected — `install_oras()` provisions it in the runner.)
- **ghcr login (Q3):** capture `gh auth token` via `bash_output`, then feed it to oras via
  `bash("oras login ghcr.io --username oauth2 --password-stdin", stdin_text=token)` — the
  `stdin_text` pattern (mirroring `ci_devkit/setup_oras.py:48–51`), NOT a shell pipe
  (`echo | oras login`), which bashrun's `bash()`/`bash_output()` reject. Idempotent; wrap
  with a clear error if `gh auth token` fails. For public packages
  (placeframe-capture-tool) no auth is needed for pull, but running the login unconditionally
  is harmless.

### Cleanup — deferred to a tracked follow-up

ghcr artifacts do not auto-expire. Without a cleanup workflow, build-output packages
accumulate forever, and the `unity-library` cache packages already have this problem
(no cleanup workflow exists anywhere in the workspace, verified by grep). Decision (Q6):
**defer** the cleanup workflow to a tracked follow-up, not part of this migration. The
deferral rests on two mechanisms: carrying cost is currently near-zero (ghcr Container
storage is free, F1) and grows slowly; and information-arrival — waiting gives the
30-day policy-change notice (F1) plus observed accumulation rate, both of which refine
the retention window before committing to one. The soft cost is `--list` noise (slow
onset, weeks-to-months); the hard ceiling is ghcr's per-package version count (~1000, far
out at typical cadence). A follow-up plan builds the scheduled
`DELETE /orgs/{org}/packages/container/{pkg}/versions/{version}` workflow for both
package families (build outputs + library cache) — net-new operational surface where a
bug deletes wanted artifacts, so it warrants focused testing against a throwaway package,
not a hasty bolt-on to this migration.

## 4. Resolved decisions

The owner has answered all of the original seven, plus the post-gate decisions (Q8–Q9) that
emerged during implementation review (the zstd/cross-platform surface). Each is recorded
below with its decision and rationale; an executor implements to these and does not
re-derive them.

### Scope questions (what to fix alongside the migration)

**Q1. Install script once-over scope.** The migration forces a rewrite of `install.py:78–115`.
While the file is open, which of these latent issues also get fixed? Recommend: fix all
that are cheap, defer the rest.

- (a) **`per_page=10` silent cap** (`install.py:92`) — the branch-latest lookup only sees
  the 10 most recent artifacts across all branches; fails on less-active branches even
  when a matching run exists. **Becomes moot under OCI** (tag-based lookup has no
  pagination cap), so the migration eliminates this bug for free. No separate fix needed.
- (b) **Cache never evicted** (`install.py:110`) — `~/.unity-devkit/builds/` grows
  forever. Add `--clear-cache` flag and/or age-based eviction. Cheap.
- (c) **No `--list` / discoverability** — can't ask "what runs are available?" Add a
  `--list` verb that shows recent tags for `(project, target)`. Under OCI use
  `oras repo tags ghcr.io/{owner}/{repo}/builds/{package-name}` (registry-native; avoids
  the GitHub Packages API's org-vs-user endpoint split and URL-encoded-slash package
  names). Subcommand verified via ORAS docs: `oras repo tags <reference>` lists all tags
  (text by default, `--format json` optional). Medium effort; high value given the
  migration makes the available-runs surface less obvious than the Actions UI was.
- (d) **Linux executable detection is heuristic** (`install.py:119–132`) — looks for a
  top-level file with matching `_Data/` dir. Works because of how `ci_build_unity.py:94`
  lays out the artifact. Tighten the contract or add a manifest entry naming the
  executable. Low priority.
- (e) **No dry-run** — add `--dry-run` that prints what would be fetched/installed
  without doing it. Cheap.
- (f) **`gh repo view` assumes cwd is the consumer repo** (`install.py:89`) — document
  or enforce. Cheap.

**Decision:** (c) `--list`, (e) `--dry-run`, (f) enforce (not document) that cwd is the
consumer repo. (a) is moot under OCI (tag-based lookup has no pagination cap — no fix
needed). (b) and (d) deferred.

**Q2. Across-the-board vs. player-builds-only.** The owner originally said "no
`actions/upload-artifact` at all in any repo." The actual blast radius for build artifacts
is 2–3 repos (the player-build repos). The other `upload-artifact` uses in the workspace
are: `extruded-text` (test results, small), `governance` (rendered PDFs + packet zips,
90-day retention, **human consumers — board members click-download from the Actions UI**),
`placeframe-capture-tool` (a lock file, tiny). Branch:
- (i) **True zero** — migrate all of them, including governance PDFs. Cost: board members
  lose one-click download (need `gh run download` or `oras pull`); adds cleanup surface
  for small artifacts that were never the problem.
- (ii) **No large build outputs via Actions storage** (recommended) — migrate only the
  Unity build outputs in `build-unity.yml`; set `retention-days: 1–3` on the small stuff
  elsewhere. Kills the quota killer, keeps Actions UI for human-consumed small artifacts.
  The small artifacts at 1–3 day retention are negligible against any plan's allowance.

**Decision:** (ii) — migrate only the Unity build outputs in `build-unity.yml`; set
`retention-days: 1–3` on the small stuff elsewhere. Refined further by owner: exclude
`extruded-text` and `governance` from this plan entirely (governance's PDFs are
human-consumed by board members via the Actions UI — out of scope). For
`placeframe-capture-tool`, in addition to migrating its Unity build outputs, delete the
dead `Upload images.lock` step (`ci.yml:141–146`) — the artifact has no consumer anywhere
in the workspace or `release-devkit`, and the canonical `workloads/images.lock` is
committed to git, so the artifact is a stale snapshot nobody reads (see §2).

### Design questions

**Q3. Auth UX.** Auto-run `oras login` from `gh auth token` inside `install.py`
(transparent, recommended) vs. document that the user runs `oras login` once (less magic,
more setup friction). Recommend auto.

**Decision:** (i) auto — `install.py` runs `oras login` via `gh auth token` at the top of
the fetch path, idempotently, wrapped in a helper with a clear error if `gh auth token`
fails.

**Q4. BuildReport.json destination.** Currently a separate Actions artifact
(`build-unity.yml:115–121`). Options:
- (i) Include it in the build-output OCI artifact (one pull gets everything). Simple.
- (ii) Keep as a tiny Actions artifact with `retention-days: 1`. Keeps the report
  accessible from the Actions UI for post-build debugging without pulling the whole build.
- (iii) Push as its own tiny OCI artifact. Overkill.
Recommend (i) — one artifact, one pull, and it removes the last `upload-artifact` call
from `build-unity.yml`.

**Decision:** (ii) — keep `BuildReport.json` as a tiny Actions artifact with
`retention-days: 1`. The build-output OCI artifact carries only the build outputs. (This
leaves one `upload-artifact` call in `build-unity.yml` for the report — acceptable; it's
small and human-consumed from the Actions UI.)

**Q5. OCI media type for build outputs.** Reuse
`application/vnd.unity-devkit.cache.v1+zstd` (the library-cache type) or mint
`application/vnd.unity-devkit.build.v1+zstd`? The media type is a wrapper identifier
(per `AGENTS.md`); `oras pull` doesn't filter on it. Recommend reuse (less machinery)
unless there's a filtering/discovery reason to distinguish.

**Decision:** Superseded by Q9 (post-gate zstd-drop). Once build outputs push as raw file
layers (not a tar.zst wrapper), there is no wrapper media type to decide — raw file layers
use `application/octet-stream`, and `oras pull` doesn't filter on it. The original
"reuse vs mint" framing applied only to the wrapper blob, no longer used for build outputs.
(For reference: the actual cache media type in code is
`application/vnd.ci-devkit.cache.v1+zstd` — `cache.py:83`, owned by ci-devkit post-
extraction; the unity-devkit AGENTS.md reference to `vnd.unity-devkit.*` is stale and gets
corrected in step 9.)

**Q6. Cleanup workflow scope.** Build the scheduled ghcr cleanup workflow as part of this
plan, or defer to a follow-up? It's net-new operational surface and applies to both
`unity-library` cache packages (already accumulating) and the new build-output packages.
Recommend: build it as part of this work — the migration adds accumulation pressure, and
solving it once for both package families is cheaper than revisiting. Lives in
`unity-devkit/.github/workflows/` (scheduled, `gh api` delete calls with an age cutoff).
Owner to set the retention window (suggest 14 days for build outputs, 30 for library
cache).

**Decision:** Defer to a tracked follow-up. The deferral rests on two mechanisms:
carrying cost is currently near-zero (ghcr Container storage is free, F1) and grows
slowly; information-arrival — waiting gives the 30-day policy-change notice (F1) plus
observed accumulation rate, both of which refine the retention window before committing
to one. Soft cost is `--list` noise (slow onset); hard ceiling is ghcr's per-package
version count (~1000, far out at typical cadence). The follow-up builds the scheduled
`DELETE /orgs/{org}/packages/container/{pkg}/versions/{version}` workflow for both package
families — net-new operational surface where a bug deletes wanted artifacts, so it
warrants focused testing against a throwaway package, not a hasty bolt-on to this
migration. See §3 "Cleanup — deferred."

**Q7. `Make-it-Sing` (non-fork) scope.** Confirm whether it does player builds (no
`platforms` manifest in the local checkout, but references `build-unity.yml`). If yes,
it's a third consumer repo and needs the same pin-bump treatment.

**Decision:** `Make-it-Sing` (non-fork) is out of scope per owner decision. Pin-bump
consumers are `Make-it-Sing-fork` and `placeframe-capture-tool`. (Investigated finding,
not a scope ask: `Make-it-Sing` is in a broken state w.r.t. the current unity-devkit
contract — legacy `unity-devkit.json` format (`builds` array + `execute_methods`, not the
current `platforms` map) and a malformed 79-char workflow pin SHA in `ci.yml:97`.
Recorded so it's not rediscovered; not pulled into this migration.)

### Post-gate decisions (emerged during implementation review)

**Q8. Local oras prerequisite.** The pull-side rewrite (`install.py` → `oras pull`)
requires `oras` installed locally for anyone running `install` — the CI side provisions it
(`install_oras()`), but local dev machines do not. Options: (A) auto-provision oras from
`install.py` (mirroring CI provisioning, adding macOS support to ci-devkit's
`install_oras`); (B) check for oras on PATH, error with install pointers if missing, leave
installation to the user.

**Decision:** (B) — check + error, no auto-provisioning. The dev already needs `gh`
installed and authenticated, so requiring oras alongside is acceptable; auto-provisioning
would add macOS provisioning surface to ci-devkit (arch detection, brew-or-tarball, zstd
install) for a one-time-per-machine cost that doesn't justify the machinery.

**Q9. Drop the tar.zstd wrapper for build outputs.** `ci_devkit.cache.save` wraps content
in tar.zst; the pull/extract step then needs zstd + a zstd-aware tar. zstd is not
pre-installed on macOS or Windows, and macOS's bsdtar only handles zstd if libarchive was
built with it — a cross-platform footgun independent of who provisions oras (it's the
artifact format that drags the dependency). Options: (i) keep tar.zst and require zstd
locally alongside oras; (ii) drop the wrapper for build outputs — push raw file layers
(Android `.apk` as one layer; Linux `exe + _Data/` as a plain `.tar`), so `oras pull -o`
writes files / a plain tar extractable with ubiquitous `tar -xf`, no zstd anywhere on the
pull side.

**Decision:** (ii) — drop the tar.zstd wrapper for build outputs. Push via direct
`oras push` (NOT `save()`), raw files for Android, plain tar for Linux. The library cache
keeps `save()` (CI-only, runner has zstd). This supersedes Q5 (no wrapper → no wrapper
media type) and revises the §3 push/pull design accordingly.

## 5. Execution order

The §4 review gate has passed; implementation is authorized. The cleanup workflow (Q6) is
deferred and is not in this execution order. Steps 6–8 (publish, pin-bump, verify) require
git push / merge — the sandbox GitHub App token is `Contents: read` only and cannot push;
hand those to the operator after the code edits (steps 2–4) land and pass checks.

1. **Blast radius confirmed (Q7).** Pin-bump consumers: `Make-it-Sing-fork` and
   `placeframe-capture-tool`. `Make-it-Sing` (non-fork) out of scope. Capture each
   consumer's current `unity-devkit` pin SHA so the post-migration bump is explicit
   (`Make-it-Sing-fork` → `@69e621f5`; `placeframe-capture-tool` → `@b61dc729`).
2. **Edit `build-unity.yml` + `ci_build_unity.py`.** Replace the two `upload-artifact`
   steps (`:107–121`) with ORAS push (dual-tag, per §3). Keep `BuildReport.json` as a tiny
   Actions artifact with `retention-days: 1` (Q4). Push build outputs via direct
   `oras push` (NOT `save()`) — raw `.apk` file layers (Android) / plain `.tar` (Linux),
   no zstd (Q9). Add the `--builds-registry` option to `ci-build-unity` and a
   `BUILDS_REGISTRY` env var in the workflow. NOTE: step-2 code was started before the
   zstd-drop decision — the `ci_build_unity.py` push step (which used `save()`) is stale
   against this plan and is reworked on resume; the `--builds-registry` option and the
   `build-unity.yml` edits (env var, flag, removed `upload-artifact`, `retention-days: 1`)
   stand.
3. **Edit `install.py`.** Rewrite the fetch path (`:78–115`) to `oras pull` (raw files /
   plain tar, no zstd per Q9). Add the auth + prerequisites (Q3: `oras login` via
   `stdin_text` from `gh auth token`; Q8: check oras on PATH, error if missing). Apply the
   scoped once-over fixes from Q1: `--list`, `--dry-run`, and enforce (not document) that
   cwd is the consumer repo. Keep `--build` path (`:71–76`) and install/launch step
   (`:134–150`) untouched.
4. **Edit `placeframe-capture-tool/.github/workflows/ci.yml`.** Delete the dead `Upload
   images.lock` step (`:141–146`). (The `unity` job's build-output migration is handled by
   the `build-unity.yml` pin bump in step 7; this step is the repo-local `build-zed` job
   edit.)
5. **Test in `unity-devkit`'s own harness** — the `PlayerBuild` harness is compile-only
   (no platforms), so it can't test the full push/pull. Test the `install.py` changes
   against a manually-pushed OCI artifact in the unity-devkit ghcr namespace.
6. **Publish `unity-devkit` to PyPI** via the normal release flow (`release.yml`,
   `unity-devkit-v*` tag). The package change lands before the workflow change reaches
   consumers.
7. **Bump the `unity-devkit` workflow pin** in each consumer repo's `build-dispatch.yml`
   (`Make-it-Sing-fork`, `placeframe-capture-tool`). Determine whether `unity-dispatch`
   regeneration handles the bump or it's manual per repo. Each consumer bump is a separate
   PR; the package PyPI version and the workflow SHA are independent pins (per
   `AGENTS.md`: "the one sanctioned way to spend a name change is a lockstep workflow-SHA
   + package bump in a single consumer change" — but here the entry-point names and flags
   are unchanged, so no lockstep requirement).
8. **Verify end-to-end** in `Make-it-Sing-fork`: trigger a build, confirm the OCI push
   lands in ghcr, confirm `install` pulls and installs it. Confirm the Actions+Packages
   storage quota is no longer accumulating from builds.
9. **Update `AGENTS.md`** with the new contract: build outputs live in ghcr as OCI
   artifacts (dual-tagged), `install` pulls from ghcr, the Actions-artifact path is gone.
   Add the quota-model clarification from §1 verified fact 6 so the next session doesn't
   re-derive the ghcr-is-free distinction.

## 6. Process protocol

Mirror `plan.md`'s protocol: propose → wait for the owner's explicit instruction → only
then edit. Review gates halt implementation mid-stream. Always yield. The §4 review gate
has passed; the owner authorized implementation (and authorized updating this plan first,
then yielding before any code edits). Subsequent review gates, if any, are at the owner's
discretion to insert.

## 7. Verified facts appendix

Re-stated for cold-reader trust. Each is load-bearing; do not re-litigate without new
evidence.

- **F1.** ghcr Container registry storage is currently free (GitHub Packages billing docs,
  "currently free" note, as of 2026-09). Homebrew's 0.5 PB/month ORAS-to-ghcr distribution
  is the proof at scale.
- **F2.** Actions artifact storage + non-container Packages share one pooled allowance
  (500 MB on Free for Organizations). Actions cache is separate (10 GB/repo). Container
  registry is separately free.
- **F3.** Public repos' Actions storage does not count against the org quota. Private
  repos' does.
- **F4.** The "Artifact storage quota has been hit" block is enforced on
  `actions/upload-artifact` only. `oras push` to ghcr bypasses it. Replacing the step
  unblocks builds immediately — no recalc wait, no cycle reset wait, no payment method.
- **F5.** The billing page's "X GB used" is accrued GB-hours this cycle, not a live
  snapshot. Deletion stops future accrual but doesn't reduce the accrued figure; only the
  cycle reset zeroes it. This only matters if `upload-artifact` is still in use — once
  migrated, the accrued figure is irrelevant to builds.
- **F6.** The ORAS push mechanism already exists for the library cache: `ci_devkit.cache.save`
  (used at `ci_build_unity.py:86` for `unity-library`), media type
  `application/vnd.ci-devkit.cache.v1+zstd` (`cache.py:83` — owned by ci-devkit post-
  extraction; the unity-devkit AGENTS.md reference to `vnd.unity-devkit.*` is stale). Build
  outputs do NOT reuse `save()` (Q9 dropped the tar.zstd wrapper for cross-platform
  reasons) — they push via direct `oras push` as raw file layers, but to a parallel
  namespace: `ghcr.io/{owner}/{repo}/builds/{name}:{tag}` (vs the library cache's
  `.../cache/{name}:{tag}`).
- **F7.** `build-unity.yml` already grants `packages: write` (`:49–51`). No permission
  change needed for the push.
- **F8.** The `install.py` `--build` path (`:71–76`) calls `build_player` locally and is
  entirely independent of the CI fetch path. It is the escape hatch if the OCI migration
  has teething issues — it keeps working through the migration.
