"""Order oracle, including an unknown slot dying, summons and deck changes."""
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path[:0] = [str(pathlib.Path(__file__).resolve().parents[1]), str(pathlib.Path(__file__).resolve().parent)]
from simkit import battle, unit
from battlesim.mc import Unit


def original(b, side):
    pool = [u for u in b.side_units(side) if not u.dead]
    slots = [b._game_slot(u) for u in pool]
    return sorted(pool, key=b._game_slot) if all(s is not None for s in slots) else pool


class SafeOrder(unittest.TestCase):
    def test_order_and_lifetime(self):
        defs = [unit(str(i)) for i in range(4)]
        for d, slot in zip(defs, (3, None, 0, 0)):
            d.game_slot = slot
        b = battle([unit(str(i)) for i in range(4)], defs)
        self.assertEqual(b.alive(1), original(b, 1))
        b.foes[1].dead = True
        self.assertEqual(b.alive(1), original(b, 1))
        self.assertEqual([u.pos for u in b.alive(1)], [2, 3, 0])
        # Same slot ties are stable; newly appended summons join after prior occupants.
        d = unit('summoned'); d.game_slot = 0
        b.foes.append(Unit(d, 1, 4, b))
        self.assertEqual(b.alive(1), original(b, 1))
        b.waves.append([unit('next')]); b.spawn_wave()
        self.assertEqual(b.alive(1), original(b, 1))
        b.foes[0].d.game_deck = 'BATTLE_SLOT_3'
        self.assertEqual(b.alive(0), original(b, 0))

    def test_repeated_lookup_only_filters(self):
        b = battle([unit(str(i)) for i in range(4)], [unit('f')])
        b.alive(0)
        with patch.object(b, '_game_slot', side_effect=AssertionError('repeated slot lookup')):
            self.assertEqual([u.pos for u in b.alive(0)], [2, 0, 1, 3])
            b.allies[0].dead = True
            self.assertEqual([u.pos for u in b.alive(0)], [2, 1, 3])


if __name__ == '__main__':
    unittest.main()
