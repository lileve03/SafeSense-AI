# Private Radar Sensing Audit and Results

Date: 30 October 2026, Asia/Singapore.

## Decision

**The available real radar data does not verify multi-person tracking.** Implemented the requested fallback: an isolated, clearly labeled synthetic multi-person workflow inside the original private Three.js room. Real classifier labels are never converted to people counts, person coordinates or measured distances. The existing raw radar fall classifier and non-speech acoustic workflow remain available.

## Actual dataset evidence

Audited every CSV in `datasets/private/radar/iwr6843/mmwave-radar-fall-detection-main/`:

- 102 recordings, **22,696 points**, **2,458 frames**; 23–25 frames per recording.
- All headers: `frame,DetObj#,x,y,z,v,snr,noise`.
- Class directories: 51 Fall / 51 Not. Filename subjects: areeb, raffay and towsif, 34 recordings each.
- No timestamp columns, documented frame rate or room calibration found.
- `DetObj#=0` restarts in every one of the 2,458 frames. The source notebook also pads individual points using this index. It is not a persistent person ID.

| Requested field | Actual finding | What can be claimed |
| --- | --- | --- |
| Timestamped point clouds | Frame-indexed point-cloud CSVs, no acquisition timestamps | Ordered point sets; these are processed radar detections, not raw ADC/IQ captures |
| Radar target IDs | Only per-frame point index | No verified anonymous person identity |
| X/Y/Z target positions | Point-level x/y/z | Real point coordinates, not person centroids or calibrated room positions |
| Velocity/Doppler | Point-level `v` plus SNR/noise | Reported point velocity; units/radial convention not established by local README |
| Continuous trajectories | Short sequences without target association or timing | No verified person trajectories |
| Multi-person recordings | Three subjects / six activity types documented; no occupancy or identity truth | Multi-person occupancy is not verified; point multiplicity is not people count |
| Ground truth | Class directories, motion and subject filenames | Recording-level labels, not target identity/count/position or timed fall truth |

[Per-recording SHA/columns/count audit](runtime/radar-capability-audit/dataset-evidence.json), [README](datasets/private/radar/iwr6843/mmwave-radar-fall-detection-main/README.md), [example CSV](datasets/private/radar/iwr6843/mmwave-radar-fall-detection-main/GatheredData/Fall/Areeb_back_1.csv), [source notebook](datasets/private/radar/iwr6843/mmwave-radar-fall-detection-main/FallDetection.ipynb).

## Models, hardware and Phase 2

The existing `ai_models/radar/benchmark_radar.py` computes recording-level features for LOSO SVM_RBF / RandomForest fall classification. These are not people detectors, count estimators, multi-object trackers or room calibrators. The dataset notebook defines a CNN classifier; no exported radar CNN/tracker checkpoint or calibration/config file was found in the audited radar source tree.

Fresh execution of the preserved cached SVM on the actual registered raw fall CSV produced **0.9932906517861326**, 238 points / 24 frames, `model_cache_hit=true`. No retraining occurred. This remains recording-level possible-fall inference, not per-person fall timing or recognition accuracy. [Actual worker output](runtime/scenario-tests/radar-capability-audit.json).

Windows serial enumeration identifies **COM3: Intel(R) Active Management Technology - SOL**. This is not a verified radar interface. No physical radar stream, firmware target list, calibration, acoustic sensor or SOS hardware was verified. Serial enumeration cannot rule out unenumerated USB/network devices; no device was opened. The first console table obscured this entry; the dedicated saved inventory is authoritative. [Hardware evidence](runtime/radar-capability-audit/serial-ports.json).

The extracted Phase 2 `server.py` loads supplied synthetic frames/track identities and an unverified synthetic fall annotation. Its real YAMNet score extraction does not make its radar tracks genuine. Its experimental independent-audio alignment does not verify real co-occurrence. The separate reference server/database and synthetic positions were not imported as operational measurements.

## Implemented visible workflow

Open **Digital Twin Map → toilet → Multi-person radar workflow demonstration → Open isolated tracking simulation**. It is closed by default.

- Original room, partition, sensor fixtures, lighting, camera, Orbit/Zoom/Reset and styling retained.
- A fixed 24-second, 10-Hz synthetic scenario supplies three scripted anonymous identities. Count is computed from those synthetic identities, not claimed as real people detection.
- Plain anonymous cylinders use synthetic X/Y floor coordinates and height, mapped to Three.js X/Z and vertical Y. No identifiable reconstruction or imaging is used.
- Pair distances are calculated from synthetic coordinates and labeled **synthetic meters**, never measured hardware distance.
- Repeated-motion rule: at least three X-velocity reversals above the demonstration deadband within four seconds. This is not aggression recognition.
- Possible-fall rule: recent upright synthetic height ≥1.1 followed by height ≤0.4 sustained ≥0.5 seconds. Red marker, binary flag; no fabricated numeric confidence.
- Scripted acoustic distress overlaps the synthetic fall. The explicit record control creates HIGH through the existing independent-modality fusion policy. Explicit SOS independently creates CRITICAL.
- Closing the preview restores unlocated real-sensor mode, zero positioned people and Unavailable separation. Simulation positions never enter the real sensor-state stream.

