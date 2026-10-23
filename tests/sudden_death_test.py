# -*- coding: utf-8 -*-
"""서든데스 회귀: python -X utf8 -I tests/sudden_death_test.py

전역 턴(아군·적 행동 수)이 단계의 끝 턴을 넘으면 아군 전원에 최대 생명력%·방어력%·주는 회복량%·주는 보호막량% 감소
(data/sudden_death.json, tools/build_sudden_death.py, 규칙 mc.sudden_death)."""
import json
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, unit   # noqa: E402
from battlesim import api   # noqa: E402
from battlesim.mc import Ctx   # noqa: E402

STEPS = [[3, 0.0, 0.0, 0.0, 0.0], [5, -50.0, -20.0, -50.0, -50.0], [None, -100.0, -50.0, -90.0, -90.0]]


def total_actions(b):
    return sum(u.actions for u in b.allies) + sum(u.actions for u in b.all_foes)


class SuddenStepTest(unittest.TestCase):
    def setUp(self):
        self.b = battle([unit('a', hp=10000, df=1000), unit('b', hp=10000)], [unit('boss', hp=10 ** 9, boss=True)], sudden=STEPS)

    def at(self, turn):
        self.b.global_turns = turn
        self.b._sudden_step()
        return self.b.allies[0]

    def test_boundary_inclusive(self):
        a = self.at(3)
        self.assertEqual((self.b.sd_level, a.maxhp, a.sd), (0, 10000.0, {}))
        a = self.at(4)
        self.assertEqual(self.b.sd_level, 1)
        self.assertEqual(a.maxhp, 5000.0)
        a = self.at(6)
        self.assertEqual(self.b.sd_level, 2)    # 마지막 단계(끝 턴 없음)는 끝까지

    def test_hp_clamped_not_damaged(self):
        a, c = self.b.allies
        a.hp, c.hp = 9000.0, 3000.0
        self.at(4)
        self.assertEqual((a.hp, c.hp), (5000.0, 3000.0))   # 최대보다 크면 자르고, 작으면 그대로(비율 유지 아님)
        self.assertEqual((a.taken, c.taken), (0.0, 0.0))     # 피해로 치지 않음

    def test_stats_and_dead_allies(self):
        a, c = self.b.allies
        c.dead, c.hp = True, 0.0
        self.at(4)
        self.assertAlmostEqual(self.b.def_stat(a), 800.0)
        m = a.mods()
        self.assertAlmostEqual(m['heal_give'], -0.5)
        self.assertAlmostEqual(m['barrier_give'], -0.5)
        self.assertEqual(c.maxhp, 5000.0)          # 쓰러진 아군도 맞춘다(부활 생명력 기준)
        self.assertEqual(a.n_harmful() + a.n_good(), 0)   # 효과 개수에 안 잡힘
        for f in self.b.foes:
            self.assertEqual((f.sd, f.maxhp), ({}, 10.0 ** 9))   # 적에게는 안 걸림

    def test_hp_floor_minus_99(self):
        a = self.at(9)
        self.assertEqual(a.maxhp, float(math.floor(10000 * 0.01)))

    def test_final_stat_input_same(self):
        # 기본 HP 10,000 + 패시브 15% 와 최종 HP 11,500(stats_final) 은 같은 결과(서든데스는 전투 전 최종값에 곱함 — codex 리뷰)
        base = unit('p', hp=10000)
        base.passive['hpp'] = 0.15
        final = unit('f', hp=11500)
        b = battle([base, final], [unit('boss', hp=10 ** 9)], sudden=STEPS)
        b.global_turns = 9
        b._sudden_step()
        self.assertEqual([u.maxhp for u in b.allies], [float(math.floor(11500 * 0.01))] * 2)
        b = battle([base, final], [unit('boss', hp=10 ** 9)], sudden=STEPS)
        b.global_turns = 4
        b._sudden_step()
        self.assertEqual([u.maxhp for u in b.allies], [5750.0, 5750.0])

    def test_hp_scaling_damage_same(self):
        # 생명력 비례 피해 항도 입력 방식과 무관(codex 재검토): 기본 10,000+패시브 15% vs 최종 11,500, 서든데스 −50%, 생명력 100% 계수 공격
        def taken(u):
            b = battle([u], [unit('dummy', hp=10 ** 9, df=0)], sudden=STEPS)
            b.global_turns = 4
            b._sudden_step()
            a, v = b.allies[0], b.foes[0]
            sk = a.d.skills['기본기']
            sk.cf = [0, 10000, 0, 0]
            ctx = Ctx(a, a, sk)
            ctx.targets = [v]
            b.deal(a, ctx)
            return v.taken
        base = unit('p', hp=10000)
        base.passive['hpp'] = 0.15
        self.assertEqual(taken(base), taken(unit('f', hp=11500)))
        self.assertGreater(taken(unit('f', hp=11500)), 0)

    def test_heal_and_shield_reduced(self):
        a = self.at(4)                               # 회복 −50%, 보호막 −50%, 최대 생명력 5000
        a.hp = 1.0
        self.b.run_special(a, None, Ctx(a, a, None), '자신에게 회복 = 자신 공격력×100%')
        self.assertEqual(a.hp, 1.0 + math.floor(1000 * 0.5))
        self.b.run_special(a, None, Ctx(a, a, None), '자신에게 〈보호막〉 (2턴) 보호막 = 자신 공격력×100%')
        self.assertEqual(a.shield_total(), math.floor(1000 * 0.5))
        a.hp = 4900.0
        self.b.run_special(a, None, Ctx(a, a, None), '자신에게 회복 = 자신 공격력×100%')
        self.assertEqual(a.hp, 5000.0)               # 회복 상한 = 줄어든 최대 생명력

    def test_off_switch(self):
        b = battle([unit('a', hp=10000)], [unit('boss', hp=10 ** 9)], mc=dict(sudden_death='off'), sudden=STEPS)
        b.global_turns = 9
        b._sudden_step()
        self.assertEqual((b.allies[0].maxhp, b.allies[0].sd), (10000.0, {}))


