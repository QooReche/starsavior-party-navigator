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
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WORKSPACE = {'quick_test.py', 'web_test.py', 'shim_compat_test.py'}
SKIP = {'run_workspace_test.py'}
SKIP_RE = re.compile(r'\[건너뜀\][^\n]*|OK \(skipped=\d+\)|FAILED \([^)]*skipped=\d+[^)]*\)')


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
    ap.add_argument('--strict', action='store_true', help='환경 때문에 건너뛴 검사가 하나라도 있으면 실패로 침')
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
    skipped = []
    for name, cmd in tests:
        code, out = run(cmd, a.timeout)
        marks = [m.group(0).strip() for m in SKIP_RE.finditer(out)]
        print(('ok   ' if code == 0 else 'FAIL ') + name + ('  (건너뜀 있음)' if marks else ''), flush=True)
        skipped += [(name, m) for m in marks]
        if code:
            fails.append((name, out))
    print('\n통과 %d / 실패 %d' % (len(tests) - len(fails), len(fails)))
    if skipped:
        print('건너뜀 %d건 (이 PC 에서 검사하지 못함%s):' % (len(skipped), ', --strict 라 실패 처리' if a.strict else ''))
        for name, m in skipped:
            print('  %s: %s' % (name, m))
    for name, out in fails:
        print('\n--- %s ---' % name)
        lines = out.strip().splitlines()
        flagged = [l for l in lines if l.lstrip().startswith(('FAIL', 'ERROR', 'Traceback', 'AssertionError'))]
        print('\n'.join(flagged[:20] + ['...'] + lines[-10:] if flagged else lines[-15:]))
    return 1 if (fails or (a.strict and skipped)) else 0


if __name__ == '__main__':
    sys.exit(main())
