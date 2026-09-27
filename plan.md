# plan.md — org.outernet.playerbuild: apply-to-globals (rewrite 3)

This plan moved to unity-devkit at the unitybuild repo's retirement (2026-09-27); the
package and harness it describes live here under `PlayerBuild/`. The unitybuild repo was
this initiative's development home — the phases below are its execution record, updated
in place as work lands.

This is an execution plan, not a status doc. A session with no prior context should be able
to execute it top to bottom. It was rewritten wholesale on 2026-09-27 after the owner
reversed the profiles-spine architecture (rewrite 2) in favor of **apply-facts-to-globals**.
The previous plan is in git history; nothing from it that contradicts this document survives.

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

Next session, in order:
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
materialization (`ApplyEnvironment` + `ApplyFieldValues`, unchanged model) — then write
the platform record. Three callers: the batchmode entry (facts from env vars), the
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

devkit stamps `bundleVersion`/`AndroidBundleVersionCode` into global
`ProjectSettings/ProjectSettings.asset` pre-batchmode; nothing exists in CI to shadow it.
On editor machines the ambient version is whatever globals say (as today). No package
involvement.

### Environment model — UNCHANGED from rewrite 2

`build-config.json` carries one optional `environment_config` umbrella; presets are
name → `Assets/` source path; unset `ENVIRONMENT` with no `default_preset` is a logged
no-op; overrides (`ENVIRONMENT_FIELDS`) are the only value-setting layer, applied through
`PlayerBuild.ApplyFieldValues`; the configure window's pane is a write-through view of the
workspace with snap-to-preset as the one destructive write; the package is
semantics-blind. Full schema and semantics: AGENTS.md (authoritative) and the schema
sketch below.

### build-config.json (target schema)

