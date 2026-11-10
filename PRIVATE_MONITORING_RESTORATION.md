# Original 3D private monitoring restoration

## Latest verification — private-room follow-up

The ORIGINAL room remains active at http://127.0.0.1:3000 → Digital Twin Map → click the toilet/private-zone polygon. It was reused in place. Executed comparison against the archived original confirms identical 16 geometry constructions, 12 material constructions, the perspective camera and both original orbit defaults. Floor, walls, partition, radar illustration, SOS box, original geometric simulation mannequins and orbit/zoom/reset controls are retained.

The privacy follow-up removes located floor mannequins from presence-only backend readings: current recorded radar predictions contain class labels, not people counts or coordinates. An anonymous **presence signal · count and position unknown** overlay is used instead. People Count and Separation remain N/A; Relative Positions explicitly says unavailable. The original mannequins, illustrative positions and simulated counts/distances remain available only in the clearly labeled original local simulation. Room/sensor layout is described as illustrative, not a surveyed physical installation.

The new sensor-provenance panel identifies each radar/non-speech acoustic reading separately: SIMULATION, RECORDED SENSOR REPLAY, or model output with hardware unverified, plus its actual timestamp, model score where supplied and source evaluation row. Unrelated recorded sources are not represented as synchronized. Fall visualization follows the latest radar observation; unresolved historical incidents remain in the separate incident workflow. SOS stays connected to backend incident state. No camera, images, video, speech transcription or audio recording is introduced.

Executed on the normal dashboard: **14/14 private-view checks PASS**, TypeScript PASS and production build PASS. The browser recorded **zero camera/microphone requests** and **zero private media elements**; both fight/fall private upload endpoints returned 403. No JavaScript/WebGL errors were recorded. Actual sensor hardware remains unavailable and unverified. Results: `runtime/private-view-restoration/browser-results.json`. Screenshots: `original-private-page-restored.png`, `radar-acoustic-indicators.png`, `original-local-simulation.png` in that same folder. Reproduce with `.\.venv-vision\Scripts\python.exe tests\test_private_monitoring_restore.py`.

The sections below document the preceding restoration and its historical checks; the current presence-only behavior above supersedes the earlier illustrative backend mannequin placement.

## Cause and recovery

The original scene was **hidden, not deleted**. The recent integration added an `if (isLiveMode) return ...` branch in `PrivateAreaMonitoringView.tsx`, returning a sensor panel before the original three-column page could mount. Backend Events is the default mode, so its users never reached the Three.js room. The existing DigitalTwinPage route and original component were still present.

The project root and checked source folders have no Git repository, so commit history is unavailable. The existing project ZIP contains both original private-monitoring components. Before restoration, `PrivateAreaDigitalTwin3D.tsx` was byte-for-byte identical to the archived original (SHA256 `e062cf1fb2e609c2e53235e8fb0a070452e4250b09a0c64729fbe19bd05693b8`). Both components were reused in place; no generic replacement was introduced. Current pre-change sources and archived originals were backed up under `runtime/private-view-restoration/before` and `archive`.

The original uses plain Three.js procedural meshes, not React Three Fiber or external GLB/GLTF models. No original 3D assets are missing. Floor, grid, semi-transparent walls, entrance privacy partition, SOS wall box, ceiling radar, coverage cone/wave, geometric mannequins and original toolbar are retained.

## Changes (six existing source files)

- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx`: removed the backend-mode bypass; restored the original full page in both modes; connected radar/acoustic/SOS indicators and original acknowledgement to backend state; retained original panels, scene, seven local scenarios and SOS confirmation. Added the existing sensor replay controls below the room, scoped to the selected private zone. Public-zone selection returns to the school map. No simulated fallback is used on backend failure.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx`: reused the original geometry/materials/camera and orbit controls. Added metadata-driven presence visibility, acoustic/SOS indicators and SOS box emissive highlighting. Applied the original risk lighting after initialization, added resize observation and disposed scene resources on navigation. Unknown coordinates/counts remain unavailable; backend markers use illustrative positions. Removed misleading live-camera/confirmed-injury labels.
- `dashboard/src/components/map/SchoolDigitalTwinMap.tsx`: a private-room click (or existing Enter-key action) opens its original dedicated 3D view. Public room selection retains the existing map behavior.
- `dashboard/src/context/SafeSenseContext.tsx`: exposes typed read-only sensor observation data to the private view. Supports an optional scenario zone override so all seven original private-room controls affect the currently selected private zone; existing school-wide calls keep their original defaults.
- `dashboard/src/types/safesense.ts`: adds the metadata-only SensorObservation type.
- `dashboard/src/components/analysis/SensorEventPanel.tsx`: optional private-zone scope and non-modal updates for embedding in the original view. Private-only controls include labeled presence, normal/rapid motion, fall and acoustic simulations. Existing public-page behavior remains the default.

Added `tests/test_private_monitoring_restore.py` and this report. Runtime artifacts contain backups, original-source comparisons, executed results and screenshots. No backend, inference-service, trained model, dataset, unrelated page, sidebar design or evaluation source was edited for this restoration.

## Match to the original experience

Source comparisons verify identical **16 geometry constructions**, **12 material constructions**, **perspective-camera construction**, and **default/reset orbit settings** (theta 0.6, phi 0.45, radius 12). The original room layout, colors/materials, camera perspective, lighting palette, mannequin designs and existing camera toolbar remain. The full original three-column page and local simulation controls are reused.

Small intentional differences are status accuracy and integration: Backend Events mode now renders the room; no measured positions or person counts are invented; possible-fall labels require review; acoustic/SOS metadata is visible in the scene; hardware unavailability and replay/simulation provenance are explicit. This is a sensor digital twin, never private-area CCTV or identifiable imagery. No image/video/audio capture is started by opening the room.

