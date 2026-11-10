> **Current update ? 30 October 2026:** Authorized TEST routing is configured. The real Dashboard Test SOS received Telegram HTTP 200, ok=true, message ID 5; one attempt/accepted message, no API errors. Phone receipt remains unconfirmed. See [TELEGRAM_REAL_SOS_RESULTS.md](TELEGRAM_REAL_SOS_RESULTS.md). The earlier configuration failures below are historical.

# Telegram Integration Results

Date: 30 October 2026, Asia/Singapore.

## Actual outcome

The existing FastAPI/SQLite notification system was extended in place. No duplicate bot, incident database or application was built. **Actual Telegram API sending and recipient receipt remain NOT TESTED because local configuration is missing. Sending remains disabled; zero external messages were sent.**

Actual running backend readiness:

- `TELEGRAM_MODE=disabled`, `status=NOT_CONFIGURED`.
- Missing `TELEGRAM_BOT_TOKEN`, `TELEGRAM_TEST_CHAT_ID`, and an active private-zone teacher/duty_teacher route via `SAFESENSE_STAFF_ROUTES`.
- No local `.env` file was present during the check.
- Optional reply verification also needs `TELEGRAM_TEST_ACK_USER_IDS` configured before sending.

[Actual readiness, secret-marker checks and data preservation](runtime/telegram-integration/actual-results.json).

## Reused functionality

Inspected and reused `backend/main.py`, `backend/storage.py`, `backend/notifications.py`, `staff-routes.example.json`, `scripts/start_services.py`, the existing backend test CLI, incident acknowledgement/review endpoints and shared Dashboard evidence/report components.

Existing staff selection respects zone, active/on-duty roster, shift times, backup ordering and teacher roles for private areas. Existing trusted-live-ingestion checks remain: dashboard/test/research events cannot impersonate verified live sources or reach staff recipients. Test/replay events use the authorized TEST chat only; no staff fallback exists.

## Implemented changes

### Backend-only credentials and test action

- Bot token, authorized chat IDs and optional authorized test-user IDs remain backend environment values. No React credential inputs or bot API calls were added.
- The service launcher now strips every `TELEGRAM_*` value and the trusted-ingestion secret from the dashboard process environment.
- Existing `.gitignore` excludes `.env`, `.env.*` other than the blank example, the default private staff routing file and runtime artifacts. No actual credentials were written to source, logs or browser results.
- Existing authenticated `POST /incidents/{id}/notify-test` remains the Send Test action. It forces TEST routing, uses the same incident and never returns bot credentials, raw chat IDs or receipt nonce hashes.
- The existing `scripts/test_telegram_dispatch.py` provides read-only readiness by default, explicit `--send-test` and optional `--verify-receipt --incident-id ...`.

### Automatic incident notifications and policy

Confirmed private SOS still saves its incident first, assigns the existing configured on-duty teacher route and queues notification through the existing bounded worker. Sending requires explicit configured mode and recipient.

Policy for automatic sends:

- CRITICAL incidents, including SOS, are eligible.
- Private radar/acoustic corroboration requires HIGH; single private OBSERVE signals are suppressed.
- Public vision incidents use `TELEGRAM_PUBLIC_AI_MIN_SEVERITY` (default OBSERVE, preserving existing whole-clip candidate notifications; set HIGH for a stricter policy).
- Explicit authorized test actions can preview/test an existing incident independently of the automatic severity threshold.
- Simulation/research/recorded results remain TEST notifications, never live staff delivery. Staff mode additionally requires `TELEGRAM_STAFF_DISPATCH_ENABLED=true` and verified live provenance.

### Privacy-safe message content and links

Messages contain incident ID, canonical zone, event type, source/provenance, timestamp, severity and current incident status. They omit free-form incident/review text, assigned-person names, filenames, raw sensor data and all image/video/audio attachments. This prevents private-area personal information leaking through arbitrary descriptions.

No View Incident link is included: the current local dashboard does not provide a verified externally accessible authenticated incident URL. No API token or local unauthenticated URL is embedded in Telegram. Staff can use the existing authenticated dashboard workflow. Remote authenticated portal/login deployment was not invented or claimed.

### Persistent idempotency and bounded retries

