# Private-area sensor deployment interface

Anonymous-track distance and temporal analysis is described in [PROXIMITY_MOTION_RULES.md](PROXIMITY_MOTION_RULES.md). It adds optional `tracking_session_id`, backend-owned candidate rules and explainable `motion_analysis` output, while preserving classification-only replay limitations and disconnected hardware status.

The original Toilet Three.js room, radar tracking simulation, acoustic pipeline, SOS workflow, fusion engine, and SQLite incident records are retained. The room and fixture locations remain illustrative. No physical sensor is connected or verified. The interface reports **Hardware Disconnected**, including when the FastAPI server is online.

## Capabilities

| Adapter | Current inputs | Spatial capabilities | Physical verification |
| --- | --- | --- | --- |
| SIMULATION | Explicit synthetic normalized observations; original scripted radar preview retained | Optional synthetic anonymous tracks/points, always labeled simulation | Never |
| RECORDED_REPLAY | Existing saved radar/acoustic predictions and fresh model inference on registered recordings | Current recorded classification outputs have no tracks, positions, count, velocity or distance; these fields remain null | Never |
| LIVE_HARDWARE | Extension stub only; ingestion returns HTTP 503 | No capabilities enabled before commissioning | Disconnected |

Radar point returns are not people. Track counts are anonymous tracker outputs, not verified occupancy. A class label or fall score cannot establish a location, people count, distance, measured height, velocity, or a physical fall. Acoustic metadata includes only `scream`, `impact`, and `normal_acoustic`; no raw audio, speech, transcripts, images, video, or biometric identities are accepted.

The existing TI IWR6843 benchmark reads `frame,x,y,z,v` and optional SNR from raw recordings, then aggregates features for classification. Those sensor-frame returns are not calibrated Toilet-room positions or anonymous person tracks. This adapter deliberately exposes the existing classification result only. Mapping a raw point cloud into this room requires a documented recording coordinate system and valid zone transform. The existing acoustic window helper labels model timing as nominal recording offsets, not synchronized sensor capture time.

## Version 1 observation

`backend/sensor_observations.py` defines the Pydantic/OpenAPI contract. All nested models reject unknown fields, non-finite coordinates, out-of-range confidence/quality, and excessive arrays. Timestamps must have a timezone. Optional fields distinguish unsupported (`null`) from an explicitly supplied empty list.

```json
{
  "schema_version": 1,
  "source_mode": "SIMULATION",
  "device_id": "simulated-radar-01",
  "zone_id": "ZONE_TOILET_BLINDSPOT",
  "timestamp": "2026-11-02T06:00:00Z",
  "timestamp_basis": "CAPTURE_TIME",
  "observation_id": "unique-frame-id",
  "data_validity": "VALID",
  "validity_reason": "Explicit synthetic example; timestamp must be current for fusion",
  "coordinate_frame": "zone_meters_x_right_y_forward_z_up",
  "tracks": [{"id": "anonymous-1", "position": {"x": 1, "y": 2, "z": 0.8}, "velocity": {"x": 0, "y": 0, "z": 0}, "quality": 0.9}],
  "point_cloud": null,
  "radar_event": "presence",
  "confidence": 0.9,
  "acoustic_events": null,
  "sos_state": "UNKNOWN",
  "evidence_reference": "synthetic example"
}
```

Track ID is required; position, velocity, quality (0–1) and SNR (dB) are optional. Coordinates use meters with x right, y forward, z up in a registered zone frame; velocity uses meters/second. Spatial payloads require the coordinate-frame declaration. Three.js maps these axes to `(x,z,y)` without inventing positions. The hardware adapter must validate the actual calibration before allowing such a declaration. The current renderer displays supplied valid tracks/point clouds as points, not inferred people. Distances remain unavailable rather than inferred from missing data.

