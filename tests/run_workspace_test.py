"""Run a test using temporary directories inside this checkout.

Usage: python -X utf8 -I tests/run_workspace_test.py tests/quick_test.py
Python 3.13's Windows mkdtemp(0700) may deny writes from restricted tokens.
New test directories inherit the workspace ACL; existing ACLs are unchanged.
"""
import runpy
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'local' / 'test-tmp'


def workspace_temp(suffix=None, prefix=None, dir=None):
    BASE.mkdir(parents=True, exist_ok=True)
    path = BASE / ((prefix or 'tmp') + uuid.uuid4().hex + (suffix or ''))
    path.mkdir(mode=0o777)
    return str(path)


if __name__ == '__main__':
    target = (ROOT / sys.argv[1]).resolve()
    if not target.is_relative_to(ROOT / 'tests'):
        raise ValueError('Only workspace tests are supported')
    tempfile.mkdtemp = workspace_temp
    tempfile.tempdir = str(BASE)
    sys.argv = sys.argv[1:]
    runpy.run_path(str(target), run_name='__main__')
