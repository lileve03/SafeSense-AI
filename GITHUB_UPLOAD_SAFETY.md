# GitHub upload safety review

Prepared 10 November 2026. No files were deleted, no Git history was reset, and no commit, push or remote change was performed.

## Git state

The repository is initialized on `master` with no commits, no tracked/staged files and no configured remotes. Consequently there is no committed history containing secrets or private recordings to remove. The working tree is an existing, untracked application; preparation preserves all application source, model settings, React dashboard, FastAPI services and Three.js functionality. Ignore rules affect Git upload only, not local runtime access.

## Credentials and private data

- `.env` contains a Telegram bot token (line 3) and recipient ID (line 4). Values are deliberately omitted. Keep the file ignored. Rotate the bot token through BotFather if it has ever been shared or published; this audit found no committed exposure.
- `staff-routes.json`, `dashboard/.env.local`, camera registry files, local environment files and agent configuration are excluded. The root `.env.example` contains empty credential fields, Telegram disabled, and staff dispatch off. `staff-routes.example.json` has inactive placeholder routes.
- `datasets/`, `runtime/`, `reports/`, `runs/`, `evaluation/outputs/` and `backend/data/` are excluded. These can contain identifiable recordings, acoustic/radar inputs, incident/evidence records, notification history, session identifiers, predictions, screenshots or generated exports. Public research data still needs license/authorization review before redistribution.
- Recorded media, model weights, serialized classifiers, databases and compressed archives are ignored globally. Model source/configuration stays available. The bundled dashboard PNG was visually reviewed as a product illustration, not a private recording.
- The automated scan found nine recipient-ID matches in test fixtures. Context uses fake Telegram tokens or mocked environment tests; these are review findings, not evidence of live credentials. They are retained to preserve tests. The script deliberately continues to flag them so future changes receive review.

The scanner checks Telegram bot tokens/recipient assignments, private keys, GitHub/Google/AWS key patterns, and file sizes. It never prints matched values. This heuristic scan cannot prove that arbitrary prose, source fixtures or images contain no personal information. Review the exact staged diff before publication. Historical task reports describe local testing; do not infer current production readiness from them.

## Size audit

