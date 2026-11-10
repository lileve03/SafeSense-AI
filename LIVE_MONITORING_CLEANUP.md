# Live Monitoring interface cleanup

Verified 29 October 2026 (Asia/Singapore).

Live Monitoring now contains **Campus Camera Feeds / automatic Fight + Fall monitoring** and **Recent Events**. Scenario Testing Library, Upload & Sensor Tools, Public-area Video Analysis and Sensor Replay & SOS Demo are removed from its component tree, together with the duplicate saved-prediction/controlled-test controls previously embedded in the camera panel. Their blank wrappers are removed rather than hidden.

Camera selection, automatic playback/inference, actual overlays, detection results, event timeline, incident evidence and the existing theme remain in place. Main monitoring no longer fetches the research scenario/replay catalogs.

## Retained tools and SOS access

Developer/research tools are available at **`http://127.0.0.1:3000/#/developer/testing`** (use your dashboard's port if different). The route contains the original Scenario Testing Library, manual public-video analysis, sensor replay/SOS demonstrations and saved-prediction/controlled-test entries, including the existing Telegram TEST entry. No new operator-sidebar item was added.

Direct loading, refresh, browser back/forward, sidebar exit and the “Return to Live Monitoring” button work. Returning through browser history restores the previous operator page.

Operational SOS remains in **Digital Twin Map → private zone → original 3D Private Monitoring → ACTIVATE SOS EMERGENCY**. Its existing prototype authorization confirmation and backend behavior are preserved. No backend endpoint, dataset, trained model, replay utility, research output or original scenario script was deleted.

## Actual verification

| Check | Result | Evidence |
| --- | --- | --- |
| Focused cleanup/navigation browser suite | **PASS 6/6** | `runtime/monitoring-cleanup/results.json`, `browser-tests.log` |
| Retained full real-monitoring integration | **PASS 21/21** | `runtime/monitoring-cleanup/integration-regression.log` |
| Nested upload/replay/SOS/report/mobile browser suite | **PASS 13/13** | `runtime/real-monitoring-tests/legacy-browser-output.txt`; nested within the integration suite, not an additional top-level count |
| TypeScript (`npm run lint`) | **PASS, exit 0** | `runtime/monitoring-cleanup/typescript.log`, `build-results.json` |
| Production build (`npm run build`) | **PASS, exit 0** | `runtime/monitoring-cleanup/build.log`, `build-results.json` |
| Preservation hashes | **PASS** | Eleven protected operational/backend files and three trained model artifacts match their saved hashes. `runtime/monitoring-cleanup/preserved-after.json`, `preserved-models.json` |

Browser checks confirm:

- Main monitoring has exactly the camera panel and Recent Events as its two direct sections, with zero leftover bottom gap or testing wrappers. Requested headings/buttons and file upload controls are absent from the main page; research catalog requests are absent there too.
- An actual Canteen recording autoplays and completes automatic V3 + YOLO11-Pose analysis. Real detections, normal-result state, timeline section and evidence section remain available. A normal recording correctly has no invented timeline events or captured incident clips.
- Developer tools render their actual scenario/replay catalogs. A saved radar prediction successfully replays against an isolated backend and opens its incident. No Telegram message was sent.
- All nine existing sidebar entries render. Digital Twin opens the original private WebGL canvas, with zero private video/audio/image elements. The operational SOS confirmation opens and can be cancelled without a broadcast.
- Desktop/mobile rendering passes, and no JavaScript page exceptions occur. Desktop screenshots were visually reviewed.

Tests used isolated services and a separate copy of SQLite; existing normal-port services were not restarted. The focused suite tested SOS access/confirmation without broadcasting. The retained integration suite additionally exercised actual prototype SOS generation, persistence, acknowledgement and map synchronization, with external delivery disabled. Initial focused-test assertions were corrected to wait for asynchronous catalog loading and to check the visible timeline section rather than an intentionally empty event container; final results above all pass.

The build retains its existing Vite config-loader and bundle-size warnings. No physical hardware or actual Telegram receipt is claimed by these UI tests.

## Modified files

| Application file | Change |
| --- | --- |
| `dashboard/src/pages/LiveMonitoringPage.tsx` | Remove testing/upload/sensor panel mounts and empty wrappers. |
| `dashboard/src/components/analysis/CameraMonitoringPanel.tsx` | Remove embedded saved-prediction/test controls and their unused catalog fetch/handler; preserve camera inference/playback. |
| `dashboard/src/pages/DeveloperTestingPage.tsx` | New separate page retaining development, research and legacy controlled-test interfaces. |
| `dashboard/src/App.tsx` | Render the developer page separately from operator pages. |
| `dashboard/src/context/SafeSenseContext.tsx` | Add developer hash-route navigation and previous-operator-page history handling. |
| `dashboard/src/types/safesense.ts` | Add the developer page identifier. |

Test files: new `tests/test_monitoring_cleanup_browser.py`; updated developer-route navigation in `tests/test_browser_demo.py`, `tests/test_detection_monitoring.py` and `tests/test_scenario_library.py`. The full detection/scenario suites were not separately rerun for this layout-only task; the executed focused and full integration suites are listed above.

This report, production build outputs and runtime verification artifacts were generated. No backend source, model weights, datasets or research results were changed.