- SQLite `notification_claim` records use the existing generic records table, keyed by incident, transport mode and authorized-recipient fingerprint. `BEGIN IMMEDIATE` claims persist intent before network I/O and protect against concurrent sends, restarts, manual repeats and severity changes. No new database/schema migration is needed.
- An API-accepted or ambiguous attempt is not automatically resent. A timeout/upstream 5xx is UNKNOWN rather than assumed failure; Telegram sendMessage has no client idempotency key guaranteeing safe blind retries.
- At most three network attempts per delivery key. Explicit 429 rejections with short delays (up to two seconds) can retry automatically, respecting `retry_after`; longer delays are persisted without shortening and need a later explicit retry. Explicit permanent rejections do not loop automatically. Every actual attempt and next eligible retry time is saved.
- Closed incidents do not send. Queued snapshots recheck persisted closure. Already accepted messages are not resent merely to obtain a new receipt code.

### Truthful states and verified test acknowledgement

| Display/API state | Meaning |
| --- | --- |
| DISABLED | Configuration/mode/policy/assignment prevents sending |
| PENDING | Queued or transport processing; no success inferred |
| API_ACCEPTED | A valid Telegram success response supplied a message ID; recipient receipt remains unconfirmed |
| FAILED | Explicit rejection; attempt/retry metadata retained |
| UNKNOWN | Network/upstream ambiguity; automatic resend blocked |
| RECEIPT_CONFIRMED | An authorized Telegram TEST user returned the correct one-time command through authenticated bot updates |

The legacy stored `SENT` status is retained for existing consumers, with a separate normalized `delivery_state`. Legacy SENT is displayed as API acceptance, never recipient delivery. Existing records are not rewritten just to rename statuses.

