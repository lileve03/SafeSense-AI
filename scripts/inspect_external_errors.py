
from pathlib import Path
import cv2
import numpy as np
import pandas as pd

ROOT = Path("evaluation/outputs/fight_external_v2")
OUT = ROOT / "error_storyboards"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "external_predictions.csv")

# Select 5 most confident false negatives
fn = df[
    (df["ground_truth"] == 1) &
    (df["prediction"] == 0)
].nsmallest(5, "violence_score")

# Select 5 most confident false positives
fp = df[
    (df["ground_truth"] == 0) &
    (df["prediction"] == 1)
].nlargest(5, "violence_score")

cases = [
    ("FN", row)
    for row in fn.itertuples(index=False)
] + [
    ("FP", row)
    for row in fp.itertuples(index=False)
]

def make_tile(frame, label):
    target_w, target_h = 320, 200
    h, w = frame.shape[:2]
    scale = min(target_w / w, 170 / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))

    canvas = np.full(
        (target_h, target_w, 3), 30, dtype=np.uint8
    )
    resized = cv2.resize(frame, (nw, nh))

    x = (target_w - nw) // 2
    y = 28 + (170 - nh) // 2

    canvas[y:y+nh, x:x+nw] = resized

    cv2.putText(
        canvas, label, (8, 19),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48, (255, 255, 255), 1
    )
    return canvas

records = []

for kind, row in cases:
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
        print("No frames:", path)
        continue

    indices = np.linspace(
        0, len(frames)-1, 6
    ).astype(int)

    tiles = []
    for index in indices:
        t = index / fps if fps > 0 else 0
        tiles.append(
            make_tile(frames[index], f"{t:.2f}s")
        )

    storyboard = np.vstack([
        np.hstack(tiles[:3]),
        np.hstack(tiles[3:])
    ])

    filename = f"{kind}_{path.stem}_storyboard.jpg"
    output = OUT / filename

    cv2.imwrite(str(output), storyboard)

    records.append({
        "type": kind,
        "video": path.name,
        "ground_truth": row.ground_truth,
        "violence_score": round(row.violence_score, 4),
        "duration_sec": round(len(frames)/fps, 2)
            if fps > 0 else None,
        "storyboard": filename
    })

summary = pd.DataFrame(records)
summary.to_csv(
    OUT / "storyboard_summary.csv", index=False
)

print("\n===== EXTERNAL STORYBOARD SUMMARY =====")
print(summary.to_string(index=False))
print("\nSaved:", OUT.resolve())
print("DONE")
