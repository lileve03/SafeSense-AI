import test from 'node:test';
import assert from 'node:assert/strict';
import { CAMERA_ANALYSIS_MODE, cameraAnalysisLabel, cameraAnalysisVersions } from '../dashboard/src/lib/cameraAnalysisContract.ts';

test('every camera uses the supported all wire value', () => {
  assert.equal(CAMERA_ANALYSIS_MODE, 'all');
});
test('legacy all response with no policy fields retains every actual model', () => {
  const job = { result: { model_results: [{model_version:'v2'}, {model_version:'v3'}, {model_version:'yolo11n-pose-temporal-rule-v1'}] } };
  assert.deepEqual(cameraAnalysisVersions(job), ['v2','v3','yolo11n-pose-temporal-rule-v1']);
  assert.equal(cameraAnalysisLabel(job), 'V2 + V3 + YOLO11-Pose');
});
test('configured all response displays its two resolved model versions', () => {
  const job = { resolved_models: ['v2','pose'], result: { analysis_policy: {fight_model:'v2'}, model_results: [{model_version:'v2'}, {model_version:'yolo11n-pose-temporal-rule-v1'}] } };
  assert.equal(cameraAnalysisLabel(job), 'V2 + YOLO11-Pose');
});
test('queued results show configured detectors without blank or undefined versions', () => {
  assert.equal(cameraAnalysisLabel({resolved_models:['v3','pose']}), 'V3 + YOLO11-Pose');
  assert.deepEqual(cameraAnalysisVersions(null, 'all', 'v2'), ['v2','yolo11n-pose-temporal-rule-v1']);
});
test('legacy single-pose mode maps to its actual version', () => {
  assert.deepEqual(cameraAnalysisVersions(null, 'pose'), ['yolo11n-pose-temporal-rule-v1']);
});
test('partial success still shows failed detectors instead of silently omitting them', () => {
  const job = { result: { model_results: [{model_version:'v2'}], model_errors: [{model:'v3'}, {model:'pose'}] } };
  assert.deepEqual(cameraAnalysisVersions(job), ['v2','v3','yolo11n-pose-temporal-rule-v1']);
});
