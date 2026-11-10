"""Evaluate pretrained YAMNet on official FSD50K weak clip labels (no fine-tuning)."""
import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np


def split_tags(value):
    return {s.strip() for s in (value or '').split(',') if s.strip()}


def read_ground_truth(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'fname', 'mids'}.issubset(reader.fieldnames or []):
            raise ValueError('Ground truth CSV requires fname and mids columns')
        for row in reader:
            yield row['fname'].strip(), split_tags(row['mids']), row.get('labels', '')


def load_yamnet(model_url):
    import tensorflow_hub as hub
    import tensorflow as tf
    model = hub.load(model_url)
    classmap = model.class_map_path().numpy().decode('utf-8')
    with open(classmap, encoding='utf-8', newline='') as f:
        mapping = list(csv.DictReader(f))
    return model, mapping, tf


def load_audio(path, tf):
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    audio, sample_rate = sf.read(str(path), dtype='float32', always_2d=True)
    audio = audio.mean(axis=1)
    if sample_rate != 16000:
        d = gcd(sample_rate, 16000)
        audio = resample_poly(audio, 16000 // d, sample_rate // d).astype(np.float32)
    if audio.size < 15600:
        audio = np.pad(audio, (0, 15600 - audio.size))
    audio = np.clip(audio, -1.0, 1.0)
    return tf.convert_to_tensor(audio, dtype=tf.float32)


def metrics(y_true, y_pred):
    tp = sum(a == 1 and b == 1 for a, b in zip(y_true, y_pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y_true, y_pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y_true, y_pred))
    tn = sum(a == 0 and b == 0 for a, b in zip(y_true, y_pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, precision=precision, recall=recall, f1=f1,
                accuracy=(tp + tn) / max(tp + fp + fn + tn, 1))


def main():
    parser = argparse.ArgumentParser(description='Evaluate YAMNet against FSD50K clip-level weak labels')
    parser.add_argument('--labels', required=True, help='Official FSD50K dev.csv or eval.csv')
    parser.add_argument('--audio-dir', required=True, help='Matching extracted .wav directory')
    parser.add_argument('--output-dir', default='evaluation/outputs/yamnet')
    parser.add_argument('--target', default='Screaming', help='Exact YAMNet class display_name, e.g. Screaming')
    parser.add_argument('--threshold', type=float, default=0.5, help='Fixed score threshold, NOT calibrated probability')
    parser.add_argument('--limit', type=int, default=0, help='0 = all available clips')
    parser.add_argument('--model-url', default='https://tfhub.dev/google/yamnet/1')
    parser.add_argument('--list-classes', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error('threshold must be 0..1')
    labels_file, audio_dir, output_dir = Path(args.labels), Path(args.audio_dir), Path(args.output_dir)
    if not labels_file.is_file():
        parser.error(f'Labels not found: {labels_file}')
    if not audio_dir.is_dir():
        parser.error(f'Audio directory not found: {audio_dir}')
    print('Loading pretrained YAMNet (first run downloads model)...', flush=True)
    model, mapping, tf = load_yamnet(args.model_url)
    if args.list_classes:
        for r in mapping:
            if any(x in r['display_name'].lower() for x in ('scream', 'shout', 'slam', 'bang', 'thud', 'impact')):
                print(r['index'], r['mid'], r['display_name'])
        return
    matched = [r for r in mapping if r['display_name'].strip().casefold() == args.target.strip().casefold()]
    if len(matched) != 1:
        examples = [r['display_name'] for r in mapping if args.target.lower() in r['display_name'].lower()]
        raise ValueError(f'No unique YAMNet class for {args.target!r}. Possible matches: {examples}')
    target = matched[0]
    target_mid, target_index = target['mid'], int(target['index'])
    if not target_mid:
        raise RuntimeError('Selected YAMNet class has no MID; cannot match official FSD50K ground truth.')
    print(f"Target: {target['display_name']} | AudioSet MID: {target_mid} | threshold={args.threshold}")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / 'yamnet_predictions.csv'
    rows, skipped = [], []
    original = list(read_ground_truth(labels_file))
    if args.limit:
        original = original[:args.limit]
        print('WARNING: limited subset; scores are not full benchmark results.')
    for n, (fname, mids, labels) in enumerate(original, 1):
        filename = audio_dir / (fname + '.wav')
        if not filename.exists():
            skipped.append((fname, 'audio file missing'))
            continue
        try:
            waveform = load_audio(filename, tf)
            tic = time.perf_counter()
            scores, _, _ = model(waveform)
            inference_ms = (time.perf_counter() - tic) * 1000.0
            # Maximum across time is a weak event-presence score, not calibrated probability.
            score = float(np.max(scores.numpy()[:, target_index]))
            row = dict(filename=filename.name, ground_truth=int(target_mid in mids),
                       score=score, predicted=int(score >= args.threshold),
                       inference_ms=round(inference_ms, 2), target=target['display_name'],
                       target_mid=target_mid, split=labels_file.stem,
                       gt_labels=labels)
            rows.append(row)
            if n % 100 == 0:
                print(f'Processed {n}/{len(original)}; evaluated={len(rows)}; skipped={len(skipped)}', flush=True)
        except Exception as e:
            skipped.append((fname, f'{type(e).__name__}: {e}'))
    if not rows:
        raise RuntimeError('No files were evaluated. Check audio-dir and labels filenames.')
    with out_file.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with (output_dir / 'skipped_files.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['fname', 'reason']); w.writerows(skipped)
    y_true = [r['ground_truth'] for r in rows]
    y_pred = [r['predicted'] for r in rows]
    if sum(y_true) == 0 or sum(y_true) == len(y_true):
        print('WARNING: evaluated subset contains only one true class; metrics are not representative.')
    summary = metrics(y_true, y_pred)
    summary.update(target=args.target, target_mid=target_mid, threshold=args.threshold,
                   evaluated_clips=len(rows), positive_clips=sum(y_true),
                   skipped_clips=len(skipped), score_aggregation='max_over_yamnet_frames',
                   ground_truth='FSD50K clip-level MID labels',
                   model_url=args.model_url)
    with (output_dir / 'yamnet_metrics.json').open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with (output_dir / 'yamnet_metrics.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(summary)); w.writeheader(); w.writerow(summary)
    print('\nRESULT', json.dumps(summary, indent=2))
    print('Saved:', out_file, 'and metrics and skipped_files.csv')
    print('Interpretation: FSD50K weak clip labels; not timestamped event detection or live school safety performance.')

if __name__ == '__main__':
    main()
