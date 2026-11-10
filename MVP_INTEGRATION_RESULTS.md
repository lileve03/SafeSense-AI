# SafeSense AI MVP Integration Results

Date: **30 October 2026 (Asia/Singapore)**. Recording/incident timestamps and report chart grouping retain their stored UTC values.

## Delivered application and scope

Integrated and verified the existing SafeSense MVP in place. No separate app, backend replacement, retraining, database reset or dashboard redesign. Overview and Alerts source/style files are unchanged. Existing Fight V2/V3, R3D-18, YOLO11-Pose, datasets, SQLite, evidence retention, Digital Twin and reports remain.

The additional projects were inspected before integration. Phase 2 contains a synthetic tracked replay and prototype HTTP server, not real radar/YAMNet inference. Its supplied positions remain isolated in the optional labeled simulation lab. threejs_test contributes compatible local controls/status-ring ideas to the original private room, not its mock risk scores, dispatch claims or fabricated telemetry. Real private sensor inference continues to use existing SafeSense raw radar and local YAMNet workers.

**Overall:** Public and private recorded/demo workflows pass. SOS creation, configured-route assignment logic, notification preview and dashboard acknowledgement pass. **Actual Telegram transport and assignment to a real teacher remain NOT TESTED because the running backend is disabled/unconfigured.** A fixture route and mocked Telegram transport are explicitly distinguished below. No external message was sent during this verification.

## Confirmed fixes in this completion pass

1. Completed cached camera results immediately refresh shared backend incident state, as fresh completion already did.
2. Notification actions refresh the shared context, block duplicate simultaneous clicks and refresh their containing operational report snapshot.
3. Incident dossiers clear old state when IDs change and reject mismatched report identities, preventing stale records appearing under another incident ID.
4. Confirmed private SOS has an in-flight guard and a stable event ID retained across failed responses. A real-browser fault test committed the event on the backend, returned a deliberate 503 to the browser, then retried: same event and incident, no duplicate.
5. A genuine CSV check found that acknowledgement updated the dossier before the Analytics list's 15-second poll. The report now awaits its parent snapshot refresh after mutations. The final CSV contains the actual acknowledged timestamp and `under_review`, not the previous pending snapshot.
6. Corrected existing text-encoding artifacts in the touched incident report labels. Layout/theme are unchanged.

## PUBLIC AREA: camera to Digital Twin

**PASS.** Each configured camera was clicked in Chromium with a newly isolated analysis cache. Original authorized research footage autoplayed independently of analysis. The API selected exactly one configured Fight model (V3 in this run) plus Pose; it did not run V2 and V3 together. Actual CPU inference produced model scores, nonempty frame-level person detections and keypoints. Pause/seek displayed the corresponding actual frame coordinates and skeletons.

Positive AIRTLab Fight and UR Fall results created existing-schema public incidents, retained real video evidence, served evidence bytes and matching camera metadata, and updated the existing Digital Twin zone state. Negative recordings were not forced positive. Camera switching and cached visits kept source identity separate. V2 remains supported/preserved; this five-camera default test used the configured V3 baseline.

- Corridor A: V3 classifier score **0.984895**, genuine whole-clip positive; 646 person detections over 165 frames (not 646 unique people).
- Staircase: genuine UR Fall recording; **33 person-associated binary fall-candidate frames**, red box/skeleton and no fabricated numeric fall score.
- Canteen / Entrance / Hall: actual negative Fight scores retained; no invented positive label.
- Whole-video classification never supplies person boxes. Existing experimental participant candidates require separately supported pose-interaction evidence. Four additional safety tests verify classifier-only, missing-person, low-confidence and mismatched-source inputs abstain. Participant heuristic values are not V2/V3 scores or validated aggression probabilities.

### Actual CPU measurements

Milliseconds are browser click-to-playback and first actual person-box DOM observations. CPU latency excludes the browser scheduling/poll interval. Cold means the durable result cache started empty; installed local model weight files were already available. Cached rows reuse original inference CPU metadata rather than claiming that inference reran. These are single samples, not hardware benchmarks or guarantees.

