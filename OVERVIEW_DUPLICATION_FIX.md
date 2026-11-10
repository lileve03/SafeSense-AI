# Task 1 — Overview duplicate insights (29 October 2026)

Completed only Task 1. No next-task changes were made.

## Targeted change

The same Staircase and Corridor A recorded inputs had been analyzed more than once, creating distinct persistent incident IDs. The Overview `/insights` endpoint previously emitted every incident, so repeated analyses appeared as duplicate insights. Matching scores alone would incorrectly hide unrelated incidents.

The endpoint now selects the latest representative using stable incident ID, a full shared event-ID set, or a valid recorded-input identity. Recorded-video identity includes zone, processing mode/source, severity, camera, model, event type, input SHA256 and evidence interval/event timing. Generated annotation IDs and confidence scores are not identity. Saved sensor replay uses the exact evaluation-row reference. Missing provenance is not guessed; live incidents, simulations, precomputed provenance, different models/cameras/zones and different event times remain distinct.

This is **Overview presentation grouping only**. Incidents are not merged, deleted, resolved or otherwise mutated. Alerts, counters, response history and other APIs keep their existing records. The `/insights` response schema and summary/provenance wording are unchanged.

## Files changed

- `backend/main.py`: import/call the Overview-only helper from `/insights`.
- `backend/overview_insights.py`: pure identity-based grouping helper.
- `tests/test_overview_insights.py`: 12 regression cases for identity and provenance boundaries.
- `tests/test_overview_duplicates_browser.py`: read-only current-data API/browser verification.
- This documentation file.

No frontend source, styles, layouts, cards, Digital Twin components, models, datasets, training code, notification logic or incident persistence logic changed. Protected hashes confirm OverviewPage.tsx, AlertsPage.tsx and ActiveHistoricalIncidents.tsx are byte-for-byte unchanged from the start of Task 1.

## Executed results

| Check | Actual result |
|---|---|
| Identity/provenance unit tests | PASS 12/12 |
| TypeScript (`npm.cmd --prefix dashboard run lint`) | PASS |
| New endpoint on an isolated copy of current records | PASS; no incident mutation |
| Overview browser layout classes versus baseline | PASS; unchanged |
| Alerts browser content versus baseline | PASS; unchanged; source filter works |
| Protected Overview/Alerts source hashes | PASS; unchanged |
| Activated normal-port Overview and Alerts | PASS; no JavaScript errors |
| Persistent incident state before/after activation | PASS; all 18 incident records identical |

The current snapshot contains 17 active incident records and now produces 15 distinct insights. The two repeated recorded-analysis entries are grouped in Overview only. All 18 total incidents remain available to Alerts and incident management. No inference or retraining was run for this fix.

Evidence: `runtime/overview-task1/results.json`, `activation.json`, and `state-before-activation.json`. Screenshots: `overview-before.png`, `overview-after.png`, `overview-active.png`, and `alerts-unchanged.png` in that same directory. The read-only browser test validates the new backend in isolation with a snapshot; the separate activation check verifies the real unmocked endpoint at http://127.0.0.1:3000.
