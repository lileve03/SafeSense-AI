# Final integration test results — 28 October 2026 (Singapore)

**Latest scenario-library follow-up:** see [SCENARIO_LIBRARY_AUDIT.md](SCENARIO_LIBRARY_AUDIT.md) and [SCENARIO_LIBRARY_TEST_RESULTS.md](SCENARIO_LIBRARY_TEST_RESULTS.md) for all 12 fresh recorded-data inputs, actual radar/acoustic model execution, preservation hashes and current feature regressions. The response-workflow counts below document the preceding integration round.

The latest complete incident-response implementation and normal-port activation are documented in [INCIDENT_RESPONSE_WORKFLOW.md](INCIDENT_RESPONSE_WORKFLOW.md). This supersedes earlier test-only Telegram limitations: configured live staff routing now exists behind explicit enable and server-only ingestion credentials, while all tests/replays remain TEST-chat-only. Actual Telegram receipt remains unverified; the running instance has no configured bot/test chat and remains disabled.

All results below refer to executed local checks, not inferred production readiness. Original models, datasets and research evaluations were retained. External Telegram sending was disabled throughout system tests.

| Executed suite | Result | Evidence |
|---|---|---|
| New actual-data integration + browser | PASS 20/20 | `runtime/real-monitoring-tests/results.json`; includes combined models and organized report lifecycle |
| Existing API/model regression suite | PASS 36/36 | `runtime/test-results/results.json` |
| Existing temporal/sensor/privacy/evaluation unit tests | PASS 16/16 | `runtime/test-results/unit-results.json` |
| Telegram routing/transport safety tests | PASS 13/13 | `tests/test_notification_safety.py`; mocked HTTP transport, no actual message sent |
| Incident response/security/outbox tests | PASS 10/10 | `tests/test_incident_response_workflow.py`; isolated SQLite and mocked transport |
| TypeScript | PASS | `npm.cmd --prefix dashboard run lint` |
| Production build | PASS | `npm.cmd --prefix dashboard run build` |
| Actual PowerShell launcher | PASS | `Start-SafeSense.ps1 -SmokeTest`; owned services became ready on isolated 28000/28001/3002 and shut down |
| Activated normal-port dashboard | PASS | `runtime/real-monitoring-tests/activation.json`; actual browser playback/inference/evidence verified at http://127.0.0.1:3000 |

The latest response-workflow verification passed 95 individual checks across these suites, all rerun for this integration. TypeScript and production build also passed. The existing Vite warnings about __dirname compatibility and large bundles remain; they are not build failures. Historical follow-up sections below describe earlier integration rounds.

## Actual model observations

| Recording | Executed model | Actual result |
|---|---|---|
| AIRTLab violent/cam1/97.mp4 | V2 | Score 0.9745275974273682; threshold 0.4; candidate, retained real clip and incident |
| Same conflict recording | V3 | Score 0.9848954677581787; threshold 0.7; matches saved research reference; feature-cache reuse disclosed |
| AIRTLab non-violent/cam1/1.mp4 | V3 | Score 0.09235220402479172; no candidate; output was not forced |
| UR Fall fall-02-cam0-rgb.mp4 | YOLO11n-Pose + existing experimental temporal rule | Candidate at 2.1s (frame 64); actual boxes/skeletons in annotated video; bounded evidence and incident |

Final isolated run: cold V2 model pipeline 5.723s for a 5.5s video; normal V3 2.567s; fall pipeline 4.702s for a 3.667s video. These timings vary with CPU load. Cached V3 reported zero frame-inference FPS because it reused actual features. Pipeline timings exclude separately reported evidence/delivery overhead. No real-time performance is claimed.

## Executed workflows

