# Real TEST SOS Telegram Results

Date: 30 October 2026, Asia/Singapore. Stored incident timestamps remain UTC.

## Actual result: PASS

One confirmed **Test SOS was pressed in the existing running Dashboard**. It followed the existing `/event` -> FastAPI -> SQLite incident -> notification worker -> Telegram Bot API path. This was a real Telegram API call, not a mocked transport or standalone PowerShell send.

| Actual response/evidence | Result |
| --- | --- |
| Dashboard POST /event | HTTP 200 |
| Backend environment | Root .env loaded; TELEGRAM_MODE=test; both credentials present |
| Authorized route | TEST-only test_operator; no invented real teacher identity |
| SQLite incident | 010a8dde-5c59-482e-86b9-88dbd8b3a5d3 |
| Telegram HTTP response | **200** |
| Telegram API ok | **true** |
| Telegram message ID | **5** |
| Notification attempts | **1** |
| Accepted messages for this incident | **1** |
| Duplicate event identity | Suppressed; same incident, no second notification |
| Telegram/API errors | **None** |
| Production/staff dispatch | Disabled |
| Recipient phone receipt | Not independently confirmed; API acceptance is not a read/delivery receipt |

The same incident was read back after testing. It still has one notification, message ID 5. No second real test message was sent to verify the display.

## Configuration completed

- Preserved the saved bot-token and Chat-ID values in the project-root `.env`; neither was printed, returned to React or placed in source code.
- Configured `SAFESENSE_STAFF_ROUTES` to the private local `staff-routes.json`.
- Added an explicit `Authorized Telegram TEST recipient` route for `ZONE_TOILET_BLINDSPOT`, role `test_operator`, active=true, test_only=true. It refers to `TELEGRAM_TEST_CHAT_ID` by environment-variable name, not a copied Chat ID.
- A TEST-only operator is eligible only in test mode for non-live test provenance. It cannot route live-source or production/staff notifications. Existing teacher/duty_teacher authorization remains for real private-area staffing.
- Kept `TELEGRAM_STAFF_DISPATCH_ENABLED=false`.
- Verified `.env` and `staff-routes.json` are covered by the existing `.gitignore` rules.
- Safely restarted the idle owned FastAPI process to load the saved configuration; the AI service was not interrupted.

## Application changes

- `backend/notifications.py`: TEST-only authorized operator routing; persist actual Telegram HTTP status and API ok flag, without exposing credentials/recipient IDs.
- `scripts/test_telegram_dispatch.py`: existing backend-only CLI recognizes the authorized TEST operator route. The CLI was not used to create an additional real message during this verification.
- `dashboard/src/components/incidents/IncidentEvidence.tsx`: displays actual Telegram HTTP code, ok flag, message ID and error code when recorded; missing historical values are not invented.
- `tests/test_telegram_verified_workflow.py`: regression test proving a TEST operator can send a test SOS but cannot become a live/staff route.
- `.env`: local routing path and production-dispatch=false setting; existing credentials preserved (private/ignored).
- `staff-routes.json`: local TEST-only route (private/ignored).
- `TELEGRAM_REAL_SOS_RESULTS.md`: this report.
- Prior integration/diagnosis reports received a current-result link; earlier failure evidence remains historical.

## Verification

- **18 notification workflow tests PASS**, including recipient/nonce authorization, retries, privacy, idempotency and the TEST-only operator restriction. These regression transports are mocked/disabled; they send no extra real messages.
- **65 existing backend regressions PASS**.
- **TypeScript and production build PASS**. Existing Vite configuration/large-bundle warnings remain.
- Real browser confirmed the Dashboard result and incident dossier, with zero browser errors.
- Dashboard now visibly shows **Telegram HTTP 200 / API ok: true / Message ID: 5**.
- Built frontend assets checked against the actual configured token and Chat ID: neither appears in the assets. Values were compared privately, not printed.
- All **708 pre-existing SQLite record body hashes remained unchanged**. The authorized test added five records: event, incident, notification request, notification attempt and idempotency claim. Existing records were not deleted or replaced.
- No Fight V2/V3, YOLO Pose weights/datasets, original room geometry, existing incident workflow, evidence retention or report exports were replaced.
- No private imagery/audio, personal names or recordings were sent. Only the existing operational metadata-only Telegram text was used.

## Evidence

- [Sanitized actual API and browser result](runtime/telegram-real-sos/real-dashboard-results.json)
- [Actual Test SOS outcome](runtime/telegram-real-sos/actual-test-sos-outcome.png)
- [Actual incident notification result](runtime/telegram-real-sos/actual-notification-api-result.png)
- [HTTP 200 / ok / message ID visible in Dashboard](runtime/telegram-real-sos/actual-http-response-display.png)

Screenshots were opened for visual inspection. The UI explicitly says receipt unconfirmed. No token, configured Chat ID or raw Telegram response body is included in these artifacts.

## Remaining distinction

Telegram accepted this alert. A confirmed device delivery/read receipt or authorized incoming acknowledgement was not obtained during this test. Normal authenticated Dashboard acknowledgement remains available. No additional real SOS was sent merely to test acknowledgement.
