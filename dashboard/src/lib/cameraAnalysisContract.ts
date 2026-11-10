// Wire values supported by the deployed FastAPI camera endpoint. "all" means
// automatic event analysis for the operator; it is not a model-picker control.
export const CAMERA_ANALYSIS_MODE = 'all' as const;

const poseVersion = 'yolo11n-pose-temporal-rule-v1';
export function cameraAnalysisVersions(job: any, mode: string = CAMERA_ANALYSIS_MODE, baseline = 'v3'): string[] {
  // Older all-mode responses contain three outputs and no policy/resolved_models.
  // Render actual returned outputs rather than silently dropping a classifier.
  const outputs = job?.result?.model_results;
  if (outputs?.length) return [...new Set<string>([
    ...(job?.resolved_models || []).map((version: string) => version === 'pose' ? poseVersion : version),
    ...outputs.map((output: any) => output.model_version),
    ...(job?.result?.model_errors || []).map((failure: any) => failure.model === 'pose' ? poseVersion : failure.model),
  ])];
  if (job?.resolved_models?.length) return job.resolved_models.map((version: string) => version === 'pose' ? poseVersion : version);
  if (mode === 'all') return [job?.result?.analysis_policy?.fight_model || baseline, poseVersion];
  return [mode === 'pose' ? poseVersion : mode];
}

export function cameraAnalysisLabel(job: any, baseline = 'v3'): string {
  return cameraAnalysisVersions(job, CAMERA_ANALYSIS_MODE, baseline)
    .map(version => version === poseVersion ? 'YOLO11-Pose' : version.toUpperCase()).join(' + ');
}
