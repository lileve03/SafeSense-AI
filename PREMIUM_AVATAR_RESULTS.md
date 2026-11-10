# Premium minimalist avatar upgrade

The existing `AnonymousPersonAvatar` and `AnonymousTrackingLayer` were upgraded in place. The original toilet room, fixture locations, page layout, theme and one-canvas architecture remain intact. No second character renderer was added.

## Visual and animation changes

- Continuous elliptical torso with rounded shoulders, tapered waist and pelvis, oval faceless head and visible neck.
- Rounded upper/lower limbs, subtle hands and feet, articulated hips/knees/shoulders/elbows; no clothing, facial details, textures or identity.
- Matte standard material (roughness .94, metalness 0): teal-green normal, amber supported motion review, coral-red supported falls. Selection keeps a subtle cyan accent.
- Track-driven simulation gait with opposing arm/leg motion, knee lift, torso counter-rotation and slight body lift. Stride eases in/out; turning follows the shortest angular path.
- Subtle deterministic idle movement while simulation playback runs. Pause freezes all body animation. Coordinates never wander or change to create a pose.
- Explicit simulated falls use the existing collapse interval (8 to 9.2 seconds) for a smooth staged rotation into lying. Recorded position-only tracks remain neutral; a valid associated fall label can still produce the existing clearly schematic fall-state indication, never a measured body pose.

Track IDs, X/Y/Height/Velocity, source labels, distance lines, trails, radar/acoustic/SOS, room risk lighting and incident delivery remain on the existing data path. Missing velocity stays unavailable.

## Actual before/after captures

Baseline images and source copies were saved **before editing**. Matching upgraded images use the same original camera, viewport, scenario and playback offsets (walking 3.5s, normal 6s, proximity 10s, fall 11s). These are browser-rendered application screenshots, not generated artwork.

| Scenario | Before | After |
|---|---|---|
| Two people walking | [Before](runtime/premium-avatars/before/walking-room.png) | [After](runtime/premium-avatars/after/walking-room.png) |
| Normal | [Before](runtime/premium-avatars/before/normal-room.png) | [After](runtime/premium-avatars/after/normal-room.png) |
| Approaching / review | [Before](runtime/premium-avatars/before/approaching-room.png) | [After](runtime/premium-avatars/after/approaching-room.png) |
| Fall | [Before](runtime/premium-avatars/before/fall-room.png) | [After](runtime/premium-avatars/after/fall-room.png) |

Additional screenshots and a mid-fall capture are in `runtime/premium-avatars/checks/`.

## Browser validation

`tests/test_premium_avatar_browser.py` passes all scenario, animation and contract checks, with no browser errors. It verifies two moving people, stopping without coordinate drift, idle movement, opposite arm/leg swings, gradual direction changes, intermediate/full fall progression, pause freeze, amber review/red fall, distances, trails, selected telemetry, twelve valid simultaneous track slots and neutral body animation for recorded position-only inputs.

Explicit synthetic browser fixtures test animation and replay contracts; they are not presented as actual recordings or hardware measurements. Invalid, unverified hardware and no-position observations still produce no located humans.

The Part 1 single-room/incident regression and mocked SOS/Telegram regression are run separately. Existing SQLite data is not edited; tests use separate databases. No external Telegram messages are sent by the tests.

## Rendering cost

Shared low-polygon geometry is reused across all slots. Each articulated segment is pre-merged where possible; materials are shared within a person. There is no skeletal solver, per-frame geometry creation, texture loading, avatar shadow pass or physical material. The existing 30fps cap, lazy slot pool, cached labels, bounded trails and 1.5 pixel-ratio cap remain. Paused browser checks reported zero extra renders over 600ms.

The richer silhouette adds modest draw calls and several thousand triangles. These are measured renderer diagnostics at matching camera/offsets, not a frame-rate guarantee on a target laptop:

| Scenario | Before triangles / calls | After triangles / calls |
|---|---:|---:|
| walking | 2128 / 56 | 5800 / 64 |
| normal | 1368 / 44 | 3204 / 48 |
| approaching | 2128 / 56 | 5800 / 64 |
| fall | 2128 / 56 | 5800 / 64 |

TypeScript and production build pass. Existing Vite configuration and bundle-size warnings remain.
