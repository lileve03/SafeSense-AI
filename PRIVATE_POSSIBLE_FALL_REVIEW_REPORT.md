# Possible Fall red review state

## Root cause

The simulation's `simulationVisualRisk` explicitly returned OBSERVE for `fall_only`. The shared avatar, ground, room and radar palette therefore correctly rendered yellow. Holding the final playback frame retained that yellow policy. This change introduces the requested separate HIGH/red demo review policy without changing backend classification or incident severity.

## Behavior

Possible Fall becomes HIGH/red at its fall cue and shows **Possible Fall - Review Required**. The affected avatar, its ground highlight, floor footprint, room illumination and radar ring all use the existing shared HIGH accent. The review risk and pose persist through completion, backward seeking and Play after completion. Restart, scenario changes and Reset Test State clear that visual latch without changing SQLite incidents.

The right card displays Scenario Risk HIGH, Fall Status Possible Fall, Acoustic Status Quiet and SOS Status Inactive. Actual Backend Assessment remains a separate backend result (currently OBSERVE for an uncorroborated fall); Linked Incident Status remains independent. Fall + Distress, recorded inference, notifications, tracking controls and the single Three.js room are preserved.

## Changed files

- `dashboard/src/components/private-area/sceneTracking.ts`: Possible Fall uses the HIGH visual palette.
- `dashboard/src/components/private-area/trackingPlayback.ts`: hold review risk/pose until explicit visual reset; prevent Play from implicitly clearing completed review.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx`: review-required message and Possible Fall status wording.
- `tests/privateScenarioRisk.test.ts`: verify red review with backend OBSERVE/resolved incident, completion, replay, seek, restart, reset and scenario switch.
- `tests/test_private_risk_completion_browser.py`: test actual rendered red pixels and right-card states, completion, Restart, Reset Test State and switching to Normal.
- `tests/test_part4_private_browser.py`: separate Possible Fall HIGH visual expectations from backend OBSERVE expectations.
- This report. Generated screenshots/results and dashboard build outputs are refreshed.

## Validation

- TypeScript: PASS.
- Production build: PASS (existing Vite configuration and bundle-size warnings).
- State/playback/workflow contracts: 24 PASS, 0 FAIL.
- Real Chromium + FastAPI + SQLite integration: 21 PASS, 0 FAIL. Includes Possible Fall's red completion state with backend OBSERVE, exact right-card labels, Fall + Distress, Restart, Reset Test State, Normal Presence switching, incident history preservation and rendered-pixel checks.

Screenshots: `runtime/private-risk-completion/possible-fall-completed.png` and `possible-fall-to-normal.png`. Exact browser results: `runtime/private-risk-completion/results.json`.

During validation, two test assumptions were corrected: completion needs enough time for the full playback timeline, and Normal Presence can legitimately start with zero tracks. The final rerun passed all checks.

Browser results and screenshots are in `runtime/private-risk-completion/`. Tests use real Chromium, FastAPI and isolated SQLite, with explicitly simulated inputs. No live hardware verification or actual Telegram receipt is claimed. This report supersedes earlier descriptions of Possible Fall's yellow demo styling; the backend OBSERVE policy is unchanged.
