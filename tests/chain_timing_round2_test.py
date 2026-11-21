"""Native chain grouping and the reaction-to-turn-end boundary; --mutations."""
import inspect
import io
import json
import os
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from battlesim.starsavior import chain_se
from battlesim.starsavior.data import get_db
from battlesim.starsavior.myinfo_combat import select_skills
from battlesim.starsavior.parser import Line, UnitDef
from battlesim.starsavior.mc_semantics import normalized_lines


class ChainTimingTest(unittest.TestCase):
    def setup_chain(self):
        b = battle([unit('caster', df=0)], [unit('target', df=0, hp=10**6)], opts={'coop': False, 'nova': False})
        a, v = b.allies[0], b.foes[0]
        a.key = a.d.key = 'cristelle'
        slot, raw = next(k for k in chain_se.data()['cristelle'] if k[0] == '고유 패시브')
        ln = Line(raw, slot, 'passive')
        a.d.lines = [ln]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = v, [v]
        give(v, '약화', harmful=True)
        return b, a, v, ln, ctx

    def test_mapping_every_skill_level(self):
        db = get_db()
        for key in ('cristelle', 'asherah-order-striker'):
            for level in range(1, 5):
                raw = select_skills(db.units[key], key, {'skills': {'passive': level, 'hyper': level}})
                d = UnitDef(db, key, unit_data=raw)
                lines = [ln for ln in normalized_lines(d) if ln.eff['kind'] == 'chain']
                self.assertTrue(lines)
                for ln in lines:
                    self.assertIn((ln.slot, ln.raw), chain_se.data()[key])

    def test_generated_mapping_matches_client(self):
        tables = os.environ.get('COSMO_TABLES')
        if not tables:
            self.skipTest('COSMO_TABLES 없음')
        from tools.build_chain_se import build
        expected = json.loads((ROOT / 'data/chain_se.json').read_text(encoding='utf8'))['units']
        self.assertEqual(build(tables), expected)

    def test_snapshot_survives_source_death_and_uses_live_defense(self):
        b, a, v, ln, ctx = self.setup_chain()
        b.run_line(a, ln, ctx)
        self.assertEqual(v.taken, 0)
        self.assertEqual(len(b._chain_damage), 1)
        amount = b._chain_damage[0][3]
        self.assertEqual(amount, 740)
        give(a, '공격 증가', {'공격력%': 1000})
        v.d.stats['def'] = 1000
        b.dirty(v)
        b.kill(a, v)
        b.flush_chain_damage()
        from battlesim import rules
        self.assertEqual(v.taken, int(amount * rules.DEF_K / (1000 + rules.DEF_K)))
        self.assertEqual(b.rule_hits['chain_timing_applied'], 1)

    def test_flush_after_reactions_before_turn_end(self):
        b, a, v, ln, ctx = self.setup_chain()
        events = []
        apply, fire = b.apply_damage, b.fire
        def record(owner, target, amount, kind, **kw):
            if kind == 'chain': events.append('chain')
            return apply(owner, target, amount, kind, **kw)
        def react():
            events.append('reaction')
        def on_fire(owner, kind, context):
            if kind == 'own_te': events.append('turn_end')
            return fire(owner, kind, context)
        with patch.object(b, '_run_reactions', react), patch.object(b, 'apply_damage', record), patch.object(b, 'fire', on_fire):
            b.act(a)
        self.assertGreater(b.progress(), 0)
        self.assertIn('chain', events)
        self.assertLess(events.index('reaction'), events.index('chain'))
        self.assertLess(events.index('chain'), events.index('turn_end'))

    def test_group_order_and_dead_targets(self):
        b = battle([unit('a')], [unit('one'), unit('two'), unit('dead')])
        a = b.allies[0]; one, two, dead = b.foes
        # Smaller BuffId loses to a group hitting two distinct targets.
        b._chain_damage = [(1, a, one, 3, True, 0), (2, a, one, 4, True, 0),
                           (2, a, two, 5, True, 0), (3, a, dead, 9, True, 0)]
        b.kill(dead, a)
        seen = []
        def record(owner, target, amount, true, pen):
            seen.append(amount)
            # A death-trigger revival during an earlier group cannot revive a
            # pending hit that was excluded at the start of the native flush.
            dead.dead, dead.hp = False, 100
        with patch.object(b, '_apply_chain_amount', record):
            b.flush_chain_damage()
        self.assertEqual(seen, [4, 5, 3])
        self.assertFalse(b._chain_damage)

    def test_legacy_stays_immediate(self):
        b, a, v, ln, ctx = self.setup_chain()
        b.mc['chain_timing'] = 'immediate'
        b.run_line(a, ln, ctx)
        self.assertGreater(v.taken, 0)
        self.assertFalse(b._chain_damage)


def mutations():
    cases = [
        ('chain', "if mode in ('client_mapped', 'client_queue') else None", 'if False else None', 'test_snapshot_survives_source_death_and_uses_live_defense'),
        # 기본 chain_timing=client_queue 는 통합 큐(flush_add_damage)를 부름(tests/chain_queue_conn_test.py).
        ('_act_turn', 'self.flush_add_damage()', 'None', 'test_flush_after_reactions_before_turn_end'),
        ('flush_chain_damage', '(-len({r[2] for r in groups[k]}), k)', '(k, 0)', 'test_group_order_and_dead_targets'),
        ('flush_chain_damage', 'if target in dead_at_start or target.dead:', 'if target.dead:', 'test_group_order_and_dead_targets'),
    ]
    for method, old, new, test in cases:
        original = getattr(Battle, method)
        source = textwrap.dedent(inspect.getsource(original))
        assert old in source
        ns = {}; exec(source.replace(old, new), original.__globals__, ns)
        run = lambda: unittest.TextTestRunner(stream=io.StringIO()).run(ChainTimingTest(test))
        assert run().wasSuccessful(), test
        with patch.object(Battle, method, ns[method]): result = run()
        assert result.failures and not result.errors, (test, result.errors)
        print(test, 'mutation rejected')


if __name__ == '__main__':
    if '--mutations' in sys.argv: mutations()
    else: unittest.main()
