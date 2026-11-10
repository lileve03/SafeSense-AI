
from pathlib import Path
import cv2
import pandas as pd
import numpy as np

ROOT = Path("evaluation/outputs/fight_temporal_validation")
OUT = ROOT / "false_negative_inspection"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "adaptive_rule_results.csv")

fn = df[
    (df["ground_truth"] == 1) &
    (df["adaptive_prediction"] == 0)
].copy()

records = []

for row in fn.itertuples():
    path = Path(row.path)
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        print("Cannot open:", path)
        continue

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)

    cap.release()

    if not frames:
        continue

    duration = len(frames) / fps if fps > 0 else 0
    height, width = frames[0].shape[:2]

    indices = np.linspace(
        0, len(frames) - 1, 6
    ).astype(int)

    tiles = []

    for index in indices:
        frame = cv2.resize(frames[index], (320, 180))

        time_sec = index / fps if fps > 0 else 0

        cv2.putText(
            frame,
            f"{time_sec:.2f}s",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        tiles.append(frame)

    storyboard = np.vstack([
        np.hstack(tiles[:3]),
        np.hstack(tiles[3:])
    ])

    camera = path.parent.name
    filename = f"{camera}_{path.stem}_storyboard.jpg"

    cv2.imwrite(str(OUT / filename), storyboard)

    records.append({
        "video": path.name,
        "camera": camera,
        "duration_sec": round(duration, 2),
        "fps": round(fps, 2),
        "resolution": f"{width}x{height}",
        "frames": len(frames),
        "max_score": row.max_score,
        "storyboard": filename
    })

summary = pd.DataFrame(records)
summary.to_csv(
    OUT / "inspection_summary.csv",
    index=False
)

print("\n===== VIDEO INSPECTION =====")
print(summary.to_string(index=False))
print("\nStoryboards saved to:", OUT.resolve())
print("DONE")
