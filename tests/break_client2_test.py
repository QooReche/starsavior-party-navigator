"""PC 26752678 오비탈 모델: 연속 보스 격파·팀 광역 피해·전투효과 영역."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simkit import battle, unit, give
from battlesim import mc
from battlesim.starsavior.parser import Line
from battlesim.api import assumptions_used
from battlesim.rules import MC_OPTS, DEFAULT_OPTS


class BreakClient2Test(unittest.TestCase):
    def chain(self):
        foe = unit('boss', hp=10**9, sa=6, skills=[dict(slot='기본기', dm=0)])
        foe.boss = True
        b = battle([unit('ally%d' % i, sa=100) for i in range(4)], [foe],
                   break_skill={'name': '행성 정화', 'level': 1},
                   max_turns=25, timeline=True)
        for ally in b.allies:
            ally.d.skills['기본기'].ab = 2
        b.run()
        self.assertGreater(b.foes[0].taken, 0)
        self.assertGreaterEqual(b.foes[0].breaks, 3)
        self.assertGreaterEqual(b.break_skill_uses, 2)
        self.assertGreaterEqual(b.break_points_gained, 6)
        self.assertEqual(b.break_points_gained, b.break_skill_uses * 3 + b.break_points)
        self.assertGreater(b.break_skill_dmg, 0)
        self.assertLessEqual(b.break_points, 3)
        return b

    def test_chain(self):
        self.chain()

    def test_chain_mutation(self):
        with patch.object(mc.Battle, '_add_break_points', lambda *args: None):
            with self.assertRaises(AssertionError):
                self.chain()

    def test_live_team_attack_sum(self):
        def damage(dead):
            b = battle([unit(atk=1000), unit('second', atk=3000)], [unit('boss', hp=10**9)],
                       break_skill={'name': '특이점 관측', 'level': 1})
            b.allies[1].dead = dead
            give(b.allies[0], '공격력 증가', {'공격력%': 50})
            b.break_points = 3
            with patch.object(b, '_break_dmg', wraps=b._break_dmg) as calc:
                b._use_break_skill(b.allies[0])
                return calc.call_args.args[1]
        self.assertAlmostEqual(damage(False), 4500 * .7 / 4 * 1.85)
        self.assertAlmostEqual(damage(True), 1500 * .7 / 4 * 1.85)

    def test_domain_separate_from_dispellable_buff(self):
        b = battle([unit()], [unit('boss')], break_skill={'name': '큐브 과부하'})
        a = b.allies[0]
        give(a, '강화 불가', harmful=True)
        b.break_points = 3
        b._use_break_skill(a)
        domain = a.eff['치트 매트릭스']
        self.assertEqual((domain.category, domain.fixed, domain.dur), ('marker', True, 5))
        give(a, '일반 강화', {'공격력%': 10})
        give(a, '오메가 프로토콜', {'공격력%': 10})
        f = b.foes[0]
        ctx = mc.Ctx(f, f, f.d.skills['기본기'])
        ctx.targets, ctx.target = [a], a
        b.run_line(f, Line('[스킬 사용 후] 스킬 대상에게 〈해제〉 (강화효과 해제)', '기본기', 'active'), ctx)
        self.assertFalse(a.has('일반 강화'))
        self.assertFalse(a.has('오메가 프로토콜'))
        self.assertTrue(a.has('치트 매트릭스'))
        for left in range(4, -1, -1):
            b._tick_break_domain('global')
            self.assertEqual(b.break_domain_remaining, left)
        self.assertFalse(a.has('치트 매트릭스'))

    def test_confirmed_rules_not_assumptions(self):
        names = {r['rule'] for r in assumptions_used(MC_OPTS, DEFAULT_OPTS)}
        for name in ('normal_points', 'boss_points', 'domain_clock', 'fixed', 'model'):
            self.assertNotIn('mc.break_skill_' + name, names)
        self.assertNotIn('mc.break_skill_residuals', names)


if __name__ == '__main__':
    unittest.main()
