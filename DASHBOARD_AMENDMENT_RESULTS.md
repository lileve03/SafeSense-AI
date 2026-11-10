# SafeSense AI Dashboard amendment integration results

Tested: **29 October 2026, Asia/Singapore**. Final result: **PASS for the tested local dashboard workflows after one confirmed backend fix. No outstanding confirmed failures.** Hardware, external delivery and native print-dialog limitations are listed below rather than counted as passes.

Actual Chromium browser tests, local HTTP services, real model inference, SQLite restart tests, TypeScript and production build were executed. Tests used separate databases or read-only copies of the existing 28-incident database. External Telegram transport was disabled; notification transport unit tests used mocks. No project redesign, model training or source replacement was performed. Test services were stopped afterward; these results do not claim a production deployment or continuously running services.

## Requested workflows

| # | Workflow | Final status | Actual verification |
| --- | --- | --- | --- |
| 1 | Overview appearance and duplicate insights | **PASS after fix** | Browser reproduced duplicate Staircase text. Overview grouping now recognizes the same recorded candidates when an additional negative `normal_motion` observation has no retained clip. Fresh browser rerun passes; layout classes and protected Overview source hash remain unchanged. Incident records are untouched. |
| 2 | Alerts & Notifications preserved | **PASS** | Original Alerts and incident-list source hashes match their protected baselines. Browser compares Alerts content, operates the source filter, and exercises acknowledgement/resolution. Notification routing, recipient restrictions and lifecycle tests pass. Actual Telegram receipt is NOT TESTED. |
| 3 | Every configured camera has the correct playable recording or honest unavailable state | **PASS** | All five configured recordings decode and play in Chromium; requested source URLs match each registry entry. Independent file probing records paths, hashes, dimensions and frame counts. Missing-camera metadata fixture displays “No recording configured.” and removes the player. Expired evidence returns an explicit unavailable state. |
| 4 | Video starts without clicking Play | **PASS** | All five camera cards reach ready state with muted playback and advancing current time. Playback advances while CPU inference runs. Pause, seek, replay and rapid switching pass. |
| 5 | V2/V3 and YOLO11-Pose show actual results | **PASS** | Actual V2 conflict score **0.9745275974273682**, threshold **0.4**; V3 **0.9848954677581787**, threshold **0.7**. Normal V3 score **0.09235220402479172** remains a negative. Real pose inference emits boxes and 17 keypoints per person. Legacy HTTP inference agrees with saved research scores; cache reuse is disclosed. Outputs are not forced to match scenario labels. |
| 6 | Boxes and skeletons synchronize with video | **PASS** | Independent YOLO prediction on source frame 12 matches API boxes/keypoints within 0.001 pixels and confidence within 0.000001. Annotated video has **165 frames at 30 FPS**. Browser seeks at 0.6, 2.3 and 4.1 seconds show the expected frame within one decoded frame. Pause/handoff preserves time and playback rate. Fall marker corresponds to frame **64**, time **2.1 s**. |
| 7 | Live Monitoring lower section | **PASS** | Browser verifies responsive 390px layout without horizontal overflow, Scenario Library visibility, collapsed upload/sensor tools, retained upload/SOS controls and absence of the former simulated coordinate diagram. Desktop screenshot visually reviewed. |
| 8 | Incident Audit Details captured evidence | **PASS** | Ten API/browser checks pass: actual historical and fresh Fight/Fall evidence, incident/analysis binding, scores, genuine annotated/original toggle, autoplay, seek/replay, downloads, service-restart persistence and deleted-media handling. Missing evidence never substitutes an unrelated dataset recording. |
| 9 | Private-area imagery prohibited | **PASS** | Fight/fall uploads, monitoring jobs and private video ingestion reject prohibited inputs. Private 3D view contains zero video/audio/image elements and makes zero camera/microphone capture requests. Audit and exports retain sensor metadata while excluding private media references. Raw private acoustic streaming is rejected. |
| 10 | Analytics evaluation section removed | **PASS** | Seven browser checks pass against 28 SQLite records, including absence of the research panel, eight charts, filters, date/empty/error/stale states and mobile layout. Saved evaluations remain available separately under Reports → Model evaluation. |
| 11 | Download PDF | **PASS** | Actual button download opened with PDF parsers and rendered for visual review. [Verified PDF](runtime/dashboard-amendments/verified-report.pdf): **21,741 bytes, two A4 pages**, extractable report text, all four sections, no screenshot-only pages. Long-response pagination also passes with an 11-page fixture. |
| 12 | Print PDF | **PASS for print invocation and rendered print view; native dialog NOT TESTED** | Browser print invocation verified. [Print preview PDF](runtime/dashboard-amendments/verified-print-preview.pdf): **52,348 bytes, two A4 pages**; opened, rendered and visually reviewed. All sections included, table headers repeat, cells wrap, dashboard navigation/buttons are absent. Native OS print preview is unavailable in headless Chromium. |
| 13 | Download CSV | **PASS** | [Verified CSV](runtime/dashboard-amendments/verified-report.csv): **528 bytes**, UTF-8 BOM, **17 columns**, one selected backend incident. Parsed values match incident ID, zone, status, event types and provenance. Date/status scope, escaping, formula-prefix protection and private-reference exclusion pass. PDF, print and CSV identify the same selected incident. |
| 14 | Digital Twin, original private 3D, SQLite, SOS, Telegram restrictions, Scenario Library | **PASS for local/prototype functions** | Original private view passes **14/14** browser checks including archived geometry/material/orbit preservation, real WebGL, orbit/zoom/reset, sensor replay, SOS and acknowledgement. Digital Twin tracks incident lifecycle. SQLite and scenario histories survive actual process restarts. Scenario Library passes **20/20** checks including all **12 fresh inputs**. Telegram safety **13/13**, response/security **10/10**; all delivery transport mocked or disabled. Physical devices and Telegram receipt are NOT TESTED. |
| 15 | Current routes and APIs | **PASS for exercised routes and API contracts** | All nine dashboard pages render without JavaScript exceptions. All **16 non-parameterized GET routes** enumerated from both OpenAPI schemas return HTTP 200 with authentication. Parameterized job/source/evidence/report APIs and mutation/security workflows are exercised by the browser, audit and 36-check legacy API suites. This is not an exhaustive test of every possible API input. |

