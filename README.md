# SafeSense AI

Privacy-conscious school safety research demonstration. The existing React dashboard and trained V1/V2/V3 models are preserved. Public-area analysis uses real offline CPU inference; private areas accept only radar/acoustic/SOS metadata. AI candidates require human review and do not prove wrongdoing, injury or an emergency.

## Architecture

| Component | Location | Responsibility |
| --- | --- | --- |
| React / TypeScript / Vite dashboard | `dashboard/` | Monitoring, incidents, analytics, reports, and Three.js digital twin |
| FastAPI application | `backend/main.py` | Privacy rules, sensor fusion, SQLite persistence, response workflow and opt-in Telegram routing |
| FastAPI CPU inference service | `fight_api.py`, `monitoring_ai.py` | R3D-18 features with V2/V3 fight classifiers and YOLO11 pose analysis |
| Model and research tools | `ai_models/`, `evaluation/` | Vision, radar and acoustic adapters and evaluation tooling |
| Local supervisor | `Start-SafeSense.ps1`, `scripts/start_services.py` | Environment loading, loopback services and lifecycle management |

The dashboard calls the backend on port 8000 and inference service on 8001. Operational records and evidence stay under ignored `runtime/`. Private zones use sensor metadata; public video processing requires authorization. Research scores support human review, not automatic emergency decisions.

## Fresh clone installation

Install Python 3.12, Node.js/npm compatible with `dashboard/package-lock.json`, and FFmpeg on PATH for H.264 encoding. Run from the repository root in PowerShell. Only create environments if they do not already exist:

```powershell
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
if (-not (Test-Path .venv-vision)) { py -3.12 -m venv .venv-vision }
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv-vision\Scripts\python.exe -m pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv-vision\Scripts\python.exe -m pip install -r requirements-inference.txt
npm.cmd --prefix dashboard ci
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Pinned dependencies reflect the existing local project; a clean online installation was not performed during upload preparation. If an index cannot supply a pinned package, resolve compatibility explicitly before changing model-loading versions. Keep `.env` local and leave Telegram disabled for initial startup. See [MODEL_AND_DATA_SETUP.md](MODEL_AND_DATA_SETUP.md) for separately provisioned weights and authorized demo inputs. A source-only clone does not include trained classifiers, recordings or saved benchmark outputs; unavailable scenarios require those prerequisites and must not be represented as working inference.

## Start on Windows

**Integrated monitoring update:** Campus Camera Feeds autoplay actual registered research recordings and run Fight V2, V3 and YOLO11-Pose together by default. Independent scores/results and actual YOLO boxes/skeletons are shown; person boxes are not fight localization. Candidate clips synchronize with Alerts, Incidents and the Digital Twin. The original private 3D room is retained. Candidate incidents now queue persisted staff notifications, support acknowledgement and resolution, and generate organized Summary/Evidence/Response/Analysis reports. Telegram is disabled by default; authorized live events can use explicitly enabled on-duty staff routing, while all test/replay incidents remain restricted to the authorized TEST chat. See TELEGRAM_SETUP.md before enabling any recipient.

Read [SYSTEM_WORKFLOW.md](SYSTEM_WORKFLOW.md), [SCENARIO_TEST_GUIDE.md](SCENARIO_TEST_GUIDE.md), [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md), [REAL_MONITORING_AUDIT.md](REAL_MONITORING_AUDIT.md), and [FINAL_INTEGRATION_TEST_RESULTS.md](FINAL_INTEGRATION_TEST_RESULTS.md) for the current integration and executed checks. Earlier reports describe prior versions.

The complete response flow and its preceding 95-check verification are documented in [INCIDENT_RESPONSE_WORKFLOW.md](INCIDENT_RESPONSE_WORKFLOW.md). Reports separates Summary, Evidence, Response and Analysis for each incident, with operational analytics and model evaluation in separate categories. The newer scenario-library checks are documented below.

**Fresh scenario library:** Live Monitoring now includes 12 actual-input inference scenarios (eight AIRTLab/UR Fall videos, two raw radar recordings and two acoustic samples), plus preserved saved-prediction and controlled-test shortcuts. Radar uses fresh raw features and a transparently reconstructed held-out benchmark; acoustic runs actual cached-pretrained YAMNet. No output is forced from a scenario label. See [SCENARIO_LIBRARY_AUDIT.md](SCENARIO_LIBRARY_AUDIT.md), [SCENARIO_TEST_GUIDE.md](SCENARIO_TEST_GUIDE.md), and [SCENARIO_LIBRARY_TEST_RESULTS.md](SCENARIO_LIBRARY_TEST_RESULTS.md). New authenticated endpoints: `/testing/scenarios`, `POST /testing/runs`, `/testing/runs` and `/testing/runs/{id}`. Existing APIs remain supported.

Open PowerShell in the project directory:

```powershell
.\Start-SafeSense.ps1
```

If local script execution is restricted, run this process-scoped invocation:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-SafeSense.ps1
```

