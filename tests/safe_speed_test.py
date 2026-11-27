"""One speed calculation per pre-action segment, renewed at round boundaries."""
import pathlib
import sys
import unittest
from collections import Counter
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from simkit import battle, unit
from battlesim.mc import Unit


class SafeSpeed(unittest.TestCase):
    def test_segment_and_round_boundary(self):
        b = battle([unit('a', spd=20)], [unit('f', spd=20)],
                   mc={'break_skill_cd_unit': 'round'},
                   break_skill={'name': '큐브 과부하', 'level': 5})
        calls, segments, boundaries = Counter(), [], []
        original = Unit.spd

        def speed(u):
            calls[u] += 1
            return original(u)

        def tick():
            if calls:
                segments.append(dict(calls))
                self.assertEqual(set(calls.values()), {1})
                calls.clear()

        def boundary():
            boundaries.append(b.t)
            b.foes[0].d.spd_base += 30

        actors = []
        def act(u):
            actors.append(u.side)
            u.gauge = 0
            if len(actors) == 3:
                b.allies[0].dead = True

        with patch.object(Unit, 'spd', speed), patch.object(b, 'tick', tick), \
                patch.object(b, '_tick_break_skill', boundary), patch.object(b, 'act', act):
            b.run()
        self.assertGreater(len(segments), 3)
        self.assertGreater(len(boundaries), 0)
        self.assertEqual(actors[0], 1, 'speed change at boundary affects next actor')
        self.assertGreater(b.global_turns, 0)


if __name__ == '__main__':
    unittest.main()
