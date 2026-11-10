# SafeSense overlay pipeline diagnosis and fixes

Verified 29 October 2026 against both the actual dashboard on port 3000 and isolated fresh inference/browser services. **10 browser/integration checks PASS, 65 backend regressions PASS, 13 TypeScript unit tests PASS, 6 Python identity/tracking tests PASS; TypeScript and production build PASS.**

## Exact diagnosis

1. **The actual AI worker on port 8001 was stale.** Its saved outputs contained genuine boxes/keypoints but `tracking_available: false`, and persons contained only `bbox_xyxy`, `confidence`, `keypoints`. They had no person-associated fall rule/track state. The newer frontend correctly refused to paint these untracked detections red. The worker also returned the older V2+V3+Pose default rather than the current selected-fight-model policy. The stale process was identified by its exact SafeSense uvicorn command, refreshed, and the actual running health endpoint now reports `overlay_contract: pose-tracks-v2`. Original stored jobs remain readable; no historical tracking metadata was invented.
2. **A blanket absence of all person overlays was not reproduced.** A read-only browser diagnosis of the real app, reusing its genuine saved inference verbatim without submitting AI jobs, showed Entrance at 0.516 s: one box and 15 skeleton edges. Hall at 0.522 s had zero boxes because the genuine model detects no person in frames 0?29. Hall's first actual detection is frame 30 / 1.0 s; Entrance starts at frame 5 / 0.166667 s. Empty early frames are preserved, not filled with fake boxes.
3. **Canonical camera IDs already matched in the deployed data.** Both job/result IDs were CAM_ENTRANCE/CAM_HALL. Strict raw-string equality was nonetheless brittle for legitimate registered names/aliases or case/separator variants. Reproduced boundary cases now have shared registry resolution, not an unconditional identity bypass.
4. **Existing source timing and SVG geometry were valid for these recordings.** FFprobe source presentation timestamps exactly matched all 150/180 serialized frame timestamps (maximum measured error 0.0 s); both videos and annotation dimensions were 640x480 at 30 FPS. The old one-microsecond frame-selection tolerance was unnecessarily strict for slightly quantized decoder times; it could select the preceding frame near a boundary. This boundary behavior is corrected with a bounded tolerance.
5. **The verified Fight schema contains both score and violence_score with identical numeric values.** Missing canonical scores were not the cause in the inspected running records. A validated compatibility fallback now supports the verified alias without fabricating a score or converting missing/string values to zero.

Sources: [actual running JSON](runtime/overlay-diagnosis/CAM_ENTRANCE.json), [running browser diagnosis](runtime/overlay-diagnosis/running-browser-before.json), [fresh JSON audit](runtime/overlay-diagnosis/fresh-json-audit.json), [source PTS audit](runtime/overlay-diagnosis/source-pts-audit.json), [actual service after refresh](runtime/overlay-diagnosis/actual-service-after.json).

## Fixes

- Added frontend `cameraRegistry.ts`, populated only from the shared backend `/monitoring/cameras` registry. Resolve canonical IDs, registered names and explicit aliases case-insensitively with whitespace/hyphen normalization. Unknown, missing, conflicting and ambiguous identities remain rejected; zone/source IDs cannot authorize a camera overlay.
- Backend job submission performs the same registry resolution before validating camera/zone/source and forming the inference cache identity. Alias requests return the canonical registered camera ID; unknown aliases return 422. Public registry output supports explicit aliases.
- Both the panel's result gate and the overlay's identity gate use registry resolution. Incident evidence loads the registry before rendering matching overlay metadata. Strict incident/analysis/source provenance validation remains in place.
- `playbackPoseFrame()` uses the actual serialized frame timestamps, with tolerance `min(2 ms, 5% of the nominal frame interval)` ? 1.667 ms at 30 FPS. Large gaps, expired data and invalid clocks remain rejected; no interpolation or synthetic frames are generated.
- `requestVideoFrameCallback` remains the primary decoded-frame clock. Added a requestAnimationFrame/currentTime fallback for browsers without it; native timeupdate and seek handling remain. A real browser with rVFC disabled showed advancing genuine pose frames 6 to 12.
- Kept the correct source-pixel SVG viewBox and centered contain scaling. Browser measurements independently validated video letterboxing and SVG transforms, rather than changing already-correct geometry. Source box screen positions matched expected video-content positions to less than 0.001 CSS pixels in the measured samples.
- Fight banner uses canonical finite numeric `score`, then verified `violence_score` compatibility alias, with valid range 0?1. It displays the actual V2/V3 version and explicitly uncalibrated classifier score. R3D-18 remains whole-video classification: no fighter-specific boxes or invented fight timestamps.
- Cyan person boxes/skeletons remain actual YOLO outputs. Supported, tracked fall transitions use red POSSIBLE FALL and the actual binary ACTIVE state. Detector confidence is separately labeled; the rule has no numeric fall confidence to display.
- Added a health contract marker and refreshed the actual stale AI service. The main backend and dashboard services were preserved. Supported `/event` idempotent replay verified original recorded-event authentication with zero new events/incidents; no external messages were sent. Live hardware credentials were not needed for the recorded pipeline.

## Fresh actual inference counts

A person instance means one genuine person detection in one analyzed frame, not a unique identity. Keypoint counts include all serialized model points; only finite points with confidence at least 0.5 are drawn.

| Camera | pose_frames | Nonempty frames | Person instances | Serialized keypoints | Supported red frames |
|---|---:|---:|---:|---:|---:|
| CAM_ENTRANCE | 150 | 145 | 145 | 2465 | 0 |
| CAM_HALL | 180 | 150 | 150 | 2550 | 0 |
| CAM_STAIRCASE | 110 | 110 | 121 | 2057 | 33 |
| CAM_CORRIDOR_A | 165 | 165 | 646 | 10982 | 0 |

