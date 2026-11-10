
from pathlib import Path
import json
import cv2
import joblib
import numpy as np
import pandas as pd
import torch

from tqdm import tqdm
from torchvision.models.video import (
    r3d_18, R3D_18_Weights
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score,
    recall_score, f1_score, confusion_matrix
)

CSV = Path(
    "datasets/open_hidden/fighting/airtlab_split.csv"
)

V1 = Path("evaluation/outputs/fight_r3d18_v1")
OUT = Path("evaluation/outputs/fight_multiclip_v2")
CACHE = OUT / "feature_cache"
CACHE.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)

assert len(df) == 350
assert df.groupby("group_id")["split"].nunique().max() == 1

# Do not touch the held-out test split
work = df[df["split"].isin(["train", "val"])].copy()

print("Training videos:", sum(work.split == "train"))
print("Validation videos:", sum(work.split == "val"))
print("Test set: excluded")

weights = R3D_18_Weights.DEFAULT
model = r3d_18(weights=weights)
model.fc = torch.nn.Identity()
model.eval()
preprocess = weights.transforms()

def read_video(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open: {path}")

    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )
    cap.release()

    if not frames:
        raise RuntimeError(f"No frames: {path}")

    return frames

def extract_multiclip(frames):
    # Divide the full video into three equal time segments
    boundaries = np.linspace(
        0, len(frames), 4
    ).astype(int)

    features = []

    with torch.inference_mode():
        for i in range(3):
            start = boundaries[i]
            end = boundaries[i + 1]

            # Handle very short clips
            start = min(start, len(frames) - 1)
            end = max(start + 1, end)

            indices = np.linspace(
                start, end - 1, 16
            ).astype(int)

            selected = np.stack([
                frames[j] for j in indices
            ])

            tensor = torch.from_numpy(
                selected
            ).permute(0, 3, 1, 2)

            x = preprocess(tensor).unsqueeze(0)
            feature = model(x).squeeze().numpy()
            features.append(feature)

    return np.concatenate(features).astype(np.float32)

# Extract features with per-video caching
X = []
y = []
splits = []

for row_id, row in enumerate(
    tqdm(
        work.itertuples(index=False),
        total=len(work),
        desc="V2 Feature Extraction"
    )
):
    cache_file = CACHE / f"feature_{row_id:04d}.npz"

    if cache_file.exists():
        saved = np.load(cache_file)
        if saved["path"].item() != row.path:
            raise RuntimeError(
                f"Cache mismatch: {cache_file}"
            )
        feature = saved["feature"]
    else:
        frames = read_video(row.path)
        feature = extract_multiclip(frames)

        np.savez_compressed(
            cache_file,
            feature=feature,
            path=np.array(row.path)
        )

    assert feature.shape == (1536,)

    X.append(feature)
    y.append(1 if row.label == "violent" else 0)
    splits.append(row.split)

X = np.stack(X)
y = np.array(y)
splits = np.array(splits)

train = splits == "train"
val = splits == "val"

# Hyperparameter tuning using validation only
best_f1 = -1
best_model = None
best_c = None
best_threshold = None

for c in [0.01, 0.1, 1.0, 10.0]:
    clf = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=c,
            class_weight="balanced",
            max_iter=3000,
            random_state=42
        )
    )

    clf.fit(X[train], y[train])
    scores = clf.predict_proba(X[val])[:, 1]

    for threshold in [0.4, 0.5, 0.6, 0.7, 0.8]:
        pred = (scores >= threshold).astype(int)
        score = f1_score(y[val], pred)

        if score > best_f1:
            best_f1 = score
            best_model = clf
            best_c = c
            best_threshold = threshold

def evaluate(name, actual, pred):
    tn, fp, fn, tp = confusion_matrix(
        actual, pred, labels=[0, 1]
    ).ravel()

    return {
        "method": name,
        "accuracy": accuracy_score(actual, pred),
        "precision": precision_score(actual, pred),
        "recall": recall_score(actual, pred),
        "f1": f1_score(actual, pred),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "TN": int(tn)
    }

# Evaluate V2
v2_scores = best_model.predict_proba(X[val])[:, 1]
v2_pred = (v2_scores >= best_threshold).astype(int)

v2_result = evaluate("V2 Multi-Clip", y[val], v2_pred)

# Load original V1 cached features for fair comparison
original = np.load(V1 / "features.npz")
v1_clf = joblib.load(V1 / "fight_classifier.joblib")

assert np.array_equal(
    original["splits"],
    df["split"].to_numpy()
)

assert np.array_equal(
    original["y"],
    (df["label"] == "violent").astype(int).to_numpy()
)

v1_X = original["X"][df["split"] == "val"]
v1_y = original["y"][df["split"] == "val"]

assert np.array_equal(v1_y, y[val])

v1_scores = v1_clf.predict_proba(v1_X)[:, 1]
v1_pred = (v1_scores >= 0.6).astype(int)

v1_result = evaluate("V1 Whole-Clip", v1_y, v1_pred)

comparison = pd.DataFrame([v1_result, v2_result])

comparison.to_csv(
    OUT / "validation_comparison.csv",
    index=False
)

joblib.dump(
    best_model,
    OUT / "fight_multiclip_classifier.joblib"
)

(OUT / "training_config.json").write_text(
    json.dumps({
        "method": "3-clip R3D-18 features",
        "feature_dimension": 1536,
        "selected_C": best_c,
        "selected_threshold": best_threshold,
        "validation_f1": best_f1,
        "test_set_used": False
    }, indent=2),
    encoding="utf-8"
)

print("\n===== V1 VS V2 VALIDATION =====")
print(comparison.to_string(index=False))

print("\nSelected C:", best_c)
print("Selected threshold:", best_threshold)
print("Saved to:", OUT.resolve())
print("DONE")