## Executed suites

These counts describe executed checks and intentionally overlap in workflow coverage; the legacy browser suite is invoked within the real-monitoring integration suite.

| Suite | Final outcome | Evidence |
| --- | --- | --- |
| `test_camera_playback.py` | PASS 7/7 | `runtime/camera-playback-task2/results.json` |
| `test_detection_monitoring.py` | PASS 8/8 | `runtime/detection-task3/results.json` |
| `test_audit_evidence.py` | PASS 10/10 | `runtime/audit-evidence-task4/results.json` |
| `test_real_monitoring.py` | PASS 21/21 | `runtime/real-monitoring-tests/results.json` |
| Nested `test_browser_demo.py` | PASS 13/13 | `runtime/test-results/browser-results.json` |
| `test_scenario_library.py` | PASS 20/20 | `runtime/scenario-library-tests/results.json` |
| `test_analytics_browser.py` | PASS 7/7 | `runtime/analytics-task5/results.json` |
| `test_reports_exports.py` | PASS 7/7 | `runtime/reports-task6/results.json` |
| `test_overview_duplicates_browser.py` | Initial FAIL; final PASS | `runtime/dashboard-amendments/overview-initial-failure.log`; final `test_overview_duplicates_browser.py.log` |
| `test_camera_unavailable.py` | PASS | `runtime/dashboard-amendments/test_camera_unavailable.py.log` |
| `test_private_monitoring_restore.py` | PASS 14/14 | `runtime/private-view-restoration/browser-results.json` |
| Retained temporal/sensor/evaluation/privacy unit suites | PASS 16/16 | `runtime/test-results/unit-results.json` |
| Telegram safety | PASS 13/13 | `runtime/dashboard-amendments/backend-unit-safety.log` |
| Incident response/security | PASS 10/10 | `runtime/dashboard-amendments/backend-response.log` |
| Overview grouping regression | PASS 13/13 | `runtime/dashboard-amendments/overview-unit.log` |
| Legacy model/API integration | PASS 36/36 | `runtime/test-results/results.json`; `runtime/dashboard-amendments/legacy-api.log` |
| Analytics calculation tests | PASS 10/10 | `runtime/dashboard-amendments/analytics-unit.log` |
| `npm run lint` / `tsc --noEmit` | PASS, exit 0 | `runtime/dashboard-amendments/typescript.log` |
| `npm run build` | PASS, exit 0 | `runtime/dashboard-amendments/build.log` |

## Verified camera sources

All are **recorded research videos assigned to demonstration zones**, not live school CCTV. All five independently decode and pass actual browser autoplay, pause, seek and replay. AIRTLab paths below are relative to `datasets/open_hidden/fighting/raw/AIRTLab/A-Dataset-for-Automatic-Violence-Detection-in-Videos-master/violence-detection-dataset/`.

