# Executed test results — 2026-10-28 (Asia/Singapore)

Final results: **36/36 API/inference, 13/13 browser, 14/14 preserved HTTP smoke, 16/16 unit tests passed**. TypeScript, production build, Python imports and compile checks passed. These counts exclude unexecuted hardware checks.

Actual machine-readable evidence: [API](runtime/test-results/results.json), [browser](runtime/test-results/browser-results.json), [unit tests](runtime/test-results/unit-results.json), [existing smoke script](runtime/test-results/legacy-api-results.csv). Screenshots and server logs are in the same directory. No predictions were mocked in real-video or browser workflows.

## Real inference measurements

| Check | Observed output |
|---|---|
| V2 real MP4 HTTP inference and saved research score equivalence | Score 0.9745275974273682; saved reference 0.9745276; 6.123s; feature cache hit=False |
| V3 real MP4 HTTP inference and saved research score equivalence | Score 0.9848954677581787; saved reference 0.98489547; 0.009s; feature cache hit=True |
| YOLO11-Pose temporal rule | 3.667s input, 110.0 annotated frames, candidate at 2.1s, 4.006s processing, 1291599 bytes, h264_browser |

Fight test input: existing AIRTLab violent/cam1/97.mp4 from the reserved-comparison manifest. Score differences are below 1e-5. V2 includes feature extraction/model initialization; V3 reused those features. The cached V3 latency is not standalone R3D inference latency. Fall input: datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4. Browser verified actual advancing H.264 playback, not just a video element.

## API / inference checks

