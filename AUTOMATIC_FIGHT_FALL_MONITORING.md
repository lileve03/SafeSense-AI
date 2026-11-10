# Automatic public-camera Fight + Fall monitoring

Verified 29 October 2026, Asia/Singapore. **PASS: 69 executed checks across the suites below; TypeScript and production build also pass.**

## Behavior

Clicking a public camera immediately plays its registered video and submits one `auto` job. The camera panel has no detection-type selector, model selector or Analyze button. Replay controls video playback only. Re-selecting a completed camera revalidates/reuses its result; selecting it again after a recoverable failure retries automatically through the same bounded admission path.

An automatic job runs **one configured fight classifier plus YOLO11-Pose**, sequentially in the existing single-worker CPU scheduler. The default fight baseline is **V3**. `SAFESENSE_FIGHT_BASELINE=v2` selects the existing V2 baseline globally; an existing camera-registry entry can override the global baseline with `fight_model: "v2"` or `fight_model: "v3"`. Selection never depends on the recording's ground-truth label. Invalid configuration fails explicitly rather than silently choosing a detector.

Both trained fight classifiers remain available through the existing individual/comparison APIs and research tools. Ordinary camera selection does not run both classifiers or launch redundant R3D-18 extraction. Existing feature caching, active-job coalescing, bounded completed-result caching, selection priority/cancellation and retry/backpressure remain in use. Worker/queue capacity was not increased.

Completed analysis displays Fight/Fall predictions, actual classifier scores, thresholds, versions, per-model latency and total original processing latency. It explicitly distinguishes **Fresh inference** from **Cached / reused completed analysis**. Feature-cache provenance remains available in analysis details. Fall has no fabricated probability: the UI displays N/A for the experimental posture rule, while genuine person/keypoint confidence is shown separately.

Actual YOLO boxes and skeletons come from the generated annotated recording and matching per-frame metadata. Fight classification remains whole-clip: no fighter-specific boxes, validated fight timestamps or tracking IDs are invented. Only actual pose-rule events populate the event timeline.

A completed result with neither candidate displays **Normal monitoring — no Fight or Fall candidate detected in this recording**. Missing/failed detectors display an incomplete state instead. Each automatic job supplies a distinct `analysis_run_id` to event ingestion, preventing a previous recording's fall in the same zone from creating an incident for a later normal recording. Triggering observations retain their actual model/version and captured evidence; the job stores its resolved policy and links to incident provenance.

## Actual recording results

The test-only operator registry selected V2 for Corridor A to verify its override, and V3 for the other cameras. The retained default-configuration regression also exercised automatic V3 + pose on Corridor A. These are recorded research videos assigned to demonstration zones, not live school CCTV.

| Camera / registered recording | Fight baseline | Actual fight score | Fight candidate | Pose fall candidate | Measured total processing |
| --- | --- | --- | --- | --- | --- |
| Corridor A / AIRTLab violent `cam1/97.mp4` | V2 override | 0.9745275974 | Yes | No | 14.551 s |
| Canteen / AIRTLab non-violent `cam1/1.mp4` | V3 | 0.0923522040 | No | No | 10.020 s |
| Staircase / UR Fall `fall-02-cam0-rgb.mp4` | V3 | 0.5614077449 | No | Yes, frame 64 / 2.1 s | 5.053 s |
| School Entrance / UR Fall `adl-01-cam0-rgb.mp4` | V3 | 0.1108175367 | No | No | 7.284 s |
| School Hall / UR Fall `adl-02-cam0-rgb.mp4` | V3 | 0.0387568846 | No | No | 6.843 s |

V2 threshold remains 0.4; V3 threshold remains 0.7. Timings include evidence work and vary with CPU load and feature reuse. These are actual uncalibrated model outputs, not a real-world accuracy or real-time performance claim. The normal cases created no incidents and left existing incident records unchanged. Default V3 conflict score remains 0.9848954678 in the retained model/automatic-camera regression.

Full scores, source hashes, candidate flags, timestamps and latency: [actual-model-results.json](runtime/automatic-monitoring/actual-model-results.json).

## Executed validation

