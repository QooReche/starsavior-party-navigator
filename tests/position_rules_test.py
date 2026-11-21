"""build 26610546 NKM:616-635,1032,7766-7809,9040-9072,13247-13263."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit
from battlesim.mc import Ctx


class PositionRulesTest(unittest.TestCase):
    def make(self, slots=(0, 2, 4), deck='BATTLE_SLOT_4', **mc):
        b = battle([unit('front1'), unit('front2'), unit('back0'), unit('back3')],
                   [unit('f' + str(i)) for i in range(len(slots))], mc=mc)
        for u, slot in zip(b.foes, slots):
            u.d.game_slot = slot
            u.d.game_deck = deck
        return b

    def test_enemy_filter_uses_spawn_slot_not_list_index(self):
        b = self.make()
        a = b.allies[0]
        self.assertEqual(b._filter(a, b.foes, 'front'), [b.foes[1]])
        self.assertEqual(b._filter(a, b.foes, 'back'), [b.foes[0]])
        self.assertGreater(b.rule_hits['target_row_slot'], 0)

    def test_deck_sizes_and_neutral_fifth_slot(self):
        for deck, front, back in [('BATTLE_SLOT_1', [0], []),
                                  ('BATTLE_SLOT_2', [0, 1], []),
                                  ('BATTLE_SLOT_3', [1], [0, 2]),
                                  ('BATTLE_SLOT_4', [1, 2], [0, 3])]:
            with self.subTest(deck=deck):
                b = self.make(tuple(range(5)), deck)
                self.assertEqual([v.d.game_slot for v in b._filter(b.allies[0], b.foes, 'front')], front)
                self.assertEqual([v.d.game_slot for v in b._filter(b.allies[0], b.foes, 'back')], back)

    def test_empty_row_filter_keeps_candidates(self):
        b = self.make((4,))
        self.assertIs(b.filter_pick(b.allies[0], b.foes, [('front', 1.0)]), b.foes[0])
        self.assertIs(b.filter_pick(b.allies[0], b.foes, [('back', 1.0)]), b.foes[0])

    def test_four_ally_rows_stay_the_same(self):
        b = self.make()
        self.assertEqual(b._filter(b.foes[0], b.allies, 'front'), b.allies[:2])
        self.assertEqual(b._filter(b.foes[0], b.allies, 'back'), b.allies[2:])

    def test_unknown_custom_foes_keep_approximation(self):
        b = self.make((None, None, None))
        self.assertEqual(b._filter(b.allies[0], b.foes, 'front'), b.foes[:2])
        self.assertEqual(b.alive(1), b.foes)

    def test_living_order_keeps_slot_holes(self):
        b = self.make((4, 0, 2))
        self.assertEqual([v.pos for v in b.alive(0)], [2, 0, 1, 3])
        self.assertEqual([v.d.game_slot for v in b.alive(1)], [0, 2, 4])
        b.kill(b.allies[0], b.foes[0])
        self.assertEqual([v.pos for v in b.alive(0)], [2, 1, 3])
        self.assertGreater(b.rule_hits['living_slot_order'], 0)

    def test_aoe_target_order_follows_game_slots(self):
        b = self.make()
        a = b.foes[0]
        a.d.skills['기본기'].all = True
        self.assertEqual([v.pos for v in b.skill_targets(a, a.d.skills['기본기'])], [2, 0, 1, 3])

    def test_preemptive_first_success_can_be_back_row(self):
        b = self.make()
        a = b.foes[0]
        # Two certain interceptors: game slot 0 must win before game slot 1.
        b.allies[0].d.passive['preempt'] = 1.0
        b.allies[2].d.passive['preempt'] = 1.0
        ctx = Ctx(a, a, a.d.skills['기본기'], False)
        self.assertEqual(b._preemptive_check(a, [b.allies[3]], ctx), [b.allies[2]])


if __name__ == '__main__':
    unittest.main()
