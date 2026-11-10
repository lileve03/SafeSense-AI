
from pathlib import Path
import json
import cv2
import joblib
import numpy as np
import pandas as pd
import torch

from tqdm import tqdm
from torchvision.models.video import r3d_18, R3D_18_Weights
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)

ROOT = Path("datasets/open_hidden/fighting/raw/Archive6/Peliculas")
MODEL_DIR = Path("evaluation/outputs/fight_multiclip_v2")
OUT = Path("evaluation/outputs/fight_external_v2")
CACHE = OUT / "feature_cache"

CACHE.mkdir(parents=True, exist_ok=True)

# 1. Discover real external videos
records = []

for label, folder in [(1, "fights"), (0, "noFights")]:
    directory = ROOT / folder

    if not directory.exists():
        raise FileNotFoundError(directory)

    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in {".avi", ".mpg", ".mpeg", ".mp4"}:
            records.append({
                "path": str(path.resolve()),
                "label": label,
                "category": folder
            })

df = pd.DataFrame(records)

assert len(df) == 201, f"Expected 201 videos, got {len(df)}"
assert (df["label"] == 1).sum() == 100
assert (df["label"] == 0).sum() == 101

print("\nEXTERNAL DATASET")
print(df.groupby("category").size())

# 2. Load frozen model and threshold
with open(MODEL_DIR / "training_config.json", encoding="utf-8") as f:
    config = json.load(f)

threshold = float(config["selected_threshold"])
assert abs(threshold - 0.4) < 1e-8

classifier = joblib.load(
    MODEL_DIR / "fight_multiclip_classifier.joblib"
)

weights = R3D_18_Weights.DEFAULT
extractor = r3d_18(weights=weights)
extractor.fc = torch.nn.Identity()
extractor.eval()

preprocess = weights.transforms()

# 3. Decode actual video
def read_video(path):
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise RuntimeError("Cannot open video")

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frames.append(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )

    cap.release()

    if len(frames) == 0:
        raise RuntimeError("No decodable frames")

    return frames

# 4. Same V2 preprocessing as training
def extract_features(frames):
    boundaries = np.linspace(
        0, len(frames), 4
    ).astype(int)

    features = []

    with torch.inference_mode():
        for i in range(3):
            start = min(
                boundaries[i], len(frames) - 1
            )
            end = max(
                start + 1, boundaries[i + 1]
            )

            ids = np.linspace(
                start, end - 1, 16
            ).astype(int)

            selected = np.stack([
                frames[j] for j in ids
            ])

            tensor = torch.from_numpy(
                selected
            ).permute(0, 3, 1, 2)

            x = preprocess(tensor).unsqueeze(0)
            feature = extractor(x).squeeze().numpy()

            features.append(feature)

    return np.concatenate(features).astype(np.float32)

# 5. Real inference with per-file cache
results = []
failures = []

for i, row in enumerate(
    tqdm(
        df.itertuples(index=False),
        total=len(df),
        desc="External V2 Inference"
    )
):
    cache_path = CACHE / f"video_{i:04d}.npz"

    try:
        if cache_path.exists():
            saved = np.load(cache_path)
            if saved["path"].item() != row.path:
                raise RuntimeError("Cache path mismatch")
            feature = saved["feature"]
        else:
            frames = read_video(row.path)
            feature = extract_features(frames)

            np.savez_compressed(
                cache_path,
                path=np.array(row.path),
                feature=feature
            )

        if feature.shape != (1536,):
            raise RuntimeError("Incorrect feature dimension")

        score = float(
            classifier.predict_proba(
                feature.reshape(1, -1)
            )[0, 1]
        )

        prediction = int(score >= threshold)

        results.append({
            "path": row.path,
            "category": row.category,
            "ground_truth": row.label,
            "violence_score": score,
            "prediction": prediction,
            "correct": int(prediction == row.label)
        })

    except Exception as e:
        failures.append({
            "path": row.path,
            "error": str(e)
        })
        print("\nFAILED:", row.path, e)

# Always save individual predictions
pd.DataFrame(results).to_csv(
    OUT / "external_predictions.csv",
    index=False
)

if failures:
    pd.DataFrame(failures).to_csv(
        OUT / "failed_videos.csv",
        index=False
    )
    print("\nFAILED VIDEOS:", len(failures))
    print("Fix decoding problems before final evaluation.")
    raise RuntimeError(
        "External evaluation incomplete: some videos failed"
    )

# 6. Full evaluation
pred_df = pd.DataFrame(results)

y_true = pred_df["ground_truth"]
y_pred = pred_df["prediction"]

tn, fp, fn, tp = confusion_matrix(
    y_true, y_pred, labels=[0, 1]
).ravel()

metrics = {
    "model": "SafeSense Fight V2 Multi-Clip R3D-18",
    "dataset": "Peliculas External",
    "videos": len(pred_df),
    "threshold": threshold,
    "accuracy": float(accuracy_score(y_true, y_pred)),
    "precision": float(precision_score(y_true, y_pred)),
    "recall": float(recall_score(y_true, y_pred)),
    "f1": float(f1_score(y_true, y_pred)),
    "TP": int(tp),
    "TN": int(tn),
    "FP": int(fp),
    "FN": int(fn)
}

(OUT / "external_metrics.json").write_text(
    json.dumps(metrics, indent=2),
    encoding="utf-8"
)

errors = pred_df[pred_df["correct"] == 0]
errors.to_csv(
    OUT / "external_errors.csv",
    index=False
)

print("\n===== EXTERNAL DATASET EVALUATION =====")
print(json.dumps(metrics, indent=2))

print("\nCLASSIFICATION REPORT")
print(classification_report(
    y_true, y_pred,
    target_names=["Non-Fight", "Fight"]
))

print("\nSaved to:", OUT.resolve())
print("DONE")