Telegram documents that successful `sendMessage` returns a Message; this is the basis for API_ACCEPTED, not proof of recipient reading. [Official sendMessage documentation](https://core.telegram.org/bots/api#sendmessage).

Optional receipt verification sends a random one-time code only to the TEST chat. Preview/API reports redact the code and omit its hash. The recipient replies:

`/safesense_ack <one-time code>`

The authenticated backend `POST /incidents/{id}/verify-test-receipt` fetches updates through the bot's authenticated HTTPS API. It validates the configured chat, an explicitly authorized numeric Telegram user ID, active matching teacher/staff assignment and nonce hash, rejecting forwarded/incorrect/spoofed input. Request-body fake updates are ignored; only the backend's Telegram API response is considered. No unauthenticated webhook or callback button was added. [Official getUpdates documentation](https://core.telegram.org/bots/api#getupdates).

Only after that explicit proof does the backend record receipt confirmation and invoke the existing acknowledgement function for a test incident. It never reopens closed incidents or automatically acknowledges real production incidents from a TEST reply. Receipt verification is idempotent; it can also resolve an UNKNOWN send using a genuine authorized reply without retransmission or inventing an API message ID.

Receipt confirmation means an authorized user explicitly replied with the message's code, not a native device delivery/read receipt. A dashboard acknowledgement alone never confirms Telegram receipt.

## Real setup and test procedure

Configure values locally using the existing `.env.example` and `staff-routes.example.json`. Do not paste secrets into React, chat or logs. Keep the real `.env` and `staff-routes.json` private/ignored.

Required backend environment:

```text
TELEGRAM_MODE=test
TELEGRAM_BOT_TOKEN=<actual bot token, stored locally only>
TELEGRAM_TEST_CHAT_ID=<authorized numeric test chat ID>
SAFESENSE_STAFF_ROUTES=<absolute path to private routing JSON>
TELEGRAM_STAFF_DISPATCH_ENABLED=false
```

For optional reply verification, also set `TELEGRAM_TEST_ACK_USER_IDS` to comma-separated numeric IDs of explicitly authorized test staff. Configure it BEFORE sending so the message includes a receipt code. The routing JSON must contain the real authorized on-duty teacher/duty_teacher for `ZONE_TOILET_BLINDSPOT`; placeholder inactive example routes do not authorize sending. No staff/chat identities were invented in the actual configuration.

Reload services through the existing launcher after environment changes. Use the current authenticated incident dashboard for normal acknowledgement. Backend CLI commands from the repository root:

```powershell
.venv/Scripts/python.exe scripts/test_telegram_dispatch.py
.venv/Scripts/python.exe scripts/test_telegram_dispatch.py --send-test
.venv/Scripts/python.exe scripts/test_telegram_dispatch.py --verify-receipt --incident-id <incident-id>
```

The send action refuses missing transport/teacher configuration before creating a test incident. With valid configuration it creates a new explicit private TEST SOS, queues the existing notification and records only actual API acceptance. The recipient must confirm via the nonce command and the backend verification action, or separately acknowledge through the authenticated dashboard. `real-test-results.json` / `real-receipt-results.json` are written only by actual requested CLI stages; no such real delivery evidence was fabricated here.

Reply verification is optional polling for a dedicated test bot. It does not install or remove webhooks, consume arbitrary updates with offsets, or replace another bot service. Existing webhooks/conflicting pollers or more than the first 100 pending updates can prevent this check; such cases remain unconfirmed. Production inbound Telegram acknowledgement and a production identity provider are outside this local MVP.

## Actual test results

| Check | Result | Actual scope |
| --- | --- | --- |
| New FastAPI/SQLite notification workflow tests | PASS: 17 | Mocked Telegram HTTPS only |
| SOS -> incident -> route -> API acceptance | PASS | Real backend/SQLite, fake Telegram response |
| Authorized reply -> receipt -> acknowledgement | PASS | Chat/user/nonce/route checks against fake Telegram update |
| Wrong chat/user/nonce, unsigned body, revoked route | PASS | No receipt or acknowledgement |
| Duplicate event/manual send/severity change/concurrency | PASS | One network call per delivery key |
| Pending vs accepted vs unknown vs failed | PASS | No false success from timeout or 5xx |
| Safe 429 retries and two-day retry_after | PASS | Three-attempt cap; long retry time retained |
| Private message allowlist/redaction | PASS | No names, free text, files, audio, media, raw chat IDs or secrets exposed |
| Frontend service environment isolation | PASS | Telegram and ingestion secrets removed |
| Existing backend regressions | PASS: 65 | Existing model/queue/incident/privacy/notification checks |
| Real-browser workflow | PASS: 2 | Explicit mock transport; acceptance/receipt labels, SOS acknowledgement and Reports sync |
| TypeScript | PASS | npm run lint / tsc --noEmit |
| Production build | PASS | Existing Vite config/large-bundle warnings remain |
| Built frontend secret-marker scan | PASS | No test token or credential assignment markers |
| Actual dashboard disabled-mode/readiness | PASS | Missing setup displayed, authenticated status required |
| Existing user data | PASS | All 696 record body hashes unchanged; original 73 incidents preserved |
| Real Telegram API send | NOT TESTED | Bot token/chat/route not configured |
| Actual authorized recipient receipt | NOT TESTED | No real message sent |
| Actual teacher acknowledgement from Telegram | NOT TESTED | Only declared test fixtures/mocked updates exercised |

No FAIL results remained in executed application tests. Missing real transport setup is recorded as NOT TESTED, not converted into a success claim. No external message was sent during this work.

## Screenshots / evidence

- [API accepted, receipt explicitly unconfirmed — mock transport](runtime/telegram-integration/browser/api-accepted-receipt-unconfirmed.png)
- [Authorized test reply confirmed — mock transport](runtime/telegram-integration/browser/verified-test-reply-acknowledged.png)
- [Actual dashboard disabled/missing setup](runtime/telegram-integration/actual-disabled-configuration.png)
- [Browser PASS results with mock labels](runtime/telegram-integration/browser/results.json)
- [Actual readiness and unchanged-record verification](runtime/telegram-integration/actual-results.json)

Acceptance and receipt screenshots were opened for visual inspection. The fixture teacher/chat shown in isolated tests is not a claim of an actual recipient. The actual application remains disabled with no recipient configured.

## Modified files

- `backend/notifications.py`: policy, private-message allowlist, atomic claims, retries, truthful states and verified TEST reply logic.
- `backend/main.py`: pending/shared state, redacted notification reports and authenticated receipt/ack action.
- `scripts/start_services.py`: strip backend-only secrets from dashboard child environment.
- `scripts/test_telegram_dispatch.py`: reuse backend-only explicit SOS test, acceptance and receipt evidence.
- `.env.example`: backend-only receipt allowlist and public AI severity policy configuration.
- `dashboard/src/lib/notificationState.ts` (new): clear acceptance/receipt labels.
- `dashboard/src/lib/api.ts`: shared notification state labels.
- `dashboard/src/components/incidents/IncidentEvidence.tsx`: status/setup guidance and authenticated verification action.
- `dashboard/src/components/incidents/IncidentReportView.tsx`: consistent summary status.
- `tests/test_telegram_verified_workflow.py` (new).
- `tests/test_telegram_browser_workflow.py` (new).
- `tests/telegram_browser_backend.py` (new; isolated mock server only, never production).
- `TELEGRAM_INTEGRATION_RESULTS.md` (new).

Generated runtime evidence and dashboard/dist assets are updated. No AI weights, datasets, original room geometry, dashboard layout, evidence records or database schema was replaced. SQLite claims reuse the existing generic records table. Existing `.env`/private routing values were not created, changed or exposed.