```json
{
  "environment_config": {
    "target": "UnityEnv.asset",
    "default_preset": "supabase",
    "presets": {
      "supabase": "Assets/App/Resources/BuildConfigs/UnityEnv.Supabase.asset",
      "airgapped": "Assets/App/Resources/BuildConfigs/UnityEnv.Airgapped.asset"
    },
    "fields": {
      "config_mode":   { "path": "configMode", "type": "enum",
                         "values": ["Supabase", "Airgapped", "Override"] },
      "log_level":     { "path": "localConfig.logLevel", "type": "enum",
                         "values": ["Default", "Info", "Warning", "Error"] },
      "statesync_url": { "path": "localConfig.stateSyncConnectionString", "type": "string" },
      "log_groups":    { "path": "localConfig.logGroups", "type": "integer" }
    }
  },
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

Validation stays the closed set (see AGENTS.md). `platforms` keyed by base name, exactly
two entries per consumer, no dev duplication (the entry applies the column from
`DEVELOPMENT`).

### Package shape

`Assets/Package/Editor/`: `PlayerBuild.cs` (the `PlatformSpec` + `Platform` table vocabulary at
the top, the `PlatformRecord` DTO, the `BuildVerification` preprocessor class; then `Entry`
boundary catch; parameterless `RunBuild`; the `Apply` orchestrator and the application functions
every door calls — platform facts, environment, XR, pipeline, defines; the record read/write;
the OpenXR-retry build; the verification function), `ConfigureWindow.cs`
(dropdown/dev-checkbox/Apply + environment pane), `BuildConfig.cs` (DTOs + parse validation),
`SerializableBuildReport.cs`, the asmdef (references `UnityEditor.BuildProfileModule` for
the verification reads), `.meta` files for all. One file per document kind (the table is
vocabulary, not a document — it lives in `PlayerBuild.cs`). Conventions:
namespace `Outernet` flat; always brace single-statement bodies; callers before callees;
classes at top; no comments except greppable markers; no applier classes (F6); no unit
tests ever (F6/F8) — verification is the compile gate, the preprocessor, and consumer CI.

**No unit tests, no drift gate, no generated artifacts, no Profiles directory.**

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
  harness is not a consumer, minimal manifest, no XR bootstrap-and-create.
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

## Superseded decisions (do not relitigate)

Everything profiles-spine is superseded by this rewrite: Build Profile assets shipped in
the package; the authoring pipeline (table → profile regeneration, bootstrap-by-copy,
two-pass load-bound sessions, self-heal strip, drift gate, pair validation);
`BuildPlayerWithProfileOptions`; per-profile Graphics/Quality retirement markers; the
"one implementation, two doors" phrasing that meant profile resolution. Earlier
supersessions from rewrite 2's list stand where still meaningful (env-var dev bit,
`scenes` in build-config, custom build menus — the native window remains the build door,
fed by applied globals + the preprocessor guard).

## Execution phases

**Phase I — implement rewrite 3.** Doc-first (this document + AGENTS.md, done). Then the
remaining steps in Status, in order. Acceptance: `check-unity` green, CSharpier clean,
`publish-stable --dry-run` intact, preprocessor provably firing (a hand-vandalized global
fails a local build loudly).

**Phase F — fold into unity-devkit** (operator-gated; mechanical, unchanged from
rewrite 2): move `Assets/Package/` + harness + CI into `/workspace/unity-devkit`; one
`release-devkit.json` (PyPI `unity-devkit` + npm `org.outernet.playerbuild`); trusted
publisher bound to devkit's `release.yml`; this repo retires. Sequenced before the
`0.1.12` release (OQ5).

**Phase V — devkit release `0.1.12`** (operator, unchanged): push devkit main (typed
`--environment`/`--development`/`--environment-field` flags, child-env control, dispatch
generator verb, `--build-env` deletion, hosted `unity-build.yml` input migration).

**Phase CT — capture-tool flip**: npm-pin the package; write `build-config.json`
(`environment_config`: `air-gapped` preset → `default-settings.json` source; no
`default_preset` — unset env is the ambient no-op; `platforms["AndroidMobile"]`);
migrate CI `--build-env CONFIG_TYPE=default` → `--environment`; catalog entry → the
single executeMethod; generate the dispatch-wrapper workflow; delete
`Assets/Editor/BuildScript.cs`; standardize Newtonsoft sourcing; convergence method;
`compile-unity` local build; APK smoke (`aapt` versionName/Code vs the stamp); hand
branch + SHA to operator.

**Phase MIS — Make-it-Sing flip**: `build-config.json` with both presets + full `UnityEnv`
field schema (transitional `config_mode` baking `Override`); both platforms with pipeline
assets; `--build-env` migration; catalog → executeMethod; dispatch workflow; define
renames in app code (`OUTERNET_*`); app refactor riding the flip (delete `ConfigMode` +
`ResolveEffective`; `UnityEnvInspector` → stub opening the configure window; re-save
canonical template assets); **delete `Assets/Settings/Build Profiles/Magic Leap 2.asset`
(F19); delete the `Build > Configure` menu items and `BuildScript.cs`'s configure
functions; rewire `CreateAssetBundles.cs` + `AssetBundleManagerWindow.cs` to the
package's apply + verify (F15/F31)**; placeframe magicleap gate rename + republish
ahead of the flip; F4 git-pin → npm migration; convergence method; Elliot smoke: Apply →
native Build on both platforms, bake bundles on both platforms (through the rewired
entry points), workspace round-trip.

**Phase C — cleanup**: fold load-bearing plan content into AGENTS.md; delete this plan
(also in the folded home); delete placeframe's dead `BuildUtility`.

**Excluded**: the 6000.2 editor upgrade (own initiative; changes nothing here — see
§Unity 6 pin).

## Convergence verification method (mandatory at each flip)

Before deleting each old BuildScript, in that consumer's checkout: run the old configure
path and the new package path in batchmode against the same project, each followed by a
state dump to JSON — defines (all layers), graphics APIs, architectures, texture
subtarget, encoding, XR loader assignment, OpenXR feature enable-set, render pipelines,
applied environment fields, the effective-value verification inputs. Diff; every delta
must be on the convergence list (table contents + F16 vocabulary); unlisted delta = bug.
Then one `compile-unity` build; compare applied-config log lines and `BuildReport.json`.

## Executor constraints (unchanged)

No pushes from the sandbox — commit locally, hand branch + SHA to the operator. Prose and
code in separate commits; subject under 72 chars; no trailers; no bypass flags. CSharpier
120 cols; always-brace bodies; comments rare, self-contained. Never invoke
`/opt/unity/.../Unity` directly — always the devkit verbs (ADB guard); until 0.1.12
lands, the devkit-checkout venv vehicle (`/workspace/unity-devkit/.venv/bin/<verb>`, cwd
at the target repo root). Never `gh run watch`. Keep `.gitignore` strict (`Library/`,
`_LocalWorkspace/`).