| Camera | Result path | Video ms | First boxes ms | Pose frames | Person detections | V3 score | Fall-candidate frames |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CAM_CORRIDOR_A | cold | 258.7 | 15251.8 | 165 | 646 | 0.984895 | 0 |
| CAM_CANTEEN | cold | 184.1 | 9704.7 | 158 | 452 | 0.092352 | 0 |
| CAM_STAIRCASE | cold | 168.9 | 5818.7 | 110 | 121 | 0.561408 | 33 |
| CAM_ENTRANCE | cold | 171.7 | 6612.4 | 150 | 145 | 0.110818 | 0 |
| CAM_HALL | cold | 160.4 | 7396 | 180 | 150 | 0.038757 | 0 |
| CAM_CORRIDOR_A | cached | 337 | 337 | 165 | 646 | 0.984895 | 0 |
| CAM_HALL | cached | 216.1 | 305 | 180 | 150 | 0.038757 | 0 |

Cold CPU analysis took 5.381-14.408 seconds; original playback began in 160.4-258.7 ms. Cached boxes appeared in 305-337 ms on the two revisited cameras. Fresh CPU inference is not instantaneous. Source/model/configuration-hashed caching, model reuse, selected Fight + Pose, bounded queues and obsolete-selection cancellation remain in use.

## PRIVATE AREA: toilet to sensors/fusion/incident

**PASS for recorded inference and labeled simulation.** Clicking the existing toilet opens the original Three.js room, retaining its geometry, controls and theme. The same browser session executed registered raw TI radar fall inference and local YAMNet Screaming inference. Their separate recorded source identities produced separate OBSERVE incidents; they were not treated as synchronized recordings.

Explicitly labeled simulation then sent independent radar fall + acoustic scream in the same zone/window and created a HIGH fused incident with both supporting event records. Fusion retains the existing explainable rule: independent modalities, same zone/processing mode/analysis group and five-second arrival window. SOS is CRITICAL. These rules are not recognition accuracy or calibrated probability.

The room receives metadata/status, not private footage. Actual recorded class outputs create no located people or measured distances. No radar points were relabeled as occupants. Source fixtures are schematic, not surveyed. Recorded classifications remain static because no validated room-level trajectory/timing is supplied; clearly labeled simulation may animate. Original room Orbit/Zoom/Reset, privacy and responsive checks are covered by the preceding six-check original-room integration suite; the current combined test rechecks real rendering, metadata updates and navigation.

## SOS: assignment, notification and acknowledgement

| Stage | Result | Actual scope |
| --- | --- | --- |
| Private confirmation to SQLite incident | PASS | Explicit prototype SOS, simulation provenance, same EventIn schema |
| Retry after committed event / lost response | PASS | Same event ID, deduplicated original incident |
| On-duty teacher assignment logic | PASS (fixture) | Explicit test-only duty_teacher route; not an actual school teacher |
| Notification preview and shared status | PASS | DISABLED, no external message; assigned fixture teacher visible |
| Dashboard acknowledgement | PASS | Browser Response tab, named fixture reviewer, actual acknowledged_at timestamp |
| Browser reload / fresh backend persistence | PASS | ACKNOWLEDGED state and assignment retained |
| Telegram recipient/routing safeguards | PASS (mock transport) | Existing isolated tests confirm TEST recipient, no staff fallback, dedup and privacy |
| Telegram API acceptance / real recipient delivery | NOT TESTED | Actual service: mode disabled, test_configured false, no routes |
| Acknowledgement by a verified real teacher identity | NOT TESTED | MVP uses authenticated local dashboard plus entered staff name; no verified teacher identity provider |
| Inbound Telegram acknowledgement | NOT IMPLEMENTED | Existing supported acknowledgement path is the dashboard; Telegram receipt/read is not inferred |

The user indicated they will configure the authorized Telegram test locally. At the last readiness check no `.env` file, bot token, test chat or staff route file was available to the current environment, and the running backend reported NOT_CONFIGURED. No secrets were printed or copied into test evidence.

