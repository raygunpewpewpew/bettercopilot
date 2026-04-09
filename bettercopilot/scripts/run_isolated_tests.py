#!/usr/bin/env python3
"""Simple harness to run test scripts in isolated subprocesses.

- Runs each script in a fresh Python process with PYTHONPATH set to the
  repository root to ensure imports resolve.
- Saves stdout/stderr to a logs/ directory next to the scripts.
- Can run the existing headless feedback test and the consensus runner per task.
"""
import subprocess
import sys
import os
from pathlib import Path
import time

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
LOG_DIR = SCRIPT_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Tests to run (script name relative to this scripts dir)
TESTS = [
    {'name': 'feedback_headless', 'script': 'test_feedback_loop_headless.py', 'args': []},
]

# Consensus tasks to exercise (one fresh process per task)
CONSENSUS_TASKS = [
    'Centralize debug log',
    'Log every function call and prompt',
    'Place single debug field under file tree',
    'Remove Run Task buttons',
    'Set editor background to white',
    'Send empty editor when prompting to write a new script',
]

# Add consensus_runner invocations
for t in CONSENSUS_TASKS:
    TESTS.append({'name': f'consensus_{t[:20]}', 'script': 'consensus_runner.py', 'args': ['--task', t, '--iters', '2']})


def run_test_entry(entry):
    script_path = SCRIPT_DIR / entry['script']
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return 2, f"Script not found: {script_path}"

    env = os.environ.copy()
    # Ensure subprocesses can import the package regardless of layout.
    # Include both the repository root and the inner package directory.
    pkg_dir = REPO_ROOT / 'bettercopilot'
    env_paths = [str(REPO_ROOT), str(pkg_dir)]
    prev = env.get('PYTHONPATH')
    if prev:
        env_paths.insert(0, prev)
    env['PYTHONPATH'] = os.pathsep.join(env_paths)
    # Log the PYTHONPATH used for debugging
    print('PYTHONPATH for child:', env['PYTHONPATH'])

    logfile = LOG_DIR / f"{entry['name']}_{int(time.time())}.log"
    cmd = [sys.executable, str(script_path)] + list(entry.get('args', []))
    print('Running:', ' '.join(cmd))
    try:
        res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        with open(logfile, 'w', encoding='utf-8') as f:
            f.write(res.stdout or '')
        return res.returncode, res.stdout
    except Exception as e:
        with open(logfile, 'w', encoding='utf-8') as f:
            f.write(str(e))
        return 1, str(e)


def main():
    summary = []
    for entry in TESTS:
        code, out = run_test_entry(entry)
        ok = (code == 0)
        summary.append({'name': entry['name'], 'code': code, 'ok': ok})
        print(f"Finished {entry['name']}: exit={code} ok={ok}")

    print('\nSummary:')
    for s in summary:
        print(f" - {s['name']}: exit={s['code']} ok={s['ok']}")

    # exit non-zero if any test failed
    any_fail = any(not s['ok'] for s in summary)
    sys.exit(1 if any_fail else 0)


if __name__ == '__main__':
    main()
