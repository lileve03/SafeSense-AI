# CPU inference queue fix

Verified 29 October 2026 (Asia/Singapore). **Final automated results: PASS — 37 checks, plus TypeScript and production build.**

## Cause

Each camera click submitted an all-model inference job. Changing the React generation counter ignored old responses but did not remove their backend work. Active identical jobs were already coalesced, but completed jobs were discarded from that lookup, so revisiting cameras started more work. Several different camera clicks could therefore occupy the one-running/two-waiting CPU budget. The resulting HTTP 429 was shown directly as an error.

The zone-navigation effect was already preview-only; it has remained so. No additional automatic inference effect was added.

## Changes

- A single CPU worker now drains an explicitly bounded pending deque. Capacity remains **three outstanding jobs: one executing and two waiting**. Cancelled work is actually removed from the deque, rather than leaving cancelled executor tasks in an internal backlog.
- Matching active requests share a job. The key includes the registered recording signature, model selection, classifier/pose weight signatures, thresholds, inference source revision, evidence-window configuration and camera/zone delivery context. Different cameras never receive another camera's incident or evidence binding.
- Completed recorded results use an LRU cache bounded to **six entries, 32 MiB of serialized result payload and 15 minutes**. Python object overhead is additional; this is not a 32 MiB process-RSS claim. Missing annotations/evidence or failed incident delivery invalidate reuse. Partial model failures are not cached. Live samples are never reused as completed recordings.
- A camera panel owns its queued selections through a random client ID and increasing sequence number. New selections remove only that panel's obsolete waiting work and prioritize its new work. Shared jobs remain queued while another client needs them; jobs submitted without a panel owner are protected. **Running inference is never cancelled.** Cancelled job metadata remains in SQLite.
- Out-of-order requests cannot overwrite a newer selection. Bounded request receipts contain IDs rather than large results and make retries of the same explicit reanalysis idempotent, including after completion. A new explicit reanalysis action may still intentionally run again.
- Playback mounts immediately, independent of queue admission. Submissions are debounced by 180 ms; obsolete requests/retry timers are aborted. Busy/service failures use serial exponential backoff with jitter, at most eight retries, then an explicit retry state. Poll failures also use bounded backoff.
- The panel displays **“AI analysis queued”** or **“Processing”** while playback remains available. The API retains HTTP 429 for true saturation, with structured `CPU_BUSY` details and `Retry-After: 2`, rather than increasing capacity.
- Job polling reads a single SQLite record instead of deserializing every historical job and pose result.
- Cached annotation handoff preserves position/pause/rate only from a playable video. Testing found and fixed a fast-cache race where the temporary paused state of an unloaded player could otherwise suppress autoplay.

## Actual verification

| Executed check | Final result | Evidence |
| --- | --- | --- |
| Queue concurrency/resource tests | **PASS 9/9** | `runtime/cpu-queue-fix/unit-tests.log` — 30 simultaneous duplicate submissions execute once; protected/shared work survives saturation; obsolete waiting work is cancelled; stale selections rejected; cache entry/byte/TTL bounds and invalidation; force-retry idempotency; failure recovery; live sample exclusion. |
| Real queue/API/browser integration | **PASS 5/5** | `runtime/cpu-queue-fix/results.json`, `browser-tests.log` — actual models, real source recordings and isolated SQLite. |
| Existing model/overlay/evidence browser regression | **PASS 8/8** | `runtime/detection-task3/results.json`, `runtime/cpu-queue-fix/detection-regression.log`. |
| Privacy adapter backend tests | **PASS 5/5** | `runtime/cpu-queue-fix/privacy-tests.log`. |
| Incident response/security backend tests | **PASS 10/10** | `runtime/cpu-queue-fix/incident-tests.log`. |
| TypeScript | **PASS, exit 0** | `runtime/cpu-queue-fix/typescript.log`, `build-results.json`. |
| Production build | **PASS, exit 0** | `runtime/cpu-queue-fix/build.log`, `build-results.json`. Existing Vite config-loader/chunk-size warnings remain. |

The real integration tests explicitly verified:

1. Three unrelated actual jobs fill the original CPU budget. An identical active request returns the existing job; a fourth distinct request receives structured 429/backpressure.
2. Rapid switching through School Entrance, School Hall and Corridor A ends on the correct Hall recording, with immediate autoplay, **12 bounded submission requests** across the switching/retry sequence, and **zero JavaScript page errors**.
3. Completed reuse returns the same job and actual scores without changing incident records. All unrelated jobs finish normally.
4. A superseded queued Entrance job becomes `CANCELLED`, while the running job continues and the newest Hall job completes. A stale selection returns HTTP 409. Repeating the completed force request returns the same job rather than rerunning inference.
5. The inference service is actually stopped while idle and restarted. The recording keeps playing during the outage; bounded retries automatically complete analysis after recovery.

The retained detection test now verifies the expected cache hit before using **Analyze recording again** to exercise fresh CPU inference. Its old assumption that every camera click reruns inference failed initially and was updated. A subsequent run exposed the unloaded-video pause race described above; that defect was fixed. Final checks confirm autoplay, paused handoff at **1.2 seconds / 1.5×**, independent YOLO boxes/keypoints, **165 annotated frames at 30 FPS**, seek alignment, actual captured evidence and private-video rejection. Initial failure logs are retained under `runtime/cpu-queue-fix/detection-initial-assumption-failure.log` and `detection-fast-cache-autoplay-failure.log`.

## Modified files

- `backend/inference_queue.py` — new bounded scheduler, ownership, priority, cache and idempotency.
- `monitoring_ai.py` — queue integration, configuration keys, cache validity, structured backpressure and release endpoint.
- `backend/storage.py` — single-record job lookup; no schema change or record deletion.
- `dashboard/src/components/analysis/CameraMonitoringPanel.tsx` — debounce, ownership, retry/backpressure, lifecycle cleanup and playback handoff.
- `tests/test_inference_queue.py` — deterministic queue tests.
- `tests/test_cpu_queue_browser.py` — actual saturation/switching/cache/cancellation/restart tests.
- `tests/test_detection_monitoring.py` — retain fresh inference regression while accounting for completed-cache reuse.
- `CPU_INFERENCE_QUEUE_FIX.md` — this report.

Production build output and runtime verification artifacts were regenerated. Model inference algorithms, trained weights, datasets, incident processing, retained evidence policy and other dashboard pages were not redesigned.

## Activation and limits

Tests run against isolated services and test databases, with external Telegram delivery disabled. The currently running normal-port SafeSense supervisor was identified and left untouched: restarting only its inference child would make that supervisor stop the other services too. **Restart SafeSense through the existing launcher to load the backend changes.** No active normal-port inference or unrelated incident processing was terminated during this work.

The result cache and request receipts are process-local and reset on service restart; persistent incident/job metadata remains in SQLite. After retries are exhausted, an operator can retry explicitly. Existing service-interrupted jobs retain the existing interrupted-job semantics rather than pretending incomplete inference succeeded. Physical live-camera connectivity and load testing at production scale were not tested or claimed.
