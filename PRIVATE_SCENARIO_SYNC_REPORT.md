# Private Area scenario-state synchronization

## Exact cause

Guided Demo deliberately reuses its stored run and incident IDs to prevent duplicate incidents and Telegram sends. On replay, it passed the persisted incident response back to `TrackingPlayback.updateGuidedAssessment`. `deriveVisual` then explicitly converted RESOLVED/FALSE_ALARM into LOW, even for a current simulated fall. It also used the cached backend assessment as the scenario risk. Additional closure checks suppressed fall/SOS indicators in the observation envelope, Three.js scene and status panel. The acoustic cue expired at 13.2 seconds, so the final distress frame read Quiet. These were state-policy errors, not a Three.js material failure.

## Current policy

- Selected scenario, timestamp and playback phase determine simulated pose, risk and scenario indicators.
- Scenario risk follows the existing timeline: Fall + Distress starts LOW, begins falling at 8 seconds with WARNING, reaches HIGH at 9.2 seconds and holds the final HIGH/fall/distress frame through completion. Seeking backward rewinds the pose and risk consistently.
- Actual backend assessment remains a separate backend result. Missing results display Unavailable. Illustrative HIGH is never presented as a verified live measurement or inference.
- Persisted incident response remains separately visible as NEW, ACKNOWLEDGED or RESOLVED. Even a matching resolved incident cannot cancel a selected simulation. Restart preserves its ID and SQLite response history; existing duplicate/send protections remain in place.
- Normal Presence restores green; SOS follows its CRITICAL timeline. Recorded acoustic tests retain their actual backend inference result and never invent person motion.

This policy supersedes the earlier reports' “linked resolution clears scenario visuals” policy, as explicitly requested in the current task.

## Modified files

- `dashboard/src/components/private-area/trackingPlayback.ts`: remove incident-driven visual suppression and backend-driven simulation risk; timestamp-based seek/pose; retain final distress cue.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx`: remove incident-response suppression of simulated sensor indicators and test highlights; retain shared risk materials and single canvas.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx`: separate Scenario Risk, Actual Backend Assessment and Incident Status; label synthetic fall/distress; unavailable backend results remain unavailable.
- `dashboard/src/components/private-area/GuidedPrivateDemo.tsx`: concise independent-state policy wording.
- `tests/privateScenarioRisk.test.ts`: resolved history, mismatched backend risk, backward seek and final state regressions.
- `tests/test_private_risk_completion_browser.py`: real Chromium resolved-history replay, start/falling/completed screenshots, material/pixel checks and persisted SQLite verification.
- `tests/test_part4_private_browser.py`: wait for independent scenario timeline and assert the new provenance tooltip.
- `tests/test_private_test_actions_browser.py`: assert explicit simulated fall/distress labels.
- This report; generated screenshots/results and production build outputs are refreshed.

## Verified results

- TypeScript and production build: PASS (existing Vite configuration/chunk-size warnings).
- Scenario/playback/test workflow contracts: 23 PASS, 0 FAIL.
- Real backend fusion/incident/privacy/duplicate/notification tests: 16 PASS, 0 FAIL.
- Shared-canvas Acoustic/Fusion/SOS browser regressions: 18 PASS, 0 FAIL. Includes actual registered recorded YAMNet inference, incident reuse, reset, notification Disabled/API Accepted/Failed/unknown rendering and duplicate-send prevention. The Telegram transport is mocked in this suite; no real delivery or receipt is claimed.
- Broad dashboard browser regressions: 29 PASS, 0 FAIL. Includes original layout, six scenarios, recorded radar/acoustic inference, map/Alerts/Review navigation, staff response persistence and privacy.
- Real Chromium + FastAPI + SQLite scenario synchronization suite: 17 PASS, 0 FAIL. Covers natural completion, pause/resume, final-frame seek, restart, Normal, Possible Fall, SOS, acknowledgement, explicit resolution, cached resolved replay, missing hardware and one unchanged canvas.

Screenshots under `runtime/private-risk-completion/`: `resolved-replay-start.png`, `resolved-replay-falling.png`, `resolved-replay-completed.png`, `before-completion.png`, `after-completion.png`, `normal-presence.png`, `sos-lighting.png`, and `radar-unavailable.png`. Machine-readable results are in `results.json` in that directory.

Tests use isolated SQLite and explicitly simulated scenarios, plus registered recorded inputs where supported. Live radar/acoustic hardware and real Telegram receipt are unverified. The completion suite disables external Telegram sends. No private CCTV, speech recording/transcription or identifiable human reconstruction was added.

Validation fixes: the old shared-scene browser assertions expected “Possible fall”/“impact”; they now assert the required explicit simulation labels. A screenshot rerun also exposed an obsolete timing assumption: immediate backend SOS incident creation does not imply that the visual timeline has reached its five-second SOS cue. The browser test now waits for that independent visual phase before pausing and checking CRITICAL. These intermediate assertion failures were corrected before the final reruns.
