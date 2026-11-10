# Private Area risk lighting fix

## Root cause

The current scenario controller already retained HIGH and the final fall pose at completion. The remaining rendering defect was separate from playback: two radar status writers still assigned teal independently of scenario risk, and the test radar halo retained a hardcoded teal material. The cone had only 0.035 opacity, the sweep faded to 0.025, and ambient illumination mixed 87% white into the risk color. The white floor had no explicit risk tint. Consequently, the avatar could correctly show HIGH while coverage looked green or almost uncolored.

## Change

`dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx` now uses its existing shared scenario accent for the room lights, floor tint/emission, radar cone, sweep, fixture ring and radar test halo. Removed the competing fall/teal writers. Added one lightweight schematic floor footprint inside the existing scene, increased cone/sweep visibility and reduced white dilution. Existing risk crossfades remain in use; room risk does not pulse or flash. No additional canvas, view, controls or person animation was introduced.

The existing backend policy remains authoritative: LOW/Normal is green, OBSERVE yellow, WARNING orange, HIGH red and CRITICAL strong red. Possible Fall alone currently produces backend OBSERVE, so it correctly displays yellow rather than fabricating a corroborated HIGH assessment. Fall + Distress produces HIGH/red. Missing hardware remains unavailable/neutral.

Completion and acknowledgement preserve HIGH and the final fall pose. Explicit linked resolution clears the alert color without inventing recovery movement. Restart/scenario change resets the visual epoch while preserving SQLite history. Unrelated historical incidents do not control the selected scenario.

## Verification

- TypeScript check and production build: PASS. Existing Vite configuration/chunk-size warnings remain.
- Scenario/test workflow contracts: 22 PASS, 0 FAIL.
- Backend fusion, incident, notification and privacy regression tests: 16 PASS, 0 FAIL.
- Real Chromium + FastAPI + isolated SQLite lighting/completion suite: 14 PASS, 0 FAIL. Covers Normal, Possible Fall, Fall + Distress, SOS, pause/resume, completion, final-frame seek, acknowledgement, explicit resolution, restart and missing hardware.
- Shared-scene Acoustic/Fusion/SOS browser regressions: 18 PASS, 0 FAIL. Includes actual registered recorded YAMNet inference, notification state rendering, incident linkage, reset, duplicate prevention and privacy. Telegram API acceptance uses a mocked HTTPS transport in this suite; it does not establish real delivery or receipt.
- Actual screenshot pixel checks: 96,513 red pixels before completion; 96,385 red pixels after completion. Material checks also verify cone, footprint, sweep and radar halo agree with HIGH.

Screenshots: `runtime/private-risk-completion/before-completion.png`, `after-completion.png`, `possible_fall-lighting.png`, `sos-lighting.png`, `restarted.png`, `normal-presence.png`, `explicitly-resolved.png`, `radar-unavailable.png`. Exact integration results: `runtime/private-risk-completion/results.json`.

`tests/test_private_risk_completion_browser.py` adds real rendered-pixel checks, material diagnostics assertions and Possible Fall/SOS lighting coverage. Production changes are confined to the existing scene component. This report is the third changed source/document file; generated screenshots, results and dashboard build assets were refreshed.

Hardware limitations: tests use explicitly simulated scenarios and recorded inputs where supported. No live radar or acoustic hardware was verified. The completion suite disables Telegram delivery; no real recipient receipt is claimed. Private-area CCTV, speech recording and identifiable reconstruction remain prohibited.