Open http://127.0.0.1:3000. The supervisor starts the existing backend on **8000**, the vision environment on **8001**, and Vite on **3000**, bound to loopback. It checks readiness, writes `runtime/logs`, refuses occupied ports, and stops only its own child processes on Ctrl+C. No model download, training, microphone capture or webcam capture is started by this launcher.

Manual startup in three terminals (run from project root):

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
.\.venv-vision\Scripts\python.exe -m uvicorn fight_api:app --host 127.0.0.1 --port 8001
npm.cmd --prefix dashboard run dev -- --host 127.0.0.1 --strictPort
```

The old `backend.fight_api:app` command also works through a compatibility shim. `fight_api.py` is the canonical implementation. Do not start both inference entrypoints on the same port.

## Environment and dependencies

Reuse existing `.venv`, `.venv-vision`, `.venv-radar`, and `.venv-acoustic` environments when available. For a fresh clone, create the two core environments below; optional radar/acoustic environments have separate requirements under `ai_models/`. Do not merge these environments. Python 3.12 and Node/npm are required. Backend uses `backend/requirements.txt`; tested inference package versions are recorded in `requirements-inference.txt`. If dependencies are missing:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv-vision\Scripts\python.exe -m pip install -r requirements-inference.txt
npm.cmd --prefix dashboard ci
```

For a fresh vision environment, install compatible CPU PyTorch/Torchvision wheels from `https://download.pytorch.org/whl/cpu` before the remaining requirements. Preserve the scikit-learn version used by existing joblib artifacts. No retraining is necessary.

R3D-18 uses the actual pretrained `r3d_18-b3b3357e.pth` in Torch's checkpoint cache. The service deliberately returns 503 if it is missing rather than downloading weights during an upload. To provision the official checkpoint explicitly while online:

```powershell
.\.venv-vision\Scripts\python.exe -c "from torchvision.models.video import r3d_18,R3D_18_Weights; r3d_18(weights=R3D_18_Weights.DEFAULT)"
```

YOLO weights: root `yolo11n-pose.pt`. Fight classifiers:

- `evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib` — V2 threshold **0.4**.
- `evaluation/outputs/fight_v3/fight_v3_classifier.joblib` — V3 threshold **0.7**.

Model paths resolve relative to the project, independent of the terminal working directory. FFmpeg on PATH is used to encode browser-compatible H.264 annotated MP4s. Without it, the service explicitly reports a downloadable MP4V fallback. Input audio is never included in annotations.

## Configuration

The launcher propagates `SAFESENSE_API_TOKEN` to both services and `VITE_SAFESENSE_API_TOKEN` to Vite. The default `local-demo-only` is a public local demo credential, **not production authentication**. For manually started processes set the same values in all relevant terminals:

```powershell
$env:SAFESENSE_API_TOKEN = 'your-local-demo-access-value'
$env:VITE_SAFESENSE_API_TOKEN = $env:SAFESENSE_API_TOKEN
```