- Registered source existence, all eight scenarios, five configured/unconfigured public cards, real byte-range media seeking.
- Camera click → actual muted autoplay → asynchronous real inference → candidate → retained H.264 evidence → incident modal.
- Actual fight V2/V3, normal classification, actual pose annotation and fall-rule timestamps.
- Private video rejection through both legacy upload APIs, new jobs and evidence ingestion; unauthenticated sensitive media/incident reads rejected.
- Sensor-only recorded radar/acoustic replay, clearly simulated fusion and SOS; no private images/video/speech captured.
- Original Three.js private room, WebGL canvas, map navigation, in-scene incident action and zero private media elements.
- Unified acknowledgement/history, zone risk synchronization, resolution and rejection of acknowledgement on closed incidents.
- SQLite incident/status preservation across a real backend process restart.
- Evidence deletion, expired-reference response, evidence UUID traversal defenses.
- All nine existing dashboard pages rendered without JavaScript exceptions.
- Legacy missing classifiers, empty/bad/oversized video, invalid models/zones and concurrent analysis rejection.
- Telegram mock transport: exact TEST recipient, active routing, successful-send deduplication, unknown-delivery suppression, token redaction, missing-credential/inactive-route behavior and blocked production mode.

Earlier browser runs exposed an assertion before evidence finished loading and an unreliable network-idle wait on a polling app. The final suite waits for actual evidence/player and backend-ready state; the final 18/18 results were rerun successfully. A staff-picker TypeScript error was corrected and type-check reran successfully.

## NOT TESTED / incomplete

- Physical RTSP/HTTP camera connectivity: NOT TESTED. The configured live preview and bounded-sample adapter exist, but continuous real-time analysis and a validated live pre-trigger rolling buffer remain incomplete.
- Physical radar/acoustic/SOS hardware and measured occupants/positions/distances: NOT TESTED / unavailable. Saved prediction replay and labeled simulation are supported instead.
- Actual Telegram message receipt: NOT TESTED / no authorized test credentials were configured by this work. A mock Bot API response is not proof of receipt.
- Telegram callback acknowledgement: NOT IMPLEMENTED; staff acknowledge through the authenticated local dashboard.
- Staff Telegram dispatch: implemented behind explicit mode/enable settings and verified live-ingestion credentials; remains DISABLED on this local demonstration. No real staff or public emergency-channel messages were sent.
- School production security: NOT IMPLEMENTED. Shared local token/loopback controls are not identity roles, TLS or encrypted-at-rest storage.
- Multi-sensor physical synchronization and validated person-level fight localization: unavailable, not claimed.

Screenshots: `runtime/real-monitoring-tests/camera-evidence.png`, `runtime/real-monitoring-tests/private-original-3d.png`. Full operational setup, limitations and configured live source behavior are in SYSTEM_WORKFLOW.md and TELEGRAM_SETUP.md.

## Local activation

The pre-update supervisor and its exact service children were identified from Windows process command lines. Existing local session state was backed up under `runtime/session-backups/20261028T131246Z.json` and migrated before those verified processes were restarted. That session contained zero events/incidents. The updated supervisor now serves the normal 3000/8000/8001 URLs. A subsequent actual browser check created one genuine research-video candidate and verified its retained evidence at the normal dashboard URL. Screenshot: `runtime/real-monitoring-tests/active-dashboard.png`. Telegram remains disabled/NOT_CONFIGURED; no external messages were sent.

## Public-camera follow-up

Every configured camera click now submits one bounded job that runs the existing V2, V3 and YOLO11-Pose models sequentially on CPU. Individual model selection remains available. Real pose overlays are not fight-person localization. Independent results, errors, delivery statuses and captured evidence remain visible. The live preview is separated from completed recorded-sample analysis. Unconfigured cards are disabled, and operator-configured live sources take precedence over any recorded scenario mapping so a recorded file cannot be mislabeled as live.

The normal-port browser check passed after activation: actual source autoplay, all three model outputs, actual annotated-video playback, retained evidence, and the same incident visible in Alerts, Incident Review and the Digital Twin. Evidence: `runtime/real-monitoring-tests/public-camera-activation.json`; screenshot: `runtime/real-monitoring-tests/public-camera-all-models.png`. V2 score 0.9745275974273682 and V3 score 0.9848954677581787 produced candidates; YOLO returned no fall candidate for this conflict recording. No output was forced to match a scenario label.

Before activation, one existing event/incident was backed up under `runtime/session-backups/20261028T132332Z.json`; SQLite state was preserved. Physical live-camera connectivity remains NOT TESTED. The first follow-up browser assertion accidentally selected a hidden dropdown option; it was changed to assert the selected model value and actual visible model results, and the 19-check suite reran successfully.
