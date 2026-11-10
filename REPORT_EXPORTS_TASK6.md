# Task 6: report exports verification

Implemented in the active Reports page (`IncidentReportsPage.tsx` and `IncidentReportView.tsx`), using `lib/reportExport.ts`. Summary, Evidence, Response and Analysis remain available. Existing staff actions and dashboard pages are preserved.

All three buttons export the selected incident, constrained by status and inclusive UTC date filters. The UI states this scope. Each button fetches the current full report and validates its identity before exporting; failures appear in the report error area. No backend records or staff messages are changed by export.

| Verification | Result | Actual evidence |
| --- | --- | --- |
| Download PDF | PASS | `runtime/reports-task6/selected-report.pdf`: 21,741 bytes, two A4 pages, 1,730 extractable text characters; opened with pypdf and PyMuPDF, rendered and visually inspected. Contains all four report sections and selected incident data. No raster images. |
| Print / Save as PDF | PASS for print invocation and rendered document | `runtime/reports-task6/print-preview.pdf`: two A4 pages; isolated print HTML contains all four sections, repeating table headers, wrapping cells and no navigation, buttons, images or video. Browser print invocation verified. Native OS print dialog was not inspected because tests run headless. |
| Download CSV | PASS | `runtime/reports-task6/selected-report.csv`: 528 bytes, UTF-8 BOM, 17 columns, one actual selected incident. Parsed and compared with the incident report API. |
| Scope and filters | PASS | Date/status options match records independently read from a database snapshot. An empty date range match removes export controls. All three artifacts identify the same selected incident. |
| Privacy | PASS | Private and unknown zone exports suppress evidence references and export no media. A deliberately injected private image/video reference is absent from PDF, print HTML and CSV. |
| CSV safety | PASS | Quotes, commas and line breaks escaped; formula prefixes including leading whitespace and control characters protected with an apostrophe. |
| Long-report pagination | PASS | 100 long response history records generate an 11-page text PDF. |
| Existing interface | PASS smoke checks | All four report tabs and Overview, Alerts, Analytics and Reports navigation remain functional. No browser exceptions. |
| TypeScript | PASS | `npm run lint` (`tsc --noEmit`). |
| Production build | PASS | `npm run build`. Vite reports config-loader and chunk-size warnings. |

Reproduce: install `requirements-test.txt` and Chromium (`python -m playwright install chromium`), then run `.venv/Scripts/python.exe tests/test_reports_exports.py`. The test starts isolated services, copies the real SQLite database using read-only access, and terminates its services afterward. Machine-readable results: `runtime/reports-task6/results.json`. Print preview image: `runtime/reports-task6/print-preview.png`.
