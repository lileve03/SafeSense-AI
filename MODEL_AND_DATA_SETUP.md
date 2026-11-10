# Model weights and authorized demo data

All existing local artifacts are preserved. They are intentionally excluded from the Git upload. Obtain pretrained weights from the original publishers and project classifiers from the project owner using an approved private transfer. Verify provenance, SHA-256 checksums supplied by that owner, dependency versions and redistribution rights. No public download for the custom classifiers is configured in this repository. Do not substitute an unrelated checkpoint or invent weights. Joblib/pickle checkpoints must come from a trusted source because loading them can execute code.

## Core vision models

From the project root, explicitly provision the official R3D-18 pretrained backbone while online:

```powershell
.\.venv-vision\Scripts\python.exe -c "from torchvision.models.video import r3d_18,R3D_18_Weights; r3d_18(weights=R3D_18_Weights.DEFAULT)"
.\.venv-vision\Scripts\python.exe -c "from ultralytics import YOLO; YOLO('yolo11n-pose.pt')"
```

The R3D checkpoint is `r3d_18-b3b3357e.pth` in the current user's Torch checkpoint cache. YOLO pose must be available as `yolo11n-pose.pt` at the repository root. `yolo11n.pt` is retained locally for tools that use it; it is not a replacement for the pose checkpoint. Official references: [Torchvision R3D-18](https://docs.pytorch.org/vision/main/models/generated/torchvision.models.video.r3d_18.html) and [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/). Review the publishers' license terms for your use.

Request these exact custom artifacts from the project owner, retaining directory layout:

- `evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib` (V2 threshold 0.4).
- `evaluation/outputs/fight_v3/fight_v3_classifier.joblib` (V3 threshold 0.7).

Training/evaluation source remains under `ai_models/` and `scripts/`; inspect each tool's `--help` before running. Upload preparation does not retrain or modify models. Missing weights prevent the relevant real inference, even when service health endpoints respond.

## Optional acoustic and radar scenarios

Create `.venv-acoustic` and `.venv-radar` separately if needed, using the requirements in `ai_models/acoustic/` and `ai_models/radar/`. YAMNet's model URL in the existing acoustic tools is `https://tfhub.dev/google/yamnet/1`. Obtain that publisher model explicitly and set `SAFESENSE_YAMNET_PATH` to its local extracted SavedModel directory, which must include `saved_model.pb`, variables, and `assets/yamnet_class_map.csv`. The runtime also supports an existing TensorFlow Hub cache; scenario readiness does not implicitly download it.

Radar scenarios require authorized raw recordings and the existing `evaluation/outputs/radar_route_a/radar_features.csv`. Saved replay scenarios also depend on excluded prediction outputs. Request these privately from the project owner, or reproduce them with the corresponding evaluation tools and legally obtained inputs. They can contain participant/session information and are not public repository fixtures.

## Demo inputs and authorization

The source registry in `backend/registry.py` and readiness checks in `backend/scenario_catalog.py` define the expected local paths. Existing scenarios reference AIRTLab violence-detection videos, UR Fall recordings, FSD50K acoustic samples, and radar inputs. Obtain datasets from their original research publishers under their access and usage terms; public availability alone does not grant permission to redistribute recordings. No dataset download or redistribution is performed by this preparation.

For a self-recorded demo, obtain documented consent and location authorization, avoid bystanders and identifying details, and use authorized public-area clips with the manual upload flow. Do not record private zones. Configure any local camera registry through ignored `camera-registry.json` / `SAFESENSE_CAMERA_REGISTRY`; private staff routing stays in ignored `staff-routes.json`.

Keep datasets under ignored `datasets/`, evaluation results under ignored `evaluation/outputs/`, and recordings, screenshots, operational exports and evidence out of Git. Do not use Git LFS to publish private data. Before sharing an approved demo asset separately, verify its license/consent, inspect metadata, and remove identifiers. Scenario entries without prerequisites should remain unavailable; simulated demos must remain clearly labeled.
