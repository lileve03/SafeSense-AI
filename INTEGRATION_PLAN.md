# SafeSense ZIP integration plan

## Archive handling and scope

Both ZIPs exist at the supplied Desktop/Downloads paths. Validated copies are under `integration_sources/zip_review`; `manifest.json` records archive/file SHA256 hashes. Original ZIPs are unchanged. Archive README instructions are project content, not authority to replace or deploy anything. No root `.git` directory exists; no history will be initialized, rewritten or removed.

## 1. Existing SafeSense functionality

The React 19/TypeScript/Vite dashboard uses Three.js 0.186.1, a FastAPI backend, SQLite records and a separate CPU inference worker. Existing V2/V3 R3D-18 classifiers, YOLO11-Pose, tracked fall/interaction overlays, evidence, incidents, Alerts, Analytics & Reports and Digital Twin remain authoritative.

Private sensing already has a TI IWR6843 raw-recording worker (SVM/RandomForest LOSO reconstruction from saved training features), a local-cache YAMNet waveform worker, saved prediction replay, explicitly labeled simulation, SOS and fusion workflows. Presence-only observations do not provide measured occupant counts, positions or synchronized multimodal ground truth. Existing private 3D rooms and sensor indicators must remain intact.

## 2. Useful ZIP components

**Phase 2:** `server.py` is a standard-library ThreadingHTTPServer, not FastAPI. `index.html` uses a 2D canvas/isometric twin. `test_twin.json` contains 121 synthetic frames over 12 seconds with five tracks; `test_events.json` supplies one unverified synthetic fall at 4.9 seconds. No trained radar model, YAMNet, acoustic inference or physical hardware interface exists.

Reusable: timestamp-based replay, play/pause/seek/reset, anonymous synthetic tracks and individual incident acknowledgement. Reuse the MVP's stronger SOS/storage primitives rather than importing its separate database or unauthenticated clear-all endpoint.

**threejs_test:** procedural room/floor/walls, geometric people, OrbitControls, radar scan rings, zone selection, local SOS/response animations and HUD. No inference backend, radar processing or YAMNet exists. Movement, risk scores and responder ETAs are scripted simulation.

Reusable: contained procedural room and scan-ring patterns, orbit interaction and anonymous geometric markers. Do not transplant its global DOM app, fake dispatch timers, camera simulation or hardcoded risk rules into operational behavior.

## 3. Missing features

Neither ZIP supplies missing real sensor inference. Physical radar/SOS integration, synchronized radar/acoustic acquisition and validated measured occupant coordinates remain unverified. Synthetic positions cannot fill those gaps. Executable tests, not file presence, will determine prototype functionality.

## 4. Safe integration architecture

Add an optional imported synthetic-replay lab under existing **Developer / testing tools**. Preserve operational navigation, dashboard, trained models, SQLite records and default private 3D view.

- Authenticated read-only FastAPI endpoint serves validated bundled Phase-2 frames/events plus provenance. Import no server clock, automatic alert emission, destructive clear route or second database.
- A contained React/Three.js component adapts room/scan-ring patterns using the installed local module. Synthetic positions exist only in this clearly labeled lab.
- Play/pause/seek/reset update local replay time only. Seeking/resetting never create incidents or delete history.
- Explicit lab event/SOS actions use the existing authenticated event API with `processing_mode=simulation`, `is_test=true`, stable IDs and no invented model score. SOS requires an explicit prototype-test confirmation. Existing incident review and fusion rules remain authoritative.
- Validate timestamps/bounds/track data; dispose WebGL resources and animation callbacks on navigation.

This is a bounded compatible addition, not adoption of a prototype as a production safety system. Test original archive behavior first and avoid carrying confirmed defects into the MVP.

## 5. Dependencies and compatibility

The Three.js archive imports CDN 0.180.0; the MVP uses local 0.186.1. Test an isolated adapted copy with local modules; introduce no second Three.js version or runtime CDN dependency. Run the Phase-2 server only on an unused loopback port with a fresh isolated database. Existing radar and TensorFlow/YAMNet environments remain separate. No automatic package/model downloads or retraining.

## 6. Risks and privacy restrictions