Optional configuration: `SAFESENSE_BACKEND_URL` (default http://127.0.0.1:8000), `SAFESENSE_FUSION_WINDOW_SECONDS` (5), `SAFESENSE_COOLDOWN_SECONDS` (15), `SAFESENSE_MIN_CONF` (0.5). Frontend URLs: `VITE_API_BASE_URL`, `VITE_AI_BASE_URL`; defaults point to loopback ports 8000/8001. Restart services after configuration changes. UI threshold controls apply only to illustrated local simulation; they cannot disable backend privacy or change fixed fight thresholds.

## Four reproducible demos

**A — Public-area physical conflict:** Open Live Monitoring → Public-area Video Analysis. Select Corridor A and V2 or V3. Upload an authorized research MP4 (for example violent/cam1/97.mp4 under the existing AIRTLab dataset). Confirm authorization and run analysis. Inspect whole-video score, threshold, processing time and `real_model` label. Open incident details and acknowledge. Digital Twin highlights Corridor A at Observe; two camera-model scores never constitute independent corroboration.

**B — Possible fall:** Select YOLO11-Pose / Experimental fall rule, upload `datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4`, confirm public-area authorization and run. View actual bounding boxes/skeletons, annotated MP4 and time markers. The tested clip produced an upright-to-horizontal candidate at 2.1 seconds. This is a posture heuristic, not a trained or clinically validated fall classifier.

**C — Private-area metadata:** In Sensor Replay & SOS Demo select the private zone. Choose a saved radar/acoustic prediction and replay it; provenance is `recorded_sensor_replay`. These are saved evaluation model outputs, not newly executed radar inference or live hardware. Unrelated dataset recordings are never fused. Alternatively click **Simulate radar + acoustic fusion** to emit two explicitly simulated virtual sensor signals in one five-second window, yielding a High review incident. No audio/video is uploaded. Private-area video requests return 403 even if the caller declares a public zone_type. The private map inspector also opens these metadata controls.

**D — SOS:** Select a zone and click **Trigger test SOS**. A Critical, explicitly simulated SOS incident appears immediately. Open/acknowledge it, then review or resolve it. Acknowledgement preserves active zone risk; resolving all zone incidents clears that zone's active status. No physical dispatch or external notifications occur.

The default **Backend Events** mode displays actual API event records with per-event processing labels. **Simulated Demo** mode preserves the original seeded illustrations/scenarios and is visibly labeled. Run Demo Scenarios switches explicitly to that local mode. No simulated inference is used behind the upload controls.

## API contracts

Backend: existing routes remain, now with `X-SafeSense-Token` required on sensitive reads and mutations. New routes: `/monitoring/cameras`, `/monitoring/scenarios`, `/monitoring/sources/{scenario}`, `/monitoring/scenarios/{scenario}/run`, `/incidents/{id}/report`, `/incidents/{id}/notify-test`, `/notifications/status`, `/analytics/incidents`. `/reset` clears persisted demo events/incidents; it does not erase evidence or notification audit. AI adds `/monitoring/jobs`, `/monitoring/jobs/{id}`, `/monitoring/evidence/{id}`, authenticated POST `/monitoring/evidence/{id}/delete`, and configured `/monitoring/live/{camera_id}`.

Event input retains legacy `zone/type/source/confidence` plus `processing_mode`, optional `sensor_modality`, `score`, `model_version`, `evidence_reference`, `event_id`. Modes: `real_model`, `recorded_sensor_replay`, `simulation`. Real-model event submission requires the service token. Legacy events default to explicit simulation. Acknowledgement requires JSON `{"staff":"Duty operator"}`. Review status accepts DISPATCHED, VERIFIED, RESOLVED, FALSE_ALARM. Dispatch records a local operator action only.

Inference: `GET /health`, `/ai/fight/health`, `/ai/fight/models`; multipart `POST /ai/fight/analyze` with `file`, `zone_id`, `authorized=true`, `model_version=v2|v3`, header `X-SafeSense-Token`. Fall: `POST /ai/fall/analyze` with the same file/zone/authorization fields. Both validate the server zone registry, not caller-supplied privacy labels. Annotated output: `/ai/fall/artifacts/{id}` with token header or token query for video playback.

Limits: 100 MiB, MP4/AVI/MPG/MPEG, at most 120 seconds / 3600 decoded frames, at most 1920×1080 pixels, <=120 FPS. One CPU analysis at a time; overlapping requests receive 429. Decode and fall processing have time budgets; fall processing stops after 180 seconds. Upload tempfiles are removed after requests. The last 16 fight feature vectors are cached in memory by video SHA256, allowing V2/V3 comparison without repeat extraction. Scores are not calibrated probabilities; fight results have no frame-level timestamps.

## Tests

```powershell
.\.venv-vision\Scripts\python.exe tests\test_integration_demo.py
.\.venv-vision\Scripts\python.exe -m unittest discover -s tests -p test_privacy_adapters.py -v
.\.venv-vision\Scripts\python.exe -m unittest discover -s tests -p test_evaluate_fsd50k.py -v
.\.venv-vision\Scripts\python.exe -m unittest discover -s ai_models\vision -p test_temporal_logic.py -v
.\.venv-vision\Scripts\python.exe -m unittest discover -s ai_models\private_sensors -p test_private_sensor_simulator.py -v
npm.cmd --prefix dashboard run lint
npm.cmd --prefix dashboard run build
```

Integration tests use isolated ports 18000/18001 and their own temporary SQLite database. They execute real V2/V3/fall inference and compare fight scores against saved research outputs. They do not retrain or overwrite research artifacts. The new tests/test_real_monitoring.py also starts its own dashboard on 3001 and disables external notifications. Legacy browser tests require the three demo services running and add test incidents to that session:

```powershell
.\.venv-vision\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv-vision\Scripts\python.exe -m playwright install chromium
.\.venv-vision\Scripts\python.exe tests\test_browser_demo.py
```

See `TEST_RESULTS.md` for actual outcomes and `runtime/test-results` for machine-readable results, server logs and screenshots.

## Limits and retention

- Local demonstration only: shared-token access and loopback binding, no individual login roles, TLS or emergency-services dispatch. Staff Telegram delivery is opt-in; test/replay events remain test-chat-only. SQLite persists incidents, evidence references, histories, jobs, notification requests and attempts under `runtime/safesense.sqlite3`.
- Public uploads/pose annotations can identify people. Pose extraction is not anonymization. Candidate video clips are now retained in `runtime/evidence` for configurable retention (default seven days), with authenticated access/deletion. Fight clips retain the entire analyzed interval because precise event timing is not validated. Pose annotation previews retain the existing ten-file limit and may expire earlier than incident evidence. Source upload temporary files are deleted.
- Radar and acoustic dashboard replay uses existing saved evaluation predictions. Raw point-cloud replay and fresh hardware inference are not implemented. Existing benchmark and YAMNet tools are retained. Microphone/camera capture is opt-in and was not exercised; no hardware connectivity is claimed. Scream research metrics exist; impacts remain experimental without validated metrics.
- YOLO fall logic monitors one most-confident person without stable identity tracking. Occlusions, changes of person and posture can cause errors. Four-sequence baseline results do not validate this temporal rule.
- V3 improves combined research performance but loses some AIRTLab recall versus V2. Dataset metrics are not school performance or deployment certification. CPU upload processing is offline; no real-time performance is claimed.
- Original datasets, classifiers and evaluation outputs remain local and are excluded from upload. The repository was initialized on `master` with no commits or remotes at the time of upload preparation.


## Safe GitHub publication

Read [GITHUB_UPLOAD_SAFETY.md](GITHUB_UPLOAD_SAFETY.md) for the local audit and explicit commit/push commands. `.gitignore` excludes environments, credentials, routing files, runtime databases/evidence, research recordings, model binaries and generated research outputs. Source code, Three.js assets, model configuration and dependency manifests remain available to commit. Never use `git add -f` for excluded private artifacts. Older task reports describe previous implementations and are not guarantees of current behavior. No project license is added by this preparation; confirm project and third-party redistribution rights before publication.
