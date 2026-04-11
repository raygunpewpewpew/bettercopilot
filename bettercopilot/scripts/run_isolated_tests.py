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
import argparse
import time
from pathlib import Path
import xml.etree.ElementTree as ET


def _sanitize_name(s: str) -> str:
    return ''.join(c if (c.isalnum() or c in ('_', '-')) else '_' for c in s)[:120]


def _write_junit_single(name: str, elapsed: float, rc: int, output: str, xml_path: Path, classname: str = 'run_isolated_tests'):
    """Write a minimal JUnit XML file for a single test run."""
    testsuite = ET.Element('testsuite', attrib={
        'name': 'run_isolated_tests',
        'tests': '1',
        'failures': '1' if rc != 0 else '0',
        'errors': '0',
        'time': f"{elapsed:.3f}",
    })
    tc = ET.SubElement(testsuite, 'testcase', attrib={'classname': classname, 'name': name, 'time': f"{elapsed:.3f}"})
    if rc != 0:
        # Use CDATA-like section by placing output as text inside failure element
        fail = ET.SubElement(tc, 'failure', attrib={'message': f'Exit code: {rc}'})
        fail_text = output or ''
        try:
            fail.text = fail_text
        except Exception:
            try:
                fail.text = str(fail_text)
            except Exception:
                pass

    tree = ET.ElementTree(testsuite)
    try:
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(xml_path), encoding='utf-8', xml_declaration=True)
    except Exception:
        # best-effort: ignore write failures
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
LOG_DIR = SCRIPT_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Globals controlled by CLI
JUNIT_DIR = None
PYTEST_K = None

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

# Discover pytest suites to run (repo-level and package-level)
PYTEST_SUITES = []
try:
    root_tests = REPO_ROOT / 'tests'
    if root_tests.exists():
        PYTEST_SUITES.append({'name': 'pytest_root', 'type': 'pytest', 'path': str(root_tests)})
except Exception:
    pass
try:
    pkg_tests = REPO_ROOT / 'bettercopilot' / 'tests'
    if pkg_tests.exists():
        PYTEST_SUITES.append({'name': 'pytest_package', 'type': 'pytest', 'path': str(pkg_tests)})
except Exception:
    pass

# Append pytest runs to TESTS so they are executed in isolated subprocesses
for p in PYTEST_SUITES:
    TESTS.append(p)


def run_test_entry(entry):
    """Run a single test entry in an isolated subprocess and emit logs and JUnit XML.

    Uses module-level `JUNIT_DIR` and `PYTEST_K` if set by `main()`.
    """
    env = os.environ.copy()
    # Ensure subprocesses can import the package regardless of layout.
    pkg_dir = REPO_ROOT / 'bettercopilot'
    env_paths = [str(REPO_ROOT), str(pkg_dir)]
    prev = env.get('PYTHONPATH')
    if prev:
        env_paths.insert(0, prev)
    env['PYTHONPATH'] = os.pathsep.join(env_paths)
    # Log the PYTHONPATH used for debugging
    print('PYTHONPATH for child:', env['PYTHONPATH'])

    timestamp = int(time.time())
    logfile = LOG_DIR / f"{_sanitize_name(entry.get('name','test'))}_{timestamp}.log"

    # Support two entry types: regular python scripts and pytest-suite runs
    if entry.get('type') == 'pytest':
        test_path = entry.get('path') or str(REPO_ROOT / 'tests')
        junit_path = (globals().get('JUNIT_DIR') or LOG_DIR) / f"{_sanitize_name(entry.get('name'))}_{timestamp}.xml"
        kopt = []
        if globals().get('PYTEST_K'):
            kopt = ['-k', globals().get('PYTEST_K')]
        cmd = [sys.executable, '-m', 'pytest', test_path, '-q', '--maxfail=1', f"--junitxml={str(junit_path)}"] + kopt
        print('Running pytest:', ' '.join(cmd))
    else:
        script_path = SCRIPT_DIR / entry['script']
        if not script_path.exists():
            print(f"Script not found: {script_path}")
            return 2, f"Script not found: {script_path}"
        cmd = [sys.executable, str(script_path)] + list(entry.get('args', []))
        print('Running:', ' '.join(cmd))

    try:
        start = time.time()
        res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        duration = time.time() - start
        out = res.stdout or ''
        with open(logfile, 'w', encoding='utf-8') as f:
            f.write(out)

        # Emit per-test JUnit XML for non-pytest scripts (pytest already wrote its own JUnit file)
        if entry.get('type') != 'pytest':
            junit_path = (globals().get('JUNIT_DIR') or LOG_DIR) / f"{_sanitize_name(entry.get('name'))}_{timestamp}.xml"
            _write_junit_single(entry.get('name'), duration, res.returncode, out, junit_path)

        return res.returncode, out
    except Exception as e:
        duration = 0.0
        out = str(e)
        with open(logfile, 'w', encoding='utf-8') as f:
            f.write(out)
        # write junit for failures
        junit_path = (globals().get('JUNIT_DIR') or LOG_DIR) / f"{_sanitize_name(entry.get('name'))}_{timestamp}.xml"
        _write_junit_single(entry.get('name'), duration, 1, out, junit_path)
        return 1, out


