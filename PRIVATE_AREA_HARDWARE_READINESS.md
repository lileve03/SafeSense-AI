# SafeSense Private Area hardware readiness

Validated 2026-11-02 on the local Windows workstation.

**Result: software prototype checks PASS; physical deployment is NOT VERIFIED. Hardware remains Disconnected.** No physical driver, device identity, heartbeat, mounting calibration or physical tracking stream has been verified. LIVE_HARDWARE ingestion deliberately returns HTTP 503. A running FastAPI server is not evidence of working radar hardware. Future device capabilities must be established individually.

## Verified behavior

| Requirement | Actual result |
| --- | --- |
| Original Three.js Toilet | PASS: 21 original room/material/light/camera declarations, nine fixture placements and initial orbit match the archived component. Orbit, zoom, reset, track and fixture selection work in Chromium. Campus navigation and theme retained. |
| Normal Presence | PASS: anonymous markers enter/move/leave; normal signals; no fabricated danger incident. |
| Two-Person Proximity | PASS: valid coordinate separation, duration candidate and relevant track highlights; proximity alone creates no danger incident. |
| Repetitive Abnormal Motion | PASS: temporal position history produces explainable motion features and a review candidate; connected simulation produces OBSERVE, not a fighting/bullying verdict. |
| Possible Fall + Acoustic Impact | PASS: explicit synthetic fall and impact animate corresponding indicators; independent virtual modalities inside the existing fusion window produce HIGH. This is not real radar/YAMNet inference. |
| SOS Emergency | PASS: direct help request produces CRITICAL independently of model confidence; SOS indicator and incident workflow synchronize. |
| Smooth anonymous tracking | PASS: five paths sampled every 0.01 simulation seconds; consecutive active positions move less than 0.05 m. Browser validates multiple moving IDs, derived count, optional bounded trails, selection and speed/pause/restart controls. No recognizable people. |
| Distance | PASS: Euclidean XYZ calculations match coordinates, including an exact 3–4–5 m fixture. Missing coordinates yield unavailable distance, never invented zero positions. |
| Radar/acoustic/SOS/fusion | PASS: scenario indicators and persisted fusion outcomes checked against backend responses. Simulated signals and scores stay labeled SIMULATED. |
| SQLite and synchronization | PASS: new backend process reloads the same incident, acknowledgement and evidence; replay retries do not duplicate them. Map, Alerts and Incident Review share canonical incident IDs and response transitions. |
| Refresh/restart | PASS: browser refresh restores exercise identity paused at Ready/0 s; no automatic duplicate incident or response. Starting again continues the same incident workflow. Actual backend process restart preserves SQLite evidence. Late unrelated impact remains OBSERVE rather than falsely upgrading an old fall to HIGH. |
| Missing data/track loss/ID changes | PASS: missing/partial/nonfinite coordinates, invalid/stale timestamps, unsupported tracks, dropped IDs and replacement IDs clear invalid markers, distance, trails and highlights. No identity matching is invented. |
| Mode isolation | PASS: source, device and session changes isolate visualization history; panel also checks zone/mode. Unverified live-shaped packets are suppressed in telemetry and rendering. Client-provided hardware verification is rejected by the strict backend schema. |
| Privacy | PASS: no private-area video, microphone capture, speech recording or transcription added. Browser capture calls: zero. Observation schema rejects media/transcript fields. Existing authorized research recordings are distinct from private-area capture. |
| Telegram | PASS for response handling with mocked transport and actual disabled status in isolated workflows. External API delivery and recipient receipt: NOT_RUN. No external messages sent during this validation. |

Guided response automatically demonstrates acknowledgement/resolution only on its own SIMULATION test incident. The responder and notes explicitly say simulated, not a human acknowledgement or arrival. It does not automatically mark danger VERIFIED. Separate browser tests explicitly exercise NEW → ACKNOWLEDGED → VERIFIED → RESOLVED through existing response endpoints using a test operator.

The original-room archive is `runtime/private-view-restoration/archive/components/private-area/PrivateAreaDigitalTwin3D.tsx`, SHA-256 `e062cf1fb2e609c2e53235e8fb0a070452e4250b09a0c64729fbe19bd05693b8`. The full current component has additional tracking code; the preservation assertion compares original room construction and placement, not byte equality of the entire file. Seven protected source/model files also retained their hashes during the browser fault tests.

## Actual validation results

All commands below were executed, not proposed. Final runs: **104 backend tests PASS; 10 frontend tests PASS; 73 browser checks PASS; zero final failures.** One external Telegram browser check is explicitly NOT_RUN and excluded from the PASS total. Test databases were isolated; existing user incident data was not reset. External dispatch was disabled or transport was mocked.

