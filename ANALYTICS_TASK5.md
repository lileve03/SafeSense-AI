# Task 5: operational Analytics

The large research evaluation section and duplicate operational summary have been removed from Analytics. ResearchMetrics, saved evaluations, scripts, trained models and research files remain intact. Reports > Model evaluation still reads and displays the existing saved results (including the V3 comparison value 0.9167).

## Operational data and layout

Analytics now requests authenticated /incidents records and /zones labels from the existing backend, whose incident records are persisted in SQLite. It does not use the global in-memory demonstration alerts, trigger-text heuristics or placeholder performance metrics. Switching the dashboard's demo/backend mode does not substitute a fabricated analytics dataset. Persisted simulations remain explicitly labeled and filterable.

Kept the existing white/slate/blue cards and severity, location, source and recent-activity views. Added a compact shared filter bar, measured response summaries, date trend, observed alert types, processing-mode and workflow breakdowns. Horizontal distribution charts keep category labels readable; optional View counts tables expose exact values without oversized evaluation tables. The layout stacks at narrow widths.

All KPIs, eight charts and the recent incident list use exactly the same selected records. Filters include date range (UTC, inclusive custom dates), processing mode, zone, initiating source, severity, workflow status and acknowledgement. Reset restores all records. Invalid date intervals hide misleading statistics and show an error. A refresh button and 15-second automatic refresh load a new backend snapshot; requests have a 10-second timeout and reject obsolete responses.

No-record and no-match states are explicit. An initial API failure shows no false zero statistics. A refresh failure keeps the last successful snapshot with a visible stale-data message. Zone-label errors fall back to stored zone IDs. The live backend was receiving additional camera-analysis incidents during initial verification; detailed tests therefore use a SQLite backup on isolated services, while the active-app smoke check compares the precise response snapshot with its persisted incident IDs. No active jobs or services were stopped.

## Counting and measurement definitions

- Incident count uses stable incident IDs; separate saved test runs remain separate records. No score-based merging or inferred unique physical emergencies.
- Open means status is neither RESOLVED nor FALSE_ALARM. Acknowledged means a parseable acknowledged_at timestamp is saved; awaiting acknowledgement means an open incident without one.
- Source distribution uses the incident's actual initiating source field, rather than guessing radar/YOLO from words such as fall or pose. Processing mode distinguishes real_model, recorded_sensor_replay and simulation; unknown values remain explicit. Real-model events may come from recorded research videos and are not labeled live hardware events.
- Alert types count each incident once per distinct observed evidence type. Multi-type incidents can contribute to several categories, so that chart's total may exceed the incident count. Its caption discloses this.
- Trends use actual incident creation dates in UTC, without synthetic trend points. Invalid dates are reported/excluded from the trend and from date-filtered scopes.
- Mean acknowledgement measures created_at to acknowledged_at. Mean closure uses created_at to resolved_at for terminal incidents, including reviewed false alarms. Missing/invalid/negative timestamp pairs are excluded; zero-second measured intervals remain valid. Sample counts accompany both means. On-site arrival and physical delivery time remain unmeasured.
- Reviewed false-alarm rate uses false alarms divided by all closed incidents, not all detections or an accuracy estimate. Empty denominators display Not measured.

## Verification

- TypeScript: PASS (`npm run lint`). Production build: PASS (`npm run build`), with existing Vite configuration/bundle-size warnings.
- 10 aggregation/filter tests: PASS. Cover actual mode/source classification, intersecting filters, inclusive UTC boundaries, unknown dates, stable ID deduplication, distinct event types, acknowledgement/closure denominators, negative timestamps, empty data and real zero-second measurements.
- 7 browser checks: PASS against a read-only copy of 28 actual SQLite incident records. All eight chart datasets and KPI counts matched independently computed Python/SQLite expectations. The snapshot had mean acknowledgement 17.2 seconds from three valid timestamp pairs. Verified category/date/combined filters, invalid dates, empty selections, tooltip and count-table interaction, 390px responsiveness, global-mode independence, research access through Reports, and clearly scoped empty/error/stale UI metadata fixtures. No model inference or media was fabricated or run for Analytics testing.
- Active dashboard smoke: PASS. Actual backend snapshot of 28 incidents matched persisted SQLite records and displayed distributions; evaluation section absent, no JavaScript exceptions. Live incident totals may continue changing with authorized monitoring activity.
- Protected Overview/Alerts, incident list, original private monitoring components, V2/V3/YOLO model files, ResearchMetrics and the saved comparison file had unchanged hashes during verification. Backend incident records in the isolated snapshot remained unchanged. Task 5 introduces no backend mutation or incident creation action.

Artifacts: runtime/analytics-task5/results.json, protected-hashes.json, activation.json, summary.json, analytics-desktop.png, analytics-mobile.png and active-analytics.png.

## Changed files

- dashboard/src/pages/AnalyticsPage.tsx: operational-only data loading, consistent filters, measured KPIs, retained/improved charts and explicit loading/error/empty states.
- dashboard/src/lib/incidentAnalytics.ts (new): shared selection and aggregation definitions.
- tests/analytics.test.ts (new): aggregation and filter tests.
- tests/test_analytics_browser.py (new): isolated SQLite-backed browser verification.
- tests/test_analytics_activation.py (new): read-only live snapshot verification.
- tests/test_browser_demo.py: updates the old analytics assertion to check operational Analytics and verify the unchanged research results in Reports > Model evaluation, returning to Analytics afterward.
- This report and generated dashboard/dist/runtime verification artifacts.

No Overview, Alerts, private 3D view, backend API, operational model, evaluation script or research result was modified. No retraining or service restart was performed for this task.
