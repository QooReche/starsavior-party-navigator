# -*- coding: utf-8 -*-
"""회복 전용 노바 정책 및 변경 전 auto/manual 수치 회귀. python -X utf8 -I tests/heal_burst_test.py"""
import hashlib
import copy
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim.api import _CustomFoe, simulate
from battlesim.mc import Battle, heal_burst_rank
from battlesim.metrics import unit_def
from battlesim.starsavior.parser import Line, Skill
import ingame_check

TEAM = ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle']


def battle(keys=TEAM, **opts):
    foe = _CustomFoe(dict(name='target', hp=10**8, atk=1000, **{'def': 1000}, spd=100), 0)
    b = Battle([unit_def(k) for k in keys], [[foe]], random.Random(7),
               opts=dict(nova_policy='heal', coop=False, **opts), timeline=True)
    b.spawn_wave()
    return b


def support(ef=(), hl=None, nb=()):
    d = _CustomFoe(dict(name='healer', hp=10000, atk=1000, **{'def': 1000}, spd=100), 0)
    raw = dict(sl='궁극기', n='heal', ty='액티브', tg='아군 전체', act='비공격', ef=list(ef), hl=hl)
    d.skills = {'궁극기': Skill(raw)}
    d.lines = [Line(r, '궁극기', 'active') for r in ef]
    d.nb = {'궁극기 사용 시': list(nb)}
    return d