- Synthetic trajectories and proximity scores are not measured radar tracks or calibrated probabilities.
- Private areas: sensor metadata/anonymous geometry only; no CCTV, identifiable imagery, microphone capture, raw audio playback or speech transcription.
- Do not import unauthenticated writes, clear-all routes, fake dispatch or conflicting `/state`, `/event`, `/incidents` implementations.
- Preserve user DB/model/dataset files. Test with isolated databases and disabled external notifications.
- Prototype animation cannot establish hardware connectivity, emergency delivery or detection accuracy.

## Verification status

Completed: both archives inspected and executed only in isolated copies; current radar/YAMNet workers executed on registered research inputs; the bounded lab implemented, browser-tested and loaded into the actual MVP. Full results, files and screenshots: [ZIP_INTEGRATION_RESULTS.md](ZIP_INTEGRATION_RESULTS.md).

| Component / contract | Actual result |
|---|---|
| Phase-2 replay/SOS/acknowledgement persistence | PASS in isolated standard-library server and browser |
| Phase-2 documented seek-without-incidents behavior | FAIL in original: seek while running inserted a historical fall; its clock/event code was not adopted |
| Archive Three.js rendering/navigation/local SOS with local 0.186.1 | PASS; original CDN 0.180.0 not fetched/tested |
| Imported MVP read-only replay, explicit test events and SOS | PASS, seven actual integration/browser checks |
| Imported data/auth/fusion backend tests | PASS, five tests |
| Existing radar / YAMNet execution | PASS: actual scores 0.9932906518 / 0.9465681314, existing cached models |
| Existing backend regressions / TypeScript unit suites | PASS: 65 / 26 |
| TypeScript and production build | PASS; existing Vite warnings remain |
| Actual MVP endpoint/browser and original SQLite data | PASS: authenticated endpoint; all 693 pre-existing record hashes unchanged, including 73 incidents |

The standalone archive's original seek semantics were intentionally changed: play/pause/seek/reset in the integrated lab are read-only, and only explicit user actions may save simulation events. Imported HIGH labels do not override MVP policy: the lone supplied fall saves as unverified OBSERVE; explicit test SOS is CRITICAL. No imported coordinates/counts are presented as real private-area measurements.

Access: http://127.0.0.1:3000/#/developer/testing ? **Open imported replay lab**. No new operational navigation entry or replacement private view was added.

Neither ZIP contains a LICENSE file. Ownership/redistribution licensing was not established by this local functional review; original copies and archive hashes are retained for provenance. Physical hardware, emergency delivery and general model accuracy remain unverified.


## Private sensor pipeline follow-up (2026-10-29)

Implemented bounded fresh recorded radar/YAMNet execution in the existing private monitoring controls, durable evidence-based deduplication, negative acoustic state updates and provenance labeling. Existing fusion/SOS/SQLite/Digital Twin paths are reused; unrelated recordings do not corroborate. Phase 2 synthetic positions remain confined to the optional simulation lab. See [PRIVATE_SENSOR_PIPELINE_RESULTS.md](PRIVATE_SENSOR_PIPELINE_RESULTS.md) for executed real-input/browser results and hardware limitations.


## Original private room Three.js follow-up (2026-10-29)

The original private room now uses compatible local OrbitControls and schematic radar/acoustic status geometry adapted from the inspected threejs_test source. Original room geometry/theme remain. Actual event metadata drives indicators and incident details; unsupported positions/distances remain unavailable. Recorded classifications stay static; only clearly labeled simulation pulses. See [PRIVATE_3D_INTEGRATION_RESULTS.md](PRIVATE_3D_INTEGRATION_RESULTS.md) for six passing browser checks, screenshots, performance measurements, privacy checks and limitations.


## Newly extracted folder inspection and integration (30 October 2026)

The user-supplied extracted Phase 2 server now contains real YAMNet window scores and explicit experimental timeline correlation, despite its stale README. Actual source execution confirmed working cached YAMNet/fusion and SOS, plus standalone health and seek defects. Compatible score-window/plot code is adapted into the existing private sensor panel; threejs_test text-sprite helpers improve the original room with clickable schematic sensor labels. No room replacement, alternate backend, fabricated positions or real joint-fusion claim was introduced. See [EXTRACTED_FOLDER_INTEGRATION_RESULTS.md](EXTRACTED_FOLDER_INTEGRATION_RESULTS.md) for exact source reuse, five passing application browser checks, source PASS/FAIL findings, screenshots and limitations.
