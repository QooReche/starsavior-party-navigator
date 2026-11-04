# -*- coding: utf-8 -*-
"""build 26314877 선제 방어 차단 경계. 계정 자료 없이 공개/합성 유닛만 사용."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.mc import Ctx
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS


class PreemptiveClientTest(unittest.TestCase):
    def test_buff_gate_reaches_actual_attack(self):
        self.assertEqual(MC_OPTS['preemptive_defense'], 'client_main')   # 2026-11-04 기본 전환(legacy recognize)
        for mode, blocked in [('client', True), ('on', False)]:
            b = battle([unit('victim', hp=10**7), unit('guard', hp=10**7)],
                       [unit('attacker', hp=10**7)], mc={'preemptive_defense': mode})
            victim, guard = b.allies
            guard.d.passive['preempt'] = 1.0
            attacker = b.foes[0]
            give(attacker, '선제 방어 무시')
            b.cast(attacker, attacker.d.skills['기본기'], target=victim)
            self.assertEqual(attacker.cast_count['기본기'], 1)
            self.assertGreater(sum(x.maxhp - x.hp for x in b.allies), 0)
            self.assertEqual(victim.hp < victim.maxhp, blocked)
            self.assertEqual(guard.hp < guard.maxhp, not blocked)

    def test_skill_gate_uses_exact_form_and_slot(self):
        for key, slot, blocked in [('trish', '궁극기', True), ('trish', '기본기', False),
                                   ('bunny-claire@개화(SSR)', '궁극기', True),
                                   ('bunny-claire', '궁극기', False)]:
            b = battle([unit_def(key)], [unit('victim'), unit('guard')],
                       mc={'preemptive_defense': 'client'})
            attacker = b.allies[0]
            victim, guard = b.foes
            guard.d.passive['preempt'] = 1.0
            ctx = Ctx(attacker, victim, attacker.d.skills[slot])
            got = b._preemptive_check(attacker, [victim], ctx)
            self.assertEqual(got, [victim if blocked else guard])


if __name__ == '__main__':
    unittest.main()
