# Telegram test notification setup

Actual delivery uses the official [Telegram Bot API sendMessage](https://core.telegram.org/bots/api#sendmessage). There are no fake successful sends. No message was sent during automated verification; the transport safety tests use a mock.

1. Create your bot and obtain its token through Telegram's BotFather. Start the bot from a test account/chat you explicitly authorize.
2. Copy `.env.example` to `.env`. Set TELEGRAM_MODE=test, TELEGRAM_BOT_TOKEN and TELEGRAM_TEST_CHAT_ID to your authorized test values. Do not paste tokens into source code, screenshots or chat.
3. Copy `staff-routes.example.json` to private `staff-routes.json`. Set actual zone/staff assignments and active=true only for authorized on-duty staff. Private routes require role teacher or duty_teacher. `chat_id_env` references a server environment variable, rather than storing a chat ID in the routing JSON. Optional shift_start and shift_end are timezone-aware ISO timestamps; both must be supplied together. Without timestamps, active is the operator-maintained current roster. An active is_backup route is selected if no primary is on duty. No staff locations are inferred.
4. Set SAFESENSE_STAFF_ROUTES to that JSON's absolute path. Restart the launcher. Inspect `/notifications/status` through the authenticated dashboard: READY_TEST_ONLY means configuration exists, not that delivery has been verified.
5. In Scenario Test Library, run Telegram TEST dispatch, or open an incident and choose Send to configured authorized TEST chat. Verify the actual message in that chat and check SENT/message ID in incident history. No evidence files, imagery or conversation recordings are attached.

Every non-Low candidate, including public AI review candidates, queues an attempt automatically without claiming a confirmed emergency. Private SOS queues immediately and selects an on-duty teacher independently of the vision models. An active zone assignment is required. All simulated incidents, dataset replays and recorded real-video analyses can send only to TELEGRAM_TEST_CHAT_ID, even when staff delivery is enabled. Missing test-chat configuration never falls back to a staff recipient.

## Configured staff delivery

This code path is implemented but remains disabled on the running demonstration. Enable it only after explicitly authorizing the real recipients and configuring your actual duty roster:

1. Set TELEGRAM_MODE=staff and TELEGRAM_STAFF_DISPATCH_ENABLED=true. Both are required.
2. Set TELEGRAM_SECURITY_CHAT_ID / TELEGRAM_TEACHER_CHAT_ID or your own TELEGRAM_*_CHAT_ID variables. Reference their variable names from the corresponding route's chat_id_env. Never use a test chat as an implicit fallback for an unconfigured staff route.
3. Use real authorized live-camera/sensor/SOS input with source_type LIVE CAMERA, LIVE SENSOR or LIVE SOS, processing_mode real_model and is_test=false. The backend additionally requires a **server-only** X-SafeSense-Ingest-Token header matching SAFESENSE_INGEST_TOKEN. Dashboard credentials alone cannot authorize a live event eligible for staff delivery.
4. The launcher generates a shared random ingestion key for backend/inference when none is supplied. For external sensor adapters or manually launched services, securely configure the same server-only SAFESENSE_INGEST_TOKEN yourself. Never expose it through a VITE_ variable. Existing vision ingestion passes it server-to-server automatically.
5. Restart services after configuration changes. READY_STAFF indicates configured transport, not proven physical camera connectivity or verified delivery. Observe actual SENT/message ID or failure history for each incident.

Staff delivery uses the selected on-duty public-zone recipient or private-zone teacher. Failed/unconfigured/off-duty routes remain visible. A backup is not contacted after an uncertain network timeout because the primary may already have received the message. Staff chat IDs, bot tokens and ingestion keys are never returned in status/report responses. Local demo access controls still lack production identity roles and TLS; enabling real staff delivery does not make this a production-certified emergency system.

Statuses include DISABLED, NOT_CONFIGURED, NO_ACTIVE_ASSIGNMENT, STAFF_DISPATCH_NOT_AUTHORIZED, SENDING, SENT, FAILED, DELIVERY_UNKNOWN and CANCELLED_CLOSED. Pending requests are persisted before bounded background delivery and recovered after restart. Successful/in-flight/unknown attempts suppress duplicate sends across restarts by incident, mode, recipient fingerprint and severity. A higher severity can generate an updated alert. HTTP rejections are recorded as FAILED; up to three rejected attempts are allowed. Network uncertainty is not retried automatically. Exception strings containing token-bearing URLs are never persisted.

Staff acknowledge in the authenticated local dashboard or Reports → incident → Response, then provide a resolution note. Acknowledgement, delivery and resolution are distinct records. Closed incidents cannot be reopened through review. Telegram callback buttons/webhook authentication are not implemented. No localhost incident link is sent because it would not be reachable by remote staff. Actual Telegram receipt remains NOT TESTED until authorized credentials are configured.

To explicitly verify your authorized test chat after configuration:

```powershell
.\.venv\Scripts\python.exe scripts\test_telegram_dispatch.py
.\.venv\Scripts\python.exe scripts\test_telegram_dispatch.py --send-test
```

The first command inspects configuration without sending. The second creates an explicitly simulated private SOS and requests TEST-chat delivery only. Telegram acceptance is recorded; verify actual receipt yourself in that chat. Automated suites mock this transport and never send staff messages.
