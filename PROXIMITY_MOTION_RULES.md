# Anonymous-track proximity and temporal motion rules

These are deterministic, explainable **review candidates**, not fighting/bullying detection or machine-learning predictions. Normal conversation, queuing, exercise and pacing can satisfy these rules. There is no claimed accuracy, confidence, intent, emergency probability or diagnosis. New motion candidates do not automatically create incidents, alter risk/fusion rules, send notifications, or replace the existing radar fall classifier.

## Try the demonstrations

Open **Digital Twin Map → Private Area 3D View → Source mode: SIMULATION**. In the existing tracking controls choose **Repeated back-and-forth motion (review demo)** or **Sustained nearby tracks (review demo)**. Start playback or seek to 14 seconds (repeated motion) / 12 seconds (proximity).

The backend readout shows nearest anonymous-track distance, observed proximity duration, rule conditions, explanatory candidate reasons and per-track motion features. Expand **Explainable motion features** for speed, acceleration, heading/change angle, reversal count, sample count, observed span and path length. Magenta rings highlight relevant tracks inside the original Toilet scene; gold still identifies a selected track. Seeking/restarting changes the simulation analysis session and clears previous results before requesting new ones. The existing room, fixtures, navigation, theme, private-area safeguards and hardware-disconnected status remain preserved.

Simulation previews reconstruct explicitly synthetic history using normalized Observation objects. A preview is not a claim that a physical duration was observed. The browser sends no rule settings. It obtains the analysis window from the backend and requests a bounded preview at at most 2 Hz; drawing still uses the existing renderer. These preview requests do not write SQLite observations/events/incidents or send notifications.

## Backend configuration

All deployment thresholds are defined by immutable `MotionRules` / `RULES` in `backend/track_motion.py`. Change them there and restart the backend. `GET /sensors/motion/rules` exposes the actual defaults and rule version. Playback speed and timeline controls do not change thresholds.

| Rule/condition | Default |
| --- | --- |
| Proximity | 3D point separation strictly **< 0.8 m** |
| Proximity duration | **≥ 3.0 seconds**, continuously near in the supported sampled sequence |
| Motion analysis window | Latest **8 seconds** of supported samples |
| Minimum observed span | **4 seconds** |
| Meaningful direction reversals | **≥ 3**, successive horizontal displacement-leg angle **≥ 150°** |
| Meaningful travel leg | Horizontal displacement **≥ 0.35 m**, duration **≥ 0.2 s**, mean travel speed **≥ 0.2 m/s** |
| Additional repeated-motion conditions | Horizontal path **≥ 2 m**, net displacement / path **≤ 0.5** |
| Maximum continuity gap | **0.75 seconds** |
| Temporal feature sampling | At most approximately **20 Hz** (minimum interval 0.05 s) |
| Quality filter | Exclude supplied quality **< 0.3**; omitted quality remains unknown, not fabricated |
| Possible ID reuse / implausible step | Displacement **> 2 m** or coordinate-derived speed **> 6 m/s** resets that ID's history and related pair duration |
| Implausible reported velocity | Magnitude **> 6 m/s** is ignored with an explanation; supported coordinate-delta estimates may still be used |
| Coordinate safety bound | Exclude any absolute coordinate **> 1000 m**, non-finite or missing xyz |
| Bounded state | Up to **256 feature samples / track**, **64 streams**, idle stream expiry **60 s** |

Proximity duration starts at the first qualifying pair frame and resets on an outside-threshold sample, missing/excluded ID, invalid input, changed session or excessive gap. It measures the span supported by sampled observations; movement between samples remains unknown. Distances are Euclidean `hypot(dx,dy,dz)` between supplied track points, not body-edge distances, contact or verified social interaction.

Reversal rules use accumulated meaningful **coordinate displacement legs**, not raw velocity sign flips. Tiny jitter, stationary noisy velocity reports and gradual circular turns do not establish back-and-forth travel. Velocity uses a supplied finite, plausible vector when available; otherwise supported position differences are explicitly labeled `position_delta`. Acceleration is a finite difference of consecutive velocities from the same origin. A first sample, missing predecessor or changed velocity origin has no acceleration estimate. Heading and reversal directions use calibrated horizontal x/y axes, so vertical centroid/fall motion is not interpreted as pacing. Derivative features are estimates affected by sampling and tracker noise; acceleration/heading changes alone do not trigger a threat classification.

