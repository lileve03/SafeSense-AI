# SafeSense Private Toilet Guided Demo

The original Three.js room is now presented through a compact **Guided Demo** by default. Campus navigation, room geometry, walls/partition, fixtures, lighting, Orbit, Zoom and Reset remain preserved. **Advanced Monitoring** retains the previous source selector, raw observation provenance, motion features, connected test controls and actual recorded-inference tools.

## Present the demonstration

1. Open `http://127.0.0.1:3000` → **Digital Twin Map** → the private Toilet zone.
2. Choose **Normal Presence**, **Proximity**, **Repetitive Motion**, **Possible Fall**, or **SOS**.
3. Click **Start guided demo**. The 40-second sequence runs detection, rule assessment, conditional test-incident handling and an explicitly simulated staff response automatically. Speed supports 1×, 2× and 4×.

**Pause** freezes playback and stops subsequent scripted steps. A request already submitted may still finish; it is not rolled back. Hiding the tab pauses playback. **Restart** replays the same exercise/incident IDs rather than duplicating incidents. Use **Source & demonstration details → Prepare new guided exercise** when intentionally creating a separate exercise. Selecting another scenario pauses the old one before preparing the next. Starting/replaying a previously closed exercise does not reopen its incident.

The compact readout shows active anonymous track count, separation only when two valid positions exist, movement state and sensor status. **SIMULATED DEMO** and **Hardware Disconnected** remain visible. Clicking a 3D track shows its synthetic coordinates/speed; clicking a sensor fixture or its accessible status button explains its simulated state. Linked incidents open the original incident details. **Return to campus map** uses the existing campus navigation.

## What each scenario demonstrates

| Scenario | Generated input | Actual backend exercise outcome |
| --- | --- | --- |
| Normal Presence | Anonymous scripted arrival/motion/departure, presence and normal acoustic metadata | LOW, no danger incident, no staff escalation |
| Proximity | Two synthetic tracks, approximately 0.60 m separation in the stationary segment | Backend proximity-duration candidate, no automatic danger incident |
| Repetitive Motion | Scripted back-and-forth trajectory | Waits for actual backend temporal-rule support, then creates an OBSERVE test review incident |
| Possible Fall | Scripted marker-height change and virtual acoustic impact | Existing fall-plus-impact fusion creates one HIGH test incident |
| SOS | Virtual help-request signal | Existing direct SOS policy creates CRITICAL even with event confidence zero; no model dependency |

The guide never labels proximity, pacing or the animation as proof of fighting, bullying, injury or real danger. Fall/impact/SOS inputs are scripted scenario signals, not deductions from actual physical acquisition.

## Exactly what is simulated, computed or genuinely inferred

| Item | Source and meaning |
| --- | --- |
| Track IDs, count, coordinates and trajectories | **SIMULATED**. Anonymous scripted markers; no real people, physical radar returns or identifiable video. Count is the number of active simulated tracks, not measured occupancy. |
| Velocity/movement state and trails | **SIMULATED inputs / deterministic calculations** from those scripted trajectories. They are not physical velocity measurements. |
| Separation distance | **Actually calculated** from valid synthetic xyz coordinates with Euclidean distance. It is explicitly labeled **Simulated separation**; room/sensor positions are illustrative, not surveyed calibration. No value is invented when fewer than two valid tracks are available. |
| Radar presence/fall, acoustic impact and SOS states | **SIMULATED metadata**. No physical radar driver, microphone, acoustic sensor or wall button is connected. |
| Capture timestamps | **Synthetic playback clock**, anchored to a timestamp and advanced by demo time/speed. They are not physical acquisition timestamps or transport-latency evidence. |
| Risk and temporal rule outputs | **Actual backend code executed on synthetic data**. The existing distance/duration/reversal/fusion/SOS rules run; this is not an ML model prediction or accuracy experiment. Rules remain backend-owned. |
| SQLite events and incidents | **Actual test records**, explicitly `is_test=true`, `source_type=SIMULATION`, with stable IDs and existing endpoint deduplication. They are not reports of actual private-area danger. |
| Staff acknowledgement/resolution | **Scripted SIMULATED DEMO actions** through the existing response endpoints, labeled in the staff name and resolution note. They do not assert human acknowledgement, responder arrival or actual danger verification. |
| Telegram status | **Read from actual backend records**. API acceptance is not recipient receipt. In isolated verification, sending was DISABLED. No Telegram delivery/receipt is fabricated. |
| ML inference during Guided Demo | **None**. The guide starts zero model jobs and displays no invented radar/YAMNet scores. |
| Genuine model results | Available separately in **Advanced Monitoring → RECORDED_REPLAY → Actual radar / YAMNet inference**, only after the existing registered-file worker produces a result. Scores, model versions, input hashes and candidate outputs come from the completed job. They are not calibrated danger probabilities. |
| Physical hardware status | **Disconnected**. A future physical adapter must verify identity, heartbeat, capabilities and calibration before it may present actual hardware observations. Backend API availability is labeled separately from hardware connectivity. |

