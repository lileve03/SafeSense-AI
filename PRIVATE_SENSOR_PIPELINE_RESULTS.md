# Private Area Sensor Pipeline - Actual Results

Date: 2026-10-29. Changes extend the existing FastAPI/SQLite application; no replacement backend, database migration or model replacement.

## Findings and integration

The inspected Phase 2 ZIP has synthetic positional replay and an unverified fall annotation, not radar/YAMNet inference. Its read-only optional simulation lab remains separate. This integration reuses SafeSense's existing raw TI IWR6843 feature extraction, held-out-subject SVM_RBF worker, cached local YAMNet and registered research recordings. It does not treat ZIP animations as measurements.

Private monitoring now offers authorized fresh inference of registered radar/non-speech acoustic files through the existing bounded `/testing/runs` queue (one worker, two waiting). Saved CSV predictions still use `/sensors/replay`. Simulation controls remain explicitly separate. Fresh execution on a recording has `processing_mode=real_model`, `source_type=RECORDED SENSOR REPLAY`, `is_test=true`; it is not verified live hardware.

Both paths use the original EventIn schema, event policy, SQLite incident store and context refresh into the existing private Digital Twin. No camera, microphone, transcription or waveform export was added. Unsupported occupant count, positions and distances remain unavailable and the operational scene has zero positioned occupants.

## Fixes

- Stable fresh-recording event IDs include source SHA-256, model/version and available model/training/threshold configuration. Separate inference runs retain their actual run history but reuse the original observation/incident for identical evidence.
- Saved replay IDs include zone, modality, row and prediction-file SHA-256. Identical replay does not create another incident.
- Event deduplication now checks SQLite when an ID has left the 500-event in-memory window. Original timestamps are retained; a replay is not a new measurement.
- Fresh worker output is checked against the actual source checksum and a finite score in [0,1] before event delivery. Invalid saved scores are rejected; missing scores remain null rather than fabricated zero.
- Negative acoustic replay emits normal_acoustic metadata instead of silently leaving the previous scream observation active. It creates no incident.
- Private controls reject simultaneous duplicate clicks and display an explicit already-recorded message.

## Explainable fusion and SOS

Existing conservative rules are reused. Independent radar fall plus acoustic scream/impact in the same zone, processing mode and analysis run within the configured five-second arrival window yields HIGH. A single positive signal yields OBSERVE. Explicit SOS yields CRITICAL. Incident reasons and supporting event evidence explain the rule.

Unrelated fresh recordings have separate analysis-run IDs and do not corroborate one another. Saved research replays cannot fuse with other records. Tests use explicitly labeled simulation to exercise corroborated fusion; this is not evidence that the radar/audio datasets describe a shared real incident. Ingest timestamps are observation/processing times, not validated recording event times.

## Executed tests

| Check | Result | Actual evidence |
| --- | --- | --- |
| Raw recorded radar fall and normal | PASS | Actual feature extraction + SVM_RBF inference, SHA-verified inputs |
| Recorded YAMNet scream and background | PASS | Actual cached TensorFlow model, Screaming class only |
| Unrelated raw recordings remain uncorroborated | PASS | Positive records individually OBSERVE, never HIGH |
| Explainable fusion | PASS | Simulated independent radar + acoustic gives HIGH |
| SOS | PASS | Existing simulated sos_button path gives CRITICAL; no dispatch |
| SQLite synchronization | PASS | Real recorded observations/incident persisted; repeat analysis reuses same ID |
| Durable replay dedup | PASS | In-memory events cleared; SQLite still returns original incident |
| Negative acoustic observation | PASS | normal_acoustic, no incident |
| Private-zone rejection | PASS | Camera provenance/media rejected 403; vision modality/source and speech type rejected 422 |
| Integration suite | PASS | 4 tests, zero failures/errors; four real recordings + repeated radar inference |
| Real browser | PASS | 4 checks: fresh worker, private Twin, duplicate run, fusion/SOS and preservation |
| Existing backend regressions | PASS | 65 tests, zero failures/errors |
| TypeScript | PASS | npm run lint (tsc --noEmit) |
| Production build | PASS | npm run build; existing Vite config/chunk-size warnings remain |
| Running dashboard/backend smoke | PASS | Controls visible on :3000, health 200 on :8000, zero smoke events |
| User data preservation | PASS | All 696 pre-restart SQLite record body hashes unchanged |
| Fight/Pose/models/private scenes | PASS | Browser suite checked 10 protected files unchanged, original 73 incidents unchanged |
| Physical radar/acoustic/SOS hardware | NOT TESTED | No connected/verified hardware supplied |
| Synchronized real multimodal fusion | NOT TESTED | No time-aligned shared recording provided |
| Recognition accuracy | NOT TESTED | Four samples are functionality checks, not a validated accuracy study |

