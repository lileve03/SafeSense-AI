# Telegram SOS diagnosis and genuine live test

## Actual findings

The running FastAPI service loaded `TELEGRAM_MODE=test`, with staff dispatch disabled. The configured authorized recipient is a **personal chat, masked as `***7365`**, not a group. The on-duty `test_operator` route is active, test-only and selected for the private zone. No recipient or token was changed.

The SOS Test workflow stores its request/observation IDs in session storage. Reset Test State clears presentation while deliberately retaining those IDs. Repeating the test therefore reuses its SQLite event/incident and accepted notification; it does not create another Telegram send. The last saved SOS acceptance before this diagnosis was message ID **24**, at **2026-11-03 02:33:01 UTC**, for the same current authorized recipient (verified by hash comparison). That explains how the UI can continue showing API accepted without a new message appearing. The user's exact previously displayed browser session was not directly inspected, so historical non-receipt itself cannot be established from this evidence.

Existing records contained HTTP 200 and `telegram_api_ok=true`; the running backend used the production `backend.main:app` entrypoint. Browser/unit fixtures do mock Telegram explicitly on isolated ports and databases; they are not live-delivery evidence. The new live test below used the real `urllib.request` HTTPS transport in the running production backend.

## Genuine live result

- Result: **PASS**.
- Fresh backend-only request: `b697b712-6e0b-4ac5-84af-cd82152807af`.
- SQLite TEST SOS incident: `2a879ace-54e1-4285-a149-b052ef678248`.
- Authorized recipient: `***7365`; Telegram response chat matched the configured recipient exactly inside the backend.
- Telegram HTTP status: **200**; API `ok`: **true**.
- Telegram message ID: **25**, accepted **2026-11-03 05:16:53 UTC**.
- Persisted notification attempts: **1**. Retrying the same request ID returned message 25 without sending another message.
- Receipt: the user explicitly replied **“Yes, message received”**. This is user-confirmed receipt, separate from backend receipt verification. Automated Telegram reply/nonce verification is not configured and the backend `receipt_confirmed` remains false; no staff acknowledgement or receipt proof was fabricated.

Sanitized live evidence: `runtime/telegram-integration/real-test-results.json`.

## Changes

- `backend/main.py`: authenticated backend-only `POST /notifications/send-test`, requiring `authorized=true`, a UUID request ID, running TEST mode and an authorized route. A fresh UUID creates one clearly labeled TEST SOS; the same UUID remains idempotent. It reuses the existing event, SQLite incident and notification paths.
- `backend/notifications.py`: masked recipient/process/transport diagnostics; record HTTP/API/message and returned-recipient-match evidence; mismatch is UNKNOWN. Legacy SENT labels without `ok=true` and a valid message ID no longer imply API acceptance. Logs contain masked recipient, message ID and state, never token/full recipient/payload.
- `scripts/test_telegram_dispatch.py`: uses the new action with real-transport guard, saves its request ID before I/O, supports `--request-id` retries and prints only sanitized evidence. Receipt checking remains separate.
- `dashboard/src/components/private-area/privateTestWorkflow.ts`: requires API response evidence before rendering API accepted; preserves acceptance time/message ID for provenance.
- `dashboard/src/components/private-area/PrivateTestActions.tsx`: tooltips explain cached acceptance and that SOS Passed means incident creation; no extra frontend send button, token or recipient field.
- `tests/test_telegram_verified_workflow.py`, `tests/privateTestWorkflow.test.ts`: explicit authorization, test-only routing, request deduplication, missing/fake acceptance evidence and recipient-mismatch regressions.
- This report and sanitized runtime evidence. Existing Three.js scene, SOS visuals, incidents and AI model code were preserved. The existing supervisor stopped its dashboard/model children after the backend restart; those services were restored using their original commands and ports.

## Validation

- Verified Telegram backend workflow: **25 PASS, 0 FAIL** (explicitly mocked HTTPS for unit tests).
- Environment loading: **4 PASS, 0 FAIL**.
- Notification safety: **13 PASS, 0 FAIL**.
- Frontend test workflow: **15 PASS, 0 FAIL**.
- Real Chromium shared-scene Acoustic/Fusion/SOS regressions: **18 PASS, 0 FAIL**. HTTPS is explicitly mocked in this suite; it is not the genuine live test above.
- TypeScript and production build: **PASS**; existing Vite configuration/bundle-size warnings remain.
- An intermediate safety assertion caught an unnecessary retry-only response field. It was removed to preserve stable idempotent responses; the final safety suite passed.

HTTP error handling remains explicit: definite rejection is FAILED; only bounded, definite 429 rejection may retry (maximum three attempts, honoring retry_after). Ambiguous timeout/5xx remains UNKNOWN without blind resend. Accepted or pending SQLite claims prevent duplicate transmission. Configured means credentials are present; API Accepted requires Telegram response evidence; Delivery Verified requires a separate receipt signal.

To deliberately send a future fresh authorized test from the backend: `.venv\Scripts\python.exe scripts/test_telegram_dispatch.py --send-test`. This sends a real message. Reuse the saved UUID via `--request-id <uuid>` when retrying an interrupted request instead of generating another send.
