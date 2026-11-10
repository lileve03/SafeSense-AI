# Extracted Reference Folder Integration - Actual Results

Date: **30 October 2026, Asia/Singapore**.

## Inspected folders

Only the supplied extracted folders were used for this inspection:

- `SafeSense_Phase2_End_to_End_Test/SafeSense_Phase2_End_to_End/`
- `threejs_test/`

All eight original files, including the reference `incidents.db`, were hashed and left unchanged. No archive search/extraction or old review-copy lookup was used. Reference instructions were treated as project documentation, not authorization to replace SafeSense or clear databases.

## Actual findings

### SafeSense Phase 2

The current `server.py` is newer than its README: it contains **real YAMNet inference**, non-speech Screaming window scores, an acoustic HTTP endpoint and explicit experimental fusion. The README incorrectly says there is no YAMNet inference.

Radar is still synthetic replay: 121 frames over 12 seconds, five supplied tracks, and one unverified fall annotation at 4.9s. There is no raw radar-processing/model implementation in this reference. It cannot supply genuine room positions, occupancy or measured distances.

The server is `ThreadingHTTPServer`, not FastAPI. Inspected routes include health/state, replay controls, SOS, acknowledgement, acoustic analysis and fusion configuration. No automated tests or FastAPI application are supplied in this folder. Its own database and unauthenticated standalone service were not imported into the operational application.

Executed the actual reference SOS HTTP/SQLite acknowledgement and the original `infer_audio`, `audio_peak_events` and `try_fuse` functions in isolated copies. Actual YAMNet ran with the retained local pretrained cache, without downloading weights. A registered research recording was converted to the reference's strict 16-kHz mono PCM16 format in RAM. Its real reference output was **0.9466**, **28 windows**, **3 threshold windows**. Explicit synthetic-radar/independent-audio correlation created one deduplicated experimental fusion link, with the reference's own warning that this is not a verified shared incident.

Two real reference defects were confirmed and deliberately not imported:

- Standalone `/health` drops the request because `importlib.util` was not explicitly imported.
- Seeking while playing past the supplied fall inserts one historical incident despite the documented no-side-effect seek behavior.

The authenticated SafeSense backend, existing arrival-window fusion policy and safe replay controls remain authoritative.

### threejs_test

Inspected and executed the actual `main.js` scene against the application's compatible local Three.js 0.186.1 modules. WebGL rendered without page errors. The reference import map specifies remote 0.180.0; that CDN version was not fetched or claimed verified.

Useful code includes text sprites, reusable geometry, sensor rings, OrbitControls and scene interaction patterns. Its people/movement, distance, speed, interaction risk, responder ETAs and dispatch states derive from scripted scene values. They are not actual radar inference or responder telemetry and were not imported as operational data. No inference/network backend is implemented there.

## Source files actually reused

| Reference file | Reused compatible code | Existing application destination |
| --- | --- | --- |
| `SafeSense_Phase2_End_to_End_Test/SafeSense_Phase2_End_to_End/server.py` | YAMNet class-series extraction, nominal 0.48s enumeration and above-threshold window selection from `infer_audio` / `audio_peak_events`; adapted with finite-score validation, original precision and explicit timing limitations | `backend/acoustic_windows.py`, `scripts/scenario_sensor_worker.py` |
| `SafeSense_Phase2_End_to_End_Test/SafeSense_Phase2_End_to_End/index.html` | `plotAudio` score/threshold plotting logic, adapted to scalable SVG and metadata-only replay controls | `dashboard/src/components/analysis/AcousticScoreTimeline.tsx` |
| `threejs_test/main.js` | `createTextSprite` / `updateSpriteText` canvas-texture/sprite construction, adapted to typed reusable fixture labels, raycast selection, lifecycle disposal and responsive positioning | `dashboard/src/components/private-area/sensorTextSprite.ts`, `PrivateAreaDigitalTwin3D.tsx` |

The code was adapted into normal application modules; production never imports the reference Python module, which would create a second database at import time. Reference room geometry was not copied over the original room. `test_twin.json`, `test_events.json`, the standalone `index.html` import map and `incidents.db` were inspected, not used as new operational measurements or another deployed application.

## Visible functional improvements

### Original private 3D room

