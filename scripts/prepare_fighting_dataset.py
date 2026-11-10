from pathlib import Path
import csv
import random
from collections import defaultdict

ROOT = Path(
    "datasets/open_hidden/fighting/raw/AIRTLab/"
    "A-Dataset-for-Automatic-Violence-Detection-in-Videos-master/"
    "violence-detection-dataset"
)

OUTPUT = Path("datasets/open_hidden/fighting/airtlab_split.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

RNG = random.Random(42)
rows = []

for label in ("violent", "non-violent"):
    groups = defaultdict(list)

    for camera in ("cam1", "cam2"):
        folder = ROOT / label / camera

        for video in folder.glob("*.mp4"):
            groups[video.stem].append(video)

    group_ids = sorted(groups)
    RNG.shuffle(group_ids)

    n = len(group_ids)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)

    for i, group_id in enumerate(group_ids):
        if i < n_train:
            split = "train"
        elif i < n_train + n_val:
            split = "val"
        else:
            split = "test"

        for video in groups[group_id]:
            rows.append({
                "path": str(video.resolve()),
                "label": label,
                "group_id": f"{label}_{group_id}",
                "split": split,
            })

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["path", "label", "group_id", "split"]
    )
    writer.writeheader()
    writer.writerows(rows)

summary = defaultdict(int)
for row in rows:
    summary[(row["split"], row["label"])] += 1

print("\nDATASET SPLIT SUMMARY")
for key, count in sorted(summary.items()):
    print(key, count)

assert len(rows) == len({r["path"] for r in rows})

group_splits = defaultdict(set)
for row in rows:
    group_splits[row["group_id"]].add(row["split"])

assert all(len(v) == 1 for v in group_splits.values())

print("\nTotal videos:", len(rows))
print("Total groups:", len(group_splits))
print("Group leakage check: PASS")
print("Saved:", OUTPUT.resolve())
