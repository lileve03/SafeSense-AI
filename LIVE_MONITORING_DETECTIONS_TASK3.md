# Task 3: real detections and compact Live Monitoring

## Behavior

Clicking a configured camera still autoplays its registered recorded research video immediately and schedules the existing V2, V3 and YOLO11-Pose models independently of playback. The camera registry, original dataset sources, trained classifiers, privacy gates, Telegram policy and Scenario Testing Library are preserved.

YOLO annotations are rendered from actual `prediction.plot()` results on every decoded source frame: person bounding boxes, confidence labels, skeletons and keypoints. New API metadata exposes the same per-frame boxes, person confidence and keypoint coordinates/confidences, plus actual FPS/frame count/dimensions and input SHA256. `predict()` does not perform tracking; there are no track IDs. The experimental temporal fall rule still follows only the most confident person's posture; the detector/annotation metadata includes all detected people. No trained fall probability is invented.

V2/V3 remain R3D-18 feature-based whole-video classifiers with their existing thresholds 0.4 and 0.7. Scores are uncalibrated classifier outputs. They do not supply fighter boxes or exact fight timestamps. Cached feature use is disclosed under Analysis details; classifier inference still runs. Person detections are independent of fight classification.

A compact Detection Results panel shows each model, actual prediction, score, threshold, status and measured latency. Playback detections show frame-local confidence, visible keypoint count and expandable pixel coordinates. Event Timeline contains only actual timestamped pose-rule events; buttons seek the active video. Evidence Preview opens actual retained candidate clips, with authenticated links and incident actions. Whole-clip fight evidence is identified explicitly.

## Synchronization

Annotated files preserve source frame count and constant FPS with no frame skipping. Boxes/skeletons are baked into the corresponding frames, so they remain aligned during seek, pause and replay. Frame-specific metadata uses requestVideoFrameCallback mediaTime when available; timeupdate/seeked provide a fallback. The UI chooses the corresponding zero-based frame and does not interpolate fake detections. Coordinates are source pixels; low-confidence keypoints are reported with their actual confidence.

When completed annotations replace the unannotated source, playback position, manual pause and playback rate are retained. If the original clip has already ended, the completed annotated replay starts from the beginning. Reanalysis similarly preserves playback state. Camera changes clear job results, evidence preview, scores and the old player; selection-generation guards reject late submit/poll results.

No synchronization error was observed on the tested local constant-FPS clips. The frame readout is allowed one decoded frame of timing tolerance around browser seeking; encoded overlays are part of the displayed video frame. Variable-frame-rate sources, other browser engines and physical live hardware have not been validated. A configured live stream remains separate from its bounded analyzed sample; annotations do not claim to describe the current live frame. Continuous real-time inference is not implemented or claimed. Missing/failed inference is visible, without simulated overlays.

## Layout

The existing white/slate/blue theme and camera selector remain. The video uses a responsive aspect ratio/object-contain layout. Detection results sit beside it on wide screens, with frame details, timeline and evidence below; small screens stack these sections. Recent Events lists actual backend events with mode, source and timestamps and a working map-zone action. Removed the redundant synthetic public-camera diagrams and oversized simulated radar card from this page. Original private 3D monitoring remains in Digital Twin. Upload analysis and sensor replay/SOS controls remain functional under the collapsible Upload & sensor tools section. The Scenario Testing Library stays directly accessible. Research metrics remain on Analytics, not duplicated on Live Monitoring.

## Changed files

- fight_api.py: actual pose-frame metadata, annotation alignment, input SHA256; model/rule behavior unchanged.
- monitoring_ai.py: forwards actual pose metadata in combined model results.
- dashboard/src/components/analysis/CameraMonitoringPanel.tsx: responsive player, synchronized clock/handoff, compact results integration, removes duplicate video scenario shortcuts (the main library retains them).
- dashboard/src/components/analysis/DetectionResults.tsx: new model results, frame details, pose timeline and evidence controls.
- dashboard/src/pages/LiveMonitoringPage.tsx: compact operational sections and collapsible existing tools.
- tests/test_detection_monitoring.py: isolated actual model/API/browser verification.
- tests/test_browser_demo.py: opens the new tools disclosure through an actual click before exercising the preserved workflows.
- This report and generated dashboard/dist build assets/runtime test artifacts.

## Verification and actual results

Run with the existing .venv-vision Python (contains the test dependencies), not the minimal backend environment. Tests start isolated localhost services with a temporary SQLite database and Telegram disabled; they do not send staff notifications or modify the active incident database.

- `tests/test_detection_monitoring.py`: actual V2/V3/YOLO runs, original source SHA256, per-frame metadata invariants, independent one-frame YOLO comparison, encoded FPS/frame count, privacy/authentication, real browser playback during CPU inference, manual paused handoff, seek/replay, evidence playback/links, camera reset, actual pose marker, responsive 390px layout and retained tools. Results and screenshots: runtime/detection-task3/.
- `tests/test_real_monitoring.py`: 21/21 passed, including existing APIs, real inference/evidence, negative clip, privacy, SQLite restart, original private 3D, reports, all nine pages and the original 13-case browser workflows.
- TypeScript checking and production build passed. Existing Vite configuration/bundle-size warnings remain.

Observed AIRTLab conflict clip: V2 score 0.9745275974273682; V3 0.9848954677581787. YOLO produced 165 frame records at 30 FPS. Independent frame 12 had four detections matching API boxes, coordinates and confidences. Browser handoff retained pause at 1.2 seconds and playback rate 1.5. Seek checks at 0.6, 2.3 and 4.1 seconds selected the matching frame metadata. UR Fall produced a possible_fall posture event at 2.1 seconds; this is an experimental rule event, not a validated real-world incident time.

An early independent-test path typo caused Ultralytics to fetch a duplicate YOLO weight file under ai_models. It was byte-identical to the existing root model (SHA256 869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0), removed, and the test now explicitly requires the existing root path before loading it. Production inference always used the original root model; no original trained artifacts were replaced or retrained.

Final rerun: focused detection/API/browser suite 8/8 PASS; existing end-to-end suite 21/21 PASS (including the original 13 browser checks); five-feed playback/inference regression 7/7 PASS. Active dashboard original-source playback PASS for all five feeds, with job submission disabled in that smoke-test browser only. All 19 active-database incident records retained unchanged; Task 3 adds no active-database incidents. Overview/Alerts read-only regression PASS with protected source hashes unchanged. Final TypeScript and build PASS. Summary: runtime/detection-task3/summary.json.
