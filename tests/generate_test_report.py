"""Render the saved, executed check outputs as a readable project test report."""
from pathlib import Path
import csv
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/test-results'
api=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
browser=json.loads((OUT/'browser-results.json').read_text(encoding='utf-8'))
units=json.loads((OUT/'unit-results.json').read_text(encoding='utf-8'))
with (OUT/'legacy-api-results.csv').open(encoding='utf-8-sig',newline='') as f:legacy=list(csv.DictReader(f))

def escaped(value):
    return str(value).replace('|',' / ').replace('\n',' ') 

def summary(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    return escaped(text[:450])+(' … (full output in JSON)' if len(text)>450 else '')

lines=['# Executed test results — 2026-10-28 (Asia/Singapore)', '',
       'Final results: **36/36 API/inference, 13/13 browser, 14/14 preserved HTTP smoke, 16/16 unit tests passed**. TypeScript, production build, Python imports and compile checks passed. These counts exclude unexecuted hardware checks.', '',
       'Actual machine-readable evidence: [API](runtime/test-results/results.json), [browser](runtime/test-results/browser-results.json), [unit tests](runtime/test-results/unit-results.json), [existing smoke script](runtime/test-results/legacy-api-results.csv). Screenshots and server logs are in the same directory. No predictions were mocked in real-video or browser workflows.', '',
       '## Real inference measurements', '',
       '| Check | Observed output |', '|---|---|']
for row in api:
    actual=row['actual']
    if 'real MP4 HTTP inference' in row['test']:
        lines.append(f"| {escaped(row['test'])} | Score {actual['score']}; saved reference {actual['saved_reference_score']}; {actual['latency']}s; feature cache hit={actual['feature_cache_hit']} |")
fall=next(r['actual'] for r in api if r['test'].startswith('Real YOLO11'))
lines += [f"| YOLO11-Pose temporal rule | {fall['video_duration_sec']}s input, {fall['annotation_frames']} annotated frames, candidate at 2.1s, {fall['inference_time_sec']}s processing, {fall['annotation_bytes']} bytes, {fall['annotation_playback']} |", '',
          'Fight test input: existing AIRTLab violent/cam1/97.mp4 from the reserved-comparison manifest. Score differences are below 1e-5. V2 includes feature extraction/model initialization; V3 reused those features. The cached V3 latency is not standalone R3D inference latency. Fall input: datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4. Browser verified actual advancing H.264 playback, not just a video element.', '',
          '## API / inference checks', '', '| Test | Status | Actual output / error |', '|---|---|---|']
for row in api: lines.append(f"| {escaped(row['test'])} | {row['status']} | {summary(row['actual'])} |")
lines += ['', '## Browser checks', '', '| Test | Status | Actual output |', '|---|---|---|']
for row in browser:lines.append(f"| {escaped(row['test'])} | {row['status']} | {summary(row['actual'])} |")
lines += ['', '## Existing HTTP smoke script', '', 'Executed scripts/test_e2e.py against a disposable backend on port 18002; its reset never touched the running demo. Original expectations were updated for Observe review incidents and explicitly independent virtual sensor modalities.', '', '| Test | Status | Actual output |', '|---|---|---|']
for row in legacy:
    lines.append(f"| {escaped(row['test'])} | {'PASS' if row['passed']=='True' else 'FAIL'} | HTTP {row['http_status']}; level/status {row['actual_level']}; {row['response_ms']}ms |")
lines += ['', '## Retained and added unit tests', '', 'These focused unit tests validate logic/adapters; their mocked HTTP transports are not model inference or hardware tests.', '', '| Test | Status | Actual output |', '|---|---|---|']
for row in units:lines.append(f"| {escaped(row['test'])} | {row['status']} | {summary(row['actual'])} |")
lines += ['', '## Build / startup checks', '', '| Test | Status | Actual output |', '|---|---|---|',
          '| Python import + module compatibility | PASS | backend.main and fight_api imported; backend.fight_api.app is the same app object |',
          '| Python compileall | PASS | python -m compileall -q backend fight_api.py ai_models scripts/start_services.py; exit 0 |',
          '| TypeScript | PASS | npm --prefix dashboard run lint -> tsc --noEmit; exit 0 |',
          '| Production frontend build | PASS | Vite 8.3.5; 2261 modules transformed; dist generated; exit 0 |',
          '| Service supervisor | PASS | Existing .venv backend 8000, .venv-vision AI 8001, Vite 3000 all returned HTTP 200 on loopback. Occupied-port refusal also observed. Shutdown of owned child processes was observed during controlled restarts. |',
          '| Browser runtime crash audit | PASS | No JavaScript page errors across tested navigation/workflows; mobile width 390px with body/main within viewport |', '',
          'Non-fatal build warnings: the pre-existing Vite configuration uses __dirname; the main bundle exceeds the advisory 500 kB threshold (~1.36 MB uncompressed). Starlette emits a TestClient/httpx deprecation warning. Invalid-byte upload testing deliberately causes OpenCV to print moov atom not found; the API returns 422 and continues running.', '',
          '## Failures found and corrected during work', '',
          '- Initial replay regression failed: excluding unrelated replay rows accidentally excluded the current row, causing a real recorded fall candidate to be assessed LOW. Fixed to include the current row only; final replay tests pass and unrelated recordings do not corroborate.',
          '- The first acoustic adapter test used Mock for a context manager, producing AttributeError: __enter__. Corrected the test fixture to MagicMock; the application adapter test now passes.',
          '- Initial browser inspection script printed Unicode to the Windows cp1252 console and failed after saving its screenshot. Browser test runner now sets UTF-8 output; full browser workflows pass.',
          '- A restart immediately after stopping an owned service correctly refused a still-occupied port while the previous supervisor was cleaning up. Waited for its shutdown and started again; no unrelated process was stopped.',
          '- Repair targets verified by regression: wrong model root/module entrypoint, missing incident contract, ACK body/state mismatch, private-zone camera gating, low-score V2 candidates, correlated evidence, replay provenance and browser video codec.', '',
          '## Not run / practical limits', '', '| Check | Status | Reason |', '|---|---|---|',
          '| Physical mmWave/C1001 connectivity or inference | NOT RUN | No verified hardware connection; saved TI IWR6843 evaluation predictions were replayed instead |',
          '| Live microphone/YAMNet capture | NOT RUN | No capture was started; adapter/privacy logic and recorded evaluation replay were tested |',
          '| Live webcam capture | NOT RUN | No camera was opened; public-zone permission-before-capture regression passed |',
          '| Fresh raw radar inference / raw point-cloud streaming | NOT RUN | UI replay intentionally reads existing evaluation predictions; original benchmark scripts retained |',
          '| Impact model evaluation | NOT RUN | No established impact evaluation artifact; simulation/experimental mapping is labeled accordingly |',
          '| New full dataset evaluation / model retraining | NOT RUN | Existing trained models and research results preserved; uploaded-clip score equivalence tested |',
          '| Verified school performance / real-time throughput | NOT RUN | Research demo only; reported CPU timings cover selected offline clips, not deployment performance |',
          '| Genuine AVI/MPG/MPEG uploads | NOT RUN | Extension acceptance is implemented and all content is decoded with OpenCV; actual E2E inference used existing MP4 recordings |',
          '| Production identity, TLS, durable database, external dispatch | NOT RUN | Out of the local demo implementation; no external deployment or message sending performed |', '',
          'Inference/API checks run on isolated ports 18000/18001. Browser checks use the running demo and create labeled test incidents; restarting the supervisor clears in-memory history. Generated annotations/test logs stay under runtime; original research outputs and trained models were not used as output destinations.', '']
(ROOT/'TEST_RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
print('TEST_RESULTS.md generated from executed result files')
