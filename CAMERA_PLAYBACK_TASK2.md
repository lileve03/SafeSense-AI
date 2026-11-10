# Task 2: public-area camera playback

Targeted changes: backend/registry.py assigns existing daily-activity research recordings to the previously empty Entrance and Hall demo feeds. dashboard/src/components/analysis/CameraMonitoringPanel.tsx preserves its styling and model integration, explicitly starts muted playback after metadata loads, keys the player by camera and source, guards asynchronous polling by selection generation, and clears results on selection. Native controls and Replay remain available. Missing-source cards can be opened and show "No recording configured." without retaining a previous video. Camera name, zone, elapsed video time, Recorded/Precomputed/Live source classification and research source path are visible.

## Sources

All paths are relative to the repository. Every default feed is a recorded research demonstration, not footage of the actual school. No physical live camera is configured or verified. Private zones are excluded by the existing backend registry policy; original private room/sensor protections remain.

AIR root: `datasets/open_hidden/fighting/raw/AIRTLab/A-Dataset-for-Automatic-Violence-Detection-in-Videos-master/violence-detection-dataset/`

| Camera | Zone | Existing source file | Source type |
| --- | --- | --- | --- |
| Corridor A / CAM_CORRIDOR_A | ZONE_CORRIDOR_A | AIR root + violent/cam1/97.mp4 | Recorded AIRTLab violent |
| Canteen / CAM_CANTEEN | ZONE_CANTEEN | AIR root + non-violent/cam1/1.mp4 | Recorded AIRTLab non-violent |
| Staircase / CAM_STAIRCASE | ZONE_STAIRCASE | datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4 | Recorded UR Fall |
| School Entrance / CAM_ENTRANCE | ZONE_ENTRANCE | datasets/open_hidden/test_videos/adl-01-cam0-rgb.mp4 | Recorded UR Fall daily activity |
| School Hall / CAM_HALL | ZONE_SCHOOL_HALL | datasets/open_hidden/test_videos/adl-02-cam0-rgb.mp4 | Recorded UR Fall daily activity |

The Scenario Testing Library additionally contains the alternate AIRTLab camera recordings and UR Fall fall-01 clip; no replacement downloads, fabricated videos, model training or dataset changes were necessary. Synthetic monitoring diagrams remain explicitly labeled simulations. Configured operator overrides still take precedence. Invalid/missing recording assignments show the missing-source message. An unreachable configured live camera reports an availability error; configuration alone does not establish that hardware works.

## Dataset terms (official sources checked 2026-10-29)

- AIRTLab: https://github.com/airtlab/A-Dataset-for-Automatic-Violence-Detection-in-Videos ? Dataset Release Agreement permits research and educational use and requests citation: Bianculli et al., A dataset for automatic violence detection in videos, Data in Brief 33 (2020), doi:10.1016/j.dib.2020.106587. Do not infer an unrestricted commercial license.
- UR Fall: https://fenix.ur.edu.pl/~mkepski/ds/uf.html ? CC BY-NC-SA 4.0, intended for non-commercial academic use; commercial purposes require contacting the authors. Requested citation: Kwolek and Kepski, Human fall detection on embedded platform using depth maps and wireless accelerometer, Computer Methods and Programs in Biomedicine 117(3), 2014, pp.489?501. Existing local MP4s are used as research replays, not live school feeds.

## Browser codec handling

Active-app playback without model results exposed that local UR Fall MP4s could not decode directly in Chromium. backend/browser_video.py now supplies content-addressed H.264/yuv420p, fast-start silent playback derivatives in runtime/playback when compatibility cannot be confirmed. backend/main.py serves these through the same authenticated, seekable source endpoint. Original files and inference inputs remain unchanged. FFmpeg failure is an explicit 503. Cache creation is locked and atomic; no video download or invented frames are used. FFmpeg is required for unsupported codecs.

## Verification

- tests/test_camera_playback.py runs isolated backend, inference and Vite services with a temporary SQLite database and Telegram disabled. Actual Chromium media decoding/playback is used for all five feeds, with real video HTTP requests and existing model execution; media and inference responses are not mocked. It checks dimensions, duration, advancing time, muted autoplay, controls, pause, seek, replay, completed analysis, correct camera identity and rapid switching. See runtime/camera-playback-task2/results.json and per-camera screenshots for actual results.
- tests/test_camera_unavailable.py uses a clearly scoped missing-registry metadata fixture to exercise unavailable UI handling; it does not fabricate detections or media. See runtime/camera-playback-task2/unavailable.json.
- TypeScript checking and Vite production build passed. Existing Vite configuration and bundle-size warnings remain.
- Overview and Alerts source files remain unchanged; the existing read-only Overview/Alerts browser regression is also run.

First browser run exposed an overly narrow test assertion: short clips had already switched to the genuine completed YOLO annotation before the URL was sampled. The test now verifies the actual registered raw-source request and accepts its resulting real annotation. This was a test correction, not invented playback.

Final result artifacts include activation.json: each original source played in the active dashboard with analysis submissions blocked in that browser only, proving autoplay is independent of annotated results. The isolated inference suite separately exercises real jobs. During diagnosis one actual Corridor A analysis ran on the active app and created one additional genuine test incident (18 to 19 records); all 18 existing incident records were retained unchanged. No incident deletion or staff notification was used.

Changed source files: backend/registry.py, backend/main.py, backend/browser_video.py, dashboard/src/components/analysis/CameraMonitoringPanel.tsx. Added verification scripts: tests/test_camera_playback.py, tests/test_camera_unavailable.py, tests/test_camera_activation.py. This report and generated dashboard/dist build assets/runtime evidence are also updated.

Final checks: all five active-app original-source playbacks PASS; missing-source browser case PASS; Overview/Alerts regression PASS; TypeScript PASS; production build PASS (existing configuration/bundle-size warnings). Full per-camera model/playback results are in results.json.
