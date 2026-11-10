
from pathlib import Path
import hashlib
import json
import cv2
import joblib
import numpy as np
import pandas as pd
import torch

from tqdm import tqdm
from torchvision.models.video import r3d_18, R3D_18_Weights
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix
)

# =============================================
# 1. CONFIG
# =============================================
ROOT = Path("datasets/open_hidden/fighting/v3")
OUT = Path("evaluation/outputs/fight_v3")
CACHE = OUT / "feature_cache"
CACHE.mkdir(parents=True, exist_ok=True)

MANIFEST = ROOT / "v3_development.csv"
df = pd.read_csv(MANIFEST)

assert len(df) == 465
assert set(df["split"]) == {"train", "val"}
assert not (df["split"] == "test").any()
assert df.groupby(
    ["source", "group_id"]
)["split"].nunique().max() == 1

print("===== V3 TRAINING DATA =====")
print(df.groupby(["source", "split", "label"]).size())

# =============================================
# 2. LOAD PRETRAINED R3D-18
# =============================================
weights = R3D_18_Weights.DEFAULT
model = r3d_18(weights=weights)
model.fc = torch.nn.Identity()
model.eval()

preprocess = weights.transforms()

# =============================================
# 3. MULTI-CLIP FEATURE EXTRACTION
# Exactly the same sampling as V2
# =============================================
def read_frames(path):
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {path}")

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


def extract_features(path):
    frames = read_frames(path)

    bounds = np.linspace(
        0, len(frames), 4
    ).astype(int)

    features = []

    with torch.inference_mode():
        for i in range(3):
            start = min(bounds[i], len(frames) - 1)
            end = max(start + 1, bounds[i + 1])

            ids = np.linspace(
                start, end - 1, 16
            ).astype(int)

            selected = np.stack([
                frames[j] for j in ids
            ])

            tensor = torch.from_numpy(
                selected
            ).permute(0, 3, 1, 2)

            inputs = preprocess(tensor).unsqueeze(0)
            feature = model(inputs).squeeze().numpy()

            features.append(feature)

    return np.concatenate(
        features
    ).astype(np.float32)


# =============================================
# 4. EXTRACT WITH PER-VIDEO CACHE
# =============================================
X = []
y = []
splits = []
sources = []
paths = []

for row in tqdm(
    df.itertuples(index=False),
    total=len(df),
    desc="V3 Feature Extraction"
):
    path = str(row.path)

    # Stable filename based on original path
    cache_id = hashlib.sha256(
        path.encode("utf-8")
    ).hexdigest()[:24]

    cache_path = CACHE / f"{cache_id}.npz"

    if cache_path.exists():
        saved = np.load(cache_path)

        if saved["path"].item() != path:
            raise RuntimeError("Cache path mismatch")

        feature = saved["feature"]
    else:
        feature = extract_features(path)

        np.savez_compressed(
            cache_path,
            path=np.array(path),
            feature=feature
        )

    assert feature.shape == (1536,)

    X.append(feature)
    y.append(int(row.label == "violent"))
    splits.append(row.split)
    sources.append(row.source)
    paths.append(path)

X = np.stack(X)
y = np.array(y)
splits = np.array(splits)
sources = np.array(sources)

train = splits == "train"
val = splits == "val"

assert sum(train) == 385
assert sum(val) == 80

# =============================================
# 5. TRAIN CLASSIFIER
# =============================================
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

    for threshold in [0.3, 0.4, 0.5, 0.6, 0.7]:
        pred = (scores >= threshold).astype(int)
        score = f1_score(
            y[val], pred, zero_division=0
        )

        if score > best_f1:
            best_f1 = score
            best_model = clf
            best_c = c
            best_threshold = threshold

# =============================================
# 6. VALIDATION EVALUATION BY DATA SOURCE
# =============================================
scores = best_model.predict_proba(X[val])[:, 1]
pred = (scores >= best_threshold).astype(int)

truth = y[val]
val_sources = sources[val]

def evaluate(name, mask):
    yt = truth[mask]
    yp = pred[mask]

    tn, fp, fn, tp = confusion_matrix(
        yt, yp, labels=[0, 1]
    ).ravel()

    return {
        "dataset": name,
        "videos": len(yt),
        "accuracy": round(
            accuracy_score(yt, yp), 4
        ),
        "precision": round(
            precision_score(yt, yp, zero_division=0), 4
        ),
        "recall": round(
            recall_score(yt, yp, zero_division=0), 4
        ),
        "f1": round(
            f1_score(yt, yp, zero_division=0), 4
        ),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "TN": int(tn)
    }

results = pd.DataFrame([
    evaluate(
        "Combined",
        np.ones(len(truth), dtype=bool)
    ),
    evaluate(
        "AIRTLab",
        val_sources == "AIRTLab"
    ),
    evaluate(
        "Peliculas",
        val_sources == "Peliculas"
    )
])

# =============================================
# 7. SAVE ALL RESULTS
# =============================================
joblib.dump(
    best_model,
    OUT / "fight_v3_classifier.joblib"
)

results.to_csv(
    OUT / "validation_metrics.csv",
    index=False
)

validation_predictions = df.loc[val].copy()
validation_predictions["violence_score"] = scores
validation_predictions["prediction"] = pred
validation_predictions["correct"] = (
    pred == truth
).astype(int)

validation_predictions.to_csv(
    OUT / "validation_predictions.csv",
    index=False
)

config = {
    "model": "R3D-18 Multi-Clip V3",
    "feature_dimension": 1536,
    "sampling": "3 equal segments, 16 frames each",
    "train_videos": 385,
    "validation_videos": 80,
    "selected_C": best_c,
    "selected_threshold": best_threshold,
    "selection_metric": "Combined validation F1",
    "test_set_used": False
}

(OUT / "training_config.json").write_text(
    json.dumps(config, indent=2),
    encoding="utf-8"
)

print("\n===== V3 VALIDATION RESULTS =====")
print(results.to_string(index=False))

print("\nSelected C:", best_c)
print("Selected threshold:", best_threshold)
print("Saved to:", OUT.resolve())
print("DONE")
