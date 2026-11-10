# SafeSense person-level fight candidate overlays

Implemented and verified 29 October 2026. **Red person boxes come from a separate measured pose-interaction heuristic; V2/V3 remain whole-clip classifiers and do not produce fighter boxes.** Existing video-level classifier banners and scores remain visible.

## Heuristic logic

`backend/fight_participants.py`, version `pose-interaction-v1`, uses actual YOLO boxes/keypoints and their source timestamps:

1. Require the selected real V2/V3 classifier's positive result and actual score at/above its own configured threshold. Require the pose and classifier source SHA256 to match. Because the classifier has no localized event window, this gate spans its actual analyzed clip, not an invented fight interval.
2. Associate actual detections between frames using one-to-one Hungarian assignment. Cost combines box IoU (0.45), normalized center displacement (0.30), and median shared-keypoint displacement (0.25). Require at least six shared confident keypoints, center displacement below 0.45 person heights, assignment cost below 0.65, and a uniqueness margin above 0.06. Ambiguous/missing associations reset; no predicted or interpolated boxes are created. This interaction tracker is separate from the existing fall-rule tracker.
3. Eligible persons require detector confidence at least 0.4, keypoint confidence at least 0.5, and at least four associated observations.
4. A pair must be within 0.9 average detected-person heights in 2D screen space. Motion uses wrist position relative to the corresponding shoulder, reducing whole-body walking/camera-motion effects. Require arm speed of 1.2?8 normalized person heights/second, directed approach toward the other person's upper-body keypoints of at least 0.4 heights/second, and wrist proximity within 0.3 average heights.
5. Require at least three supporting frames spanning at least 0.1 seconds in a 0.6-second history, with at least two directed-motion observations **from each person**. Proximity alone, one person's motion, and a positive clip classifier alone cannot create a red participant.
6. A supported pair can remain active for up to 0.12 seconds after its last measured interaction while both current detections remain associated and close. Only current genuine boxes are rendered. No stale identity or geometry is extrapolated.

These distances/speeds are normalized **2D image measurements**, not physical meters, actual 3D contact or confirmed aggression.

## Participant score

The score is a deterministic, uncalibrated evidence-strength value from 0 to 1:

```
proximity = max(0, 1 - pair_center_distance_heights / 0.9)
arm_motion = min(1, maximum_observed_relative_arm_speed / 3)
persistence = min(1, supporting_frames_in_window / 6)
participant_score = 0.35 * proximity + 0.40 * arm_motion + 0.25 * persistence
```

The supported pair's measured score is assigned to its two candidate participants. If a person belongs to multiple supported pairs, its strongest measured pair score is used. The score is **not** V2/V3 confidence, not a calibrated probability, and not an aggressor/victim classification. Each red person is labeled `POSSIBLE FIGHT` and `participant score: ... | heuristic`. Other persons remain cyan. Existing binary fall labels remain separate, including when both conditions are supported.

Every candidate carries its interaction track IDs, proximity, measured peak arm speed, supporting-frame counts, reciprocal counts, source window and score components. Interaction timeline markers are actual heuristic timestamps, not classifier-localized fight events.

## Actual recording behavior

Real inference and Chromium playback were used. The four files are two AIRTLab scenes from two camera angles, not four independent behavioral scenarios. No model weights, training data, source videos or thresholds were changed.

| Recording | Actual V3 clip score | Pose frames | Frames with red participants | Participant analysis + metadata CPU time | Result |
|---|---:|---:|---:|---:|---|
| AIRTLab violent/cam1/97.mp4 | 0.984895 | 165 | 32 | 0.372 s | PASS |
| AIRTLab violent/cam2/97.mp4 | 0.907331 | 165 | 0 | 0.307 s | PASS |
| AIRTLab non-violent/cam1/1.mp4 | 0.092352 | 158 | 0 | 0.129 s | PASS |
| AIRTLab non-violent/cam2/1.mp4 | 0.275407 | 158 | 0 | 0.017 s | PASS |

