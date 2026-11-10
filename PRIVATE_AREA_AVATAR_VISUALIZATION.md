# Anonymous person visualization

The existing room, campus map, dashboard layout, lighting, sensors and incident pipelines are preserved. Tracking octahedrons/rings are replaced by pooled faceless geometric people, using the actual `createPerson` geometry/material construction in `threejs_test/main.js` (around line 357): sphere head radius 0.18, capsule torso radius 0.22/length 0.70 and two 0.60 m cylinder legs. No external models, textures, faces or recordings were added. These dimensions are schematic, not measured body size.

The reference's scripted whole-body fall rotations were deliberately not reused: position-only observations do not establish a fall pose. Simulation-only leg swing is illustrative, derived from coordinate displacement, with opposing hip pivots and motion direction. Recorded/live avatars retain neutral legs. All modes use the existing normalized observation adapter; invalid, missing, stale or unverified live data remains suppressed. Avatar origins follow the supplied observation coordinates; the schematic feet do not establish a measured floor contact or person height.

Normal tracking is cyan; backend-highlighted proximity/motion candidates are amber; the explicitly supported simulated fall track is red. Selection adds an emissive highlight without changing the rule color. A zone-level fall classification without a supported track association does not arbitrarily color every person red. No skeletal keypoints, fight gestures or measured gait are inferred. Label text shows anonymous ID and coordinate-derived MOVE/STILL state; existing selection panels and coordinate separation remain available.

Eight pooled avatar slots preserve the renderer's existing capacity; current demonstrations use up to six simultaneously. No additional shadows or per-frame geometry allocation. A small hemisphere light belongs only to the separate tracking overlay scene; original room lights are unchanged. Tracks remain schematic overlays readable through the original privacy partition, not a claim of radar penetration.

## Changed files

- `dashboard/src/components/private-area/AnonymousPersonAvatar.ts` — reference geometry/material adaptation, faceless body and leg pivots.
- `dashboard/src/components/private-area/AnonymousTrackingLayer.ts` — pooled avatars, simulation gait, source-safe neutral poses, selection, colors and diagnostics.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx` — overlay-only illumination, supported simulation fall association and visibility-safe picking.
- `dashboard/src/components/private-area/trackingPlayback.ts` — optional per-track fall association in the visual frame type.
- `dashboard/src/components/private-area/TrackingPlaybackControls.tsx` and `GuidedPrivateDemo.tsx` — compact schematic-pose disclosure in existing text locations.
- `tests/test_interactive_tracking_browser.py` — avatar/gait/color assertions, neutral live-shaped fixture, fall screenshot and actual return-to-campus navigation.
- This report. No backend logic or user incident database was modified.

## Actual checks

Commands run with local virtual environment Python:

```powershell
.venv-vision/Scripts/python.exe tests/test_interactive_tracking_browser.py
.venv-vision/Scripts/python.exe tests/test_guided_private_demo_browser.py
.venv-vision/Scripts/python.exe tests/test_private_area_readiness.py
node dashboard/node_modules/tsx/dist/cli.mjs --test tests/privateAreaHardwareReadiness.test.ts
npm.cmd --prefix dashboard run lint
npm.cmd --prefix dashboard run build
```

Interactive suite: 17 PASS, covering six avatars, IDs, smooth coordinate updates and simulation leg motion, appearance/departure, selected movement information, exact Euclidean distances, cyan/amber/red colors, trails, pause, speed, restart, orbit/zoom/reset, sensor picking, stale removal, source isolation and Map → Toilet → Map → Toilet navigation. Test-only trusted live-shaped fixture stays neutral; it is not real hardware evidence. Browser capture calls and errors: zero. Tests use isolated SQLite and disable external dispatch.

Guided suite: 16 PASS, including all five scenarios, sensor/incident response, replay deduplication, source disclosure, mobile layout and campus navigation. Together the two actual browser suites passed 33 checks.

Backend readiness tests: 6 PASS, including comparison against the original room archive (21 declarations, nine placements and original camera pose), SQLite restart persistence, packet validation and disconnected hardware. Frontend normalized-data tests: 10 PASS. TypeScript and production build PASS; existing nonfatal Vite loader/large-chunk warnings remain.

The first added navigation assertion incorrectly used the sidebar as a return action; it was corrected to exercise the actual existing Return to campus map control. An initial all-cyan assertion was corrected to allow legitimate backend proximity candidates in the busy scenario; explicit amber/red checks and normal cyan fixtures remain. Final results are in the linked JSON reports.

Measured headless Chromium/SwiftShader with six avatars: 15.0 FPS, 78 draw calls, 10,176 triangles, last render CPU sample 1.4 ms, script execution 0.167 s over 3 s, JS heap 36.54 MiB. Geometry count stayed 48 → 48, textures 14 → 14; paused render delta was zero over one second. Total browser task time was 3.038 s over the sample: this is not a low-total-CPU guarantee or hardware-GPU benchmark. The prior dot renderer was cheaper; these bounded primitive figures add geometry while avoiding heavyweight assets. No long-duration or physical device performance claim is made.

## Browser evidence

- [Six simultaneous avatars screenshot](runtime/interactive-tracking-checks/six-track-simulation.png)
- [Amber repeated-motion candidate screenshot](runtime/interactive-tracking-checks/repeated-motion-candidate.png)
- [Red simulated fall candidate, neutral pose screenshot](runtime/interactive-tracking-checks/avatar-fall-candidate.png)
- [Interactive results](runtime/interactive-tracking-checks/results.json)
- [Guided workflow results](runtime/guided-private-demo-checks/results.json)

Hardware remains **Disconnected**. The change adds no camera, microphone, speech capture, real hardware driver or external Telegram delivery claim.
