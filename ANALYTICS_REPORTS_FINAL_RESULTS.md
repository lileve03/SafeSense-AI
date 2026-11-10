# SafeSense Analytics & Reports - Final Results

Date: 2026-10-29 (Asia/Singapore). Workspace: `C:\Users\ewei2\Desktop\Safesense`.

## Final status

**PASS** for the implemented functionality and final executed checks. **FAIL: 0** in the final runs. Items outside the verified scope are explicitly **NOT TESTED** below.

- Backend regressions: **58 PASS**.
- TypeScript unit/contract tests: **30 PASS**.
- Chromium browser/integration checks: **9 PASS**.
- TypeScript (`tsc --noEmit`): **PASS, exit 0**.
- Production build: **PASS, exit 0**.
- Independent PDF inspection: **8 PDFs / 78 A4 pages PASS**; no text outside page bounds, no major text overlap, and no empty trailing incident-table pages.

## Implemented behavior

The top **Download CSV**, **Download PDF** and **Print PDF** actions freeze the same current filtered backend selection. The shared snapshot contains the incident records, zone names, selected filters, source snapshot time and generated time. Matching CSV/PDF filenames and the print document carry the same dataset identifier. The identifier is a consistency label, not a cryptographic signature.

CSV does not fetch media or substitute simulated dashboard seed data. It exports one row per selected incident, using UTF-8 with BOM, CRLF records, quoted cells, doubled embedded quotes and the existing spreadsheet formula-injection escaping. The existing single-incident export remains separately labeled **Download incident CSV**.

CSV fields, in order:

`Incident ID`, `Timestamp`, `Zone`, `Event Type`, `Severity`, `Source`, `Model Version`, `Score`, `Processing Mode`, `Review Status`, `Assigned Staff`, `Acknowledged At`, `Resolved At`, `Evidence Reference`.

- IDs are full backend IDs. Zone labels fall back to the recorded zone ID when unavailable.
- Missing fields remain empty; numeric zero scores are retained.
- Model versions, scores and evidence references preserve observation order as semicolon-separated lists. Event types are unique per incident. Assigned staff uses the recorded assignment or recorded staff field.
- Private/unknown/reclassified zones omit media references and export a metadata-only description.
- Empty selections produce a valid header-only CSV and visual reports with **No data**.

Long labels now wrap in charts and tables. Oversized filter scopes get a separate scope page; oversized incident rows continue across pages. Compact chart/evidence labels may be abbreviated, while full zone labels remain available in CSV and report tables. Time-series positions follow actual creation dates. Provenance notes appear on the evidence page to avoid a notes-only final page.

## Actual SQLite results

Operational checks used a read-only backup of `runtime/safesense.sqlite3`, with isolated backend/media services and external notifications disabled. The report/export operations left the copied incident records unchanged. Original evidence files were copied for the tests, not modified.

| Metric | Actual result |
| --- | ---: |
| Incidents | 56 |
| High risk (HIGH + CRITICAL) | 5 |
| Incidents with SOS | 3 |
| Pending human review | 53 |
| Resolved | 1 |
| Average creation-to-acknowledgement | 17.2 seconds / 3 valid pairs |
| Real-model records | 46 |
| Recorded sensor replays | 5 |
| Persisted simulations | 5 |

All eight dashboard distributions were independently calculated from SQLite and compared with the rendered chart data: trend, types, zones, severity, workflow status, acknowledgement status, sources and processing modes. No example chart values were added to production code. PDF type legends, severity/status counts and response time were also checked against SQLite in both downloaded and printed documents.

The type donut counts 78 incident/type memberships across 56 incidents; a multi-type incident can appear in multiple categories, as stated on the chart.

## Verification matrix

