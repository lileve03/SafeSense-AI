# Live Monitoring UI layout results

2026-10-30: TypeScript PASS; production build PASS; Chromium browser verification 15 PASS, 0 FAIL. Existing Vite configuration and bundle-size warnings remain.

Inspected active route: App -> LiveMonitoringPage -> CameraMonitoringPanel -> DetectionResults, with VideoDetectionOverlay using the decoded video playhead. VideoAnalysisPanel is not mounted on this route and was left unchanged.

UI source files changed:
- dashboard/src/App.tsx: suppress only the shared explanatory banner on Live Monitoring; global header/sidebar unchanged.
- dashboard/src/pages/LiveMonitoringPage.tsx: reduce spacing and Recent Events card density.
- dashboard/src/components/analysis/CameraMonitoringPanel.tsx: compact five-camera selector, navy video focus, one Recorded Video indicator, concise status, collapsible source/timing details and unchanged playback/overlay handlers.
- dashboard/src/components/analysis/DetectionResults.tsx: contain results in the right column, compact model cards and collapse lengthy model limitations; preserve frame records, timeline seek, evidence preview and incident controls.
- dashboard/src/components/analysis/cameraMonitoring.css: new scoped responsive layout styles.

Verification file: tests/test_live_monitoring_layout_browser.py.

Browser checks used the running page at port 3000, all five original source videos, and genuine completed model results read from SQLite in read-only mode. The test intercepted job submissions/release and replayed those existing results; it did not run new inference or create new incidents. This is actual browser verification of playback, layout, callbacks and recorded-analysis overlays, not a new model-validation run.

All five cameras passed autoplay, replay, correct identity and two decoded-frame/overlay comparisons. Timeline buttons seek to recorded event timestamps where present. Existing result incident buttons open the original detail modal. Desktop widths 1280, 1440 and 1920 preserve the larger video left and compact results right; widths 1024, 768 and 390 stack correctly with horizontal camera-card scrolling. No browser exceptions. Original SQLite rows and hashes of the global header, sidebar, backend, context, models pipeline and synchronized-overlay logic remained unchanged.

Screenshots: runtime/live-monitoring-layout/live-monitoring-desktop.png, live-monitoring-panel.png, live-monitoring-mobile.png. Machine-readable results: runtime/live-monitoring-layout/results.json.
