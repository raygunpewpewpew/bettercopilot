#!/usr/bin/env python3
"""Scan PATH for Python interpreters and test each for PySide6.

Usage: `python scripts/find_pyside.py` or run with any Python; the script
will invoke each discovered interpreter to check for PySide6.
"""
import subprocess
import sys
import os


def find_pythons():
    paths = []
    # On Windows prefer where.exe
    if os.name == 'nt':
        try:
            out = subprocess.run(['where.exe', 'python'], capture_output=True, text=True)
            if out.returncode == 0 and out.stdout:
                for l in out.stdout.splitlines():
                    p = l.strip()
                    if p:
                        paths.append(p)
        except Exception:
            pass
    # Try py launcher list if available
    try:
        out = subprocess.run(['py', '-0p'], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout:
            for l in out.stdout.splitlines():
                p = l.strip()
                if p and p not in paths:
                    paths.append(p)
    except Exception:
        pass

    # include current interpreter
    try:
        cur = sys.executable
        if cur and cur not in paths:
            paths.insert(0, cur)
    except Exception:
        pass

    # unique-preserve-order
    seen = set()
    out = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def check_pyside(python):
    try:
        # check for spec
        cmd = [python, '-c', "import importlib.util,sys; spec = importlib.util.find_spec('PySide6'); print('SPEC_OK' if spec else 'NO_SPEC')"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if out.returncode != 0:
            # treat as not installed
            return False, None, None
        ok = 'SPEC_OK' in out.stdout
        if not ok:
            return False, None, None
        # get version and path
        cmd2 = [python, '-c', "import PySide6,sys; print(getattr(PySide6,'__version__','unknown')); print(getattr(PySide6,'__file__','unknown'))"]
        out2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=8)
        if out2.returncode == 0 and out2.stdout:
            lines = [l.strip() for l in out2.stdout.splitlines() if l.strip()]
            ver = lines[0] if len(lines) > 0 else None
            pth = lines[1] if len(lines) > 1 else None
            return True, ver, pth
        return True, None, None
    except Exception:
        return False, None, None


def main():
    pythons = find_pythons()
    if not pythons:
        print('No python interpreters found on PATH')
        return
    print('Detected python interpreters:')
    for p in pythons:
        print(' -', p)
    print()

    for p in pythons:
        exists = os.path.exists(p)
        if not exists:
            print(f'{p}: (not found)')
            continue
        ok, ver, pth = check_pyside(p)
        if ok:
            print(f"{p}: PySide6 installed (version={ver}) path={pth}")
        else:
            print(f"{p}: PySide6 not installed")


if __name__ == '__main__':
    main()