Authenticated `GET /testing/radar-simulation` is read-only. `POST /testing/radar-simulation/events` accepts only session UUID, synthetic time and record kind. It rejects arbitrary coordinate payloads, real/live-source claims and camera fields. Explicit actions use existing EventIn/create_event/fusion/SQLite incidents, `processing_mode=simulation`, `source_type=SIMULATION`, `is_test=true`, no model score/media and synthetic provenance. Session-stable event IDs prevent duplicates. Ordinary incident details and acknowledgement work.

Preview, play, pause, seek and reset never create/delete incidents. The marker/line pool is small and reused. Existing real raw radar/YAMNet processing, Fight V2/V3, YOLO Pose, Alerts, Reports, Telegram implementation and original user data are preserved.

## Actual validation

| Check | Result |
| --- | --- |
| Complete CSV audit | PASS: 102 files; actual headers, frame/index behavior, labels and hashes saved |
| Preserved raw radar inference | PASS: cached SVM, actual score above; not tracking |
| Simulation calculations/temporal rules | PASS: count, Euclidean distances, repeated motion and binary fall |
| Authenticated read-only preview | PASS: authenticated 200, missing token 401, no observation writes |
| Reject arbitrary/real-source payload | PASS: 422 |
| Simulation fusion/SOS/SQLite/dedup | PASS: HIGH fusion, CRITICAL SOS, same incident on repeat |
| Simulation unit/integration tests | PASS: 4 tests, zero failures/errors |
| Real Chromium workflow | PASS: 3 checks; actual mesh coordinates compared to source frame |
| Actual incident dossier/acknowledgement | PASS: browser acknowledges persisted simulation SOS |
| Preview isolation and close | PASS: no preview writes; real spatial values return unavailable |
| Privacy | PASS: zero private media/capture; backend vision/media submissions rejected |
| Mobile/original incidents | PASS: no overflow; original 73 incidents unchanged in isolated suite |
| Existing backend regressions | PASS: 65 tests, zero failures/errors |
| TypeScript and production build | PASS; existing Vite config/large-bundle warnings remain |
| Actual running dashboard smoke | PASS: new endpoints/preview work, 696 original record hashes unchanged, zero created events |
| Real multi-person detector/count/tracking | NOT VERIFIED: no suitable validated input/model/hardware |
| Real proximity/motion/per-person fall | NOT VERIFIED: missing identities, timing, calibration and truth |
| Synchronized real radar/audio fusion | NOT VERIFIED: independent recordings do not prove simultaneous occurrence |

The idle actual backend was reloaded to expose the tested endpoints. Tests use isolated SQLite data and disabled external notification transports. No actual Telegram delivery is claimed. No real tracking accuracy is claimed.

## Screenshots and tests

- [Original room synthetic preview](runtime/radar-tracking-browser/original-room-synthetic-tracks.png)
- [Synthetic identities, coordinates, distances and rule table](runtime/radar-tracking-browser/synthetic-tracks-distances-rules.png)
- [Actual dashboard preview after Orbit, all three markers](runtime/radar-capability-audit/actual-original-room-simulation-orbit.png)
- [Actual dashboard track table](runtime/radar-capability-audit/actual-simulation-track-table.png)
- [Browser PASS results](runtime/radar-tracking-browser/results.json)
- [Actual app/data preservation](runtime/radar-capability-audit/actual-smoke-results.json)

Screenshots were opened for visual inspection. The original partition can occlude markers from the default angle; Orbit exposes them and the table always lists synthetic tracks. This does not mean that a real sensor detected absence or lost a target.

Tests: `tests/test_radar_tracking_simulation.py`, `tests/test_radar_tracking_browser.py`, `tests/run_cpu_monitoring_checks.py`; `npm run lint`; `npm run build`; fresh `scripts/scenario_sensor_worker.py` execution in the retained radar environment.

## Modified files

- `backend/radar_simulation.py` (new)
- `backend/main.py` (register simulation routes only)
- `dashboard/src/components/private-area/RadarTrackingSimulation.tsx` (new)
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx` (isolated marker/pair-line pool; original geometry unchanged)
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx` (preview connection)
- `tests/test_radar_tracking_simulation.py` (new)
- `tests/test_radar_tracking_browser.py` (new)
- `RADAR_SENSING_AUDIT_AND_RESULTS.md` (new)

Generated runtime audit/test evidence and dashboard/dist assets are also updated. Source recordings, models and reference folders were not changed; user database hashes were verified unchanged.

## What is missing for real sensing

A verified capture/hardware stream needs acquisition timestamps or documented stable timing; documented point units/axes; sensor-to-room calibration; persistent target associations or a validated person-detector/tracker; and multi-person count/identity/trajectory ground truth covering crossings, occlusion, clutter and entry/exit. Per-person motion/fall rules need timed annotations and negative cases. Acoustic fusion needs verified clock alignment and provenance.

No live multi-person ingestion, trained target detector, identity-association/Kalman tracker, hardware adapter or tracking-accuracy claim was added. Synthetic identities are scripted, not detected. Thresholds are illustrative, not validated safety limits. Real counts, locations and distances remain unknown until supported. No private CCTV, identifiable imaging, microphone capture or speech recording/transcription is enabled.
