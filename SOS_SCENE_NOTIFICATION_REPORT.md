# SOS scene and Telegram integration

## Root causes

SOS captured and froze the previous scenario's tracks in `sosTracks`. Switching from Normal Presence at its empty opening frame, or after recorded acoustic testing, captured zero tracks permanently. The renderer also disabled body animation and held the previous pose for SOS. There was no dedicated approach or press animation.

Notification status was tied to a durable incident, not to each playback. Guided Demo reuses its saved event/run IDs, and the backend correctly suppresses another send for an already accepted incident. An API Accepted badge could therefore describe an older send. The configured live backend is in TEST mode with real HTTPS, an active test-only route and personal recipient `***7365`; no group/staff fallback or credential change was needed.

## Changes

- `dashboard/src/components/private-area/trackingPlayback.ts`: dedicated simulation-only SOS path containing one anonymous `SOS01` track from the first frame through completion. Approaches the wall over four seconds, makes a short gesture around activation, and remains by the device. SOS Test now plays this same path and holds after seven seconds. Replay/Hardware never use this generator.
- `dashboard/src/components/private-area/AnonymousTrackingLayer.ts`: existing humanoid joints perform the illustrative reach; the existing avatar faces the device and has a SIM SOS label. No measured skeleton or radar identity attribution is claimed.
- `dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx`: enable the SOS body motion in the original single scene; highlight the physical SOS marker for guided SOS as well as Test Actions; use existing CRITICAL red room/ground/radar accents.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx`: concise simulation-only provenance label; people count continues to derive from synthetic tracks.
- `dashboard/src/components/private-area/GuidedPrivateDemo.tsx`: notification tooltip includes the linked incident's acceptance timestamp/message ID and explains that replay does not resend.
- `tests/privateTestPlayback.test.ts`: regression for SOS selected from an empty frame, one-person approach, gesture, persistence and reset.
- `tests/run_live_sos_scene.py`: explicit `--send-live` opt-in browser test against the real running dashboard/FastAPI. Sends one new authorized TEST SOS, checks actual Telegram response and SQLite linkage, acknowledgement, replay prevention and source-mode isolation. Default invocation sends nothing.
- This report; generated screenshots, sanitized result artifacts and dashboard build files were refreshed. Backend Telegram implementation and AI model files were unchanged in this task.

## Genuine live test

- Exact incident: `d7dea991-be53-45a6-8a08-86b938432061`.
- Telegram recipient: personal chat `***7365`; real Telegram response recipient matched the backend configuration exactly.
- Running mode: `TELEGRAM_MODE=test`; real HTTPS transport; staff dispatch disabled.
- Telegram HTTP **200**, API **ok=true**, message ID **26**.
- Accepted at **3 November 2026, 1:30:11 PM Singapore time** (05:30:11 UTC).
- SQLite contains one notification attempt. Pause, seek, completion and Restart retained the same incident/message ID without another send.
- Incident is ACKNOWLEDGED with an explicitly labeled automated integration TEST acknowledgement, not a claim of human arrival. The person and CRITICAL visuals remain.
- Recipient receipt of message 26 is **confirmed by the user**, who explicitly replied ?Yes, received message 26?. This human confirmation is recorded separately from automated Telegram receipt verification, which remains false; no backend receipt proof or staff acknowledgement was fabricated.

Sanitized evidence: `runtime/sos-scene-live/results.json`. Screenshots: `sos-start.png`, `sos-approach.png`, `sos-press-critical.png`, `sos-completed.png` in that directory.

## Validation

- State/playback/workflow contracts: **25 PASS, 0 FAIL**.
- Backend Telegram workflow regression: **25 PASS, 0 FAIL** (explicitly mocked transport for unit tests).
- Genuine live browser SOS integration: **9 PASS, 0 FAIL**. Includes avatar/people count, visible gesture, CRITICAL lighting, new incident, real API request/recipient, acknowledgement, completion/restart deduplication, Replay/Hardware isolation and original one-canvas preservation.
- Shared-scene Acoustic/Fusion/SOS browser regressions: **18 PASS, 0 FAIL**. Registered recorded acoustic inference, fall animation, SOS Test, reset, notification state rendering and duplicate prevention remain functional. This separate regression suite explicitly mocks Telegram; only the genuine live test above establishes real API acceptance.
- TypeScript and production build: **PASS**. Existing Vite configuration/bundle-size warnings remain.

For an intentionally new Telegram test, use the existing **Demo workflow → Prepare new guided exercise**, then Play. Restart and repeated playback intentionally reuse the current incident. API Accepted means Telegram accepted the request; recipient receipt remains a separate fact.
