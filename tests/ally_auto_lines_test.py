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
            head = raw.split(']', 1)[-1].lstrip()
            if head.startswith('('):                 # (조건: …) 를 건너뛴 대상 머리말
                head = head.split(')', 1)[-1].lstrip()
            self.assertEqual(spec.get('ally', False), not head.startswith('적'))

    def test_foe_ally_lines_exist(self):
        d = json.loads((ROOT / 'data' / 'foe_auto.json').read_text(encoding='utf-8'))
        ally = [s for v in d['units'].values() for s in v['lines'].values() if s.get('ally')]
        self.assertGreater(len(ally), 0)


if __name__ == '__main__':
    unittest.main()
