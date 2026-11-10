# SafeSense Live AI Visualization ? Final Results

Tested 29 October 2026 on Windows 11, CPU-only, with real Chromium playback, actual backend/SQLite records and genuine YOLO/Fight inference. Final results: **19/19 main integration/browser checks PASS; 4/4 restart/regression checks PASS; 5/5 independent keypoint comparisons PASS. No remaining failing automated checks.**

## Confirmed bug fixed

Clicking an already selected, paused camera did not autoplay: React retained the video element, so its metadata/autoplay callback did not fire again. A real browser reproduced `paused: true` after the click ([before](runtime/live-ai-final/reselect-before.json)).

`CameraMonitoringPanel.open()` now explicitly resets/resumes the same video inside the click gesture, including when the existing analysis is still running. It preserves the inference deduplication guard. Browser retest: `paused: false`, two accepted cached requests, **one unique job** ([after](runtime/live-ai-final/reselect-after.json), [restart regression](runtime/live-ai-final/restarted/results.json)). No style, model, threshold or dataset changes were made.

## Requirement results

| Verification | Result | Actual evidence |
|---|---|---|
| All configured cameras autoplay real recordings | PASS | Entrance, Hall, Canteen, Staircase and Corridor A; all five tested cold and cached, muted autoplay and replay |
| Genuine cached pose results appear without CPU recomputation | PASS | All five memory-cache browser loads; all five disk-cache API loads after a real service restart; exact cached fall frame data equality |
| Person boxes and skeletons align to recording frames | PASS | Three seek samples per camera per cold/cached visit; SVG box coordinates equal payload; independent YOLO comparisons on every camera, including all 17 keypoints and their confidence values |
| Supported fall highlights the associated person red | PASS | Actual UR Fall fall-02, track 1; POSSIBLE FALL, binary ACTIVE; no invented fall score; red #ef4444; 33 supported red frames. Horizontal-only/ambiguous/missing tracks covered by safety unit tests |
| Fight banner has real score and model version | PASS | AIRTLab V3: 0.9848954677581787, red whole-video POSSIBLE FIGHT banner; explicitly uncalibrated classifier score. V2 actual backend output separately tested: 0.47800374031066895 |
| No fabricated fight-specific person boxes | PASS | Genuine person boxes stay cyan; no fighter labels/localized fighter geometry. Fight outputs contain neither person boxes nor invented event times |
| Camera switching is isolated and queue remains bounded | PASS | Rapid Entrance/Hall switching, correct camera ID, no stale overlay reuse; actual forced CPU jobs deduplicated, obsolete queued camera cancelled, running job completed safely and newest camera completed |
| Timeline and native seeking update annotations | PASS | Actual source timestamps; forward/backward sampled frames; actual fall timeline marker seeks to the supported 2.1-second event |
| Incident evidence has matching annotations/metadata | PASS | Strict incident-bound manifests match analysis ID, source SHA256 and camera; genuine retained clip byte ranges return 206; Audit Details plays matched fall/fight overlays; saved annotation variant available |
| Cold and cached latency measured separately | PASS | Tables below; browser video/overlay measurements, original CPU timing, independent restart API latency |
| Digital Twin, Incidents, Alerts, Reports and private 3D remain functional | PASS | Actual Alert Details opens evidence, Incident Review/audit works, private map opens healthy 578x458 WebGL canvas, simulation presence updates 3D indicator, zero private CCTV elements, real CSV and visual PDF exports |

The configured recordings are AIRTLab/UR Fall research recordings assigned to demo camera zones, not footage verified to originate from this school.

## Measured performance

Cold means no analysis-result cache for that camera in the isolated run. Entrance includes first model loading; later cold cameras reuse loaded models but compute a new analysis. Existing OS/video codec caches were not flushed. Each number is one observed run, not a latency guarantee. Tests ran on the shared Windows desktop; basic unit/build work and a cached browser reproduction overlapped parts of the run.

Browser video latency uses the first decoded `playing` frame callback. Overlay latency uses the first person-box DOM commit plus animation frame, from camera click; it is not a physical display measurement. CPU time is the backend's actual Fight V3 + Pose job duration. Pose FPS is pose prediction wall throughput, excluding the full export/delivery pipeline.