## Data and continuity contract

The normalized Observation schema in `backend/sensor_observations.py` now accepts optional `tracking_session_id`. For temporal rules the adapter must supply:

1. `data_validity: VALID` and `coordinate_frame: zone_meters_x_right_y_forward_z_up`.
2. Finite anonymous track `id` plus valid x/y/z coordinates in meters. Optional velocity is meters/second; optional quality is 0–1.
3. Timezone-aware, strictly increasing **capture timestamps**, identified by `timestamp_basis: CAPTURE_TIME`.
4. A stable, explicit `tracking_session_id`, device ID, zone ID and source mode. Start a new session on sensor restart, recording changes, calibration changes, tracker identity resets or ID reassignment.

State is isolated by `(source_mode, device_id, zone_id, tracking_session_id)`. A missing position or low-quality sample drops that ID's history and related proximity duration; no zero coordinates, zero distance or guessed identity is substituted. Dropped and newly appearing IDs never inherit another track's history. Duplicate IDs invalidate the frame. Non-increasing timestamps clear continuity. Large jumps reset history conservatively; there is no re-identification or extrapolation across missing frames. A tracker that silently swaps IDs with physically plausible coordinates cannot always be detected; stable device identity/session semantics and tracker validation remain necessary.

Nearest instantaneous distance can be supported by a single valid spatial frame even when capture-time/session provenance is insufficient for temporal analysis. Such frames show a partial result and **no temporal candidate**. Unknown or unsupported data is unavailable, not a safety verdict. Backend restart/idle expiry starts a new warm-up window rather than reconstructing continuous motion from unrelated stored rows.

The same analyzer handles SIMULATION, RECORDED_REPLAY and LIVE_HARDWARE envelopes. Existing recorded radar fall classifications and acoustic labels do not contain calibrated anonymous people tracks; they therefore get no invented nearest distance, trajectories or temporal features. Raw radar point clouds are not anonymous person tracks. A future server-side recorded-track loader or verified physical adapter may call the existing `save(Observation(...))` boundary with actual supported track frames and session/capture provenance. Direct browser-authored recorded/live preview data is rejected, and the hardware adapter remains disconnected until commissioned.

## Integration and persistence

- Normalized `save()` analyzes accepted new observations and attaches `motion_analysis` to their SQLite `sensor_observation` body. Existing incident records and classifiers are preserved.
- Repeated observation IDs remain idempotent and do not advance temporal state twice. Pre-upgrade records without `tracking_session_id` remain retry-compatible; no old record or incident is rewritten.
- `GET /sensors/observations` returns the stored analysis; stale current observations have unavailable analysis/highlights. Older records without analysis receive a one-frame read-only assessment, not an invented history.
- `GET /sensors/motion/rules` exposes backend-owned thresholds and version.
- `POST /sensors/motion/preview` accepts 1–121 explicit SIMULATION observations, at most eight tracks/frame, one device/zone/session, and no point cloud. It runs the same analyzer with independent bounded state and returns analysis without persistence or event creation. Extra `rules`/threshold overrides are rejected.

The normalized API retains staff-token authentication, private-zone restrictions, replay evidence provenance and fail-closed live hardware ingestion. See [HARDWARE_SENSOR_INTERFACE.md](HARDWARE_SENSOR_INTERFACE.md) for physical commissioning requirements. Nothing here connects a sensor or fabricates ML performance.

## Verification

`tests/test_track_motion.py` covers distance math, continuous duration, meaningful reversals, finite-difference features, missing/low-quality data, capture/session requirements, gaps, ID changes/reuse, duplicate/out-of-order data, source isolation and false-trigger cases (straight walking, one turn, circles, jitter and noisy reported velocity). `tests/test_track_motion_api.py` checks trusted boundaries, configuration ownership, persistence, retry compatibility and absence of automatic motion-candidate escalation. Existing radar/fall tests are retained. Browser tests exercise both new candidates, feature explanations, nearest distance and 3D highlights.

Actual executed results are documented in [PROXIMITY_MOTION_TEST_RESULTS.md](PROXIMITY_MOTION_TEST_RESULTS.md).