class SuddenRunTest(unittest.TestCase):
    def test_applies_during_run(self):
        steps = [[10, 0, 0, 0, 0], [None, -50.0, 0, 0, 0]]
        b = battle([unit('a%d' % i, hp=10 ** 7, atk=1) for i in range(4)], [unit('boss', hp=10 ** 9, atk=1, boss=True)],
                   turn_limit=20, sudden=steps)
        b.run()
        self.assertEqual(total_actions(b), 20)
        self.assertEqual(b.sd_level, 1)
        self.assertTrue(all(u.maxhp == 5 * 10 ** 6 for u in b.allies))

    def test_no_change_before_threshold(self):
        def run(sudden):
            b = battle([unit('a%d' % i, hp=10 ** 5, atk=100) for i in range(4)], [unit('boss', hp=10 ** 9, atk=300, boss=True)],
                       turn_limit=30, sudden=sudden, seed=3)
            b.run()
            return [(u.hp, u.dmg, u.taken) for u in b.allies]
        self.assertEqual(run([[30, 0, 0, 0, 0], [None, -90.0, -50.0, -90.0, -90.0]]), run(None))


class DataTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'data', 'sudden_death.json'), encoding='utf-8') as f:
            self.d = json.load(f)

    def test_shape(self):
        for g, steps in self.d['groups'].items():
            ends = [s[0] for s in steps]
            self.assertIsNone(ends[-1], g)
            self.assertEqual(ends[:-1], sorted(ends[:-1]), g)
            self.assertEqual(steps[0][1:], [0.0] * 4, g)             # 첫 단계는 효과 없음
            for s in steps:
                self.assertTrue(all(-100 <= v <= 0 for v in s[1:]), g)
        self.assertEqual(set(self.d['stages'].values()) - set(self.d['groups']), set())
        heads = {k.split('|', 1)[0] for k in self.d['stages']}
        self.assertEqual(heads, {'op', 'oph', 'clo'})

    def test_api_stage(self):
        r = api.simulate({'units': [{'key': k} for k in ('프로페서M', '그웬', '페이', '아모라')]},
                         {'stage': 'op/아가논 시가지/SECTOR 36-36'}, {'n_runs': 1, 'seed': 1})
        self.assertEqual(r['encounter']['sudden_death'], self.d['stages']['op|아가논 시가지|SECTOR 36-36'])


if __name__ == '__main__':
    unittest.main()
