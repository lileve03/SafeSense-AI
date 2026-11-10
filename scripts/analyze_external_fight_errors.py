
from pathlib import Path
import cv2
import pandas as pd

ROOT = Path("evaluation/outputs/fight_external_v2")

df = pd.read_csv(ROOT / "external_predictions.csv")

def get_video_info(path):
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        return pd.Series({
            "duration_sec": None,
            "fps": None,
            "width": None,
            "height": None
        })

    fps = cap.get(cv2.CAP_PROP_FPS)
    nframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()

    return pd.Series({
        "duration_sec": round(nframes / fps, 2) if fps > 0 else None,
        "fps": round(fps, 2),
        "width": int(width),
        "height": int(height)
    })

info = df["path"].apply(get_video_info)
df = pd.concat([df, info], axis=1)

df["error_type"] = "CORRECT"
df.loc[
    (df["ground_truth"] == 1) &
    (df["prediction"] == 0),
    "error_type"
] = "FALSE_NEGATIVE"

df.loc[
    (df["ground_truth"] == 0) &
    (df["prediction"] == 1),
    "error_type"
] = "FALSE_POSITIVE"

print("\n===== EXTERNAL SCORE DISTRIBUTION =====")
print(
    df.groupby("category")["violence_score"]
    .describe()
    .round(4)
    .to_string()
)

print("\n===== VIDEO DURATION =====")
print(
    df.groupby("category")["duration_sec"]
    .describe()
    .round(2)
    .to_string()
)

fn = df[df["error_type"] == "FALSE_NEGATIVE"]
fp = df[df["error_type"] == "FALSE_POSITIVE"]

# Most confident incorrect predictions
fn_examples = fn.nsmallest(5, "violence_score")
fp_examples = fp.nlargest(5, "violence_score")

print("\n===== 5 WORST FALSE NEGATIVES =====")
print(
    fn_examples[
        ["path", "duration_sec", "violence_score"]
    ].to_string(index=False)
)

print("\n===== 5 WORST FALSE POSITIVES =====")
print(
    fp_examples[
        ["path", "duration_sec", "violence_score"]
    ].to_string(index=False)
)

df.to_csv(
    ROOT / "external_diagnostic.csv",
    index=False
)

print("\nSaved:", ROOT / "external_diagnostic.csv")
print("DONE")
