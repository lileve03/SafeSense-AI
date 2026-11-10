# Smooth reference-style humanoids

## Visual scope and reference limitation

The existing avatar component was refined in place. The uploaded green screenshot was not available in this turn, so an exact image match cannot be independently asserted. Geometry was compared with the user's detailed design and the original `threejs_test/main.js:createPerson`: spherical head radius .18 at height 1.55, an approximately matching overall height and rounded body proportions.

The previous segmented silhouette has been replaced with a smooth sphere head, softly tapered torso, two continuous rounded arms and two separate rounded-end legs. There are no exposed joint seams, separate hands/boots, faces, clothing, hair, identity details or textures. Bright green (#22c55e), matte roughness .86 and zero metalness restore the clean green-human style. Supported motion review is amber and supported fall indication is red.

Walking and idle amplitudes are restrained. Smooth shortest-path turning, stopping and controlled simulated lying motion are retained. Only explicit simulation time drives body animation. Pause freezes animation; valid recorded position data does not manufacture measured body poses, idle breathing or walking anatomy.

## Preserved scene and data

No room geometry, walls, grid, radar placement, sensing-circle implementation, acoustic/SOS location, page layout or dashboard theme was edited. The existing single renderer and avatar pool remain. Track IDs and supplied X/Y/Height/Velocity, distance lines/labels, trails, repeated motion, room risk lighting, incidents, camera controls and Telegram handlers remain on the original paths.

The SOS scenario now snapshots the current simulation's valid tracks and retains their positions and IDs across selection, Start, Restart, seek and playback. Its synthetic velocity is zero while those positions are held. SOS flags and the actual backend test incident still drive the existing sensor/room response. No unrelated generated proximity history is analyzed during SOS. An empty scene stays empty instead of inventing new SOS occupants.

## Actual before/after screenshots

Fresh baseline captures and source copies were saved before editing. Before/after use the same original camera, viewport and exact synthetic offset. All are application screenshots from Chromium.

| View | Before | After |
|---|---|---|
| Normal / green | [Before](runtime/reference-humanoids/before/normal-room.png) | [After](runtime/reference-humanoids/after/normal-room.png) |
| Multiple people walking | [Before](runtime/reference-humanoids/before/walking-room.png) | [After](runtime/reference-humanoids/after/walking-room.png) |
| Approach / review | [Before](runtime/reference-humanoids/before/approaching-room.png) | [After](runtime/reference-humanoids/after/approaching-room.png) |
| Possible fall | [Before](runtime/reference-humanoids/before/fall-room.png) | [After](runtime/reference-humanoids/after/fall-room.png) |

The full page, mid-fall frame and SOS-preserved-position screenshots are also saved under `runtime/reference-humanoids/`.

## Verification and performance

`tests/test_reference_humanoids_browser.py` passes walking, approaching, stopping/idle, turning, repetitive motion, intermediate/full falls, SOS position retention with actual test incident, matching telemetry/distance labels, replay smoothing, invalid/unverified input rejection, neutral recorded body animations, pause freeze, twelve valid anonymous tracks and Orbit/Zoom/Reset controls. Synthetic contract fixtures are labeled as fixtures, not actual recorded/hardware measurements. Browser errors: zero. Extra paused renders over 600ms: zero.

Shared geometry, one solid matte body material per avatar, no per-frame geometry creation, no avatar shadows, bounded trails, lazy pooling, existing 30fps cap and 1.5 pixel-ratio cap are retained. Smoother surfaces use slightly more triangles while fewer body meshes reduce draw calls. These counts describe workload, not a target-laptop frame-rate guarantee.

| View | Before triangles / calls | After triangles / calls |
|---|---:|---:|
| walking | 5800 / 64 | 7224 / 56 |
| normal | 3204 / 48 | 3916 / 44 |
| approaching | 5800 / 64 | 7224 / 56 |
| fall | 5800 / 64 | 7224 / 56 |

TypeScript and production build pass with existing Vite warnings. The separate single-room/incident and mocked SOS/Telegram regression tests are also run. Tests use isolated SQLite databases and do not send external Telegram messages. Existing SQLite data was not reset or edited.