- Original floor, walls, entrance partition, sensor fixtures, lights, camera setup, simulation mannequins and premium SafeSense styling remain.
- New schematic RADAR / ACOUSTIC / SOS text sprites point back to the existing fixtures with lightweight leader lines. Labels are annotations, not fabricated hardware/sensor coordinates.
- Actual canvas raycasting selects a fixture and displays its current metadata status. Accessible sensor buttons provide the same selection.
- Label visibility toggle, original Orbit/Zoom/Reset, incident-details action and toilet navigation work.
- Label textures are created once and disposed with the room. Mobile annotations clamp within the viewport without moving the fixture geometry. Idle recorded views still add zero continuous renders during the measured check.
- Recorded class-only inputs produce zero located occupants and no measured separation. Anonymous simulation and unsupported spatial values remain explicitly labeled/unknown as before.

### Existing recorded sensor panel

- Fresh registered YAMNet execution now returns actual Screaming model-window scores, nominal recording offsets, receptive-window length and threshold states. Worker results remain persisted through the existing scenario-run SQLite records.
- A vector chart displays the genuine series and actual threshold. Play/pause/seek and peak inspection update metadata visualization only; they do not play/record audio, transcribe speech, create incidents or invent event timestamps.
- Timing is explicitly nominal: 0.48s hops / 0.96s model windows, with overlap/padding. These are not validated physical event times or synchronized radar acquisition timestamps.
- Fresh inference remains separate from saved prediction replay and simulation. Existing local weights, source SHA checks, bounded CPU queue, event deduplication and current backend schema remain in use.

### Shared incidents, fusion and privacy

- Positive acoustic/radar outputs continue through the same existing EventIn/FastAPI path, SQLite incidents, context refresh, Alerts and Digital Twin. The actual incident-details control opens the persisted dossier.
- Unrelated recorded radar and acoustic inputs remain separate OBSERVE observations. Their nominal timelines are not automatically aligned into a real HIGH incident.
- Explicit labeled simulation radar + acoustic fusion creates HIGH; SOS independently creates CRITICAL. No fake teacher, hardware or external dispatch is introduced.
- Private vision source/modality/media submissions are rejected. Browser checks found no private video/image/audio elements and zero media capture calls.
- Fight V2/V3, YOLO Pose, their weights/code, Live Monitoring, Telegram implementation and Reports were not changed. No retraining, database migration/reset or room replacement occurred.

## Actual application verification

| Check | Result |
| --- | --- |
| Adapted Three.js text sprites raycast inspection toggle and original controls | PASS |
| Phase 2 score-window plot adapted to fresh local YAMNet with side-effect-free replay | PASS |
| Actual radar existing fusion SOS SQLite and incident details stay integrated | PASS |
| Actual negative YAMNet input remains negative and clears acoustic indicator | PASS |
| Privacy sensor synchronization page navigation responsive design and models preserved | PASS |

The new browser suite passed **5/5** checks with actual model execution and no page errors. Tests use isolated SQLite databases and disabled external notifications. A navigation test initially assumed the Digital Twin always reopened on the map; it was corrected to respect the application's remembered private-room state, then the final suite passed.

Measured genuine outputs:

| Input | Actual score | Actual metadata | Result |
| --- | --- | --- | --- |
| FSD50K Screaming research recording | 0.9465681314468384 | 28 YAMNet windows, 3 above threshold | OBSERVE incident, chart and peak inspection |
| FSD50K background recording | 0.0009683079551905394 | 12 real windows, none above threshold | No scream incident; acoustic indicator clears |
| TI raw radar fall recording | Existing actual SVM_RBF output | 238 points / 24 frames | OBSERVE; points are not people |
| Labeled independent simulation radar + acoustic | No fabricated model score | Existing explainable fusion evidence | HIGH |
| Explicit test SOS | No fabricated sensor score | Existing SOS event metadata | CRITICAL |
| Acoustic score play/seek | Same actual model series | No new acquisition | Zero additional incidents |

Additional checks:

- Three score-window unit tests: **PASS** (finite bounds, threshold, offsets and padded-end handling).
- Existing backend/incident/privacy/notification/model queue regressions: **65 PASS**, zero failures/errors.
- `npm run lint` / TypeScript: **PASS**.
- `npm run build`: **PASS**; existing Vite config/large-bundle warnings remain.
- Actual :3000 dashboard desktop/mobile smoke: **PASS**, controls visible and interactive, zero page errors.
- All **696 original SQLite record body hashes unchanged** in the actual-dashboard smoke; browser suite separately preserves **73 original incidents**.
- Protected model/pipeline/page files remained unchanged throughout integration checks.

