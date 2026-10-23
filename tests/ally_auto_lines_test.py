# -*- coding: utf-8 -*-
"""효과 줄 자동 대상(게임 SE AutoTargetId) 회귀: python -X utf8 -I tests/ally_auto_lines_test.py

구원자 = data/auto_skill.json lines(mc.ally_auto_lines), 적 = data/foe_auto.json(mc.foe_auto) — 적의 아군 대상 줄 포함."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, unit   # noqa: E402
from battlesim.mc import Ctx   # noqa: E402
from battlesim.metrics import unit_def   # noqa: E402
from tools.build_auto_skill import _skip_paren   # noqa: E402


def line_of(u, slot, head):
    return next(ln for ln in u.d.lines if ln.slot == slot and head in ln.raw)


class AllyAutoLinesTest(unittest.TestCase):
    def setup(self, mc=None):
        b = battle([unit_def('dana'), unit('low_atk', atk=100), unit('high_atk', atk=5000), unit('mid', atk=3000)],
                   [unit('boss', hp=10 ** 9)], mc=mc)
        dana = b.allies[0]
        dana.d.stats['atk'] = 10 ** 6            # 자신이 공격력 최고여도 「자신 제외」 필터로 빠져야 함
        ln = line_of(dana, '특수기', '아군 1명(자동 지정)')
        b._cur_line = ln
        return b, dana, ln

    def test_data_rule_not_self_high_atk(self):
        b, dana, ln = self.setup()
        spec = b.line_spec(dana, ln)
        self.assertEqual(spec, {'one': True, 'f': ['not_self', 'high_atk'], 'ally': True})
        got = b.resolve(dana, '아군 1명(자동 지정)', Ctx(dana, dana, dana.d.skills['특수기']))
        self.assertEqual([u.name for u in got], ['high_atk'])

    def test_off_switch_uses_description(self):
        b, dana, ln = self.setup(mc=dict(ally_auto_lines='off'))
        self.assertIsNone(b.line_spec(dana, ln))

    def test_data_shape(self):
        d = json.loads((ROOT / 'data' / 'auto_skill.json').read_text(encoding='utf-8'))
        rows = [r for v in d['lines'].values() for r in v]
        self.assertGreater(len(rows), 10)
        for slot, raw, spec in rows:
            self.assertIn('(자동 지정)', raw)
            self.assertEqual(set(spec) - {'one', 'f', 'ally'}, set())
            head = _skip_paren(raw.split(']', 1)[-1].lstrip())   # (조건: …) 를 건너뛴 대상 머리말 — 조건 안 괄호 포함
            self.assertEqual(spec.get('ally', False), not head.startswith('적'))

    def test_every_level_line_registered(self):
        """내 정보 스킬 레벨이 바꿔 끼우는 줄(데이터북 L 그룹)도 같은 규칙으로 등록 — 힐데·웨딩 에핀델 궁극기 등 레벨업 추가 행."""
        d = json.loads((ROOT / 'data' / 'auto_skill.json').read_text(encoding='utf-8'))
        index = json.loads((ROOT / 'data' / 'saviors_index.json').read_text(encoding='utf-8'))
        key_of = {int(k): v['key'] for k, v in index.items() if not k.startswith('_') and v.get('key')}
        # 빌더와 같이 id 당 마지막 기록(개화 변형이 있으면 그쪽 — 게임 표 스킬과 맞는 쪽)만 본다
        book = {u['id']: u for u in json.loads((ROOT / 'rawdata' / 'databook_main.json').read_text(encoding='utf-8'))['units']}
        missing = []
        for u in book.values():
            got = {(sl, raw) for sl, raw, _ in d['lines'].get(key_of.get(u['id']), [])}
            for s in u['sk']:
                L = s.get('L')
                if not L or not any(sl == s['sl'] for sl, _ in got):
                    continue
                for grp in L['e']:
                    missing += [(key_of[u['id']], s['sl'], L['ln'][j][:40]) for j in grp
                                if '(자동 지정)' in L['ln'][j] and (s['sl'], L['ln'][j]) not in got]
        self.assertEqual(missing, [])
        hilde = [raw for sl, raw, _ in d['lines']['hilde'] if sl == '궁극기']
        self.assertEqual(len(hilde), 3)                  # 도발 기본·75%·85% 판정

    def test_foe_ally_lines_exist(self):
        d = json.loads((ROOT / 'data' / 'foe_auto.json').read_text(encoding='utf-8'))
        ally = [s for v in d['units'].values() for s in v['lines'].values() if s.get('ally')]
        self.assertGreater(len(ally), 0)


if __name__ == '__main__':
    unittest.main()