| Test | Status | Actual output / error |
|---|---|---|
| Python imports | PASS | {"backend": "SafeSense AI Zone-Aware Prototype", "inference": "SafeSense offline AI inference"} |
| Backend health | PASS | {"http": 200, "body": {"status": "online", "mode": "EXPLICIT_PROCESSING_MODES", "time": "2026-10-28T07:53:12.644999+00:00", "version": "2.0.0", "note": "Prototype only; no real emergency dispatch"}} |
| Inference health and real model files | PASS | {"http": 200, "body": {"status": "ok", "device": "cpu", "processing_mode": "real_model", "scope": "offline public-area analysis", "models": [{"version": "v2", "threshold": 0.4, "available": true, "score_type": "uncalibrated classifier score", "feature_dimension": 1536}, {"version": "v3", "threshold": 0.7, "available": true, "score_type": "uncalibrated classifier score", "feature_dimension": 1536}], "fall": {"weights_available": true, "status": "e … (full output in JSON) |
| Missing access authorization rejected | PASS | {"http": 401, "body": {"detail": "Missing or invalid local demo access token"}} |
| Unconfirmed recording authorization rejected | PASS | {"http": 403, "body": {"detail": "Confirm that you are authorized to analyze this public-area video"}} |
| Private zone cannot be overridden by zone_type | PASS | {"http": 403, "body": {"detail": "Video is prohibited in private areas"}} |
| Private fall upload rejected before pose processing | PASS | {"http": 403, "body": {"detail": "Video is prohibited in private areas"}} |
| Unknown model selection rejected | PASS | {"http": 400, "body": {"detail": "Select model v2 or v3"}} |
| Original inference import compatibility | PASS | {"same_app": true} |
| Unknown registered zone rejected | PASS | {"http": 422, "body": {"detail": "Unknown zone; select a registered public zone"}} |
| Invalid extension rejected | PASS | {"http": 400, "body": {"detail": "Supported formats: MP4, AVI, MPG, MPEG"}} |
| Invalid video bytes rejected | PASS | {"http": 422, "body": {"detail": "Cannot decode this video"}} |
| Empty video rejected | PASS | {"http": 422, "body": {"detail": "Video is empty"}} |
| Actual 100 MB upload limit | PASS | {"http": 413, "body": {"detail": "Upload exceeds 100 MB"}} |
| Missing classifier handling | PASS | {"http": 503, "body": {"detail": "v3 classifier unavailable"}} |
| Concurrent inference rejected | PASS | {"http": 429, "body": {"detail": "AI service busy; retry when current analysis finishes"}} |
| Private vision event rejected | PASS | {"http": 422, "body": {"detail": "vision source is prohibited in PRIVATE area"}} |
| Private simulated vision modality rejected | PASS | {"http": 422, "body": {"detail": "Vision modality is prohibited in PRIVATE areas, including simulation"}} |
| Untrusted real-model provenance rejected | PASS | {"http": 401, "body": {"detail": "Trusted inference token required for real-model events"}} |
| Independent permitted signals fuse and cooldown deduplicates | PASS | {"single": "OBSERVE", "fused": "HIGH", "incident_count": 1} |
| Correlated camera predictions do not corroborate | PASS | Open-area unverified safety signal; requires verification |
| Simulation cannot corroborate real-model observation | PASS | Open-area unverified safety signal; requires verification |
| V2 above-threshold score below .5 still records review candidate; event-id dedup | PASS | {"severity": "OBSERVE", "score": 0.42, "duplicate_suppressed": true} |
| SOS creation, acknowledgement, review and timestamps | PASS | {"sos": "CRITICAL", "ack": "ACKNOWLEDGED", "final": "RESOLVED", "history": [{"timestamp": "2026-10-28T07:53:16.579716+00:00", "status": "NEW", "note": "SOS activated (prototype test; no emergency dispatch)"}, {"timestamp": "2026-10-28T07:53:16.580026+00:00", "status": "ACKNOWLEDGED", "note": "Test operator"}, {"timestamp": "2026-10-28T07:53:16.580026+00:00", "status": "RESOLVED", "note": "Test reviewed"}]} |
| All existing dashboard zones registered | PASS | {"hall_public": "OPEN_HIDDEN"} |
| Real saved research metrics | PASS | {"files": 6} |
| Saved radar/acoustic replay; unrelated recordings do not corroborate | PASS | [{"type": "fall", "processing_mode": "recorded_sensor_replay", "score": 0.99329, "evidence_reference": "evaluation\\outputs\\radar_route_a\\radar_predictions.csv:row=0"}, {"type": "scream", "processing_mode": "recorded_sensor_replay", "score": 0.5374575257301331, "evidence_reference": "evaluation\\outputs\\yamnet\\yamnet_predictions.csv:row=742"}] |
| V2/V3 temporal sampling equivalence | PASS | Exact training sample indices verified for short/long clips |
| Original backend environment FastAPI HTTP startup | PASS | {"port": 18000, "health": {"status": "online", "mode": "EXPLICIT_PROCESSING_MODES", "time": "2026-10-28T07:53:18.378823+00:00", "version": "2.0.0", "note": "Prototype only; no real emergency dispatch"}} |
| Vision environment FastAPI HTTP startup | PASS | {"port": 18001, "health": {"status": "ok", "device": "cpu", "processing_mode": "real_model", "scope": "offline public-area analysis", "models": [{"version": "v2", "threshold": 0.4, "available": true, "score_type": "uncalibrated classifier score", "feature_dimension": 1536}, {"version": "v3", "threshold": 0.7, "available": true, "score_type": "uncalibrated classifier score", "feature_dimension": 1536}], "fall": {"weights_available": true, "status" … (full output in JSON) |
| V2 real MP4 HTTP inference and saved research score equivalence | PASS | {"video": "datasets\\open_hidden\\fighting\\raw\\AIRTLab\\A-Dataset-for-Automatic-Violence-Detection-in-Videos-master\\violence-detection-dataset\\violent\\cam1\\97.mp4", "score": 0.9745275974273682, "saved_reference_score": "0.9745276", "latency": 6.123, "feature_cache_hit": false, "incident": {"status": "recorded", "event_id": "c47090e5-bded-4a0f-b2af-85e974d55202", "incident_id": "52e8117f-07c7-4ae3-b1a7-9cdcc05db19c"}} |
| V3 real MP4 HTTP inference and saved research score equivalence | PASS | {"video": "datasets\\open_hidden\\fighting\\raw\\AIRTLab\\A-Dataset-for-Automatic-Violence-Detection-in-Videos-master\\violence-detection-dataset\\violent\\cam1\\97.mp4", "score": 0.9848954677581787, "saved_reference_score": "0.98489547", "latency": 0.009, "feature_cache_hit": true, "incident": {"status": "recorded", "event_id": "63cb72f0-7629-4b03-bf57-df6b7d4719ad", "incident_id": "52e8117f-07c7-4ae3-b1a7-9cdcc05db19c"}} |
| Real model event to incident and map state; V2/V3 correlated evidence retained | PASS | {"zone": "ZONE_CORRIDOR_A", "severity": "OBSERVE", "independent_confirmation": false, "ack": "ACKNOWLEDGED"} |
| Real YOLO11-Pose fall video, event metadata and decodable annotated MP4 | PASS | {"status": "success", "analysis_id": "9affe7a6-dc94-4fde-afe9-3bf19b3903a7", "model_version": "yolo11n-pose-temporal-rule-v1", "zone_id": "ZONE_STAIRCASE", "processing_mode": "real_model", "experimental": true, "events": [{"frame": 64, "time_sec": 2.1, "type": "possible_fall", "reason": "upright_to_persistent_horizontal"}], "candidate_frames": 47, "candidate_detected": true, "review_status": "pending_human_review", "video_duration_sec": 3.667, "i … (full output in JSON) |
| Inference CORS for existing Vite origin | PASS | {"allow_origin": "http://localhost:3000"} |
| Backend CORS for dashboard | PASS | {"allow_origin": "http://localhost:3000"} |

## Browser checks

| Test | Status | Actual output |
|---|---|---|
| Browser startup and all nine navigation pages | PASS | All nine existing navigation items render; backend connected |
| Browser real V3 upload, loading state, preview and result | PASS | {"score": 0.9848954677581787, "model": "v3", "mode": "real_model", "incident": "91d5b0ab-962d-4d37-a167-e89d4a167dc9", "preview": "blob URL"} |
| Browser acknowledgement persists through FastAPI | PASS | {"backend_status": "ACKNOWLEDGED", "history_entries": 2} |
| Browser Digital Twin status synchronizes with actual model event | PASS | {"zone": "ZONE_CORRIDOR_A", "risk": "OBSERVE", "acknowledged_incident_still_pending_review": true} |
| Browser SOS, incident acknowledgement and private-zone map update | PASS | {"mode": "simulation", "level": "CRITICAL", "acknowledged": true} |
| Browser actual YOLO fall inference and annotation output | PASS | {"events": [{"frame": 64, "time_sec": 2.1, "type": "possible_fall", "reason": "upright_to_persistent_horizontal"}], "annotation_displayed": true, "actual_h264_playback": true, "latency": 3.878} |
| Browser saved radar replay and explicit provenance | PASS | {"mode": "recorded_sensor_replay", "evidence": "evaluation\\outputs\\radar_route_a\\radar_predictions.csv:row=0"} |
| Browser explicit simulated radar/acoustic fusion | PASS | {"mode": "simulation", "severity": "HIGH", "independent_simulated_modalities": true} |
| Browser source and status filtering | PASS | Source=vision and status=acknowledged filters retain the acknowledged real-model incident |
| Browser real evaluation metrics render | PASS | Research comparison rendered from backend artifacts; V3 combined F1 0.9167 |
| Browser CSV export includes processing mode and evidence | PASS | {"download": "SafeSense_Incidents_2026-10-28.csv", "bytes": 2432, "provenance_included": true} |
| Browser narrow-screen navigation and upload layout | PASS | {"window": 390, "body": 390, "main": 326, "scroll": 326} |
| Browser runtime error audit | PASS | No JavaScript page errors across navigation and end-to-end workflows |

## Existing HTTP smoke script

Executed scripts/test_e2e.py against a disposable backend on port 18002; its reset never touched the running demo. Original expectations were updated for Observe review incidents and explicitly independent virtual sensor modalities.

| Test | Status | Actual output |
|---|---|---|
| Health endpoint | PASS | HTTP 200; level/status ; 41.26ms |
| Zone policy endpoint | PASS | HTTP 200; level/status ; 22.26ms |
| Reset TEST state | PASS | HTTP 200; level/status ; 2.94ms |
| Private presence -> LOW | PASS | HTTP 200; level/status LOW; 4.38ms |
| Private fall -> OBSERVE | PASS | HTTP 200; level/status OBSERVE; 3.04ms |
| Private fall+scream -> HIGH | PASS | HTTP 200; level/status HIGH; 3.48ms |
| Private vision forbidden -> 422 | PASS | HTTP 422; level/status ; 2.87ms |
| Open rapid motion -> OBSERVE | PASS | HTTP 200; level/status OBSERVE; 3.3ms |
| Open motion+impact -> HIGH | PASS | HTTP 200; level/status HIGH; 12.89ms |
| Private SOS -> CRITICAL | PASS | HTTP 200; level/status CRITICAL; 15.9ms |
| Get state | PASS | HTTP 200; level/status ; 18.16ms |
| SOS incident appears in /state | PASS | HTTP 200; level/status CRITICAL; ms |
| Acknowledge via FastAPI | PASS | HTTP 200; level/status ; 3.43ms |
| Acknowledge status confirmed | PASS | HTTP 200; level/status ACKNOWLEDGED; ms |

## Retained and added unit tests

These focused unit tests validate logic/adapters; their mocked HTTP transports are not model inference or hardware tests.

| Test | Status | Actual output |
|---|---|---|
| test_temporal_logic.TestTemporal.test_horizontal_without_transition_not_fall | PASS | ok |
| test_temporal_logic.TestTemporal.test_normal_stays_quiet | PASS | ok |
| test_temporal_logic.TestTemporal.test_sustained_motion_candidate | PASS | ok |
| test_temporal_logic.TestTemporal.test_upright_to_horizontal_candidate | PASS | ok |
| test_private_sensor_simulator.TestPrivateSensorSimulator.test_fall_uses_simulation_source | PASS | ok |
| test_private_sensor_simulator.TestPrivateSensorSimulator.test_reject_invalid_confidence | PASS | ok |
| test_private_sensor_simulator.TestPrivateSensorSimulator.test_reject_invalid_event | PASS | ok |
| test_private_sensor_simulator.TestPrivateSensorSimulator.test_sos_uses_simulation_source | PASS | ok |
| test_evaluate_fsd50k.TestPipeline.test_metrics | PASS | ok |
| test_evaluate_fsd50k.TestPipeline.test_mid_list | PASS | ok |
| test_evaluate_fsd50k.TestPipeline.test_read_labels | PASS | ok |
| test_privacy_adapters.PrivacyAdapters.test_backend_unavailable_camera_never_opens | PASS | ok |
| test_privacy_adapters.PrivacyAdapters.test_private_camera_never_opens | PASS | ok |
| test_privacy_adapters.PrivacyAdapters.test_private_zone_cannot_be_authorized | PASS | ok |
| test_privacy_adapters.PrivacyAdapters.test_speech_has_no_acoustic_event_mapping | PASS | ok |
| test_privacy_adapters.PrivacyAdapters.test_yamnet_posts_model_provenance_without_audio | PASS | ok |

## Build / startup checks

| Test | Status | Actual output |
|---|---|---|
| Python import + module compatibility | PASS | backend.main and fight_api imported; backend.fight_api.app is the same app object |
| Python compileall | PASS | python -m compileall -q backend fight_api.py ai_models scripts/start_services.py; exit 0 |
| TypeScript | PASS | npm --prefix dashboard run lint -> tsc --noEmit; exit 0 |
| Production frontend build | PASS | Vite 8.3.5; 2261 modules transformed; dist generated; exit 0 |
| Service supervisor | PASS | Existing .venv backend 8000, .venv-vision AI 8001, Vite 3000 all returned HTTP 200 on loopback. Occupied-port refusal also observed. Shutdown of owned child processes was observed during controlled restarts. |
| Browser runtime crash audit | PASS | No JavaScript page errors across tested navigation/workflows; mobile width 390px with body/main within viewport |

Non-fatal build warnings: the pre-existing Vite configuration uses __dirname; the main bundle exceeds the advisory 500 kB threshold (~1.36 MB uncompressed). Starlette emits a TestClient/httpx deprecation warning. Invalid-byte upload testing deliberately causes OpenCV to print moov atom not found; the API returns 422 and continues running.

## Failures found and corrected during work

- Initial replay regression failed: excluding unrelated replay rows accidentally excluded the current row, causing a real recorded fall candidate to be assessed LOW. Fixed to include the current row only; final replay tests pass and unrelated recordings do not corroborate.
- The first acoustic adapter test used Mock for a context manager, producing AttributeError: __enter__. Corrected the test fixture to MagicMock; the application adapter test now passes.
- Initial browser inspection script printed Unicode to the Windows cp1252 console and failed after saving its screenshot. Browser test runner now sets UTF-8 output; full browser workflows pass.
- A restart immediately after stopping an owned service correctly refused a still-occupied port while the previous supervisor was cleaning up. Waited for its shutdown and started again; no unrelated process was stopped.
- Repair targets verified by regression: wrong model root/module entrypoint, missing incident contract, ACK body/state mismatch, private-zone camera gating, low-score V2 candidates, correlated evidence, replay provenance and browser video codec.

## Not run / practical limits

| Check | Status | Reason |
|---|---|---|
| Physical mmWave/C1001 connectivity or inference | NOT RUN | No verified hardware connection; saved TI IWR6843 evaluation predictions were replayed instead |
| Live microphone/YAMNet capture | NOT RUN | No capture was started; adapter/privacy logic and recorded evaluation replay were tested |
| Live webcam capture | NOT RUN | No camera was opened; public-zone permission-before-capture regression passed |
| Fresh raw radar inference / raw point-cloud streaming | NOT RUN | UI replay intentionally reads existing evaluation predictions; original benchmark scripts retained |
| Impact model evaluation | NOT RUN | No established impact evaluation artifact; simulation/experimental mapping is labeled accordingly |
| New full dataset evaluation / model retraining | NOT RUN | Existing trained models and research results preserved; uploaded-clip score equivalence tested |
| Verified school performance / real-time throughput | NOT RUN | Research demo only; reported CPU timings cover selected offline clips, not deployment performance |
| Genuine AVI/MPG/MPEG uploads | NOT RUN | Extension acceptance is implemented and all content is decoded with OpenCV; actual E2E inference used existing MP4 recordings |
| Production identity, TLS, durable database, external dispatch | NOT RUN | Out of the local demo implementation; no external deployment or message sending performed |

Inference/API checks run on isolated ports 18000/18001. Browser checks use the running demo and create labeled test incidents; restarting the supervisor clears in-memory history. Generated annotations/test logs stay under runtime; original research outputs and trained models were not used as output destinations.
