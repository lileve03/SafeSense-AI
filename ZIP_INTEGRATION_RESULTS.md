# SafeSense ZIP integration: actual results

Completed 29 October 2026. Both requested ZIP files were found at their supplied Desktop/Downloads paths. Contents were inspected before application changes. [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) covers existing functionality, reusable pieces, missing features, architecture, dependencies/compatibility and privacy risks.

## Findings by project

| Area | Existing MVP | Phase-2 ZIP | Three.js ZIP | Decision |
|---|---|---|---|---|
| Radar inference | Raw TI CSV features + cached LOSO SVM/RandomForest worker; saved prediction replay | None: supplied synthetic tracks/annotation only | None: scripted geometric motion/proximity | Preserve existing inference; label archive trajectories SIMULATION |
| Acoustic/YAMNet | Local-cache waveform inference and non-speech event mapping | None | No YAMNet/audio inference | Preserve existing worker; import no fake acoustic results |
| SOS/fusion | Existing authenticated event API, modality/mode separation, SQLite incidents, acknowledgement | Local test SOS/ack; no sensor fusion model | Local SOS state and hardcoded interaction risk/ETA | Reuse MVP event policy; never import fake responder arrival or archive severity as truth |
| Backend | FastAPI, staff demo token, protected media, original SQLite schema | ThreadingHTTPServer; unauthenticated replay/write/clear routes | No backend/network API | Add only one authenticated read-only data endpoint |
| 3D/visualization | Existing operational Digital Twin/private room | 2D canvas/isometric visualization | Actual procedural Three.js room, people, rings and OrbitControls | Adapt safe visual patterns in an optional developer lab, not a replacement |
| Animations | Existing original private simulation and genuine sensor indicators | 121 timestamped synthetic frames, five tracks, 12 seconds | Frame-driven scripted movement/radar rings | Replay supplied timestamps and positions in a contained, labeled lab |

No radar/YAMNet model, FastAPI service, actual synchronized sensor fusion, hardware integration or validated measured tracking was hidden in either ZIP. Source inspection and actual execution both support these findings.

## Implemented compatible improvement

Open **http://127.0.0.1:3000/#/developer/testing** and select **Open imported replay lab**.

- Phase-2 synthetic frames and its unverified 4.9-second annotation are bundled with their original SHA256 provenance.
- `/testing/imported-lab` serves validated metadata only and uses the existing authentication middleware. Missing/invalid/checksum-mismatched data fails closed. No imported standalone server is mounted.
- Contained React/Three.js visualization adapts the ZIP's floor/walls, OrbitControls and radar-ring patterns using local Three.js 0.186.1. Anonymous markers follow the exact supplied frame coordinates/heights; no interpolated or measured-real positions are invented. Camera framing fits the schematic room on desktop/mobile without moving supplied coordinates.
- Play/pause/seek/reset update local replay time only. They create no incidents and clear no history. No real model score, physical distance, responder ETA or hardware status is manufactured.
- Explicit fall recording uses existing `processing_mode=simulation`, `source_type=SIMULATION`, `is_test=true`, no model version/score, and a session-stable event ID. Repeating the action is deduplicated; reset preserves records. The MVP classifies the lone unverified simulated fall as OBSERVE rather than adopting the archive's HIGH label.
- Prototype SOS requires confirmation and uses the existing SOS/incident/acknowledgement path. No physical device or emergency dispatch is claimed.
- The operational private 3D room remains unchanged and continues to show positions/counts as unavailable for presence-only observations. Imported coordinates are not fed into it. Main dashboard, camera overlays, evidence, Alerts, Reports, SQLite schema and trained models were not replaced.

## Confirmed archive defect avoided

The original Phase-2 README says seeking alone does not create incidents. Actual testing found that seeking beyond 4.9 seconds **while running** inserted a historical fall: rows increased from two to three. Its `update_clock()` checks every pending annotation `<= position`, rather than a safe crossing boundary. This behavior contract is **FAIL in the original archive**. The original ZIP/review copy was preserved; its clock/automatic insertion implementation was deliberately not imported. The integrated seek contract passes with zero new records.

The Three.js prototype's apparent responder dispatch/arrival is a local countdown and DOM update, not a working backend dispatch. Its model/risk values come from scripted simulation. Those semantics were excluded from operational behavior.

## Actual verification

| Check | Result / evidence |
|---|---|
| ZIP inspection/path-safe extraction and original hashes | PASS: [manifest](integration_sources/zip_review/manifest.json); both original ZIP hashes unchanged |
| Original Phase-2 server/browser replay, SOS, ack, SQLite persistence | PASS in isolated copy on loopback; synthetic data only |
| Original seek contract | FAIL, confirmed and avoided as above; diagnosis test itself passed |
| Original Three.js code adapted only to local imports | PASS: actual healthy WebGL canvas, zone navigation and local SOS. Original remote CDN 0.180.0 NOT TESTED |
| New integrated real browser tests | 7/7 PASS: WebGL, local clock, no seek side effects, explicit/deduplicated fall, confirmed SOS, actual ack, scene cleanup, mobile, existing pages/privacy |
| New backend tests | 5 PASS: source data/bounds/timestamps/track association, authenticated read-only endpoint, no implicit writes and existing distinct-modality simulation fusion |
| Existing backend regression runner | 65 PASS, zero failures/errors |
| TypeScript unit suites | 26 PASS, including supplied timestamp lookup, AI identity/overlay safeguards and report exports/privacy |
| TypeScript compiler | PASS: npm --prefix dashboard run lint |
| Production build | PASS: npm --prefix dashboard run build; existing native-config/large-chunk warnings remain |
| Actual running MVP smoke | PASS: endpoint 200 with token / 401 without; actual browser lab visible |
| Original database preservation | PASS: every one of 693 pre-existing record hashes unchanged after backend refresh/read-only smoke; 73 incident records preserved |
| Protected source/model preservation | PASS: 10 hashes checked, including V2/V3 classifiers, YOLO pose weights and original operational/private UI files |
| Private camera/microphone requests | PASS: zero requests and zero image/video/audio elements in imported/private views |
| Physical radar/SOS hardware, real dispatch, synchronized acquisition | NOT TESTED / not supplied by these ZIPs |

