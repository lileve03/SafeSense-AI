# Settings verification

Final result: PASS (9 checks), 0 failures. Tested in headless Chromium on 2026-10-30.

- PASS: authenticated read-only GET /settings returns runtime fusion window, cooldown and minimum event confidence; unauthenticated GET is rejected and POST is unsupported. Private-zone vision remains prohibited.
- PASS: backend mode disables simulation controls; connection wording and rendered UTF-8 punctuation are correct.
- PASS: Save persists simulation risk bands and audio across reload.
- PASS: Restore Defaults saves the shared defaults immediately and survives reload.
- PASS: changing the Observe ceiling to 60 classifies the new score-58 scenario as Observe; SOS remains Critical.
- PASS: blocked browser storage displays a save error.
- PASS: Settings causes no backend writes or browser exceptions.
- PASS: backend failure displays unavailable configuration without invented values.
- PASS: 390px mobile Settings has no horizontal overflow.

TypeScript check: PASS. Production build: PASS; existing Vite configuration and bundle-size warnings remain.

Run: `.venv/Scripts/python.exe tests/test_settings_browser.py` with Vite serving dashboard on port 3017. The test starts an isolated authenticated backend on port 8019 with a temporary database and forwards the browser configuration read to it. Remaining backend calls use the existing dashboard API configuration. Simulator behavior checks invoke the same context action as the scenario runner and inspect committed React state. Existing incident data and notification services are not mutated. This is focused Settings verification, not a full regression test of AI inference, Telegram, SOS hardware or Digital Twin.

Evidence: runtime/settings-check/results.json, settings-desktop.png and settings-mobile.png.

Backend AI model thresholds are not exposed by the configuration API; the page says so and refers to analysis evidence. No write API was added. Restart the existing backend to make the new GET /settings route available; an older running backend shows the unavailable state until restarted.
