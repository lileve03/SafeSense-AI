"""Read-only upload audit. Prints paths/line numbers, never matched secret values.

Exit 1 means an upload candidate needs review. Does not stage, commit or push.
Heuristics cannot certify that arbitrary documents contain no private information.
"""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'Telegram bot token': r'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b',
    'private key': r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
    'GitHub token': r'\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    'Google API key': r'\bAIza[A-Za-z0-9_-]{30,}',
    'AWS access key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'Telegram recipient ID': r'(?i)["\x27]?(?:TELEGRAM_\w*(?:CHAT_ID|USER_IDS)|chat_id)["\x27]?\s*[:=]\s*["\x27]?[-\d][\d, -]{4,}',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    candidates = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')) - {''}
    findings, large = [], []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != '.git']
        for name in files:
            path = Path(base) / name
            rel = path.relative_to(ROOT).as_posix()
            size = path.stat().st_size
            if size >= 50 * 1024**2:
                large.append({'path': rel, 'MiB': round(size / 1024**2, 2),
                              'blocked_by_normal_git_limit': size > 100 * 1024**2,
                              'upload_candidate': rel in candidates})
            # Scan all candidate text, and local env files; dependencies are not candidates.
            if (rel in candidates or name.startswith('.env')) and size < 10 * 1024**2:
                raw = path.read_bytes()
                if b'\0' in raw:
                    continue
                for number, line in enumerate(raw.decode('utf-8', errors='replace').splitlines(), 1):
                    for kind, pattern in PATTERNS.items():
                        if re.search(pattern, line):
                            findings.append({'path': rel, 'line': number, 'kind': kind,
                                             'upload_candidate': rel in candidates})
    report = {'candidate_count': len(candidates), 'credential_findings_values_redacted': findings,
              'large_files': large}
    print(json.dumps(report, indent=2))
    return int(any(f['upload_candidate'] for f in findings + large))


if __name__ == '__main__':
    raise SystemExit(main())
