# Five connected private-area test scenarios

Open `http://127.0.0.1:3000`, then **Digital Twin Map → Private Area 3D View → Source mode: SIMULATION**. The original Three.js Toilet, room/partition design, fixtures, lighting, Orbit/Zoom/Reset, anonymous markers and dashboard theme remain preserved.

In **Five connected private-area demos · SIMULATED TEST workflow**, choose a demo and click **Run connected test demo**. Playback is 40 simulated seconds; the existing speed, pause and timeline controls remain available. Basic tracking playback alone does not emit events. Connected playback is explicitly armed by this separate action.

| Labeled demo | Synthetic playback / signals | Backend outcome |
| --- | --- | --- |
| Normal Presence | One anonymous simulated track; radar presence and normal acoustic metadata | LOW; no danger incident |
| Two-Person Proximity | Two simulated tracks; coordinate-based distances and backend duration features | Proximity review candidate only; presence metadata, no automatic danger incident |
| Repetitive Abnormal Motion | Simulated back-and-forth trajectory; waits for the backend repeated-motion rule | `rapid_motion` test event → OBSERVE / pending human review |
| Possible Fall + Acoustic Impact | Anonymous marker lowers; schematic radar fall and impact indicators activate; two explicitly simulated modalities | Existing independent-modality fall + impact rule → HIGH / human review required |
| SOS Emergency | Schematic SOS fixture activates; explicit direct test help request | CRITICAL, independent of model confidence; no emergency-services dispatch |

All generated tracks, distances, sensor signals and rule input confidence are SIMULATED. Synthetic model scores are **not applicable**, not invented numerical ML results. SOS is deliberately submitted with confidence zero and no model score to demonstrate the existing confidence-independent help-request policy. No motion candidate automatically establishes fighting, bullying or verified physical danger.

## Source integrity and actual recorded inference

Select **RECORDED_REPLAY** to use **Actual radar / YAMNet inference**. The UI uses the existing registered-input catalog and `/testing/runs` worker pipeline. Available inputs include raw radar fall/daily activity recordings and non-speech YAMNet scream/background research samples. Results show actual model version, raw model score, input SHA-256, candidate flag, processing origin and persisted event/incident link. The selected file's completed result is cleared when selecting another input; old results are not relabeled as a new recording.

The available positive YAMNet sample is a **scream**, not an impact. Current radar and acoustic recordings are unrelated historical files. They must not be presented as synchronized fall-plus-impact evidence or fused into a synthetic HIGH event. They retain separate analysis IDs and RECORDED SENSOR REPLAY provenance. Classification-only recordings do not supply calibrated anonymous tracks: their room positions, people counts, distances and movement histories remain unavailable. No forced candidate score or fallback inference is substituted if a file/model/environment fails.

LIVE_HARDWARE remains **Hardware Disconnected**. No private CCTV, person/face video, microphone capture, speech recording/transcription, or raw audio export is introduced. Only registered offline research files are processed by their existing workers.

## Existing endpoints, fusion and synchronization

Connected demos prepare a track-only normalized `/sensors/observations` snapshot. The snapshot has no SOS/fall/acoustic trigger, preventing a second event path. Actual test signals are then posted only to the existing authenticated **`POST /event`** endpoint, with explicit `simulation` / `SIMULATION` provenance, `is_test=true`, no media and no model score. No new incident-creation endpoint or parallel incident store is introduced.

Each run has a stable `private-demo:<UUID>` analysis ID and one deterministic event ID per signal type. The browser persists the prepared payload and IDs in session storage before submission. Double clicks, request retries, ordinary playback restarts, navigation/reload in the same tab, and replaying the same test retain those IDs. **Prepare explicit new test run** is the deliberate action that allocates a new run/incident scope. Replaying a closed SOS test is labeled **Replay same test SOS request**; use an explicit new test run for another help-request exercise. Clearing session storage starts a new tab/run scope; it does not delete existing backend incidents.

The backend's existing event deduplication remains authoritative. For this narrowly scoped simulated private-demo namespace, active same-run evidence can aggregate after cooldown expiry/restart without duplicating the incident. The existing fusion time window and confidence rules remain unchanged: delayed or unrelated signals are not newly promoted to HIGH. Closed runs reject previously unseen signal IDs instead of reopening/duplicating an incident; known IDs still return their original result. Retained incident evidence is preserved when a late signal is attached.

The shared app context switches to canonical backend events for connected runs while the visual source remains explicitly SIMULATION. Map risk, Alerts, Private Toilet indicators and Incident Review use the same persisted incident IDs and state. Active risk clears after resolution when no other active zone incident remains. Existing incident records, radar fall-classification/evaluation artifacts and previous simulation components are retained.

## Response and Telegram truthfulness

The connected card reads the actual incident report from `/incidents/{id}/report`. It offers the existing `/ack` and `/review` response actions. Human test verification and resolution are explicit operator actions; a simulation does not auto-verify danger. Resolution requires an acknowledgement and a supplied review note. Closed incidents retain the canonical history and cannot be reopened through these controls.

Telegram status is read from actual backend notification records. `SENT`/`API_ACCEPTED` is displayed as **Telegram API accepted — receipt unconfirmed**; receipt is shown only when the backend has an authorized `RECEIPT_CONFIRMED` record. Disabled, failed, unknown, pending and policy-suppressed states are not called delivered. Refresh failures are displayed rather than inventing a delivery result. Test/replay incidents remain governed by the existing authorized TEST recipient policy; no route/recipient setting is changed here.

Verification in this task used isolated databases and **disabled external Telegram sending**. Actual DISABLED status was observed; no live recipient delivery or receipt was tested or claimed. Existing transport-unit regressions use mocks and do not constitute external delivery evidence.

## Verification

See [CONNECTED_PRIVATE_SCENARIO_RESULTS.md](CONNECTED_PRIVATE_SCENARIO_RESULTS.md) for actual PASS/FAIL/NOT_RUN results. The browser suite completes all five playbacks, confirms no incident for normal/proximity, checks OBSERVE/HIGH/CRITICAL, replay deduplication, Map/Alerts/Review synchronization, response transitions and risk clearance, and runs actual registered radar and YAMNet inference. Separate tracking tests exercise fall height/impact/SOS fixture animation and source-mode privacy boundaries.
