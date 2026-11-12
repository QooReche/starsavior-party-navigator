"""편애의 마녀: SE 10612016, build 26610546. --mutate로 결함 주입 검증."""
import io
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, ally_auto_lines, support_report
from battlesim.metrics import unit_def


class AsherahToughnessTest(unittest.TestCase):
    def setup_battle(self, crush=True, bosses=(True, False), sa=30, mode='client'):
        b = battle([unit_def('asherah-order-striker')],
                   [unit('foe%d' % i, hp=10**9, sa=sa, boss=boss) for i, boss in enumerate(bosses)],
                   mc={'toughness_elem': mode}, opts={'coop': False, 'nova': False})
        a = b.allies[0]
        if crush:
            give(a, '파쇄', {'공격력%': 10, '강인도 고정 피해': 1})
        return b, a

    def cast(self, b, a, slot='특수기'):
        seen = []
        original = b._exec_line
        def record(owner, ln, ctx):
            if ln.eff.get('stat') == '강인도 피해 감소':
                seen.append(ctx)
            return original(owner, ln, ctx)
        with patch.object(b, '_exec_line', record):
            b.cast(a, a.d.skills[slot], target=b.foes[0])
        self.assertGreater(b.progress(), 0)
        self.assertFalse(b.unsup, dict(b.unsup))
        return seen

    def test_mapping_and_support(self):
        d = unit_def('asherah-order-striker')
        ln = next(l for l in d.lines if l.eff.get('stat') == '강인도 피해 감소')
        self.assertEqual(ln.eff['val'], -3)
        spec = ally_auto_lines(variants=True, client=True)[d.key][ln.slot, ln.raw]
        self.assertEqual(spec, {'one': False, 'f': [['has', ['보스 확인용 버프']]]})
        self.assertEqual(support_report([d]), [])

    def test_real_cast_condition_and_all_bosses(self):
        for crush, expected, count in ((False, [29, 29, 29], 0), (True, [23, 26, 23], 1)):
            b, a = self.setup_battle(crush, (True, False, True))
            seen = self.cast(b, a)
            self.assertEqual(len(seen), count)
            self.assertEqual([f.sa for f in b.foes], expected)
            if seen:
                self.assertEqual([seen[0].local_by[f].get('tough_red', 0) for f in b.foes], [-3, 0, -3])
            self.assertTrue(all(f.mods().get('tough_red', 0) == 0 for f in b.foes))

    def test_no_boss_no_fallback(self):
        b, a = self.setup_battle(bosses=(False, False))
        self.assertEqual(len(self.cast(b, a)), 1)
        self.assertEqual([f.sa for f in b.foes], [26, 26])

    def test_cast_lifetime_and_no_stacking(self):
        b, a = self.setup_battle()
        first = self.cast(b, a)[0]
        second = self.cast(b, a)[0]
        self.assertIsNot(first, second)
        self.assertEqual([f.sa for f in b.foes], [16, 22])
        self.cast(b, a, '기본기')
        self.assertEqual([f.sa for f in b.foes], [15, 22])

    def test_signed_reduction_clamp_and_immunity(self):
        for reduction, immune, expected in ((2, False, 25), (10, False, 30), (0, True, 30)):
            b, a = self.setup_battle()
            give(b.foes[0], 'test reduction', {'강인도 피해 감소': reduction})
            if immune:
                give(b.foes[0], '강인도 피해 무효')
            self.cast(b, a)
            self.assertEqual([f.sa for f in b.foes], [expected, 26])

    def test_break_and_legacy(self):
        for mode, expected in (('client', [0, 3]), ('db', [3, 3])):
            b, a = self.setup_battle(sa=7, mode=mode)
            self.cast(b, a)
            self.assertEqual([f.sa for f in b.foes], expected)
            self.assertEqual(b.foes[0].breaks, int(mode == 'client'))
            self.assertEqual(b.foes[0].broken, mode == 'client')


def mutations():
    original_exec, original_hit, original_targets = Battle._exec_line, Battle.tough_hit, Battle.line_auto_targets
    def drop(b, owner, ln, ctx):
        if ln.eff.get('stat') != '강인도 피해 감소':
            return original_exec(b, owner, ln, ctx)
    def wrong_sign(b, a, v, ctx):
        ctx.local_by[v]['tough_red'] *= -1
        return original_hit(b, a, v, ctx)
    def all_targets(b, owner, spec, ctx):
        if spec['f'] == [['has', ['보스 확인용 버프']]]:
            return b.alive(1 - owner.side)
        return original_targets(b, owner, spec, ctx)
    def leak(b, owner, ln, ctx):
        result = original_exec(b, owner, ln, ctx)
        if ln.eff.get('stat') == '강인도 피해 감소':
            for target in list(ctx.local_by):
                if ctx.local_by[target].get('tough_red'):
                    give(target, 'leaked reduction', {'강인도 피해 감소': -3})
        return result
    cases = [('drop', '_exec_line', drop, 'test_real_cast_condition_and_all_bosses'),
             ('sign', 'tough_hit', wrong_sign, 'test_real_cast_condition_and_all_bosses'),
             ('target', 'line_auto_targets', all_targets, 'test_no_boss_no_fallback'),
             ('lifetime', '_exec_line', leak, 'test_cast_lifetime_and_no_stacking')]
    for name, attr, fn, test in cases:
        with patch.object(Battle, attr, fn):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(AsherahToughnessTest(test))
        if result.errors or not result.failures:
            raise AssertionError('%s: expected assertion failure, got %r' % (name, result))
        print('detected:', name)


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations()
    else:
        unittest.main()