| Suite | Result | Evidence |
| --- | --- | --- |
| Automatic policy/provenance | PASS 7/7 | `runtime/automatic-monitoring/policy-tests.log` |
| Actual automatic-camera browser/API | PASS 9/9 | `runtime/automatic-monitoring/results.json`, `browser-tests.log` |
| Retained real-model/overlay browser regression | PASS 8/8 | `runtime/automatic-monitoring/detection-regression.log`, `runtime/detection-task3/results.json` |
| Full real-monitoring integration | PASS 21/21 | `runtime/automatic-monitoring/integration-regression.log`, `runtime/real-monitoring-tests/results.json` |
| Queue concurrency/cache/ownership | PASS 9/9 | `runtime/automatic-monitoring/queue-tests.log` |
| Incident response/security | PASS 10/10 | `runtime/automatic-monitoring/incident-tests.log` |
| Privacy adapters | PASS 5/5 | `runtime/automatic-monitoring/privacy-tests.log` |
| TypeScript (`npm run lint`) | PASS, exit 0 | `runtime/automatic-monitoring/typescript.log` |
| Production build (`npm run build`) | PASS, exit 0 | `runtime/automatic-monitoring/build.log`, `build-results.json` |

The full integration suite also invokes the retained 13-check upload/pose/replay/SOS/report/filter/mobile browser suite; that nested suite passed and is not added again to the 69-check total.

Actual browser assertions verify one automatic submission per first camera selection, exactly one fight output plus pose, no manual camera controls, advancing muted playback, source hashes, correct fresh/cached labels, real candidates and no-incident negative cases. Independent YOLO inference on source frame 12 matches boxes and 17-keypoint coordinates within 0.001 pixels. A 2.3-second seek displays frame 69. The retained regression verifies paused handoff at 1.2 seconds / 1.5×, synchronized overlays, captured clips and private-video rejection.

Candidate evidence opens under the same incident in the existing modal, Alerts and Incident Review; Digital Twin zone state matches the backend incident. Rapid Entrance/Hall/corridor switching at 80 ms intervals produced only **one submission** for the final selection, used the valid cache, rendered responsively at 390 px and produced **zero JavaScript page errors**.

Model preservation: all three trained artifacts match their retained SHA-256 baselines. See [preserved-models.json](runtime/automatic-monitoring/preserved-models.json). No training, dataset change or weight replacement occurred.

## Modified files

- `monitoring_ai.py` — automatic execution plan, configuration-aware cache key, resolved-policy audit data and per-job provenance.
- `fight_api.py` — propagate automatic-run provenance during existing event delivery; inference algorithms unchanged.
- `backend/registry.py` — publish configured fight baseline for each public camera.
- `dashboard/src/components/analysis/CameraMonitoringPanel.tsx` — automatic submission, remove manual model/Analyze controls, show provenance/latency and normal/incomplete/candidate states.
- `dashboard/src/components/analysis/DetectionResults.tsx` — automatic two-detector presentation with actual versions and Fight/Fall labels.
- `.env.example` — document default/override baseline configuration.
- `tests/test_automatic_monitoring.py`, `tests/test_automatic_camera_browser.py` — new policy and actual-video/browser checks.
- `tests/test_detection_monitoring.py`, `tests/test_real_monitoring.py` — update retained camera expectations for automatic baseline + pose and absent manual controls.
- `tests/test_cpu_queue_browser.py` — align its queued-state wording with the camera panel; its full suite was not rerun in this task. The queue unit suite and new automatic switching checks were executed as listed above.
- `AUTOMATIC_FIGHT_FALL_MONITORING.md` — this report. Build outputs and runtime evidence were regenerated.

Other dashboard pages were not redesigned. Existing backend incident rules, SQLite schema, staff/SOS workflows and trained detection algorithms were preserved.

## Activation and limitations

**Restart SafeSense through the existing launcher to load the updated inference/registry code.** Verification used isolated services/databases with external Telegram delivery disabled. The running normal-port supervisor was not restarted, so unrelated active inference or incident processing was not interrupted.

Physical camera connectivity and continuous live-stream detection were not tested. Configured live cameras retain their existing bounded-sample behavior; they do not acquire validated continuous real-time or pre-trigger buffering through this change. Fall detection remains an experimental YOLO posture rule. Normal monitoring describes this recording's model output, not a guarantee that a scene is safe. Build passes with the existing Vite config-loader and bundle-size warnings.