| Camera | Exact recording | Resolution | Frames / FPS | Duration | Result |
| --- | --- | --- | --- | --- | --- |
| `CAM_CORRIDOR_A` | AIRTLab `violent/cam1/97.mp4` | 1920×1080 | 165 / 30 | 5.500 s | PASS |
| `CAM_CANTEEN` | AIRTLab `non-violent/cam1/1.mp4` | 1920×1080 | 158 / 30 | 5.267 s | PASS |
| `CAM_STAIRCASE` | `datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4` | 640×480 | 110 / 30 | 3.667 s | PASS |
| `CAM_ENTRANCE` | `datasets/open_hidden/test_videos/adl-01-cam0-rgb.mp4` | 640×480 | 150 / 30 | 5.000 s | PASS |
| `CAM_HALL` | `datasets/open_hidden/test_videos/adl-02-cam0-rgb.mp4` | 640×480 | 180 / 30 | 6.000 s | PASS |

Full source paths, SHA-256 hashes, byte sizes and decode results: [camera-file-verification.json](runtime/dashboard-amendments/camera-file-verification.json). Returned registry: [verified-camera-registry.json](runtime/dashboard-amendments/verified-camera-registry.json).

## Confirmed issue, fix and modified files

**Initial confirmed failure:** the current database produced duplicate Overview summaries for repeated Staircase analysis. The newer record included an extra negative `normal_motion` observation without retained media. The existing identity function rejected the entire record as ungroupable, so the repeated candidates were displayed again.

**Fix:** ignore that extra negative observation for Overview identity only when its valid recording hash and camera match retained candidates. Missing candidate provenance and unrelated recordings still remain distinct. No incidents are deleted or merged in storage. A regression test checks this case and rejects grouping when the negative observation belongs to another input. The actual Overview/Alerts browser test was rerun successfully after the fix.

Modified/created during this integration:

- `backend/overview_insights.py` — the only changed application source file; targeted grouping fix.
- `tests/test_overview_insights.py` — regression for an additional negative observation and mismatched input.
- `tests/test_browser_demo.py` — replaced the obsolete `Export CSV`/old-column assertion with `Download CSV`, actual selected scope and backend record comparisons. The updated 13-check browser suite passes.
- `tests/run_dashboard_amendments.py` — runs retained suites sequentially and records exit codes/logs.
- `tests/run_dashboard_interface_checks.py` — isolated normal-port services, Overview/Alerts/private-view checks, API smoke and camera-registry capture.
- `DASHBOARD_AMENDMENT_RESULTS.md` — this report.
- Generated production build outputs and verification artifacts/logs under `dashboard/dist` and `runtime`.

The application source snapshot confirms **51 other backend/dashboard source files unchanged**, including Overview, Alerts, Live Monitoring, Analytics, Reports and the original 3D view. Scenario tests additionally verify **19 source/model/research artifacts unchanged**. See `runtime/dashboard-amendments/source-changes.json` and `runtime/scenario-library-tests/preserved-artifacts.json`.

## Remaining limitations and NOT TESTED

- **NOT TESTED:** physical RTSP/HTTP cameras, radar/acoustic/SOS devices, continuous live-stream inference, physical sensor synchronization and any real emergency dispatch. Current successful camera tests use registered recordings.
- **NOT TESTED:** actual Telegram delivery or receipt. Tests prove local routing/restrictions with mocked transport, not external message delivery. No staff/test chat messages were sent during this integration.
- **NOT TESTED:** native OS print dialog, physical printer output, non-Chromium browsers and cross-platform behavior. Print invocation and actual Chromium A4 print rendering were tested.
- Scores are uncalibrated model outputs. A correct display is not proof of correct real-world classification; false positives remain possible, including conflict candidates on daily-activity/fall recordings. V2/V3 do not identify fighters or validated event timestamps. YOLO boxes/keypoints are person detections; the temporal fall rule is experimental and tracking IDs are unavailable.
- Cached feature reuse is labeled and tested; not every analysis repeats every neural feature extraction. Independent YOLO comparison and cold legacy V2 inference were executed.
- Build passes with Vite warnings about `__dirname`/future config-loader compatibility and large bundles. No unrelated bundling redesign was performed.
- Production identity roles, TLS, encrypted storage, retention operations at scale, load testing and exhaustive arbitrary API inputs are outside this verification.

Machine-readable suite outcomes: [suite-results.json](runtime/dashboard-amendments/suite-results.json), [interface-results.json](runtime/dashboard-amendments/interface-results.json), [api-smoke.json](runtime/dashboard-amendments/api-smoke.json). Actual export hashes: [verified-export-files.json](runtime/dashboard-amendments/verified-export-files.json).
