# Interactive Toilet tracking: actual results

Executed on 2026-11-02 using the existing backend and vision environments. All browser runs used an isolated backend/SQLite database and disabled Telegram delivery. The user's incident database was not used by the browser fixtures.

- **12 interactive Chromium browser checks passed** (`tests/test_interactive_tracking_browser.py`).
- **6 existing observation/mode browser checks passed** (`tests/test_sensor_observations_browser.py`).
- **8 normalized-observation backend tests passed** (`tests/test_sensor_observations.py`).
- **4 existing radar-simulation backend tests passed** (`tests/test_radar_tracking_simulation.py`).
- TypeScript and Vite production build passed. Existing non-fatal Vite config/chunk warnings and the Starlette httpx deprecation remain.

The interactive checks exercised the actual WebGL canvas and real controls: six simultaneous markers and their IDs; exact coordinate distances; track-button selection and 3D raycast selection; current movement information; orbit drag, zoom in/out and reset; movement and motion trails; pause; trail/coverage toggles; playback speed; restart, departures and scenario changes; normalized future-track fixture ingestion using the same renderer; stale data clearing; responsive canvas; and source-mode isolation. Browser runtime errors, microphone/camera capture calls, new backend events and new incidents were all **zero**.

The paused scene rendered **0 additional frames during a one-second sample**. Across all synthetic scenarios, sampled trajectories stayed within room bounds and avoided the existing privacy partition. Maximum sampled movement speed was approximately **1.45 m/s** at normal playback speed. In the six-track scenario, sampled active counts at 0, 2, 4, 6, 12, 32, 35 and 40 seconds were **0, 2, 4, 6, 6, 5, 2, 0**.

Final six-track performance sample in headless Chromium with **SwiftShader software graphics**:

| Metric | Actual |
| --- | --- |
| Observed animation frame rate | 10.33 FPS (30 FPS ceiling) |
| Draw calls / triangles | 60 / 960 |
| Geometries during sample | 36 → 36 |
| Textures during sample | 14 → 14 |
| Last measured CPU frame submission | 3.0 ms |
| Browser JavaScript duration over ~3 seconds | 0.118 seconds |
| Browser total task duration over sample | 3.170 seconds |
| JS heap at sample end | 33.66 MiB |

This is a software-renderer measurement, not a physical GPU performance claim. The original room's transparent materials remain preserved. Rendering the track overlay separately reduced the measured six-track draw workload from 72 calls / 1296 triangles to 60 calls / 960 triangles. Paused rendering remains idle; tracks, trail histories and GPU resource pools are bounded. No physical sensor was connected or tested.

Machine-readable results: `runtime/interactive-tracking-checks/results.json`. Screenshot: `runtime/interactive-tracking-checks/six-track-simulation.png`. Usage and shared-renderer integration notes: [INTERACTIVE_TRACKING_SIMULATION.md](INTERACTIVE_TRACKING_SIMULATION.md).
