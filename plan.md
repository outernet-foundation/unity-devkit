# plan.md — org.outernet.playerbuild: apply-to-globals (rewrite 3)

This plan moved to unity-devkit at the unitybuild repo's retirement (2026-09-27); the
package and harness it describes live here under `PlayerBuild/`. The unitybuild repo was
this initiative's development home — the phases below are its execution record, updated
in place as work lands.

This is an execution plan, not a status doc. A session with no prior context should be able
to execute it top to bottom. It was rewritten wholesale on 2026-09-27 after the owner
reversed the profiles-spine architecture (rewrite 2) in favor of **apply-facts-to-globals**,
then amended later the same day (session 2): the environment model went **class-sourced**
(§Environment model). The previous plans are in git history; nothing from them that
contradicts this document survives.

**The reversal in one paragraph**: `BuildPipeline.BuildAssetBundles` has no profile form and
never will — it bakes against ambient global state — so an apply-facts-to-globals path must
exist in *every* architecture, forever. The profiles spine would have kept it as a second
path alongside shipped profile assets: two sources of truth for the same facts, the exact
disease behind every wound of the 09-26 sessions (stale snapshots, self-heal strips,
byte-drift gates, load-bound authoring chains). The hybrid makes apply-to-globals the *only*
path. The Elliot door keeps its status-quo two-step UX (Configure → Build, what MIS runs
today), version shadowing dies structurally in CI (no snapshots can exist there), and a
build preprocessor verifying effective values against the table makes silent
misconfiguration impossible at every door we own. Build profiles are declared **irrelevant
to the system**: never shipped, never authored, never activated, never guarded-as-such.

