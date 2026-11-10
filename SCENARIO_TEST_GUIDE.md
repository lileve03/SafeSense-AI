# Scenario tests

Open Live Monitoring → Scenario Test Library. Entries come from one registry, which verifies source files and labels input/provenance. No file is downloaded or fabricated.

Use the new **Scenario Testing Library** panel for fresh execution. It contains 12 existing research inputs: four AIRTLab fight/non-fight videos, four UR Fall/ADL videos, two raw radar CSVs and two acoustic WAV samples. Select a recording/model, confirm authorized offline use, and click **Run actual inference**. Video preview is recorded footage; private audio is processed server-side without playback, microphone access, transcription or new recording.

Results show actual scores/candidates, processing duration, provenance, frame/point counts where meaningful, model cache disclosure, per-model label comparisons and incident navigation. Negative controls run the model normally; false positives/negatives are not overwritten. Run history persists in SQLite. Use View incident zone on Digital Twin or Open actual incident to inspect the integrated response workflow. Model/source failures are explicit, with no simulated fallback.

The original **Legacy scenario shortcuts** and **Sensor Replay & SOS Demo** are preserved. Entries `radar` and `acoustic` there still mean saved-prediction replay. Fresh raw inputs have IDs `radar_raw_fall`, `radar_raw_normal`, `acoustic_scream` and `acoustic_background`. SOS/fusion/Telegram controls remain explicit controlled tests, not learned inference.

| Scenario | Actual source and behavior |
|---|---|
| A Physical conflict | AIRTLab violent/cam1/97.mp4 → actual V2/V3 → review candidate → full analyzed clip evidence → backend incident/map |
| B Normal activity | AIRTLab non-violent/cam1/1.mp4 → actual classifier output, including false positives if present; label is never forced |
| C Possible fall | Existing UR Fall fall-02-cam0-rgb.mp4 → actual YOLO boxes/skeletons → experimental posture-rule timeline → bounded evidence |
| D Radar fall / daily activity | Fresh raw CSV features → original LOSO SVM/RandomForest benchmark reconstructed without the test subject → metadata-only result/incident. Legacy saved-prediction replay remains separate. Points are not tracked people |
| E Acoustic anomaly / negative control | Existing research WAV → fresh cached-pretrained YAMNet → actual Screaming score → metadata-only event/incident. Legacy saved output replay remains separate; no speech recording/transcription |
| F Private SOS | Explicit simulated SOS → Critical incident without depending on a vision model |
| G Fusion | Explicit simulated radar fall + acoustic scream; not synchronized physical recordings |
| H Telegram | Test SOS incident + real test transport only if configuration and active route exist; otherwise honest disabled/not-configured preview |

Existing upload controls, original private-room scenarios and scoped sensor-replay controls remain available. Public research videos are assigned demo zones; these are not actual school camera recordings. Private areas never accept video.

Run isolated verification (no external sends):

```powershell
.\.venv-vision\Scripts\python.exe tests\test_scenario_library.py
.\.venv-vision\Scripts\python.exe tests\test_real_monitoring.py
.\.venv-vision\Scripts\python.exe -m unittest discover -s tests -p test_notification_safety.py -v
.\.venv-vision\Scripts\python.exe tests\run_unit_checks.py
npm.cmd --prefix dashboard run lint
npm.cmd --prefix dashboard run build
```

The integration harness starts owned services on 18000/18001/3001 with an isolated database and disabled Telegram, then shuts only those processes down. Keep those test ports free. Results, actual model metadata, screenshots and logs are in `runtime/real-monitoring-tests`. Existing normal services are not stopped or reset. See FINAL_INTEGRATION_TEST_RESULTS.md for executed outcomes and remaining untested hardware.

The expanded scenario suite uses 18100/18101/3001 and a separate database. Run it sequentially with other browser suites because both use 3001. It executes every fresh source plus both radar algorithms and checks preservation hashes. Results: [SCENARIO_LIBRARY_TEST_RESULTS.md](SCENARIO_LIBRARY_TEST_RESULTS.md); source audit: [SCENARIO_LIBRARY_AUDIT.md](SCENARIO_LIBRARY_AUDIT.md).

Prerequisites reuse the retained `.venv-vision`, `.venv-radar` and `.venv-acoustic`. YAMNet must already exist in the local TF Hub cache, or set SAFESENSE_YAMNET_PATH to a local SavedModel directory. No automatic download occurs. Radar runtime estimator caches go only to `runtime/scenario-model-cache`; original research artifacts are never overwritten. Optional SAFESENSE_AI_URL points scenario video jobs to the inference service; the launcher sets it automatically for its selected port.
