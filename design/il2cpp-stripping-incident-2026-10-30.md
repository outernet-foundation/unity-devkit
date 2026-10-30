# IL2CPP managed stripping vs runtime reflection — incident, analysis, and roadmap

Record of the 2026-10-30 Make It Sing / Magic Leap 2 "no logs in Loki" incident, the
investigation that followed, the ecosystem research, the blast-radius audit of the
affected app, the bridge deployed in response, and the roadmap to a correct end-state.
Pre-implementation design: expected to go stale as pieces land; when a tier ships, fold
its content into the co-located `AGENTS.md` and cut it here.

## 1. Incident

The Magic Leap 2 build of Make It Sing (`com.plerion.makeitsing`) never delivered any
logs to the backend Loki (`{app="make-it-sing"}` had zero streams, ever). The device's
logcat showed `LokiSink POST returned 422 Unprocessable Entity`, six attempts with
textbook exponential backoff, then apparent silence (later shown to be the 60 s backoff
cap, not a wedge).

## 2. Evidence

A tcpdump inside the Loki container's network namespace captured the app's actual push
during a controlled relaunch (16:50:51 UTC, 2026-10-30):

```
POST /loki/api/v1/push HTTP/1.1
Host: 5.78.28.175:58080
Content-Length: 2
Content-Type: application/json; charset=utf-8
X-Anonymous-Identity: a46ffda29e43518b15751265dee57bbf

{}
```

Loki 3.5.0 answers exactly `422 "error at least one valid stream is required for
ingestion"` when a push body decodes to zero streams. The producer
(`org.outernet.logging` 2.0.0-dev.1338, `LokiSink.cs`) built its payload with:

```csharp
JsonConvert.SerializeObject(
    new { streams = new[] { new { stream = _labels, values = ... } } })
```

Everything else on the path was healthy: hand-crafted pushes with the app's exact
labels returned 204 through the full public path (rathole → door → Loki); tunnel,
gateway wiring, label validity, and clock were all verified good.

### Settings archaeology (Make-it-Sing `ProjectSettings.asset`)

- `scriptingBackend: Android: 1` (IL2CPP) — ML2 builds ride the Android stanza.
- `managedStrippingLevel: Android: 1` = **Minimal** — the least stripping IL2CPP
  permits — since the initial commit (2026-05-15).
- A side branch (`origin/fix/working-midstep`, 2026-07-27) briefly set it to `4`
  (= High), never merged. The value `4` being serializable proves the five-value
  Unity 6 enum (Disabled=0, Minimal=1, ...), which pins `1` = Minimal.
- **Unity has no "Disabled" managed stripping on IL2CPP** — the editor's own UI
  hides it ("If scripting backend is IL2CPP, managed stripping can't be disabled")
  and the docs mark Disabled as Mono-only.

Conclusion: the `{}` envelope happened **at the IL2CPP stripping floor**. There is no
settings-based escape valve; lowering the level is not available.

## 3. Root cause class

IL2CPP's managed stripper removes type members that no code statically references.
Reflection-only reachability — serialization libraries, DI, property discovery — is
invisible to it. Anonymous types are the worst case: their members are *never*
statically referenced, so they are always stripped, and Newtonsoft's reflection finds
zero properties → `{}`. Named classes survive only while each member happens to have a
static reference somewhere in player code — an incidental, unenforced, invisible
guarantee that differs between editor and player builds.

## 4. Ruled out during the investigation

Server-side ingestion/config (204 probes with exact labels); tunnel/gateway wiring;
bad label names or timestamp classes (they produce 400, not 422); device clock skew;
the auth handler (header-only); empty-batch sends; a wedged drain loop (retries
continue at the 60 s cap); the raw-HTTP "200 empty" probe anomaly (toybox nc probe
artifact).

## 5. Ecosystem research (how mature shops handle this)

Every mature trajectory converges on moving serialization contracts from runtime
reflection to compile time:

- **.NET / System.Text.Json source generation**: compile-time contract generation;
  "eliminates runtime reflection"; trim-clean by construction; plus an annotation
  culture (`[RequiresUnreferencedCode]`, IL2026/IL3050) that surfaces unsafe
  reflection at build time, and `JsonSerializerIsReflectionEnabledByDefault=false`
  which makes the reflection path fail with a descriptive exception instead of
  misbehaving silently.
