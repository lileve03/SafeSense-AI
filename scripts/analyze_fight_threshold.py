
from pathlib import Path
import joblib
import numpy as np

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

ROOT = Path("evaluation/outputs/fight_r3d18_v1")

data = np.load(ROOT / "features.npz")
X = data["X"]
y = data["y"]
splits = data["splits"]

model = joblib.load(ROOT / "fight_classifier.joblib")

# IMPORTANT: Validation set only
mask = splits == "val"

X_val = X[mask]
y_val = y[mask]

scores = model.predict_proba(X_val)[:, 1]

print("\nVALIDATION THRESHOLD ANALYSIS")
print("Videos:", len(y_val))

thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

results = []

for threshold in thresholds:
    pred = (scores >= threshold).astype(int)

    precision = precision_score(
        y_val, pred, zero_division=0
    )
    recall = recall_score(
        y_val, pred, zero_division=0
    )
    f1 = f1_score(
        y_val, pred, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_val, pred, labels=[0, 1]
    ).ravel()

    results.append((threshold, precision, recall, f1, fp, fn))

    print(
        f"Threshold={threshold:.1f} | "
        f"Precision={precision:.4f} | "
        f"Recall={recall:.4f} | "
        f"F1={f1:.4f} | "
        f"FP={fp} | FN={fn}"
    )

best = max(results, key=lambda r: r[3])

print("\nBEST VALIDATION THRESHOLD (by F1)")
print("Threshold:", best[0])
print("F1:", round(best[3], 4))
print("\nDONE")
