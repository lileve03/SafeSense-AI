
from pathlib import Path
import argparse
import cv2
import numpy as np
from ultralytics import YOLO

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
args = parser.parse_args()

SOURCE = Path(args.source)
OUT = Path("evaluation/outputs/fight_input_comparison")
OUT.mkdir(parents=True, exist_ok=True)

# Load pretrained YOLO11 person detector
detector = YOLO("yolo11n.pt")

cap = cv2.VideoCapture(str(SOURCE))
frames = []

while True:
    ok, frame = cap.read()
    if not ok:
        break
    frames.append(frame)

cap.release()

if not frames:
    raise RuntimeError("Cannot read input video")

height, width = frames[0].shape[:2]

# Sample 6 frames across the whole clip
indices = np.linspace(
    0, len(frames) - 1, 6
).astype(int)

selected = [frames[i] for i in indices]

# Detect people separately for each sampled frame
crop_regions = []

for frame in selected:
    result = detector.predict(
        frame,
        classes=[0],
        conf=0.35,
        verbose=False,
        device="cpu"
    )[0]

    detected = result.boxes.xyxy.cpu().numpy()

    # Keep at most the two largest detected persons
    if len(detected) > 0:
        areas = (
            (detected[:, 2] - detected[:, 0]) *
            (detected[:, 3] - detected[:, 1])
        )
        detected = detected[np.argsort(areas)[::-1][:2]]

        bx1 = detected[:, 0].min()
        by1 = detected[:, 1].min()
        bx2 = detected[:, 2].max()
        by2 = detected[:, 3].max()

        pad_x = (bx2 - bx1) * 0.25
        pad_y = (by2 - by1) * 0.25

        x1 = max(0, int(bx1 - pad_x))
        y1 = max(0, int(by1 - pad_y))
        x2 = min(width, int(bx2 + pad_x))
        y2 = min(height, int(by2 + pad_y))

        crop_regions.append((x1, y1, x2, y2))
    else:
        crop_regions.append((0, 0, width, height))

print("Per-frame crop regions:")
for i, region in enumerate(crop_regions):
    print(f"Frame {i+1}: {region}")

# Resize without stretching the image
def make_tile(image, label):
    target_w, target_h = 400, 250

    h, w = image.shape[:2]
    ratio = min(target_w / w, 220 / h)

    new_w = max(1, int(w * ratio))
    new_h = max(1, int(h * ratio))

    resized = cv2.resize(image, (new_w, new_h))

    tile = np.full(
        (target_h, target_w, 3),
        30,
        dtype=np.uint8
    )

    offset_x = (target_w - new_w) // 2
    offset_y = 25 + (220 - new_h) // 2

    tile[
        offset_y:offset_y + new_h,
        offset_x:offset_x + new_w
    ] = resized

    cv2.putText(
        tile,
        label,
        (10, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1
    )

    return tile

original_tiles = []
cropped_tiles = []

for i, frame in enumerate(selected):
    x1, y1, x2, y2 = crop_regions[i]
    original = frame.copy()
    cv2.rectangle(
        original, (x1, y1), (x2, y2),
        (255, 0, 0), 4
    )

    crop = frame[y1:y2, x1:x2]

    original_tiles.append(
        make_tile(original, f"Original - frame {i+1}")
    )

    cropped_tiles.append(
        make_tile(crop, f"Person Crop - frame {i+1}")
    )

# 2 rows x 6 frames:
# top = original, bottom = crop
comparison = np.vstack([
    np.hstack(original_tiles),
    np.hstack(cropped_tiles)
])

output_path = OUT / (
    SOURCE.parent.name + "_" +
    SOURCE.stem + "_comparison.jpg"
)

cv2.imwrite(str(output_path), comparison)

print("\nDONE")
print("Comparison saved:", output_path.resolve())
