# Private Area UI refactor

The page retains one Three.js Toilet scene and the original three-column organization. The center column is wider, the room is 520px tall, and the room appears first when the layout stacks on smaller screens.

## UI improvements

- A single desktop control row contains Input Source, Scenario, Play/Pause, Restart and Speed, with SOS on the right. Source, hardware and notification states use small badges.
- Zone information and the monitored-zone switcher stay on the left. One privacy badge replaces the repeated camera/privacy paragraphs.
- Radar, Acoustic and SOS inspection chips sit above the room. The scene shows a primary track label and distance label. Enabling sensor labels substitutes the selected sensor label for the track label, keeping the total at two.
- The right panel contains a compact risk/metrics card and a linked incident card. Open Incident remains visible; acknowledgement and alert navigation retain their existing actions.
- Track selection, coordinates, playback seeking, trails, coverage and motion analysis share one expandable card.
- Recent activity uses short cards with local time and a concise description. Clicking reveals the full event text; earlier events remain expandable.
- Technical Details, Sensor provenance, saved prediction replay and Backend rules start collapsed. Only one normalized sensor panel is mounted, retaining observation polling and recorded inference tools.
- The app-level explanatory banner and duplicate mobile mode switch are suppressed only while this private view is open.
- Recorded incident status and reason use the linked backend assessment directly while the shared alerts list refreshes.

Backend event delivery, fusion, SQLite lifecycle, Telegram policy and API routes were not changed. The existing guided demo still labels its automatic staff actions as simulated.

## Changed files

| File | Change |
| --- | --- |
| `dashboard/src/App.tsx` | Defer private-view source explanation to its own toolbar. |
| `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx` | Unified layout, compact status/incident cards, short timeline and consolidated technical tools. |
| `dashboard/src/components/private-area/GuidedPrivateDemo.tsx` | Single-row controls, concise badges and expandable workflow. |
| `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx` | Larger scene, sensor chips above it and selected-sensor label inspection. |
| `dashboard/src/components/private-area/AnonymousTrackingLayer.ts` | Bound floating labels while retaining avatars, trails, distance and selection. |
| `dashboard/src/components/private-area/TrackingPlaybackControls.tsx` | One expandable track/display card. |
| `tests/test_part4_private_browser.py` | Updated UI selectors and checks for layout, collapsed sections, labels, retained actions and responsive behavior. |

The production bundle was regenerated under `dashboard/dist`.

## Verification

- TypeScript: PASS.
- Production Vite build: PASS.
- Real Chromium/FastAPI/SQLite integration: PASS — 29/29 checks, zero browser errors or capture calls. Results: `runtime/part4-private/browser-results.json`.
- Browser coverage includes all six scenarios, canonical incident IDs, acknowledgement/resolution, replay deduplication, Open Incident, track selection, trails, coverage, sensor inspection, source isolation, and fresh radar/YAMNet inference through the retained controls.
- Layout checks cover 1600px desktop, 1280px laptop and 768px tablet widths. Desktop controls occupy one row; the center remains the widest desktop column; smaller layouts have no page-content horizontal overflow.
- Screenshots: `runtime/part4-private/private-ui-desktop.png`, `private-ui-fall.png` and `private-ui-tablet.png`.
- Browser integration uses an isolated database with external Telegram sending disabled.
