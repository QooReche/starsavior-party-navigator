# -*- coding: utf-8 -*-
"""시험 전부를 한 번에: Python tests/*_test.py + golden_check + JS tests/*_test.js (+ 선택: e2e).
실행 전 엔진·화면을 고쳤으면 시뮬 파일 목록·index.html 을 다시 만든다(--rebuild).

  python -X utf8 -I tools/run_tests.py              # 전체(e2e 제외)
  python -X utf8 -I tools/run_tests.py --rebuild    # build_simpack + build_party_html 먼저
  python -X utf8 -I tools/run_tests.py --e2e <venv 의 python>   # 브라우저 시험까지
  python -X utf8 -I tools/run_tests.py enforce wave  # 이름에 낱말이 들어간 시험만

끝에 «통과 N / 실패 M» 과 실패 목록·마지막 출력 몇 줄. 실패가 있으면 종료 코드 1.
web·quick·shim_compat 시험은 tests/run_workspace_test.py 를 거친다(Windows 임시 폴더 문제)."""
import argparse
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WORKSPACE = {'quick_test.py', 'web_test.py', 'shim_compat_test.py'}
SKIP = {'run_workspace_test.py'}


def run(cmd, timeout):
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, '시간 초과 %d초' % timeout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('only', nargs='*', help='이 낱말이 이름에 들어간 시험만')
    ap.add_argument('--rebuild', action='store_true', help='tools/build_simpack.py, build_party_html.py index.html 먼저')
    ap.add_argument('--e2e', metavar='PYTHON', help='Playwright 가 깔린 python 경로(예: E:\\AI_mk2\\venv-pw\\Scripts\\python.exe)')
    ap.add_argument('--timeout', type=int, default=900)
    a = ap.parse_args()
    py = [sys.executable, '-X', 'utf8', '-I']
    if a.rebuild:
        for cmd in (py + ['tools/build_simpack.py'], py + ['build_party_html.py', 'index.html']):
            code, out = run(cmd, a.timeout)
            print(('OK  ' if code == 0 else 'ERR ') + ' '.join(cmd[4:]))
            if code:
                print(out[-2000:])
                return 1
    tests = []
    tdir = os.path.join(ROOT, 'tests')
    for f in sorted(os.listdir(tdir)):
        if f in SKIP:
            continue
        if f.endswith('_test.py') or f == 'golden_check.py':
            tests.append((f, py + (['tests/run_workspace_test.py'] if f in WORKSPACE else []) + ['tests/' + f]))
        elif f.endswith('_test.js'):
            tests.append((f, ['node', 'tests/' + f]))
    if a.only:
        tests = [t for t in tests if any(w in t[0] for w in a.only)]
    if a.e2e:
        tests.append(('e2e/test_page.py', [a.e2e, '-X', 'utf8', 'tests/e2e/test_page.py', '--shots', 'local/shots']))
    fails = []
    for name, cmd in tests:
        code, out = run(cmd, a.timeout)
        print(('ok   ' if code == 0 else 'FAIL ') + name, flush=True)
        if code:
            fails.append((name, out))
    print('\n통과 %d / 실패 %d' % (len(tests) - len(fails), len(fails)))
    for name, out in fails:
        print('\n--- %s ---' % name)
        print('\n'.join(out.strip().splitlines()[-15:]))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
