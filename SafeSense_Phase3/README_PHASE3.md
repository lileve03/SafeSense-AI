# SafeSense AI Phase 3: Zone-aware Backend

This ZIP replaces **only** `backend/main.py` in the previously delivered backend. It retains `GET /health`, `GET /state`, `POST /event`, `POST /incidents/{id}/ack`, and `POST /reset` used by the Phase 2 dashboard. New optional endpoint: `GET /zones`.

Run from `C:\Users\ewei2\Desktop\Safesense`:

```powershell
Copy-Item .\backend\main.py .\backend\main.backup.py.txt
# Copy extracted Phase 3 backend/main.py to your project's backend/main.py.
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal, execute the included `scripts/test_phase3.ps1` or its commands. Verify `/zones` and `/state` in your browser. If scripts are blocked, paste the script content directly into a PowerShell terminal rather than changing execution policy.

Zones: `Demo-Private-A` / `Toilet Entrance` map to `ZONE_TOILET_BLINDSPOT` (PRIVATE); `Corridor A`, `Staircase`, `Canteen`, `Main Entrance` are OPEN_HIDDEN for this prototype. You may change these policies to match the actual school site: a canteen or entrance is an open public area, not necessarily a hidden area; change enum/category when expanding the schema.

Private zone rejects `vision` events (HTTP 422). Radar handles fall/presence/motion, YAMNet handles scream/impact, and SOS is separate. Open areas may accept vision. Shared high-confidence observations within 5 seconds are fused per canonical zone. HIGH means **needs human verification**, not verified violence. The request source label is user supplied: no sensor authentication or real model inference yet. Dashboard should label all such output as simulated.

Known limitations: in-memory last 500 events and unbounded incident list, duplicate HIGH incidents possible from repeated events, no auth or rate limit, `/reset` open, no database, no actual deployment, no real dispatch, and no validation of YOLO/YAMNet model performance. Never deploy to an untrusted network or use for real emergency response as-is.
