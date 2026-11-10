# Scenario testing results — 28 October 2026 (Singapore)

## Executed actual-input suite

`tests/test_scenario_library.py`: **20/20 PASS**. This executes every registered fresh source, not simulated detection buttons, and additionally exercises both existing radar benchmark algorithms.

| Existing source | Executed model | Actual output |
|---|---|---|
| AIRTLab violent/cam1/97.mp4 | V2, V3, YOLO11-Pose | V3 0.9848954677581787; fight candidate; real pose overlay; no fall label is inferred from AIRTLab ground truth |
| AIRTLab non-violent/cam1/1.mp4 | V2, V3, YOLO11-Pose | V3 0.09235220402479172; no conflict flag |
| AIRTLab violent/cam2/97.mp4 | V2, V3, YOLO11-Pose | V3 0.9073311686515808; conflict candidate |
| AIRTLab non-violent/cam2/1.mp4 | V2, V3, YOLO11-Pose | V3 0.2754074037075043; no conflict flag |
| UR Fall fall-02-cam0-rgb.mp4 | Actual YOLO + existing temporal rule | Possible-fall candidate; retained real evidence |
| UR Fall fall-01-cam0-rgb.mp4 | Actual YOLO + existing temporal rule | Possible-fall candidate |
| UR ADL adl-01-cam0-rgb.mp4 | Actual YOLO + existing temporal rule | No candidate |
| UR ADL adl-02-cam0-rgb.mp4 | Actual YOLO + existing temporal rule | No candidate |
| Raw radar Areeb_back_1.csv | Fresh features + reconstructed held-out SVM | 0.9932906517861326; fall candidate |
| Raw radar Areeb_squat_4.csv | Fresh features + reconstructed held-out SVM | 0.21749784996737054; no fall flag |
| Same raw radar fall file | Reconstructed held-out RandomForest | 0.825; matches original saved benchmark reference |
| Existing FSD50K 355741.wav | Fresh cached-pretrained YAMNet | 0.9465681314468384; scream candidate |
| Existing FSD50K 37199.wav | Fresh cached-pretrained YAMNet | 0.0009683079551905394; no scream flag |

These are selected dataset outcomes, not an estimate of school accuracy or validated live performance. Ground-truth labels do not force outputs. Fall logic remains experimental; fight classifiers have no validated person/event localization. Acoustic classification uses a weak clip-level maximum score and does not transcribe speech. Radar models are explicitly reconstructed LOSO benchmarks, not a pre-existing serialized estimator.

The suite also executed source/prerequisite validation, authenticated API rejection, invalid IDs/model/modality checks, private-video override rejection, private raw-audio streaming rejection, missing-model handling without simulated fallback, separation of unrelated radar/acoustic incidents, persistence through backend restart, browser raw-radar inference and incident navigation, and SHA256 preservation checks.

## Preservation evidence

All **19 selected original source/model/research artifacts** had identical before/after hashes. This includes registered raw inputs/video files, root YOLO weights, V2/V3 classifiers, original radar features/predictions and acoustic predictions. Full hash evidence: `runtime/scenario-library-tests/preserved-artifacts.json`. This is a targeted preservation check, not a claim that every repository file was hashed.

Full executed results: `runtime/scenario-library-tests/results.json`. Worker output and logs: `runtime/scenario-tests`. Browser screenshot: `runtime/scenario-library-tests/fresh-radar-library.png`. Scenario history/results are stored in each test's isolated SQLite database; the running application uses its normal runtime database.

## Existing feature regressions

- Monitoring/report integration: **21/21 PASS**, including real V2/V3/YOLO, evidence, original private-room entry, report acknowledgement/resolution and the original browser-suite wrapper. Results: `runtime/real-monitoring-tests/results.json`.
- Original browser suite inside that wrapper: **13/13 PASS** for upload/preview, acknowledgement, map sync, SOS, pose video playback, saved replay, controlled fusion, filters, metrics, CSV, mobile and runtime errors. Results: `runtime/test-results/browser-results.json`.
- Existing temporal/privacy/evaluation unit suite: **16/16 PASS**.
- Legacy API/model suite: **36/36 PASS**, including actual V2/V3 score equivalence, real pose output, upload limits/privacy, original endpoints and CORS.
- Incident response/security suite: **10/10 PASS**.
- Telegram routing/safety suite: **13/13 PASS** with mocked HTTP only.
- TypeScript and production build: **PASS**. Existing Vite large-bundle/__dirname warnings remain advisory.

The 13 original browser checks are nested in the 21-check integration wrapper; these counts should not be blindly summed as independent tests. Legacy API/model outcomes are also recorded in `runtime/test-results/results.json`.

## Errors found and corrected

1. Legacy sensor scenarios returned saved predictions instead of fresh inference. Fresh raw-data paths now execute separately while retaining legacy replay semantics.
2. Adding raw sensor entries to the existing registry would have sent those IDs to legacy simulated/replay controls. Legacy shortcuts now retain only supported entries; the new testing panel owns fresh raw execution.
3. An early preservation test looked up slash-separated source paths in a Windows-backslash hash dictionary. All raw jobs had executed, but four assertions failed. Paths were normalized and the complete 20-check suite reran successfully.
4. Combined model grading initially risked treating AIRTLab violence labels as fall annotations. Ground-truth comparison is now modality-specific, with unsupported comparisons marked unavailable.
5. Original browser regression exposed navigation starting background camera inference and making an upload return 429. Navigation now previews playback; explicit CCTV-card clicks and Analyze controls still start real models. Final dashboard regression results are recorded separately below/alongside the main monitoring report.

## Remaining unverified conditions

- Physical live cameras, radar, microphones and SOS hardware: NOT TESTED; no availability claimed.
- Actual Telegram receipt: NOT TESTED / not configured. Test suites explicitly disable external dispatch.
- Measured private occupant counts/room positions/distances: unavailable; raw point counts are not people counts.
- Real-world synchronized radar/acoustic recording and calibrated event localization: unavailable.
- Windows default process launch previously produced error 1385, but authorized elevated execution succeeded throughout this task. No current access blocker prevented implementation or testing; no OS account policy was modified.

## Normal-port activation

The tested update is active at http://127.0.0.1:3000 → Live Monitoring → Scenario Testing Library. All eight previous incidents were preserved; their pre-update backup is `runtime/session-backups/20261028T145025Z.json`.

The activated `.venv` backend was verified driving both separate sensor environments from the browser: fresh raw radar produced 0.9932906517861326 and fresh acoustic negative-control inference produced 0.0009683079551905394. Both runs completed with fresh_raw_input_inference provenance; private sensor panels had zero media elements, and the actual radar incident opened successfully. No external notification was sent. Evidence: `runtime/scenario-library-tests/activation.json`; screenshot: `active-fresh-radar.png` in that directory.

The first inline normal-port smoke assertion lost a Unicode separator through the Windows shell and timed out despite a completed correct model run. Encoding-safe assertions were used and the complete activation check passed. This was separate from error 1385, which did not block execution.
