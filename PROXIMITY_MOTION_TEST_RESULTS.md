# Proximity and temporal motion verification

Executed locally on 2026-11-02. Test databases are isolated, physical hardware is not connected, and external notification delivery is disabled.

| Suite | Actual result |
| --- | --- |
| `tests/test_track_motion.py` | **23 passed** |
| `tests/test_track_motion_api.py` | **6 passed** |
| `tests/test_sensor_observations.py` | **8 passed** |
| `tests/test_radar_tracking_simulation.py` | **4 passed** |
| `tests/test_private_sensor_pipeline.py` | **4 passed**, including actual recorded radar/acoustic inference; 69.855 s |
| `tests/test_interactive_tracking_browser.py` | **15 Chromium browser checks passed** |
| `tests/test_sensor_observations_browser.py` | **6 Chromium mode/interface checks passed** |
| TypeScript / Vite production build | **Passed** |

Total: **45 backend tests and 21 browser checks passed**. These are software verification counts, not detection accuracy measurements.

Unit coverage includes exact 3D pair/nearest distances, strict distance thresholds, configurable dwell duration, meaningful reversal counting, estimated/reported velocity provenance, acceleration and direction features, source/device/zone/session isolation, capture-time provenance loss, dropped/reassigned IDs, plausible-history resets, missing/non-finite/out-of-range coordinates, low quality, impossible reported velocity, duplicate/out-of-order timestamps and continuity gaps. Negative cases include short proximity passes, straight walking, a single U-turn, circular motion, stationary jitter and alternating noisy velocity reports without coordinate travel.

API checks verify that the preview accepts only explicit simulation data and refuses frontend rule overrides or forged recorded/live sources; normalized observations retain explainable analysis in SQLite without creating incidents; retries do not advance state; pre-upgrade observation IDs remain compatible; classification-only recorded replay remains spatially unavailable; and uncommissioned live ingestion remains HTTP 503.

Actual browser checks verified:

- The repeated-motion demonstration produces `REPEATED_BACK_AND_FORTH`, exposes backend features/rule conditions, and highlights T01 in the original Toilet scene.
- Sustained proximity reports **0.60 m**, produces `PROXIMITY_DURATION`, and highlights both T01/T02.
- Seeking to the empty room clears previous candidates and highlights.
- Existing playback, selection/raycast, Orbit/Zoom/Reset, trails, coverage toggles, speed, restart, departures and source-mode isolation remain functional.
- Browser runtime errors, capture calls, preview-created backend events and preview-created incidents were all **zero**.
- The paused render loop emitted **zero additional frames over one second**. The six-track software-renderer sample measured **18.67 FPS**, 60 draw calls / 960 triangles, stable geometries **36 → 36**, stable textures **14 → 14**, and 0.142 s browser JavaScript duration over a roughly three-second sample. These Chromium/SwiftShader measurements are not a physical GPU guarantee.

Machine-readable browser evidence: `runtime/interactive-tracking-checks/results.json`. Candidate screenshot: `runtime/interactive-tracking-checks/repeated-motion-candidate.png`. Existing mode checks: `runtime/hardware-prototype-checks/browser-results.json`.

The existing radar fall-classification modules, training/evaluation artifacts and incident/fusion policies were not replaced or reinterpreted as motion rules. Actual recorded-input pipeline regressions passed. No physical-device validation or machine-learning performance experiment was performed. Existing non-fatal Vite config/chunk warnings and Starlette's httpx deprecation remain.

Rule definitions, defaults and supported-data limitations: [PROXIMITY_MOTION_RULES.md](PROXIMITY_MOTION_RULES.md).
