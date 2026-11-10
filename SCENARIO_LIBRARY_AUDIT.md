# Scenario library audit — 28 October 2026

## Access and repository

Windows command/file access succeeds through the available authorized elevated execution path. Error 1385 did not block this work. No Windows account/security policy was modified. The repository has no `.git` directory and no AGENTS.md was found in the searched source tree; Git history/diff verification is unavailable. Existing source, model paths, API contracts, restoration documentation and actual datasets were inspected in place.

Observed local inventory: **102 radar CSV files**, **10,231 extracted FSD50K WAV files**, and **four prepared UR Fall MP4 files**. Existing AIRTLab violent/non-violent recordings are present under the retained violence-detection dataset. Counts describe local files, not validated sample counts or deployment performance.

## Findings before changes

| Component | Actual behavior | Gap |
|---|---|---|
| Public camera jobs | Genuine V2/V3 R3D-18 classifier execution and genuine YOLO pose inference; offline CPU processing | Scenario manifest exposed only one fight, one non-fight and one fall clip |
| Radar scenario | Replayed a saved `radar_predictions.csv` row | No fresh extraction/prediction from the available raw CSV |
| Acoustic scenario | Replayed a saved `yamnet_predictions.csv` row | No fresh waveform inference despite existing audio and local pretrained model cache |
| Radar model artifacts | Benchmark trains SVM_RBF/RandomForest per held-out subject; no saved radar estimator was found | Cannot truthfully claim to load a pre-existing serialized radar classifier |
| Acoustic model | Existing pretrained YAMNet SavedModel is cached locally | Need explicit local-only loading, not an implicit network download |
| Private privacy and response | Original Three.js room, metadata-only replay, SOS, shared incidents/reports and safe Telegram routing already exist | Fresh unrelated sensor recordings need separate run IDs to prevent accidental fusion |

## Implemented

- Central registry now contains **17 entries**, including **12 fresh inputs**: four AIRTLab videos, four UR Fall/ADL videos, two raw radar CSVs and two FSD50K samples. Existing two saved-prediction and three controlled-test IDs remain unchanged and visibly separate.
- New Scenario Testing Library in the existing Live Monitoring page runs real jobs through authenticated `/testing/scenarios`, `/testing/runs`, and `/testing/runs/{id}`. Original feed, upload, replay, simulation, private room, navigation and response controls remain available.
- Video scenarios reuse the existing bounded inference service and trained V2/V3/YOLO paths. CPU feature-cache reuse is disclosed; inference is never replaced by a forced label.
- Radar reconstructs the existing LOSO benchmark from its original feature table, excluding the selected recording's subject, with the original model parameters. Runtime estimator caching writes only under `runtime/scenario-model-cache`. Every scenario extracts fresh raw CSV features and predicts again. This is explicitly a reconstructed benchmark, not a previously saved trained radar artifact or a live person tracker.
- Acoustic inference uses the retained `.venv-acoustic`, existing local YAMNet model and existing evaluation preprocessing. It reads the selected research waveform server-side and computes the actual Screaming score. No microphone, raw audio endpoint, playback, speech recognition or new recording is added. FSD50K labels are weak clip labels, not guaranteed timestamps or exhaustive annotations.
- Workers retain the separate radar/acoustic/vision environments. No package environment was recreated or merged, no model download was initiated, and research outputs/datasets were not overwritten.
- Jobs are bounded, asynchronous and persistent. Failures, missing prerequisites and interrupted runs are exposed without simulated fallback. Source IDs/models are allowlisted; caller file paths and private-video zone overrides are rejected.
- Fresh raw sensor runs have unique analysis IDs and metadata/hash evidence. Unrelated radar/acoustic samples cannot fuse into a corroborated incident. Counts of radar points are never presented as people counts or calibrated room positions/distances.
- Dataset-label comparisons apply only to the relevant modality: AIRTLab does not provide fall ground truth for YOLO, and UR Fall does not provide fight labels for V2/V3. Classification mismatches are retained rather than forced away.
- Navigation previews public video without launching hidden CPU analysis. Explicit camera-card clicks still autoplay and run models; this prevents navigation-triggered work from unexpectedly blocking the original upload workflow. The original browser suite passed after the correction.

Fresh negative acoustic results are recorded as `normal_acoustic` metadata, an additive event type; existing event types/endpoints remain supported. The old `/sensors/replay` API still means saved prediction replay. Existing scenario IDs `radar` and `acoustic` keep that behavior; fresh raw-data scenarios have separate IDs.

## Preservation and limits

End-to-end verification hashes selected source recordings, original model weights/classifiers and research tables before and after execution. Hash evidence is written to `runtime/scenario-library-tests/preserved-artifacts.json`. This verifies the selected 19 artifacts, not a full hash inventory of every dataset file. Additional run results, cache files, evidence and logs are restricted to runtime storage.

No live sensor/camera availability, calibrated private occupancy/positions, school accuracy, synchronized physical multi-sensor recording, real Telegram receipt or emergency dispatch is claimed. See SCENARIO_LIBRARY_TEST_RESULTS.md for executed outcomes and limitations.
