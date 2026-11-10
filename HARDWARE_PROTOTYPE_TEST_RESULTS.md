# Hardware-ready private-area prototype verification

Executed locally on 2026-11-02. Backend tests use isolated SQLite databases. No physical hardware acquisition or live staff delivery was exercised.

| Check | Actual result |
| --- | --- |
| `tests/test_sensor_observations.py` (.venv) | 8 tests passed |
| `tests/test_radar_tracking_simulation.py` (.venv) | 4 tests passed |
| `tests/test_privacy_adapters.py` (.venv-vision, project PYTHONPATH) | 5 tests passed |
| `tests/test_private_sensor_pipeline.py` (.venv) | 4 tests passed; actual recorded radar/acoustic inference suite completed in 102.382 seconds |
| `tests/test_incident_response_workflow.py` (.venv) | 10 tests passed; Telegram transport mocked |
| `tests/test_sensor_observations_browser.py` (.venv-vision) | 6 checks passed in isolated backend/frontend/browser |
| `npm.cmd --prefix dashboard run lint` | TypeScript passed |
| `npm.cmd --prefix dashboard run build` | Production build passed |

31 backend tests passed across the listed suites. Contract coverage includes authentication, fail-closed hardware ingestion, invalid/stale data suppression, schema/coordinate validation, duplicate IDs and changed-payload rejection, synthetic fusion/SOS, persisted recorded evidence without fabricated coordinates, and retained incident records. Existing regressions cover radar simulations, actual recorded inference, privacy adapters and incident response.

Browser checks verify that the original Toilet WebGL room remains visible, recorded mode initially has zero positioned occupants, hardware mode reports disconnected with no positioned occupants, explicit simulation submits through the new shared API, switching back to replay clears synthetic tracks, and there are no browser runtime errors. Screenshot and machine-readable browser results are in `runtime/hardware-prototype-checks/`.

The backend environment initially lacked the repository-pinned `httpx==0.28.1` test dependency; it was installed. Privacy checks require the existing vision environment because the backend environment has no OpenCV. The browser fixture was adjusted to use the existing allowed CORS origin on port 3001. These issues were resolved before the successful runs above.

Non-fatal existing tooling warnings: Starlette deprecates its httpx fallback; Vite warns about `__dirname` with its future native config loader and a large output chunk. No hardware-in-loop test was performed. No physical driver or verified connection is claimed.

The locally running supervisor was refreshed. All three services reported ready, and authenticated `GET /sensors/observations/status` returned `connected:false`, `verified:false`, `Hardware Disconnected`.