Backend commands use `.venv-vision/Scripts/python.exe tests/<file>`:

| File | Tests passed |
| --- | ---: |
| test_private_area_readiness.py | 6 |
| test_connected_private_demos.py | 10 |
| test_incident_response_workflow.py | 10 |
| test_track_motion.py | 23 |
| test_track_motion_api.py | 6 |
| test_sensor_observations.py | 8 |
| test_radar_tracking_simulation.py | 4 |
| test_notification_safety.py | 13 |
| test_telegram_verified_workflow.py | 20 |
| test_backend_telegram_environment.py | 4 |

Frontend:

```powershell
node dashboard/node_modules/tsx/dist/cli.mjs --test tests/privateAreaHardwareReadiness.test.ts
npm.cmd --prefix dashboard run lint
npm.cmd --prefix dashboard run build
```

All ten Node assertions, TypeScript checking and Vite production build passed. Build retains nonfatal loader `__dirname` and large-chunk warnings; these are not a hardware or performance certification.

Browser commands use `.venv-vision/Scripts/python.exe tests/<file>` and actual Chromium/WebGL:

| File | Checks passed | Evidence |
| --- | ---: | --- |
| test_private_area_readiness_browser.py | 7 | [Refresh, process restart, packet loss and hardware gates](runtime/private-area-hardware-readiness/browser-readiness-results.json) |
| test_guided_private_demo_browser.py | 16 | [Guided workflow](runtime/guided-private-demo-checks/results.json) |
| test_interactive_tracking_browser.py | 16 | [Tracking, interactions and performance](runtime/interactive-tracking-checks/results.json) |
| test_connected_private_demos_browser.py | 28 | [Scenarios, incidents and actual recorded inference](runtime/connected-private-demo-checks/results.json) |
| test_sensor_observations_browser.py | 6 | [Shared interface and mode guards](runtime/hardware-prototype-checks/browser-results.json) |

Recorded/live-shaped packet-loss fixtures are **synthetic test inputs**, not physical measurements or genuine recorded positions. The standalone renderer's trusted-verification fixture is explicitly test-only; it does not establish a physical connection.

Actual registered-recording jobs ran through existing worker endpoints: `radar_raw_fall`, SVM_RBF-LOSO-reconstructed, score **0.9932906517861326**; `acoustic_scream`, YAMNet-pretrained-local-cache, score **0.9465681314468384**. These are individual inference outputs, not accuracy measurements. They retain independent recording provenance and OBSERVE outcomes, with no fabricated spatial tracks or cross-recording fusion. Scream is not an acoustic impact recording. No synchronized real fall-plus-impact recording was demonstrated.

Telegram contract tests distinguish successful API acceptance with message ID (`SENT`, public `API_ACCEPTED`), explicit rejection (`FAILED`), and timeout/missing message ID (`DELIVERY_UNKNOWN`, public `UNKNOWN`). Acceptance is not recipient receipt. Duplicate accepted/uncertain dispatch is suppressed. Authenticated receipt contracts were tested with fixtures; no real recipient receipt is claimed.

### Performance measurements and limits

[Backend evidence](runtime/private-area-hardware-readiness/backend-readiness-results.json): 1,200 observations, six tracks each, synthetic 10 Hz timestamps, 1.3498 s wall time and 1.2969 s process CPU; mean process CPU 1.0807 ms/observation, median elapsed 1.1909 ms and p95 elapsed 1.5297 ms. History reached 81 samples, below the 256 cap; stream registry remained at 64 after 70 sessions. This measures normalization/motion processing, excluding physical acquisition and ML inference.

Actual headless Chromium/SwiftShader: **18.33 FPS**, 60 draw calls, 960 triangles, last measured render CPU 1.3 ms, 0.142 s script execution over a 3 s sample, 50.96 MiB JS heap. Browser total task time was 3.004 s over that sample, so this is not a claim of low overall CPU usage on every machine. Geometry counts stayed 36→36 and textures 14→14. Paused render count increased by zero over one second. Rendering is capped at 30 FPS with bounded trails and pooled track objects. This test is not a long-duration leak, physical GPU or deployment-load benchmark.

Dashboard HTTP 200 and backend `/health` online were checked after the final suites. Server availability does not change Hardware Disconnected.

## Hardware adapter specification

This section specifies the future integration boundary. Driver implementation, connection-health lifecycle and physical commissioning are **not complete**. See also [current schema and endpoints](HARDWARE_SENSOR_INTERFACE.md) and [backend motion rules](PROXIMITY_MOTION_RULES.md).

