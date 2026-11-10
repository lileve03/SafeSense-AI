# Private Area avatar consolidation - Part 2

The single unified page and original toilet room are retained. No tabs, alternate monitoring page or second room were added. Room walls, grid and radar/acoustic/SOS fixture positions are unchanged.

## Reference adaptation

`threejs_test/main.js:createPerson` supplies the sphere head (radius .18 at height 1.55), capsule torso (radius .22, length .70 at .90), and two cylinder legs. The existing dashboard adaptation lacked arms, used cyan and never rotated into a fall. The new avatar preserves those reference proportions and adds two simple rounded arms. It has no face, clothing, textures, identity inference or skeleton reconstruction.

Normal tracks are green (#22c55e). Supported backend motion candidates and explicitly associated fall candidates are red (#ef4444), with subtle matching transparent ground discs. Proximity candidates are review signals, not proof of violence. Calculated distance labels use validated track coordinates and reset on source/scenario/seek changes.

Simulation walking includes restrained limb motion. Explicit simulated falls rotate the relevant humanoid into a lying orientation. Non-simulated fall illustration requires a valid fall observation with exactly one supplied track, since the current backend schema has no per-track fall association. Multi-track class-only fall output never guesses which person fell. Every fall pose is labeled schematic; no measured anatomy is claimed.

## Source and rendering behavior

One avatar is used per valid anonymous track within the backend schema's maximum of 128. Eight slots are prepared initially; additional slots are allocated lazily and reused. Coordinates remain X/Y/Height from the active source; Three.js maps height to its vertical Y axis. Detail panels use the same source and show supplied velocity or 'Velocity unavailable'.

Valid replay samples with continuity use bounded smooth interpolation between received positions, lasting at most 300ms. There is no future extrapolation. Long gaps, source changes and invalid frames reset interpolation. Position-only replay keeps a neutral schematic pose and does not manufacture a walking gait or measured body pose. Existing recorded class-label evidence usually supplies no tracks, so it still produces no located humans or distances.

CPU controls: shared low-polygon body geometry, one solid material per avatar, no avatar shadows, pixel ratio capped at 1.5, existing 30fps cap, bounded trails, cached label textures and rendering only on change (or active playback/interpolation). Browser checks observed zero extra paused renders over 600ms. At the default test camera, diagnostics reported 1,368 triangles / 45 draw calls for one track and 2,128 / 58 for two. These are diagnostic workload counts, not a claim of target laptop frame rate.

## Actual Chromium validation

`tests/test_private_avatar_part2_browser.py` uses a temporary SQLite database and disabled external notifications. It checks Normal Presence, Close Proximity, Repeated Motion and Possible Fall; avatar counts, two arms, colors, standing/lying states, moving positions, trails, calculated distance labels, selected telemetry and idle rendering. It also checks replay interpolation and rejection of invalid/unverified/no-position input. Replay contract fixtures are explicitly synthetic test data, not actual recordings or hardware.

Screenshots and structured results: `runtime/private-avatar-part2/`.

- `normal-room.png` / `normal-page.png`
- `proximity-room.png` / `proximity-page.png`
- `repetitive-room.png` / `repetitive-page.png`
- `fall-room.png` / `fall-page.png`

Part 1 regression: `tests/test_private_no_tabs_acceptance_browser.py` passes the original canvas identity, no-tabs, active incident and hardware safeguards. `tests/test_unified_private_notifications_browser.py` passes three SOS/Telegram outcomes using mocked transport. No external messages are sent by tests. TypeScript and production build pass with existing Vite warnings.

No existing SQLite records were reset or edited. Backend fusion, incident, notification and staff response logic was preserved.
