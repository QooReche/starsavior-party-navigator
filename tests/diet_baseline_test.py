# -*- coding: utf-8 -*-
"""엔진 다이어트 결과 불변 기준선 시험(docs/engine_diet_1122.md).

- test_baseline_same: 콘텐츠별 스테이지 × 대표 파티 × 시드 3개의 결과 해시(raw_runs·runs·결과 전체·web.run_auto 문자열)가
  tests/golden/diet_baseline.json 과 바이트 일치. 다이어트(스위치 삭제·log 가드·묶음 경량화)는 이 시험을 바꾸지 않고 통과해야 한다.
  엔진 결과를 «의도적으로» 바꾼 커밋에서만 tools/diet_baseline.py --write 로 다시 고정하고 사유를 docs/HISTORY.md 에.
- test_pack_same: sim/manifest.json 의 파일만 빈 폴더에 복사해(브라우저 Pyodide 와 같은 조건: metrics.py·quick.py·default.json 없음,
  축약본 default.min.json 만) 같은 기준선을 계산해도 바이트 일치.
- test_slim_rules_current: 묶음의 축약본이 지금 default.json 에서 다시 만든 것과 같다(default.json 만 고치고 build_simpack 을 안 돌린 경우를 잡음).

  python -X utf8 -I tests/diet_baseline_test.py
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_simpack  # noqa: E402
import diet_baseline  # noqa: E402

DROPPED = ('battlesim/metrics.py', 'battlesim/quick.py', 'battlesim/rules/default.json')


def _golden():
    with open(diet_baseline.GOLDEN, encoding='utf-8') as f:
        return json.load(f)['cases']


class DietBaseline(unittest.TestCase):
    def test_baseline_same(self):
        want = _golden()
        got = diet_baseline.compute()
        self.assertEqual(len(got), len(diet_baseline.CASES) * len(diet_baseline.PARTIES) * len(diet_baseline.SEEDS))
        self.assertEqual(sorted(got), sorted(want))
        bad = [k for k in got if got[k] != want[k]]
        self.assertEqual(bad, [], '기준선과 다른 케이스')
        # 기준선이 실제로 뭔가를 지키는지: 진행도 0 인 케이스만 있으면 엔진을 꺼도 통과한다
        self.assertTrue(all(v['prog'] > 0 for v in got.values()))
        self.assertTrue(any(v['clear'] < 1 for v in got.values()) and any(v['clear'] > 0 for v in got.values()))
        # PC 경로에서도 진입점이 묶음에서 뺀 모듈을 안 부른다
        self.assertNotIn('battlesim.metrics', sys.modules)
        self.assertNotIn('battlesim.quick', sys.modules)

    def test_slim_rules_current(self):
        with open(os.path.join(ROOT, *build_simpack.SLIM_RULES.split('/')), encoding='utf-8', newline='') as f:
            self.assertEqual(f.read(), build_simpack.slim_rules(), 'tools/build_simpack.py 재실행 필요(default.json 변경)')

    def test_pack_same(self):
        with open(os.path.join(ROOT, 'sim', 'manifest.json'), encoding='utf-8') as f:
            man = json.load(f)
        self.assertEqual([p for p in DROPPED if p in man['files']], [])
        self.assertIn(build_simpack.SLIM_RULES, man['files'])
        tmp = os.path.join(ROOT, 'local', 'test-tmp', 'diet_pack_' + uuid.uuid4().hex)
        try:
            for p in man['files']:
                dst = os.path.join(tmp, *p.split('/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(ROOT, *p.split('/')), dst)
            for p in DROPPED:
                self.assertFalse(os.path.exists(os.path.join(tmp, *p.split('/'))))
            env = dict(os.environ, PN_SRC=tmp)
            code = ('import sys,json;sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2]);import diet_baseline as D;'
                    'got=D.compute();import battlesim.rules as R;'
                    'print(json.dumps(dict(got=got,mods=sorted(m for m in sys.modules if m.startswith("battlesim")),'
                    'rules=R.__file__,legacy=len(R.LEGACY_OPTS))))')
            r = subprocess.run([sys.executable, '-X', 'utf8', '-I', '-c', code, os.path.join(ROOT, 'tools'), tmp],
                               capture_output=True, text=True, encoding='utf-8', env=env, cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr[-1500:])
            out = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertTrue(out['rules'].startswith(tmp), out['rules'])       # 묶음 폴더의 엔진이 돌았다
            self.assertEqual(out['legacy'], 0)                                 # 축약본(legacy 없음)을 읽었다
            self.assertNotIn('battlesim.metrics', out['mods'])
            self.assertNotIn('battlesim.quick', out['mods'])
            want = _golden()
            bad = [k for k in want if out['got'].get(k) != want[k]]
            self.assertEqual(bad, [], '묶음만으로 계산한 결과가 기준선과 다름')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