### Capabilities and packets

Maintain a device-specific manifest: manufacturer/model, firmware, packet protocol/version, serial identity, transport, clock domain, units, mounting calibration revision and independently verified capabilities. Presence classification, point clouds, stable anonymous tracks, XYZ position, vector velocity, quality/SNR, acoustic classes and SOS are separate optional capabilities. A point cloud is not a person tracker. A class-only device cannot supply people count or separation distance. Do not promise that the present radar or any future device supports all of them.

The vendor decoder should accept bounded, documented packets containing device/session identity, sequence/frame ID, capture ticks or capture UTC, receipt UTC, optional tracks and optional point returns. Track entries need a session-scoped anonymous ID and supported measurements only. Preserve vendor quality semantics; do not map an unspecified quality score to confidence without validation. Raw return attributes such as intensity, radial Doppler and SNR remain vendor-specific until a versioned schema supports them.

Example decoder-side structure, **not directly accepted by the strict observation POST**:

```json
{
  "protocol_version": "vendor-specific",
  "device_id": "commissioned-device-id",
  "boot_session": "unique-per-reboot",
  "sequence": 123,
  "capture_ticks": 456789,
  "clock_domain": "documented-device-monotonic",
  "received_at": "timezone-bearing UTC",
  "tracks": [{"id": "session-local-id", "position_sensor": [1, 2, 0.8]}],
  "points": [{"position_sensor": [1, 2, 0.8], "radial_doppler_mps": 0.2}]
}
```

Validate framing, length, endianness, checksum where available, protocol/TLV versions and array limits before normalization. Derive a stable observation ID from device/boot/frame identity; retries must preserve payload and ID. Reject conflicting reuse. Never reuse tracker IDs across reboot without a new `tracking_session_id`.

Normalize to `backend.sensor_observations.Observation` version 1: source mode, device ID, registered private zone ID, timezone-aware timestamp, timestamp basis, data validity/reason, optional session ID and calibrated coordinate frame. Optional tracks carry ID, complete finite XYZ position, optional complete XYZ velocity, quality 0–1 and SNR dB when supported. Optional point cloud currently accepts **XYZ only**; acoustic events accept class/confidence metadata; SOS is ACTIVE/INACTIVE/UNKNOWN. Null means unsupported/unavailable; an empty supported array means no tracks detected. Neither establishes ground-truth occupancy.

Current bounds: 128 tracks, 4,096 points, 32 acoustic events per observation; visualization pools eight track slots and demonstration paths use at most six. These are software bounds, not promised sensor capacity. Motion-preview batches are simulation-only, at most 121 observations/eight tracks and no points. Schema rejects unknown fields, nonfinite numbers and duplicate track IDs. Vendor extensions require an explicit versioned change, not silently added JSON keys.

All modes use the same normalized observation/visualization interface. `/sensors/observations` accepts explicit simulation; `/sensors/observations/replay` accepts a persisted recorded event ID through the recorded adapter. LIVE_HARDWARE is gated by the disconnected adapter. `/sensors/motion/preview` is read-only simulation analysis. `/event` and existing incident response endpoints remain the incident workflow; hardware integration must not write incident rows directly.

### Time and continuity

Map device ticks to timezone-aware UTC using a measured clock relationship and record uncertainty/drift. Receipt time is not capture time. Current timestamp bases are CAPTURE_TIME and REPLAY_EVENT_TIME; the current recorded classifier has only replay-event time, so temporal spatial analysis remains unavailable. Unsynchronized device data must remain unavailable for temporal fusion until the schema/adapter explicitly handles its provenance; never relabel receipt time as capture time.

Detect sequence gaps, out-of-order frames, clock jumps and boot/session changes. Existing live/simulation freshness is 10 s maximum age and 5 s future tolerance; temporal continuity is stricter at 0.75 s. Backend history resets on dropped IDs, missing coordinates/provenance and implausible jumps rather than connecting unrelated people. Backend configuration owns these thresholds. Do not extrapolate measurements across missing frames or join changed IDs by assumption.

### Coordinates and mounting calibration

Canonical frame: `zone_meters_x_right_y_forward_z_up`; position metres, velocity metres/second. Establish an actual surveyed origin, axis orientation and floor reference. A decoder transform should explicitly apply

`p_zone = R * B * (scale * p_sensor) + translation`

where B handles documented axis order/handedness and R is the mounting rotation. Velocity uses the corresponding unit/axis/rotation transform without translation. Radial Doppler is not XYZ velocity. A 2D device must not receive an invented measured Z merely to satisfy the current XYZ schema; omit unsupported position or introduce a documented schema extension first.