| Status | Check | Actual result / evidence |
| --- | --- | --- |
| PASS | Filtered CSV field fidelity | All 56 rows and all 14 fields matched SQLite; UTF-8 BOM verified. |
| PASS | Same selection across formats | CSV/PDF dataset IDs matched; print used the same layout ID, values and evidence images. |
| PASS | Date + zone + severity + event filters | Actual 2026-10-29 Staircase / OBSERVE / possible_conflict subset: 9 CSV rows and 4-page PDF, with excluded incidents absent. |
| PASS | CSV escaping / formula safety | Quotes, commas, embedded newlines, non-Latin text, leading controls, whitespace and `= + - @` attack prefixes tested. |
| PASS | Real visual charts | Downloaded and printed PDFs contain vector trend, donut, zone, severity and response charts, rather than screenshots of charts. |
| PASS | Full visual report | Download and print each produced 7 A4 pages with 4 permitted retained evidence thumbnails. |
| PASS | Image quality | Embedded thumbnails are 960 x 540 pixels at approximately 297.4 effective DPI at their printed size; visually inspected. Original recording quality remains the upper limit. |
| PASS | Private evidence | Private-only report: 0 images and 0 thumbnail requests. Unauthenticated/private/mismatched evidence requests rejected with 401/403/404. |
| PASS | Empty selection | Header-only CSV; visual PDF displays No data and includes no images. |
| PASS | Long labels | Explicit 684-character zone-label UI fixture, 2 records, 6-page PDF; full CSV label retained. |
| PASS | Large datasets | Explicit 300-record UI fixture: 300 CSV rows and matching 23-page download/print outputs; every incident ID found. |
| PASS | Oversized single rows | Unit test verifies continuation of one oversized row across A4 pages. |
| PASS | Navigation | One Analytics & Reports entry; six old/canonical hash/path links resolved correctly. |
| PASS | Responsive layout | 390-pixel Chromium viewport had no page-level horizontal overflow. |
| PASS | Existing monitoring pages | Overview, Live Monitoring, Alerts and Digital Twin navigation/rendering checked; private 3D canvas remained healthy WebGL with no private images/video. |
| PASS | Other behavior regressions | Backend incident acknowledgement/resolution/reporting, notification safety, privacy adapters, Overview identity handling, inference queue and automatic-camera policy tests passed. Camera model/overlay contracts also passed. |
| PASS | Protected source files | Overview, Live Monitoring, Alerts, Digital Twin, both private monitoring components and CameraMonitoringPanel remained unchanged during this completion; hashes retained. |
| PASS | Build checks | TypeScript and production build exited 0; existing Vite warnings remain. |
| NOT TESTED | Native OS print dialog / physical printer | Headless tests verified print invocation, isolated print document, print media and actual Chromium-generated PDF instead. |
| NOT TESTED | Excel / LibreOffice application import | CSV was decoded and parsed programmatically, including injection cases; spreadsheet applications were not launched. |
| NOT TESTED | Other browser engines | Chromium tested; Safari/Firefox not exercised. |
| NOT TESTED | Hardware / external delivery / fresh model inference | No physical sensors/cameras or real Telegram delivery; notification transport was mocked. Fresh YOLO/fight inference was not rerun in this export task. |

The stress/security fixtures are explicitly labeled test-only data. They were never inserted into the operational database or used for the actual 56-incident results above.

## Generated artifacts and inspection evidence

Actual SQLite selection:

- [Filtered CSV - all 56 incidents](runtime/analytics-reports-final/filtered-all.csv)
- [Filtered CSV - 9-incident subset](runtime/analytics-reports-final/filtered-subset.csv)
- [Downloaded visual PDF - 7 pages](runtime/analytics-reports-final/download-visual.pdf)
- [Printed visual PDF - 7 pages](runtime/analytics-reports-final/print-visual.pdf)
- [Filtered visual PDF - 4 pages](runtime/analytics-reports-final/filtered-visual.pdf)
- [Private-only metadata PDF](runtime/analytics-reports-final/private-metadata.pdf)
- [Empty-selection PDF](runtime/analytics-reports-final/no-data.pdf)
- [Print HTML used by the browser](runtime/analytics-reports-final/print-report.html)

Explicit layout fixtures:

- [Long-label PDF](runtime/analytics-reports-final/long-labels.pdf)
- [300-record CSV](runtime/analytics-reports-final/large-dataset.csv)
- [300-record downloaded PDF - 23 pages](runtime/analytics-reports-final/large-dataset.pdf)
- [300-record printed PDF - 23 pages](runtime/analytics-reports-final/large-dataset-print.pdf)

Inspection evidence:

- [Per-page vector/image/font/bounds inspection - 78 pages](runtime/analytics-reports-final/pdf-inspection.json)
- [Independent PDF chart/value verification](runtime/analytics-reports-final/pdf-data-verification.json)
- [Final browser results - 9 PASS](runtime/analytics-reports-final/results.json)
- [Backend results - 58 PASS](runtime/analytics-reports-final/backend-results.json)
- [Frontend command exit codes](runtime/analytics-reports-final/frontend-checks.json)
- [Protected source hashes](runtime/analytics-reports-final/protected-source-hashes.json)
- [Private 3D regression screenshot](runtime/analytics-reports-final/private-monitoring-regression.png)
- [Mobile dashboard screenshot](runtime/analytics-reports-final/combined-mobile.png)
- [Final large-report download page](runtime/analytics-reports-final/large-dataset-page-23.png)
- [Final large-report print page](runtime/analytics-reports-final/large-dataset-print-page-23.png)
- [Long-label scope page](runtime/analytics-reports-final/long-labels-page-2.png)

Representative PDF pages were opened and visually inspected after rendering the actual files:

![Downloaded cover, KPIs and charts](runtime/analytics-reports-final/download-visual-page-1.png)

![Printed vector distributions](runtime/analytics-reports-final/print-visual-page-2.png)

![Permitted retained evidence](runtime/analytics-reports-final/download-visual-page-3.png)

## Modified / added files in this completion

Implementation:

- `dashboard/src/lib/filteredReportCsv.ts` - new filtered CSV serializer, shared dataset identifier and supported field mapping.
- `dashboard/src/lib/incidentAnalytics.ts` - types for supported incident/evidence export fields.
- `dashboard/src/pages/AnalyticsReportsPage.tsx` - filtered Download CSV, common export snapshot cache and clarified export scope.
- `dashboard/src/components/incidents/IncidentReportView.tsx` - distinguish individual-incident CSV from the filtered export.
- `dashboard/src/lib/visualReport.ts` - long-label layout, time-axis positioning, row continuation and removal of notes-only trailing pages.

Tests / documentation:

- `tests/filteredReportCsv.test.ts` - CSV security/fidelity, empty data, long labels and oversized rows.
- `tests/test_analytics_reports_final_browser.py` - SQLite/browser/export/navigation/privacy and stress checks.
- `tests/run_analytics_reports_backend.py` - isolated backend regression runner.
- `tests/inspect_analytics_reports_final.py` - independent PDF rasterization, bounds/overlap, vector and resolution checks.
- `ANALYTICS_REPORTS_FINAL_RESULTS.md` - this report.

`dashboard/dist/` was regenerated by the production build. Test artifacts, isolated databases, PDFs, CSVs, logs and screenshots are under `runtime/analytics-reports-final/`. No dependencies were added.

## Reproduction

Run from the project root:

```powershell
npm --prefix dashboard run lint
npm --prefix dashboard run build
node --import ./dashboard/node_modules/tsx/dist/loader.mjs --test tests/analytics.test.ts tests/analyticsReports.test.ts tests/visualReport.test.ts tests/filteredReportCsv.test.ts tests/cameraAnalysisContract.test.ts tests/videoDetections.test.ts
.venv-vision/Scripts/python.exe tests/run_analytics_reports_backend.py
.venv-vision/Scripts/python.exe tests/test_analytics_reports_final_browser.py
.venv/Scripts/python.exe tests/inspect_analytics_reports_final.py
```

Logs: [TypeScript](runtime/analytics-reports-final/typescript.log), [build](runtime/analytics-reports-final/build.log), [unit tests](runtime/analytics-reports-final/typescript-tests.log), [backend tests](runtime/analytics-reports-final/backend-tests.log).

## Remaining limitations

- PDF uses built-in Latin fonts and ASCII-safe text. Arbitrary non-Latin PDF labels need an embedded Unicode font; CSV preserves UTF-8 text and this was tested.
- Evidence is limited to four representative permitted thumbnails; unavailable/expired clips become metadata-only placeholders. Thumbnail resolution does not create detail absent from the original recording.
- PDF tables abbreviate displayed incident IDs to eight characters; CSV retains full identifiers.
- Vite still warns about `__dirname` in its configuration and the existing large bundle. Build succeeds.
- Regression results cover the stated suites/pages, not an exhaustive certification of every feature, model or hardware integration.
