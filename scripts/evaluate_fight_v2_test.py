
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

BASE = Path("evaluation/outputs")
V1 = BASE / "fight_r3d18_v1"
V2 = BASE / "fight_multiclip_v2"
OUT = V2 / "heldout_test"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    "datasets/open_hidden/fighting/airtlab_split.csv"
)
test_df = df[df["split"] == "test"].copy()
assert len(test_df) == 54

with open(V2 / "training_config.json", encoding="utf-8") as f:
    config = json.load(f)

threshold_v2 = float(config["selected_threshold"])
threshold_v1 = 0.6

# Frozen classifiers
clf1 = joblib.load(V1 / "fight_classifier.joblib")
clf2 = joblib.load(V2 / "fight_multiclip_classifier.joblib")

# Original V1 features (already extracted)
original = np.load(V1 / "features.npz")
assert len(original["X"]) == len(df)
assert np.array_equal(
    original["splits"], df["split"].to_numpy()
)
assert np.array_equal(
    original["y"],
    (df["label"] == "violent").astype(int).to_numpy()
)

test_mask = df["split"].to_numpy() == "test"
y = original["y"][test_mask]
v1_features = original["X"][test_mask]
assert len(y) == len(test_df)

# Load pretrained extractor for V2
weights = R3D_18_Weights.DEFAULT
extractor = r3d_18(weights=weights)
extractor.fc = torch.nn.Identity()
extractor.eval()
preprocess = weights.transforms()

def read_frames(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open: {path}")

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    cap.release()

    if not frames:
        raise RuntimeError(f"Empty video: {path}")

    return frames

def extract_v2(path):
    frames = read_frames(path)
    bounds = np.linspace(0, len(frames), 4).astype(int)
    features = []

    with torch.inference_mode():
        for i in range(3):
            start = min(bounds[i], len(frames) - 1)
            end = max(start + 1, bounds[i + 1])

            ids = np.linspace(
                start, end - 1, 16
            ).astype(int)

            selected = np.stack([frames[j] for j in ids])
            tensor = torch.from_numpy(
                selected
            ).permute(0, 3, 1, 2)

            x = preprocess(tensor).unsqueeze(0)
            feature = extractor(x).squeeze().numpy()
            features.append(feature)

    return np.concatenate(features).astype(np.float32)

# Extract and cache held-out features
cache = OUT / "v2_test_features.npz"

if cache.exists():
    saved = np.load(cache)
    assert np.array_equal(
        saved["paths"],
        test_df["path"].to_numpy()
    )
    X2 = saved["X"]
    print("Loaded cached V2 test features")
else:
    X2 = []
    for path in tqdm(
        test_df["path"],
        desc="V2 Held-out Test"
    ):
        X2.append(extract_v2(path))

    X2 = np.stack(X2)
    np.savez_compressed(
        cache,
        X=X2,
        paths=test_df["path"].to_numpy()
    )

assert X2.shape == (54, 1536)

# Predict using already-selected thresholds
score1 = clf1.predict_proba(v1_features)[:, 1]
score2 = clf2.predict_proba(X2)[:, 1]

pred1 = (score1 >= threshold_v1).astype(int)
pred2 = (score2 >= threshold_v2).astype(int)

def evaluate(name, pred):
    tn, fp, fn, tp = confusion_matrix(
        y, pred, labels=[0, 1]
    ).ravel()

    return {
        "model": name,
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred), 4),
        "recall": round(recall_score(y, pred), 4),
        "f1": round(f1_score(y, pred), 4),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "TN": int(tn)
    }

comparison = pd.DataFrame([
    evaluate("V1 Whole-Clip", pred1),
    evaluate("V2 Multi-Clip", pred2)
])

comparison.to_csv(
    OUT / "test_comparison.csv",
    index=False
)

predictions = test_df[["path", "label"]].copy()
predictions["v1_score"] = score1
predictions["v1_prediction"] = pred1
predictions["v2_score"] = score2
predictions["v2_prediction"] = pred2

predictions.to_csv(
    OUT / "test_predictions.csv",
    index=False
)

print("\n===== V1 VS V2 HELD-OUT TEST =====")
print(comparison.to_string(index=False))
print("\nV1 threshold:", threshold_v1)
print("V2 threshold:", threshold_v2)
print("Saved to:", OUT.resolve())
print("DONE")