| Camera | Analyzed frames | Cold video start ms | Fresh backend CPU s | Cold first pose s | Pose prediction FPS |
|---|---:|---:|---:|---:|---:|
| School Entrance | 150 | 107.6 | 27.865 | 29.311 | 9.754 |
| School Hall | 180 | 84.9 | 15.593 | 16.382 | 13.85 |
| Canteen | 158 | 146.3 | 23.336 | 24.251 | 13.921 |
| Staircase | 110 | 77.9 | 14.742 | 15.959 | 9.965 |
| Corridor A | 165 | 197.1 | 30.085 | 32.296 | 11.385 |

| Camera | Cached video start ms | Cached first pose ms | Restart disk-cache API ms |
|---|---:|---:|---:|
| Corridor A | 149.1 | 1166.6 | 1109.15 |
| Canteen | 237.7 | 1414.1 | 583.94 |
| Staircase | 164 | 816.9 | 349.29 |
| School Entrance | 271.3 | 1045.7 | 499.8 |
| School Hall | 77.3 | 1078.6 | 459.12 |

Cached browser pose rendering ranged from **816.9?1414.1 ms**. These results are quick replay of genuine precomputed detections, not instant fresh CPU inference. Original analysis timings shown in the UI remain separate from cache-loading timings. The direct memory-cached fall API check returned in 131.89 ms; the restart table is from the final separate service-restart run.

Cold queue delay was 0.022?0.070 s. Maximum recorded Windows process-lifetime peak working set in the cold model profiles was **1552.3 MiB**; this is AI-process telemetry, not whole-machine RAM or memory attributable to a single inference. Per-stage preprocessing, R3D inference, YOLO inference and annotation timings are retained in [performance.json](runtime/live-ai-final/performance.json).

Restart disk-cache tests produced **zero new events and zero new incidents**. Forced fresh jobs used only to test queue cancellation ran against the isolated database; they were allowed to create genuine fresh evidence/incidents there.

## Tests run

| Suite | Actual result |
|---|---|
| Python/Chromium main integration: test_live_ai_visualization_final.py | 19 PASS, 0 FAIL |
| Python/Chromium service restart: test_live_ai_restart_final.py | 4 PASS, 0 FAIL |
| Independent real inference: test_pose_keypoint_integrity.py | 5 cameras PASS; boxes/XY within 0.001 source pixels, keypoint confidence within 0.000001 |
| Python backend regression runner | 65 PASS, 0 failures/errors; queue, durable cache, privacy, incident workflow, notification safety and Overview |
| Python per-track safety tests | 5 PASS |
| TypeScript unit tests | 21 PASS; overlay timestamps/confidence, camera contracts, report routes/filters, safe CSV, vector/print pagination/privacy |
| TypeScript compiler | PASS: npm --prefix dashboard run lint |
| Production build | PASS: npm --prefix dashboard run build |

Existing Vite native-config and large-chunk warnings remain non-fatal. No browser runtime errors were reported in the main run. Test services were stopped after verification; existing user services were not stopped or replaced. External notifications were disabled, and tests used isolated SQLite/media/cache directories.

Commands, from the repository root:

```powershell
.venv-vision/Scripts/python.exe tests/test_live_ai_visualization_final.py
.venv-vision/Scripts/python.exe tests/test_live_ai_restart_final.py
.venv-vision/Scripts/python.exe tests/test_pose_keypoint_integrity.py
.venv-vision/Scripts/python.exe tests/run_cpu_monitoring_checks.py
.venv-vision/Scripts/python.exe -m unittest tests.test_pose_tracking
node --import ./dashboard/node_modules/tsx/dist/loader.mjs --test tests/videoDetections.test.ts tests/cameraAnalysisContract.test.ts tests/analyticsReports.test.ts tests/filteredReportCsv.test.ts tests/visualReport.test.ts
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

The restart and independent-integrity tests intentionally run after the main suite and read only its isolated database/results. Raw results: [main](runtime/live-ai-final/results.json), [restart](runtime/live-ai-final/restarted/results.json), [keypoints](runtime/live-ai-final/keypoint-integrity.json), [queue cancellation](runtime/live-ai-final/queue-switch-results.json), [backend](runtime/cpu-visualization/backend-results.json).

## Inspected screenshots and exported files

Screenshots were opened and visually inspected, not merely generated.

- [Supported red fall overlay on actual UR Fall playback](runtime/live-ai-final/actual-fall-overlay.png)
- [AIRTLab whole-video fight banner with genuine cyan person boxes/skeletons](runtime/live-ai-final/actual-airtlab-fight.png)
- [Corresponding decoded fall incident evidence](runtime/live-ai-final/fall-audit-genuine-overlay.png)
- [Timeline marker seeking](runtime/live-ai-final/restarted/timeline-fall.png)
- [Rendered private sensor-only 3D scene](runtime/live-ai-final/restarted/private-3d-scene.png)
- [Mobile camera layout](runtime/live-ai-final/mobile-overlay.png)
- [Analytics & Reports dashboard](runtime/live-ai-final/analytics-reports.png)
- [Downloaded real report PDF](runtime/live-ai-final/operational-report.pdf): 4 A4 pages, all four rendered and inspected: [cover/KPIs/trend/donut](runtime/live-ai-final/report-page-1.png), [zone/severity/status charts](runtime/live-ai-final/report-page-2.png), [permitted evidence](runtime/live-ai-final/report-page-3.png), [incident table](runtime/live-ai-final/report-page-4.png). Values matched the 4 actual incident records in the test snapshot; no acknowledgement statistics were invented.
- [Downloaded CSV](runtime/live-ai-final/operational-incidents.csv): 4 actual incident rows, 14 supported columns.

![Actual decoded fall evidence with binary rule overlay](runtime/live-ai-final/fall-audit-genuine-overlay.png)

![Healthy private sensor-only 3D scene](runtime/live-ai-final/restarted/private-3d-scene.png)

## Remaining limitations and NOT TESTED

- Cold fresh CPU analysis takes approximately 14.7?30.1 seconds in this run. Video starts independently; cached replay avoids that work but is not zero-latency.
- Fall detection remains an experimental, binary posture-transition rule, not a calibrated trained fall classifier or confirmation of an injury. Recording-local IoU association resets on missing/ambiguous detections and can miss occluded/fast-moving subjects.
- Fight scores are classifier outputs, not established event probabilities or ground truth. V2 flagged a normal UR activity clip in the backend check; the UI faithfully reports it for review. No classifier weights, thresholds or datasets were altered to change the result.
- V3 visual rendering and V2 backend inference were exercised; a separately configured V2-default camera session was not tested. The shared banner renderer supports both versions.
- Physical live-camera hardware, physical private sensors, real emergency dispatch and external Telegram delivery: **NOT TESTED**. The private 3D presence action was explicitly labeled SIMULATION; it provided no CCTV imagery or fabricated occupant positions.
- Native OS print dialog: **NOT TESTED in this final pass**. Report download and CSV were exercised in Chromium; shared vector/print layout unit tests passed. No claim of a new native print-preview inspection is made.
- Existing global status-copy encoding artifacts are visible in some screenshots; this task preserved that global dashboard copy/style and changed only camera playback behavior.

## Modified files in this final pass

- dashboard/src/components/analysis/CameraMonitoringPanel.tsx ? same-camera click autoplay fix; inference and design preserved.
- tests/test_live_ai_visualization_final.py ? new all-camera real browser/integration and performance suite.
- tests/test_live_ai_restart_final.py ? new real restart-cache, repeated selection, timeline and cross-feature regressions.
- tests/test_pose_keypoint_integrity.py ? new independent genuine YOLO coordinate/confidence verification.
- LIVE_AI_VISUALIZATION_RESULTS.md ? this report.

Production build files under dashboard/dist and actual screenshots/PDF/CSV/test logs under runtime/live-ai-final were regenerated. Existing model checkpoints, training/evaluation datasets and original incident database were not modified.
