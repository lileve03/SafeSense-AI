# SafeSense Live Monitoring - CPU performance results

Implemented and measured on 2026-10-29, Windows 11 / AMD64, 16 logical CPUs, 63.4 GiB RAM. CPU inference only; no GPU was used.

## Outcome

Recorded-camera playback is independent of AI preparation. Genuine completed pose/fall/fight results now survive service restarts in a bounded disk cache, and subsequent selections replay the original timestamped detections without executing the neural models again. The UI explicitly says **Cached recorded analysis - not live inference**. An uncached selection says **Preparing analysis** while video continues playing.

Fresh CPU inference is **not instant**. In the measured final run it took 11.475 seconds for School Entrance and 8.146 seconds for School Hall. The main improvement is durable preparation/replay and earlier video display, not a claim that neural computation became instantaneous.

## Measured camera-click performance

These are actual browser/HTTP tests using the registered recordings. Times include Playwright click dispatch/wait overhead; the component's own timers are retained separately in the JSON. Services and the dashboard were already healthy/loaded. Filesystem/playback-derivative caches may be warm. These are individual measured trials, not latency guarantees.

| Camera / path | Baseline video first frame | Updated video first frame | Baseline analysis visible | Updated analysis visible |
| --- | ---: | ---: | ---: | ---: |
| School Entrance, uncached recording / cold models | 344.8 ms | 127.2 ms | 12,991.86 ms | 12,301.88 ms |
| School Hall, uncached recording / models already resident | 280.5 ms | 79.3 ms | 9,868.80 ms | 8,660.96 ms |
| School Entrance, memory-cache replay | 261.4 ms | 73.3 ms | 293.71 ms | 296.99 ms |
| School Hall, after inference-service restart | 286.6 ms | 62.2 ms | 14,520.07 ms (reran inference) | 415.10 ms (disk-cache replay) |

The existing warm in-process cache was already fast; its latency remains similar. The major fix is avoiding the roughly 14.5-second recomputation after restart. The updated component measured cached overlay commits at 182.9 ms (memory) and 313.7 ms (disk) after its camera handler began; response JSON parsing was 0.5-0.9 ms in the measured runs.

### Service startup and memory

A separate final measurement distinguished process boot from replay. Memory values below use binary MiB (1,048,576 bytes), although telemetry keys retain the `_mb`/`_MB` suffix:

- AI process startup/imports to healthy: **7.734 seconds**.
- First disk-cache API response once healthy: **225.01 ms**, confirmed cache hit, with no fresh inference.
- Cache-only process-tree RSS: **332.3 MB**.
- Peak Windows process working set during the measured first two inference jobs: **777.5 MB** (process-lifetime peak, not a per-layer allocation measurement).

The camera-click table excludes service boot. Starting the service before a demonstration and preparing recordings once is still necessary for consistently fast visualization.

## Profiling: where the CPU time goes

Final uncached School Entrance measurements:

| Stage | Measured time |
| --- | ---: |
| First classifier load/import | 3.575 s |
| R3D-18 model load | 0.351 s |
| Fight decode validation scan | 0.099 s |
| Selected-frame decode | 0.054 s |
| R3D preprocessing | 0.049 s |
| R3D network forward passes | 1.053 s |
| Classifier prediction | 0.112 s |
| YOLO model load | 0.036 s |
| YOLO frame prediction loop, 150 actual frames | 4.968 s |
| Annotation draw/write | 0.353 s |
| Browser annotation encoding | 0.260 s |
| Queue wait on idle service | 0.015 s |

School Hall used 180 actual pose frames. Its idle queue wait was 0.018 s. Pose reused the already validated video scan instead of decoding the whole recording for validation again. Stage profiles include upload/copy hashing, evidence capture and backend delivery separately; YOLO internal preprocessing/inference/postprocessing are nested within its wall-clock prediction timer and should not be added to that timer again.

- YOLO prediction-loop throughput: **30.196 FPS** for Entrance and **29.519 FPS** for Hall in this run.
- End-to-end preparation includes model loading, decoding, serialization, annotation/evidence encoding and delivery, so it is slower than the prediction-loop FPS.
- R3D still uses exactly **3 x 16 training-compatible samples**; only the selected frames are retrieved/converted on the second decode pass.
- Pose retains **every original frame** at the default 640-pixel input size. No interpolated skeletons, duplicated synthetic detections or changed temporal-rule windows were introduced to make the numbers look faster.

A separate benchmark of 32 genuine Hall frames after model setup measured 8.99 / 14.22 / 23.73 / 31.73 FPS at 1 / 2 / 4 / 8 threads respectively. The defaults therefore use 4 R3D threads and 8 pose threads on this machine, bounded by available CPUs. This is tunable and hardware-dependent.

