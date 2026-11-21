# -*- coding: utf-8 -*-
"""게임 전투 통계 «피해»·«받은 피해»와 같은 집계(dmg_stat·taken_stat → api battle_stat).
클라(빌드 26610546): 통계는 계산 피해 OBF_32563 을 그대로 더함(NKM:2678-2686). 무적·스킬 무효·보호막·불사·피해 제한·오버킬은
피해 적용 함수 OBF_23259 의 지역값만 깎음(2693-2787). 즉시 피해는 대상이 시전자가 아니고 살아남을 때만(8131-8135),
연쇄 피해의 수호 분담은 받은 피해만(8378), 오비탈은 공격자 몫 없음(3290). 기존 dmg·taken(판정·로직용)은 그대로.
실행: python -X utf8 -I tests/battle_stat_test.py"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from simkit import battle, give, unit  # noqa: E402
from battlesim.mc import Ctx   # noqa: E402


def pair(hp=10000):
    b = battle([unit('a', atk=1000)], [unit('v', hp=hp)])
    return b, b.allies[0], b.foes[0]


class ApplyDamageStat(unittest.TestCase):
    def test_plain_hit_same_as_engine(self):
        b, a, v = pair()
        b.apply_damage(a, v, 1000, 'hit')
        self.assertEqual((a.dmg, v.taken), (1000, 1000))
        self.assertEqual((a.dmg_stat, v.taken_stat), (1000, 1000))

    def test_overkill_counted_in_stat_only(self):
        b, a, v = pair(hp=300)
        b.apply_damage(a, v, 1000, 'hit')
        self.assertTrue(v.dead)
        self.assertEqual((a.dmg, v.taken), (300, 300))           # 기존 집계: 넘친 피해 제외
        self.assertEqual((a.dmg_stat, v.taken_stat), (1000, 1000))

    def test_invincible_counted_in_stat_only(self):
        b, a, v = pair()
        give(v, '무적')
        self.assertTrue(v.invincible())
        b.apply_damage(a, v, 1000, 'hit')
        self.assertEqual((a.dmg, v.taken, v.hp), (0, 0, 10000))
        self.assertEqual((a.dmg_stat, v.taken_stat), (1000, 1000))

    def test_shield_absorb_same(self):
        b, a, v = pair()
        give(v, '보호막').shield = 400
        b.apply_damage(a, v, 1000, 'hit')
        self.assertEqual((a.dmg, v.taken, v.hp), (1000, 1000, 9400))
        self.assertEqual((a.dmg_stat, v.taken_stat), (1000, 1000))

    def test_undying_counted_in_full(self):
        b, a, v = pair(hp=300)
        give(v, '불사')
        b.apply_damage(a, v, 1000, 'hit')
        self.assertFalse(v.dead)
        self.assertLess(a.dmg, 300)
        self.assertEqual((a.dmg_stat, v.taken_stat), (1000, 1000))

    def test_stat_modes(self):
        b, a, v = pair()
        b.apply_damage(a, v, 500, 'guard', stat='taken')
        self.assertEqual((a.dmg_stat, v.taken_stat), (0, 500))
        self.assertEqual(a.dmg, 500)                              # 기존 집계는 그대로
        b.apply_damage(a, v, 500, 'hit', stat='none')
        self.assertEqual((a.dmg_stat, v.taken_stat), (0, 500))
        b.apply_damage(None, v, 200, 'bskill')                     # 오비탈: 공격자 몫 없음
        self.assertEqual(v.taken_stat, 700)

    def test_dead_or_zero_not_counted(self):
        b, a, v = pair(hp=100)
        b.apply_damage(a, v, 0, 'hit')
        self.assertEqual(v.taken_stat, 0)
        b.apply_damage(a, v, 1000, 'hit')
        b.apply_damage(a, v, 1000, 'hit')                          # 이미 죽은 대상
        self.assertEqual(v.taken_stat, 1000)


class InstantStat(unittest.TestCase):
    def test_instant_kill_not_counted(self):
        b, a, v = pair(hp=100)
        b._instant_damage(a, v)
        self.assertTrue(v.dead)
        self.assertEqual((a.dmg_stat, v.taken_stat), (0, 0))      # NKM:8131 살아남을 때만
        self.assertGreater(a.dmg, 0)                               # 기존 집계는 그대로

    def test_instant_survive_counted(self):
        b, a, v = pair(hp=10 ** 9)
        b._instant_damage(a, v)
        self.assertFalse(v.dead)
        self.assertEqual(a.dmg_stat, a.dmg)
        self.assertEqual(v.taken_stat, v.taken)

    def test_instant_invincible_counted_without_side_effects(self):
        b, a, v = pair(hp=10 ** 9)
        give(v, '무적')
        b._instant_damage(a, v)
        self.assertEqual((a.dmg, v.taken), (0, 0))
        self.assertGreater(a.dmg_stat, 0)
        self.assertEqual(a.dmg_stat, v.taken_stat)
        # 통계용 추가 계산(방어·공격력)은 rule_hits 를 남기지 않음 — 무적 조기 반환 전에 원래 세던 것만 남음
        self.assertEqual({k for k, n in b.rule_hits.items() if n} - {'dot_hit_result'}, set())

    def test_self_instant_not_counted(self):
        b, a, _ = pair()
        b._instant_damage(a, a)
        self.assertEqual((a.dmg_stat, a.taken_stat), (0, 0))
        self.assertEqual(a.dmg, 0)


class CallSiteStat(unittest.TestCase):
    """실제 호출 경로(codex 2차 리뷰 권고): 연쇄·고정 피해 수호 분담은 받은 피해만, 오비탈·타격 무효도 계산 피해를 셈."""

    def _chain(self, eff_extra=None, mc=None):
        b = battle([unit('a', df=1000), unit('g', df=3000)], [unit('f', atk=1000)],
                   mc=dict({'chain_round': 'client', 'chain_guard': 'client'}, **(mc or {})))
        a, g, f = b.allies[0], b.allies[1], b.foes[0]
        give(g, '수호', {'피해 분담(수호)': 50})
        ctx = Ctx(f, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = f, [f]
        b.chain(f, dict(stat='atk', coef=0.3337, target='attacker', **(eff_extra or {})), ctx)
        return b, a, g, f

    def test_chain_guard_share_taken_only(self):
        b, a, g, f = self._chain()
        self.assertEqual(b.rule_hits['chain_guard'], 1)
        self.assertGreater(g.taken, 0)
        self.assertEqual((a.taken_stat, g.taken_stat), (a.taken, g.taken))
        self.assertEqual(f.dmg_stat, a.taken)                     # 수호자 몫은 공격자 통계에 안 들어감(NKM:8378)
        self.assertEqual(f.dmg, a.taken + g.taken)                # 기존 집계는 그대로

    def test_chain_stat_true_guard_share_taken_only(self):
        b, a, g, f = self._chain({'damage_type': 'ADT_STAT_TRUE'}, {'chain_stat_true': 'client'})
        self.assertEqual(b.rule_hits['chain_stat_true'], 1)
        self.assertGreater(g.taken, 0)
        self.assertEqual(f.dmg_stat, a.taken)
        self.assertEqual(g.taken_stat, g.taken)

    def test_fixed_true_guard_share_taken_only(self):
        b = battle([unit('s')], [unit('t', hp=10 ** 6), unit('g', hp=10 ** 6)], mc={'fixed_true_formula': 'client'})
        s, (t, g) = b.allies[0], b.foes
        give(g, '수호', {'피해 분담(수호)': 50})
        b.fixed_true_damage(s, t, 1000)
        self.assertEqual(b.rule_hits['add_damage_guard'], 1)
        self.assertEqual((t.taken, g.taken), (500, 500))
        self.assertEqual((s.dmg_stat, t.taken_stat, g.taken_stat), (500, 500, 500))

    def _orbital(self, nullify):
        foe = unit('boss', hp=10 ** 9, skills=[dict(slot='기본기', dm=0)])
        b = battle([unit('a0'), unit('a1')], [foe], break_skill={'name': '차원 강습', 'level': 5})
        b.break_points = 3
        f = b.foes[0]
        if nullify:
            give(f, '스킬 피해 무효')
        hp = f.hp
        b._use_break_skill(b.allies[0])
        return b, f, hp

    def test_orbital_no_attacker_share(self):
        b, f, hp = self._orbital(False)
        self.assertEqual(f.taken_stat, hp - f.hp)
        self.assertTrue(all(u.dmg_stat == 0 for u in b.allies))

    def test_orbital_nullified_counts_calculated(self):
        b, f, hp = self._orbital(True)
        _, f0, hp0 = self._orbital(False)
        self.assertEqual(f.hp, hp)
        self.assertEqual(b.rule_hits['bskill_nullify'], 1)
        self.assertEqual(f.taken_stat, hp0 - f0.hp)              # 무효가 없을 때 들어갔을 계산 피해와 같음
        self.assertTrue(all(u.dmg_stat == 0 for u in b.allies))

    def _strike(self, nullify, mc):
        b = battle([unit('a', atk=1000)], [unit('v', hp=10 ** 6)], mc=mc)
        a, v = b.allies[0], b.foes[0]
        if nullify:
            give(v, '스킬 피해 무효')
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = v, [v]
        b.strike(a, v, 1000, ctx, False, 0, 0, [])
        return b, a, v

    def test_strike_nullified_counts_calculated_both_paths(self):
        _, a0, v0 = self._strike(False, {})
        for mc in ({},):
            b, a, v = self._strike(True, mc)
            self.assertEqual((v.taken, v.hp), (0, 10 ** 6), mc)
            self.assertEqual((a.dmg_stat, v.taken_stat), (v0.taken, v0.taken), mc)


class ApiStat(unittest.TestCase):
    def test_api_battle_stat_outside_per_unit(self):
        from battlesim.api import simulate
        spec = {'units': [dict(key='claire', build='standard'), dict(key='hilde', build='standard'),
                          dict(key='professor-m', build='standard'), dict(key='waltz-asherah', build='standard')]}
        r = simulate(spec, {'stage': 'op/해식 동굴/SECTOR 41-33'}, dict(n_runs=4, seed=3))
        self.assertIn('battle_stat', r)
        for nm, v in r['per_unit'].items():
            self.assertNotIn('dmg_stat', v)
            s = r['battle_stat'][nm]
            self.assertGreaterEqual(s['taken'] + 1, v['dmg_taken'], nm)   # 통계 ≥ 기존(넘친 피해·무적 몫 추가)
            self.assertGreaterEqual(s['dmg'] + 1, v['dmg'], nm)


if __name__ == '__main__':
    unittest.main()
