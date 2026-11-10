
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

ROOT = Path("evaluation/outputs/fight_r3d18_v1")
SPLIT_CSV = Path(
    "datasets/open_hidden/fighting/airtlab_split.csv"
)

# Load trained model and cached features
model = joblib.load(ROOT / "fight_classifier.joblib")
data = np.load(ROOT / "features.npz")

X = data["X"]
y = data["y"]
splits = data["splits"]

df = pd.read_csv(SPLIT_CSV)

# Check features match original CSV ordering
assert len(X) == len(df) == 350
expected_y = (df["label"] == "violent").astype(int).to_numpy()
assert np.array_equal(y, expected_y)
assert np.array_equal(splits, df["split"].to_numpy())

# Select held-out test set
test_mask = splits == "test"

X_test = X[test_mask]
y_test = y[test_mask]
test_df = df.loc[test_mask].copy()

# Predictions
predictions = model.predict(X_test)
scores = model.predict_proba(X_test)[:, 1]

test_df["prediction"] = np.where(
    predictions == 1, "violent", "non-violent"
)
test_df["violence_score"] = scores

def classify_error(row):
    if row["label"] == "non-violent" and row["prediction"] == "violent":
        return "FALSE_POSITIVE"
    if row["label"] == "violent" and row["prediction"] == "non-violent":
        return "FALSE_NEGATIVE"
    return "CORRECT"

test_df["result"] = test_df.apply(classify_error, axis=1)

# Save complete test predictions with real file paths
all_file = ROOT / "test_predictions_with_paths.csv"
test_df.to_csv(all_file, index=False)

# Save only mistakes
errors = test_df[test_df["result"] != "CORRECT"].copy()

error_file = ROOT / "error_analysis.csv"
errors.to_csv(error_file, index=False)

print("\n===== ERROR ANALYSIS =====")
print("Test videos:", len(test_df))
print("Correct:", (test_df["result"] == "CORRECT").sum())
print("False Positives:", (test_df["result"] == "FALSE_POSITIVE").sum())
print("False Negatives:", (test_df["result"] == "FALSE_NEGATIVE").sum())

print("\nMISCLASSIFIED VIDEOS:")
for row in errors.itertuples():
    print(
        f"\n{row.result}"
        f"\nVideo: {row.path}"
        f"\nGround Truth: {row.label}"
        f"\nPrediction: {row.prediction}"
        f"\nViolence Score: {row.violence_score:.4f}"
    )

print("\nSaved:", error_file.resolve())
print("DONE")
