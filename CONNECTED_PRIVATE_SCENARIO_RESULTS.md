# Connected private-area scenario results

Executed locally on 2026-11-02. Browser suites use isolated FastAPI/SQLite instances and disabled Telegram sending. No user incident database was reset or used for the browser fixtures. The original room, navigation and privacy restrictions were retained.

## Actual scenario PASS / FAIL

| Complete 40-second simulated playback | Result | Observed outcome |
| --- | --- | --- |
| Normal Presence | **PASS** | Presence + normal acoustic test metadata; no new danger incident |
| Two-Person Proximity | **PASS** | Backend duration candidate / supported simulated distances; no automatic danger incident |
| Repetitive Abnormal Motion | **PASS** | Backend repeated-motion support before delivery; one OBSERVE pending-review test incident |
| Possible Fall + Acoustic Impact | **PASS** | One HIGH test incident; fall + impact evidence from distinct simulated modalities, using existing fusion rules |
| SOS Emergency | **PASS** | One CRITICAL direct-help test incident with model confidence zero and no model score |

All five ran through their full playback duration at the selected playback speed. All synthetic event rows had `processing_mode=simulation`, `source_type=SIMULATION`, `is_test=true`, explicitly SIMULATED evidence, `score=null` and no model version. No numerical ML score was fabricated for a synthetic event.

For OBSERVE, HIGH and CRITICAL scenarios, actual Chromium interaction verified:

- Replaying the same run produced **no duplicate incident**.
- Digital Twin Map risk matched the same persisted incident ID shown in Alerts.
- UI actions completed **NEW → ACKNOWLEDGED → VERIFIED → RESOLVED**. VERIFIED was an explicit human **simulation-test** action, not proof of real danger.
- Incident Review retained that incident and its resolved history.
- The map returned to LOW after resolution with no remaining active zone incident.
- The incident card read actual backend notification state **DISABLED**; it did not claim Telegram API acceptance, delivery or receipt.

Separate browser checks verified actual anonymous marker movement, coordinate distances, trajectories/trails, selection, camera interaction, simulated fall height, radar/acoustic/SOS fixture indicators, mode isolation and clearing unsupported spatial data. Basic unarmed playback created no backend event or incident. All browser suites reported **zero runtime errors and zero camera/microphone capture calls**.

## Actual registered model inference

These were executed through the existing browser `/testing/runs` workflow using the existing radar/acoustic environments. Scores are actual raw model outputs, not calibrated danger probabilities or accuracy estimates.

| Registered recording | Result | Actual output |
| --- | --- | --- |
| `radar_raw_fall` | **PASS** | `SVM_RBF-LOSO-reconstructed`, score **0.9932906517861326**, candidate true |
| `acoustic_scream` | **PASS** | `YAMNet-pretrained-local-cache`, score **0.9465681314468384**, candidate true |

Both results reported `fresh_raw_input_inference`, input SHA-256 and persisted RECORDED SENSOR REPLAY test events. Each positive result remained an independent OBSERVE recording candidate. No synchronized fall-plus-impact fusion, anonymous people tracks, measured room positions or distances were invented from these classifications. The available YAMNet positive sample was correctly labeled **scream**, not impact.

Actual input digests:

- Radar: `cbb896a8f9b09cec540639044a563a003a5a19b529e4133feea7aba31aad1c8f`
- YAMNet: `c6b5f0c74896988b4ef5b2078f580ae5edb42bc0dc2bb01fd93ee414635e1153`

## Executed test counts

| Suite | Actual |
| --- | --- |
| `tests/test_connected_private_demos.py` | **10 PASS** |
| `tests/test_incident_response_workflow.py` | **10 PASS**; Telegram transport mocked in this unit suite |
| `tests/test_track_motion.py` | **23 PASS** |
| `tests/test_track_motion_api.py` | **6 PASS** |
| `tests/test_sensor_observations.py` | **8 PASS** |
| `tests/test_radar_tracking_simulation.py` | **4 PASS** |
| `tests/test_connected_private_demos_browser.py` | **28 PASS**, **1 NOT_RUN** |
| `tests/test_interactive_tracking_browser.py` | **16 PASS** |
| `tests/test_sensor_observations_browser.py` | **6 PASS** |
| TypeScript / Vite production build | **PASS** |

Total: **61 backend tests and 50 browser checks passed; zero remaining FAIL results**. These are software verification counts, not ML performance measurements. Existing non-fatal Vite config/chunk warnings and the Starlette httpx deprecation remain.

The backend tests additionally exercised delayed/restarted-run aggregation without false fusion, cross-run isolation, rejection of new signals for a closed run, explicit new-run behavior, idempotent SOS, confidence-independent help escalation, canonical response transitions, and rejection of private video/speech metadata. Existing fall classification and explainable fusion were preserved.

## Explicit external-service limitation

**External Telegram delivery / recipient receipt: NOT_RUN.** External sending was disabled in the isolated tests. Actual DISABLED status was read from the backend. Transport-mocked API acceptance tests are not external delivery evidence. No live Telegram recipient receipt, physical sensor, physical danger, emergency-services dispatch or synchronized real fall/impact recording was verified or claimed.

Machine-readable evidence:

- `runtime/connected-private-demo-checks/results.json`
- `runtime/interactive-tracking-checks/results.json`
- `runtime/hardware-prototype-checks/browser-results.json`
- Screenshot: `runtime/connected-private-demo-checks/connected-sos.png`

Usage, source distinctions, run IDs and endpoint details: [CONNECTED_PRIVATE_SCENARIOS.md](CONNECTED_PRIVATE_SCENARIOS.md).