## Durable caching and scheduling

- SHA-256 identity includes original recording contents; YOLO and R3D checkpoint contents; selected classifier contents and threshold; pipeline/rule code; library versions; confidence/image-size/sampling/thread configuration; and evidence-window configuration.
- Camera, zone, selected model policy, database and media namespace are included so another camera/store cannot inherit the wrong incident IDs or detections.
- Recordings, classifiers and code are rehashed for validation, including rapid same-size Windows writes. Large immutable neural checkpoints use memoized hashes keyed by file metadata and identity; concurrent initial requests do not redundantly hash the large checkpoint.
- Successful completed job results are compressed on disk. Defaults: 32 entries / 256 MB disk / 7 days; memory cache remains bounded to 6 entries / 32 MB. Expiry, source/model/config changes and explicit force requests can trigger fresh preparation.
- Optional annotated-video expiry no longer invalidates genuine pose coordinates. Retained annotation files can be served after restart; absent media is not replaced with another recording.
- One CPU worker executes jobs with at most two waiting. Active duplicates coalesce, same-selection retries are idempotent, obsolete unowned waiting tasks are cancelled, and a running job is allowed to finish safely. Other viewers' work is preserved.
- Valid disk hits bypass the CPU work queue. Cache replay does not recapture evidence, create duplicate events/incidents or resend notifications.
- JSON pose responses use selective gzip compression. Video range responses and evidence thumbnails are left untouched.
- Camera submission waits for decoded video readiness (with a bounded fallback), polls running jobs more frequently, and rejects obsolete responses by selection generation. Source-video preparation is cached rather than probing/transcoding again on every visit.

The default camera path runs **one configured fight classifier + Pose**, not V2 and V3 together. Legacy explicitly requested comparison APIs remain available.

## Genuine precompute verification

The precompute helper was run against all five real registered research recordings, sequentially, using isolated test services with external notifications disabled:

| Camera | Pose frames | Original CPU preparation | Repeated helper elapsed (cache hit) |
| --- | ---: | ---: | ---: |
| Corridor A | 165 | 16.527 s | 0.239 s |
| Canteen | 158 | 11.607 s | 0.175 s |
| Staircase | 110 | 6.688 s | 0.127 s |
| School Entrance | 150 | 11.475 s | 0.080 s |
| School Hall | 180 | 8.146 s | 0.087 s |

The repeated sequential preparation of all five took 0.708 seconds in summed per-camera helper timings, all cache hits. The first helper pass prepared three misses and reused the two recordings already prepared by the browser benchmark. All five used V3 + Pose; there was no default V2/V3 comparison run.

## Validation results

| Result | Verification |
| --- | --- |
| PASS | 65 isolated backend/cache/queue/privacy/incident/notification/Overview regressions. |
| PASS | 9 TypeScript camera-model/pose timestamp contract tests. |
| PASS | 6 actual-recording browser overlay checks: Entrance, Hall, real fall overlay, switching/mobile, actual V2 output and evidence/incident/Alerts/Digital Twin preservation. |
| PASS | Source-model scores for Entrance and Hall exactly matched the baseline; independent YOLO frame results matched the rendered boxes/keypoints. |
| PASS | Persistent-cache replay after actual service restart preserved the prepared job ID and did not create new events/incidents. |
| PASS | Real active CPU duplicate requests returned the same job; an obsolete queued selection was cancelled while the running job and latest selection completed. |
| PASS | Stale selection sequences rejected with 409; private video inference rejected with 403. |
| PASS | Retained evidence remained available and seekable with HTTP 206; incident links resolved to the correct camera zone. |
| PASS | TypeScript (`npm --prefix dashboard run lint`) and production build. Existing Vite configuration/bundle warnings remain. |
| NOT TESTED | Physical live cameras/sensors or real Telegram delivery. Tests used genuine recorded videos and mocked/disabled external delivery. |
| NOT TESTED | Distributed multi-process inference workers; this design targets the existing single CPU inference service. |

No model was downloaded, no research recording was modified, and no private-area imagery was generated. First-use preparation in the intended store follows the existing recorded/test incident and evidence policy. Isolated benchmark caches are not transplanted into production incident history.

## Use before a demonstration

Restart the local services normally to load the Python changes, then run from the project root:

```powershell
.venv-vision/Scripts/python.exe scripts/precompute_monitoring.py
```

The helper reads the existing local token/environment, prepares browser playback and runs the configured model + Pose for each available registered recording one at a time. Later runs reuse valid results. To prepare only selected cameras:

```powershell
.venv-vision/Scripts/python.exe scripts/precompute_monitoring.py --camera CAM_ENTRANCE --camera CAM_HALL
```