Entrance and Hall independently matched YOLO boxes on decoded source frames. Every frame was timestamped in original recording coordinates; no missing poses or keypoints were manufactured. Fresh UR Fall has 33 supported red frames on track 1, with the first actual rule event at 2.1 s. AIRTLab V3 score is 0.9848954677581787; the video-level banner is red while visible person boxes remain cyan.

## Browser playback proof

| Camera | Advancing video times | Advancing pose frame indices | Fresh click to visible playing pose observed |
|---|---|---|---:|
| Entrance | 0.2945 ? 0.4979 s | 9 ? 15 | 16.140 s |
| Hall | 1.0046 ? 1.1986 s | 30 ? 36 | 11.156 s |

These timings include actual first uncached CPU work and waiting until a detected person is visible. They are not instant fresh inference. The cached fall API check returned exact genuine frame metadata in 103.87 ms. Timing observations and actual SVG transforms are saved in [Entrance playback proof](runtime/overlay-diagnosis/fresh/CAM_ENTRANCE-playback-proof.json) and [Hall playback proof](runtime/overlay-diagnosis/fresh/CAM_HALL-playback-proof.json).

Passed browser/integration checks include actual playing footage, pause, forward/backward seeks, Entrance/Hall switching, mobile layout, real AIRTLab fight banner, real UR Fall red box, retained incident clips/metadata, Audit Details, registry alias normalization, unknown identity rejection, private video rejection and no-rVFC fallback. Actual JSON and screenshots were checked, not only API responses.

## Screenshots opened and visually inspected

![Entrance genuine boxes and skeleton during recorded playback](runtime/overlay-diagnosis/fresh/CAM_ENTRANCE-actual-playback.png)

![Hall genuine boxes and skeleton after the first actual person detection](runtime/overlay-diagnosis/fresh/CAM_HALL-actual-playback.png)

- [Supported red fall box and binary rule state](runtime/overlay-diagnosis/fresh/actual-fall-overlay.png)
- [AIRTLab red video-level fight banner with normal cyan people](runtime/overlay-diagnosis/fresh/actual-airtlab-fight.png)
- [Incident fall evidence with matching overlay](runtime/overlay-diagnosis/fresh/fall-audit-genuine-overlay.png)
- [Playback fallback without requestVideoFrameCallback](runtime/overlay-diagnosis/fresh/fallback-playback.png)
- [Before: real app Entrance boxes already visible](runtime/overlay-diagnosis/CAM_ENTRANCE-before.png)
- [Before: Hall at a genuine empty detection frame](runtime/overlay-diagnosis/CAM_HALL-before.png)

## Modified files

- dashboard/src/lib/cameraRegistry.ts ? new registry-backed identity resolver.
- dashboard/src/lib/api.ts ? register the backend camera registry response.
- dashboard/src/lib/videoDetections.ts ? bounded timing tolerance and verified Fight score mapping.
- dashboard/src/components/analysis/VideoDetectionOverlay.tsx ? canonical identity guard and score mapping.
- dashboard/src/components/analysis/CameraMonitoringPanel.tsx ? canonical result gating and fallback playback clock.
- dashboard/src/components/incidents/IncidentMedia.tsx ? load shared identities before evidence overlay rendering.
- backend/registry.py ? canonical identity resolver and public aliases.
- monitoring_ai.py ? normalize registered identities before inference/cache validation.
- fight_api.py ? current overlay-contract health marker.
- tests/videoDetections.test.ts ? timing/score regression tests.
- tests/cameraRegistry.test.ts, tests/test_camera_identity.py ? new alias/identity fail-closed tests.
- tests/diagnose_running_overlays.py ? read-only real dashboard diagnosis.
- tests/test_overlay_diagnosis_browser.py ? fresh actual inference and browser geometry/playback integration.
- OVERLAY_PIPELINE_DIAGNOSIS_RESULTS.md ? this report.

Build outputs under dashboard/dist and actual test artifacts under runtime/overlay-diagnosis were regenerated. Models, datasets, original dashboard layout, autoplay, original incident records and privacy rules were preserved.

## Validation and limitations

- `npm --prefix dashboard run lint`: PASS.
- `npm --prefix dashboard run build`: PASS; existing Vite config and bundle-size warnings remain.
- Node overlay/registry/camera contract unit suites: 13 PASS.
- Python camera identity + track safety suites: 6 PASS.
- `tests/run_cpu_monitoring_checks.py`: 65 PASS, zero failures/errors.
- `tests/test_overlay_diagnosis_browser.py`: 10 PASS, zero failures, no browser runtime errors.
- Actual running AI `/health`: PASS, pose-tracks-v2; original authenticated job access: HTTP 200.
- Actual supported recorded-event delivery idempotency: PASS, no new records ([result](runtime/overlay-diagnosis/actual-recorded-delivery.json)).

Fall detection remains an experimental binary rule; it is not a calibrated trained fall classifier or proof of injury. Missing/ambiguous tracking does not authorize a red box. Whole-video Fight outputs do not identify participants. The timing tolerance does not solve arbitrary VFR/transcoded time warps; source timestamps were explicitly validated for these CFR recordings. Physical live cameras/sensors and live emergency dispatch were not tested.

Reload the existing dashboard and reselect a camera to obtain current tracked results from the refreshed AI worker. A first uncached computation is genuine CPU work and may take several seconds; older saved untracked results remain historical evidence, not retroactively fabricated red fall tracks.
