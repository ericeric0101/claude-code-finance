#!/usr/bin/env python3
"""Check installed skill completeness, upstream identity and actual CLI examples."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    manifest = json.loads((ROOT/'docs/upstream-versions.json').read_text())
    for skill, metadata in manifest.items():
        folder = ROOT/'.agents/skills'/skill
        for relative, expected in metadata['sha256'].items():
            path = folder/relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f'{skill}/{relative}: missing or differs from recorded upstream')
        print(f'{skill}: {len(metadata["sha256"])} upstream files checked')
    for name in ['ratios','score','valuation','verify_data','lint_report']:
        path = ROOT/'.agents/skills/stock-analysis/scripts'/f'{name}.py'
        for args in [['--help'], *([['--example']] if name in ['ratios','score','valuation'] else [])]:
            result = subprocess.run([sys.executable,str(path),*args],capture_output=True,text=True)
            if result.returncode: errors.append(f'{name} {args}: {result.stderr.strip()}')
        print(f'{name}: CLI smoke checks passed' if not any(e.startswith(name+' ') for e in errors) else f'{name}: FAIL')
    env_path = ROOT/'.env'
    if env_path.exists():
        values = dict(line.split('=',1) for line in env_path.read_text().splitlines() if '=' in line and not line.startswith('#'))
        print('SEC User-Agent: configured' if values.get('SEC_EDGAR_USER_AGENT','').strip('" ') else 'SEC User-Agent: missing')
        print('Alpha Vantage: configured (not connection-tested)' if values.get('ALPHA_VANTAGE_API_KEY','').strip('" ') else 'Alpha Vantage: not configured')
    ignore = subprocess.run(['git','check-ignore','.env'],cwd=ROOT,capture_output=True,text=True)
    tracked = subprocess.run(['git','ls-files','.env'],cwd=ROOT,capture_output=True,text=True)
    if ignore.returncode or tracked.stdout.strip(): errors.append('.env is not safely excluded from Git')
    print('.env: excluded from Git' if not any('.env' in e for e in errors) else '.env: FAIL')
    for skill in ['finance-skill', 'stock-analysis', 'my-equity-research']:
        folder = ROOT/'.agents/skills'/skill
        if not (folder/'SKILL.md').is_file():
            errors.append(f'{skill}: missing Codex skill entry')
        elif folder.resolve() != (ROOT/'.claude/skills'/skill).resolve():
            errors.append(f'{skill}: Codex entry does not resolve to versioned package')
        else:
            print(f'{skill}: Codex entry resolves to complete package')
    if not (ROOT/'AGENTS.md').is_file(): errors.append('AGENTS.md: missing')
    print('Host: Codex desktop; no Claude login required')
    for error in errors: print('ERROR:',error)
    return 1 if errors else 0


if __name__=='__main__': raise SystemExit(main())