Camera-1 violent recording: **32 frames / 64 person-frame candidates**, consistently interaction tracks 1 and 2. Visual inspection shows the man in white and the woman in black receiving red boxes during the supported interaction. The woman in blue and woman in beige remain cyan. The first supported event is at 1.400 s; its score is 0.8035 (displayed to three decimals). Across flagged frames, measured participant scores range from 0.5055 to 0.9039.

Actual red intervals, end-exclusive at 30 FPS:

- 1.400?1.833 s
- 3.233?3.567 s
- 3.633?3.867 s
- 3.933?4.000 s

Camera-2 violent recording: V3 is positive at 0.907331, but the available poses do not satisfy the reciprocal interaction gates. **Only the red video-level banner appears; all person boxes stay cyan.** This is intentional abstention rather than inventing participants from the clip label.

Both tested non-fight recordings produce zero participant frames. Entrance/Hall switching also produces no stale fight candidates, and the original UR Fall binary red box remains functional.

### V2 independently verified

A separate test configured **V2 + Pose only**, without also running V3:

- Violent cam1/97: actual V2 score **0.9745275974273682**, 32 participant frames / 64 person-frame candidates; browser screenshot shows a V2 banner and the separate heuristic participant score.
- Non-violent cam1/1: actual V2 score **0.05313368886709213**, zero red participant frames.

V2 and V3 can share the same participant score on the same poses because the localization score is computed from measured interaction features, not from the classifier score.

## Browser screenshots inspected

These images were opened and visually inspected, including actual playback before native seeking:

![V3: two supported participants red, two bystanders cyan, independent scores](runtime/fight-participants/verification/CAM_CORRIDOR_A-participants.png)

![V2: classifier score differs while the separate pose heuristic remains explicit](runtime/fight-participants/v2-verification/v2-participants.png)

Additional evidence:

- [Natural playback before seeking](runtime/fight-participants/verification/CAM_CORRIDOR_A-natural-playback.png)
- [Complete dashboard](runtime/fight-participants/verification/CAM_CORRIDOR_A-dashboard.png)
- [Positive V3 camera-2 classifier with no reliable localized participants](runtime/fight-participants/verification/CAM_FIGHT_CAM2-no-participants.png)
- [Actual non-fight recording, cyan people](runtime/fight-participants/verification/CAM_CANTEEN-no-participants.png)
- [Actual non-fight camera 2](runtime/fight-participants/verification/CAM_NORMAL_CAM2-no-participants.png)
- [Corresponding incident Audit Details evidence](runtime/fight-participants/verification/audit-participant-evidence.png)
- [Existing fall overlay preserved](runtime/fight-participants/verification/fall-preserved.png)

## Evidence, cache and integration

- Original V2/V3 outputs, actual detector boxes/keypoints and existing evidence captures remain unchanged. Combined results add separate `participant_heuristic`, `participant_events`, and person-level fields on copied frame metadata.
- Existing incident media receive provenance-bound sidecar metadata tied to the same analysis ID, source SHA256, camera and retained clip interval. Audit Details replays the corresponding source-aligned person overlays. The original recorded MP4 remains original; participant labels are replayed from metadata, not claimed to be permanently burned into every downloaded clip.
- No new backend incident, alert or external message is generated by the interaction heuristic. Existing classifier/fall capture and delivery paths remain in charge.
- Heuristic implementation and SciPy version participate in cache identity. Cached result frames were exactly equal to the computed frames; replay created no additional events/incidents.
- Private video remained HTTP 403. Registry camera validation, generation guards, actual frame selection, autoplay and original page styling remain in place.
- Actual local AI worker on port 8001 was refreshed only after confirming it was idle and identifying its SafeSense command. Its health endpoint now reports `participant_heuristic: pose-interaction-v1` ([service status](runtime/fight-participants/actual-service-status.json)). The main backend and dashboard services were preserved.

