# -*- coding: utf-8 -*-
"""구원자별 예외 규칙 표(battlesim/starsavior/savior_rules.py, 설계 fable_unify 4단계) 계약.

  - 표에 오른 키가 모두 시뮬 DB 구원자 키다(오타는 조용히 무시되므로 여기서 실패시킨다).
  - 조건 사전의 열쇠는 해석기(matches)가 아는 것뿐이다.
  - marker_se.KEYS = MARKER_SCOPE 의 키, MARKER_TARGETS 의 키는 MARKER_SCOPE 안에 있다.
  - 표 대상 구원자 전원이 보강 기준선(tools/unify_baseline.py) 파티에 들어 있다.
  - 표 대상 구원자의 정규화 줄(normalized_lines 의 효과 사전·after_active_se·marker_se.scope)이 골든
    tests/golden/savior_rules_lines.json 과 같다(전투 결과에 안 드러나는 표 행 — 예: 린 표지 대상 — 을 지워도 잡힘).
  - 표의 행마다 맞는 줄이 하나 이상 있다(죽은 행·조건 오타 검출).

  python -X utf8 -I tests/savior_rules_test.py
  python -X utf8 -I tests/savior_rules_test.py --write    # 골든 다시 쓰기 — 표 결과가 «의도적으로» 바뀐 커밋에서만
"""
import hashlib
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim.starsavior import marker_se, savior_rules as R   # noqa: E402
from battlesim.starsavior.data import get_db   # noqa: E402

GOLDEN = os.path.join(ROOT, 'tests', 'golden', 'savior_rules_lines.json')
RULESETS = {'default': None, 'off': {}}   # None = MC_OPTS(marker_se_flow·smile_waterbomb_scope 등 기본값)


def lines_of(key, rules):
    from battlesim import api
    from battlesim.rules import MC_OPTS
    from battlesim.starsavior.mc_semantics import normalized_lines, after_active_se
    defs, _ = api._norm_party([key], get_db(), 'fixed', 'standard', MC_OPTS)
    return defs[0], normalized_lines(defs[0], dict(MC_OPTS) if rules is None else rules), after_active_se


def snapshot():
    out = {}
    for key in sorted(R.table_keys()):
        for rn, rules in RULESETS.items():
            _, ls, after = lines_of(key, rules)
            rows = [[ln.slot, ln.src_kind, ln.kind, ln.raw, list(ln.eff.items()), after(key, ln), marker_se.scope(key, ln)]
                    for ln in ls]
            s = json.dumps(rows, ensure_ascii=False, default=repr, separators=(',', ':'))
            out['%s/%s' % (key, rn)] = hashlib.sha256(s.encode('utf-8')).hexdigest()[:20]
    return out


LINE_KEYS = {'ln_slot', 'ln_src', 'ln_kind', 'ln_kind_in', 'ln_raw_has'}


def conds():
    yield from (c for _, c in R.AFTER_ACTIVE)
    yield from R.MARKER_SCOPE.values()
    yield from (c for rows in R.MARKER_TARGETS.values() for c, _ in rows)
    yield from (row[3] for row in R.KEEP_NATIVE_SELECTOR)


class SaviorRules(unittest.TestCase):
    def test_keys_exist(self):
        units = get_db().units
        self.assertEqual(sorted(k for k in R.table_keys() if k not in units), [])

    def test_cond_keys(self):
        for c in conds():
            for k in c:
                if k.startswith('ln_'):
                    self.assertIn(k, LINE_KEYS)
                    if k != 'ln_raw_has':
                        self.assertIn(k[:-3] if k.endswith('_in') else k, R.LINE_ATTR)

    def test_marker_tables(self):
        self.assertEqual(marker_se.KEYS, frozenset(R.MARKER_SCOPE))
        self.assertLessEqual(set(R.MARKER_TARGETS), set(R.MARKER_SCOPE))

    def test_switches_exist(self):
        from battlesim.rules import MC_OPTS
        for _, switch, on, _, hit in R.KEEP_NATIVE_SELECTOR:
            self.assertIn(switch, MC_OPTS)

    def test_baseline_covers_table(self):
        import unify_baseline as U
        units = {u for c in U.CASES for _, us in c[4] for u in us}
        self.assertEqual(sorted(R.table_keys() - units), [])

    def test_normalized_lines_golden(self):
        with open(GOLDEN, encoding='utf-8') as f:
            want = json.load(f)['lines']
        got = snapshot()
        self.assertEqual(sorted(k for k in got if got[k] != want.get(k)), [])
        self.assertEqual(sorted(got), sorted(want))

    def test_every_row_used(self):
        """표의 행마다 그 구원자의 줄(원본 d.lines + 기본 규칙 정규화 결과) 중 맞는 것이 있다."""
        unused = []
        for key in sorted(R.table_keys()):
            d, ls, _ = lines_of(key, None)
            pool = list(d.lines) + list(ls)
            for keys, cond in R.AFTER_ACTIVE:
                if key in keys and not any(ln.src_kind == 'passive' and R.matches(ln, cond) for ln in pool):
                    unused.append(('AFTER_ACTIVE', key, cond))
            if key in R.MARKER_SCOPE and not any(R.matches(ln, R.MARKER_SCOPE[key]) for ln in pool):
                unused.append(('MARKER_SCOPE', key))
            for cond, _ in R.MARKER_TARGETS.get(key, ()):
                if not any(R.matches(ln, cond) for ln in pool):
                    unused.append(('MARKER_TARGETS', key, cond))
            for k, _, _, cond, _ in R.KEEP_NATIVE_SELECTOR:
                if k == key and not any(R.matches(ln, cond) for ln in pool):
                    unused.append(('KEEP_NATIVE_SELECTOR', key, cond))
        # 옛 marker_se.normalize 가 세레스·메이드 리디아 공용 블록에 둔 규칙 — 현재 세레스 줄에는 해당 표지가 없다(동작 보존으로 둠)
        known = [('MARKER_TARGETS', 'ceres', {'name': R.TURN})]
        self.assertEqual([u for u in unused if u not in known], [])


if __name__ == '__main__':
    if '--write' in sys.argv:
        with open(GOLDEN, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(dict(_note='구원자 예외 규칙 표 대상의 정규화 줄 해시(tests/savior_rules_test.py --write). sha256 앞 20자',
                           lines=snapshot()), f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        print('저장', GOLDEN)
    else:
        unittest.main()