Optional environment settings (restart services after changing them):

- `SAFESENSE_FIGHT_BASELINE=v3` (or `v2`; per-camera registry `fight_model` overrides it).
- `SAFESENSE_CPU_THREADS=4`.
- `SAFESENSE_POSE_THREADS=8`.
- `SAFESENSE_POSE_IMG_SIZE=640` (default used in all reported measurements).
- `SAFESENSE_ANALYSIS_CACHE_DIR` and `SAFESENSE_ANALYSIS_CACHE_DAYS` (default 7, bounded 1-30 days).

Ordinary first camera activation also prepares a missing entry; the helper is for preparing before presentation time. The production cache must be prepared in its own database/media context so evidence and incident IDs remain correct.

## Evidence and reproduction

- [Summary including hardware and preserved-output checks](runtime/cpu-visualization/summary.json)
- [Baseline measurements and stage profiles](runtime/cpu-visualization/baseline/performance.json)
- [Optimized measurements and frontend timings](runtime/cpu-visualization/optimized/performance.json)
- [Separate startup/cache-only memory measurement](runtime/cpu-visualization/optimized/restart-startup.json)
- [Actual pose thread benchmark](runtime/cpu-visualization/pose-thread-profile.json)
- [Initial five-camera preparation](runtime/cpu-visualization/optimized/precompute-all.json)
- [Repeated five-camera cache hits](runtime/cpu-visualization/optimized/precompute-all-repeated.json)
- [Cache/evidence/privacy integration results](runtime/cpu-visualization/optimized/integration-results.json)
- [Real queue-switch/coalescing results](runtime/cpu-visualization/optimized/queue-switch-results.json)
- [65 backend test results](runtime/cpu-visualization/backend-results.json)
- [Actual recording overlay browser results](runtime/cpu-visualization/overlay-checks/results.json)
- [Cached monitoring screenshot](runtime/cpu-visualization/optimized/cached-monitoring.png)
- [Actual fall overlay screenshot](runtime/cpu-visualization/overlay-checks/actual-fall-overlay.png)

```powershell
.venv-vision/Scripts/python.exe tests/run_cpu_monitoring_checks.py
.venv-vision/Scripts/python.exe tests/test_cpu_visualization_performance.py
.venv-vision/Scripts/python.exe tests/measure_cache_restart_startup.py
npm --prefix dashboard run lint
npm --prefix dashboard run build
node --import ./dashboard/node_modules/tsx/dist/loader.mjs --test tests/cameraAnalysisContract.test.ts tests/videoDetections.test.ts
```

The measured baseline was captured before the optimizations; running `--baseline` against the new code cannot recreate the old implementation.

## Modified files

- `fight_api.py`: CPU stage timers, model-specific thread settings, selected-frame retrieval, shared validation scans and retained annotation serving after restart.
- `monitoring_ai.py`: durable hashed analysis identity, model-refresh checks, strict source/camera binding, cached-job lookup and successful-result persistence.
- `backend/analysis_cache.py` (new): bounded atomic compressed disk cache, content hashing and JSON-only gzip middleware.
- `backend/cpu_profile.py` (new): stage timers and optional Windows process-memory telemetry.
- `backend/inference_queue.py`: completed disk-result lookup and bounded memory promotion, preserving queue ownership/cancellation semantics.
- `backend/browser_video.py`: reuse prepared playback sources and skip repeated probes/transcodes.
- `backend/main.py`: video preparation timing response header.
- `backend/incident_media.py`: configured annotation-directory compatibility for retained evidence recovery.
- `dashboard/src/components/analysis/CameraMonitoringPanel.tsx`: video-first submission, preparation/cache provenance, faster polling and frontend timing details.
- `scripts/precompute_monitoring.py` (new): sequential preparation helper.
- `tests/test_cpu_visualization_performance.py` (new), `tests/test_durable_analysis_cache.py` (new), `tests/run_cpu_monitoring_checks.py` (new), `tests/measure_cache_restart_startup.py` (new).
- `LIVE_MONITORING_CPU_RESULTS.md` (new): this report. Production `dashboard/dist/` regenerated by the build.

## Practical limits

Fresh inference remains multi-second, and first process startup/imports also take time. Video playback/cache latency varies with CPU load, disk/browser caches and recording size. Failed model/evidence/delivery runs are not treated as successful prepared sessions. Retention expiry or intentional version/config/store changes can require preparation again.

The measured synchronization checks cover the registered constant-frame-rate recordings. Whole-video fight scores still do not identify fighters or exact event times. Fall logic remains the experimental frame-local posture/temporal rule, with no calibrated fall probability or identity tracking. Live streams remain uncached bounded samples; continuous real-time CPU analysis is not claimed.
