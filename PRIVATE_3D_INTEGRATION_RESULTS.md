# Original Private 3D View - Three.js Integration Results

Date: 2026-10-29. Existing room improved in place; no room redesign, backend replacement or dataset/model changes.

## Reused compatible components

Inspected source: integration_sources/zip_review/threejs/threejs_test/main.js, previously extracted from the user-supplied threejs_test.zip. Reused its local-compatible OrbitControls pattern and lightweight radar RingGeometry/status fixture approach. Everything runs through the existing React/TypeScript lifecycle and installed Three.js 0.186.1. No CDN scripts, new dependencies, renderer, postprocessing pipeline or copied standalone application were introduced.

The original 8 x 7 floor, grid, semi-transparent walls, entrance privacy alcove, ceiling radar fixture, wall SOS box, lighting arrangement, original camera position, dashboard layout and light theme remain. Original anonymous simulation mannequins are retained only in clearly labeled simulation. Recorded sensor classifications never create located people.

## Behavior

- Reviewed OrbitControls provides pointer/touch orbit and wheel zoom. Existing Zoom In, Zoom Out and Reset buttons remain; Reset restores the original camera position.
- A small radar status ring is attached to the existing ceiling fixture: gray without observation, teal with radar output, red for a possible fall candidate. A low-poly wall acoustic marker changes to amber for actual scream/impact metadata. The existing wall SOS box glows red while an active Critical SOS incident exists.
- Fixture coordinates are explicitly schematic, not surveyed hardware locations. Abstract markers represent sensor fixtures/status, not identifiable people or reconstruction from private-area media.
- Explicit presence metadata can show a presence-only notice. Class-only fall/normal-motion results no longer imply presence detection, occupant count or located people. Existing recorded inputs provide none of those measurements.
- Recorded class-level observations remain static: no invented per-frame trajectory, timing, measured range or moving person. Simulation's illustrative radar pulse is clearly labeled. Distance remains Unavailable in recorded/backend mode; simulation distance is explicitly Simulated.
- Fall, acoustic, SOS, risk status and provenance appear in compact responsive overlays. Normal acoustic metadata clears the acoustic signal indicator. The risk indicator opens the highest-priority actual unresolved SQLite incident in the selected zone through the existing incident dossier.
- Clicking the private toilet on the original Digital Twin still opens this original room. Leaving disposes controls, observer/listeners, geometry/materials, shadow target and renderer; reopening creates one canvas.
- Idle recorded scenes render only on state, camera or size changes. Simulation is capped at 30 FPS, uses elapsed time and pauses while hidden. Pixel ratio retains the original cap of 2. No scene rebuild occurs on each sensor update.

## Actual validation

Executed: `.venv-vision/Scripts/python.exe tests/test_private_three_integration.py`.

| Check | Result | Actual evidence |
| --- | --- | --- |
| Toilet map to original room | PASS | Real browser navigation, valid WebGL context, canvas 578 x 458 |
| Orbit / Zoom / Reset | PASS | Drag changes actual camera coordinates, both zoom buttons work, reset restores initial coordinates |
| Recorded radar | PASS | Fresh raw TI CSV inference, SVM_RBF score 0.9932906517861326, real fall observation updates room |
| Actual incident details | PASS | Clicking scene risk indicator requests the corresponding persisted incident report and opens dossier |
| Recorded acoustic | PASS | Fresh local YAMNet scream inference updates acoustic marker/banner |
| Negative acoustic update | PASS | Saved negative observation clears active acoustic indicator |
| SOS and risk | PASS | Explicit simulation SOS via existing backend produces CRITICAL and updates room |
| Unsupported geometry | PASS | Recorded fall has zero positioned occupants; no inferred presence from class-only result |
| Recorded idle cost | PASS | Zero extra renders in measured 600 ms interval |
| Simulation animation | PASS | 14 renders in measured 600 ms; labeled simulation, capped at 30 FPS |
| Close/reopen | PASS | Canvas disposed on leaving; exactly one on reopening |
| Privacy rejection | PASS | Backend rejects private vision source/modality and media (403/422) |
| Private media/capture | PASS | Zero video/image/audio elements, zero getUserMedia calls |
| Mobile | PASS | 390 x 844 browser viewport; no horizontal overflow; screenshot labels visually inspected after overlap fix |
| Browser suite | PASS | 6/6 checks, zero page errors |
| Existing backend regressions | PASS | 65 tests, zero failures/errors |
| TypeScript | PASS | npm run lint / tsc --noEmit |
| Production build | PASS | npm run build; existing Vite configuration and large-bundle warnings remain |
| Actual dashboard smoke | PASS | Existing :3000 dashboard opens original room; no events created; all 696 SQLite record hashes unchanged |
| Physical installation / positions / ranges | NOT TESTED | No connected hardware, surveyed layout or validated measurements available |
| Real recorded per-person motion | NOT TESTED | Existing radar inference exposes recording-level labels, not calibrated per-frame trajectories |

Browser suite uses an isolated SQLite database and disabled notification transports. It verifies original 73 incidents remain unchanged and hashes 10 application/model files throughout the test; Fight, YOLO, Live Monitoring and Analytics files were not modified by this task. A separate read-only smoke test checks the actual running dashboard and all existing record hashes. No emergency/staff messages were sent.

## Screenshots and machine-readable evidence

- [Original room, no sensor data](runtime/private-three-integration/original-room-empty.png)
- [Actual recorded radar possible fall](runtime/private-three-integration/original-room-recorded-fall.png)
- [Acoustic and explicit SOS](runtime/private-three-integration/original-room-acoustic-sos.png)
- [Clearly labeled simulation](runtime/private-three-integration/original-room-labeled-simulation.png)
- [Mobile room](runtime/private-three-integration/original-room-mobile.png)
- [Actual running dashboard](runtime/private-three-integration/actual-dashboard-original-room.png)
- [Six browser check results](runtime/private-three-integration/results.json)
- [Actual dashboard/data preservation](runtime/private-three-integration/actual-smoke-results.json)

Recorded radar, acoustic/SOS and mobile screenshots were opened and visually inspected. The original geometry is visible, source labels are readable, mobile indicators are stacked without overlap, and there are no reconstructed people in recorded mode.

## Modified files

- dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx
- dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx
- tests/test_private_three_integration.py (new)
- PRIVATE_3D_INTEGRATION_RESULTS.md (new)
- INTEGRATION_PLAN.md (follow-up documentation)

## Remaining limitations

Room/sensor placements remain illustrative. Real hardware count/positions/distances and synchronized raw sensor animation require validated sensor fields, coordinate calibration and acquisition timestamps; these are not invented. Recorded-file classifier scores are model outputs, not calibrated event probabilities or recognition accuracy. Explicit simulation can contain pre-existing synthetic distances and acoustic descriptions; these remain visibly simulated and are not hardware measurements. Only one private toilet zone is currently configured in the operational backend. No CCTV, speech recording, face/body reconstruction or additional live sensor acquisition was enabled. Original ZIP archives and the separate optional synthetic replay lab remain unchanged.
