# Original Toilet twin: interactive tracking simulation

Open the dashboard at `http://127.0.0.1:3000`, enter **Digital Twin Map → Private Area 3D View**, and set **Source mode → SIMULATION**. The original room, walls, privacy partition/cubicle layout, sensors, lighting, Orbit, Zoom and Reset controls remain in place.

Below the room, select a scenario and press **Start tracking**. **Pause tracking** freezes both tracks and schematic radar coverage. **Restart tracking** begins again at zero. Playback supports 0.5×, 1×, 2× and 4× speed, and the time slider pauses at a chosen point. Scenarios cover staggered arrivals/departures, two tracks passing in the aisle, and six simultaneous tracks. Each complete sequence lasts 40 simulated seconds.

Click an anonymous diamond in the room or a **SIM Txx** button to select it. The selected marker gains a gold ring and its current coordinates, velocity and speed appear below the scene. Track IDs are synthetic, not personal identities. Toggle motion trails or schematic radar coverage independently. Trails show a bounded recent floor projection, not physical sensor returns. Distances use `hypot(dx,dy,dz)` from the current simulation coordinates; the scene shows the nearest pair (or nearest pair involving the selected active track), and the panel lists pair distances. The simulation people count is exactly the number of active simulated tracks; it begins and ends at zero.

All tracking markers and distances are explicitly labeled SIMULATION. No face, recognizable person, camera image, private-area video or microphone capture is rendered or acquired. The previous mannequin objects remain in the preserved component code but are hidden; the displayed tracking targets are abstract geometric markers. Existing incident indicators remain independent of this visual playback. Playback itself emits no backend events, notifications or incidents. The previous isolated radar-rule demonstration remains available as its own clearly labeled component; opening it pauses this new playback.

## Shared rendering interface

- `trackingPlayback.ts` defines a source-aware `TrackingFrame`, anonymous `VisualTrack`, simulation clock, synthetic paths, coordinate-distance helper and normalized-observation adapter.
- `AnonymousTrackingLayer.ts` renders the same frame shape for SIMULATION, RECORDED_REPLAY or future LIVE_HARDWARE observations. It supports selection, labels, trails and pair-distance annotation without rebuilding the room.
- `TrackingPlaybackControls.tsx` provides playback, scenario, speed, count and selection controls. React UI snapshots publish at 5 Hz; coordinates are evaluated continuously by the scene render loop.
- `PrivateAreaDigitalTwin3D.tsx` retains the original room and camera and composes the tracking layer as a lightweight annotation pass. This avoids rendering track markers again in the room's transmission/shadow passes. Markers and labels stay legible behind the original partition; this is a schematic overlay, not a demonstration of wall penetration or a verified coverage survey.

Future observations use the existing normalized schema documented in [HARDWARE_SENSOR_INTERFACE.md](HARDWARE_SENSOR_INTERFACE.md). `observationFrame` accepts only VALID spatial observations with `coordinate_frame = zone_meters_x_right_y_forward_z_up`. It maps `(x,y,z)` to Three.js `(x,z,y)` and retains supplied velocities/quality. It never derives a person location from a class label or invents missing velocity. Invalid/stale observations clear the tracking layer. Actual device connection, calibration, authorization and heartbeat verification still belong to the physical adapter; this work does not connect or verify hardware. The UI continues to report **Hardware Disconnected**.

The visual pool supports eight positioned tracks; supplied frames retain their full track count in diagnostics and `visible` identifies the rendered subset. Current synthetic scenarios use at most six. Before deploying a physical tracker with higher track capacity, choose an explicit bounded display budget or extend the pool; do not equate anonymous tracker outputs with verified occupancy. Existing replay classifications have no calibrated room tracks and therefore remain unpositioned.

## Resource limits and verification

The renderer is capped at 30 FPS, renders on demand when paused, pauses playback when the tab becomes hidden, and disposes all tracking geometries/materials/textures on unmount. Each marker has at most 32 trail vertices. Marker/line geometries and label textures are reused; no growing trail history, per-frame model inference, sensor network streaming or incident writes occur. Static room shadows are cached while preserving the existing room lighting.

`tests/test_interactive_tracking_browser.py` launches an isolated FastAPI/SQLite instance and frontend, then exercises actual headless Chromium/WebGL. It checks playback, 3D raycast and button selection, count and coordinate distances, Orbit/Zoom/Reset, trails and coverage toggles, speed, departures/restart/scenario changes, rendering resource counts, a normalized future-hardware **test fixture**, invalid/stale removal, mobile layout, and absence of capture/incident side effects. Paths are also sampled across all scenarios to check room bounds and partition clearance.

Machine-readable actual results and a screenshot are saved under `runtime/interactive-tracking-checks/`. This environment uses Chromium's SwiftShader software renderer; its measured frame rate is not a physical GPU benchmark. The results record actual FPS, draw calls, triangle count, script time, frame submission time, GPU resource counts and heap usage rather than claiming a hardware frame rate.

Run with the existing environments:

```powershell
.\.venv-vision\Scripts\python.exe tests/test_interactive_tracking_browser.py
.\.venv-vision\Scripts\python.exe tests/test_sensor_observations_browser.py
.\.venv\Scripts\python.exe tests/test_sensor_observations.py
.\.venv\Scripts\python.exe tests/test_radar_tracking_simulation.py
npm.cmd --prefix dashboard run lint
npm.cmd --prefix dashboard run build
```
