# Incident response workflow

The workflow is integrated with the existing models, privacy-safe private room and shared incident state:

**Detection → permitted evidence → persistent incident → Digital Twin → assigned duty recipient → Telegram delivery attempt → staff acknowledgement → resolution note → organized report.**

## Detection, evidence and map

Real public video analysis retains the analyzed candidate interval before submitting its event. V2/V3 predictions stay whole-clip classifications; YOLO contributes real person pose overlays and experimental fall-rule timestamps. Incidents retain model versions, scores, source/provenance, actual media references and review reasons. Private radar/acoustic/SOS events retain metadata only. No private images, video, raw audio or speech are captured.

Public AI candidates remain unverified human-review items but now queue a duty-staff notification attempt automatically. SOS queues immediately without depending on vision. Backend incidents, active zone IDs and dashboard polling supply the same state to Alerts, Incident Review, Digital Twin and Reports.

## Staff routing and safe Telegram delivery

See TELEGRAM_SETUP.md and the inactive `staff-routes.example.json`. The live Telegram adapter sends actual `sendMessage` requests only after configuration. Routes are by zone, role and active shift, with an optional backup. Private routes require a teacher/duty_teacher. Optional shift_start/end use timezone-aware ISO timestamps. No nearest-staff locations or automatic availability are invented.

- Default: TELEGRAM_MODE=disabled; honest local previews and disabled attempts, no sends.
- Test: TELEGRAM_MODE=test; all notifications go only to TELEGRAM_TEST_CHAT_ID, never a staff chat.
- Staff: TELEGRAM_MODE=staff plus TELEGRAM_STAFF_DISPATCH_ENABLED=true, configured recipient environment variables and on-duty routes. Only verified live-source incidents can reach staff recipients.
- Every recorded video, dataset replay, controlled simulation or explicit test request stays TEST-only even in staff mode. Missing test credentials never falls back to staff.
- A source eligible for staff delivery must specify is_test=false, processing_mode=real_model, a supported LIVE source_type and the server-only X-SafeSense-Ingest-Token. The launcher generates a shared server key for backend/inference; it is never exported through VITE_. The browser's demo credential alone cannot forge a staff-deliverable live incident.

Pending notification requests are stored before bounded background processing. Restart recovery resumes requests not yet attempted. Attempts record mode, assigned recipient name/role, timestamps, status, recipient fingerprint and actual Telegram message ID on acceptance. Chat IDs and tokens stay out of report/status responses. Successful/in-flight/uncertain attempts are deduplicated per incident, recipient, mode and severity; severity escalation can send an updated alert. HTTP rejection and unknown network delivery are distinguished. Unknown sends are not automatically retried.

## Acknowledge and resolve

Acknowledgement is a staff review action, not a Telegram delivery receipt. It preserves the first acknowledgement timestamp and actor and does not clear map risk. Assignment and reviewing actor remain separate. Resolution requires prior acknowledgement and a nonempty note, records its own actor/time, and removes that incident from active zone risk. False-alarm review is recorded separately. Closed incidents cannot be reopened by ordinary review actions. Notifications and all transitions persist in SQLite.

The dashboard shared token is local demo access control, not verified individual staff login. Telegram callback/webhook acknowledgements are not implemented; staff acknowledge through the dashboard. Enabling Telegram recipients does not supply production roles/TLS or emergency-service dispatch.

## Focused reports

Reports has three categories: Incident reports, Operational analysis, and Model evaluation. Each selected incident has four independent sections:

| Section | Contents |
|---|---|
| Summary | Actual incident reason, zone/time, severity/status, source/mode, assigned recipient and delivery state |
| Evidence | Retained video or private sensor metadata, model scores, source records and timestamps; unavailable clips are labeled |
| Response | Delivery attempts, acknowledgement/resolution actors and times, required resolution note, audit history |
| Analysis | Actual observations/model results and measured acknowledgement/resolution durations; model limitations |

CSV exports filtered actual incidents. Print / Save PDF prints the selected report section. Dataset model evaluation remains separate from operational incident statistics.

## Executed verification

- Actual-data/API/browser integration: **20/20 PASS**, including real model inference/evidence, map synchronization and report-based acknowledgement/resolution.
- Legacy model/API regressions: **36/36 PASS**.
- Existing temporal/sensor/privacy tests: **16/16 PASS**.
- Telegram routing/safety tests: **13/13 PASS**, using mocked HTTP only.
- Incident response/security/outbox tests: **10/10 PASS**, isolated SQLite and mocked Telegram only.
- TypeScript and production build: **PASS**.

That is 95 automated checks. Full actual-data results are in `runtime/real-monitoring-tests/results.json`; legacy/unit results are in `runtime/test-results`. Reproduce routing and workflow checks with:

```powershell
.\.venv-vision\Scripts\python.exe -m unittest discover -s tests -p test_notification_safety.py -v
.\.venv-vision\Scripts\python.exe -m unittest discover -s tests -p test_incident_response_workflow.py -v
```

**Actual Telegram receipt is NOT TESTED:** no authorized bot/test-chat credentials were configured by this work, and no real staff messages were sent. After explicit configuration, `scripts/test_telegram_dispatch.py --send-test` can exercise only the authorized test recipient. Physical live sensors/cameras and real on-duty staff availability remain unverified.

## Activated local verification

The updated services are active on 3000/8000/8001. Seven existing incidents and nineteen recent events were backed up to `runtime/session-backups/20261028T140855Z.json` and preserved before the verified SafeSense supervisor was restarted. On the normal dashboard, an explicitly simulated SOS was acknowledged and resolved through the new report, private evidence contained no media, and CSV export succeeded. Existing incidents were not resolved or removed by this check. Telegram stayed disabled/NOT_CONFIGURED, and the setup utility was run without --send-test to confirm that inspection does not send a message.

Evidence: `runtime/real-monitoring-tests/incident-response-activation.json`; screenshots: `response-report-summary.png` and `response-report-analysis.png` in that directory. The remaining real-delivery verification requires the user's authorized credentials and test recipient.