`data_validity` is VALID, INVALID, STALE, or UNAVAILABLE. For current synthetic ingestion, capture times outside -5 to +10 seconds of server time are stored as STALE and do not enter fusion. Reads age out current data after 10 seconds; recorded classifications remain historical evidence. Recorded timestamps explicitly use REPLAY_EVENT_TIME: they describe the existing backend replay event, not original sensor acquisition time. Capture time is unavailable in the current prediction files. Server `received_at` records ingestion separately.

## API and adapters

All routes use the existing `X-SafeSense-Token` authentication and registered private-zone restrictions:

- `GET /sensors/observations/status`: modes, current hardware verification state and recorded capabilities.
- `POST /sensors/observations`: shared validated envelope. SIMULATION is accepted through SimulationAdapter; LIVE_HARDWARE is routed to the fail-closed HardwareAdapter. Direct browser-authored recorded payloads are rejected.
- `POST /sensors/observations/replay` with `{ "event_id": "persisted-recorded-event-id" }`: RecordedAdapter uses server-owned evidence. Existing `/sensors/replay` and raw radar/acoustic scenario inference also populate normalized observations automatically.
- `GET /sensors/observations?zone_id=ZONE_TOILET_BLINDSPOT&source_mode=RECORDED_REPLAY`: same read interface for every mode, with `observation: null` until that mode has data.

Full schemas are exposed in FastAPI `/docs`. The mode selector is independent of API connectivity; choosing LIVE_HARDWARE cannot authorize acquisition or delivery. The original simulation preview and scenario controls remain explicitly synthetic. A new explicit simulated fall+scream submission exercises the normalized interface and the existing fusion engine.

Valid synthetic event metadata maps to existing EventIn/fusion/SOS rules with `is_test=true`. Signals within one normalized observation share a fusion identity; separate observations, replay inputs and modes cannot corroborate each other through this path. Recorded normalization does not emit duplicate events or reinterpret old recordings as synchronized live signals. Invalid or stale metadata is retained for diagnosis but never creates event escalation. Track/point-cloud data alone never generates a fall or people-count claim.

SQLite adds `sensor_observation` records to the existing `records` table. There is no destructive migration or incident reset. Observation IDs are idempotent; changed payloads with an existing ID return 409. Event IDs are deterministic for retry-safe delivery. Observation storage and incident processing use existing transactional helpers; they are separate transactions, so retry the identical request if delivery is interrupted. The new UI polls every three seconds and clears current observation data after API errors.

## Commissioning a physical adapter

Implement a device-specific driver behind HardwareAdapter, using the same Observation envelope. Required deployment work:

1. Identify actual vendor/model, firmware, serial/device identity, transport (serial/USB/TCP/MQTT), authentication and reconnect behavior. Keep acquisition credentials server-side; a staff dashboard token must not authorize live staff dispatch.
2. Verify a real connection and fresh device heartbeat before reporting connected. Expire connection state when heartbeats stop. A client-supplied flag is never verification. Persist device registration and capability declarations independently of observations.
3. Document frame format/checksum, sequence numbers, sample frequency, sensor capture timestamps, clock synchronization, latency and out-of-order/drop policy. Set validity from actual driver checks. Do not treat server receipt time as capture time silently.
4. Survey mounting height/orientation, room boundaries and zone transform. Validate sensor axes, units, velocity semantics, calibration version and precision. If the device supplies only classifications, omit spatial fields. Never reconstruct measured tracks from class labels.
5. Establish anonymous track lifetime/reuse policy, quality/SNR meaning, point-cloud filtering, field of view, occlusion limitations and supported count estimates. Acoustic devices must emit approved non-speech classes only. SOS requires physical input identity, debounce, state transitions, heartbeat and test/live distinction.
6. Supply transport/firmware fixtures and hardware-in-loop tests covering disconnects, stale/future packets, corrupt frames, duplicate/reordered messages, calibration failures, privacy rejection and SOS retries. Verify notification routing separately before any live delivery. The current adapter intentionally cannot reach live dispatch.

This is a hardware integration prototype. No vendor parser, physical acquisition, measured calibration, or device verification has been implemented or claimed.
