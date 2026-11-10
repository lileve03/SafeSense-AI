# Incident Report UI verification

2026-10-30: Chromium browser checks: 10 PASS, 0 FAIL. TypeScript: PASS. Production build: PASS (existing Vite configuration and bundle-size warnings).

The report retains Summary, Evidence, Response and Analysis; adds a navy incident header, compact risk/location/notification cards, a two-column summary, a separate description, organized evidence and model records, and a chronological response history. Purple accents and white cards preserve the SafeSense theme.

Verified actual report identity, source, risk, timestamps and scores; all four tabs; keyboard tab navigation; downloaded CSV identity/UTC timestamps/zone/severity; simulation labels; private-zone media exclusion; local notification preview; acknowledgement and resolution gating and persistence; and panel overflow at 1280, 768 and 390 pixels. Browser timezone was Asia/Singapore; visible timestamps include GMT+8 and time elements retain ISO UTC values. CSV timestamps remain unchanged UTC records.

Response tests used the existing backend APIs on a disposable SQLite copy. A newly created simulation incident in that copy was previewed, acknowledged and resolved. TELEGRAM_MODE was disabled. No live Telegram acceptance or recipient receipt was generated or claimed. Original SQLite rows were compared before and after and remained identical. Protected backend, notification, simulation-context and CSV-exporter file hashes remained unchanged.

Browser requests to the normal backend URL were forwarded to the isolated real backend on port 18271. Existing evidence media still uses the unchanged identity-checked IncidentMedia component and OPEN_HIDDEN permission gate. Model inference, live hardware, real Telegram transmission and receipt verification were not exercised.

Evidence: runtime/incident-investigation/results.json and incident-summary.png, incident-evidence.png, incident-response.png, incident-analysis.png. Run tests/test_incident_investigation_browser.py with the dashboard serving on port 3000.