## Measured recording results

CPU Windows, retained local environments and existing cached models. Model timing excludes interpreter/import/model setup; wall time includes the complete worker and event delivery. Radar models were already cached. These are individual measurements, not benchmark averages.

| Recording | Actual model score | Candidate | Model inference seconds | End-to-end seconds |
| --- | --- | --- | --- | --- |
| radar_raw_fall | 0.9932906517861326 | True | 0.030355 | 4.254 |
| radar_raw_normal | 0.21749784996737054 | False | 0.030777 | 4.087 |
| acoustic_scream | 0.9465681314468384 | True | 0.170566 | 12.588 |
| acoustic_background | 0.0009683079551905394 | False | 0.152923 | 12.039 |

Radar fall: 238 points / 24 frames; normal: 307 points / 25 frames. These are sensor point/frame counts, not people. Scores are model outputs, not demonstrated recognition accuracy or calibrated event probabilities.

## Browser inspection evidence

- [Recorded radar result in existing private monitoring](runtime/private-sensor-browser/recorded-radar-private-twin.png)
- [Explicit simulation fusion](runtime/private-sensor-browser/simulation-fusion-private-twin.png)
- [Controls on actual running dashboard](runtime/private-sensor-pipeline/actual-dashboard-recorded-controls.png)
- [Real inference integration results](runtime/private-sensor-pipeline/results.json)
- [Browser assertions](runtime/private-sensor-browser/results.json)
- [Actual service/data preservation](runtime/private-sensor-pipeline/actual-smoke-results.json)

The recorded-radar screenshot was opened and visually inspected: readable model/version, genuine score and source SHA; explicit no-live-hardware notice; unavailable geometry; original sidebar and light private monitoring design retained. Browser assertions verify no video/audio/image elements, zero capture calls and zero positioned occupants.

## Modified application files

- backend/main.py
- backend/scenario_testing.py
- dashboard/src/components/analysis/SensorEventPanel.tsx
- dashboard/src/components/analysis/PrivateRecordedSensorPanel.tsx (new)

Tests: tests/test_private_sensor_pipeline.py and tests/test_private_sensor_browser.py (new). Documents: PRIVATE_SENSOR_PIPELINE_RESULTS.md (new), INTEGRATION_PLAN.md (updated).

## Limitations

No verified live hardware ingestion, occupancy estimation, per-person tracking, room coordinate calibration, sensor-to-person association or validated event timestamp was added. The classifier inputs are recording-level examples. A repeated analysis of identical evidence deliberately retains the original observation timestamp and incident, including after resolution; it does not represent a new occurrence. Existing historic duplicate records are preserved, not silently deleted. A new independently acquired hardware occurrence must carry its own acquisition identity.

YAMNet targets non-speech Screaming; no speech recognition/recording in toilets is enabled. Offline research WAV processing does not imply permission to record private-area audio. Hardware deployment still needs authorized event-only acquisition, calibration, synchronized clocks and physical validation. Existing Fight V2/V3, YOLO Pose, evidence pipeline and trained artifacts were not changed. No Git repository was present; no history was initialized or rewritten.
