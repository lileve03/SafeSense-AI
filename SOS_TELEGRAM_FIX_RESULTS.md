> **Current update ? 30 October 2026:** Authorized TEST routing is configured. The real Dashboard Test SOS received Telegram HTTP 200, ok=true, message ID 5; one attempt/accepted message, no API errors. Phone receipt remains unconfirmed. See [TELEGRAM_REAL_SOS_RESULTS.md](TELEGRAM_REAL_SOS_RESULTS.md). The earlier configuration failures below are historical.

# SOS to Telegram - Exact Integration Diagnosis and Fix

Date: 30 October 2026, Asia/Singapore.

## Observed failure

The user's successful direct PowerShell send is accepted as evidence that those credentials work in that PowerShell context. The SafeSense failure was earlier in the application pipeline: **the running FastAPI process had TELEGRAM_MODE=disabled, no bot/test-chat credentials, zero staff routes and no project .env file.** Its notification service intentionally returned DISABLED before attempting Telegram HTTPS. This was not an observed Telegram rejection or a SQLite failure.

The user's two recent actual incidents prove this:

| Existing SOS incident | Saved state | Notification | API message ID |
| --- | --- | --- | --- |
| 0ebbae3f-4c85-4dfd-8ecd-8f3cc11a9dab | CRITICAL / NEW, source sos_button | DISABLED | absent |
| 7619496f-8331-409d-931a-1a8323e29997 | CRITICAL / NEW, source simulation | DISABLED | absent |

Both have no assigned staff. Their existing records were inspected, not fabricated or deleted. [Actual prior-SOS trace](runtime/sos-telegram-diagnosis/existing-sos-trace.json).

## Actual request and handler

Prominent private-room button: `PrivateAreaMonitoringView.tsx` -> `handleSosTrigger` -> confirmation -> `handleConfirmLiveTestSos` -> authenticated **POST /event**.

Its body uses zone `ZONE_TOILET_BLINDSPOT`, type `sos`, source `sos_button`, processing_mode `simulation`, source_type `SIMULATION`, is_test true and a stable UUID event_id. The actual browser request, excluding headers/credentials, is saved in [actual-dashboard-trace.json](runtime/sos-telegram-diagnosis/actual-dashboard-trace.json).

FastAPI: `backend/main.py:create_event` -> existing zone/privacy validation -> CRITICAL assessment -> existing SQLite event/incident persistence -> existing teacher routing -> `queue_notification` -> `backend/notifications.py:dispatch`.

The current failure stops at the dispatch configuration gate: disabled mode. After that is corrected, valid TEST credentials and an active authorized private-zone teacher route must also be configured. Direct PowerShell variables do not automatically enter an already-running FastAPI process.

Other existing paths remain: the compact SensorEventPanel Test SOS posts `/event`; controlled test scenarios use `/monitoring/scenarios/{id}/run`. All backend incident paths use the same SQLite/event system.

## Fixed application defects

1. **Direct backend startup skipped configuration loading.** Only the supervisor loaded root `.env`; `python -m uvicorn backend.main:app` did not. Main now loads the same backend-only project environment before storage, registry, notification imports and constants. It works independently of the shell working directory. Explicit process environment values retain precedence.
2. **The prominent SOS button bypassed FastAPI in local simulation mode.** It previously called only the frontend scenario animator. It now always requires confirmation and submits the backend TEST SOS, then switches to Backend Events so the actual incident is visible. Explicit local animation scenario controls remain separate.
3. **A saved incident was reported as generic success without notification outcome.** The banner previously said only ?Backend confirmed test SOS.? It now checks the persisted incident report and backend readiness, displaying Telegram NOT SENT with the actual reason, pending, failure/unknown, API accepted/receipt unconfirmed or receipt confirmed. Blocked results remain visible instead of disappearing after five seconds. The compact Test SOS control uses the same result helper.
4. Added `TELEGRAM_CHAT_ID` as a compatibility alias only when `TELEGRAM_MODE=test` and no explicit TEST chat is set. It never becomes a staff recipient fallback. Canonical `TELEGRAM_TEST_CHAT_ID` wins.

No credentials were scraped from shell history/process memory, invented, printed, moved into React or stored in source. No authorization/assignment gates were bypassed and no duplicate notification service was added.

## Actual running-app reproduction after the fix

One explicitly requested diagnostic Test SOS was clicked in the actual :3000 dashboard, starting from local simulation mode. It posted to actual :8000 FastAPI:

