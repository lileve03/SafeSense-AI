# PROJECT AUDIT - 2026-10-28

Actual entrypoints: backend.main:app (8000), root fight_api:app (8001), dashboard/src/main.tsx -> App -> SafeSenseContext (Vite 3000).

Existing: zone-aware in-memory event/fusion/SOS/ack/reset APIs, nine dashboard pages, interactive maps and incident workflows, simulation engine. Real R3D-18 V1/V2/V3 classifiers, training configs, feature caches, test/external CSV results, cached pretrained weights and YOLO11n-Pose weights exist. Temporal fall script is a real pose model plus experimental handcrafted history rules, not a trained temporal classifier. TI IWR6843 benchmark, YAMNet/FSD50K evaluation and private sensor simulation scripts exist.

Broken: fight_api root resolves one directory too high; backend.fight_api module absent. Unbounded decoding, caller-declared zone privacy, missing model registry/CORS/backend events/fall upload. Dashboard requests nonexistent GET /incidents, assumes wrong JSON shape, sends ACK without staff body, updates on failure, lacks polling and backend-driven zone status. Monitoring illustrations claim live feeds and fixed FPS. Analytics includes invented trends, response times and success rates. Fusion correlates types without checking source independence or processing mode and creates duplicates.

Real versus simulation: research scripts and root fight classifier use actual models; dashboard seeded alerts/telemetry/scenarios and private simulator are simulated. No physical hardware verified. Existing YAMNet evaluation has 10,231 clips and 123 scream positives; impacts not established. Existing pose evaluation has only four sequences. Research metrics do not establish school performance. Replay of saved predictions is replay, not new inference.

Repository preservation: no .git at project root; git status fails (not a git repository). No AGENTS.md at root. Preserve original research scripts, datasets, models and evaluation outputs through targeted source edits. No retraining.

Sequence: repair module/path/upload bounds; extend existing event/fusion/workflow APIs; integrate real fight and fall; connect context and upload UI while retaining design; replace unsupported live claims; run regressions/real videos/build/HTTP checks; document startup, demos and limitations.

Environment: sandbox process creation fails (Windows error 1385); approved shell execution outside sandbox is required. Existing virtual environments retained; availability checked by imports rather than assumed.
