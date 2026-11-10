# SafeSense AI Backend — Zero-to-Running (Windows / VS Code)

This ZIP contains **backend/** and **scripts/** only. Keep the latest React dashboard as-is.

1. Extract ZIP contents into `C:\Users\ewei2\Desktop\SafeSense-AI-Starter\` so you have `SafeSense-AI-Starter\backend\main.py`. Existing `dashboard` stays intact.
2. Open VS Code terminal in `SafeSense-AI-Starter` and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

If `py -3.12` is unavailable, try `py -3 -m venv .venv`, or `python -m venv .venv`.
If `.venv` already exists, skip creating it.

3. Visit http://127.0.0.1:8000/docs and http://127.0.0.1:8000/health.
4. Open **another** PowerShell terminal while the API is running:

```powershell
cd C:\Users\ewei2\Desktop\SafeSense-AI-Starter
.\scripts\test_scenarios.ps1
```

5. Verify `/state` displays events and HIGH/CRITICAL incidents. To acknowledge from PowerShell:

```powershell
$state = Invoke-RestMethod http://127.0.0.1:8000/state
$id = $state.incidents[0].id
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/incidents/$id/ack" -ContentType 'application/json' -Body '{"staff":"Demo Staff"}'
```

## API
- `GET /health` connection check
- `GET /state` last 40 events and 30 incidents
- `POST /event` accepts `{zone,type,confidence,source}`
- `POST /incidents/{id}/ack` accepts `{staff}`
- `POST /reset` clears all data

## Risk engine
- normal presence/motion → LOW
- individual fall/scream/impact/rapid motion → OBSERVE
- fall and scream/impact within 5 seconds in same zone → HIGH
- SOS → CRITICAL

## Known limitations (intentional for Phase 1)
- **No authentication**, database, sensor connection, real AI inference, real dispatch, or production safety guarantees.
- Data only persists until the server restarts. Restarting clears incidents.
- Source values like `yamnet` or `radar` are metadata, not proof that a hardware/model was connected.
- No numerical risk score, radar coordinates, personnel count or sensor heartbeat.
- CORS only allows localhost ports 3000/3001/5173. Live Google AI Studio cloud preview cannot connect to this localhost backend.
- /reset and /event are unauthenticated: keep bound to `127.0.0.1` and only run locally for testing.

## Next phase
Connect React Context to `/state` on a 2-second polling interval, map backend zone names to original zone IDs, expose DEMO/LIVE mode, and only acknowledge after a successful POST. Do not delete original Dashboard Context or change types until that integration is done.
