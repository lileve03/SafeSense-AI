# Task 4: Incident Management / Audit Details evidence

## Result

Audit Details retains the existing modal, header, metadata bar and incident action controls. Only its shared evidence section changes. The same improvement is available in report evidence views.

The section displays the selected incident ID, incident timestamp, zone and processing mode. Each selected saved clip shows its captured camera ID (or Not captured), model version, actual prediction, score/threshold when available, source type, evidence duration and observation timestamp. Videos autoplay muted, retain native pause/seek controls, have Replay evidence and an authenticated attachment download. Multiple clips use an explicit evidence selector; switching clips or incidents unmounts the previous player and clears loading/error state. Polling the report does not restart playback.

Pose evidence defaults to the genuine retained annotation if available, with an original/annotated toggle. Person boxes, confidence labels, skeletons and keypoints are burned into the actual matching YOLO frames. V2/V3 evidence remains whole-clip classification: no fighter boxes, exact fight times or tracking IDs are fabricated. Pose-rule times are explicitly experimental; absent scores remain N/A rather than being replaced by a confidence default.

For PRIVATE or unknown zone types, the UI renders only selected observation metadata (radar, acoustic and SOS source, event type, model/score when supplied, timestamp, mode and reason). It creates no video, image, audio or download elements. The new media API independently refuses private/unknown zones, including requests using a valid public evidence ID.

No-video incidents show a useful message and their saved observations. Expired/deleted media returns 410 and displays an unavailable message. The UI never substitutes a dataset recording, the last camera video, or another incident's media. Missing camera/provenance fields on older incidents remain explicit. Notification configuration lookup failures do not suppress otherwise available incident evidence.

## Saved media and annotation lifecycle

New YOLO candidate evidence captures both the existing original clip and a retained H.264 annotated clip covering the same source interval. These are stored with an analysis-linked JSON sidecar in runtime/evidence, independent of the temporary ten-item annotated preview library. Retained annotations therefore survive inference restart and temporary preview expiry. Original dataset files and trained models are unchanged.

For older pose clips, annotation recovery is allowed only when an existing persisted output matches the exact analysis ID, model and zone, its original-input SHA256 matches the observation provenance, zero frame skipping is recorded, and the matching actual annotated artifact still exists. The saved source interval is cut from that artifact, and its retention age follows the original evidence; recovery does not extend retention. No inference is rerun when opening Audit Details. If this provenance or artifact is unavailable, the original retained clip is shown with an explicit no-annotation note. The active historical samples currently have no recoverable annotations; those clips correctly remain raw.

Evidence binding checks use incident membership, canonical UUID, saved sidecar ID, zone, analysis ID, model, camera, score and interval identity. Known observation metadata must agree. Older observations missing optional provenance fields remain compatible with their original saved sidecars; no incident records are rewritten.

New authenticated AI-service endpoints:

- GET /monitoring/incidents/{incident_id}/evidence/{evidence_id}/metadata
- GET /monitoring/incidents/{incident_id}/evidence/{evidence_id}?variant=original|annotated
- The same media route with download=true returns a correctly named attachment. Media supports byte-range seeking.

Existing unbound evidence/job/upload APIs and lifecycle routes remain available. Deleting a captured clip also deletes its retained annotated derivative. A new optional server-only SAFESENSE_EVIDENCE_DIR lets tests isolate their captured files; its default remains runtime/evidence.

## Verified outcomes

- Focused real API/browser suite: **10/10 PASS**. Cloned existing SQLite incident records and copied actual saved Fight/Fall clips into a separate evidence directory. Ran the existing V3 and YOLO models on actual repository sources; no media or inference responses were mocked. Verified correct historical evidence, newly retained original/annotated clips, actual download, exact legacy recovery, unchanged retention age, tampered-analysis rejection (409), wrong-incident rejection (404), private denial (403), unauthorized denial (401), byte-range playback, inference restart, muted browser autoplay, pause/replay/seek, annotation toggle, deletion/410, radar/acoustic/SOS metadata, no-evidence state, and acknowledgement/configured assignment/resolution/Digital Twin synchronization.
- Existing real monitoring regression: **21/21 PASS**, including original upload/browser workflows, SQLite restart, original private 3D monitoring, reports and all nine dashboard pages.
- Existing workflow, notification safety and Overview identity unit tests: **35/35 PASS**.
- Final TypeScript checking and production build: PASS. Existing Vite configuration and bundle-size warnings remain.
- Active app: all **17 saved media references** passed identity/availability checks. Actual saved V3 and pose clips autoplayed through Audit Details using their selected evidence IDs. Private Audit Details had zero media elements; 390px layout had no horizontal overflow. All **19 existing incident records remained unchanged**, with no new active-database incidents or external notification sends.

Artifacts: runtime/audit-evidence-task4/results.json, activation.json, existing-media-identity.json, summary.json, and Fight/Fall/missing-evidence/active-app screenshots. Example annotated clip: a genuine possible-fall pose-rule signal at source time 2.1 seconds, with no trained fall probability. The actual V3 test clip score was 0.9848954677581787 with its existing threshold 0.7.

A preliminary active-app smoke test checked for the multi-clip selector before the report finished loading and consequently sampled its default first clip. The test now waits for the selected incident report before choosing the evidence ID; actual selector changes and playback passed. This was a test timing correction, not replacement of incident data.

## Changed files

- backend/incident_media.py (new): incident binding, manifest validation and exact legacy annotation recovery.
- monitoring_ai.py: retained pose derivative capture, incident-bound endpoints/download, derivative deletion and optional isolated evidence directory.
- fight_api.py: passes the actual completed pose annotation into evidence capture; Fight V2/V3 behavior unchanged.
- dashboard/src/components/incidents/IncidentEvidence.tsx: scoped incident report, metadata-only privacy, clip selector, saved detection metadata and independent notification status loading.
- dashboard/src/components/incidents/IncidentMedia.tsx (new): authorized saved media player, metadata, annotation toggle, autoplay, replay/download and unavailable handling.
- tests/test_audit_evidence.py (new): isolated saved-media/API/browser/incident lifecycle verification.
- tests/test_audit_activation.py (new): read-only active-app historical evidence verification.
- This report and generated dashboard/dist/runtime artifacts.

IncidentReviewPage, AlertDetailModal, acknowledgement/assignment/resolution handlers, SQLite schema, Digital Twin logic and private 3D view were not edited. No retraining or dataset modifications occurred.

## Limits

Historical annotations cannot be reconstructed when their exact temporary artifact/provenance is no longer retained; raw saved clips and actual detection metadata remain available. Repository incident evidence currently consists of MP4 files and JSON sidecars, not registered image attachments; no image fixture or private imaging was introduced. Playback was tested in Chromium. Existing browser-compatible encoded frames preserve annotation synchronization; no claim of continuous live inference or new event localization is made.