Record mounting position/height, yaw/pitch/roll, scale, calibration version/date, device identity and measured residual error against known points. Revalidate after moving/reconfiguring the sensor. The Three.js `(x,z,y)` display mapping is a presentation mapping, not sensor calibration. Existing room dimensions, sensor heights and radar coverage are illustrative, not a surveyed installation or validated penetration through cubicles.

Commission coverage using known positions/movements across entrances, cubicles and blind spots. Measure occlusion, reflections/multipath, door/partition effects, interference, effective FOV/range, ID stability and stationary-person behavior. Evaluate falls separately with suitable safe labeled data. Existing IWR6843 research classification performance does not establish physical performance in this Toilet or another device/domain.

### Connection health, security and privacy

Proposed states: DISCONNECTED → CONNECTING → VERIFIED_STREAMING, with DEGRADED/STALE/ERROR on heartbeat loss, clock drift, sequence loss, calibration or packet failures. Transport connection alone is insufficient. Verification requires authenticated expected device identity, supported manifest, calibrated frame and repeated fresh valid packets. Define heartbeat/stale budgets against the actual device frame rate. Current implementation intentionally stays Disconnected; the lifecycle above is a commissioning requirement, not an implemented driver.

Only a trusted server-side adapter may establish verification. Browser flags and staff API credentials do not physically verify hardware. Keep authenticated ingestion, rate/size limits and isolated test/live routing; fail closed on unsupported packets. Expose explicit health reasons without leaking secrets.

Physical SOS needs authenticated device/press identity, timestamp and debounce/idempotency; ACTIVE is a direct help request independent of ML confidence, with UNKNOWN on lost state. Keep commissioning traffic test-marked until approved for real operations. Acoustic hardware may supply approved event metadata only; a companion processor/model is an optional separately validated capability. No private-area video, speech recordings, transcripts or biometric identities belong in this interface.

### Analysis and fusion acceptance

Distance requires valid supported spatial coordinates. Velocity/acceleration/direction changes and repetitive motion require reliable timed history. Current repetition rule uses an 8 s window, at least 4 s supported span, three reversals of at least 150 degrees, meaningful motion legs, path length at least 2 m and net/path ratio at most 0.5. Proximity requires less than 0.8 m for at least 3 s. Quality, speed, gap and displacement guards apply; consult backend rules for the full configuration. These are explainable review candidates, not proof of violence or ML accuracy estimates.

Real multi-sensor fusion requires actual independently supported sources in the same zone with valid synchronized timing within existing fusion rules. Do not combine unrelated research recordings to imply a physical fall. Never invent missing tracks/count/distance, infer height from a class label or display synthetic scores as real inference.

Before enabling live operation, complete device-specific packet fixtures, physical mounting survey, timestamp/transform checks, missing-data/reboot tests, ID/occupancy validation, measured latency/load and long-duration tests, safely labeled scenario evaluation, hardware SOS tests and authorized notification/recipient-receipt trials. None of those physical deployment trials is certified by this report.

## Files changed in this completion pass

- `dashboard/src/components/private-area/SensorObservationPanel.tsx`: suppress wrong-mode/zone and unverified live observations in telemetry and scene.
- `dashboard/src/components/private-area/trackingPlayback.ts`: require valid timestamp/frame/complete coordinates, reject duplicate IDs and unverified live data, isolate source/device/session rendering history.
- `tests/test_interactive_tracking_browser.py`: explicitly label the trusted live-renderer fixture test-only.
- Added `tests/privateAreaHardwareReadiness.test.ts`, `tests/test_private_area_readiness.py`, `tests/readiness_persistence_worker.py`, `tests/readiness_test_server.py`, `tests/test_private_area_readiness_browser.py` and this report.

Previously implemented upgrade components inspected and exercised include `backend/main.py`, `backend/sensor_observations.py`, `backend/track_motion.py`, `backend/scenario_testing.py`, radar/acoustic workers, notification/storage modules, `PrivateAreaDigitalTwin3D.tsx`, `GuidedPrivateDemo.tsx`, `PrivateAreaMonitoringView.tsx` and the existing incident/map interfaces. Existing radar fall classification and incident evidence are retained.

Related documentation: [Guided demo](GUIDED_PRIVATE_DEMO.md), [Connected scenarios](CONNECTED_PRIVATE_SCENARIOS.md), [Tracking simulation](INTERACTIVE_TRACKING_SIMULATION.md), [Sensor interface](HARDWARE_SENSOR_INTERFACE.md), [Motion rules](PROXIMITY_MOTION_RULES.md).
