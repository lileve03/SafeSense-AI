# Correction: One Private Area Monitoring page, no view tabs

This section supersedes the earlier consolidation report below. The previous change left a Guided Demo / Advanced Monitoring switcher; that switcher and its `guidedDemo` view state are now removed completely.

Inspection confirmed that both views already used `PrivateAreaDigitalTwin3D`, with page-owned `TrackingPlayback`, context-owned incidents and sensor observations, and GuidedPrivateDemo-owned run/report state. The remaining problem was the view switch plus a disconnected choice of which incident/risk to show.

The final page has one always-mounted scenario engine, one original room and one compact controller above the three columns. One input-source select chooses Simulation, Recorded Replay or verified Hardware input for that same room; it does not switch monitoring pages. Selecting external input pauses synthetic playback and disables only simulation actions, while retaining the controller, columns and canvas.

The engine publishes its existing run/report state to the page. The right-hand sensor summary uses the same playback snapshot as the room, while its incident and risk follow the scenario's persisted incident and actual backend assessment. Resolved exercises show resolved response state and return to LOW room lighting. Historical zone incidents remain accessible through the existing incident workflow and event log.

The separate bottom SOS card is removed. Its working request, confirmation, idempotency and Telegram outcome handler is retained behind one compact SOS action in the controller. Replay adapters render without another input selector or simulation trigger collection. The bottom contains a compact event log and collapsed Technical Details with provenance and recorded tools.

Verification:

- Full Chromium regression: `tests/test_unified_private_monitoring_browser.py` (17 passing checks), now explicitly asserting zero view tabs, one canvas, one direct SOS action, active fall synchronization, and resolved scenario response state.
- SOS/Telegram regression: `tests/test_unified_private_notifications_browser.py` (3 passing cases with mocked transport; no external messages).
- Dedicated no-tabs screenshot and canvas identity check: `tests/test_private_no_tabs_acceptance_browser.py`, output `runtime/unified-private-no-tabs-acceptance/`. Checks exact canvas DOM identity across all three sources and zero positioned occupants for disconnected hardware.
- TypeScript and production build pass (existing Vite warnings remain).

Tests use separate SQLite databases. Existing SQLite records were not reset or edited. No Git reset was used.

---

# Unified Private Area Monitoring

## Inspection before editing

The page entry is `DigitalTwinPage -> PrivateAreaMonitoringView -> PrivateAreaDigitalTwin3D`.
There was one room implementation with two competing presentations, rather than two independent room constructors:

- Guided: `guidedDemo` hid both side columns, expanded the center to 12 columns and mounted `GuidedPrivateDemo` inside the room component.
- Advanced: restored the sidebars, mounted `TrackingPlaybackControls`, which also mounted `PrivateDangerScenarioControls`.
- The page separately mounted `RadarTrackingSimulation`, a second playback clock/frame source, and a seven-button `runScenario` bar backed by context state.
- `SensorEventPanel` added another collection of simulation triggers alongside recorded adapters.
- Room-local `TrackingPlayback`, guided scenario/run/report state, legacy `trackingPreview`, context zone/alert/timeline state and normalized sensor observations could describe different moments or different scenarios.

## Final structure

The page owns one `TrackingPlayback` and subscribes to its snapshot. The original Three.js toilet room, guided engine, sensor summary and track details share that instance. The original room geometry, camera, fixture picking and anonymous tracking layer are retained.

One compact Guided Demo scenario controller sits above the three columns. Workflow narration and notification details are expandable. The room no longer mounts a controller or allocates its own playback store.

- Left: zone classification, sensor inventory and zone switching, always visible.
- Center: source adapter, original 460px room, orbit/zoom, track selection, X/Y/Height/Velocity, pair distances, trails, coverage and motion analysis.
- Right: sensor status, active alert and staff response from existing backend/context records.

Removed from this page's rendered tree: the expanded Guided room presentation, legacy seven-button scenario bar, standalone `RadarTrackingSimulation`, nested `PrivateDangerScenarioControls`, secondary playback scenario/speed/start/restart controls, and replay-panel simulation buttons. Their underlying workflow/adapter modules remain available; no backend detection, fusion, persistence or notification logic was deleted.

Simulation sensor summaries use the shared playback rather than old context illustration values. Replay/hardware use validated normalized observations. The source adapter does not poll or submit independent synthetic fall observations while shared simulation is active. Recorded inference tools remain accessible in Replay; hardware continues to require verified observations.

Guided fall, repeated motion, proximity, normal and SOS use the existing `privateDemoWorkflow` delivery and report polling. Restart reuses the test run, incident synchronization uses existing context refresh, and the scripted responder remains guarded to its own SIMULATION test incident. The prominent SOS button retains its authenticated backend request, idempotency key, confirmation and truthful notification outcome.

## Verification

- TypeScript: `npx --prefix dashboard tsc --noEmit -p dashboard/tsconfig.json`.
- Production build: `npm run build` in dashboard (existing Vite configuration and chunk-size warnings).
- Actual Chromium workflow: `tests/test_unified_private_monitoring_browser.py`; output and screenshots in `runtime/unified-private-monitoring-checks`.
- Actual Chromium SOS notification regression: `tests/test_unified_private_notifications_browser.py`; output in `runtime/unified-private-notification-checks`. Telegram transport is mocked; no external message is sent.

Browser workflows create separate SQLite test databases. The monitoring workflow uses a temporary directory. Existing SQLite data is neither reset nor edited; notification regression also compares original incident records read-only before/after. No Git reset was used (this workspace has no Git repository metadata).

Final outcome: 17 monitoring browser checks and 3 notification browser cases PASS. No browser errors or media capture. A final read-only visual smoke on the running dashboard also confirmed one canvas, two shared tracks and shared presence metadata; all persistent browser writes were blocked and none were attempted. See `runtime/unified-private-monitoring-checks/final-visual-smoke.json` and `unified-three-column-desktop.png`.
