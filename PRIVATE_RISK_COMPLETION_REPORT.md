# Private Area risk-state synchronization

## Actual root cause

Three independent rules disagreed:

1. `PrivateAreaMonitoringView.tsx` applied the selected run's backend risk only while `tracking.time < 33`. `sceneTracking.ts` also returned LOW after the fall/SOS time window ended.
2. `GuidedPrivateDemo.tsx` automatically posted RESOLVED at 32 seconds after acknowledgement. The page then explicitly chose LOW for that closed report, even though a fallen body was still shown. Playback progress was also coupled to incident closure.
3. `AnonymousTrackingLayer.ts` independently forced any nonzero fall pose to HIGH. Room/radar lighting followed the page's LOW while the affected avatar and ground highlight followed the pose's forced HIGH. Pose generation and synthetic departures had separate end-time cutoffs too.

This was a state-policy inconsistency, not a backend fusion failure. HIGH incident severity remains historical evidence even after its status changes.

## Explicit demo policy

- Playing, Paused and Completed describe only the playback clock.
- Scenario visual risk is held independently. Completion does not clear a HIGH/CRITICAL alert.
- NEW and ACKNOWLEDGED keep the alert active. Only explicit resolution/false-alarm closure of the corresponding scenario incident, or an explicit visual reset/restart/scenario change, clears the selected visual alert.
- Scripted acknowledgement remains explicitly labeled simulated. Time-based automatic resolution has been removed.
- The last schematic fall pose and positions remain at completion. After explicit resolution, alert colors clear together while the last illustrative pose remains; no recovery movement is invented.
- Restart creates a fresh visual epoch. Switching to Normal Presence cannot inherit another run's incident risk. Neither action updates or deletes historical SQLite incidents.
- Radar availability is independent: Active, Missing or Disconnected. Missing/disconnected readings display Unavailable/Disconnected and neutral gray, not a green Normal claim.

The existing `TrackingPlayback` instance owns the scenario visual state, fall progress, current run binding and linked incident status. Room lighting, radar accents and the affected avatar/ground/labels consume the same severity. Backend reports must match the selected scenario and bound run before changing it.

## Actual PASS/FAIL results

| Browser case | Result |
| --- | --- |
| Fall + Distress creates its matching HIGH incident and consistent red room/radar/avatar/ground colors | PASS |
| Pause preserves time, pose, coordinates and HIGH; resume continues the same playback | PASS |
| Natural playback reaches 40 seconds / Completed while risk stays HIGH and incident stays ACKNOWLEDGED | PASS |
| Seek to the last frame preserves HIGH and completed fall pose | PASS |
| Acknowledgement does not resolve or clear colors | PASS |
| Explicit linked resolution clears all alert colors and agrees with SQLite | PASS |
| Restart resets visual epoch/pose without changing historical incident records | PASS |
| Normal Presence ignores unrelated CRITICAL and historical HIGH incidents | PASS |
| Missing/disconnected radar is unavailable and neutral gray | PASS |
| One original canvas, zero browser errors | PASS |

The test seeded an unrelated CRITICAL incident before starting Fall + Distress. The selected demo stayed HIGH, then Normal Presence stayed LOW, while those unrelated/history records remained intact. No automatic `/review` request occurred through completion. Before and after completion, radar and affected avatar/ground colors were exactly `ef4444`, room ambient color was unchanged, and the same two held positions remained visible.

Screenshots captured in Chromium:

- [Before completion — paused, HIGH, NEW](runtime/private-risk-completion/before-completion.png)
- [After completion — Completed, HIGH, ACKNOWLEDGED](runtime/private-risk-completion/after-completion.png)
- [Explicitly resolved — consistent cleared colors](runtime/private-risk-completion/explicitly-resolved.png)
- [Restarted scenario](runtime/private-risk-completion/restarted.png)
- [Normal Presence with historical alerts retained](runtime/private-risk-completion/normal-presence.png)
- [Radar unavailable](runtime/private-risk-completion/radar-unavailable.png)

## Verification suites

- New completion-policy Chromium/FastAPI/SQLite suite: **10 PASS, 0 FAIL** — `runtime/private-risk-completion/results.json`.
- Existing Private Area browser regression: **29 PASS, 0 FAIL** — `runtime/part4-private/browser-results.json`.
- Acoustic/Fusion/SOS shared-scene browser suite: **18 PASS, 0 FAIL** — `runtime/private-test-actions/browser-results.json`.
- Controller/workflow contracts: **22 PASS, 0 FAIL** — `tests/privateScenarioRisk.test.ts`, `tests/privateTestPlayback.test.ts`, `tests/privateTestWorkflow.test.ts`.
- Backend incident/fusion/privacy/deduplication suite: **16 PASS, 0 FAIL** — `tests/test_connected_private_demos.py`.
- TypeScript and production Vite build: **PASS**.

The completion suite uses an isolated SQLite database with external notifications disabled. The shared-scene suite executes real registered YAMNet inference and mocks Telegram HTTPS while using the actual backend queue and SQLite. No external Telegram receipt or hardware verification is claimed. Existing resolved SQLite incidents are not reopened or rewritten; the existing “Prepare new guided exercise” action remains available for a fresh run.

## Changed files

- `dashboard/src/components/private-area/trackingPlayback.ts` — independent playback/visual/incident state, run binding, risk latch, retained pose/positions and reset epochs.
- `dashboard/src/components/private-area/sceneTracking.ts` — remove time-window fallback to LOW after meaningful fall/SOS cues.
- `dashboard/src/components/private-area/GuidedPrivateDemo.tsx` — remove automatic resolution; bind reports to the current run; report playback completion independently.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx` — controller-driven severity, separate radar availability and run-specific incident selection.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx` — shared pose/risk, neutral unavailable accents and separated diagnostic states.
- `dashboard/src/components/private-area/AnonymousTrackingLayer.ts` — affected avatar/ground severity follows shared risk rather than independently forcing HIGH from pose.
- `tests/privateScenarioRisk.test.ts` — state-policy contracts.
- `tests/test_private_risk_completion_browser.py` — actual completion/lifecycle browser checks and screenshots.
- `PRIVATE_RISK_COMPLETION_REPORT.md` — this report.

The original room, smooth humanoids, tracking details, trails, distance lines, camera controls, source-mode boundaries, Test Actions, Telegram behavior and three-column layout remain. Production backend routes and SQLite schemas were not changed. The production bundle was regenerated under `dashboard/dist`.