## Access

Open http://127.0.0.1:3000 ? **Digital Twin Map** ? click **Blind Spot Zone**. The original room opens directly. The existing **Private Area 3D View** tab also works. **Full School 2.5D Map** returns to the map, and choosing a public zone in the room's zone list returns to that zone's map.

In Backend Events mode use the embedded scoped controls to simulate presence/motion/fall/acoustic events, replay a saved radar/acoustic prediction, or run a test SOS. They update backend records and the original scene without replacing it. **Use original local simulation** enables all seven retained scenario controls. No hardware connectivity or sensor coordinates are claimed.

## Executed verification

Final detailed results are linked below. Hardware was unavailable; radar/acoustic checks use explicitly labeled simulation and recorded prediction replay. Browser tests add labeled test events to the existing demo session without resetting its history.

| Check | Result | Actual evidence |
|---|---|---|
| Private map click restores original 3D page in default mode | PASS | Default Backend Events mode now opens original three-column 3D private room directly from private map zone |
| Original Three.js scene renders a real healthy WebGL canvas | PASS | {"width": 628, "height": 458, "webgl2": true, "lost": false, "canvasCount": 1} |
| Original camera orbit, zoom and reset interactions | PASS | Drag orbit, zoom in/out and original reset controls change rendered pixels without losing WebGL context |
| Labeled backend radar presence updates abstract 3D marker | PASS | {"mode": "simulation", "event": "presence", "positions_and_counts": "explicitly unavailable; illustrative glyph only"} |
| Labeled radar motion updates original telemetry panel | PASS | {"event": "rapid_motion", "mode": "simulation"} |
| Fall pose and non-speech acoustic indicators reconnect to backend fusion | PASS | {"fall_overlay": "possible candidate, not confirmed", "acoustic": "scream", "backend_risk": "HIGH"} |
| Recorded radar replay remains in original 3D view and labels provenance | PASS | {"mode": "recorded_sensor_replay", "score": 0.99329, "evidence": "evaluation\\outputs\\radar_route_a\\radar_predictions.csv:row=0"} |
| Original SOS control records backend incident and highlights 3D indicator | PASS | {"incident": "dc385cb1-7318-40d9-a13e-30de7bdbc579", "mode": "simulation", "risk": "CRITICAL"} |
| Original incident acknowledgement uses confirmed FastAPI state | PASS | {"incident": "dc385cb1-7318-40d9-a13e-30de7bdbc579", "status": "ACKNOWLEDGED", "timestamp": "2026-10-28T08:28:44.272744+00:00"} |
| Original room navigation and scene lifecycle | PASS | School map, private tab, public-zone switch and private re-entry all work; canvas remounts once |
| Private page contains no visual feed and fight/fall uploads stay prohibited | PASS | {"video_endpoints": {"fight": 403, "fall": 403}, "private_page_media_elements": 0, "zone_controls": "private scoped"} |
| Original local simulation and scenario controls preserved | PASS | All seven original scenarios run in the selected private zone; original room, mannequin fall pose and reset are preserved |
| No critical browser or WebGL console errors | PASS | {"page_errors": [], "console_errors": []} |
| Existing dashboard browser suite | PASS: 13/13 | Real V3 upload, actual YOLO fall/H.264 playback, incident acknowledgement, map synchronization, SOS, replay, source/status filters, metrics, CSV export, mobile layout and JavaScript error checks |
| Existing API/inference suite | PASS: 36/36 | Actual V2 score 0.9745275974273682; V3 score 0.9848954677581787, both matching saved research outputs; actual fall annotation and privacy/error regressions passed |
| TypeScript | PASS | npm.cmd --prefix dashboard run lint; tsc --noEmit returned exit 0 |
| Production build | PASS | npm.cmd --prefix dashboard run build; Vite transformed 2261 modules and generated dist; exit 0 |
| Original design source comparison | PASS | 16 geometry blocks, 12 materials, camera construction and both default/reset orbit definitions match archive |

Build retains the pre-existing advisory warnings about __dirname and bundle size. Initial TypeScript checking exposed a missing level field in the new SensorObservation type; it was added and checking reran successfully. Initial browser selectors hit the animated map alert bounding box instead of the actual room polygon, and the original scenario incident modal blocked subsequent clicks. Tests now click the real room polygon and close the original modal between scenarios. These final results were rerun successfully; unexecuted checks are not counted as passes.

Physical mmWave hardware and live acoustic capture: **NOT RUN / unavailable**. The restored room does not open a camera or microphone, record speech, or substitute guessed live sensor positions. Real-model API checks use actual authorized public research videos on isolated ports; the private room checks use labeled metadata-only simulation/replay.

Evidence: [private browser results](runtime/private-view-restoration/browser-results.json), [original source checks](runtime/private-view-restoration/original-design-checks.json), [archive and backup hashes](runtime/private-view-restoration/recovery-evidence.json), [existing browser results](runtime/test-results/browser-results.json), [API results](runtime/test-results/results.json).

Screenshots: [restored original room](runtime/private-view-restoration/original-room-restored.png), [full restored page](runtime/private-view-restoration/original-private-page-restored.png), [radar/acoustic indicators](runtime/private-view-restoration/radar-acoustic-indicators.png), [original local simulation](runtime/private-view-restoration/original-local-simulation.png).

Reproduce (with the existing demo services running):

```powershell
.\.venv-vision\Scripts\python.exe tests\test_private_monitoring_restore.py
.\.venv-vision\Scripts\python.exe tests\test_browser_demo.py
.\.venv-vision\Scripts\python.exe tests\test_integration_demo.py
npm.cmd --prefix dashboard run lint
npm.cmd --prefix dashboard run build
```
