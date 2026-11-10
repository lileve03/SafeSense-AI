# Private Area Test Actions

The unified Private Area page now includes Run Acoustic Test, Run SOS Test, Run Fusion Test and Reset Test State below Scenario Controls, with concise result chips and a Test Summary.

| Action | Behavior |
| --- | --- |
| Acoustic | Uses actual YAMNet inference on the registered scream recording when its input/model is ready. Otherwise submits a metadata-only `SIMULATED ACOUSTIC TEST` through the existing normalized observation endpoint. Shows Not Tested / Running / Passed / Failed and the backend-detected scream, impact or none. A failed real inference does not silently become simulation. |
| SOS | Submits a labeled TEST help request through the existing canonical observation → event → incident → notification queue workflow. The toolbar SOS confirmation and Test Actions button share the same saved request. Shows Triggered, Incident Created, and a separate notification chip. |
| Fusion | Submits synthetic radar fall + acoustic impact in one zone/run with one capture timestamp. PASS requires actual backend HIGH corroboration and the same incident ID for both signals. Unrelated recordings are not combined. |
| Reset | Clears displayed test statuses while retaining request IDs, observations and recorded-job IDs. It does not delete SQLite incidents or trigger another notification. |

SOS summary PASS means a CRITICAL TEST incident was created, independently of Telegram delivery. Notification chips distinguish Pending, Notification unavailable, API accepted, Failed and Acceptance unknown. API acceptance never establishes recipient receipt. Receipt confirmed is shown only when the backend report contains receipt evidence. The toolbar badge follows the selected SOS test state.

Stable per-action request IDs are saved before submission. Repeated clicks, reset, navigation/reload and polling reuse those IDs. Recorded acoustic retries reuse the completed inference job. Incident links use canonical backend IDs, and passive status polling does not send notifications.

## Actual verification

| Suite | Result |
| --- | --- |
| Test workflow contracts | PASS — 14 tests: real/simulated branches, missing/negative detections, strict event identity, fusion rejection, reset/retry IDs, SOS phases, missing incident, pending/disabled/failed/unknown notification handling and receipt evidence |
| New real Chromium + FastAPI + SQLite integration | PASS — 13 checks |
| Existing complete Private Area browser regression | PASS — 29 checks |
| Existing backend scenario/fusion/privacy/deduplication tests | PASS — 16 tests |
| TypeScript | PASS |
| Production Vite build | PASS |

The browser executed fresh YAMNet inference against the registered recording. It also exercised simulated acoustic fallback, timestamp-compatible HIGH fusion, SOS incident creation/linking, toolbar/card deduplication, reset/reload persistence and failure rendering.

Telegram HTTPS was explicitly mocked in the new browser fixture while the real backend queue, API reports and SQLite were exercised. No external Telegram message was sent during this work; actual recipient receipt is unverified. Physical radar, acoustic hardware, GPIO and calibration remain unverified. No camera, microphone capture, speech transcription or identifiable reconstruction was added.

Evidence:

- `runtime/private-test-actions/browser-results.json`
- `runtime/private-test-actions/accepted.png`
- `runtime/private-test-actions/failed.png`
- `runtime/private-test-actions/unknown.png`
- `runtime/part4-private/browser-results.json`

## Changed files

- `dashboard/src/components/private-area/PrivateTestActions.tsx` — test card, summary, persistent state, status polling and incident links.
- `dashboard/src/components/private-area/privateTestWorkflow.ts` — action orchestration, result validation, notification labels and reset semantics.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx` — integrate the card, selected incident and shared toolbar SOS entry point.
- `dashboard/src/components/private-area/GuidedPrivateDemo.tsx` — show the selected test's notification state in the toolbar.
- `tests/privateTestWorkflow.test.ts` — workflow contract coverage.
- `tests/private_test_actions_backend.py` — isolated real-backend fixture with controlled capability availability and mocked Telegram transport.
- `tests/test_private_test_actions_browser.py` — browser/backend/model integration checks.
- `PRIVATE_AREA_TEST_ACTIONS_REPORT.md` — this report.

The production bundle was regenerated under `dashboard/dist`. Production backend routes, fusion rules, notification routing and SQLite schemas were not changed.