To complete real delivery, configure the existing `.env`/service environment using `.env.example`, an active real duty_teacher/teacher route using `staff-routes.example.json`, and the authorized TEST chat. Reload services through the existing `scripts/start_services.py` workflow after configuration. The existing `scripts/test_telegram_dispatch.py` is a read-only readiness check by default; `--send-test` explicitly sends to the configured TEST chat only. Actual Telegram acceptance must be recorded as SENT with a message ID, receipt checked in that chat, and the corresponding incident acknowledged in the dashboard. No production/staff or emergency dispatch is enabled by this integration.

## Shared schema, records, evidence and reports

All public video, sensor replay, simulation and SOS use the existing FastAPI EventIn/event policy and SQLite incident records. Status changes use existing acknowledgement/review endpoints; pages share actual incident IDs. Public retained video/annotation metadata stays restricted to public zones. Private evidence stays metadata-only, including report exports. Processing mode and test/source provenance are preserved.

A fresh FastAPI process reloaded a copied integrated database: **43 record bodies unchanged**, acknowledged SOS retained, two public evidence references retained, zero private video references. Separate actual-dashboard read-only verification preserved **all 696 existing user record hashes**, including **73 original incidents**. Test runs used separate SQLite/evidence/cache locations and did not inject test incidents into the user's database.

Reports were independently verified against a read-only copy of the existing 73 SQLite incidents: CSV fields and charts match backend data; downloaded and printed PDF use the same filtered dataset/layout; both contain vector charts and permitted evidence thumbnails. Original date/zone/severity/type filtering, legacy routes and single combined navigation work. Empty/private selections and 300-record pagination pass.

Eight generated PDFs / **81 pages** were inspected for A4 bounds and text overlap/clipping. Minimum measured evidence-image resolution: **297.4 DPI**. Downloaded and printed visual PDFs are eight pages each, with four permitted evidence images each. Headless Chromium verifies the print document, print invocation, print media and generated PDF; the native Windows print dialog was not manually operated.

## Executed checks

| Suite / check | Actual result |
| --- | --- |
| tests/test_mvp_end_to_end.py | 11 PASS, zero FAIL, real browser/API/models/sensors |
| tests/test_mvp_persistence.py | PASS, fresh backend reload of actual integrated test records |
| tests/test_mvp_acknowledgement_reload_browser.py | PASS, persisted acknowledged state visibly shown |
| tests/run_cpu_monitoring_checks.py | 65 PASS, zero failures/errors |
| tests/run_analytics_reports_backend.py | 58 PASS, zero failures/errors; overlaps some core regressions |
| test_fight_participants.py | 4 PASS, provenance/abstention logic |
| TypeScript unit tests | 36 PASS, zero failures |
| tests/test_analytics_reports_final_browser.py | 9 PASS, actual CSV/PDF/Print/privacy/navigation |
| tests/inspect_analytics_reports_final.py | 8 PDFs, 81 pages; vector charts, no clipping/major text overlap |
| npm run lint | PASS, tsc --noEmit |
| npm run build | PASS; pre-existing Vite config/chunk warnings remain |
| Actual running dashboard read-only smoke | PASS, no browser errors, zero created events, 696 user record hashes unchanged |
| Actual Telegram transport | NOT TESTED, configuration pending |

### Combined browser scenarios

| Scenario | Result |
| --- | --- |
| Public camera autoplay genuine Fight + Fall evidence and incident: CAM_CORRIDOR_A | PASS |
| Public camera autoplay genuine Fight + Fall evidence and incident: CAM_CANTEEN | PASS |
| Public camera autoplay genuine Fight + Fall evidence and incident: CAM_STAIRCASE | PASS |
| Public camera autoplay genuine Fight + Fall evidence and incident: CAM_ENTRANCE | PASS |
| Public camera autoplay genuine Fight + Fall evidence and incident: CAM_HALL | PASS |
| Cached synchronized camera replay: CAM_CORRIDOR_A | PASS |
| Cached synchronized camera replay: CAM_HALL | PASS |
| Public incident reaches existing Digital Twin shared state | PASS |
| Toilet original room to real sensor inference / labeled fusion / same SQLite incidents | PASS |
| Confirmed private SOS / idempotent retry / fixture teacher / notification preview / browser acknowledgement | PASS |
| Shared state reports CSV legacy routes Alerts privacy and original feature preservation | PASS |

