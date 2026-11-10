# SafeSense detection overlay results

Implemented and verified 29 October 2026 on CPU-only Windows. No model output, coordinates, timestamps or numeric fall scores were fabricated.

## Root cause and changes

The old fall rule accumulated the highest-confidence detection across frames without tracking, potentially combining different people's histories. Candidate boxes were orange, fight-score semantics were unclear, and incident playback lacked corresponding frame metadata. Evidence seeking also updated overlays before the target video frame had decoded.

- Actual YOLO boxes/keypoints remain unchanged; normal boxes are cyan. Source dimensions and decoded timestamps align the SVG with letterboxed playback.
- Added recording-local conservative IoU association (minimum overlap 0.2). Only unique one-to-one matches retain history; missing or ambiguous matches reset it. This is spatial tracking, not identity recognition.
- The experimental binary rule requires at least three observed upright frames followed by persistent horizontal posture (five observations in a twelve-frame window) on the same continuous track. Only its active supported subject receives a red POSSIBLE FALL box. Horizontal posture without the transition remains a separate review candidate, without a red person box. Legacy untracked candidates cannot activate red boxes.
- Fall labels explicitly show binary ACTIVE and separate actual person-detector confidence. The rule has no trained numeric fall score.
- Positive Fight V2/V3 results use a red POSSIBLE FIGHT video-level banner, actual version and uncalibrated classifier score. Person boxes never identify fighters. Whole-video scope is explicit; no exact fight timestamps are invented.
- Real pose-event timestamps include the local track ID and remain seekable. Camera identity guards, autoplay, asynchronous inference completion and genuine cached replay remain in use.
- Retained pose evidence has provenance-bound overlay metadata (analysis ID, source SHA256, camera and source timestamps). Audit Details and Live Monitoring evidence previews use the same overlay component, with clip-start offsets and decoded-frame callbacks. Seeking hides pose geometry until a decoded frame is available. Original clips remain original files; optional saved pose annotations contain the supported colored boxes and actual skeletons.
- Tracker implementation participates in cache hashing. Evidence overlay sidecars follow evidence deletion/retention. Private-area media authorization remains enforced before metadata/media access.

## Actual verification

| Check | Result | Evidence |
|---|---|---|
| TypeScript | PASS | npm --prefix dashboard run lint |
| Production build | PASS | npm --prefix dashboard run build; existing Vite native-config and bundle-size warnings remain |
| Backend regressions | PASS | 65 tests; queue, durable cache, privacy, incidents, notifications and Overview; runtime/cpu-visualization/backend-results.json |
| TypeScript overlay/contracts | PASS | 10 tests: timestamp lookup, missing frames, keypoint confidence, legacy-red suppression and camera contracts |
| Track attribution | PASS | 5 Python tests: binary transition, horizontal-only abstention, missing/ambiguous reset, replacement-person reset and only one supported subject turning red |
| Actual recordings/browser | PASS | 9 checks; runtime/visual-overlays/results.json |
| Evidence decoded seeking | PASS | 2 focused checks; runtime/audit-seek-check/results.json |
| Fresh retained annotated file | PASS | Genuine 110-frame UR Fall inference and MP4 encoding; runtime/retained-overlay-check/results.json |
| Physical live cameras | NOT TESTED | Recording playback only; no connected live hardware claimed |
| Clinical/benchmark validation of fall accuracy | NOT TESTED | Experimental posture heuristic; observed rule activation is not confirmation of an injury |

School Entrance (UR Fall ADL01, 150 frames) and School Hall (ADL02, 180 frames): actual boxes independently matched YOLO inference, skeletons visible, forward/backward seeking and autoplay passed; neither recording produced red fall boxes. Rapid camera switching and mobile overflow checks passed without browser errors.

UR Fall fall-02: 110 genuine frames. Supported track 1 first triggered at source frame index 63 / 2.100 seconds; the fresh retained run had 33 supported red frames. Frame 80 / 2.666667 seconds was inspected in both decoded Audit Details playback and the newly encoded MP4. Fall score is null, explicitly binary. The separate fresh inference took 20.279 seconds, with 6.932 pose-predict FPS during concurrent test activity; this is not an isolated CPU throughput benchmark or instant fresh inference.

AIRTLab violent cam1/97: 165 genuine pose frames; V3 score 0.9848954677581787, red video-level banner, cyan person boxes and no fighter localization. V2 backend classification was separately exercised on an actual UR recording (score 0.47800374031066895); its score is reported as a classifier output, not ground truth.

Cached fall replay returned the exact stored 110 frames in 364.05 ms (memory cache) without inference. Private video submission returned HTTP 403. This is one measured API response, not a universal camera-click latency guarantee. Cold runs continue to show Preparing analysis; cached outputs are explicitly recorded inference, not live inference.

## Inspected images

- [Live supported fall](runtime/visual-overlays/actual-fall-overlay.png)
- [AIRTLab whole-video fight banner and genuine person skeletons](runtime/visual-overlays/actual-airtlab-fight.png)
- [Decoded evidence seek, frame 80](runtime/audit-seek-check/fall-decoded-seek.png)
- [Fresh saved annotated MP4 frame](runtime/retained-overlay-check/retained-fall-frame.png)

The earlier screenshot caught a seek before decoding finished; the decoded-frame fix and focused rerun supersede that screenshot. An earlier cache privacy test used an unregistered zone; the corrected final nine-check run uses ZONE_TOILET_BLINDSPOT and passes.

## Modified files

- fight_api.py
- monitoring_ai.py
- backend/pose_tracking.py (new)
- backend/incident_media.py
- scripts/safesense_temporal_fall.py
- dashboard/src/lib/videoDetections.ts
- dashboard/src/components/analysis/VideoDetectionOverlay.tsx
- dashboard/src/components/analysis/DetectionResults.tsx
- dashboard/src/components/incidents/IncidentMedia.tsx
- tests/test_pose_tracking.py (new)
- tests/videoDetections.test.ts
- tests/test_visual_overlays.py
- tests/test_retained_pose_overlay.py (new)
- tests/test_evidence_overlay_seeking.py (new; runs after the recording suite and reuses only its isolated DB/evidence)
- LIVE_MONITORING_OVERLAY_RESULTS.md (this file)

Build output under dashboard/dist and test evidence/logs under runtime were regenerated. Original incident data and user services were not replaced or stopped. Tests used isolated SQLite databases and disabled external notifications.

## Limitations

IoU association deliberately abstains after missing/ambiguous matches and can miss falls during occlusion or fast movement. It is not persistent identity recognition. The posture rule remains experimental and uncalibrated. Fight classification has no participant localization or validated within-clip event time. Legacy retained clips without matching frame metadata retain their original/available saved annotations; they do not receive invented tracks. Updated inference invalidates prior analysis caches and requires a genuine first recomputation. Restart the application's AI service to load the backend changes; isolated test services have been stopped.
