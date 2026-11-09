# -*- coding: utf-8 -*-
"""chain_pen=client: 연쇄(추가 고정량) 피해는 공격자의 방어 관통을 쓰지 않는다(NKM:17335-17356,17837-17855).
실행: python -X utf8 -I tests/chain_pen_test.py"""
import os
import random
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from battlesim.mc import Battle, Eff                             # noqa: E402
from battlesim.metrics import unit_def                           # noqa: E402
from foe_react_test import _foe                                  # noqa: E402


def _chain_taken(chain_pen, pen_pct):
    foe = _foe({'특수기': {'timing': 'hit', 'conds': [['skill_basic']], 'target': 'react_target', 'is_attack': True}})
    b = Battle([unit_def('emily')], [[foe]], random.Random(5), opts=dict(nova_policy='auto', coop=False),
               mc=dict(chain_pen=chain_pen), timeline=False)
    b.spawn_wave()
    a, f = b.allies[0], b.foes[0]
    if pen_pct:
        e = Eff('관통', {'방어 관통': pen_pct}, 1, 99, a, False)
        e.stacks = 1
        a.eff['관통'] = e
        b.dirty(a)
    b.chain(a, dict(random_enemy=True, stat='atk', coef=1.0), None)
    return f.taken


class ChainPenTest(unittest.TestCase):
    def test_client_ignores_attacker_penetration(self):
        self.assertEqual(_chain_taken('client', 50), _chain_taken('client', 0))

    def test_attacker_mode_uses_penetration(self):
        self.assertGreater(_chain_taken('attacker', 50), _chain_taken('attacker', 0))

    def test_without_penetration_modes_agree(self):
        self.assertEqual(_chain_taken('client', 0), _chain_taken('attacker', 0))


if __name__ == '__main__':
    unittest.main()