class HealBurstTest(unittest.TestCase):
    def test_real_skill_classification(self):
        got = {(k, slot): heal_burst_rank(unit_def(k), sk) for k in TEAM
               for slot, sk in unit_def(k).skills.items() if heal_burst_rank(unit_def(k), sk)}
        self.assertEqual(got, {('white-pearl-luna', '기본기'): 2,
                               ('wedding-carmen', '기본기'): 2, ('wedding-carmen', '궁극기'): 1})
        for k in TEAM:
            for sk in unit_def(k).trigger_skills.values():
                self.assertEqual(heal_burst_rank(unit_def(k), sk), 0)

    def test_only_selected_restorative_skill_consumes(self):
        b = battle()
        ep, luna, carmen, cristelle = b.allies
        b.team_nova = 4
        for u, slot, extra in [(ep, '특수기', False), (cristelle, '궁극기', False),
                               (carmen, '궁극기', False), (carmen, '기본기', True)]:
            self.assertFalse(b.cast(u, u.d.skills[slot], extra=extra).nb)
        self.assertEqual(sum(b.nova_bursts.values()), 0)
        b.team_nova = 3
        self.assertFalse(b.cast(carmen, carmen.d.skills['기본기']).nb)
        b.team_nova = 4
        luna.hp = 1
        plain = copy.deepcopy(b)
        plain.opts['nova'] = False
        plain.cast(plain.allies[2], plain.allies[2].d.skills['기본기'])
        before = carmen.healed
        self.assertTrue(b.cast(carmen, carmen.d.skills['기본기']).nb)
        self.assertEqual(b.team_nova, 0)
        self.assertGreater(carmen.healed, before)
        self.assertEqual(carmen.healed - plain.allies[2].healed, int(carmen.maxhp * .12))
        self.assertEqual(luna.hp - plain.allies[1].hp, int(carmen.maxhp * .12))
        self.assertFalse(any('selector:' in k for k in b.unsup))

    def test_shield_and_nova_off(self):
        for enabled in (True, False):
            b = battle(['white-pearl-luna'], nova=enabled)
            u = b.allies[0]
            b.team_nova = 4
            ctx = b.cast(u, u.d.skills['기본기'])
            self.assertEqual(ctx.nb, enabled)
            self.assertEqual(u.shield_given, int(u.maxhp * .15) if enabled else 0)
            self.assertEqual(b.team_nova, 0 if enabled else 4)

    def test_unit_pool_and_enemy_never_burst(self):
        b = battle(nova_pool='unit')
        carmen = b.allies[2]
        b.team_nova = 8
        self.assertFalse(b.cast(carmen, carmen.d.skills['기본기']).nb)
        carmen.nova = 4
        self.assertTrue(b.cast(carmen, carmen.d.skills['기본기']).nb)
        self.assertEqual((carmen.nova, b.team_nova), (0, 8))
        foe = b.foes[0]
        foe.nova = 4
        self.assertFalse(b.cast(foe, carmen.d.skills['기본기']).nb)

    def test_nonattack_fallback_and_heal_bonus(self):
        for use_bonus in (False, True):
            d = support(hl='생명력×20%', nb=(['[스킬 사용 시작 시] 자신에게 능력치 보정 주는 회복량 +50% {이번 스킬에만 적용}'] if use_bonus else []))
            b = Battle([d], [[]], random.Random(1), opts={'nova_policy': 'heal'})
            u = b.allies[0]
            u.hp = 1
            b.team_nova = 4
            self.assertTrue(b.cast(u, u.d.skills['궁극기']).nb)
            self.assertEqual(u.healed, 3000 if use_bonus else 2000)  # 피해 +15%를 힐에 곱하지 않음
            self.assertEqual(b.team_nova, 0)

    def test_effect_lines_and_conditional_execution(self):
        rows = [('[스킬 사용 후] 아군 전체에게 회복 = 자신 생명력×10%', 1),
                ('[스킬 사용 후] 자신에게 〈보호막〉 (1턴) 보호막 = 자신 생명력×10%', 1),
                ('[스킬 사용 후] 자신에게 강인도 1 회복', 0),
                ('[스킬 사용 시작 시] (조건: 내 공격 시 [대상이 보유: 보호막]) 자신에게 능력치 보정 피해 증가 +20% {이번 스킬에만 적용}', 0)]
        for raw, expected in rows:
            d = support(ef=[raw])
            self.assertEqual(heal_burst_rank(d, d.skills['궁극기']), expected)
        d = support(nb=['[스킬 사용 후] (조건: 내 행동 후 [자신이 보유: 없는 효과]) 아군 전체에게 회복 = 자신 생명력×10%'])
        b = Battle([d], [[]], random.Random(1), opts={'nova_policy': 'heal'})
        b.team_nova = 4
        u = b.allies[0]
        u.hp = 1
        self.assertTrue(b.cast(u, u.d.skills['궁극기']).nb)
        self.assertEqual(u.healed, 0)  # 후보 판정이 실제 조건을 무시해 회복시키면 안 됨

    def test_auto_manual_exact_prechange_results(self):
        expected = {'auto': '1bcc41ffa37245ac81cf5c04203c3c962886615c7aff1236ed836ccb8f270d01',
                    'manual': 'c47a35ccae24c19dd5c5e8b6d7e4d7e3202879ebb82bc27913991dbd351030cc'}
        enc = {'waves': [[{'name': 'target', 'hp': 100000000, 'atk': 1000, 'def': 1000, 'spd': 100}]], 'max_turns': 12}
        for policy, digest in expected.items():
            # Keep the original digest as a legacy regression. Native skill-end
            # gain, slot effects, skill-local chain damage and debuff-object
            # counting change later rules.
            r = simulate(TEAM, enc, {'n_runs': 3, 'seed': 7, 'nova_policy': policy, 'timeline': True,
                                    'rules_override': {'nova_skill_gain': False,
                                                       'nova_force_effects': False,
                                                       'nova_slot_effects': False,
                                                       'chain_skill_damage_up': False,
                                                       'debuff_instance_count': False,
                                                       'ally_auto_target': 'boss_first',
                                                       'enemy_auto_target': 'weighted',
                                                       'auto_skill': 'off',
                                                       'reaction_timing': 'nested',
                                                       'buff_maxhp': 'off',
                                                       'instant_damage': 'off',
                                                       'break_skill_level': 'off',
                                                       'break_skill_scale': 'off',
                                                       'ally_auto_lines': 'off',
                                                       'foe_react': 'off',
                                                       'summon': 'off'}})
            frozen = {k: v for k, v in r.items() if k in ('per_unit', 'outcome', 'timeline', 'breaks', 'break_skill', 'foes')}
            frozen['outcome'] = {k: v for k, v in frozen['outcome'].items() if k not in ('progress', 'ttk_actions_median')}   # 나중에 더한 요약 칸(전투 규칙 무관)
            self.assertEqual(hashlib.sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), digest)
            self.assertEqual(r['nova_burst']['total'] > 0, policy == 'manual')

    def test_ingame_defaults_override_and_all_run_counts(self):
        self.assertEqual(ingame_check.NOVA_POLICY, {'36-36': 'heal', '37-2': 'auto', '37-3': 'auto', '37-4': 'auto', '37-5': 'auto', '17': 'auto', '17e': 'auto', '17r': 'auto'})
        r = ingame_check.run('36-36', runs=5, bs=True)
        self.assertGreater(r['nova_burst']['total'], 0)
        self.assertEqual(r['nova_burst']['total'], sum(sum(v.values()) for v in r['nova_burst']['by_unit'].values()))
        self.assertTrue(all(set(v) == {'기본기'} for v in r['nova_burst']['by_unit'].values()))
        off = ingame_check.run('36-36', runs=5, bs=True, ov={'nova_policy': 'auto'})
        self.assertEqual(off['nova_burst']['total'], 0)
        self.assertEqual(off['nova_policy'], 'auto')


if __name__ == '__main__':
    unittest.main()