## Reference-project validation (separate from application results)

These are honest source findings; the two reference failures were not imported into the MVP.

| Reference check | Actual result |
| --- | --- |
| Reference standalone health endpoint | FAIL |
| Reference radar is supplied synthetic replay, not hardware inference | PASS |
| Reference seek while playing must not insert historical incidents | FAIL |
| Actual reference SOS HTTP and SQLite acknowledgement | PASS |
| Actual Phase2 infer_audio, audio_peak_events and explicit experimental fusion | PASS |
| Actual threejs_test scene renders against compatible local installed Three.js | PASS |
| Both extracted reference folders unchanged including original incidents.db | PASS |

Reference checks: **5 PASS, 2 FAIL**. No blanket claim that every supplied file was functional.

## Screenshots and evidence

- [New clickable labels in the original room](runtime/reference-folder-integration/original-room-clickable-sensors.png)
- [Genuine YAMNet score-window chart](runtime/reference-folder-integration/actual-yamnet-score-windows.png)
- [Existing labeled fusion and original room](runtime/reference-folder-integration/sensor-fusion-original-room.png)
- [Actual running dashboard sensor inspection](runtime/reference-folder-integration/actual-dashboard-sensor-inspection.png)
- [Final mobile labels and inspection](runtime/reference-folder-integration/actual-dashboard-mobile-labels.png)
- [Application browser PASS results](runtime/reference-folder-integration/results.json)
- [Actual dashboard/data preservation](runtime/reference-folder-integration/actual-smoke-results.json)
- [Reference PASS/FAIL results](runtime/extracted-reference-review/results.json)
- [Original reference file hashes](runtime/extracted-reference-review/folder-manifest.json)
- [Original reference YAMNet/fusion output](runtime/extracted-reference-review/reference-acoustic-results.json)
- [Actual standalone Three.js scene](runtime/extracted-reference-review/actual-reference-threejs.png)

Original-room, mobile and score-chart screenshots were opened and visually inspected. Label placement was refined after inspection so the desktop labels avoid the original status legend; mobile annotations are clamped within the canvas. Status controls and privacy labels retain the existing design.

## Modified/new files

Application:

1. `backend/acoustic_windows.py` (new)
2. `scripts/scenario_sensor_worker.py`
3. `dashboard/src/components/analysis/AcousticScoreTimeline.tsx` (new)
4. `dashboard/src/components/analysis/PrivateRecordedSensorPanel.tsx`
5. `dashboard/src/components/private-area/sensorTextSprite.ts` (new)
6. `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx`

Tests:

- `tests/test_acoustic_windows.py` (new)
- `tests/test_reference_folder_integration_browser.py` (new)
- `tests/test_extracted_reference_projects.py` (new)
- `tests/reference_acoustic_runner.py` (new; dedicated environment helper)

Documentation: `EXTRACTED_FOLDER_INTEGRATION_RESULTS.md` (new), `INTEGRATION_PLAN.md` (follow-up). Generated dashboard/dist assets rebuilt. Both supplied reference folders are unchanged.

## Remaining limitations / NOT TESTED

- No physical radar, acoustic sensor, SOS button, surveyed installation or real occupancy/distance calibration was available.
- No validated simultaneous radar/audio recording exists; nominal YAMNet windows do not establish joint event occurrence. The reference's manually aligned synthetic/real fusion is experimental only.
- The acoustic model exposes a non-speech class score, not recognition accuracy or a calibrated safety probability. No private-area CCTV, identifiable reconstruction, speech recording/transcription or microphone capture was enabled.
- No arbitrary WAV upload endpoint from the unauthenticated prototype was added; existing authorized registered recordings and sensor metadata ingestion are retained.
- The reference's remote CDN 0.180.0 and first-run model downloads were not fetched. Compatibility was verified with installed local Three.js and YAMNet weights.
- Telegram behavior is preserved and covered by mocked transport safety regressions; no new real Telegram message/delivery verification was performed in this change.
- Native hardware/safety performance remains unvalidated. Every new 3D position here is an explicitly schematic fixture/annotation position, never an inferred person/radar measurement.