Existing recorded radar/acoustic class labels do not provide calibrated anonymous people tracks. Their positions, distances and movement histories remain unavailable. Current radar and YAMNet research recordings are separate files, not synchronized fall-plus-impact evidence. The positive YAMNet sample is a scream, not an impact; the guided impact is explicitly synthetic.

## Shared observation interface and preserved room

`simulationObservation()` in `trackingPlayback.ts` produces the normalized version-1 sensor envelope: source mode, device/zone/session identity, timestamp/basis, validity, coordinate frame, optional anonymous tracks/velocity, optional acoustic events and SOS state. The room renders this envelope through the same `observationFrame()` adapter used by supported future recorded/live tracks. The synthetic capture clock is converted into a relative playback clock only for animation timing. No separate person/video renderer is introduced.

The same envelopes are validated by the backend simulation-motion preview endpoint. Source mode remains SIMULATION throughout the guide. The existing live adapter still fails closed. See [HARDWARE_SENSOR_INTERFACE.md](HARDWARE_SENSOR_INTERFACE.md) and [PROXIMITY_MOTION_RULES.md](PROXIMITY_MOTION_RULES.md) for future hardware commissioning and data requirements.

Sensor inspection and track selection use the existing Three.js raycasting/navigation. Geometry/material pools and bounded trails are reused, animation retains its 30 FPS ceiling, and paused rendering is on demand. The dense engineering controls are available under Advanced Monitoring, rather than mixed into the presentation.

## Automatic workflow and safeguards

- Detection and risk assessment progress from the generated observations. Normal/proximity do not create a fabricated danger incident.
- Repetitive motion waits for an actual backend repeated-motion candidate before posting the labeled test event.
- Possible fall/impact and SOS use the existing explainable fusion/direct-help rules and `/event`; no parallel incident store is created.
- At approximately 20 simulated seconds, the guide records a **SIMULATED DEMO responder (not a human acknowledgement)** on its own incident. At approximately 32 seconds it records a clearly labeled simulated exercise resolution. At 40 seconds the guide is complete once the backend has confirmed the required state.
- The guide does **not automatically set VERIFIED**. Automatic response first checks exact incident ID, test flag, simulation source/mode and the guided run's analysis ID. Real, non-test or unrelated incident fixtures are rejected.
- Read/write failures pause the exercise or show unavailable status rather than claiming a completed response. Backend state, not a frontend animation, determines the recorded incident status.
- Guided and manually connected test runs use separate session-storage scopes. Restart retains test event IDs. Existing incident data, classifiers and the manual workflow remain intact.

No CCTV, private video, recognizable people, face imagery, microphone capture, speech recording or transcription is added. This is a hardware-integration demonstration, not a verified emergency-response deployment.

Actual browser/backend results: [GUIDED_PRIVATE_DEMO_RESULTS.md](GUIDED_PRIVATE_DEMO_RESULTS.md).