- Incident ID: 44ea04de-191d-42b1-b114-6ba9097864da
- HTTP event/incident successfully persisted in the existing SQLite database.
- Severity CRITICAL; is_test true.
- Telegram result **DISABLED**, no API message ID, no staff assignment.
- The new visible banner explicitly says **Telegram NOT SENT: backend TELEGRAM_MODE=disabled** and names the missing backend setup.
- All **704 pre-existing record body hashes remained unchanged**. Four new records belong to this explicitly requested diagnostic test (event, incident, notification request and disabled notification attempt). They were retained as audit evidence, not silently removed.
- Zero browser errors. No private video/image/audio capture.

This confirms the exact remaining blocker, rather than declaring a received phone message based on API/UI success. [Actual trace](runtime/sos-telegram-diagnosis/actual-dashboard-trace.json), [actual banner screenshot](runtime/sos-telegram-diagnosis/actual-sos-outcome.png).

## Test results

| Check | Actual result |
| --- | --- |
| Direct Uvicorn-style backend import loads project settings | PASS |
| Existing environment precedence / TEST-only alias | PASS: four configuration tests |
| Prominent SOS from local simulation posts backend and saves SQLite | PASS |
| Disabled backend produces truthful NOT SENT banner | PASS |
| Configured credentials without teacher route produce NO_ACTIVE_ASSIGNMENT | PASS |
| Configured TEST mode plus authorized fixture route reaches Telegram transport | PASS with explicitly mocked HTTPS, API accepted label |
| Duplicate event returns same incident and one notification | PASS |
| Three Chromium integration cases | PASS, zero page errors; no real Telegram traffic |
| Existing verified notification workflow tests | PASS: 17 |
| Existing backend regressions | PASS: 65 |
| TypeScript / production build | PASS; existing Vite config/chunk warnings remain |
| Actual authorized phone receipt through SafeSense | NOT TESTED: backend setup still absent |

The multi-case browser harness initially hit Windows port reuse errors; it was corrected to use separate test ports and test-only CORS, then all cases passed. No production CORS permissions were broadened.

[Browser results](runtime/sos-telegram-diagnosis/browser/results.json), [configured fixture acceptance screenshot](runtime/sos-telegram-diagnosis/browser/test-assigned/sos-result.png). Mocked acceptance is not a claim of actual Telegram receipt.

## Remaining local setup / real send

The user said they will configure the backend locally. At the latest inspection only `.env.example` existed; `.env`, backend `.env` and `staff-routes.json` did not. The running backend still reports disabled/unconfigured. No new real Telegram message was sent by this work.

Save the working values in `C:\Users\ewei2\Desktop\Safesense\.env`, not in React or `.env.example`:

```text
TELEGRAM_MODE=test
TELEGRAM_BOT_TOKEN=<same working value, locally only>
TELEGRAM_TEST_CHAT_ID=<same authorized chat, locally only>
SAFESENSE_STAFF_ROUTES=<private routing JSON path>
TELEGRAM_STAFF_DISPATCH_ENABLED=false
```

Use the existing routing example to configure the actual authorized on-duty teacher/duty_teacher for `ZONE_TOILET_BLINDSPOT`. An inactive placeholder does not authorize sending. A PowerShell `$token`/`$chatId` variable is not a backend environment variable; use actual environment values or the project file. Reload FastAPI after saving configuration; the direct-startup loader fix now supports that path. If configuring only `$env:` values in a PowerShell session, start FastAPI from that configured session.

After setup, use the actual confirmed SOS button or retry the saved diagnostic incident via the existing authenticated notify-test action. Do not repeatedly create SOS incidents to retry messaging. Real API acceptance needs a returned message ID; actual phone receipt must be confirmed separately. Optional existing authorized test-reply verification remains available when its user-ID allowlist was configured before sending. No public unauthenticated incident link or private media is sent.

## Modified files

- `backend/main.py`: load backend settings on direct startup before dependent imports.
- `scripts/start_services.py`: reusable configuration loader and TEST-only generic chat-ID alias.
- `dashboard/src/lib/sosNotificationOutcome.ts` (new): report actual persisted SOS/Telegram state.
- `dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx`: confirmed backend SOS in either display mode; truthful persistent result banner.
- `dashboard/src/components/analysis/SensorEventPanel.tsx`: same notification outcome for compact Test SOS.
- `tests/test_backend_telegram_environment.py` (new).
- `tests/test_sos_telegram_diagnosis_browser.py` (new).
- `tests/telegram_browser_backend.py`: isolated test-only CORS for independent browser cases.
- `SOS_TELEGRAM_FIX_RESULTS.md` (new).

Models, weights, datasets, original room geometry, staff authorization, notification idempotency, receipt verification and reports were preserved. Existing records were not deleted or replaced.
