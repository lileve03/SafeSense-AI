"""SafeSense Phase 4: microphone -> YAMNet -> optional FastAPI event.

Only short in-memory audio buffers are processed. No audio is stored.
For a local, supervised proof of concept; not a certified safety detector.
"""
import argparse
import csv
import math
import time
from collections import defaultdict
from pathlib import Path
from urllib import request, error
import json
import os

MODEL_URL = "https://tfhub.dev/google/yamnet/1"


def post_event(api_base: str, zone: str, event_type: str, confidence: float):
    payload = json.dumps({
        "zone": zone,
        "type": event_type,
        "confidence": round(float(confidence), 4),
        "source": "yamnet", "processing_mode": "real_model",
        "score": round(float(confidence),4), "model_version": "YAMNet-scream-impact-experimental",
        "evidence_reference": "transient_non_speech_event; no waveform retained",
    }).encode("utf-8")
    req = request.Request(
        url=api_base.rstrip("/") + "/event",
        data=payload,
        headers={"Content-Type": "application/json", "X-SafeSense-Token": os.getenv("SAFESENSE_API_TOKEN", "local-demo-only")},
        method="POST",
    )
    with request.urlopen(req, timeout=5) as response:
        return json.load(response)


def load_names(model):
    raw = model.class_map_path().numpy()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    with open(raw, newline="", encoding="utf-8") as fh:
        return [row["display_name"] for row in csv.DictReader(fh)]


def choose_classes(names):
    """Restrictive mapping avoids treating normal conversation as an incident."""
    scream_words = {"screaming", "scream"}
    impact_words = {"thump, thud", "bang", "crash", "glass", "breaking"}
    selected = {"scream": [], "impact": []}
    for idx, name in enumerate(names):
        normalized = name.lower().strip()
        if normalized in scream_words or normalized.startswith("screaming"):
            selected["scream"].append(idx)
        if normalized in impact_words or normalized in {"glass shatter", "glass breaking", "breaking glass"}:
            selected["impact"].append(idx)
    return selected


def main():
    parser = argparse.ArgumentParser(description="Local SafeSense YAMNet microphone pilot")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--device", type=int, default=None, help="Input device index from --list-devices")
    parser.add_argument("--zone", default="Demo-Private-A")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--consecutive", type=int, default=2)
    parser.add_argument("--cooldown", type=float, default=15.0)
    parser.add_argument("--duration", type=float, default=1.25, help="Audio duration seconds per inference (>= 0.975)")
    parser.add_argument("--send", action="store_true", help="Opt-in: POST candidate events to local API")
    args = parser.parse_args()

    import sounddevice as sd
    if args.list_devices:
        print(sd.query_devices())
        return
    if args.duration < 0.975:
        parser.error("--duration must be >= 0.975 seconds")
    if not 0 < args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")
    if args.consecutive < 1:
        parser.error("--consecutive must be >= 1")

    # Import heavyweight packages after lightweight device listing succeeds.
    import numpy as np
    import tensorflow as tf
    import tensorflow_hub as hub
    from scipy.signal import resample_poly

    device_info = sd.query_devices(args.device, "input")
    input_sr = int(round(device_info["default_samplerate"]))
    if input_sr < 8000:
        raise RuntimeError(f"Unexpected input device sampling rate: {input_sr}")
    print(f"Input device: {device_info['name']} (capture {input_sr} Hz; YAMNet 16000 Hz)")
    print("Loading YAMNet (first run downloads model from TensorFlow Hub)...")
    model = hub.load(MODEL_URL)
    names = load_names(model)
    target_indexes = choose_classes(names)
    print("Mapped categories:", {k: [names[i] for i in v] for k, v in target_indexes.items()})
    if not target_indexes["scream"]:
        print("WARNING: YAMNet class map has no screaming class; scream output will be disabled")
    if not target_indexes["impact"]:
        print("WARNING: YAMNet class map has no impact classes; impact output will be disabled")
    print("MODE:", "SEND REAL MODEL CANDIDATES TO FASTAPI (EXPERIMENTAL)" if args.send else "LOCAL PREVIEW ONLY")
    print("No raw audio files, transcripts, or waveforms are saved. Press Ctrl+C to stop.")

    streaks = defaultdict(int)
    last_sent = defaultdict(lambda: -float("inf"))
    try:
        while True:
            recording = sd.rec(
                frames=int(input_sr * args.duration),
                samplerate=input_sr,
                channels=1,
                dtype="float32",
                device=args.device,
                blocking=True,
            )
            waveform = np.asarray(recording[:, 0], dtype=np.float32)
            if input_sr != 16000:
                divisor = math.gcd(input_sr, 16000)
                waveform = resample_poly(waveform, 16000 // divisor, input_sr // divisor).astype(np.float32)
            scores, _, _ = model(tf.convert_to_tensor(waveform, dtype=tf.float32))
            # Max over YAMNet frames favors short transients; tune on test recordings.
            frame_scores = scores.numpy()
            top_indices = np.argsort(frame_scores.max(axis=0))[-3:][::-1]
            top = ", ".join(f"{names[i]} {frame_scores[:, i].max():.2f}" for i in top_indices)
            print(f"Top sounds: {top}")
            now = time.monotonic()
            for kind, idxs in target_indexes.items():
                confidence = float(frame_scores[:, idxs].max()) if idxs else 0.0
                streaks[kind] = streaks[kind] + 1 if confidence >= args.threshold else 0
                if streaks[kind] >= args.consecutive and now - last_sent[kind] >= args.cooldown:
                    print(f"  CANDIDATE {kind.upper()} conf={confidence:.3f} ({streaks[kind]} windows)")
                    if args.send:
                        try:
                            result = post_event(args.api, args.zone, kind, confidence)
                            level = result.get("event", {}).get("level", "?")
                            print(f"  POST success: {kind} -> {level}")
                            last_sent[kind] = now
                        except error.HTTPError as exc:
                            print(f"  Backend rejected request HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}")
                        except (error.URLError, TimeoutError) as exc:
                            print(f"  Backend unavailable: {exc}")
                    else:
                        last_sent[kind] = now
    except KeyboardInterrupt:
        print("\nStopped. No raw audio was saved.")


if __name__ == "__main__":
    main()
