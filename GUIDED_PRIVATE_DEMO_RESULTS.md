# Guided Private Toilet Demo: actual results

Executed locally on 2026-11-02 with isolated SQLite databases and disabled external Telegram sending. The user's incident database was not reset or used by browser fixtures.

| Verification | Actual result |
| --- | --- |
| Default compact guided view, five scenarios, explicit simulated/disconnected labels | **PASS** |
| Pause freezes tracks and pending scripted steps; paused render sample | **PASS**, zero additional frames in the checked idle interval |
| Rendered normalized observation accepted by actual backend schema | **PASS** |
| Active count and distance agree with rendered coordinates | **PASS**, two tracks and matching Euclidean distance in the sampled frame |
| Actual 3D track and sensor picking, accessible sensor inspection | **PASS** |
| Original camera zoom/reset and room | **PASS** |
| Complete Possible Fall → rules → incident → automatic simulated response | **PASS**, HIGH test incident resolved, all four stages observed |
| Normal Presence, Proximity, Repetitive Motion and SOS complete hands-off | **PASS** |
| Linked incident opens the original canonical details | **PASS** |
| Automatic responder rejects real/non-test/unrelated incident fixtures | **PASS**, five rejection variants |
| Restart does not duplicate the test incident | **PASS** |
| Source disclosure, no fabricated ML inference, actual disabled notification status | **PASS** |
| 430 px mobile layout | **PASS** |
| Campus map/navigation and Advanced Monitoring preserved | **PASS** |

All five guided scenarios completed without clicking individual event, acknowledgement or resolution actions:

| Scenario | New danger test records | Recorded outcome |
| --- | --- | --- |
| Normal Presence | 0 | No danger incident |
| Proximity | 0 | Candidate-only demonstration |
| Repetitive Motion | 1 | OBSERVE → explicitly simulated acknowledgement/resolution |
| Possible Fall | 1 | HIGH → explicitly simulated acknowledgement/resolution |
| SOS | 1 | CRITICAL → explicitly simulated acknowledgement/resolution, confidence-independent |

Automatic staff names/notes were explicitly SIMULATED DEMO. The browser confirmed no automatic VERIFIED transition. The completed exercise returned the private zone to LOW when no other active incident remained. Restart retained the same test record. Real/non-test fixtures were exercised only against the response-scope validation function, not mutated in a real backend.

## Executed suites

| Suite | Actual |
| --- | --- |
| `tests/test_guided_private_demo_browser.py` | **16 PASS** |
| `tests/test_interactive_tracking_browser.py` | **16 PASS** |
| `tests/test_sensor_observations_browser.py` | **6 PASS** |
| `tests/test_connected_private_demos.py` | **10 PASS** |
| `tests/test_incident_response_workflow.py` | **10 PASS**; notification transport mocked in this unit suite |
| `tests/test_track_motion.py` | **23 PASS** |
| `tests/test_track_motion_api.py` | **6 PASS** |
| `tests/test_sensor_observations.py` | **8 PASS** |
| `tests/test_radar_tracking_simulation.py` | **4 PASS** |
| TypeScript / Vite build | **PASS** |

Total: **38 actual Chromium browser checks and 61 backend tests passed**. No remaining FAIL result. Existing non-fatal Vite config/chunk warnings and the Starlette httpx deprecation remain.

The guided browser test recorded **zero model-job requests**, **zero camera/microphone capture calls**, **zero browser runtime errors**, and no invented actual-model result in the advanced panel before inference was requested. No real model inference or physical hardware experiment was performed by this guided verification. Existing genuine recorded inference remains a separate explicit advanced action; no prior score was substituted for a guided result.

The preserved advanced tracking performance sample used Chromium/SwiftShader software graphics: 18.33 FPS, 60 draw calls / 960 triangles, stable geometry count 36 → 36 and textures 14 → 14. This is a software-renderer sample, not a physical GPU guarantee.

**External Telegram delivery/receipt: NOT RUN. Physical radar/acoustic/SOS hardware: NOT CONNECTED.** Actual DISABLED backend notification state was observed; mocked transport tests do not establish recipient delivery. No human acknowledgement, responder arrival, real danger verification or emergency dispatch was claimed.

Evidence:

- `runtime/guided-private-demo-checks/results.json`
- `runtime/guided-private-demo-checks/guided-fall-desktop.png`
- `runtime/guided-private-demo-checks/guided-complete-desktop.png`
- `runtime/interactive-tracking-checks/results.json`
- `runtime/hardware-prototype-checks/browser-results.json`

Exact source disclosure and presentation instructions: [GUIDED_PRIVATE_DEMO.md](GUIDED_PRIVATE_DEMO.md).
