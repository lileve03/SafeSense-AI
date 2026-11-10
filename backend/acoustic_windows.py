"""Metadata-only YAMNet windows adapted from the extracted Phase 2 infer_audio/audio_peak_events.
Nominal model-window offsets are not validated event timestamps or synchronized sensor time.
"""
import math

def score_windows(series, threshold, duration):
    values=[float(value) for value in series]
    if not values or len(values)>1000 or not math.isfinite(duration) or duration<=0:
        raise ValueError('Invalid acoustic window series')
    if not math.isfinite(threshold) or not 0<=threshold<=1:
        raise ValueError('Invalid acoustic threshold')
    if any(not math.isfinite(value) or not 0<=value<=1 for value in values):
        raise ValueError('Invalid acoustic model score')
    # Phase 2 enumerates YAMNet scores on its nominal 0.48-second hop.
    # Preserve full model values; explicitly describe the 0.96-second receptive window/padding.
    points=[{'index':i,'start_sec':round(i*0.48,6),'end_sec':round(min(duration,i*0.48+0.96),6),
             'score':value,'above_threshold':value>=threshold}
            for i,value in enumerate(values) if i*0.48<duration]
    return {'score_windows':points,'window_hop_sec':0.48,'window_length_sec':0.96,
            'window_time_scope':'nominal_recording_offsets_not_validated_event_times',
            'above_threshold_windows':sum(p['above_threshold'] for p in points)}