GitHub warns for files above 50 MiB and blocks ordinary Git files above 100 MiB: [official limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

The full filesystem scan includes virtual environments and dependencies. Every file at least 50 MiB is excluded from upload. Largest research archives include the 3072 MiB FSD50K split volume, 2896.95 MiB FSD50K archive, 1049.56 MiB violence dataset archive and 444.10 MiB dataset archive. Several UR Fall archives also exceed 100 MiB. Runtime SQLite snapshots exceed 50 MiB. None belongs in this source upload. Git LFS does not make private recordings safe to publish.

| Local file | MiB | Exceeds 100 MiB | Upload candidate |
| --- | ---: | --- | --- |
| `.venv/Lib/site-packages/playwright/driver/node.exe` | 89.56 | False | False |
| `.venv-acoustic/Lib/site-packages/clang/native/libclang.dll` | 80.1 | False | False |
| `.venv-acoustic/Lib/site-packages/tensorflow/python/_pywrap_tensorflow_common.dll` | 1007.69 | True | False |
| `.venv-vision/Lib/site-packages/cv2/cv2.pyd` | 71.59 | False | False |
| `.venv-vision/Lib/site-packages/playwright/driver/node.exe` | 89.56 | False | False |
| `.venv-vision/Lib/site-packages/torch/lib/torch_cpu.dll` | 291.72 | True | False |
| `.venv-vision/Lib/site-packages/_polars_runtime_32/_polars_runtime.pyd` | 164.01 | True | False |
| `datasets/A-Dataset-for-Automatic-Violence-Detection-in-Videos-master.zip` | 1049.56 | True | False |
| `datasets/archive (6).zip` | 444.1 | True | False |
| `datasets/open_hidden/ur_fall/adl-01-cam0-rgb.zip` | 65.88 | False | False |
| `datasets/open_hidden/ur_fall/adl-02-cam0-rgb.zip` | 79.62 | False | False |
| `datasets/open_hidden/ur_fall/adl-03-cam0-rgb.zip` | 80.49 | False | False |
| `datasets/open_hidden/ur_fall/adl-04-cam0-rgb.zip` | 67.41 | False | False |
| `datasets/open_hidden/ur_fall/adl-05-cam0-rgb.zip` | 81.37 | False | False |
| `datasets/open_hidden/ur_fall/adl-06-cam0-rgb.zip` | 103.28 | True | False |
| `datasets/open_hidden/ur_fall/adl-07-cam0-rgb.zip` | 80.53 | False | False |
| `datasets/open_hidden/ur_fall/adl-08-cam0-rgb.zip` | 79.96 | False | False |
| `datasets/open_hidden/ur_fall/adl-09-cam0-rgb.zip` | 66.35 | False | False |
| `datasets/open_hidden/ur_fall/adl-10-cam0-rgb.zip` | 133.79 | True | False |
| `datasets/open_hidden/ur_fall/adl-11-cam0-rgb.zip` | 132.78 | True | False |
| `datasets/open_hidden/ur_fall/adl-12-cam0-rgb.zip` | 104.39 | True | False |
| `datasets/open_hidden/ur_fall/adl-13-cam0-rgb.zip` | 109.59 | True | False |
| `datasets/open_hidden/ur_fall/adl-14-cam0-rgb.zip` | 97.39 | False | False |
| `datasets/open_hidden/ur_fall/adl-15-cam0-rgb.zip` | 115.08 | True | False |
| `datasets/open_hidden/ur_fall/adl-16-cam0-rgb.zip` | 99.04 | False | False |
| `datasets/open_hidden/ur_fall/adl-17-cam0-rgb.zip` | 95.29 | False | False |
| `datasets/open_hidden/ur_fall/adl-18-cam0-rgb.zip` | 110.44 | True | False |
| `datasets/open_hidden/ur_fall/adl-19-cam0-rgb.zip` | 104.62 | True | False |
| `datasets/open_hidden/ur_fall/adl-20-cam0-rgb.zip` | 112.86 | True | False |
| `datasets/open_hidden/ur_fall/adl-21-cam0-rgb.zip` | 116.57 | True | False |
| `datasets/open_hidden/ur_fall/adl-22-cam0-rgb.zip` | 100.23 | True | False |
| `datasets/open_hidden/ur_fall/adl-30-cam0-rgb.zip` | 115.11 | True | False |
| `datasets/open_hidden/ur_fall/adl-31-cam0-rgb.zip` | 81.7 | False | False |
| `datasets/open_hidden/ur_fall/adl-32-cam0-rgb.zip` | 60.6 | False | False |
| `datasets/open_hidden/ur_fall/adl-33-cam0-rgb.zip` | 60.08 | False | False |
| `datasets/open_hidden/ur_fall/adl-34-cam0-rgb.zip` | 56.82 | False | False |
| `datasets/open_hidden/ur_fall/adl-35-cam0-rgb.zip` | 82.14 | False | False |
| `datasets/open_hidden/ur_fall/adl-36-cam0-rgb.zip` | 100.45 | True | False |
| `datasets/open_hidden/ur_fall/adl-37-cam0-rgb.zip` | 103.32 | True | False |
| `datasets/open_hidden/ur_fall/adl-38-cam0-rgb.zip` | 98.39 | False | False |
| `datasets/open_hidden/ur_fall/adl-39-cam0-rgb.zip` | 77.65 | False | False |
| `datasets/open_hidden/ur_fall/adl-40-cam0-rgb.zip` | 95.07 | False | False |
| `datasets/open_hidden/ur_fall/fall-01-cam0-rgb.zip` | 55.05 | False | False |
| `datasets/open_hidden/ur_fall/fall-03-cam0-rgb.zip` | 78.11 | False | False |
| `datasets/open_hidden/ur_fall/fall-05-cam0-rgb.zip` | 51.84 | False | False |
| `datasets/open_hidden/ur_fall/fall-07-cam0-rgb.zip` | 54.39 | False | False |
| `datasets/open_hidden/ur_fall/fall-09-cam0-rgb.zip` | 63.89 | False | False |
| `datasets/private/audio/fsd50k/FSD50K.eval_audio.z01` | 3072.0 | True | False |
| `datasets/private/audio/fsd50k/FSD50K.eval_audio.zip` | 2896.95 | True | False |
| `runtime/safesense.sqlite3` | 61.59 | False | False |
| `runtime/analytics-reports-final/snapshot-1793290770378375700.sqlite3` | 61.11 | False | False |
| `runtime/incident-investigation/test-1793345751276010200.sqlite3` | 61.25 | False | False |
| `runtime/incident-investigation/test-1793345799083002800.sqlite3` | 61.25 | False | False |
| `runtime/incident-investigation/test-1793345818284498200.sqlite3` | 61.25 | False | False |

## Files eligible for source commit

The final `git status --short` lists only untracked candidates, with nothing staged. Eligible categories after review: root documentation/examples/manifests; `backend/` source and requirements; `dashboard/` source, public illustration, lockfiles and build configuration; `ai_models/` Python/configuration; `scripts/`; `tests/`; `threejs_test/`; retained phase/integration source trees; root inference entrypoints. No weights, datasets, runtime records or generated evaluation outputs are needed in the source commit. The exact candidate manifest is `GITHUB_COMMIT_CANDIDATES.txt`.

## Commit and push (run manually)

Create an EMPTY repository on GitHub first, without an initial README, license or .gitignore. Replace `YOUR_USERNAME` and `YOUR_REPOSITORY` below with your actual destination. Use an HTTPS URL without embedded credentials; authenticate through Git Credential Manager or GitHub's supported sign-in flow. These instructions preserve the existing `master` branch. If you initialize a nonempty remote, stop and reconcile its history without force-pushing.

```powershell
Set-Location 'C:\Users\ewei2\Desktop\Safesense'
git status --short
.\.venv\Scripts\python.exe scripts\audit_github_upload.py
# The scanner intentionally exits 1 for the documented dummy recipient test fixtures.
# Stop for ANY new credential finding or any large upload candidate.
git add --dry-run .
git add .
git diff --cached --check
git diff --cached --stat
git diff --cached
# Inspect locally: the full diff can contain newly added sensitive material.
# Proceed only when the staged content has been reviewed.
git commit -m "Prepare SafeSense AI MVP source and documentation"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin master
```

No `git init`, reset, history rewrite, forced add, remote replacement or force push is required. If you spot something after staging, `git rm --cached -- 'relative/path'` removes it from the index while retaining the local file; add an appropriate ignore rule before committing. If Git asks for author identity, configure your intended name and GitHub email locally before committing. Do not publish until unexpected scan findings have been resolved.

To repeat the redacted audit and save it locally:

```powershell
.\.venv\Scripts\python.exe scripts\audit_github_upload.py > runtime\github-upload-audit.json
```

`runtime/` stays ignored. AI models and authorized data setup: [MODEL_AND_DATA_SETUP.md](MODEL_AND_DATA_SETUP.md).
