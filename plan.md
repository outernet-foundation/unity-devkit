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

## Status (2026-09-27, session 9 close — Phase 5 complete)

Phase 5 executed in full: the Python half plus the release preparation. Landed:

- **Transport + child-env control.** `run_unity_batchmode` grew an `env` parameter (a bashrun overlay — never
  `os.environ` mutation) and now returns the captured log path. `unity.py` gained
  `parse_environment_fields` (newline/repeatable `path=value` → dict, split on first `=`, loud on bare
  paths) and `child_environment` (builds the entry contract: `PLATFORM`, `DEVELOPMENT` always,
  `ENVIRONMENT`/`ENVIRONMENT_FIELDS` only when non-empty — unset stays ambient no-op). Build names map to
  playerbuild platform names via `playerbuild_platform` in `PLATFORM_CONFIGS` (`android-mobile` →
  `AndroidMobile`, `magicleap` → `MagicLeap2`; `linux64`/`win64` carry `""` — their execute methods are
  consumer-owned). `resolve_unity_build` returns the 4-tuple including the platform name.
- **Doors.** `compile-unity`: `--development` bool flag, `--environment <preset>`, repeatable
  `--environment-field path=value` (the plan's CLI spelling). `build-unity`: `--environment`,
  `--development` (validated `'true'`/`'false'` string — workflow booleans arrive as strings; the two
  doors' skins differ, the transport spelling is one), `--environment-fields` (newline `path=value` — the
  shape the generated dispatch workflow emits). `--build-env` and its KEY=VALUE loop are deleted.
- **`unity-build.yml`**: `build-env` input replaced by `environment`/`development`/`environment-fields`
  (repo-agnostic — per-field inputs live only in the consumer's generated wrapper). Known consequence on
  record: CT's unpushed ci.yml still passes `build-env:` and will error against the new input surface
  until its Phase 6 remainder migrates — expected; that work is gated on this release anyway.
- **`unity-dispatch`** (new verb, `dispatch.py`): runs the dump door
  (`Outernet.PlayerBuild.DumpEnvironment`, class pointer from `--environment-class` or the project's
  `build-config.json`), extracts the payload structurally (log line parsing as a JSON object with
  `class_name` — no magic-string coupling), validates into a forbid-extra pydantic model, renders static
  YAML: preset choice (leading empty option = unset = ambient no-op) + development boolean + one input
  per simple-typed field — bool → checkbox, non-flags enum → choice (empty option first), flags enum →
  comma-separated text, string/number → text; the mode field dedupes into the preset choice; field input
  ids are dot→dashed and referenced with bracket notation (`inputs['localConfig-apiUrl']` — dotted ids
  would parse as property access minus). Loud past the 25-input cap and on unknown field types.
  `--check` regenerates and diffs — the F20 drift gate for consumer CI. The transport forwards only
  non-empty inputs (per-field `inputs['id'] != '' && format('path={0}', …) || ''` lines); boolean fields
  transport only when checked (checkbox = opt-in override; forcing false goes through the CLI door).
- **Tests** (43, up from 27): generator render assertions (dedup, type mapping, bracket refs, transport
  lines, cap, unknown type, determinism, YAML validity via pyyaml — added to the root dev group,
  test-only), extraction, field parse, child-env contract, and the 4-tuple resolve. The fixture dump
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

The release (one devkit release carrying both registries) rides the operator push: 31 commits local on
main (29 prior, plus the owner's mid-session `b7b77fd`/`2559e0a` window-fix pair) → push → CI → `release.yml` publishes PyPI `unity-devkit` + npm `org.outernet.playerbuild` (path-
diff covers `packages/python/unity-devkit`; the hosted workflow edits ride the SHA pin, not a ledger).
CT's gated remainder then rides the release: CI `--environment` migration + ci.yml input fix, npm pin
swap for the local `file:` pin, dispatch workflow generation + drift gate, APK smoke, the Phase 1
acceptance probe. Phase 6's flip list otherwise unchanged.

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

devkit stamps `bundleVersion`/`AndroidBundleVersionCode` into global
`ProjectSettings/ProjectSettings.asset` pre-batchmode; nothing exists in CI to shadow it.
On editor machines the ambient version is whatever globals say (as today). No package
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

**CLI (Phase 5)**: `--environment <preset>` + repeatable `--environment-field
path=value`; the door→entry transport carries the override set as a JSON payload
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
`--environment`/`--development`/`--environment-field` flags with the JSON
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
write-back chain stays untouched); delete `airgapped-settings.json`. Then: npm-pin the
package; `build-config.json` with the class-path `environment_config` +
`platforms["AndroidMobile"]`; migrate CI `--build-env CONFIG_TYPE=default` →
`--environment`; catalog entry → the single executeMethod; generate the dispatch-wrapper
workflow; delete `Assets/Editor/BuildScript.cs`; `compile-unity` local build; APK smoke
(`aapt` versionName/Code vs the stamp); the open Phase 1 acceptance probe
(hand-vandalize an applied global, build, expect the loud "run Apply" preprocessor
failure; the harness cannot host it — no `build-config.json` by design); hand branch +
SHA to operator.

**Phase 7 — Make-it-Sing flip** (old Phase MIS; amended): `UnityEnv` gains two members —
`public static readonly Dictionary<ConfigMode, string> Presets` (keys = door spellings;
`airgapped`, not `air-gapped`) and `public const string TargetPath =
"Assets/_LocalWorkspace/Resources/UnityEnv.asset"`; re-save both canonical presets (F21
stale `room:` shape). **`ConfigMode` + `ResolveEffective` survive — no deletion** (owner
reversal). **Delete `UnityEnvInspector.cs`** (subsumed — F34; stub fallback on record).
Both platforms with pipeline assets; `--build-env` migration; catalog → executeMethod;
dispatch workflow; define renames in app code (`OUTERNET_*`); delete
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
`/opt/unity/.../Unity` directly — always the devkit verbs (ADB guard); until the Phase 5
release lands, the devkit-checkout venv vehicle (`/workspace/unity-devkit/.venv/bin/<verb>`, cwd
at the target repo root). Never `gh run watch`. Keep `.gitignore` strict (`Library/`,
`_LocalWorkspace/`).
