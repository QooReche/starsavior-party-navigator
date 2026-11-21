"""M reaction booking vs skill-end consumption (build 26610546).
Native evidence: NKM 8645-8651, 9101-9151; SE 10392011 SKILL_END.
"""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Ctx
from battlesim.metrics import unit_def

class StackReactTimingTest(unittest.TestCase):
    def setup_battle(self):
        b = battle([unit_def('professor-m'), unit('ally')],
                   [unit('old', hp=10**9), unit('new', hp=10**9)],
                   mc={'toughness': 'off'}, opts={'coop': False, 'nova': False})
        m, ally = b.allies
        give(m, '냉각', stacks=5)
        b.dirty(m)
        m.last_target = b.foes[0]
        b._react_q, b._react_seen, b._revenged, b._hit_log = [], set(), set(), None
        ctx = Ctx(ally, ally, ally.d.skills['기본기'])
        ctx.target = b.foes[0]
        ctx.targets = ctx.hit_targets = [b.foes[0]]
        return b, m, ally, ctx

    def test_booking_and_duplicate_do_not_consume(self):
        b, m, ally, ctx = self.setup_battle()
        b.event_triggers(ally, ctx, 'ally_post')
        self.assertEqual(len(b._react_q), 1)
        self.assertEqual(m.stack('냉각'), 5)
        b.event_triggers(ally, ctx, 'ally_post')
        self.assertEqual(len(b._react_q), 1)
        self.assertEqual(m.stack('냉각'), 5)

    def test_execution_target_and_skill_end(self):
        b, m, ally, ctx = self.setup_battle()
        b.event_triggers(ally, ctx, 'ally_post')
        m.last_target = b.foes[1]
        seen = []
        original = b.deal
        def deal(a, c):
            if a is m: seen.append((m.stack('냉각'), c.target))
            return original(a, c)
        b.deal = deal
        b._run_reactions()
        self.assertEqual(seen, [(5, b.foes[1])])
        self.assertEqual(m.stack('냉각'), 0)
        self.assertAlmostEqual(m.gauge, 1500.0)  # basis points
        self.assertEqual(m.cast_count['특수기(추가)'], 1)

    def test_failed_cast_preserves_stacks_and_gauge(self):
        b, m, ally, ctx = self.setup_battle()
        b.event_triggers(ally, ctx, 'ally_post')
        give(m, '기절')
        b.dirty(m)
        b._run_reactions()
        self.assertEqual(m.stack('냉각'), 5)
        self.assertEqual(m.gauge, 0)
        self.assertEqual(m.cast_count['특수기(추가)'], 0)
        self.assertNotIn(b._react_key(m, '특수기'), b._react_seen)

    def test_missing_or_dead_recent_target_uses_living_enemy(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                b, m, ally, ctx = self.setup_battle()
                b.event_triggers(ally, ctx, 'ally_post')
                b.foes[0].dead = True
                m.last_target = None if missing else b.foes[0]
                seen = []
                original = b.deal
                def deal(a, c):
                    if a is m: seen.append((m.stack('냉각'), c.target))
                    return original(a, c)
                b.deal = deal
                b._run_reactions()
                self.assertEqual(seen, [(5, b.foes[1])])
                self.assertEqual(m.stack('냉각'), 0)

    def test_condition_is_not_checked_again_at_execution(self):
        b, m, ally, ctx = self.setup_battle()
        b.event_triggers(ally, ctx, 'ally_post')
        self.assertEqual(m.stack('냉각'), 5)
        m.eff['냉각'].stacks = 1
        b.dirty(m)
        b._run_reactions()
        self.assertEqual(m.cast_count['특수기(추가)'], 1)
        self.assertEqual(m.stack('냉각'), 0)

if __name__ == '__main__':
    unittest.main()
