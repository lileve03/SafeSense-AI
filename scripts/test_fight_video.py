
from pathlib import Path
import argparse
import csv
import cv2
import joblib
import numpy as np
import pandas as pd
import torch

from torchvision.models.video import r3d_18, R3D_18_Weights

parser = argparse.ArgumentParser()
parser.add_argument("--source", default=None)
parser.add_argument(
    "--sample",
    choices=["violent", "non-violent"],
    default="violent"
)
args = parser.parse_args()

ROOT = Path("evaluation/outputs/fight_r3d18_v1")
MODEL_PATH = ROOT / "fight_classifier.joblib"
SPLIT_PATH = Path(
    "datasets/open_hidden/fighting/airtlab_split.csv"
)

if not MODEL_PATH.exists():
    raise FileNotFoundError(MODEL_PATH)

# Choose a held-out test video when --source is omitted
if args.source:
    video_path = Path(args.source)
    ground_truth = "unknown"
else:
    df = pd.read_csv(SPLIT_PATH)
    candidates = df[
        (df["split"] == "test") &
        (df["label"] == args.sample)
    ]
    if candidates.empty:
        raise RuntimeError("No matching test video found")

    video_path = Path(candidates.iloc[0]["path"])
    ground_truth = args.sample

if not video_path.exists():
    raise FileNotFoundError(video_path)

print("Video:", video_path)
print("Ground Truth:", ground_truth)

# Load exactly the same pretrained extractor as training
weights = R3D_18_Weights.DEFAULT
preprocess = weights.transforms()

feature_extractor = r3d_18(weights=weights)
feature_extractor.fc = torch.nn.Identity()
feature_extractor.eval()

classifier = joblib.load(MODEL_PATH)

# Read input frames
cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    raise RuntimeError("Cannot open input video")

fps = cap.get(cv2.CAP_PROP_FPS)
if not np.isfinite(fps) or fps <= 0:
    fps = 25.0

frames = []

while True:
    ok, frame = cap.read()
    if not ok:
        break
    frames.append(frame)

cap.release()

if not frames:
    raise RuntimeError("Input video has no decodable frames")

# Use 16 evenly sampled frames, consistent with training
indices = np.linspace(
    0, len(frames) - 1, 16
).astype(int)

selected = np.stack([
    cv2.cvtColor(frames[i], cv2.COLOR_BGR2RGB)
    for i in indices
])

tensor = torch.from_numpy(selected).permute(0, 3, 1, 2)
inputs = preprocess(tensor).unsqueeze(0)

with torch.inference_mode():
    features = feature_extractor(inputs).numpy()

score = float(classifier.predict_proba(features)[0, 1])

prediction = (
    "violent" if score >= 0.5 else "non-violent"
)

print("\n===== REAL VIDEO RESULT =====")
print("Prediction:", prediction)
print(f"Violence score: {score:.4f}")
print("Ground Truth:", ground_truth)

# Save annotated output video
output_dir = ROOT / "real_video_testing"
output_dir.mkdir(parents=True, exist_ok=True)

output = output_dir / (
    video_path.stem + "_fight_prediction.mp4"
)

h, w = frames[0].shape[:2]

writer = cv2.VideoWriter(
    str(output),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (w, h)
)

if not writer.isOpened():
    raise RuntimeError("Cannot create annotated MP4")

label = (
    "POSSIBLE VIOLENCE"
    if prediction == "violent"
    else "NO VIOLENCE CLASSIFIED"
)

for frame in frames:
    annotated = frame.copy()

    cv2.rectangle(
        annotated, (0, 0), (w, 100),
        (20, 20, 20), -1
    )

    cv2.putText(
        annotated, label,
        (15, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75, (255, 255, 255), 2
    )

    cv2.putText(
        annotated,
        f"Clip-level violence score: {score:.3f}",
        (15, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55, (255, 255, 255), 2
    )

    writer.write(annotated)

writer.release()

# Append result to a CSV
result_csv = output_dir / "predictions.csv"

row = {
    "video": str(video_path),
    "ground_truth": ground_truth,
    "prediction": prediction,
    "violence_score": score,
    "output_video": str(output)
}

new_file = not result_csv.exists()

with result_csv.open(
    "a", newline="", encoding="utf-8"
) as f:
    writer_csv = csv.DictWriter(
        f, fieldnames=list(row)
    )
    if new_file:
        writer_csv.writeheader()
    writer_csv.writerow(row)

print("Saved video:", output)
print("Saved CSV:", result_csv)
print("DONE")
