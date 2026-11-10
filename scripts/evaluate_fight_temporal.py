
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
    f1_score, confusion_matrix
)

ROOT = Path("evaluation/outputs/fight_r3d18_v1")
OUT = Path("evaluation/outputs/fight_temporal_validation")
OUT.mkdir(parents=True, exist_ok=True)

WINDOW_SEC = 3.0
STRIDE_SEC = 1.5
THRESHOLD = 0.6

df = pd.read_csv(
    "datasets/open_hidden/fighting/airtlab_split.csv"
)
df = df[df["split"] == "val"].copy()

assert len(df) == 52, "Expected 52 validation videos"

classifier = joblib.load(ROOT / "fight_classifier.joblib")

weights = R3D_18_Weights.DEFAULT
model = r3d_18(weights=weights)
model.fc = torch.nn.Identity()
model.eval()
preprocess = weights.transforms()

def get_window_starts(total, window, stride):
    last = max(0, total - window)
    starts = list(range(0, last + 1, stride))

    if starts[-1] != last:
        # Avoid adding an almost identical final window
        if last - starts[-1] < stride / 2:
            starts[-1] = last
        else:
            starts.append(last)

    return sorted(set(starts))

def predict_video(path):
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        cap.release()
        raise RuntimeError(f"Invalid FPS: {path}")

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)

    cap.release()

    if not frames:
        raise RuntimeError(f"No frames: {path}")

    window = max(1, round(WINDOW_SEC * fps))
    stride = max(1, round(STRIDE_SEC * fps))

    starts = get_window_starts(
        len(frames), window, stride
    )

    records = []

    with torch.inference_mode():
        for start in starts:
            end = min(start + window, len(frames))

            indices = np.linspace(
                start, end - 1, 16
            ).astype(int)

            rgb = np.stack([
                cv2.cvtColor(
                    frames[i], cv2.COLOR_BGR2RGB
                )
                for i in indices
            ])

            tensor = torch.from_numpy(
                rgb
            ).permute(0, 3, 1, 2)

            x = preprocess(tensor).unsqueeze(0)
            feature = model(x).numpy()

            score = float(
                classifier.predict_proba(feature)[0, 1]
            )

            records.append({
                "start_sec": start / fps,
                "end_sec": end / fps,
                "score": score
            })

    return records

video_results = []
window_results = []

for row in tqdm(
    df.itertuples(index=False),
    total=len(df),
    desc="Temporal validation"
):
    windows = predict_video(row.path)

    scores = [w["score"] for w in windows]
    flags = [s >= THRESHOLD for s in scores]

    # Two consecutive positive windows
    confirmed = any(
        flags[i - 1] and flags[i]
        for i in range(1, len(flags))
    )

    # A single short video may have only one window.
    # Under this strict rule it cannot be confirmed.

    video_results.append({
        "path": row.path,
        "label": row.label,
        "ground_truth": int(row.label == "violent"),
        "max_score": max(scores),
        "positive_windows": sum(flags),
        "total_windows": len(windows),
        "single_window_0_6": int(any(flags)),
        "temporal_2_windows": int(confirmed)
    })

    for w in windows:
        window_results.append({
            "path": row.path,
            "label": row.label,
            **w,
            "candidate": int(w["score"] >= THRESHOLD)
        })

results = pd.DataFrame(video_results)

results.to_csv(
    OUT / "video_predictions.csv",
    index=False
)

pd.DataFrame(window_results).to_csv(
    OUT / "window_predictions.csv",
    index=False
)

# Original whole-clip model baseline
features = np.load(ROOT / "features.npz")
split_mask = features["splits"] == "val"

X_val = features["X"][split_mask]
y_val = features["y"][split_mask]

whole_clip_scores = classifier.predict_proba(
    X_val
)[:, 1]

# Ensure both orders are from original validation CSV
original_val = pd.read_csv(
    "datasets/open_hidden/fighting/airtlab_split.csv"
)
original_val = original_val[
    original_val["split"] == "val"
]

assert np.array_equal(
    y_val,
    (original_val["label"] == "violent").astype(int)
)

assert np.array_equal(
    results["path"].to_numpy(),
    original_val["path"].to_numpy()
)

def evaluate(name, truth, prediction):
    tn, fp, fn, tp = confusion_matrix(
        truth, prediction, labels=[0, 1]
    ).ravel()

    return {
        "method": name,
        "accuracy": round(
            accuracy_score(truth, prediction), 4
        ),
        "precision": round(
            precision_score(
                truth, prediction, zero_division=0
            ), 4
        ),
        "recall": round(
            recall_score(
                truth, prediction, zero_division=0
            ), 4
        ),
        "f1": round(
            f1_score(
                truth, prediction, zero_division=0
            ), 4
        ),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "TN": int(tn)
    }

truth = results["ground_truth"].to_numpy()

comparison = [
    evaluate(
        "Whole-clip threshold 0.5",
        truth,
        (whole_clip_scores >= 0.5).astype(int)
    ),
    evaluate(
        "Whole-clip threshold 0.6",
        truth,
        (whole_clip_scores >= 0.6).astype(int)
    ),
    evaluate(
        "Sliding any-window 0.6",
        truth,
        results["single_window_0_6"].to_numpy()
    ),
    evaluate(
        "Sliding two-consecutive 0.6",
        truth,
        results["temporal_2_windows"].to_numpy()
    )
]

summary = pd.DataFrame(comparison)
summary.to_csv(
    OUT / "comparison.csv", index=False
)

print("\n===== VALIDATION COMPARISON =====")
print(summary.to_string(index=False))

print("\nSaved to:", OUT.resolve())
print("DONE")
