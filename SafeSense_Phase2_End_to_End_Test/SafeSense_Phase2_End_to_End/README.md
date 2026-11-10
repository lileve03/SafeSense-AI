# SafeSense Phase 2 — Local end-to-end test

Synthetic sensor-shaped replay only. No real radar hardware or actual emergency infrastructure is connected.

1. On Windows, unzip, open PowerShell in this folder.
2. Run `py server.py` (standard library; no pip install needed).
3. Open `http://127.0.0.1:8765` in a browser.
4. Press **Play**. Near 4.9s, the server inserts one `fall/HIGH` incident into `incidents.db`.
5. Press **SOS** to create a separate `sos/CRITICAL` incident through `POST /event`.
6. Acknowledge individually. Refresh the browser to verify the incident log persists.
7. Reset replay resets the timeline **but does not clear past incidents**; use Clear logs to clear the test history.

Endpoints: `GET /health`, `GET /state`, `POST /replay/start|pause|reset|seek`, `POST /event` (SOS only), `POST /incidents/{id}/ack`, `POST /incidents/clear`.

The service runs on 127.0.0.1 only and is not authenticated; never expose it publicly or use it as a safety-critical deployment. No live hardware access or YAMNet inference. The 4.9s fall candidate comes from the previous synthetic point cloud output, not real-world sensor evidence.
