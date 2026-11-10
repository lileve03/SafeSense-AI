# Live Monitoring model-contract fix

Verified 29 October 2026 (Asia/Singapore). **Final result: PASS — 77 automated checks, TypeScript and production build.** A separate read-only check also verified the currently served port-3000 client.

## Confirmed root cause

The camera handler sent JSON **`model: "auto"`**. The running inference process on port 8001 was an older contract accepting **`all`, `v2`, `v3`, `pose`**. Its validation response was reproduced safely using an invalid model probe, which did not queue inference:

```json
{"detail":"Select all, v2, v3 or pose"}
```

The running OpenAPI schema also reported an older `JobIn` default of `v3` and lacked the newer client/selection fields. Local source had added `auto`, but the running process had not loaded that contract. The served client and inference process were therefore out of sync. This was a request-mode mismatch, not missing video files or failed model inference.

Evidence: [running-contract-before.json](runtime/camera-model-contract/running-contract-before.json).

## Implemented fix

- Every camera now submits **`model: "all"`**, using the existing JSON field **`model`**, not the separate upload endpoint's `model_version` form field. Registered camera IDs are passed unchanged.
- FastAPI's input schema declares exactly **`all`, `v2`, `v3`, `pose`**, with `all` as default. Unsupported `auto` still fails with HTTP 422: validation is not suppressed, aliased away or used to skip inference.
- For a registered camera, `all` runs its configured V2/V3 fight baseline plus YOLO11-Pose in one bounded job. The default fight baseline remains V3; camera/global V2 overrides remain supported. This runs one fight feature/classifier pipeline plus pose, rather than launching redundant R3D-18 work.
- Camera-less research/source comparison requests retain their existing `all` behavior: V2 + V3 + pose, with shared extracted features. Individual `v2`, `v3` and `pose` APIs remain supported.
- Response rendering supports both the older three-model `all` schema and the configured two-model schema. It derives labels from actual returned/resolved versions, handles missing policy fields, and displays failed detectors rather than silently omitting them. It never inserts invented scores or detections.
- The existing debounce, selection ownership, active-job coalescing, bounded completed-result cache, controlled retries and cancellation of obsolete waiting jobs remain in use. Running/unrelated work is not cancelled; capacity is unchanged.
- Playback remains independent of queue admission. Frame-synchronized actual YOLO annotations, pose metadata, recorded evidence, event provenance and incident/map synchronization are preserved. Dashboard styling and layout were not redesigned.

## Actual camera verification

Every configured camera was clicked in Chromium, sent one initial `all` request, autoplayed its actual registered source and completed genuine inference on isolated services. The test-only registry used a V2 override for Corridor A to verify configuration support; the default V3 path was also exercised by the retained regression.

| Camera | Fight baseline / actual score | Fight candidate | Fall candidate | Result |
| --- | --- | --- | --- | --- |
| Corridor A | V2 override / 0.9745275974 | Yes | No | **PASS** |
| Canteen | V3 / 0.0923522040 | No | No | **PASS** |
| Staircase | V3 / 0.5614077449 | No | Yes, pose frame 64 / 2.1 s | **PASS** |
| School Entrance | V3 / 0.1108175367 | No | No | **PASS** |
| School Hall | V3 / 0.0387568846 | No | No | **PASS** |

The default Corridor V3 score remains 0.9848954678 in the retained model/camera regression. Scores are actual uncalibrated classifier outputs; the pose rule has no fabricated fall probability. Full source hashes, model selections, timing and request values are recorded in [actual-model-results.json](runtime/camera-model-contract/actual-model-results.json).

Tests verify original source hashes, real boxes/17-keypoint skeletons against independent YOLO inference, annotated-video frame count/FPS, seek alignment, paused handoff at 1.2 s / 1.5×, actual captured clips and correct incident binding. Normal cases create no new incidents. Cache reuse returns the same job without new incident records. An 80 ms rapid-switch burst produces one final submission, returns the correct Hall source and causes zero JavaScript page exceptions.

## Executed tests

| Suite | Actual result | Evidence under `runtime/camera-model-contract/` |
| --- | --- | --- |
| HTTP contract + every real camera + cache/overlay/evidence/switching | **PASS 10/10** | `results.json`, `browser-tests.log` |
| Backend accepted-values, baseline and provenance policy | **PASS 8/8** | `policy-tests.log` |
| Client wire/schema compatibility, including partial failures | **PASS 6/6** | `client-contract-tests.log` |
| Retained model/overlay/evidence browser regression | **PASS 8/8** | `detection-regression.log` |
| Full real-monitoring/backend/dashboard integration | **PASS 21/21** | `integration-regression.log` |
| Queue concurrency/cache/idempotency/ownership | **PASS 9/9** | `queue-tests.log` |
| Incident response/security | **PASS 10/10** | `incident-tests.log` |
| Privacy adapters | **PASS 5/5** | `privacy-tests.log` |
| TypeScript (`npm run lint`) | **PASS, exit 0** | `typescript.log`, `build-results.json` |
| Production build (`npm run build`) | **PASS, exit 0** | `build.log`, `build-results.json` |

The full integration suite additionally invokes the retained 13-check upload/replay/SOS/report/mobile browser suite. It passed and is not counted again in the 77-check total. Existing Vite config-loader and bundle-size warnings remain warnings.

The normal-port client check independently confirmed **all five camera identities submit `all` and autoplay their actual sources**. That specific smoke test intercepted inference submissions with a controlled 503 response so existing incident records would not be changed; real completed inference is established by the isolated suites above. Its retries are backpressure retries, not additional executed inference jobs. See [running-client-contract.json](runtime/camera-model-contract/running-client-contract.json).

## Modified files

- `dashboard/src/components/analysis/CameraMonitoringPanel.tsx` — supported `all` request constant, unchanged camera IDs, compatibility-aware model/version label.
- `dashboard/src/components/analysis/DetectionResults.tsx` — render returned/resolved detector versions and partial failures across both response schemas.
- `dashboard/src/lib/cameraAnalysisContract.ts` — shared client contract constant and response-version normalization.
- `monitoring_ai.py` — explicit four-value schema, configured camera `all` execution, preserved research comparison mode and automatic-run provenance.
- `tests/test_automatic_monitoring.py`, `tests/test_automatic_camera_browser.py` — update expected wire contract and add exact accepted-value coverage.
- `tests/test_camera_model_contract_browser.py`, `tests/cameraAnalysisContract.test.ts` — new real-camera/HTTP and client-schema checks.
- `tests/test_detection_monitoring.py` — verify configured two-detector `all` output, genuine invalid-cache refresh and synchronization. Only the transient annotation created by this isolated test is expired; existing captured evidence is not removed.
- `tests/test_real_monitoring.py` — clarify the legacy source-comparison test label.
- `CAMERA_MODEL_CONTRACT_FIX.md` — this report; build outputs and runtime verification artifacts were regenerated.

No trained weights or datasets were changed. All three trained model artifacts match their saved hashes: [preserved-models.json](runtime/camera-model-contract/preserved-models.json).

## Running-service status

The served client now uses the running service's supported `all` value, so the unsupported-`auto` validation mismatch is removed without requiring an `auto` alias. Existing normal-port services were left running to avoid interrupting their work.

**Restart SafeSense through its existing launcher to load the updated backend's configured-baseline execution, schema and cache/priority implementation.** Until then, an older inference process may return its legacy three-model `all` result; the updated UI handles and displays those actual outputs. Tests did not claim that an already-running Python process automatically reloads edited source.

Physical live-camera connectivity and actual Telegram receipt were not tested. External notification delivery was disabled in integration tests.