## Test evidence

- [Combined browser assertions](runtime/mvp-integration/results.json)
- [Measured cold/cached latency and actual counts](runtime/mvp-integration/performance.json)
- [UR Fall red binary-rule overlay](runtime/mvp-integration/CAM_STAIRCASE-cold.png)
- [AIRTLab Fight result and real person detections](runtime/mvp-integration/CAM_CORRIDOR_A-cold.png)
- [Cached Hall replay](runtime/mvp-integration/CAM_HALL-cached.png)
- [Public Digital Twin risk](runtime/mvp-integration/public-digital-twin.png)
- [Private sensor fusion](runtime/mvp-integration/private-sensor-fusion.png)
- [Persisted SOS assignment and acknowledgement](runtime/mvp-integration/sos-assignment-acknowledgement.png)
- [Acknowledgement browser reload assertions](runtime/mvp-integration/acknowledgement-reload-results.json)
- [Fresh backend persistence](runtime/mvp-integration/persistence-results.json)
- [Correct acknowledged filtered CSV](runtime/mvp-integration/filtered-incidents.csv)
- [Actual running dashboard data preservation](runtime/mvp-integration/actual-smoke-results.json)
- [PDF/CSV/print browser results](runtime/analytics-reports-final/results.json)
- [Independent PDF page inspection](runtime/analytics-reports-final/pdf-inspection.json)
- [Downloaded visual PDF](runtime/analytics-reports-final/download-visual.pdf)
- [Printed visual PDF](runtime/analytics-reports-final/print-visual.pdf)
- [Download KPI/chart page inspection](runtime/analytics-reports-final/download-visual-page-1.png)
- [Printed distribution chart page inspection](runtime/analytics-reports-final/print-visual-page-2.png)

Fall, acknowledged SOS and PDF chart screenshots were opened for visual inspection. The first CSV check revealed stale acknowledgement fields; that bug was corrected and the final test asserts the actual acknowledged timestamp and review state. An initial screenshot captured the moment before React rendered acknowledgement; the final screenshot was regenerated from the persisted ACKNOWLEDGED record and verified after reload.

## File changes in this completion pass

Application:

- dashboard/src/components/analysis/CameraMonitoringPanel.tsx - refresh shared context on completed cache hit.
- dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx - confirmed SOS in-flight guard and stable retry ID.
- dashboard/src/components/incidents/IncidentEvidence.tsx - notification busy guard and shared/parent refresh.
- dashboard/src/components/incidents/IncidentReportView.tsx - identity-safe loading, awaited parent refresh after response mutation, readable labels.
- dashboard/src/pages/AnalyticsReportsPage.tsx - refresh the selected filtered snapshot after incident response changes.

Tests / evidence documentation:

- tests/test_mvp_end_to_end.py (new)
- tests/test_mvp_persistence.py (new)
- tests/test_mvp_acknowledgement_reload_browser.py (new)
- MVP_INTEGRATION_RESULTS.md (new)

No Overview/Alerts styling, inference/model implementation, trained weights, dataset, database schema, original private room geometry or original ZIP archive was changed in this completion pass. Existing generated dashboard/dist output was rebuilt.

## Remaining limitations

- No physical camera/radar/acoustic/SOS installation was connected or verified. Research recordings assigned to demo zones are not footage/measurements from the school.
- No synchronized real radar/audio acquisition timestamps, calibrated occupancy, room coordinates, per-person sensor trajectories or measured separation are available. Independent recorded classifications cannot establish real multimodal corroboration.
- Possible fall is an experimental tracked pose rule; fight-participant heuristics are experimental and may abstain/misidentify. Model scores are not demonstrated recognition accuracy or calibrated probabilities. Human review remains required.
- Fresh CPU latency is seconds; cached recorded playback is fast but is not live inference. Measurements are single-machine samples.
- Teacher routing can only be verified against actual locally supplied duty assignments. Telegram API delivery/read receipt and real teacher acknowledgement remain unverified until configured and exercised. No messaging was simulated as actual external delivery.
- Native Windows print-dialog interaction and production identity/emergency dispatch are outside the verified local MVP.