def main():
    parser = argparse.ArgumentParser(description='Run isolated tests and produce logs and JUnit XML outputs')
    parser.add_argument('--filter', '-f', help='Run only tests whose name or script contains this substring')
    parser.add_argument('--only', help='Comma-separated list of test names to run exactly')
    parser.add_argument('--pytest-filter', '-k', help='Pass -k expression to pytest runs')
    parser.add_argument('--junit-dir', help='Directory to write per-test JUnit XML files', default=str(LOG_DIR / 'junit'))
    args = parser.parse_args()

    # Configure globals
    global JUNIT_DIR, PYTEST_K
    JUNIT_DIR = Path(args.junit_dir)
    JUNIT_DIR.mkdir(parents=True, exist_ok=True)
    PYTEST_K = args.pytest_filter

    # Filter TESTS if requested
    tests_to_run = list(TESTS)
    if args.only:
        names = [n.strip() for n in args.only.split(',') if n.strip()]
        tests_to_run = [t for t in tests_to_run if t.get('name') in names]
    elif args.filter:
        sub = args.filter.lower()
        tests_to_run = [t for t in tests_to_run if sub in (t.get('name','').lower() or '') or sub in (t.get('script','').lower() or '')]

    summary = []
    for entry in tests_to_run:
        code, out = run_test_entry(entry)
        ok = (code == 0)
        summary.append({'name': entry['name'], 'code': code, 'ok': ok})
        print(f"Finished {entry['name']}: exit={code} ok={ok}")

    print('\nSummary:')
    for s in summary:
        print(f" - {s['name']}: exit={s['code']} ok={s['ok']}")

    # Aggregate any per-test JUnit XML files into a single report for CI
    try:
        agg_files = sorted((JUNIT_DIR or LOG_DIR).glob('*.xml'))
        agg_suite = ET.Element('testsuite', attrib={'name': 'aggregated', 'tests': '0', 'failures': '0', 'errors': '0', 'time': '0'})
        total = 0
        failures = 0
        errors = 0
        total_time = 0.0
        for f in agg_files:
            try:
                tree = ET.parse(str(f))
                root = tree.getroot()
                # root may be <testsuite> or <testsuites>
                if root.tag == 'testsuites':
                    for ts in root.findall('testsuite'):
                        for tc in ts.findall('testcase'):
                            agg_suite.append(tc)
                            total += 1
                            if tc.find('failure') is not None:
                                failures += 1
                            if tc.find('error') is not None:
                                errors += 1
                            try:
                                total_time += float(tc.get('time') or 0)
                            except Exception:
                                pass
                elif root.tag == 'testsuite':
                    for tc in root.findall('testcase'):
                        agg_suite.append(tc)
                        total += 1
                        if tc.find('failure') is not None:
                            failures += 1
                        if tc.find('error') is not None:
                            errors += 1
                        try:
                            total_time += float(tc.get('time') or 0)
                        except Exception:
                            pass
            except Exception:
                pass

        agg_suite.set('tests', str(total))
        agg_suite.set('failures', str(failures))
        agg_suite.set('errors', str(errors))
        agg_suite.set('time', f"{total_time:.3f}")
        agg_tree = ET.ElementTree(agg_suite)
        try:
            out_path = (JUNIT_DIR or LOG_DIR) / 'junit_report.xml'
            agg_tree.write(str(out_path), encoding='utf-8', xml_declaration=True)
            print('Wrote aggregated JUnit report to', str(out_path))
        except Exception:
            pass
    except Exception:
        pass

    # exit non-zero if any test failed
    any_fail = any(not s['ok'] for s in summary)
    sys.exit(1 if any_fail else 0)


if __name__ == '__main__':
    main()