- **Microsoft Store team** (Newtonsoft under .NET Native trimming): targeted
  preservation of the data-contract assembly ("preserve the contracts, trim the
  rest") as a bridge, with a stated destination of source generation.
- **Unity-first library ecosystem**: MessagePack-CSharp v3 ships AOT source
  generation on by default with analyzers enforcing AOT-readiness (its pre-gen CLI
  was retired); MemoryPack and Nino are zero-reflection by design; VContainer
  migrated DI from runtime reflection to a Roslyn source generator, auto-preserving
  generated classes.
- **Unity's own remedies** are amnesty mechanisms: `[Preserve]`, `link.xml`,
  build-time link.xml generation (Addressables). Note: a UPM package cannot ship its
  own `link.xml`; preservation must live in package source (attributes) or in the
  consumer's project.

## 6. Blast-radius audit (Make It Sing, 2026-10-30)

Cross-device state flow: scene `StateObject` graphs (Stateful) → ops →
`PeerToPeerStateSyncManager` (lbe-toolkit) → join-sync payload is **full-graph JSON
via Stateful `ToJSON`** (reflection-discovered children); incremental/high-frequency
paths are hand-written binary over a statically-registered primitive-serializer
registry (loud `KeyNotFoundException` on unknown types) → Photon or LiveKit `byte[]`.

| # | Finding | Status |
|---|---|---|
| M1 | `Stateful` `StateObject.InitializeInternal` (`StateTypes/StateObject.cs:37-51`) reflects `GetProperties` + `Activator.CreateInstance` over app-defined state classes. A synced property with no static player-code reference is silently absent from the graph → absent from join-sync JSON → never crosses devices, no error anywhere. | Working on-device today only because every shipped member happens to be player-referenced (verified via captured logcat: graph reflected into existence, room seeded, config arrived, transport connected). Nothing enforces this. |
| M2 | Editor/player graph asymmetry: `EditorOnlyState` is `#if UNITY_EDITOR`; room-seeding path is editor-only. Editor testing systematically misses player-only stripping holes. | Structural. |
| M3 | `SupabaseAPI` Newtonsoft over app records (config path). Load-bearing records survive via incidental static references; `FileData` members unreferenced → silently empty today. | Working, fragile. |
| M4 | Dead `PhotonSerialization` twin in app code — registered into but never read by the sync manager; a future type registered there throws at sync time despite appearing "registered". | Latent trap. |
| M5 | No preservation for first-party assemblies (only `PlaceframeApiClient` + `StringEnumConverter` were preserved). | Fixed by the bridge (below). |

`ObserveThing` and `Nessle` audited clean: statically-bound C#, zero serialization,
zero reflection — the stripping class cannot originate there.

## 7. Decision: bridge, not fix

Constraints at decision time: no bandwidth for the correct fixes, no bandwidth to vet
partial code fixes, unacceptable to merge unvetted code. The available high-level
valve is **not** a settings change (no Disabled on IL2CPP; already at Minimal — see
§2). The valve that exists is amnesty:

**`Assets/link.xml` in Make-it-Sing now preserves every first-party assembly whole**
(`Assembly-CSharp`, `App`, experience asmdefs, `Outernet.Logging`, `Stateful`,
`ObserveThing`, `Nessle`, the four lbe-toolkit assemblies, `Placeframe.*`,
`PlaceframeApiClient`) plus the Photon transport assemblies (their runtime
`Type.GetType` probes). This mechanically guarantees no first-party member metadata
is stripped at any stripping level — the Microsoft Store bridge pattern. Costs binary
size (irrelevant on a 162 MB headset APK) and keeps the reflection debt alive.

A code fix for the Loki sink (explicit `JToken` construction of the push envelope —
provably reflection-free — plus failure-body logging in SelfLog) was written, built,
and installed as a local `file:` package pin, then **reverted** before merge: with the
bridge preserving the anonymous type, the code fix is unnecessary, and the no-unvetted-
code constraint stands. The approach remains validated and is recorded in §8.

### Verification protocol for the bridge

Rebuild the ML2 APK from the bridged tree, install, relaunch, and observe: (a) the
loki-netns sniffer shows a JSON push with a real `streams` body, (b) Loki answers 204,
(c) `{app="make-it-sing"}` becomes queryable. Any 422 with an empty body means the
bridge is not effective — treat as a blocker, not a logging problem. (Note: the sink
logs only status codes; the response body is not logged in 2.0.0-dev.1338.)

## 8. Correct end-state (four tiers, order matters)

1. **Compile-time-evident serialization on every wire path.** For small fixed schemas
   (the Loki push envelope): explicit construction (`JObject`/`JArray`/string-splice —
   note each log line is already a complete JSON document, so the envelope is
   splicing). For large evolving type universes: a source-generated serializer. Ban
   `JsonConvert.SerializeObject` over runtime shapes in Unity package runtime code —
   enforceable as a preflight grep (the API surface is small and named) with zero
   exemptions rather than escape hatches. Long-term endpoint: a Roslyn analyzer
   shipped inside the packages (MessagePack-v3 pattern).
2. **Packages self-contained under any consumer stripping profile.** No reliance on
   consumer link.xml (packages cannot ship one anyway). `Stateful`'s child discovery
   must stop reflecting: registration-by-construction, or a source generator emitting
   the child map for `partial` state classes. `[Preserve]` on state properties is
   only a bridge.
3. **Loud failure at the failure surface.** Log response bodies on failed pushes
   (would have collapsed this incident from hours to minutes); self-check invariants
   (a push body without `streams`, a reflected child count below the known count, is
   a bug — say so loudly).
4. **CI proves the property on an IL2CPP player.** A runtime smoke leg: headless
   linux-il2cpp player enables the sink against a localhost listener and asserts the
   received body shape; a Stateful graph initializes and asserts its reflected child
   count. This is the only tier that catches instances originating in third-party
   code or in consumer projects outside any lint's jurisdiction. unity-devkit's
   existing IL2CPP compile-check matrix is the natural home.

## 9. Residual risks while the bridge is in place

- **Third-party assemblies not on the preserve list** can still lose reflection
  targets (Magic Leap SDK, Unity packages, LiveKit). Symptom class: missing types or
  silent empty results. Extend the list or fix forward.
- **Non-stripping IL2CPP mines** that no link.xml can fix: `System.Reflection.Emit`
  (unsupported), runtime value-type generic instantiation (`MakeGenericType` /
  deserializing into generic interface collections → `ExecutionEngineException:
  ...no AOT code was generated`). Low probability in this codebase; the symptom is
  loud, unlike stripping.
- **Minimal still strips**: Unity documents Minimal as removing *some* unused code;
  the Loki incident proves anonymous-type members go even at Minimal. Anything not
  on the preserve list has no floor guarantee.
- **The reflection debt itself** (M1–M4) is intact and preserved, not fixed: adding
  a synced state member still relies on incidental references, the editor/player
  graph asymmetry remains, and the dead `PhotonSerialization` twin remains a trap.

Reopen triggers: any 4xx on Loki pushes from a device build; any state silently
failing to cross devices (single-device symptom: works in editor, absent on headset);
any `ExecutionEngineException` mentioning AOT code generation.
