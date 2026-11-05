# -*- coding: utf-8 -*-
"""«N턴 이내 클리어율»(미션 BMT_LIMIT_TURN) 회귀: python -X utf8 -I tests/star_turn_test.py

장비 탐사 스테이지 3별 미션 = 60턴 이내 승리(표 BATTLE_TEMPLET_NORMAL). 단위는 결과 화면 TURN = 전체 행동 수(ttk_actions)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from battlesim.api import simulate   # noqa: E402

PARTY = ['professor-m', 'gwen', 'fei', 'amora']
STAGE = {'stage': 'equip/잊혀진 맹세/잊혀진 맹세 Ⅰ'}


def run(**extra):
    return simulate(PARTY, STAGE, dict({'n_runs': 12, 'seed': 3}, **extra))


class StarTurnTest(unittest.TestCase):
    def test_absent_without_option(self):
        self.assertIsNone(run().get('star_turn'))

    def test_bounds_and_monotone(self):
        base = run()
        clear = base['outcome']['clear_p']
        self.assertGreater(clear, 0, '시험 전제: 이 편성이 클리어해야 함')
        big = run(star_turns=10 ** 6)['star_turn']
        self.assertEqual(big['p'], clear)          # 한도 없는 수준이면 클리어율과 같음
        zero = run(star_turns=1)['star_turn']
        self.assertEqual(zero['p'], 0)             # 1행동 안에 못 이김
        mid = int(base['outcome']['ttk_actions_median'])
        m = run(star_turns=mid)['star_turn']['p']
        self.assertTrue(0 < m <= clear, (m, clear))
        self.assertLess(m, clear + 1e-9)

    def test_outcome_unchanged(self):
        self.assertEqual(run()['outcome'], run(star_turns=60)['outcome'])   # 해시 고정 시험이 outcome 을 보므로 불변


class HealRawTest(unittest.TestCase):
    """게임 결과 화면의 «회복»은 초과 회복을 포함한 원래 회복량(클라 SkillEffectHeal NKM:5472-5483). 시뮬 heal 은 채워진 양만 셈 -> heal_raw 가 따로 있어야 함"""

    def test_raw_includes_overheal(self):
        units = [{'key': k, 'stats_override': {'atk': 12000, 'hp': 40000, 'def': 3000, 'spd': 170}} for k in ('trish', 'haydee', 'ceres-sun-supporter', 'gwen')]
        r = simulate({'units': units, 'leader': 2}, {'stage': 'equip/혹한의 습격/혹한의 습격 XⅨ'}, {'n_runs': 8, 'seed': 3})   # 약한 능력치로 피해를 받아야 회복이 일어남
        eff = sum(v['heal'] for v in r['per_unit'].values())
        raw = sum(r['heal_raw'].values())
        self.assertGreater(eff, 0, '시험 전제: 회복이 일어나야 함')
        self.assertGreater(raw, eff, '초과 회복이 있으면 원래 회복량이 채워진 양보다 커야 함')
        for nm, v in r['per_unit'].items():
            self.assertGreaterEqual(r['heal_raw'][nm] + 1, v['heal'], nm)


if __name__ == '__main__':
    unittest.main()
