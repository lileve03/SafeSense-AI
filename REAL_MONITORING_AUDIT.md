# Real monitoring audit — 28 October 2026

The repository was inspected in place. No AGENTS.md or Git repository was found at the project root or in the searched source tree. Git history is therefore unavailable. Existing restoration notes and the retained project archive establish the original private-room implementation. No datasets, training code, model weights or evaluation results were rewritten.

| Existing path | Actual behavior before this integration | Integration |
|---|---|---|
| `fight_api.py` | Genuine R3D-18 features + trained V2/V3 classifiers on CPU; upload-driven, whole-video scores, no fight localization | Preserved; camera/scenario jobs invoke these same functions and retain candidate clips |
| YOLO fall API | Genuine YOLO11-Pose boxes/skeletons burned into video; experimental temporal posture rule | Preserved; annotated replay is frame-synchronized, candidate timeline seeks to rule timestamps |
| Video Analysis upload panel | Real upload inference and browser object-URL playback; independent of playback position | Preserved alongside registered camera monitoring |
| Camera diagrams in LiveMonitoringPage | Seeded illustrations, not camera ingestion or inference | Remain only in explicitly labeled simulation mode; operational feed cards are backed by registry and actual files |
| Original PrivateAreaDigitalTwin3D | Original Three.js geometry already restored; backend presence/fall/acoustic/SOS metadata and original orbit controls | Preserved; added incident metadata action in scene overlay |
| Radar/acoustic replay | Saved real evaluation predictions, not fresh inference or hardware telemetry | Legacy APIs preserved. New scenario IDs separately execute raw radar CSV features plus reconstructed held-out SVM/RandomForest and fresh local-pretrained YAMNet waveform inference. No measured people counts/room coordinates invented |
| Sensor fusion, SOS demo | Explicit simulated observations and transparent risk rules | Preserved; eight-scenario library labels controlled tests separately |
| Backend incidents | In-memory state and fusion/dedup rules | SQLite-backed events, incidents/history, notification attempts, jobs and deletion audit; state survives restart |
| Telegram | No actual transport | Real Bot API sendMessage adapter; disabled by default, TEST chat only, production send blocked |
| Research Metrics | Saved evaluation artifacts | Kept separate from operational incident statistics |

Five actual public UI zone names are retained: Corridor A, Canteen, Staircase, School Entrance and School Hall. Three are assigned authorized local research clips; entrance/hall are unconfigured rather than fabricated. These assignments are demo context, not assertions that the footage was recorded at the school.

Source modes are explicit: RECORDED REAL VIDEO, OFFLINE ANALYSIS, PRECOMPUTED ANALYSIS for completed actual pose output, recorded_sensor_replay for saved sensor predictions, and SIMULATION for controlled tests. LIVE CAMERA appears only for an explicitly authorized operator-configured RTSP/HTTP source; physical connectivity is not presumed.

Remaining limitations: no physical camera/radar/acoustic/SOS hardware verified; no real Telegram receipt verified; no validated fight person localization; no trained fall classifier; no synchronized physical multi-sensor recordings; no radar occupant coordinates or distances. The local shared token is demonstration access control, not school production identity/roles. See SYSTEM_WORKFLOW.md for deployment limits.
