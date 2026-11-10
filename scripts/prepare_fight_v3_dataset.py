
from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import random
import pandas as pd

BASE = Path("datasets/open_hidden/fighting")

AIR_CSV = BASE / "airtlab_split.csv"
MOVIE_ROOT = BASE / "raw/Archive6/Peliculas"

OUT = BASE / "v3"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
rng = random.Random(SEED)

# 1. Load existing AIRTLab split
air = pd.read_csv(AIR_CSV)

assert len(air) == 350
assert set(air["split"]) == {"train", "val", "test"}
assert air.groupby("group_id")["split"].nunique().max() == 1

air["source"] = "AIRTLab"

# Keep original AIRTLab splits unchanged
air = air[[
    "path", "label", "group_id", "split", "source"
]]

# 2. Discover Peliculas videos
records = []

for folder, label in [
    ("fights", "violent"),
    ("noFights", "non-violent")
]:
    directory = MOVIE_ROOT / folder

    if not directory.exists():
        raise FileNotFoundError(directory)

    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {
            ".avi", ".mpg", ".mpeg", ".mp4"
        }:
            continue

        records.append({
            "path": str(path.resolve()),
            "label": label,
            "source": "Peliculas"
        })

movies = pd.DataFrame(records)
assert len(movies) == 201

# 3. Check exact duplicate video files
def sha256_file(path):
    digest = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()

print("Checking file hashes...")

movies["sha256"] = [
    sha256_file(p) for p in movies["path"]
]

# Same bytes, possibly duplicated filenames
duplicate_count = movies["sha256"].duplicated().sum()

print("Exact duplicate files:", duplicate_count)

# Flag conflicting labels for the same file
label_conflicts = (
    movies.groupby("sha256")["label"]
    .nunique()
)

if (label_conflicts > 1).any():
    raise RuntimeError(
        "Identical files have conflicting labels"
    )

# 4. Assign groups based on identical-file hashes
movies["group_id"] = (
    "peliculas_" + movies["sha256"].str[:16]
)

# 5. Group-aware split per label
group_to_label = (
    movies.groupby("group_id")["label"]
    .first()
)

assignments = {}

for label in ["violent", "non-violent"]:
    groups = group_to_label[
        group_to_label == label
    ].index.tolist()

    rng.shuffle(groups)
    n = len(groups)

    n_train = int(n * 0.70)
    n_val = int(n * 0.15)

    for group in groups[:n_train]:
        assignments[group] = "train"

    for group in groups[n_train:n_train+n_val]:
        assignments[group] = "val"

    for group in groups[n_train+n_val:]:
        assignments[group] = "test"

movies["split"] = movies["group_id"].map(assignments)

movies = movies[[
    "path", "label", "group_id", "split", "source"
]]

# 6. Combine two sources
combined = pd.concat(
    [air, movies],
    ignore_index=True
)

# 7. Validation checks
assert len(combined) == 551
assert combined["path"].is_unique

assert (
    combined.groupby(["source", "group_id"])["split"]
    .nunique()
    .max() == 1
)

missing = [
    p for p in combined["path"]
    if not Path(p).exists()
]

if missing:
    raise RuntimeError(
        f"{len(missing)} videos are missing"
    )

# 8. Save full manifest
manifest = OUT / "v3_dataset_manifest.csv"
combined.to_csv(manifest, index=False)

# Save development data separately
development = combined[
    combined["split"].isin(["train", "val"])
]

development.to_csv(
    OUT / "v3_development.csv",
    index=False
)

# Preserve test list without using it for training
heldout = combined[
    combined["split"] == "test"
]

heldout.to_csv(
    OUT / "v3_reserved_test.csv",
    index=False
)

print("\n===== V3 DATASET SUMMARY =====")
print(
    combined.groupby(
        ["source", "split", "label"]
    ).size().to_string()
)

print("\nTotal videos:", len(combined))
print("Train:", sum(combined.split == "train"))
print("Validation:", sum(combined.split == "val"))
print("Reserved Test:", sum(combined.split == "test"))
print("Group leakage check: PASS")
print("Manifest:", manifest.resolve())
print("DONE")

