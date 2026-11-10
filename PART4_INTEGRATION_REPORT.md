# Part 4 — Private Area Digital Twin integration

Validated on 3 November 2026 (Singapore). Dashboard: http://localhost:3000.

The original three-column layout, one Three.js Toilet scene, schematic smooth humanoids, camera controls and public-area models are retained. Six scenarios now submit their synthetic observations through `/sensors/observations`, which invokes the canonical `/event` implementation exactly once per stable signal ID. The frontend no longer submits a second copy through `/event`.

| Scenario | Actual backend result |
| --- | --- |
| Normal Presence | LOW; no incident |
| Close Proximity | LOW; no danger incident |
| Repetitive Motion | OBSERVE; review candidate |
| Possible Fall | Radar-only OBSERVE; review candidate |
| Fall + Distress | Radar fall + synthetic acoustic impact → HIGH; one incident |
| SOS | Immediate CRITICAL TEST help-request incident; model confidence irrelevant |

Fusion requires the same registered zone, processing mode, test/live classification, source provenance and analysis run, compatible radar/vision versus acoustic modalities, the existing arrival-time window and compatible supplied capture timestamps. Supplied capture timestamps outside the current ingestion window cannot escalate ordinary signals. Recorded inputs without synchronized capture evidence remain independent; no fabricated cross-recording fusion is claimed.

Room risk accents, avatar colors and sensor/lighting accents use the current run's backend assessment while its signal is active. Closure clears that run's risk. Restarting before its trigger or selecting a different scenario cannot import historical incident severity into the animation. Actual recorded observations also expose their linked backend assessment and reason; closing their incident clears their displayed risk.

Stable event IDs and run IDs survive retries and playback restarts. A late retry returns already persisted events but cannot add expired new signals. Map, Alerts, Review and SQLite use the canonical backend incident ID. The existing guided automatic responder remains explicitly labeled SIMULATED; the browser tests separately perform named staff acknowledgement, verification and resolution through the real APIs.

## Executed results

| Check | Result | Evidence |
| --- | --- | --- |
| Canonical private scenarios, acoustic-only/radar-only, fusion windows/provenance, cross-zone rejection, deduplication, closure, stale capture, privacy and queue failure | PASS — 16 tests | `tests/test_connected_private_demos.py` |
| Normalized observation schema, strict source modes, forged hardware rejection, recorded linkage and private metadata validation | PASS — 8 tests | `tests/test_sensor_observations.py` |
| Notification routing, test recipient isolation and duplicate suppression | PASS — 13 tests | `tests/test_notification_safety.py` |
| Pending, disabled, explicit failure, API acceptance, timeout uncertainty, durable claims and authorized receipt verification contracts | PASS — 20 tests; HTTPS mocked for these contract tests | `tests/test_telegram_verified_workflow.py` |
| Actual radar/YAMNet file inference, replay persistence, fusion/SOS and privacy rejection | PASS — 4 integration tests | `runtime/private-sensor-pipeline/results.json` |
| Public pose tracking | PASS — 5 tests | `tests/test_pose_tracking.py` |
| Public fight participant safety | PASS — 4 tests in `.venv-vision` | `tests/test_fight_participants.py` |
| Existing full HTTP integration, including real Fight V2/V3 and YOLO11-Pose video inference | PASS — 36/36 | `runtime/test-results/results.json` |
| Chromium: six scenarios, one room, actual backend risk, active Map IDs, SQLite staff lifecycle, Alerts/Review, restart deduplication, hardware isolation and fresh recorded inference | PASS — 25 checks; zero page errors/capture calls | `runtime/part4-private/browser-results.json` |
| TypeScript and production Vite build | PASS | `npm --prefix dashboard run lint` / `npm --prefix dashboard run build` |
| Authorized external SOS → Telegram test | PASS — one API-accepted request, one stored notification attempt; duplicate observation suppressed | `runtime/part4-private/telegram-result.json` |

Actual Telegram test incident: `e6ca0dcf-177f-4d42-88c9-5d8b71eba54d`. It was created and closed in an isolated integration SQLite database, using the existing configured TEST recipient only. Telegram returned API acceptance. Recipient receipt was **not verified** and is not claimed. No staff recipient fallback or production dispatch was enabled.

Recorded CPU results from the standalone integration run:

| Input | Actual model score | Candidate | Model inference / total worker wall time |
| --- | --- | --- | --- |
| Radar fall | 0.993291 | Yes | 0.194s / 19.132s |
| Radar normal | 0.217498 | No | 0.028s / 4.441s |
| YAMNet scream | 0.946568 | Yes | 0.239s / 36.369s |
| YAMNet background | 0.000968 | No | 0.246s / 17.003s |

Scores are uncalibrated classifier outputs, not probabilities of danger. Worker startup/model loading accounts for much of the wall time. No inference runs in the render loop. The Chromium checks use CPU software rendering; no universal frame-rate guarantee is asserted.

## Changed source files

- `backend/main.py`: capture-time eligibility, provenance and modality compatibility, notification queue/worker failure states.
- `backend/sensor_observations.py`: canonical connected-run IDs, timestamp forwarding, durable retries, trusted recorded assessment linkage.
- `dashboard/src/components/private-area/privateDemoWorkflow.ts`: six scenarios and a single normalized ingestion path.
- `dashboard/src/components/private-area/trackingPlayback.ts`: independent fall-only scenario and pose/sensor state.
- `dashboard/src/components/private-area/sceneTracking.ts`: conservative fall-only risk and backend recorded assessments.
- `dashboard/src/components/private-area/GuidedPrivateDemo.tsx`: six choices, immediate SOS submission, visible backend reasons/notification state.
- `dashboard/src/components/private-area/PrivateDangerScenarioControls.tsx`: six-scenario control labeling.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx`: current-run backend risk and recorded reasons without historical animation overrides.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx`: fall-only pose and shared backend-driven accent level.
- `dashboard/src/components/private-area/SensorObservationPanel.tsx`: typed backend assessment response metadata.
- `tests/test_connected_private_demos.py`: added timestamp/provenance, single-ingestion, stale retry and queue-failure coverage.
- `tests/test_sensor_observations.py`: verifies trusted recorded event/risk linkage.
- `tests/test_part4_private_browser.py`: real Chromium/FastAPI/SQLite integration and actual recorded inference controls.
- `tests/run_part4_authorized_telegram.py`: explicit manual one-message authorized TEST integration check.
- `PART4_INTEGRATION_REPORT.md`: this report. Generated browser evidence is under `runtime/part4-private`; the production bundle was regenerated under `dashboard/dist`.

This workspace has no Git repository metadata, so a Git diff/status was unavailable. The list above records files edited during this task.

## Limits and debugging outcomes

Physical radar hardware, acoustic hardware, button GPIO, device heartbeats, calibration and acquisition synchronization remain unverified/disconnected. Recorded class labels supply no measured anonymous tracks, people counts, distances or poses. Separate radar and acoustic recordings do not establish synchronized real-world fusion. The 3D bodies remain schematic simulation avatars; no private CCTV, speech recording, microphone capture or identifiable reconstruction was added.

The first browser run exposed duplicate submission from the normalized endpoint plus direct event posting; the implementation was corrected. A later run passed its functional assertions but found an unclosed SQLite test inspection connection on Windows; the harness now closes it. The fight participant tests initially used the backend environment, which lacks SciPy; they passed in the existing vision environment. Vite still reports its existing large-bundle and future config-loader warnings; the build succeeds.