**The environment pivot (2026-09-27, session 2)**: rewrite 3 had carried rewrite 2's
JSON-declared environment model (`environment_config.fields` with paths/types/enum lists) —
a hand-maintained shadow of the consumer's C# class and a permanent sync tax on the app
author (the Elliot annoyance, judged justified). The owner reversed it: **the C# class is
the source of truth for the environment**, reflected into every door; `build-config.json`
carries one string (the class file path); presets AND per-field overrides exist at every
door (GitHub dispatch, configure window, CLI); `ConfigMode`/`ResolveEffective` survive
(their earlier-scheduled deletion is reversed); CT converts to the MIS shape. Full design:
§Environment model. Rulings that shaped it — do not relitigate: disturb MIS minimally
(Elliot's code); CT is freely modifiable; no curation or secret-exclusion machinery
(YAGNI); no discovery — one in-class preset map; no attributes on the env class
(dependency direction); `UnityEnvInspector` is deleted and subsumed (not stubbed), with
Override as a first-class *derived* concept (the map's complement).

**The restructure (2026-09-27, session 3)**: the amendment's implementation and the
release carrying it were one phase on paper and two sessions of work — split, and the
phases renumbered 1–8 (old I→1, F→2, V→5, CT→6, MIS→7, C→8; the new 3 and 4 slot between
2 and 5). Phase 3: the env core in package C#. Phase 4: the mode-aware configure window.
Phase 5: the Python half plus the release.

## Owner C# style rules (2026-09-26 review loop; binding for this package, all phases)

Codified from the owner's directives while reviewing `BuildConfigFile.cs`/`Platform.cs`.

1. **Aggressively inline single-callsite functions and single-use variables.** The only
   sanctioned helpers: (a) guard flow with early returns/continues, (b) two or more live
   callsites, (c) cross-file door API (e.g. the application functions the entry and the
   configure window both call). When rule 3 forces a helper into existence, that is
   sanctioned.
2. **Callers before callees.** Within a class, a method's definition appears above the
   helpers it calls; siblings called by the same parent are ordered by first call site in
   the parent's body. At type level, data/leaf types sit above their consumer — vocabulary
   before logic, never a pile of types at file end.
3. **No nested ifs, no else statements.** Flatten with early returns, `continue`,
   ternaries, `&&`-merged guards, early-return dispatch, or a value-returning helper where
   control must converge afterward. Continuation clauses (`else`/`catch`/`finally`) are the
   sole adjacency exemption.
4. **Blank line after `}` when the next line sits at the same indentation.** Exempt:
   dedented lines (enclosing closers) and continuation clauses — CSharpier enforces the
   `else`/`catch` exemptions mechanically. Case-label siblings are NOT exempt.
5. **A conditional must guard an action or a throw — never exist to enable a specific log
   line.** If deleting a guard changes only log wording, delete it.
6. **Name a fact once.** A condition tested more than once is hoisted to a boolean; delete
   any guard whose success/failure downstream guards already imply.
7. **Checks live with the concept's owner, hoisted up the callstack.** Low-level helpers
   stay pure mechanisms.
8. **Validation consolidates in one place, inlined there; DTOs are pure data.** Where the
   framework offers an automatic hook, use it (`[OnDeserialized]`).
9. **No catch-to-rethrow or catch-to-wrap.** Errors propagate raw to the top-level
   boundary (`catch (Exception) { Debug.LogException; EditorApplication.Exit(1); }`), the
   only base-`Exception` catch.
10. **Hew to prior art's density and register.** Minimal code observed facts justify —
    never build speculative machinery before measuring the real bytes.

Process protocol for every session: propose → wait for the owner's explicit instruction →
only then edit; review gates halt implementation mid-stream; always yield.

## Status (2026-09-27, session 14 close — the fork stands: Phase 7's E2E vehicle brought from parse-dead to one step from green)

Branch topology assembled (owner rulings on record: MIS's 5-commit dev stack moved to
`ci-support-redux`, dev reset to origin/dev, the dirty `.env.airgapped` edit discarded;
fork work merges to fork `main` immediately — everything rides the default branch; and
per-repo consolidation branches may mix concerns — placeframe's `ci-support-redux` carries
its 17-commit dev stack plus the F16 rename). GitHub mechanics learned: "Sync fork" updates
only branches the fork already has — new branches arrive by push alone; sandbox SSH
remotes fail (publickey), so cross-repo reads go over HTTPS (a fetched `upstream` remote
in the fork clone delivered `ci-support-redux` without a push). Fork main = `c07a0c1`
(merge of the stack onto the owner's dev-at-fork-time merge).

placeframe prerequisite executed: three MagicLeap runtime files renamed `#if MAGIC_LEAP` →
`#if OUTERNET_MAGIC_LEAP` (table spelling, `Platform.cs`) **plus the harness
ProjectSettings define** — correcting the session's own earlier "it stays": left as
`MAGIC_LEAP`, placeframe CI compiles the gated code out (green but hollow). Cherry-picked
onto dev as `7ec5e2f9` (18 ahead, owner-pushed); the pre-created worktree branch was
dropped (prepo drop's unmerged guard met with `git branch -D` — sanctioned, the change is
preserved on the consolidation branch). Consequence accepted: no npm `placeframe-magicleap`
until the branch lands; the MIS fork bridges via git-pin to `7ec5e2f9`. placeframe's origin
is `plerion.git` (repo renamed; old URLs redirect).

The fork CI cascade — each push surfaced one defect, all fixed same-session:

- `5160098` + `ee1f27c`: ci.yml gained the `main` push trigger (fork operating mode —
  **revert ledger**), dropped the dead `build-env:` input and its now-inert `config_type`
  dispatch input (the preset transport dead-ends until the UnityEnv machinery exists;
  ambient no-op is the defined interim; the panel honestly offers nothing until the
  generated dispatch workflow lands); uv relock 0.1.14 → 0.1.16 (renamed verbs).
- **The 0s failure was misdiagnosed as missing secrets** — the owner's org-level
  `UNITY_*` secrets were fine (note: org secrets need the repo in each secret's access
  selection). Real cause: a malformed workflow pin — `ba7a417` had appended junk hex to
  the true SHA (72 chars; "reference should be a valid branch, tag, or commit"). Fixed
  `9ffabc7`. Blast-radius sweep found the same corruption in CT ×3 sites (different junk
  suffix, a `d7bb6ba` fragment): ci.yml:101 + the generated `build-dispatch.yml`'s header
  command and `uses:` — the dispatch generator had baked the malformed pin in verbatim and
  `--check` validated garbage against garbage. CT fixed (`3a4ea42`: pin edit + regeneration
  with the corrected `--build-workflow`, drift gate green). All other consumers verified
  clean 40-char pins.
- `dc2ce70`: fork catalog went keyless (`package`, `execute_methods` dropped) — surfaced
  as the matrix step's pydantic forbid-extra failure, reproduced locally. The Phase 7 item
  executed early; `BuildScript.cs` is now dead from CI's perspective (devkit 0.1.16's
  build door hardcodes `Outernet.PlayerBuild.Entry`).
- `f6a4e8c`: `workloads/images.yml` tags + build-cache re-pointed at
  `make-it-sing-fork` — the fork's GITHUB_TOKEN cannot push the prime's ghcr packages
  (rightly). Mixed-case `GITHUB_REPOSITORY` blocks env interpolation (ghcr rejects
  uppercase refs) — **revert ledger** entry; durable fix is docker-devkit exporting a
  lowercased repo variable (upstream item, open).
- **`unity-container-prep` was structurally broken cross-repo**: a `./`-referenced local
  action inside a cross-repo-called workflow resolves against the *caller's* checkout
  (`Can't find 'action.yml'` on the fork) — while local *workflow* refs
  (`prepare-unity.yml`) resolve from the host repo and work cross-repo (proven green on
  the fork). The hosted family had never executed cross-repo: every consumer repin was
  unpushed, and devkit's own runs always had the action in-checkout. Devkit `065598f`
  inlined the composite's three steps into `build-unity.yml` + `compile-check-unity.yml`
  and deleted the action; `69e621f` records the constraint in AGENTS. **Repin sweep to
  `69e621f52fbdc7c988e69b08daaf4134f6cc68ef`**: fork `c42ea85`; CT `81b1401` (dispatch
  regenerated again, `--check` green); Nessle `e0c3d69`, ObserveThing `ce60dff`,
  StatefulUnity `fd09785`, lbe-toolkit `60d28d1` (one commit each, punted stacks);
  placeframe `be38a73e` on its `ci-support-redux`.
- Confirmed live on the fork: self-hosted unity runners, org secrets, license activation
  (green in 45s — the ORAS path works; the mixed-case `CACHE_REGISTRY` watchpoint did not
  bite). The revert ledger was created in §Phase 7 (`78b20b5`) and extended (`1be4ee0`),
  including the release-trigger rule: a ci.yml-completion `workflow_run` trigger filtered
  to the main ref is portable to prime and stays; a fork-only shape joins the ledger.

Push states at close: devkit pushed through `69e621f` (pins live on origin); fork pushed
through `c42ea85`; run 36360018379 in flight with `check`/`matrix`/`mirror` green — livekit
and the unity builds pending with outcomes analysis-certain: livekit green (namespace
fix), both unity build jobs red at the missing `Outernet.PlayerBuild.Entry` (the manifest
does not pin `org.outernet.playerbuild`). CT 12 ahead, the four compile-check consumers
and placeframe's branch tip on their punted stacks carrying the repins. Errors on record
beyond the misdiagnosis: SSH fetch failures throughout (last-known refs used — safe under
the punt); release.yml's fetch-by-SHA race reds every direct-to-main push until the
`workflow_run` retrigger lands (known, queued, not a defect of this session's work).

Next session: (1) read run 36360018379's final state to confirm the predicted outcomes.
(2) **The AndroidMobile slice**: manifest npm-pin `org.outernet.playerbuild@0.1.1`
(npmjs scoped registry, CT's shape) + `build-config.json` at `MakeItSing-Unity/` root
(minimal platform entries, CT's empty-overrides shape) + `lock-unity` regen — the first
real Entry-driven build attempt; further reds (table facts vs MIS globals, scenes, XR
sweep) are each their own fix. (3) The MagicLeap2 slice and the flip body proper: the
**placeframe-magicleap pin alone** → `7ec5e2f9` (the define-rename bridge; the other four
pins stay at `c3313124` — the stack's Core/api-client/Logging/ARFoundation changes are
consumed only by Elliot's unmerged `feature/adopt-packages`, whose landing gates the
full-pin move and the F4 npm migration), app-code define renames (`OUTERNET_*`), UnityEnv
members + preset re-saves, inspector deletion, dispatch workflow, Build Profile asset +
Configure menu deletions, the four bake call-site rewires (F15/F31). (4) release.yml
`workflow_run` retrigger + the resolve-version bridge (`app-build-version`, uvx pins →
0.1.17). Process protocol unchanged: propose → owner instruction → edit.

## Status (2026-09-27, session 13 close — the dual-registry release landed; CT Phase 6 remainder executed)

The pending releases landed, then CT's gated remainder executed against them. En-route facts,
all fixed same-session:

- **release-devkit `0.1.17` live on PyPI** (carrying `app-build-version` — CT's session-10 pin
  presumption confirmed exact). Two CI failures fixed on the way: `ruff format` drift in the
  verb's test file (the session-10 "green" record had covered `ruff check` but not
  `--check`-format), and four CI-naive tests asserting the `-dev` spelling while a runner
  exports `GITHUB_REF_NAME=main` ambient into `CliRunner` — fixed with per-test
  `monkeypatch.delenv`; verified by running the suite under a simulated runner env, the
  compensation class for sandbox certification generally (a sandbox cannot reproduce runner
  ambient).
- **unity-devkit `0.1.16` (PyPI) + playerbuild `0.1.1` (npm) live** — the npm CI channel's
  first end-to-end success. Two novel failures fixed: PyPI/CDN index lag right after upload
  (manifest-job resolution failed on a 2.5-minute-old release; re-run, transient by class),
  and npm provenance verification rejecting the publish because the package manifest carried
  no `repository` field (`422 … expected to match "https://github.com/outernet-foundation/
  unity-devkit" from provenance`) — fixed by declaring `repository` (url + directory) in the
  package's package.json (`3bada70`). The provenance failure could only surface after the
  version-conflict layer stopped firing; manual publishes (0.1.0) never do provenance. A
  partial-release state (PyPI published, no tags — the run died mid-publish) self-healed on
  the next release via the idempotency skip absorbing the PyPI republish: the burn-era
  machinery working as designed.
- devkit's workflow pins ride `release-devkit==0.1.17` (`4c590d3`), activating the npm-11
  idempotency fix for its own npm publish.

CT remainder, executed on its unpushed dev stack (now 11 ahead; known dirt untouched —
one piece consumed, see below):

- **npm pin swap** (`6421c7d`): manifest `file:` pin → `org.outernet.playerbuild@0.1.1` via
  the existing `npmjs` scoped registry; `lock-unity` regenerated the lock from the registry;
  compile gate green against the npm-resolved package. CT's dev-group devkit pin rode up to
  0.1.16 in the same commit (the lock held 0.1.14; the new verb names require it).
- **Dispatch workflow** (`9aa00a0`): `unity-dispatch` generated `.github/workflows/
  build-dispatch.yml` from the live `CaptureEnv` (preset choice Airgapped + development +
  three field inputs, mode deduped, bracket refs, `uses:` pinned to CT's existing
  `build-unity.yml@08d5378…`); `--check` proven byte-stable locally. **Design gap on record**:
  the CI drift gate needs an editor for the dump door, CT's check job is editor-less
  ubuntu-latest, and consumers may not use `prepare-unity.yml`/`unity-container-prep`
  directly — the sanctioned CI home for a consumer drift gate does not exist yet. Correct
  shape: a hosted-workflow-family addition (devkit side, next release). Interim: local
  `--check` is the manual gate.
- **APK smoke — the version-input path proven end-to-end in one artifact**: `app-build-version`
  (`0.0.0-dev+999`, no tags + off-main spelling, opaque to the stamper) → `build-unity
  --version … --run-number 999` → ProjectSettings stamp → Entry apply+build →
  `aapt dump badging`: `versionName='0.0.0-dev+999'`, `versionCode='999'`. The boundary law
  (WHAT=release-devkit, HOW=devkit stamping, TRANSPORT=the workflow input) validated live.
- **Phase 1 acceptance probe, resolved to its architecture-permitted extent**: the real APK
  build's log carries `[playerbuild] effective values verified` inside
  `BuildPipeline.BuildPlayer` — the preprocessor hook is proven live and passing. The failure
  branch ("run Apply") is unreachable from every batchmode door by construction: the entry
  applies before building, and every verify input except scenes is apply-written (scenes
  self-compare when no profile snapshot exists). It needs the native editor Build window —
  owner-side smoke, folded into the Phase 7 Elliot smoke. The harness cannot host it (no
  `build-config.json`); the sandbox extends the same reason (no non-applying player-build
  door exists in batchmode).
- Incidental proof of the convergence claim: the entry build's XR sweep consumed CT's
  long-dirty `XRGeneralSettingsPerBuildTarget.asset`, rewriting it to content identical to
  HEAD — stale state converging to the committed canonical truth. CT's remaining known dirt
  (`ProjectSettings.asset` architecture/graphics lines, `EditorBuildSettings`,
  `PackageManagerSettings`, `extraction-plan.md`) untouched as found.
- Gates: compile gate green post-swap; `unity-dispatch --check` green; full preflight green
  (the repo's uv `==0.12.15` pin tripped the sandbox's default 0.11.14 — toolchain-only,
  the repo AGENTS note's case; green under the newer uv).
- Prose follow-up on record: CT's AGENTS still names the dead `compile-unity` verb (renamed
  `build-unity` in 0.1.16) — rides the punt-lift PR; flagged, not fixed this session.

devkit is 1 ahead of origin (this record) — operator push at leisure; it is prose-only and
rides the next code push.

**MIS fork ruling (owner, this session)**: Phase 7 executes on **`Make-it-Sing-fork`** — the
owner forked MIS after enabling private-repo forking (org Settings → Member privileges; the
repo-level checkbox un-greys only after the org flip — GitHub's documented default disallows
private-repo forking). Motivation: true default-branch E2E (release-spelling versions via
`GITHUB_REF_NAME=main`, workflow_run Releases) that MIS's main cannot host under the
consumer-push punt; the work lands back per the one-PR-per-repo consolidation, unchanged.
Fork transfer costs on record as the checklist: repo secrets re-add (`UNITY_*`), self-hosted
unity runners scoped to the fork, ORAS license cache re-push (fork's token cannot read the
org namespace), fork token's read-only default flipped to write. Known first-red on the
fork: ci.yml's `build-env: CONFIG_TYPE=…` is dead input against the pinned new workflow
surface — the Phase 7 migration is the first work item, not a surprise.

Next session: **Phase 7 on the fork** per the amended phase below; the devkit-side drift-gate
hosted-workflow growth is queued behind it (or rides the next devkit release).

Next-session pointer superseded by the session-14 close above (Phase 7 on the fork is under
way — the vehicle is standing; the pointer's detail lives there); retained for the record.

## Status (2026-09-27, session 12 close — unity.py consolidation + build-core inlines)

Owner-directed follow-on to session 11: `unity.py` and `player_build.py` consolidated into one
file, then an aggressive-inlining audit applied to the result. The consolidation rationale on
record: `player_build.py`'s only importers (both doors, `install.py`) already imported from
`unity.py`; the earlier "mechanism vs orchestration" layering was aesthetic, not contractual;
the C# prior art (`PlayerBuild.cs` holds vocabulary + orchestrator + apply family in one
document) maps to one module holding the whole Unity layer. **Owner correction, same session:**
the consolidated file is named `player_build.py`, not `unity.py` — the module is the
player-build concept's home, and the legacy grab-bag name died with the merge. The cross-repo
surface (prepo imports `unity_devkit.unity.editor_version` + `find_editor_for_version`) moved
with it: prepo `9f6c944` re-points at `unity_devkit.player_build`, riding the same release
(prepo pins `unity-devkit>=0.1.0`, so the import change and the release land in the usual
lockstep).

The audit (callsite census: production excl. intra-module, tests, cross-repo) and its executed
rulings:
- **Inlined** `unity_batchmode_command` into `run_unity_batchmode` (single production caller;
  composition — editor lookup, `xvfb-run` wrap, `env -u ADB_SERVER_SOCKET`, flags — is now part
  of the runner). Test seam moved down a level: the four runner tests monkeypatch
  `read_editor_version` + `find_editor_for_version` (functools.partial, no closures) onto a fake
  editor script, so the real command composition now executes against the fake where the old
  seam bypassed it.
- **Inlined** `resolve_unity_build` into `build_player` (single production caller since the CI
  door moved to `resolve_unity_project`): the head of `build_player` is now
  `resolve_unity_project(...)` + the three inline guards (no builds / unknown build / no
  platform config) + the `build_target` lookup. `test_resolve.py`'s cases ported onto the
  harness (`test_build_player.py`), gaining a fourth failure mode (build outside
  `PLATFORM_CONFIGS`) and a `-buildTarget Android -executeMethod Outernet.PlayerBuild.Entry`
  flags assertion through the fake runner — coverage that did not exist at the resolve level.
- **Inlined** `playerbuild_environment` into `build_player` (owner ruling over the keep
  recommendation): the env dict construction sits inline at the `run_unity_batchmode` call.
  Its two pure contract tests ported to harness env assertions (module-level `RECEIVED_SESSIONS`
  recording in the producing fake).
- **Inlined** `QUIET_FAILURE_BLOCK_LINE_LIMIT` (slice bound `20`).
- **Kept**: `run_unity_batchmode` (4 callers), `read_editor_version` (matrix ×2 + runner),
  `resolve_unity_project` (2 doors + `build_player`), `prepare_unity_project` (3 callers),
  `parse_environment_fields` (2 doors), `build_player` (3 doors), `snapshot_artifacts` +
  `replace_serialized_field` (2 live callsites each in `build_player`; the latter owns the
  count-mismatch guard), `PLAYERBUILD_ENTRY` (vocabulary constant, AGENTS-named),
  `QUIET_FAILURE_SIGNATURES` (documented extension point), `find_editor_for_version` +
  `editor_version` (prepo contract regardless of count), `PLATFORM_CONFIGS` (matrix + core).

Result: one `player_build.py` (~250 lines, after the owner correction above), `player_build.py`
the module deleted at session 11's extraction re-absorbs everything and `unity.py` is deleted
too; test files renamed/ported
(`test_player_build.py` + `test_resolve.py` → `test_build_player.py`, 10 harness tests;
`test_dispatch_workflow_generator.py` sheds the two env tests it hosted). Suite 41 (net −8
removed, +10 ported/new). Commits `9aaef7d` (consolidation + inlines) + `d49e358` (AGENTS
supporting-modules/lookup/transport updates) + `d4719da`/`38498c0` (the rename to
`player_build.py` and its doc follow) — gates ruff/basedpyright 0/0/pytest 41 throughout (one
ruff Yoda-condition autofix on the new flags assertion). No
workflow, verb, or consumer surface changed beyond prepo's import — session 11's pins and
releases are untouched.

Next session: unchanged — verify the operator push (devkit now 64 ahead, HEAD = this commit)
and the dual-registry release, then CT's gated Phase 6 remainder.

## Status (2026-09-27, session 11 close — build-door rotation + player-build core)

Owner-initiated from the naming: `compile_unity.py` builds players while `check_unity.py`
compiles — inverted names — plus suspected duplication between the local and CI build doors.
Exploration confirmed both, and worse than duplication: the CI door
(`build_unity.py`'s build step) was a near-verbatim inline of the local core MINUS the
stale-artifact guard — the mtime-diff that catches a silently no-op'd incremental build. CI
restores `Library/` from cache, i.e. the exact conditions the guard was born from, yet its
collect step copied whatever sat in `Build/` and would have uploaded a stale APK as fresh.
Also: `compile_unity.py` hosted a function named `build_unity_project` (module says compile,
function says build, sibling module is `build_unity.py`).

Rulings that shaped the change — do not relitigate:
- The pin-coupling cost of changing a verb's meaning was spelled out and accepted: one-time,
  per-consumer (old workflow SHA + new package = loud typer failure; each consumer crosses once
  via a lockstep workflow-SHA + package bump, after which pin independence returns). Spent
  pre-push riding the pending release — the cheapest moment, with CT/MIS flips already scheduled
  to bump both pins anyway.
- `check-unity` ruled vague ("could mean run unit tests", with `test-unity` beside it). Successor
  named by the owner: `compile-check-unity`. Runner-up `compile-unity` was passed over: shorter
  and literally true, but the explicit name won.
- Workflow filenames corrected broadly (owner ruling): `unity-build.yml` → `build-unity.yml`,
  `unity-check.yml` → `compile-check-unity.yml`, `unity-prepare.yml` → `prepare-unity.yml` —
  verb-first, matching the verb convention. Extended by the same spirit (agent extension,
  surfaced at handoff): the matrix verbs followed (`unity-matrix`/`unity-check-matrix` →
  `build-unity-matrix`/`compile-check-unity-matrix`; functions `build_matrix`/
  `compile_check_matrix` in `matrix.py`).
- Consumer pins updated in the same session (owner choice) rather than left for flip phases.
- `versioning.py` dissolved into the build core: post-boundary-ruling it was a module named
  after a deleted concept holding one writer with, post-extraction, one caller. The stamping
  inlined as a loop over `(field, value)` pairs; `replace_serialized_field` survives as the leaf
  helper owning the count-mismatch guard. Test port grew beyond import-path-only (the inline
  removed the import target): `test_player_build.py` drives `build_player` against a tmp
  repository with module-level fake Unity runners (no closures) — stamp composition, opaque
  version strings, missing-field refusal, stale-artifact guard (41 tests total, net +1).

Landed on local main, each commit gated ruff + basedpyright 0/0 + pytest green:
- `6fe54f4` — extraction: new `player_build.py` hosts `build_player` (the old
  `build_unity_project` body: resolve → prepare → stamp → mtime snapshot → batchmode entry run →
  produced-diff guard), plus `snapshot_artifacts` and `replace_serialized_field`; both doors and
  `install --build` call it; the CI door gains the stale-artifact guard; `resolve_unity_project`
  in `unity.py` absorbs the gate's duplicated project-validation head; the artifact suffix set
  grew `.x86_64` — Linux players, without which the guard would false-fire on CI Linux the
  moment it adopted it (and install's local-launch filter had the same latent miss, fixed with
  it).
- `08d5378` — the rotation: `compile_unity.py` → `build_unity.py` (`build-unity`, local door),
  `build_unity.py` → `ci_build_unity.py` (`ci-build-unity`), `check_unity.py` →
  `compile_check_unity.py` (`compile-check-unity`); pyproject scripts follow (the dead
  `check-unity` line removed); the workflow family renames with internal verb/job/display-name
  updates; devkit ci.yml repoints at `compile-check-unity.yml`; the dispatch generator's
  `COMPILE_ERROR_SIGNATURES` import, help text, and example pins follow; install's help text
  follows; `test_matrix`/`test_dispatch_workflow_generator` updated. Verb probes confirmed the
  new entry points resolve and run.
- `77c3408` — prose: AGENTS table rows + supporting-modules paragraph (gaining `player_build.py`,
  losing `versioning.py`) + constraints vocabulary; the entry-point-contract paragraph gained the
  sanctioned-lockstep clause; README command catalog and workflow links follow.

Cross-repo execution (one commit per repo, all on their unpushed dev stacks, each repinning to
`08d5378` — the rotation commit; later devkit commits don't touch workflow content): Nessle
`711603c`, ObserveThing `6d0562d`, StatefulUnity `f35873f`, lbe-toolkit `9659501`, placeframe
`14fba5e2` (+ prose `bdc1afd2`, its workflows AGENTS row) — `unity-check.yml@4d6b4b7` →
`compile-check-unity.yml@08d5378…`; Make-it-Sing `ba7a417` (`unity-build.yml@cfd487e` →
`build-unity.yml@08d5378…`) and CT `73f8b9a` (`unity-build.yml@d7bb6ba` → same) — CT's repin
absorbs session-10's "repin if devkit history moves" assumption. Known dirt left as found:
MIS `.env.airgapped`, CT's Unity assets + `extraction-plan.md`, ObserveThing's untracked WIP.

Assumptions on record: consumers taking a renamed workflow SHA must bump their unity-devkit
package pin past this release in the same change (the lockstep crossing) — their punt-lift PRs
already consolidate exactly that; the release-devkit `0.1.17` presumption from session 10 is
unchanged. The dispatch generator's `--build-workflow` reference is consumer-supplied, so
already-generated dispatch workflows (none exist yet — CT generates its own in Phase 6) carry no
rename debt.

Next session: unchanged from the session-10 close — verify the operator push (devkit now 58
ahead, HEAD = this commit) and the dual-registry release, then CT's gated Phase 6 remainder per
the shrunk list there, its workflow pin already repointed.

## Status (2026-09-27, session 10 close — catalog shrink + the versioning boundary)

Three rulings executed, all pre-push, riding the pending releases:

- **Pinned rename executed, name amended by the owner past the pin**: `dispatch.py` →
  `dispatch_workflow_generator.py` — `dispatch_generator` judged insufficient,
  `github_workflow_dispatch_input_yml_generator` correct but unwieldy; the landed name keeps the
  load-bearing words (workflow, dispatch, generator), drops the redundant ones (github, yml,
  input). Verb stays `unity-dispatch`; entry `unity_devkit.dispatch_workflow_generator:app`; the
  test module followed (`test_<module>` mirror). Commits `a6058ad` + `4e4e5bb`.
- **The catalog schema shrank to `path` + `builds` — all four optional fields dead.**
  `execute_methods`: degenerate under Entry's env-var platform transport — the `PLAYERBUILD_ENTRY`
  constant lives in `unity.py`, `resolve_unity_build` returns a 2-tuple, the missing-method guard
  is gone. `package`/`grant_permissions`: install-door conveniences ruled cruft-or-wrong-place —
  the surviving ADB branch is bare `adb install` (reinstall over an existing package fails
  loudly; the human uninstalls — accepted), CT's READ_LOGS grant is a manual smoke-checklist
  step. `tag_prefix`: died with the versioning boundary below. Commits `355192a`/`90acdac`
  (install pair), `3f775b7`/`f5e2221` (version + execute_methods + docs), `d7bb6ba` (flattened
  the nested double rewrite in `stamp_build_version` after an owner readability complaint).
- **The versioning boundary (owner's encapsulation law)**: build tools take versions as inputs
  and never derive them — the string "release-devkit" appears nowhere in unity-devkit's code,
  workflows, or configs; unity-devkit stamps whatever opaque string it is handed. The mistake
  diagnosed: `versioning.py`'s ledger query was a verbatim clone of release-devkit's
  `list_tag_versions` and the catalog's `tag_prefix` a duplicate of release-devkit.json's app
  entry — three copies of one concept; the old "version-ledger primitives live in release-devkit
  and are not imported here" AGENTS line was the smell made policy. Corrected cut: WHAT version =
  release-devkit, sole owner, exposed for build-time use by its new `app-build-version` verb
  (latest stable `{tag_prefix}-v*` tag, prerelease-suffixed tags excluded, `0.0.0` fallback,
  `GITHUB_REF_NAME == "main"` → `{v}+{run}` else `{v}-dev+{run}`, run number from `--run-number`
  or `GITHUB_RUN_NUMBER`); HOW to stamp = the ProjectSettings writer (all that remains of
  `versioning.py`); TRANSPORT = an explicit parameter — `--version <string>` on both build verbs
  (replacing `--stamp-version`), an optional `version` input on the hosted workflow
  (SHA-pin compatible), the consumer's workflow bridges. Moving the ledger into ci-devkit was
  considered and rejected: ci-devkit is runner/step/cache floor with no version semantics;
  release-devkit cuts the tags and owns the concept. `AndroidBundleVersionCode` stays the run
  number (a CI fact, no ledger).

Cross-repo execution: release-devkit `08568e9` (verb + six tests; ruff/basedpyright/pytest-91
green) + `709db9f` (AGENTS Commands row, README boundary paragraph) — 2 ahead of origin. CT
`fa66c10` (catalog keyless; ci.yml grows a `resolve-version` job — fetch-depth 0 for the tag
ledger, `uvx --from release-devkit==0.1.17 app-build-version --app CaptureTool` — feeding the
hosted workflow's `version` input; the whole input migration done in the same edit: dead
`build-env:` dropped, pin moved off `cfd487e`) + `add6364` (READ_LOGS manual in both AGENTS) +
`b77c62a` (repin after the flatten) — 8 ahead on `dev`; its dirty Unity assets and
`extraction-plan.md` left untouched, as found. unity-devkit gates: ruff, basedpyright 0/0,
pytest 40 (net −3 by design: the ledger test file, one versioning test, one resolve test).

Assumptions on record: CT's `release-devkit==0.1.17` pin presumes the next release-devkit patch
is `0.1.17` (one-word fix at the pin if not); CT's workflow pin is `d7bb6ba` — repin if devkit
history moves again before the operator push; CT's CI hard-requires the devkit push to land
first (pin + input surface), consistent with the established gating. Still open from earlier
sessions, owner-side: the MIS panel-budget arithmetic (21 vs 22 of 25) and the session-8
platform-dropdown question (filter to `config.Platforms.Keys` vs vocabulary-wide).

Next session: verify the operator pushed unity-devkit (main 53 ahead, HEAD `d7bb6ba`) and
release-devkit (2 ahead, HEAD `709db9f`), and that the releases landed — devkit's dual-registry
release and release-devkit's `0.1.17` carrying `app-build-version` — then CT's gated remainder
per Phase 6, now shrunk to: npm pin swap off the local `file:` pin, dispatch workflow generation
+ drift gate, APK smoke (`aapt` versionName/Code vs the stamp — first live proof of the
version-input path end-to-end), and the Phase 1 acceptance probe.

## Status (2026-09-27, session 9 close — Phase 5 complete)

Phase 5 executed in full: the Python half plus the release preparation. Landed:

- **Transport + child-env control.** `run_unity_batchmode` grew an `env` parameter (a bashrun overlay — never
  `os.environ` mutation) and now returns the captured log path. `unity.py` gained
  `parse_environment_fields` (newline/repeatable `path=value` → dict, split on first `=`, loud on bare
  paths) and `playerbuild_environment` (builds the entry contract: `PLATFORM` and `DEVELOPMENT` always,
  `ENVIRONMENT`/`ENVIRONMENT_FIELDS` only when non-empty — unset stays ambient no-op). Build names ARE
  platform names (see the consolidation below); `resolve_unity_build` returns the 3-tuple.
- **Doors.** `compile-unity`: `--development` bool flag, `--environment-preset <name>`, repeatable
  `--environment-field path=value`. `build-unity`: `--environment-preset`, `--development` (bool flag —
  owner ruling: the CLI is typed, the consumer renders; the workflow emits
  `${{ inputs.development && '--development' || '' }}` and simply omits the flag for release — no
  `--no-development` spelling exists), `--environment-fields` (newline `path=value` — the
  shape the generated dispatch workflow emits). `--build-env` and its KEY=VALUE loop are deleted.
- **`unity-build.yml`**: `build-env` input replaced by `environment`/`development`/`environment-fields`
  (repo-agnostic — per-field inputs live only in the consumer's generated wrapper). Known consequence on
  record: CT's unpushed ci.yml still passes `build-env:` and will error against the new input surface
  until its Phase 6 remainder migrates — expected; that work is gated on this release anyway.
- **`unity-dispatch`** (new verb, `dispatch.py`): runs the dump door
  (`Outernet.PlayerBuild.DumpEnvironment`, class pointer from `--environment-config-class` or the
  project's `build-config.json`), extracts the payload structurally (log line parsing as a JSON object with
  `class_name` — no magic-string coupling), validates into a forbid-extra pydantic model, renders static
  YAML: preset choice (leading empty option = unset = ambient no-op) + development boolean + one input
  per simple-typed field — bool → checkbox, non-flags enum → choice (empty option first), flags enum →
  comma-separated text, string/number → text; the mode field dedupes into the preset choice; field input
  ids are dot→dashed and referenced with bracket notation (`inputs['localConfig-apiUrl']` — dotted ids
  would parse as property access minus). The build job calls the hosted workflow through the required
  `--build-workflow` pin (the consumer's cross-repo `owner/repo/.github/workflows/unity-build.yml@sha`,
  CT's shape at its ci.yml:82 — the first cut wrongly emitted a local `./.github/workflows/` path,
  caught at handoff against CT's existing pin and fixed before any flip). Loud past the 25-input cap
  and on unknown field types.
  `--check` regenerates and diffs — the F20 drift gate for consumer CI. The transport forwards only
  non-empty inputs (per-field `inputs['id'] != '' && format('path={0}', …) || ''` lines); boolean fields
  transport only when checked (checkbox = opt-in override; forcing false goes through the CLI door).
- **Tests** (43, up from 27): generator render assertions (dedup, type mapping, bracket refs, transport
  lines, cap, unknown type, determinism, pinned `--build-workflow` uses/header, YAML validity via
  pyyaml — added to the root dev group,
  test-only), extraction, field parse, child-env contract, and the build-target resolve. The fixture dump
  JSON is committed at `tests/fixtures/environment-dump.json` — captured live this session from the real
  door against `FixtureEnv` (6000.0.66f1), not hand-written.

Proven live in this sandbox, not just by tests: the dump door through `check-unity` with
`ENVIRONMENT_CONFIG_CLASS` inherited by the child; `unity-dispatch` end-to-end against the harness
(generated workflow eyeballed: choice/checkbox/number/flags rows, dedup, `${{ }}` expressions intact —
an f-string collapsing `{{`→`{` was caught and fixed by rendering transport lines through
concatenation); `--check` green on the same file, red on a one-line drift. Gates: ruff, basedpyright,
pytest 43, `check-unity` compile + env self-test green, CSharpier clean (no C# deltas — Python-only
phase). Docs: AGENTS.md gained the `unity-dispatch`/`build-unity` rows and the environment-transport
constraint; README command catalog updated.

Open arithmetic, flagged not fixed: §Environment model's panel budget line says "19 fields + 3 controls
= 22 of 25" for MIS, but the generator emits 2 controls (preset choice + development toggle) — MIS
would count 21. No third control is derivable from the panel rules; if the owner has one in mind
(runner-labels passthrough, platform selector), it is one input away.

Vocabulary amendment (owner-directed, same session, before any release froze the names): bare
`environment` became `environment_preset` in every Python-facing spelling — the bare name collided
with GitHub's `environment` input type in the panel; the generated dispatch input id and the hosted
`unity-build.yml` input followed (`environment-preset`, hyphenated ids ride bracket notation in
expressions — `inputs['environment-preset']`, subtraction would otherwise parse); the generator's
class override became `--environment-config-class`, matching the `ENVIRONMENT_CONFIG_CLASS` door var
verbatim; and the transport builder was renamed `child_environment` → `playerbuild_environment` —
naming the contract's consumer (the C# entry), not the process-tree vehicle, after the "child" +
"environment" pairing read as process jargon. The transport env vars themselves (`ENVIRONMENT`,
`ENVIRONMENT_FIELDS`) keep the Phase 3 C# spellings.

Name consolidation (owner ruling, same session): **build names are platform names** — the catalog
`builds` keys, the workflow matrix `platform` values, and the C# `Platform.Table` keys collapsed to one
spelling (`AndroidMobile`, `MagicLeap2`), killing the `playerbuild_platform` mapping field; `Linux`/
`Windows` replace `linux64`/`win64` to reserve their future table names; `build_flag` became
`build_target` holding the bare editor target (`Android`, `StandaloneLinux64`, `Win64`) with
`-buildTarget` composed at the two call sites, matching `check-unity`'s existing `--build-target`
vocabulary. `PLATFORM` rides every child env — inert for consumer-owned entries, loud under Entry
misuse. The unityci image-module field became `unityci_image_module` (emitted matrix key
`unityci-image-module` — unconsumed by any hosted workflow, verified), and `LICENSE_MODULE` became
`LICENSE_IMAGE_MODULE`. Consumer fallout (all pre-release, all local-unpushed): CT and MIS catalogs
re-keyed (CT `9df7ae9` on dev, 5 ahead; MIS `6cd6ae7` on dev, 4 ahead — MIS's unrelated dirty
`.env.airgapped` left uncommitted); artifact names change case (`CaptureTool-AndroidMobile`); ORAS
cache tags miss once.

The release (one devkit release carrying both registries) rides the operator push: main is 45 ahead of
origin (31 entering the session — 29 prior plus the owner's mid-session `b7b77fd`/`2559e0a` window-fix
pair — then this session's 13 rename/feature commits `af1cd5a`..`e19a5cb` in code/prose pairs, plus this
close) → push → CI → `release.yml` publishes PyPI `unity-devkit` + npm `org.outernet.playerbuild`
(path-diff covers `packages/python/unity-devkit`; the hosted workflow edits ride the SHA pin, not a
ledger). CT's gated remainder then rides the release: CI `--environment-preset` migration + ci.yml input
fix, npm pin swap for the local `file:` pin, dispatch workflow generation + drift gate, APK smoke, the
Phase 1 acceptance probe. Phase 6's flip list otherwise unchanged.

Pinned rename executed this session, name amended past the pin by the owner: `dispatch.py` →
`dispatch_workflow_generator.py` — `dispatch_generator` was judged insufficient (dispatch of what?)
and `github_workflow_dispatch_input_yml_generator` correct but unwieldy; the landed name is the
maximal compression keeping the load-bearing words — workflow (the artifact kind), dispatch (the
panel variant), generator (the role) — and dropping the redundant ones (github: the devkit is
GitHub-native; yml: workflows are YAML by definition; input: implied by a dispatch workflow). Verb
stays `unity-dispatch`; entry point is `unity_devkit.dispatch_workflow_generator:app`; pyproject
script line, AGENTS table row, and the test module (`test_dispatch_workflow_generator.py`, the
`test_<module>` mirror) followed. Zero behavior change; module paths aren't pinned API, and it rides
the same release for tidiness.

Next session (updated after the rename landed): verify the operator pushed and the release landed
(both registries), then CT's gated remainder per Phase 6.

Next-session pointer superseded by the session-10 close above; retained for the record.

## Status (2026-09-27, session 8 close — pane NRE root-caused and fixed)

Owner smoke found a live bug: after clicking Apply, the environment pane rendered
`NullReferenceException: Object reference not set to an instance of an object`. First the
catch had rendered type+message with no console log (anti-spam choice) — fixed in `ecce7ca`:
the pane's catch also `Debug.LogException`s the full stack whenever the error text differs
from the previous frame's. The owner then landed a full repro with stacks, pinning it:

- The trigger: the platform dropdown offers every table name; picking **MagicLeap2** in CT
  (whose config declares only AndroidMobile) and clicking Apply runs `ApplyPlatformFacts`
  first — writing the MAGIC_LEAP defines, which schedules an asset-database refresh + script
  recompile — then `PlatformFor` throws `BuildFailedException` (undeclared platform), which
  escaped `OnGUI` raw (console IMGUI error, window pattern broken).
- The NRE: during the refresh window, the pane's per-frame
  `AssetDatabase.LoadAssetAtPath` icall throws NRE **from native code mid-refresh** — the
  managed stack shows only the calling line, which is why it looked like our null deref.
  Transient by nature; heals when the refresh settles (matching both owner episodes,
  including the one that "went away on its own").

Fixes (`b7b77fd`, CSharpier + `check-unity` + env self-test green): the pane early-outs while
`EditorApplication.isCompiling || isUpdating` (no AssetDatabase calls from OnGUI during
refresh windows — kills the NRE at its trigger); `EnvironmentConfig`'s ctor guards its two
`!`-null cases with explanatory `BuildFailedException`s (missing script; script resolving no
class — amends the session-4 "no guard blocks" ruling for exactly these two cases, which the
window hit as bare NREs in normal operation; the `Single()` malformations stay
inscrutable-by-ruling); the Apply button's failure renders as the window's error box via
`ApplyFromGui` (try-owning helper, the `LoadConfigForGui` pattern) instead of throwing
through OnGUI.

**Open design question for the owner**: the platform dropdown lists all `Platform.Names()`,
so CT's window offers MagicLeap2 its config never declares — the repro's underlying trap.
Options: filter the dropdown to `config.Platforms.Keys` (config is the declared intent; the
table stays vocabulary) or keep it vocabulary-wide with the in-window error as the guard.

## Status (2026-09-27, session 7 close — CT Unity flip pulled ahead of Phase 5)

Owner reorder: Phase 6's Unity half executed first, so the configure window is visible in a real
editor — Phase 5 (Python) still follows; its remaining flip items stay gated on it. The package
reaches CT by a **local `file:` pin** (owner decision) — `org.outernet.playerbuild:
file:../../../../unity-devkit/packages/unity/PlayerBuild/Assets/Package` in CT's manifest
(relative `file:` paths anchor at the project's `Packages/` folder — three ups reaches CT's repo
root, four reaches the workspace sibling; learned by a failed resolve). The npm pin swaps in at
the Phase 5-gated finish. CT commit `f3a3d5b` on `dev` (4 ahead, unpushed with the rest of the
punt):

- `CaptureEnv : ScriptableObject` at `Assets/CaptureEnv.cs` (file named for the class — the
  `GetClass` rule) in `Placeframe.Client`: fields apiUrl/username/password, enum
  `{ Airgapped, Override }`, `Presets = { Airgapped → Assets/BuildConfigs/CaptureEnvAirgapped.asset }`,
  `TargetPath = Assets/_LocalWorkspace/Resources/CaptureEnv.asset`. No `Default` member —
  today's CONFIG_TYPE=default maps to ambient no-op: no live asset → SettingsManager's
  hardcoded-fallback tier, which is exactly today's default behavior (fresh CI checkouts get
  the same; a dev machine that applied airgapped keeps it until switched — the model's intent).
  `Override` exists so the map complement has a member (window hand-edit + future per-field
  doors); the runtime ignores the mode entirely.
- Committed preset `CaptureEnvAirgapped.asset` hand-written in fixture-asset YAML form (mode
  `Airgapped`, apiUrl `http://192.168.8.10:58080`, user/password) with minted-GUID metas;
  imported clean by the gate session (log-verified). `airgapped-settings.json` deleted.
- `SettingsManager`'s baked branch: `Resources.Load<TextAsset>("default-settings")` +
  SimpleJSON → `Resources.Load<CaptureEnv>("CaptureEnv")` seeding the three `StateValue`s; the
  `persistentDataPath` write-back chain and hardcoded fallbacks untouched (F35 shape).
- `build-config.json` at the CT project root: `environment_config: "Assets/CaptureEnv.cs"`,
  `platforms["AndroidMobile"]` empty overrides (no pipeline/defines — matches today's globals).
- Catalog `execute_methods` → `Outernet.PlayerBuild.Entry`; `BuildScript.cs` deleted. CT's
  ci.yml still passes `build-env: CONFIG_TYPE=default` — inert under Entry (unused env var ≡
  ambient no-op ≡ default), and unpushed anyway; air-gapped dispatch needs Phase 5.

Gates: `check-unity` compile gate on CaptureTool green (file: package resolved, package asmdef
compiles against CT's assemblies, lock regenerated with playerbuild + openxr 1.16.1); the dump
door run against the real class — `ENVIRONMENT_CONFIG_CLASS=Assets/CaptureEnv.cs
--execute-method Outernet.PlayerBuild.DumpEnvironment` emits the full contract JSON (class,
mode field, preset map, enum, fields) — the reflection path proven in the consumer, not just
the fixture. Editor look pending for the owner (sandbox has no GUI): open `apps/CaptureTool`,
`Window > Player Build` — pane appears between Development and Last applied; picking Airgapped
copies the preset to `_LocalWorkspace`, Override makes fields hand-editable.

Ruled and reversed this session — do not relitigate: dropping playerbuild's
`com.unity.nuget.newtonsoft-json` dependency (feared a duplicate-assembly clash with CT's
NuGetForUnity copy) — false premise: CT's own committed `zedcaptureclient` local package
already declares the same UPM dependency and has coexisted with the NuGet DLL under green CI.
Removed and reverted same session (devkit commits `668f8ef` + `1ec4089`); the dependency
stays. Local player builds through Entry are Phase-5-gated: `compile-unity` passes no
`PLATFORM`/`DEVELOPMENT` transport today — the window (direct `Apply` call) is the working
editor door, as the reorder intended.

Next session executes **Phase 5** (Python flags + dispatch generator + `--build-env`
deletion; the devkit release), then CT's gated remainder (CI `--environment` migration,
dispatch workflow, APK smoke, the Phase 1 acceptance probe) rides it.

## Status (2026-09-27, session 6 close — Phase 4 complete)

The configure window grew the mode-aware environment pane per §Environment model's derived
window rules, against the session-5 vocabulary (`ConfigureWindow.cs`, +122 lines). The pane
renders only when `build-config.json` carries `environment_config`; the resolved
`EnvironmentConfig` is cached per class path in window fields (wiped on domain reload); the
live asset at `TargetPath` is held as a `SerializedObject`, recreated on class-path change and
after every preset application (the copy replaces the asset).

- Mode selector = index popup over the map's key enum names; current value derived from the
  live asset's mode property each frame (stateless — the asset is the truth), empty when no
  live asset exists.
- Preset selection (map member) = `PlayerBuild.ApplyEnvironment(classPath, name, {})` — the
  same function the batchmode door calls; copy + mode travel + save.
- Non-preset selection = mode-only write, inline in the pane (`Enum.Parse` → `intValue`,
  `ApplyModifiedProperties`, `SaveAssets`) — no new application function (single callsite,
  rule 1). With no live asset it is a no-op under the standing warning box.
- No live asset → warning box ("select a preset to create it"); preset picks still work (the
  copy creates the asset) — the fresh-checkout reality, since `_LocalWorkspace/` is gitignored.
- Preset mode → fields inside `EditorGUI.DisabledScope`, banner "edits here are overwritten by
  the next preset application; switch to a non-preset mode to hand-edit"; non-preset mode →
  editable, banner "Hand-edited — nothing overwrites these". Write-lifecycle claims only
  (F34). The banner says "non-preset mode", not the plan's "Override" — the package-never-
  names-Override ruling (session 2) applied to UI copy.
- Field rows = `PropertyField` labeled by the reflected `EnvironmentField` paths (the door
  vocabulary is the interface); the mode field is mechanically deduped (it is the selector);
  arrays/objects stay self-excluded (never in `Fields`). Hand edits in non-preset mode persist
  via `ApplyModifiedProperties` + `SaveAssets` on change.
- Stale-asset rows (mode or field absent from the live asset) and env-class resolution
  failures render as the pane's error HelpBox — a base-`Exception` catch at the OnGUI
  boundary (a long-lived event loop, the sanctioned boundary shape), type + message, no
  per-frame log spam.
- The Apply button stays platform-only (`""` + no fields): the pane materializes environment
  state immediately on interaction, so a full Apply re-enters `ApplyEnvironment`'s no-op gate
  — harmless by construction.

Accepted edge on record: re-picking the already-selected preset is a no-op (IMGUI popups
report no change); a preset re-copy is two clicks (switch away and back). No machinery added.

Gates: CSharpier clean; `check-unity` compile gate green; the env self-test door re-run green
(preset copy + six overrides + read-back unchanged). Hand-smoke against the harness fixture is
**pending for the owner** — it needs a GUI and a temporary `build-config.json` in the harness
(`environment_config: "Assets/Editor/FixtureEnv.cs"` + a platforms entry), which the harness
deliberately never commits; delete it after the smoke.

Next session executes **Phase 5** (Python flags + dispatch generator + `--build-env`
deletion; one devkit release) per the phase list. Commits: `2a6658f` (package) plus this plan
commit — local on main; operator handoff.

Next-session pointer superseded by the session-7 close above (Phase 5 unchanged; the CT Unity
flip landed early); retained for the record.

## Status (2026-09-27, session 5 close — design cleanup + repo reorg; Phase 4 untouched)

No Phase 4 work; the session was owner-directed design cleanup of the Phase 3 output plus a repo
reorganization. Six commits, all local on main (21 ahead of origin with this one); operator
handoff. Every commit gated: CSharpier, `check-unity` compile, env self-test green; the reorg
additionally re-verified `uv sync`, pytest (27), ruff, basedpyright — all through the new layout.

Package deltas (all inside `PlayerBuild/Assets/Package/Editor/`; the npm path is unchanged):
- **`EnvironmentShape` is dead — the data class is `EnvironmentConfig`**, resolved by
  `new EnvironmentConfig(classPath)` (the constructor is the old `ResolveEnvironment` body; the
  static resolver class is gone). Symmetry with `BuildConfig`: two config objects, each
  materialized by a mechanism (JSON parse / reflection). The no-op gate in `ApplyEnvironment`
  still precedes construction — a class-less config with unset env must build; doors do not
  resolve eagerly.
- **The dump is split**: instance `EnvironmentConfig.Dump()` (emit only) + static door
  `PlayerBuild.DumpEnvironment()` beside `Entry`. The executeMethod spelling for Phase 5's
  generator and drift gate is `Outernet.PlayerBuild.DumpEnvironment` (nothing external had wired
  the old spelling). `EnvironmentConfig.cs` is now the pure observer — zero references to
  `PlayerBuild`.
- **`EnvironmentFieldLeaf` → `EnvironmentField`** (`CollectEnvironmentFields` follows). The
  "leaf" vocabulary is dead everywhere; the door dialect (error strings, `ENVIRONMENT_FIELDS`,
  `--environment-field`) was always "field". Tree walk unchanged — nested classes recurse (real
  today: `localConfig` in the fixture and MIS), arrays/Object-refs/IList self-exclude.
- **`Platform.cs` is a new file**: the `Platform` static class (table + `Find`/`Names`) with
  nested `Spec` (was `PlatformSpec`) and nested `Record` (was `PlatformRecord`). Amends the
  package-shape line "the table is vocabulary, not a document — it lives in PlayerBuild.cs":
  the package is now one-concept-per-file, and `PlayerBuild.cs` holds doors + orchestrator +
  apply family + verification.
- Ruled and rejected this session — do not relitigate: merging `BuildConfig.cs` +
  `EnvironmentConfig.cs` into a `Config.cs`; moving `BuildVerification` out of `PlayerBuild.cs`
  (it stays beside `Verify`; `SerializableBuildReport.cs` remains pure report DTOs). Tidy left
  on the table: `BuildConfig.EnvironmentConfig` property → `EnvironmentClassPath` (JSON key
  `environment_config` unchanged) — the property and the type currently share a spelling.

Repo reorg, matching placeframe's monorepo shape: `packages/python/unity-devkit/` (member
pyproject + `src` + `tests`; the root pyproject is a uv workspace shell holding the dev group,
basedpyright, pytest, preflight tables) and `packages/unity/PlayerBuild/`. Catalog path,
`release-devkit.json` (both package paths), `.gitignore`, `ruff.toml` updated; the workflows are
catalog-driven and needed no edits; the `--project PlayerBuild` contract is unchanged. The next
release's path-diff sees the wholesale moves — expect patch bumps on both ledgers (accepted
tier, same as the 0.1.12–0.1.14 burns).

Next session executes **Phase 4** (configure window, environment pane) per §Environment model's
derived window rules, against the new vocabulary (`new EnvironmentConfig(path)`,
`Platform.Spec`, `Platform.Record`). The §Package shape section's file listing predates this
session — this record's deltas govern.

Next-session pointer superseded by the session-6 close above; retained for the record.

## Status (2026-09-27, session 4 close — Phase 3 complete)

Phase 3 executed in full (env core, package C#), then owner-reviewed into a leaner shape across the
session. Landed: `EnvironmentBuild.cs` — the whole env subsystem in its own file (owner directive:
env machinery out of `PlayerBuild.cs`) — holding `DumpEnvironment` (executeMethod; class pointer
from `ENVIRONMENT_CLASS` or config), `ReadEnvironmentFields` (`ENVIRONMENT_FIELDS` JSON → dict),
`ApplyEnvironment`/`ApplyEnvironmentPreset` (preset copy + mode travel + override writes), and
`ResolveEnvironment` + leaf collection. `PlayerBuild.cs` dispatches at two points (RunBuild's read,
Apply's call); `BuildConfig`'s env content is the one-string class path; the window's JSON-model
env pane is stripped (Phase 4 rebuilds it). Package net −168 lines.

Session rulings that reshape the plan text — do not relitigate:
- **The apply family lives in `PlayerBuild.cs`; `EnvironmentConfig.cs` never mutates state.**
  `ApplyEnvironment`/`ApplyEnvironmentPreset` sit with `ApplyPlatformFacts`/`ApplyXr`/`ApplyPipeline`/
  `ApplyAdditionalDefines` (the orchestrator's five steps co-located, per the owner's rule-7
  ownership reading); `EnvironmentConfig` (renamed from EnvironmentBuild) is purely the observer
  half — reflect the class into a shape, emit the dump. The `ENVIRONMENT_FIELDS` parse
  (`ReadEnvironmentFields`) lives with the entry in `PlayerBuild.cs`, and the leaf-value parse is
  inlined at its single call site in the apply loop. Amends the session's earlier whole-subsystem
  split.
- **Resolve has no guard blocks.** `Single()` selections are the only check; every malformation
  (missing file, no class, wrong `Presets` shape, missing `TargetPath`, absent/duplicate mode
  field) degrades to a loud inscrutable BCL exception at the entry boundary. The owner accepted
  this class explicitly; the silent classes were analyzed and closed (two fields sharing the key
  enum type — the one genuinely silent case — makes `Single` throw).
- **Parse/write ride the BCL**: enums via `Enum.Parse` (names, flags commas, numerics,
  ignoreCase) → `intValue`; everything else `Convert.ChangeType(..., InvariantCulture)` →
  `SerializedProperty.boxedValue`. The hand-rolled parser, the per-kind switches, and the
  custom leaf-kind enum are gone; leaf classification is `IsPrimitive || string || IsEnum`.
- **The dump emits facts, not taxonomies**: per-leaf `path` + `field_type` (the .NET type name);
  the `enums` section carries names/values/flags. The `kind` vocabulary is dead — Phase 5's
  generator derives input types mechanically from `field_type` × `enums`.
- **`PlayerBuild.Verify` stays platform-only.** Owner ruling: its mandate is ambient state vs
  declarative intent (table + record, cross-session); env intent is session-scoped env vars, so a
  preprocessor env row could only ever re-verify the same session's apply — a self-consistency
  check wearing a guard's badge. The env read-back lives in the self-test as independent typed
  assertions. **Supersedes session 2's "the shared check grows the env rows"** and Phase 3's
  read-back clause as written.
- **The dump emits bare JSON, no log marker.** The payload is its own discriminator (a log line that
  parses as a JSON object with `class_name`); Phase 5's generator extracts structurally — schema
  coupling instead of a magic-string spelling shared across two languages.
- `ENVIRONMENT_CLASS=""` throws (loud) instead of falling back to config — the `??` collapse of
  the empty-string edge; no door sets it empty. The env var itself is spelled
  `ENVIRONMENT_CONFIG_CLASS` (renamed from `ENVIRONMENT_CLASS`).

Fixture (harness-side, never shipped — outside `Assets/Package/`): `FixtureEnv.cs` (the env class
in a file named for the class — `MonoScript.GetClass()` resolves by filename; the first attempt was
one file named `EnvironmentFixture.cs`, GetClass fell back to the first-declared enum, and the
resolve died loudly at `Presets` — the split mirrors the MIS consumer layout) +
`EnvironmentFixtureSelfTest.cs` (driver: sets the env-var door in-process, runs dump → apply →
typed read-back against known constants through Unity's own deserializer; `CreatePresetAsset`
regenerates the committed preset, which deliberately stores `configMode: Supabase` so mode travel
is asserted). Preset and metas were generated by real editor sessions.

Gates ran locally (6000.0.66f1): compile gate clean after one fix (`using System.Collections` for
`DictionaryEntry`); self-test green — dump JSON captured (flattened dotted paths, arrays
self-excluded, flags bit present), preset copy with case-insensitive `airgapped`, six overrides
applied, read-back proved mode travel. `boxedValue`, `GetInterface`, and `ChangeType` are proven
at runtime. CSharpier formatted.

CI: `unity-check.yml` gains an optional `execute-method` input plus a conditional second
check-unity session (skipped when empty — SHA-pinned consumers unaffected); devkit's `ci.yml`
passes `Outernet.EnvironmentFixtureSelfTest.Run`.

Known edges on record (accepted): a JSON `null` value in `ENVIRONMENT_FIELDS` converts silently to
a null write (degenerate door misuse); a `Presets` declared as the `IDictionary<,>` interface
rather than the concrete `Dictionary<,>` fails at the mode-field `Single` (MIS form is concrete).

Next session executes **Phase 4** (configure window, environment pane) per §Environment model's
derived window rules. Commits: `59ee5b5` (package), `8dd4a0b` (fixture + CI), plus this plan
commit — all local on main with the three pending plan commits; operator handoff.

Next-session pointer superseded by the session-5 close above; retained for the record.

## Status (2026-09-27, session 3 close — plan restructured; no code)

Plan surgery only; no code changed in any repo. The environment amendment split out of the
release phase — env core (3), configure window (4), Python + release (5) — and all phases
renumbered 1–8 (mapping in the restructure paragraph above). Two rulings recorded: the
harness reflection fixture is in (F6/F8 amended to its spirit — the package depends on no
harness state; a reflection target is test tooling, not config), and npm-only intermediate
releases after Phase 3 are acceptable (unset environment is a no-op; consumers npm-pin at
flips; the npm CI channel has never succeeded end-to-end and an intermediate proves it
cheaply). The PyPI path-diff counts prose, so pushing the pending plan-only commits may
burn a codeless patch number — cosmetic, accepted (same tier as the 0.1.12–0.1.14 burns).

Next session executes **Phase 3 only, in full, nothing else**: the env core in package C#
inside `PlayerBuild/` — dump executeMethod, env-member resolution, preset copy + field
apply, verification read-back, entry env-var transport, the harness reflection fixture.
No window (Phase 4), no Python, no release (Phase 5). Propose → owner instruction → edit,
per the process protocol. This session's commit joins the pending plan commits on local
main for operator handoff.

Next-session pointer superseded by the session-4 close above; retained for the record.

## Status (2026-09-27, session 2 close — environment pivot locked; design only, no code)

Session 2 was design-only: no code changed in any repo; the registries and pushes below
are untouched. This document now carries the environment amendment (§Environment model,
the pivot paragraph above, phases V/CT/MIS, facts F32–F36, the superseded list).

Superseded by the session-3 list above; retained for the record.

Next session, in order (amends the session-close list below; Phase V remains verified
absent in the fold release — no typed flags, no child-env control, no dispatch generator,
`--build-env` still alive end-to-end):
1. **Implement the environment amendment + Phase V** in `/workspace/unity-devkit`.
   Package C# (rides the same release via npm): dump executeMethod; env-member
   resolution (`Presets`/`TargetPath`, name+shape matched, loud on
   absent/mismatched/ambiguous); preset-copy + field apply with reflection validation;
   verification read-back of env values; mode-aware window (map-complement gating,
   banners, preset-dropdown = mode + copy). Python: typed
   `--environment`/`--development`/`--environment-field` flags; JSON
   `ENVIRONMENT_FIELDS` transport; child-env control; dispatch generator verb
   (dump-fed; panel rules in §Environment model); `--build-env` deletion end-to-end
   (`build_unity.py` + hosted `unity-build.yml`). One devkit release carries both
   registries; version = next patch after 0.1.15; preflight battery, `check-unity`,
   CSharpier gate it.
2. **Phase CT** — now opens with the MIS-shape conversion (`CaptureEnv`,
   `SettingsManager` rewire, `airgapped-settings.json` deletion; see phase list), then
   the flip items; still includes the open Phase I acceptance probe (hand-vandalize an
   applied global, build, expect the loud "run Apply" preprocessor failure; the harness
   cannot host it — no `build-config.json` by design). Push subject to the
   consumer-push punt below unless the operator carves an exception.
3. **Phase MIS**, then **Phase C** — same punt consideration.

## Status (2026-09-27, session close — push queue remains, then the consumer flips)

Phase I complete (`f3046b9`, `4c72500`, `207cd42`). Phase F executed and mostly landed.
Phase V's release landed as **0.1.15** (0.1.12–0.1.14 are collision-burn duplicates — each
release re-run died at the playerbuild npm collision and burned a devkit patch; root cause
was the unpushed `playerbuild-v0.1.0` ledger tag vs the operator's manual npm first publish).
An org-wide compile-check rollout grew out of the fold (six repos now gate their Unity code
through unity-devkit's hosted `unity-check.yml` — architecture documented in devkit's
AGENTS.md). One release-devkit bug fixed along the way (npm 11's version-conflict wording
escaped the idempotent publish skip).

Live on the registries:
- npm `org.outernet.playerbuild@0.1.0` (manual first publish by the operator). The trusted
  publisher for devkit's `release.yml` appears bound — the workflow's npm attempt reached a
  version conflict, not an auth failure. Verify on the npm settings page at leisure.
- PyPI `unity-devkit 0.1.15` — carries the fold (`PlayerBuild/` harness + package), the
  `unity-check-matrix` verb, and the hosted `unity-check.yml` + `unity-prepare.yml` +
  `.github/actions/unity-container-prep` dedup scaffold. devkit CI is green on `e9058f6`
  including the container-wrapped compile-check (self-hosted runners supply Docker; the
  `unityci/editor:<ProjectVersion>` container supplies the editor).

Operator push queue — items 1–3 are DONE and verified (2026-09-27):
1. ~~devkit ledger tags~~ — `playerbuild-v0.1.0` (→ `2a1b63f`) and `unity-devkit-v0.1.15`
   (→ `e9058f6`) confirmed on origin.
2. ~~Re-run the failed devkit Release run~~ — succeeded; the ledger is whole.
3. ~~release-devkit main~~ — pushed; self-release green; **`0.1.16` live on PyPI** with the
   npm-11 idempotency fix (inert until consumer `release-devkit==0.1.14` uvx pins bump —
   at leisure, the tags prevent the collision anyway).

Still pending, deliberately deferred (2026-09-27 session close):
4. The five compile-check repos — all on `dev`, my commits sitting ON TOP of pre-existing
   unpushed stacks (audited): placeframe 15 ahead (3 mine + the 12-commit bundle-architecture
   initiative), ObserveThing 3 (release-devkit housekeeping), Nessle 3, StatefulUnity 3,
   lbe-toolkit 5. ObserveThing's untracked WIP (`EventValueOperator` + `Operators/`) is
   declared irrelevant by the owner — leave it untracked, do not commit or re-flag it.
5. unitybuild retirement (`0d35c9f` → `a0c2c0a`), then archive.

**Operator decision (2026-09-27): all consumer pushes are punted** — everything except
unity-devkit and release-devkit (the five repos above AND this plan's original repo,
unitybuild, whose retirement commits `0d35c9f`→`f7d1f98` were never pushed) waits
until a separate initiative completes, then lands as **one PR per repo** consolidating the
stacked work. Until then: no pushes to placeframe, ObserveThing, Nessle, StatefulUnity,
lbe-toolkit, or unitybuild.

Next session, in order (superseded by the session-2 list at the top of Status; retained
for the record):
1. **Phase V is OPEN WORK, verified absent (2026-09-27)** — the devkit pushed with the fold
   carries none of it: no typed `--environment`/`--development`/`--environment-field`
   flags, no child-env control, no dispatch generator verb, and `--build-env` still alive
   end-to-end (`build_unity.py` + hosted `unity-build.yml`'s `build-env` input). The 7
   commits riding with the fold were `check-unity` tooling. Implement Phase V in
   `/workspace/unity-devkit` (Python; preflight battery gates it) — the CT/MIS flips
   block on it. The "0.1.12" naming below is moot; the release will be the next patch
   after 0.1.15.
2. Phase CT — the capture-tool flip, including the still-open Phase I acceptance probe
   (hand-vandalize an applied global, build, expect the loud "run Apply" preprocessor
   failure; the harness cannot host it — no `build-config.json` by design). Note CT's own
   push is subject to the consumer-push punt above unless the operator carves an exception.
3. Phase MIS, then Phase C — same punt consideration.

Session-3/4 delta ledger (git history carries the full text): deltas 7 (bare-path presets,
ambient no-op), 8→9→10 (application functions consolidated into `PlayerBuild.cs`,
parameterless `RunBuild`, dumb DTOs), 11 (resolution/loading in `PlayerBuild`), 12
(`Activate`/`Write` split) — 3, 4, 6, 11, 12's authoring halves are moot with the spine;
7, 9, 10's spirit survives into rewrite 3.

## The architecture

### The table is the whole truth

One C# table — `Platform.Table` (vocabulary at the top of `PlayerBuild.cs`), keyed by platform
name — states every
platform fact once: identity defines, `XrLoader` string + OpenXR feature list, graphics
API, architecture, normal-map encoding, texture subtarget, and the dev/release columns
(IL2CPP configuration, managed stripping, API compat). **No Build Profile assets ship.
No assets are generated.** Consumers run Unity's auto-created, snapshot-less default
profile and never hear about it from us.

### Application — one implementation, every door

**Apply** = write the table's facts to ambient global state: `PlayerSettings` static APIs
(defines, graphics API, encoding, architecture, columns per dev/release, API compat),
`EditorUserBuildSettings.androidBuildSubtarget`, the XR loader sweep + OpenXR feature
toggles, render pipeline assignment, `additional_defines` merge, environment
materialization (preset copy into `TargetPath` + reflection-validated SerializedObject
field writes — §Environment model) — then write the platform record. Three callers: the batchmode entry (facts from env vars), the
configure window's Apply button, and — at the MIS flip — the rewired bundle-bake entry
points (facts for the bake's platform).

The entry sequence: read env vars → find spec → load config → apply everything (order:
platform facts, environment, XR, pipeline, defines) → classic
`BuildPipeline.BuildPlayer(BuildPlayerOptions)` → report → exit. The dev bit rides
`BuildOptions.Development`; scenes come from the enabled global list. The first-build
OpenXR failure ("not yet loaded. Please build again.") is retried once (F27).

### The platform record

`Assets/_LocalWorkspace/platform.json` records the platform + development column last
applied. It exists for the editor door and the bake guards; CI never reads it (the entry
knows the platform from env vars). It is the single intent carrier — the thing that makes
"forgot to Apply" loudly detectable.

### Verification — the guard

An `IPreprocessBuildWithReport` callback (runs for every player build from every door)
and a shared check function called at the top of every bake entry point. **Reads only** —
writing defines mid-build triggers a recompile and aborts the build. For each table fact,
read the *effective* value and compare against the table for the recorded platform:

| Fact | Effective-value read |
|---|---|
| defines | `GetScriptingDefineSymbols(Android)` ∪ active profile's `scriptingDefines` |
| scenes | `BuildProfile.GetActiveBuildProfile().GetScenesForBuild()` vs enabled global list |
| graphics API / architecture / encoding / columns / stripping / API compat | facade `Get*` calls |
| subtarget / dev bit | `EditorUserBuildSettings.*` |
| XR loaders / features / pipeline | their global assets (never per-profile, F10) |
| platform | `report.summary.platform` must be Android |

The facade is the build's own read surface — facade reads return **the value that will
bind in the imminent build**, whichever source currently feeds the facade. Verification is
therefore source-agnostic: a stale snapshot, a hand-edit, a forgotten Apply, a stray
profile define — all surface as the same loud mismatch ("run Apply"). No snapshot
detection, no profile inspection, no YAML parsing. The four gap analyses that led here
are in git history; the residual, unclosable by any architecture: a third-party script
calling `BuildPipeline.BuildAssetBundles` directly.

Why profiles can stay unguarded: if a snapshot is installed on some editor machine, the
facade serves it — Apply's writes land in it, verification reads it back, and a
disagreeing build fails loudly. In CI an installed snapshot is unreachable: activation
state lives in untracked `Library/`, fresh checkouts open Unity's snapshot-less default,
the entry never activates anything, and devkit passes no `-activeBuildProfile` — so
devkit's global version stamp always binds.

### Version discipline

The build doors stamp a caller-supplied `--version` string (verbatim) plus the run number as
`AndroidBundleVersionCode` into global `ProjectSettings/ProjectSettings.asset` pre-batchmode;
nothing exists in CI to shadow it. unity-devkit derives nothing — no ledger queries, no tag
prefixes (the catalog's `tag_prefix` and `versioning.py`'s tag-query clone are dead; the version
ledger is release-devkit's sole concern, exposed for build-time use by its `app-build-version`
verb, and consumers bridge the two in their own workflows through the hosted workflow's `version`
input). On editor machines the ambient version is whatever globals say (as today). No package
involvement.

### Environment model — class-sourced (2026-09-27 amendment; supersedes rewrite 2's carryover)

The consumer's C# env class is the single source of truth for environment shape,
vocabulary, presets, and target. The package never compiles against it and never models
its runtime semantics — it reflects. Nothing about the environment is declared outside
the class.

**`build-config.json`'s entire env content is one string:**

```json
"environment_config": "Assets/App/UnityEnv.cs"
```

**The class is the complete env-system description** — four reflectable things, matched
by well-known member name + shape, failing loudly on absent/mismatched/ambiguous:

| thing | MIS form | match rule |
|---|---|---|
| env shape | `UnityEnv`'s serialized fields/enums | `MonoScript.GetClass()` + reflection |
| vocabulary | the `ConfigMode` enum | the map's key type |
| preset map | `public static readonly Dictionary<ConfigMode, string> Presets` | static `IDictionary<enum,string>`; values = committed preset asset paths |
| live target | `public const string TargetPath = "Assets/_LocalWorkspace/Resources/UnityEnv.asset"` | const/static string |

**No marker attributes.** An attribute is a package type; `UnityEnv` is a runtime class
and the package is editor-only, so attributes would force a package Runtime assembly plus
a consumer asmdef edge — app code depending on build tooling, the wrong direction. The
package must observe the consumer (reflection), never be load-bearing inside it. Magic
names couple conventionally instead: they fail loudly at the dump/apply boundary and the
drift gate, and cost zero machinery. (Unity's own precedent: `Awake`/`Update` are magic
names; attributes are only free from unconditional dependencies like `UnityEngine`.)

**Enum-keyed map**: compile-safe renames in consumer code; one vocabulary shared with the
`configMode` field and `ResolveEffective`; door spellings are enum names,
case-insensitive (`air-gapped` → `airgapped` migrates at the flips); `Override` is
structurally not-a-preset by absence from the map. **No discovery** — filename-derived
preset lookup (`FindAssets t:Type` etc.) was considered and rejected; the in-class map is
the one map.

**Presets and per-field overrides, at every door** (GitHub dispatch, configure window,
CLI):

- Preset = whole-asset copy of the map's asset into `TargetPath`; the mode travels with
  the copy (`ApplyConfigType`'s mechanism, generalized).
- Overrides = `SerializedObject` path-writes onto the live asset, on top of the copy.
  Unknown path or bad enum value fails loudly at apply (reflection-validated; the JSON
  `fields` schema is dead).
- The package's contract ends at "the live asset holds preset ⊕ overrides" plus the
  verification read-back of those values. Runtime resolution (`ResolveEffective`,
  Supabase remote fetch, F33's live/effective split) is consumer semantics — unmodeled,
  untouched, and load-bearing: field overrides take effect at runtime precisely because
  AppSetup reads live `localConfig`. Do not unify the split.
- Unset environment = ambient no-op: no copy; the live asset stays as-is, whatever its
  mode.

**`ConfigMode` + `ResolveEffective` survive** (owner reversal of this plan's earlier
scheduled deletion). Presets stay available at runtime; the runtime indirection is not
ours to model or remove. Whether a mode makes field overrides meaningful (e.g. Supabase
fetches config remotely) is likewise consumer semantics — no package-side override-policy
bits.

**Override is first-class in the package — as the map's complement.** Enum values in the
map: presets (copy semantics). Values outside the map: self-authoritative (no copy,
hand-edited). The package never names "Override". Derived window rules:

- mode selector = the asset field typed as the map's key enum (the same rule that dedups
  the dispatch panel's field inputs);
- preset mode → fields render read-only, banner: edits here are overwritten by the next
  preset application — switch to Override to hand-edit;
- Override mode → fields editable, banner: hand-edited, nothing overwrites these;
- preset selection = set mode + copy (the one destructive write); Override selection =
  set mode only.

Window claims are about **write lifecycle only** (what survives the next preset
application), never about what the runtime reads — the boundary that keeps the package
truthful where `UnityEnvInspector`'s preview was half-untrue (F34). In preset mode the
live asset IS the preset by construction (plus any door-applied override deltas, shown
read-only) — mode-following without loading the canonical.

**`UnityEnvInspector` is deleted at the MIS flip**, subsumed by the configure window.
Fate of its bespoke parts: mode-following preview → reconstructed (above); mode-gated
editability → the complement rule; help text + field curation → die. (Fallback on
record: stub opening the window, if the click-the-asset workflow must be preserved.)

**Dump verb** — package-generic executeMethod driven by the class pointer:
`MonoScript.GetClass()` → reflect shape, enum, `Presets`, `TargetPath` → JSON on stdout.
Consumer: the dispatch generator (Phase 5). Drift-gated (F20 pattern): a class edit
without dump regen is a loud CI failure — the accepted regen tax.

**Dispatch panel rules** (generated static YAML; F20/F32 caps):

- one `choice` input for preset, options = map keys; unset = ambient no-op;
- one input per simple-typed field: bool → boolean checkbox, enum → choice dropdown,
  string/number → text; arrays/structs self-exclude (no input type exists);
- flags enums → text input taking comma-separated names (`Enum.Parse`'s native format;
  numeric values also parse);
- mechanical dedup: the field typed as the map's key enum is not emitted as a field
  input (it IS the preset choice);
- no curation, no secret-name exclusion (owner YAGNI ruling; F36 census — zero true
  secrets; a future real secret belongs in GitHub environment secrets or equivalent,
  outside this model entirely);
- input values are plaintext in run UI/logs/payload (F32) — accepted: they are
  configuration, not credentials. MIS budget: 19 fields + 3 controls = 22 of 25.

**CLI (Phase 5)**: `--environment-preset <name>` + repeatable `--environment-field
path=value` (amended 2026-09-27 from `--environment` — precision: the value is a preset key, and a
bare "environment" collides with GitHub's `environment` input type in the dispatch panel); the
door→entry transport carries the override set as a JSON payload
(`ENVIRONMENT_FIELDS` = `{"path": "value", ...}` — comma-safe for flags values); the
preset rides `ENVIRONMENT`. Uniform enum application rule, flags included: names parsed
via `Enum.Parse` against the reflected member type → `SerializedProperty.intValue`;
bool/string per property type.

**One substrate forever**: `.asset` + `SerializedObject`. CT converts to the MIS shape at
its flip (Phase 6); the package never grows a JSON env writer.

### build-config.json (target schema)

```json
{
  "environment_config": "Assets/App/UnityEnv.cs",
  "platforms": {
    "AndroidMobile": {
      "render_pipeline": "Assets/Settings/AndroidMobile_PipelineAsset.asset",
      "additional_defines": []
    },
    "MagicLeap2": {
      "render_pipeline": "Assets/Settings/MagicLeap2_PipelineAsset.asset"
    }
  }
}
```

The env content is exactly one string — the env class file path; everything else derives
by reflection (§Environment model). Validation stays the closed set (see AGENTS.md).
`platforms` keyed by base name, exactly two entries per consumer, no dev duplication (the
entry applies the column from `DEVELOPMENT`).

### Package shape

`Assets/Package/Editor/`: `PlayerBuild.cs` (the `PlatformSpec` + `Platform` table vocabulary at
the top, the `PlatformRecord` DTO, the `BuildVerification` preprocessor class; then `Entry`
boundary catch; parameterless `RunBuild`; the `Apply` orchestrator and the application functions
every door calls — platform facts, environment (env-member resolution, preset copy, field
writes), XR, pipeline, defines; the dump entry; the record read/write; the OpenXR-retry build;
the verification function), `ConfigureWindow.cs` (dropdown/dev-checkbox/Apply + mode-aware
environment pane: preset dropdown = mode + copy, read-only gating per the map complement,
banners), `BuildConfig.cs` (DTOs + parse validation), `SerializableBuildReport.cs`, the asmdef
(references `UnityEditor.BuildProfileModule` for
the verification reads), `.meta` files for all. One file per document kind (the table is
vocabulary, not a document — it lives in `PlayerBuild.cs`). Conventions:
namespace `Outernet` flat; always brace single-statement bodies; callers before callees;
classes at top; no comments except greppable markers; no applier classes (F6); no unit
tests ever (F6/F8) — verification is the compile gate, the preprocessor, and consumer CI.

**No unit tests, no generated package artifacts, no Profiles directory.** (Generated,
drift-gated things — dispatch workflows, consumer dump regen — live outside the package,
in consumer repos and devkit CI; F20 pattern.)

### Unity 6 pin and upgrade outlook

All repos stay on `6000.0.66f1`. The 6000.2 upgrade remains its own queued initiative; it
no longer retires anything in this package (the `// upgrade-6000.2:` markers died with the
authoring pipeline and the per-profile pipeline applier — pipeline assignment is global
forever in this architecture). Reference (research-corrected, F29): `GetComponent` +
per-profile Graphics/Quality overrides land 6000.2; `AddComponent`/`CreateComponent`
6000.3; `CreateBuildProfile`/`GetAllBuildProfiles`/`GetBuildProfileAtPath`/
`activeProfileChanged` 6000.5; an on-disk profile format migration arrives ~6000.4/5 —
none of it changes anything we depend on while profiles stay irrelevant.

## Verified facts (do not re-earn)

- **F2 npm mechanics** (carried): release-devkit trusted publishing; one publisher per
  package bound to a single workflow **filename** (`release.yml`, never rename); dev
  channel `workflow_run`; needs `NPM_CONFIG_LOGLEVEL: verbose`.
- **F4 MIS git-pin migration** (carried, rides the MIS flip): five org packages at
  `c3313124` → npm pins; `com.magicleap.unitysdk 2.5.0` registry pin stays.
- **F5 shared outer machinery** (carried): devkit workflow pinned by SHA, root catalogs,
  env var transport.
- **F6/F8 postmortems** (carried, binding): no applier/phase classes, no unit tests ever,
  harness is not a consumer, minimal manifest, no XR bootstrap-and-create. Amended
  (session 3): the harness may carry a reflection fixture — a labeled dummy env class
  the reflection code is pointed at; the sterility that matters is the package depending
  on no harness state, and a reflection target is test tooling, not consumer config.
- **F7 editor facts** (carried): `XRGeneralSettingsForBuildTarget` null without the
  committed asset (fail loudly); OpenXR runtime assembly hosts the feature APIs;
  batchmode open+quit exits 0 despite compile errors (gate scans for `error CS`).
- **F9 Unity 6000.0.66f1 Build Profile API surface — CORRECTED 2026-09-27**: exists —
  `scriptingDefines`, `scenes`, `overrideGlobalScenes`, `Get/SetActiveBuildProfile`,
  `GetScenesForBuild`, `BuildPlayerWithProfileOptions`, the PlayerSettings override sheet
  + linking behavior. The 09-26 claim that `CreateBuildProfile`/`GetComponent`/etc. all
  arrive in 6000.2 was wrong (DLL string scan ≠ public API): the staggered schedule is
  6000.2 (`GetComponent`/`GetActiveComponent`, Graphics/Quality overrides), 6000.3
  (`AddComponent`/`CreateComponent`), 6000.5 (`CreateBuildProfile`,
  `GetAllBuildProfiles`, `GetBuildProfileAtPath`, `activeProfileChanged`).
- **F10 XR is not per-profile** (carried; still relevant to ApplyXr): XR Plug-in
  Management and OpenXR features are shared per build-target-group.
- **F12 release-devkit multi-target works** (carried): fold unblocked.
- **F13 storage map** (carried): scene list → committed `EditorBuildSettings.asset`;
  active-profile pointer → untracked `Library/EditorUserBuildSettings.asset` (the basis
  for "CI cannot have an installed snapshot").
- **F14 invoker landscape** (carried): devkit batchmode is the only build invoker;
  `--build-env` has three callers, all migrating at the flips; CT has no env transport
  today.
- **F15 Elliot's workflow — CORRECTED 2026-09-27**: never leaves the editor; configure
  menus are destructive global mutations; in-editor builds go through the native window;
  environment workflow is live-asset override. **The bundle baking is NOT self-contained:
  `CreateAssetBundles.cs` (lines 35/46) and `AssetBundleManagerWindow.cs` (137/143) call
  `Build.ConfigureForMagicLeap`/`ConfigureForAndroidMobile` before baking Android-family
  bundles — the flip must rewire all four call sites to the package's application +
  verification.** MIS CLAUDE.md documents the leaving-the-editor-in-that-config hazard.
- **F16 define audit** (carried): renames at the MIS flip (`OUTERNET_*` carried by the
  table now, not profiles); `MAGIC_LEAP` placeframe gate rename ahead of the flip;
  `USE_ML_OPENXR`/`MAGICLEAP` dead — drop.
- **F17 artifact-path contracts** (carried): output `Build/<SanitizedProductName>.apk`
  flat; `BuildReport.json` beside it; `unity-build.yml` globs both.
- **F18 CT XR sweep is a non-issue** (carried).
- **F19 MIS's committed profile** (`Assets/Settings/Build Profiles/Magic Leap 2.asset`):
  stale snapshot (dead defines, frozen `bundleVersion: 0.2.0`) — **deleted at the MIS
  flip**; under rewrite 3 it is the canonical example of why nothing ships snapshots.
- **F20 GitHub dispatch form** (carried): `workflow_dispatch` inputs, 25-input cap, static
  YAML, generated + drift-gated per file.
- **F21 MIS UnityEnv + CT JSON door** (carried): canonical assets serialize a stale class
  shape — re-saved once at the flip; CT loads `Resources` `default-settings`.
- **F22–F28** (demoted to Unity-machinery knowledge, 2026-09-27 — accurate as Unity
  facts, no longer load-bearing for this package): package-profile loading/window
  listing/building (F22); profile API addressing (F23); authoring write-routing binds at
  editor load (F24); sheet snapshot semantics + self-heal (F25); immutability is
  UI-level (F26); batchmode build vehicles + first-build OpenXR failure with one retry
  (**F27 stays load-bearing** — the entry's retry guard); regen determinism (F28).
- **F29 Unity research** (2026-09-27, sourced — docs, UnityCsReference, staff threads,
  issue tracker): the snapshot self-heal is deliberate source
  (`BuildProfilePlayerSettings.SerializePlayerSettings` →
  `PlayerSettings.EnsureUnityConnectSettingsEqual`) and the snapshot is a
  designed-complete set (staff-confirmed; partial overrides "coming" since 2024);
  `AssetModificationProcessor` has no content-mutating hook on any version (no
  `OnWillWriteAssets`); UUM-90426 (profile cloud-id) fixed 6000.0.36f1 — we have it; the
  community's converged workaround for profile YAML is text-editing the asset — the same
  class of hack the spine's strip used; the API schedule correction in F9; an on-disk
  profile format migration arrives ~6000.4/5.
- **F30 effective-value verification** (2026-09-27, sourced + derived): facade reads in
  `OnPreprocessBuild` return the values that bind in the imminent build (the build reads
  the same facade; XR/pipeline/subtarget are global anyway); the only build inputs
  outside the facade — profile `scriptingDefines` (additive) and scene override — have
  public typed readers; `BuildPipeline.BuildAssetBundles` runs no build preprocessors,
  so bake guards must live in the bake entry points; a fresh CI checkout cannot have an
  installed snapshot (F13 + snapshot-less default + entry never activates).
- **F31 bundle-bake call sites** (2026-09-27, repo-verified): see F15's correction —
  `Build.ConfigureForX` call sites in `CreateAssetBundles.cs` and
  `AssetBundleManagerWindow.cs` are flip work items.
- **F32 GitHub dispatch input facts** (2026-09-27, sourced): input types are exactly
  string/boolean/choice/number/environment — no secret/password type (open request since
  2022: community discussions #12764/#5621/#26748); input values render plaintext in the
  run UI, the event payload, and the "Set up job" log section before any step runs;
  `::add-mask::` cannot mask retroactively (actions/runner#643, open since 2020); the one
  sanctioned secret-adjacent mechanism is the `environment` input type (a selector — the
  secret stays in the environment); 25-input cap (raised from 10 in 2025-12); 65,535-char
  payload cap.
- **F33 MIS runtime authority split** (2026-09-27, repo-verified): `AppSetup.Setup` reads
  credentials from `ResolveEffective(live)` (canonical preset in preset modes) but reads
  `configMode` and `localConfig` from the **live** asset (`Assets/App/AppSetup.cs:100-103`).
  Load-bearing for this design: overrides write the live asset and take effect precisely
  because runtime reads live `localConfig` — do not unify the split. CI never sees the
  divergence (preset copy precedes the build).
- **F34 `UnityEnvInspector` autopsy** (2026-09-27, repo-verified): the canonical-asset
  guard checks nonexistent `Assets/App/BuildConfigs/` (actual:
  `Assets/App/Resources/BuildConfigs/`) so its `DrawDefaultInspector` branch never fires;
  the Airgapped/Supabase read-only preview renders the canonical's `localConfig` as if it
  runs, but runtime reads live (F33) — half-untrue by design drift. Bespoke inventory:
  mode-following preview, mode-gated editability, help text, field curation. Deleted at
  the flip; the window reconstructs the first two truthfully (write-lifecycle framing).
- **F35 CT storage map** (2026-09-27, repo-verified): preset source
  `apps/CaptureTool/Assets/BuildConfigs/airgapped-settings.json`
  (apiUrl/username/password — placeholder creds); build copies it to gitignored
  `Assets/_LocalWorkspace/Resources/default-settings.json`; runtime `SettingsManager`
  is three-tier — `persistentDataPath/settings.json` (auto-written on every settings
  change; permanently shadows the baked default) → baked `Resources` `default-settings`
  TextAsset (SimpleJSON via FofX.Stateful `StateObject.FromJSON`) → hardcoded fallbacks;
  `SettingsState` is `StateValue<T>` properties, not serialized fields; `CONFIG_TYPE`
  (`default`/`air-gapped`) arrives via ci.yml's `build-env`. Phase 6 replaces this whole
  substrate with the MIS shape.
- **F36 UnityEnv secrets census** (2026-09-27, repo-verified): zero true secrets —
  `supabaseApiKey` is a `sb_publishable_` key (public-by-design, RLS-gated),
  `supabaseProjectId` is an identifier, `username`/`password` are the literals
  `user`/`password` (Airgapped preset + live copy; CT identical). Basis for the YAGNI
  ruling on panel secret-exclusion.

## Superseded decisions (do not relitigate)

Environment amendments (2026-09-27, session 2):
- The JSON environment schema — the `environment_config` umbrella
  (`target`/`default_preset`/`presets` name→path/`fields` with paths, types, enum value
  lists) — replaced by the class-sourced model; `default_preset` dies (ambient no-op
  covers unset).
- Discovery-based preset resolution (`FindAssets t:Type` + filename-derived names) —
  rejected; the in-class enum-keyed map is the one map.
- Marker attributes on the env class — rejected; dependency direction (the package
  observes the consumer, never the reverse).
- Panel curation and secret-name exclusion lists — rejected (YAGNI; F36).
- Per-preset override-policy bits (`apply`/`refuse`) — rejected; whether a mode makes
  overrides meaningful is consumer runtime semantics, not package policy.
- The CT JSON substrate (package-side JSON env writer, preset-file-keys-as-shape) —
  replaced by converting CT to the MIS shape; the package keeps one substrate.
- Rewrite 3's scheduled deletions of `ConfigMode` + `ResolveEffective`, and the
  `UnityEnvInspector → stub` item — reversed (survive) and upgraded to
  delete-and-subsume respectively.

Catalog schema amendment (2026-09-27, session 10): the per-build `execute_methods` map dies with
the flips — Entry's env-var transport owns platform discrimination, so every consumer's map
degenerates to `{build: "Outernet.PlayerBuild.Entry"}` (keys duplicating `builds`, zero
information); the constant inlines at `resolve_unity_build`'s single lookup and the field leaves
the schema. The field is Optional, so keyless catalogs load against old and new devkit alike — the
ordering constraint runs the other way: a keyless catalog under a devkit that still has the field
fails the missing-method guard at build time, so the deletion must be released before consumers
drop the key. Accepted loss: the field was the last escape hatch for a bespoke consumer entry —
ruled YAGNI (re-adding what the package exists to own).

Same amendment, install pair: `package` (pre-install `adb uninstall`) and `grant_permissions`
(post-install `pm grant`) leave the schema with their install-door logic and the
`--no-grant-permissions` flag — device-state setup ruled not the installer's job. Accepted losses
on record: reinstalls over an existing package now fail loudly until the human uninstalls (bare
`adb install`, no `-r` — the data-wipe-on-reinstall semantics were never a requirement, just a
side effect of the uninstall step); CT's READ_LOGS grant becomes a manual smoke-checklist step
(signature-class permission; an app can never request it at runtime). CT drops both keys at its
Phase 6 remainder; MIS drops `package` at Phase 7.

Same amendment, versioning boundary (the owner's encapsulation ruling): **build tools take
versions as inputs and never derive them.** `versioning.py`'s ledger query was a verbatim clone of
release-devkit's `list_tag_versions` and the catalog's `tag_prefix` a duplicate of
release-devkit.json's app entry — three copies of one concept, the residue of a boundary never
resolved (the old "version-ledger primitives live in release-devkit and are not imported here"
line was the smell made policy). The corrected cut: WHAT version (derivation from the ledger)
belongs to release-devkit alone, exposed for build-time use by its new `app-build-version` verb;
HOW to stamp belongs to each build tool (the ProjectSettings writer is what remains of
`versioning.py`); TRANSPORT is an explicit parameter at the workflow boundary, composed by the
consumer — the same pattern as `PLATFORM`/`DEVELOPMENT`/`ENVIRONMENT_FIELDS`. The law the owner
stated: the string "release-devkit" appears nowhere in unity-devkit's code, workflows, or configs
— unity-devkit stamps whatever opaque string it is handed and does not care where it came from.
`--stamp-version` (self-deriving bool) died with it, replaced by `--version <string>` on both
build verbs; `AndroidBundleVersionCode` stays the run number (a CI fact, no ledger); the dev/release
`-dev+run` spelling convention moved to the verb (`GITHUB_REF_NAME == "main"` → release spelling,
preserving the old `branch == "main"` behavior). The hosted workflow's `version` input is optional
and SHA-pin compatible; the `bundleVersion` string is treated as opaque.

Everything profiles-spine is superseded by this rewrite: Build Profile assets shipped in
the package; the authoring pipeline (table → profile regeneration, bootstrap-by-copy,
two-pass load-bound sessions, self-heal strip, drift gate, pair validation);
`BuildPlayerWithProfileOptions`; per-profile Graphics/Quality retirement markers; the
"one implementation, two doors" phrasing that meant profile resolution. Earlier
supersessions from rewrite 2's list stand where still meaningful (env-var dev bit,
`scenes` in build-config, custom build menus — the native window remains the build door,
fed by applied globals + the preprocessor guard).

## Execution phases

**Phase 1 — implement rewrite 3** (complete; old Phase I). Doc-first (this document +
AGENTS.md, done). Then the
remaining steps in Status, in order. Acceptance: `check-unity` green, CSharpier clean,
`publish-stable --dry-run` intact, preprocessor provably firing (a hand-vandalized global
fails a local build loudly).

**Phase 2 — fold into unity-devkit** (complete; old Phase F; operator-gated, mechanical):
move `Assets/Package/` + harness + CI into `/workspace/unity-devkit`; one
`release-devkit.json` (PyPI `unity-devkit` + npm `org.outernet.playerbuild`); trusted
publisher bound to devkit's `release.yml`; this repo retires. Sequenced before the
`0.1.12` release (OQ5).

**Phase 3 — env core, package C#** (split from the old Phase V; no window, no Python, no
release — each is another phase). In `PlayerBuild/Assets/Package/`: the dump
executeMethod (class-pointer driven, JSON on stdout); env-member resolution
(`Presets`/`TargetPath`; name + shape matched; loud on absent/mismatched/ambiguous);
preset copy (whole-asset copy of the map's asset into `TargetPath`, mode travelling with
the copy) + per-field apply (`SerializedObject` path-writes; `Enum.Parse` against the
reflected member type, flags via comma-separated names; bool/string per property type;
unknown path or bad enum value fails loudly); verification read-back of env values (the
shared check grows the env rows); entry-side env-var transport — the C# side defines and
reads the `ENVIRONMENT`/`ENVIRONMENT_FIELDS` contract (`{"path": "value", ...}`); unset
environment = ambient no-op. The harness grows the reflection fixture (session-3 ruling):
a labeled dummy env class + one committed preset asset on a test-obvious path,
reflection-driven only — the package never references it by name; the harness still
carries no `build-config.json`. `check-unity --execute-method` runs dump → apply →
read-back against it in CI; its dump JSON becomes Phase 5's generator test fixture.
Gates: `check-unity`, CSharpier. An operator push after this phase may cut an npm-only
intermediate release — accepted (session-3 ruling); it de-risks the npm CI channel.

**Phase 4 — configure window, environment pane** (split from the old Phase V).
`ConfigureWindow.cs` grows the mode-aware pane per §Environment model's derived window
rules: mode selector typed as the map's key enum; preset selection = set mode + copy (the
one destructive write); Override selection = set mode only; preset mode → fields
read-only with the next-preset-overwrites banner; Override mode → fields editable with
the hand-edited banner — write-lifecycle claims only (F34 truthfulness). Calls the same
application functions every door calls; no new facts, no Python. Gates: `check-unity`,
CSharpier, hand-smoke against the harness fixture.

**Phase 5 — devkit release** (the old Phase V's Python half; version = next patch after
0.1.15 plus any intermediates the push cadence cut). Python (PyPI `unity-devkit`): typed
`--environment-preset`/`--development`/`--environment-field` flags with the JSON
`ENVIRONMENT_FIELDS` transport and child-env control (implementing the contract Phase 3
defined); the dispatch generator verb consuming the dump output (panel rules in
§Environment model; tested against the Phase 3 fixture's dump JSON); `--build-env`
deletion end-to-end (`build_unity.py` + hosted `unity-build.yml`'s `build-env` input →
preset/field inputs). Preflight battery, `check-unity`, CSharpier gate it. One devkit
release carries both registries.

**Phase 6 — capture-tool flip** (old Phase CT; amended: opens with the MIS-shape
conversion): write
`CaptureEnv : ScriptableObject` (fields `apiUrl`/`username`/`password`; preset enum;
`Presets` map; `TargetPath` = `Assets/_LocalWorkspace/Resources/CaptureEnv.asset`);
committed preset asset carrying today's `airgapped-settings.json` values; rewire
`SettingsManager`'s baked branch from `TextAsset`+SimpleJSON to
`Resources.Load<CaptureEnv>` seeding `SettingsState` (the `persistentDataPath`
write-back chain stays untouched); delete `airgapped-settings.json`. Devkit-side prerequisite
(2026-09-27 amendment, session 10 — **executed same session, pre-push, riding the pending release**):
**the catalog schema shrank to `path` + `builds` — `execute_methods`, `package`, `grant_permissions`,
and `tag_prefix` are dead.** `Outernet.PlayerBuild.Entry` is the one canonical entrypoint
(parameterless; platform rides `PLATFORM`), so the per-build map was degenerate; the constant lives
as `PLAYERBUILD_ENTRY` in `unity.py`, `resolve_unity_build` returns a 2-tuple, the missing-method
guard is gone. `package`/`grant_permissions` were install-door conveniences (pre-install
`adb uninstall`, post-install `pm grant`) ruled cruft-or-wrong-place by the owner: the surviving ADB
branch is bare `adb install` (a reinstall over an existing package fails loudly — the human
uninstalls; accepted) and permission grants move out of the tool entirely (CT's READ_LOGS is a
smoke-checklist step; a signature-class permission was never the installer's job to make permanent).
`tag_prefix` died with the versioning-boundary ruling below. Sequencing, all four fields: they were
Optional, so keyless catalogs load against old and new devkit alike — the ordering constraint is
that the deletion must be on PyPI before consumer catalogs drop keys they no longer need; executed
pre-push, it rides the same release CT's remainder gates on. Then: npm-pin the
package; `build-config.json` with the class-path `environment_config` +
`platforms["AndroidMobile"]`; migrate CI `--build-env CONFIG_TYPE=default` →
`--environment-preset`; catalog entry drops all four dead keys
(keyless per the deletion above); ci.yml grows a `resolve-version` job (release-devkit's
`app-build-version`, fetch-depth 0 for the tag ledger) feeding the hosted workflow's `version`
input; generate the dispatch-wrapper
workflow; delete `Assets/Editor/BuildScript.cs`; `compile-unity` local build; APK smoke
(`aapt` versionName/Code vs the stamp); the open Phase 1 acceptance probe
(hand-vandalize an applied global, build, expect the loud "run Apply" preprocessor
failure; the harness cannot host it — no `build-config.json` by design); hand branch +
SHA to operator.

**Phase 7 — Make-it-Sing flip** (old Phase MIS; amended): **executes on `Make-it-Sing-fork`**
(session-13 ruling) — the flip lands and is smoke-tested E2E on the fork's default branch,
then returns to MIS per the punt's one-PR consolidation; all items below are unchanged.
**Fork-window revert ledger** — deltas that exist only for the fork's direct-to-main
operating mode and must be stripped before the consolidation PR (anything else landing on
the fork during the window is permanent and rides the PR unchanged): ci.yml's `main` push
trigger (added session 14 so main-push work CI's on the fork; prime's dev→release-PR→main
flow would double-build every merge and race release.yml's artifact fetch under it), and
`workloads/images.yml`'s hardcoded image namespace (`make-it-sing-fork` — the fork's
GITHUB_TOKEN cannot push the prime's ghcr packages; mixed-case `GITHUB_REPOSITORY` blocks
env interpolation because ghcr rejects uppercase refs, so the durable fix — docker-devkit
exporting a lowercased repo var — is an upstream item; until then the namespace reverts
to `make-it-sing` at consolidation). When
the release-trigger rework lands, it joins this ledger if and only if its shape is
fork-only — a ci.yml-completion `workflow_run` trigger filtered to the main ref is
portable both ways and stays.
`UnityEnv` gains two members —
`public static readonly Dictionary<ConfigMode, string> Presets` (keys = door spellings;
`airgapped`, not `air-gapped`) and `public const string TargetPath =
"Assets/_LocalWorkspace/Resources/UnityEnv.asset"`; re-save both canonical presets (F21
stale `room:` shape). **`ConfigMode` + `ResolveEffective` survive — no deletion** (owner
reversal). **Delete `UnityEnvInspector.cs`** (subsumed — F34; stub fallback on record).
Both platforms with pipeline assets; `--build-env` migration; catalog goes keyless directly
(all four dead keys dropped outright — MIS never carries the collapsed map); dispatch workflow; define renames in app code (`OUTERNET_*`); delete
`Assets/Settings/Build Profiles/Magic Leap 2.asset` (F19); delete the
`Build > Configure` menu items and `BuildScript.cs`'s configure functions; **rewire
`CreateAssetBundles.cs` + `AssetBundleManagerWindow.cs` to the package's apply + verify
(F15/F31)**; placeframe magicleap gate rename + republish ahead of the flip; F4 git-pin →
npm migration; convergence method; Elliot smoke: Apply → native Build on both platforms,
bake bundles on both platforms (through the rewired entry points), workspace round-trip.

**Phase 8 — cleanup** (old Phase C): fold load-bearing plan content into AGENTS.md;
delete this plan
(also in the folded home); delete placeframe's dead `BuildUtility`.

**Excluded**: the 6000.2 editor upgrade (own initiative; changes nothing here — see
§Unity 6 pin).

## Convergence verification (superseded 2026-09-27, session 15)

The profiles-era mandate — a one-shot old-vs-new state-diff before deleting each old
BuildScript — is dead. It answered silent state divergence in an architecture where
nothing verified at build time; rewrite 3 verifies continuously and structurally: the
preprocessor fails every player build on any fact diverging from the table, `Verify`
guards every bake entry point, and CI reds name their facts. Precedent: CT's flip skipped
the diff and went green through the ordinary build loop. A qualitative old-vs-new check
rides the Elliot smoke.

## Executor constraints (unchanged)

No pushes from the sandbox — commit locally, hand branch + SHA to the operator. Prose and
code in separate commits; subject under 72 chars; no trailers; no bypass flags. CSharpier
120 cols; always-brace bodies; comments rare, self-contained. Never invoke
`/opt/unity/.../Unity` directly — always the devkit verbs (ADB guard); until the Phase 5
release lands, the devkit-checkout venv vehicle (`/workspace/unity-devkit/.venv/bin/<verb>`, cwd
at the target repo root). Never `gh run watch`. Keep `.gitignore` strict (`Library/`,
`_LocalWorkspace/`).
