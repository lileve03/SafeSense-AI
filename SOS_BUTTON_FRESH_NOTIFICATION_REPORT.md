# Actual SOS Test button notification fix

The user's SOS Test button was reusing the accepted incident `be588baa-5e91-4129-9aa1-84ef8e4c29db` and message **24** from 10:33 AM Singapore time. No new SOS Test event had been created. The earlier successful tests of messages 25 and 26 used other paths/runs and did not correct this button's saved request identity.

## Corrected behavior

A deliberate **Run SOS Test** click after API acceptance now gets a fresh SOS-specific request UUID, observation and incident. Other test identities are preserved. Playback, polling, Restart and uncertain/pending request retries reuse their existing identity. Reset Test State alone does not send anything. While Test Actions owns the scene, Guided Demo controls remain disabled; their handlers also preserve the existing test if invoked.

## Real result

- Actual browser button was seeded with the old accepted SOS Test session, then clicked once.
- New incident: `f26286f0-5b29-4f40-84da-32375c9dd903`.
- Authorized personal recipient: `***7365`.
- Real Telegram HTTP **200**, **ok=true**, matching recipient, message ID **27**.
- Accepted **3 November 2026, 1:48:07 PM Singapore time**.
- One SQLite notification attempt, verified again read-only. No second live message was sent to finish verification.
- The user explicitly confirmed **“Yes, message 27 arrived.”** This user confirmation is separate from automated receipt verification, which remains false.

## Validation and changed files

- `privateTestWorkflow.ts`: fresh SOS generation only after definite API acceptance; durable request IDs stay within the existing 80-character observation/session schema.
- `PrivateTestActions.tsx`: persist fresh SOS identity before I/O; clarify new explicit test versus replay/retry in notification tooltip.
- `GuidedPrivateDemo.tsx`: start/restart handlers preserve active Test Actions ownership.
- `tests/privateTestWorkflow.test.ts`: new explicit-click, uncertain-send, other-test identity and schema-size regressions.
- `tests/test_private_test_actions_browser.py`: deliberate new accepted SOS sends once; reset, disabled and unknown cases retain their protections.
- `tests/run_live_sos_button_refresh.py`: opt-in actual-button live test plus read-only verification of its existing send.
- This report and `runtime/sos-button-refresh/results.json`; production dashboard assets refreshed.

Final checks: **21 state/workflow tests PASS**, **19 browser regressions PASS**, TypeScript and production build PASS. Real button send and read-only SQLite verification PASS. No remaining product failure was observed.

Intermediate validation caught a too-long combined UUID (backend rejected it before any send); the request key now replaces the SOS-specific UUID instead of appending it. A live-test follow-up also incorrectly expected Guided Restart to be enabled; it was correctly disabled during Test Actions. The test was corrected without sending another live message. Neither issue is represented as an extra accepted Telegram send.

This policy supersedes earlier reports saying every repeated Run SOS Test click reuses the old incident. **A new intentional click after acceptance is a new test; playback and transport retries are not.** Credentials, authorized recipient, backend routing, Three.js avatars and AI models were not changed.
