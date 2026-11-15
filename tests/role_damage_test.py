"""Explicit role modifiers; build26610546 NKM:18006,18059,6212-6236."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit, give
from battlesim.mc import Ctx, ROLE_NAMES, line_kind
from battlesim.starsavior.parser import Line


class RoleDamageTest(unittest.TestCase):
    def setup_pair(self, mode='client', ar='레인저', vr='디펜더'):
        b = battle([unit('a', role=ar, hp=10**7, df=0)],
                   [unit('v', role=vr, hp=10**7, df=0)],
                   mc={'role_damage_terms': mode, 'counter_inc': 0})
        return b, b.allies[0], b.foes[0]

    def damage(self, b, a, v):
        c = Ctx(a, a, a.d.skills['기본기'])
        c.targets, c.target = [v], v
        return b.final_dmg(a, v, 1000, c, False, 0, 0, 1, None)

    def test_every_role_and_direction(self):
        for role in ROLE_NAMES:
            b, a, v = self.setup_pair(vr=role)
            give(a, 'increase', {f'vs {role} 피해 증가': 50})
            give(v, 'reduce', {'vs 레인저 피해 감소': 20})
            self.assertEqual(self.damage(b, a, v), 1300)
            self.assertGreater(b.rule_hits['role_damage_terms'], 0)
            # Reduction belongs to victim and keys on the attacker, not victim.
            a.role = '서포터'
            self.assertEqual(self.damage(b, a, v), 1500)
            v.role = '미지정'
            self.assertEqual(self.damage(b, a, v), 1000)

    def test_raw_units_stacks_and_no_implicit_bonus(self):
        b, a, v = self.setup_pair()
        self.assertEqual(self.damage(b, a, v), 1000)
        give(a, 'up', {'NST_RATE_DAMAGE_UP_ROLE_DEFENDER': 1000}, stacks=2)
        give(v, 'down', {'NST_RATE_DAMAGE_REDUCE_ROLE_RANGER': 500})
        self.assertEqual(self.damage(b, a, v), 1150)
        b.mc['role_damage_terms'] = 'off'
        self.assertEqual(self.damage(b, a, v), 1000)

    def test_normal_chain_increase_only(self):
        b, a, v = self.setup_pair()
        give(a, 'up', {'vs 디펜더 피해 증가': 50})
        give(v, 'down', {'vs 레인저 피해 감소': 90})
        c = Ctx(a, a, a.d.skills['기본기']); c.target, c.targets = v, [v]
        b.chain(a, dict(stat='atk', coef=1, target='스킬 대상'), c)
        self.assertEqual(v.taken, 2775)  # (1000 + 1000 * .5) * 1.85
        self.assertGreater(b.rule_hits['role_damage_terms'], 0)

    def test_local_increase_mixed_targets(self):
        b, a, v = self.setup_pair()
        other = a  # supporter-like nonmatching target tests isolation.
        c = Ctx(a, a, a.d.skills['기본기']); c.target, c.targets = v, [v, other]
        ln = Line('[스킬 사용 시작 시] 자신에게 능력치 보정 vs 디펜더 피해 증가 +50% {이번 스킬에만 적용}', '기본기', 'active')
        b.exec_line(a, ln, c)
        self.assertEqual(b.final_dmg(a, v, 1000, c, False, 0, 0, 1, None), 1500)
        self.assertEqual(b.final_dmg(a, other, 1000, c, False, 0, 0, 1, None), 1000)
        self.assertEqual(a.mods().get('inc_role', {}), {})
        self.assertEqual(self.damage(b, a, v), 1000)  # 다음 시전에 남지 않음

    def test_local_increase_rechecks_guard_and_chain_recipient(self):
        b = battle([unit('a', role='레인저')],
                   [unit('v', role='디펜더', df=0, hp=10**7),
                    unit('guard', role='캐스터', df=0, hp=10**7)],
                   mc={'counter_inc': 0})
        a, (v, guard) = b.allies[0], b.foes
        give(guard, '수호', {'피해 분담(수호)': 50})
        c = Ctx(a, a, a.d.skills['기본기'])
        c.target, c.targets = v, [v]
        ln = Line('[스킬 사용 시작 시] 자신에게 능력치 보정 vs 캐스터 피해 증가 +50% {이번 스킬에만 적용}', '기본기', 'active')
        b.exec_line(a, ln, c)
        b.strike(a, v, 1000, c, False, 0, 0, [])
        self.assertEqual((v.taken, guard.taken), (500, 750))
        # 같은 시전에서 원 대상 밖 적에게 추가 피해를 줄 때도 현재 수신자 역할로 조회.
        c.target, c.targets = guard, [guard]
        b.chain(a, dict(stat='atk', coef=1, target='스킬 대상'), c)
        self.assertEqual(guard.taken, 750 + 2775)

    def test_dot_increase_and_reduction(self):
        b, a, v = self.setup_pair()
        give(a, 'up', {'vs 디펜더 피해 증가': 50})
        give(v, 'down', {'vs 레인저 피해 감소': 20})
        e = give(v, '연소', src=a, harmful=True)
        e.dot, e.inst = ('atk', 1), [[a, 2]]
        b._tick_dot_hot(v)
        self.assertEqual(v.taken, 2405)  # 1000 * 1.85 * (1 + .5 - .2)

    def test_stat_true_ignores_role_increase(self):
        b, a, v = self.setup_pair()
        give(a, 'up', {'vs 디펜더 피해 증가': 50})
        c = Ctx(a, a, a.d.skills['기본기']); c.target, c.targets = v, [v]
        b.chain(a, dict(stat='atk', coef=1, target='스킬 대상', damage_type='ADT_STAT_TRUE'), c)
        self.assertEqual(v.taken, 1000)

    def test_prehit_reduction_selects_attackers_role(self):
        from collections import defaultdict
        b, a, v = self.setup_pair()
        c = Ctx(v, a, a.d.skills['기본기']); c.target, c.targets = v, [v]
        c.local = defaultdict(lambda: defaultdict(float))
        ln = Line('[피해 처리 직전] 자신에게 능력치 보정 vs 레인저 피해 감소 +20% {이번 스킬에만 적용}', '고유 패시브', 'passive')
        self.assertEqual(line_kind(ln), 'prehit_self')
        b.exec_line(v, ln, c)
        self.assertEqual(c.local[v]['red'], .2)

    def test_reduction_uses_existing_net_cap(self):
        b, a, v = self.setup_pair()
        give(v, 'down', {'vs 레인저 피해 감소': 200})
        self.assertEqual(self.damage(b, a, v), 500)  # CLIENT_CONST:136, cap 5000/10000

    def test_tyria_existing_behavior_is_not_doubled(self):
        from savior_fix_test import test_fix3_tyria_stack_role
        self.assertTrue(test_fix3_tyria_stack_role()[0])


if __name__ == '__main__':
    unittest.main()