## Actual validation results

| Check | Result |
|---|---|
| V3 actual-recording/browser integration | 8 PASS / 0 FAIL |
| V2-selected actual-recording/browser integration | 2 PASS / 0 FAIL |
| Python participant/track/identity safety tests | 10 PASS |
| TypeScript overlay/identity/camera contract tests | 14 PASS |
| Existing backend regression runner | 65 PASS / 0 failures/errors |
| TypeScript compiler | PASS |
| Production build | PASS; existing Vite config/large-chunk warnings remain |
| Browser participant boxes and score labels | PASS, inspected screenshots |
| Natural playback, pause, seek and camera switching | PASS |
| Incident metadata, clip byte ranges and Audit Details | PASS |
| Alerts and Digital Twin navigation | PASS |
| Privacy and no duplicate cached events | PASS |

The browser suite compares every enriched box and keypoint to the corresponding original pose output to ensure localization is not fabricated. It also tests the same actual poses with classifier support removed and with a mismatched source hash; both controls abstain. An early browser assertion incorrectly used HTMLElement `innerText` on SVG; it was corrected to `textContent`, then the complete final suites passed.

Raw results: [V3 suite](runtime/fight-participants/verification/results.json), [V2 suite](runtime/fight-participants/v2-verification/results.json), [backend regressions](runtime/cpu-visualization/backend-results.json). Full genuine frame JSON is retained in each verification directory.

## Files modified

- backend/fight_participants.py ? new measured interaction association, gates, score and timestamps.
- monitoring_ai.py ? combined-result enrichment, source-bound evidence metadata and cache versioning.
- backend/incident_media.py ? preserve validated participant geometry alongside the classifier banner in evidence manifests.
- fight_api.py ? health contract for the participant heuristic.
- requirements-inference.txt ? explicitly declare the already-installed SciPy 1.18.1 dependency; no packages installed or model files changed.
- dashboard/src/lib/videoDetections.ts ? strict participant provenance/score rendering guard.
- dashboard/src/components/analysis/VideoDetectionOverlay.tsx ? specific red participant boxes/skeletons with readable two-line labels.
- dashboard/src/components/analysis/DetectionResults.tsx ? distinct score explanation and real interaction timeline markers.
- dashboard/src/components/incidents/IncidentMedia.tsx ? evidence score/provenance explanation.
- tests/test_fight_participants.py ? new backend safety tests.
- tests/videoDetections.test.ts ? participant rendering safeguards.
- tests/test_fight_participants_browser.py ? real V3/AIRTLab/browser/evidence/switching/privacy verification.
- tests/test_fight_participants_v2_browser.py ? real selected-V2 fight/non-fight browser verification.
- FIGHT_PARTICIPANT_OVERLAY_RESULTS.md ? this report.

Build outputs under dashboard/dist and isolated verification artifacts under runtime/fight-participants were generated. Test services were stopped and notifications disabled. Original user incident records, dashboard design, datasets and model checkpoints were preserved.

## Limitations

This is a conservative **experimental interaction heuristic**, not a trained participant localizer or proof of aggression. Reciprocal fast gestures, sports or play can resemble fighting when the clip classifier is also positive. Occlusion, poor keypoints, fast movement, tracking ambiguity and viewpoint changes can cause missed participants; camera-2 abstention demonstrates that limitation. Normalized 2D proximity does not prove physical contact. Local track IDs do not establish a person's real identity or distinguish aggressor from victim. Only a small set of AIRTLab scenes was tested; no general precision/recall or calibrated-probability claim is made.

After refreshing the dashboard, select a camera again to compute the updated genuine cached analysis. Older saved results without interaction metadata remain video-level-only. First fresh CPU analysis is not instantaneous; subsequent visits replay the source/model/configuration-matched cache.
