
from pathlib import Path
import argparse
import csv

import cv2
import joblib
import numpy as np
import torch

from torchvision.models.video import (
    r3d_18,
    R3D_18_Weights
)

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--window-sec", type=float, default=3.0)
parser.add_argument("--stride-sec", type=float, default=1.5)
args = parser.parse_args()

MODEL_DIR = Path("evaluation/outputs/fight_r3d18_v1")
OUTPUT_DIR = Path("evaluation/outputs/fight_sliding_v1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLD = 0.5

if args.window_sec <= 0 or args.stride_sec <= 0:
    raise ValueError("Window and stride must be positive")

# 1. Load trained classifier
classifier = joblib.load(
    MODEL_DIR / "fight_classifier.joblib"
)

# 2. Load same pretrained R3D-18
weights = R3D_18_Weights.DEFAULT

model = r3d_18(weights=weights)
model.fc = torch.nn.Identity()
model.eval()

preprocess = weights.transforms()

# 3. Read real video
source = Path(args.source)

cap = cv2.VideoCapture(str(source))

if not cap.isOpened():
    raise RuntimeError(f"Cannot open: {source}")

fps = cap.get(cv2.CAP_PROP_FPS)

if not np.isfinite(fps) or fps <= 0:
    raise RuntimeError("Invalid video FPS")

frames = []

while True:
    ok, frame = cap.read()

    if not ok:
        break

    frames.append(frame)

cap.release()

if not frames:
    raise RuntimeError("No video frames found")

total_frames = len(frames)
height, width = frames[0].shape[:2]

window_size = max(1, round(args.window_sec * fps))
stride = max(1, round(args.stride_sec * fps))

starts = list(range(
    0,
    max(1, total_frames - window_size + 1),
    stride
))

last_start = max(0, total_frames - window_size)

if starts[-1] != last_start:
    starts.append(last_start)

starts = sorted(set(starts))

print("Video:", source)
print("Frames:", total_frames)
print("FPS:", fps)
print("Windows:", len(starts))

# 4. Predict each video window
results = []

with torch.inference_mode():

    for i, start in enumerate(starts):

        end = min(start + window_size, total_frames)

        indices = np.linspace(
            start,
            end - 1,
            16
        ).astype(int)

        selected = np.stack([
            cv2.cvtColor(
                frames[j],
                cv2.COLOR_BGR2RGB
            )
            for j in indices
        ])

        tensor = torch.from_numpy(
            selected
        ).permute(0, 3, 1, 2)

        inputs = preprocess(tensor).unsqueeze(0)

        features = model(inputs).numpy()

        score = float(
            classifier.predict_proba(features)[0, 1]
        )

        prediction = (
            "POSSIBLE CONFLICT"
            if score >= THRESHOLD
            else "NO CONFLICT FLAG"
        )

        row = {
            "start_sec": round(start / fps, 3),
            "end_sec": round(end / fps, 3),
            "violence_score": round(score, 4),
            "prediction": prediction
        }

        results.append(row)

        print(
            f"Window {i+1}/{len(starts)} | "
            f"{row['start_sec']:.2f}s - "
            f"{row['end_sec']:.2f}s | "
            f"Score={score:.4f} | "
            f"{prediction}"
        )

# 5. Save timeline CSV
csv_path = OUTPUT_DIR / (
    source.stem + "_timeline.csv"
)

with csv_path.open(
    "w", newline="", encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "start_sec",
            "end_sec",
            "violence_score",
            "prediction"
        ]
    )

    writer.writeheader()
    writer.writerows(results)

# 6. Save annotated MP4
video_path = OUTPUT_DIR / (
    source.stem + "_annotated.mp4"
)

writer = cv2.VideoWriter(
    str(video_path),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (width, height)
)

if not writer.isOpened():
    raise RuntimeError("Could not create MP4")

for frame_index, frame in enumerate(frames):

    time_sec = frame_index / fps

    active = [
        r for r in results
        if r["start_sec"] <= time_sec < r["end_sec"]
    ]

    if active:
        score = max(
            r["violence_score"] for r in active
        )
    else:
        score = 0.0

    label = (
        "POSSIBLE PHYSICAL CONFLICT"
        if score >= THRESHOLD
        else "NO CONFLICT FLAG"
    )

    annotated = frame.copy()

    cv2.rectangle(
        annotated,
        (0, 0),
        (width, min(85, height)),
        (20, 20, 20),
        -1
    )

    scale = min(0.65, max(0.35, width / 1100))

    cv2.putText(
        annotated,
        label,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated,
        f"Time: {time_sec:.2f}s | "
        f"Window Score: {score:.3f}",
        (10, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.3, scale * 0.75),
        (255, 255, 255),
        1
    )

    writer.write(annotated)

writer.release()

print("\nDONE")
print("Timeline:", csv_path)
print("Annotated Video:", video_path)
