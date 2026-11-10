
from pathlib import Path
import hashlib
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

BASE = Path("evaluation/outputs")
V2 = BASE / "fight_multiclip_v2"
V3 = BASE / "fight_v3"
OUT = V3 / "reserved_comparison"
CACHE = OUT / "features"
CACHE.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    "datasets/open_hidden/fighting/v3/v3_reserved_test.csv"
)

assert len(df) == 86
assert set(df["split"]) == {"test"}

clf2 = joblib.load(V2 / "fight_multiclip_classifier.joblib")
clf3 = joblib.load(V3 / "fight_v3_classifier.joblib")

weights = R3D_18_Weights.DEFAULT
model = r3d_18(weights=weights)
model.fc = torch.nn.Identity()
model.eval()
preprocess = weights.transforms()

def extract(path):
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {path}")

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()

    if not frames:
        raise RuntimeError(f"Empty video: {path}")

    bounds = np.linspace(0, len(frames), 4).astype(int)
    features = []

    with torch.inference_mode():
        for i in range(3):
            start = min(bounds[i], len(frames) - 1)
            end = max(start + 1, bounds[i+1])

            ids = np.linspace(
                start, end - 1, 16
            ).astype(int)

            selected = np.stack([frames[j] for j in ids])
            tensor = torch.from_numpy(
                selected
            ).permute(0, 3, 1, 2)

            inputs = preprocess(tensor).unsqueeze(0)
            features.append(
                model(inputs).squeeze().numpy()
            )

    return np.concatenate(features).astype(np.float32)

X = []

for row in tqdm(
    df.itertuples(index=False),
    total=len(df),
    desc="Reserved video inference"
):
    key = hashlib.sha256(
        str(row.path).encode("utf-8")
    ).hexdigest()[:24]
    file = CACHE / f"{key}.npz"

    if file.exists():
        saved = np.load(file)
        assert saved["path"].item() == row.path
        feature = saved["feature"]
    else:
        feature = extract(row.path)
        np.savez_compressed(
            file,
            path=np.array(row.path),
            feature=feature
        )

    assert feature.shape == (1536,)
    X.append(feature)

X = np.stack(X)

# Thresholds are frozen before this comparison
score2 = clf2.predict_proba(X)[:, 1]
score3 = clf3.predict_proba(X)[:, 1]

pred2 = (score2 >= 0.4).astype(int)
pred3 = (score3 >= 0.7).astype(int)

df["ground_truth"] = (
    df["label"] == "violent"
).astype(int)

df["v2_score"] = score2
df["v2_prediction"] = pred2
df["v3_score"] = score3
df["v3_prediction"] = pred3

df.to_csv(
    OUT / "predictions.csv",
    index=False
)

def evaluate(model_name, source_name, subset, pred_col):
    truth = subset["ground_truth"].to_numpy()
    pred = subset[pred_col].to_numpy()

    tn, fp, fn, tp = confusion_matrix(
        truth, pred, labels=[0, 1]
    ).ravel()

    return {
        "model": model_name,
        "source": source_name,
        "videos": len(subset),
        "accuracy": round(accuracy_score(truth, pred), 4),
        "precision": round(
            precision_score(truth, pred, zero_division=0), 4
        ),
        "recall": round(
            recall_score(truth, pred, zero_division=0), 4
        ),
        "f1": round(
            f1_score(truth, pred, zero_division=0), 4
        ),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "TN": int(tn)
    }

rows = []

for model_name, pred_col in [
    ("V2", "v2_prediction"),
    ("V3", "v3_prediction")
]:
    rows.append(
        evaluate(model_name, "Combined", df, pred_col)
    )

    for source in ["AIRTLab", "Peliculas"]:
        subset = df[df["source"] == source]
        rows.append(
            evaluate(model_name, source, subset, pred_col)
        )

summary = pd.DataFrame(rows)

summary.to_csv(
    OUT / "comparison.csv",
    index=False
)

print("\n===== V2 VS V3 RESERVED COMPARISON =====")
print(summary.to_string(index=False))
print("\nSaved to:", OUT.resolve())
print("DONE")
