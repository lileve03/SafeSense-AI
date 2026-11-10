# Private Area scene alignment, timing, labels and risk

## Findings before editing

The existing axis conversion `(track.x, track.height, track.y)` was already correct. The visual problems came from uncalibrated body proportions/ground anchoring, a low oblique camera, oversized fixed sprites, a radar sweep located near the ceiling, two competing lighting writers and fallback to historical incident severity. The room geometry and source track coordinates did not need replacement.

Fresh baseline screenshots and source copies are under `runtime/scene-alignment/before/`.

## Changes in the existing scene

- Explicit inverse coordinate helpers document and verify X/right, Y/forward, Height/up -> room X, Z, Y. No lateral offsets, coordinate rescaling or invented separation are applied.
- The existing smooth green humanoid geometry is preserved. Its schematic body is uniformly scaled to .8 so it fits the 0.6m two-person demo; the actual track anchor stays at the supplied X/Y/Height. Standing body feet align to the floor, while the source track point is treated as a sensor point rather than a measured foot joint. Fall bodies retain their supported schematic lying orientation. Body depth testing now gives proper occlusion between parts and people.
- The original room/walls/partition/floor/grid and sensor hardware positions are unchanged. The initial camera is elevated and aimed from the open side; Orbit, Zoom and Reset remain.
- Track-ID and distance sprites have compact pixel sizes and screen-space collision placement. They avoid each other, the projected body bounds, sensor labels and existing UI controls. Small leaders retain association when a label must move. Label placement never moves a person or track point.
- Distances and the visible line use the Euclidean separation of displayed 3D track points; raw source points remain separately available. Valid replay interpolation keeps its display distance separate from raw source telemetry. Distance text refreshes on the current frame, including seek and Pause.
- A captured frame supplies both normalized observation and rendering diagnostics. Telemetry publication follows capped rendered frames (up to 30Hz), replacing the independent 5Hz UI sampling. Pause freezes positions, timestamp and animation together; recorded diagnostics retain the recorded source timestamp.
- Verbose radar/source/pose explanations moved to the existing expandable Technical Details. The scene keeps compact source, scenario-risk and sensor controls.
- The subtle scan is now at world y=.03, centered on the configured radar's floor projection. Its maximum radius fits the room; the ceiling radar fixture and green ring remain at their original positions.
- One pure current-scenario risk function drives simulation status and lighting. Normal = LOW; supported proximity/repeated motion = OBSERVE; simulated fall = HIGH during its supported interval; SOS = CRITICAL during activation. Historical incident level is never an input. Recorded/hardware observation visual state is likewise separate from persisted incident severity; absent observations are labeled unavailable.
- Actual incident severity is explicitly labeled in the existing incident panel. An unrelated persisted HIGH can remain separately visible while the normal scene is green/LOW. Incidents are not downgraded or rewritten to force visual consistency.

One existing WebGL canvas and the existing room/overlay render path are retained. No duplicate room, monitoring page or renderer was added.

## Actual browser verification

`tests/test_scene_alignment_browser.py` uses a temporary SQLite database and explicitly seeds an unrelated HIGH test incident. It checks:

- Normal, two-person proximity, paused tracking, repeated motion, possible fall and visual risk transitions.
- Exact source/display coordinates in simulation, uniform body scale and floor alignment.
- Euclidean pair distances against displayed points and the actual line endpoints (float tolerance for GPU buffers).
- Identical paused observation/render timestamps and matching telemetry time, with zero extra paused renders over 600ms.
- No label intersections with other labels, body bounds, sensor annotations or UI reservations.
- Radar sensor/scan X/Z alignment and floor height.
- SOS retaining track IDs and coordinates, replay interpolation and rejection of unsupported hardware/pose data.

`tests/test_scene_labels_camera_browser.py` confirms simultaneous green/LOW scene and persisted HIGH incident display, plus collision-free labels after Zoom, Orbit and at a 430px viewport. No browser errors occurred.

## Before/after evidence

Matching synthetic offsets are used; camera framing intentionally changes as part of this fix.

| View | Before | After |
|---|---|---|
| Normal | [Before](runtime/scene-alignment/before/normal-room.png) | [After](runtime/scene-alignment/after/normal-room.png) |
| Two moving tracks | [Before](runtime/scene-alignment/before/walking-room.png) | [After](runtime/scene-alignment/after/walking-room.png) |
| Two-person proximity | [Before](runtime/scene-alignment/before/approaching-room.png) | [After](runtime/scene-alignment/after/approaching-room.png) |
| Possible fall | [Before](runtime/scene-alignment/before/fall-room.png) | [After](runtime/scene-alignment/after/fall-room.png) |

[Normal visual LOW beside actual incident HIGH](runtime/scene-alignment/camera-checks/normal-low-actual-incident-high.png)

Additional full-page, repeated-motion, paused and camera screenshots/results are in `runtime/scene-alignment/checks/` and `camera-checks/`.

## Preserved behavior and limitations

The original 30fps cap, lazy pool, shared body geometry/materials, cached label textures, bounded trails and demand rendering remain. Screen-space placement uses projected bounds and does not alter tracking. At extremely dense/offscreen views, labels that cannot safely fit are hidden rather than stacked; every valid avatar and its selectable detail record remains.

Tracking, source X/Y/Height/Velocity, proximity/repetition/fall calculations, acoustic/SOS fusion, incident IDs, staff response and Telegram handlers are retained. Simulated bodies are never presented as measured radar skeletons. The room and bodies are schematic, not a surveyed installation or reconstructed human anatomy.

TypeScript and production build pass with existing Vite warnings. Separate single-room/incident and mocked SOS/Telegram regressions are also run. All test mutations use isolated databases, Telegram transport is disabled or mocked, and existing SQLite records were not reset or edited.

Final validation: 12 scene/scenario/contract checks, 6 camera/live-clock/risk checks, 1 complete guided response, 2 single-room/input-mode checks and 3 mocked notification cases pass. The live movement timestamp comparison is captured atomically and is identical in renderer and telemetry. The complete guided fall run returns visual risk to LOW while retaining actual incident HIGH and RESOLVED status.