### Existing inference independently exercised

No archive inference was invented. Existing registered research files ran through the retained dedicated environments, without event posting, microphone access, waveform export or transcription:

- Radar SVM_RBF LOSO cached model: score **0.9932906517861326**, candidate true; 238 raw points / 24 frames, held-out subject `areeb`; model cache hit. Prediction 0.028044 s; whole worker 8.344294 s. [Actual result](runtime/scenario-tests/zip-integration-radar.json).
- Existing cached YAMNet: Screaming score **0.9465681314468384**, candidate true, source duration 13.780703 s; model cache hit. Prediction 0.198645 s; whole worker 17.460029 s. [Actual result](runtime/scenario-tests/zip-integration-acoustic.json).

These are recording-level model outputs, not calibrated probabilities, hardware validation, measured occupancy or synchronized multimodal evidence. No inference-model download, package installation, new model training or checkpoint replacement was performed.

## Screenshots inspected

- [Integrated synthetic 3D scene at the supplied annotation time](runtime/zip-integration/imported-synthetic-scene.png)
- [Complete imported lab and controls](runtime/zip-integration/imported-lab.png)
- [Actual existing dashboard lab](runtime/zip-integration/actual-dashboard-lab.png)
- [Mobile lab](runtime/zip-integration/mobile-imported-lab.png)
- [Original operational private view preserved](runtime/zip-integration/original-private-view-preserved.png)
- [Original Phase-2 isolated browser](runtime/archive-validation/phase2-original.png)
- [Original Three.js prototype adapted to local module](runtime/archive-validation/threejs-adapted.png)

Screenshots were opened and inspected. New room framing was adjusted after inspection so it fits narrow screens and does not hide the supplied tracks behind a coincident initial camera angle; synthetic positions themselves remain unchanged.

## Files added/modified

Application changes:

- backend/imported_lab.py ? new read-only validated archive endpoint.
- backend/main.py ? install that endpoint; existing routes/storage remain authoritative.
- backend/data/imported_phase2/test_twin.json, test_events.json, provenance.json ? original supplied synthetic data and archive/file hashes.
- dashboard/src/lib/importedReplay.ts ? actual supplied timestamp lookup/types.
- dashboard/src/components/analysis/ImportedReplayScene.tsx ? contained adapted geometry/rings, orbit, responsive fitting and resource disposal.
- dashboard/src/components/analysis/ImportedReplayLab.tsx ? opt-in simulation controls, clear provenance and explicit existing-API test actions.
- dashboard/src/pages/DeveloperTestingPage.tsx ? add optional lab card to the existing testing route.

Verification/documentation:

- tests/test_imported_archives.py
- tests/test_imported_lab.py
- tests/importedReplay.test.ts
- tests/test_zip_integration_browser.py
- INTEGRATION_PLAN.md
- ZIP_INTEGRATION_RESULTS.md
- integration_sources/zip_review/ ? immutable reviewed copies and manifest; never mounted as operational servers.

Build artifacts under dashboard/dist and isolated logs/results under runtime/archive-validation and runtime/zip-integration were generated. No dependency or model installation was needed. No Git repository was detected at this path or its parents; no Git history was created or rewritten. Original ZIP files and original user data are unchanged.

The existing idle main backend was refreshed to load the new read-only route only after verifying no queued notifications/jobs and taking per-record hash snapshots. The AI worker and dashboard services were not replaced. No actual user incidents were generated during the production smoke; all event/SOS/fusion tests used isolated SQLite with external notifications disabled.

## Reproduction and remaining limitations

```powershell
.venv-vision/Scripts/python.exe tests/test_imported_archives.py
.venv-vision/Scripts/python.exe -m unittest tests.test_imported_lab
.venv-vision/Scripts/python.exe tests/test_zip_integration_browser.py
.venv-vision/Scripts/python.exe tests/run_cpu_monitoring_checks.py
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

Raw outcomes: [archive tests](runtime/archive-validation/results.json), [integrated browser](runtime/zip-integration/results.json), [actual smoke/data preservation](runtime/zip-integration/actual-smoke-results.json), [backend regressions](runtime/cpu-visualization/backend-results.json).

The imported lab is intentionally simulation-only. Neither archive supplies measured private-area localization, real hardware connectivity, validated detection accuracy, synchronized radar/acoustic input or real responder delivery. No LICENSE file was present in either archive; redistribution licensing was not established. The original CDN version was not downloaded. WebGL compatibility was tested using local 0.186.1 and Chromium software rendering; hardware-specific GPU behavior remains unverified. Existing TensorFlow deprecation and original private-view shadow-map warnings were observed, without browser runtime failures.
