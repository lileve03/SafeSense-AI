# SafeSense AI — Privacy-First Campus Safety Early Warning

A staff dashboard for hackathon demo with multimodal edge sensor fusion (mmWave radar, acoustic classification, masked privacy vision, and physical SOS buttons) and zero raw surveillance storage in private zones.

## Quick Start

```bash
npm install && npm run dev
```

The application runs on Vite at `http://localhost:3000`.

## Backend Connection

SafeSense AI connects to your FastAPI backend at `http://localhost:8000` (configurable via the Settings gear in the top-right corner):

```bash
uvicorn main:app --reload --port 8000
```

### Endpoints Supported:
- `WebSocket /ws`: Pushes full snapshot JSON on every state change and on connect
- `POST /api/events`: Injects simulated telemetry (`presence`, `fast_motion`, `fall`, `scream`, `impact`, `loud_benign`, `running`, `fight_like`, `sos`)
- `POST /api/sos/{zone}`: Triggers physical SOS panic alert
- `POST /api/alerts/{id}/ack`: Triage alert (`confirmed` or `false_alarm`)
- `POST /api/scenarios/{id}/run?trials=5&speed=1`: Executes regression batches
- `POST /api/reset`: Resets demo state
- `GET /api/export/runs.csv`: Downloads benchmark CSV

*Note: SafeSense AI also includes an in-browser standalone simulator engine so you can test all features, audio chimes, SVG floor-plan digital twin, scenarios, and validation gates even without a local backend running.*
