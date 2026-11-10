# Private Area interactions and scenario animation

The existing original toilet room, smooth faceless humanoid geometry, camera framing, sensor locations, single WebGL canvas and three-column Dashboard layout are preserved. No alternate page or second room/renderer was added.

## Interactions

Walking, stopping, turning and subtle simulated idle remain driven by timestamped track positions and supplied velocity. Valid replay interpolates only between received samples, with bounded smoothing and neutral schematic body poses. There is no random wandering or claimed radar skeleton reconstruction.

Start now resumes an explicitly seeked time instead of silently resetting to zero. Restart explicitly resets the scenario clock, trail state, distance state and visual risk. Starting again at the end also resets the playback epoch and stale analysis.

Motion Trails remain optional. Seeking reconstructs recent trail samples from the selected explicitly synthetic trajectory, bounded to 32 points per track. Repeating the same seek produces the same positions and trail samples. Recorded histories use received observations; missing physical trajectories are never filled in with synthetic people. Hidden trails avoid GPU buffer uploads.

The thin distance line joins the exact displayed 3D track points. The floating label updates from their Euclidean distance and explicitly prefixes synthetic values with SIM. Existing collision avoidance now retains safe prior label offsets when possible, reducing lane switching and flicker. Cached text textures update only when the formatted value or discrete label color changes. Selected X/Y/Height/Velocity remains on the original source-data path.

## Shared risk presentation

| Current visual state | Palette |
|---|---|
| Normal / LOW | Green #22c55e |
| Observe | Yellow #eab308 |
| Warning | Orange #f97316 |
| High | Red #ef4444 |
| Critical SOS | Red emergency accent #fb3148 |

The same palette drives affected avatars, radar coverage/ring accents, room lighting and the current visual-risk badge. Body/room accents crossfade on the simulation clock during playback. Pause and seek settle consistently on the selected risk state. Valid recorded observation color changes use a bounded presentation fade and return to demand rendering when settled; this does not advance source timestamps or synthesize body actions.

The explicit simulated fall has an orange warning stage during its standing-to-lying transition, then red HIGH when the supported fall/fusion interval is reached. This presentation does not change backend fusion rules or rewrite actual incident severity.

SOS retains current anonymous IDs, coordinates, orientation and existing synthetic body poses; it does not invent running, panic, standing up or a physical button press. The wall device has a visible red emergency emission throughout activation, with a subtle clock-driven pulse. The screenshot taken after a fall intentionally holds the earlier lying pose; it is not a new SOS-generated person action. Actual backend SOS request/notification behavior is preserved.

Historical incident severity never supplies current scene visual risk. The existing incident panel continues to label persisted severity separately.

## Actual Chromium tests

`tests/test_scene_interactions_browser.py` passes Normal Presence, Proximity, Repetitive Motion, Possible Fall, SOS, Pause, Seek, Start-resume and Restart. Assertions cover exact coordinates and Euclidean line endpoints, timestamps, trail endpoint/history consistency, optional trails, label/body/control collisions, pose/turn behavior, the five palette levels, intermediate rendered colors, SOS held poses, replay contracts and demand rendering. Valid-replay contract fixtures are explicitly synthetic test fixtures, not actual recorded hardware observations.

The renderer's warning-to-high samples include orange, multiple intermediate hues, then red. The final avatar, radar and room accent agree. Paused scenes and settled replay checks observe at most one extra render in their observation windows; no continuous idle GPU loop is introduced while paused.

A separate complete guided run preserves actual NEW -> SIMULATED acknowledgement -> RESOLVED handling, with one persisted HIGH incident while visual risk returns to LOW. Three mocked Telegram cases pass (disabled, no assignment, accepted test request). Tests send no external Telegram messages and use isolated SQLite databases. Existing SQLite data is not reset or edited.

TypeScript and production build pass with existing Vite configuration/bundle warnings. Shared body geometry, pooled avatars, the 30fps cap, 1.5 pixel ratio, cached labels and bounded trails are retained. No new shadows, post-processing, model inference or per-frame geometry construction was added.

## Actual screenshots

All screenshots are captured from the application in Chromium; the times below are explicit simulation offsets.

| Evidence | Screenshot |
|---|---|
| Normal, 6s | [Normal](runtime/scene-interactions/screenshots/normal-room.png) |
| Two tracks, 2.5s, SIM 1.24m | [Motion frame 1](runtime/scene-interactions/screenshots/motion-2_5s-room.png) |
| Same tracks, 3.5s, SIM 1.03m | [Motion frame 2](runtime/scene-interactions/screenshots/motion-3_5s-room.png) |
| Proximity / yellow Observe, SIM 0.60m | [Proximity](runtime/scene-interactions/screenshots/proximity-room.png) |
| Timestamped repetitive motion | [Repetitive motion](runtime/scene-interactions/screenshots/repetitive-room.png) |
| Orange warning, partial fall, 8.6s | [Warning](runtime/scene-interactions/screenshots/warning-room.png) |
| Red high, lying pose, 11s | [High / fall](runtime/scene-interactions/screenshots/fall-room.png) |
| Critical SOS, held body poses and positions | [SOS](runtime/scene-interactions/screenshots/sos-room.png) |

Full-page captures are saved alongside the room images. Structured browser results and intermediate color samples are under `runtime/scene-interactions/checks/results.json`.
