# Private Area Test Actions — shared scene synchronization

## Cause and correction

Test Actions previously updated their local result ledger and a selected-incident callback. The room continued to read the Guided Demo playback and the independently selected sensor observation. A successful backend test therefore had no command path into the room animation.

The existing `TrackingPlayback` instance now owns the active test, source mode, backend result, incident ID and bounded pulse clock. Test Actions call `beginTest`, `updateTest` and `resetTest` on that same instance. The original renderer, Sensor Status, source badge and linked incident read this shared state. No second view, canvas, playback controller or button was added.

Guided Demo pauses and relinquishes ownership during tests. Its pending status reads cannot restart test playback, and guarded staff actions cannot execute after a test takes ownership. Historical test results cannot reactivate animations from polling or page reload alone.

## Actual browser results

| Test | Visible scene response | Backend/UI verification | Result |
| --- | --- | --- | --- |
| Acoustic | Amber pulse around the original acoustic fixture; no people, tracks or invented motion | Actual registered YAMNet scream inference; RECORDED_REPLAY label; OBSERVE in scene/status; matching canonical incident; notification unavailable because private single-signal notifications are suppressed | PASS |
| Fusion | Existing faceless humanoid fall animation, distance line, radar/acoustic pulses and HIGH room lighting | Synthetic fall + impact enter normalized ingestion at the shared impact cue; actual backend HIGH; one incident ID; API-accepted notification state from the isolated transport fixture | PASS |
| SOS | Red pulse around the original physical SOS marker; CRITICAL room/status; existing synthetic poses hold | Canonical CRITICAL TEST help-request incident; same ID in renderer and incident card; API-accepted notification state from the isolated transport fixture | PASS |
| Reset/retry | Clears test pulses, test status, synthetic occupancy and test lighting; Guided Demo remains stopped | SQLite event/incident counts remain unchanged; repeated Fusion/SOS and toolbar/card SOS create no duplicate incident or Telegram attempt | PASS |

The browser retained the exact same canvas element while Acoustic → Fusion → SOS ran in sequence. It sampled changing acoustic emission/pulse values, partial and completed fall poses, physical SOS emission, sensor highlights, risk color and source mode. Sensor Status and Event Timeline text were checked against the corresponding backend reports. Conflicting guided playback was started before Acoustic; no guided synthetic event leaked into the recorded test.

Screenshots captured during those tests:

- [Recorded acoustic pulse](runtime/private-test-actions/scene-acoustic.png)
- [Fusion during the fall](runtime/private-test-actions/scene-fusion-falling.png)
- [Fusion at backend HIGH](runtime/private-test-actions/scene-fusion-high.png)
- [SOS marker at CRITICAL](runtime/private-test-actions/scene-sos.png)

## Validation

- Shared-scene/action Chromium suite: **18 PASS, 0 FAIL** — `runtime/private-test-actions/browser-results.json`.
- Original Private Area Chromium regression: **29 PASS, 0 FAIL** — `runtime/part4-private/browser-results.json`.
- Controller and workflow contracts: **18 PASS, 0 FAIL** — `tests/privateTestPlayback.test.ts`, `tests/privateTestWorkflow.test.ts`.
- Existing backend scenario, privacy, lifecycle and deduplication suite: **16 PASS, 0 FAIL** — `tests/test_connected_private_demos.py`.
- TypeScript: **PASS**.
- Production Vite build: **PASS**.

Recorded YAMNet inference was genuinely executed. Browser integration used real FastAPI, the existing notification queue and an isolated SQLite database. Telegram HTTPS alone was mocked, including API acceptance, explicit rejection and ambiguous timeout; no external Telegram message was sent in this verification and no recipient receipt is claimed. Physical hardware and acquisition calibration remain unverified.

## Preserved behavior

The original Toilet room, camera, three-column layout, smooth schematic humanoids, X/Y/Height/Velocity inspection, trails and distance lines remain intact. Fusion motion is explicitly SIMULATED. Acoustic recordings supply classification only, with no fabricated positions. No camera, speech recording/transcription or identifiable reconstruction was introduced. Pulses use the existing demand-render loop at its 30 FPS ceiling and settle after a bounded interval. Backend routes, SQLite schemas, fusion rules and recipient routing were not changed.

## Changed files

- `dashboard/src/components/private-area/trackingPlayback.ts` — shared test ownership, result state, sensor flags, bounded pulses and fall-pose hold.
- `dashboard/src/components/private-area/privateTestWorkflow.ts` — trusted recorded observation forwarding, generic notification state and impact-cue submission gate.
- `dashboard/src/components/private-area/PrivateTestActions.tsx` — connect actions/reset/status polling to the shared controller; show each incident's notification state.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx` — derive scene inputs, source mode, risk, metrics and linked incident from the controller.
- `dashboard/src/components/private-area/GuidedPrivateDemo.tsx` — pause conflicting workflow and synchronize the disabled scenario selection during tests.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx` — pulse the existing fixture locations in the same renderer and consume shared test signals.
- `tests/privateTestPlayback.test.ts` — ownership, no fabricated recorded tracks, fall/SOS behavior, reset and historical-result isolation.
- `tests/test_private_test_actions_browser.py` — in-test screenshots and visible animation/sensor/risk/incident/notification assertions.
- `PRIVATE_TEST_SCENE_SYNC_REPORT.md` — this report.

The production bundle was regenerated under `dashboard/dist`.
