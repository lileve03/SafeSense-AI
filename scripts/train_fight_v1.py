
from pathlib import Path
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
    f1_score, confusion_matrix, classification_report
)

# 1. Paths
CSV = Path("datasets/open_hidden/fighting/airtlab_split.csv")
OUT = Path("evaluation/outputs/fight_r3d18_v1")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)
assert len(df) == 350, "Expected 350 videos"
assert df.groupby("group_id")["split"].nunique().max() == 1

print("Dataset:", len(df), "videos")
print(df.groupby(["split", "label"]).size())

# 2. Load real pretrained model
weights = R3D_18_Weights.DEFAULT
print("Loading pretrained R3D-18...")

model = r3d_18(weights=weights)
model.fc = torch.nn.Identity()
model.eval()

preprocess = weights.transforms()

# 3. Read 16 frames from a video
def read_video(path, num_frames=16):
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
        raise RuntimeError(f"No frames: {path}")

    indices = np.linspace(
        0, len(frames) - 1, num_frames
    ).astype(int)

    selected = np.stack([frames[i] for i in indices])

    return torch.from_numpy(selected).permute(0, 3, 1, 2)

# 4. Extract video features
features_file = OUT / "features.npz"

if features_file.exists():
    saved = np.load(features_file)
    X = saved["X"]
    y = saved["y"]
    splits = saved["splits"]

    print("Loaded cached features")

else:
    X, y, splits = [], [], []
    failed = []

    with torch.inference_mode():
        for row in tqdm(
            df.itertuples(index=False),
            total=len(df),
            desc="Extracting video features"
        ):
            try:
                frames = read_video(row.path)
                inputs = preprocess(frames).unsqueeze(0)

                feature = model(inputs)
                feature = feature.squeeze().numpy()

                X.append(feature)
                y.append(1 if row.label == "violent" else 0)
                splits.append(row.split)

            except Exception as e:
                failed.append((row.path, str(e)))
                print("FAILED:", row.path, e)

    if failed:
        pd.DataFrame(
            failed, columns=["path", "error"]
        ).to_csv(OUT / "failed_videos.csv", index=False)
        raise RuntimeError(
            f"{len(failed)} videos failed. "
            "Fix them before training."
        )

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int64)
    splits = np.asarray(splits)

    np.savez_compressed(
        features_file, X=X, y=y, splits=splits
    )

    print("Features saved:", X.shape)

# 5. Split
train = splits == "train"
val = splits == "val"
test = splits == "test"

for name, mask in [
    ("train", train), ("val", val), ("test", test)
]:
    assert mask.sum() > 0
    assert len(np.unique(y[mask])) == 2

# 6. Train classifier
best_model = None
best_score = -1
best_c = None

for c in [0.01, 0.1, 1.0, 10.0]:
    clf = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=c,
            class_weight="balanced",
            max_iter=2000,
            random_state=42
        )
    )

    clf.fit(X[train], y[train])

    val_pred = clf.predict(X[val])
    score = f1_score(y[val], val_pred)

    print(f"C={c}, Validation F1={score:.4f}")

    if score > best_score:
        best_score = score
        best_model = clf
        best_c = c

print("Selected C:", best_c)

# 7. Evaluate held-out test set once
pred = best_model.predict(X[test])
prob = best_model.predict_proba(X[test])[:, 1]

metrics = {
    "accuracy": float(accuracy_score(y[test], pred)),
    "precision": float(precision_score(y[test], pred)),
    "recall": float(recall_score(y[test], pred)),
    "f1": float(f1_score(y[test], pred)),
    "confusion_matrix": confusion_matrix(
        y[test], pred, labels=[0, 1]
    ).tolist(),
    "selected_C": best_c
}

print("\nTEST RESULTS")
print(json.dumps(metrics, indent=2))

print(classification_report(
    y[test], pred,
    target_names=["Non-Violent", "Violent"]
))

# 8. Save model and results
joblib.dump(best_model, OUT / "fight_classifier.joblib")

(OUT / "metrics.json").write_text(
    json.dumps(metrics, indent=2)
)

pd.DataFrame({
    "ground_truth": y[test],
    "prediction": pred,
    "violence_score": prob
}).to_csv(OUT / "test_predictions.csv", index=False)

print("\nTRAINING COMPLETED")
print("Results saved to:", OUT.resolve())
