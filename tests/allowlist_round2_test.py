"""PC 26752678: HIT/EVADE and lifecycle/guard precision regressions."""
import inspect
import io
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, Ctx, buff_flags
from battlesim.starsavior.parser import Line
from battlesim.starsavior import hit_stats
from battlesim.starsavior.foe import load_foe, FoeDef


class Round2Test(unittest.TestCase):
    def test_public_hit_mapping_and_nondefault_loader(self):
        raw = load_foe()
        keys = {hit_stats.signature(u['n'], u['b']) for u in raw['u']}
        self.assertEqual(keys - hit_stats.data().keys(), set())
        key = hit_stats.signature(raw['u'][0]['n'], raw['u'][0]['b'])
        with patch.dict(hit_stats.data(), {key: [13000, 700]}):
            d = FoeDef(raw, 0)
            self.assertEqual((d.stats['hit'], d.stats['evade']), (13000, 700))
            b = battle([unit('target')], [d])
            give(b.allies[0], '회피', {'회피율': 40})
            ctx = Ctx(b.foes[0], b.foes[0], d.skills['기본기'])
            self.assertAlmostEqual(b.evade_rate(b.foes[0], b.allies[0], ctx), .1)

    def test_split_model_assumptions(self):
        from battlesim.api import assumptions_used
        from battlesim.rules import MC_OPTS, DEFAULT_OPTS
        rows = {r['rule']: r for r in assumptions_used(MC_OPTS, DEFAULT_OPTS)}
        self.assertNotIn('mc.evade_model', rows)
        self.assertNotIn('model.not_modeled', rows)
        self.assertTrue({'model.effect_mapping', 'model.chain_timing', 'model.season_inputs'} <= rows.keys())
        self.assertIn('BuffId', rows['model.chain_timing']['note'])

    def test_base_hit_and_force_flags(self):
        b = battle([unit('target')], [unit('boss', hit=13000)])
        a, v = b.foes[0], b.allies[0]
        give(v, '회피', {'회피율': 20})
        ctx = Ctx(a, a, a.d.skills['기본기'])
        self.assertEqual(b.evade_rate(a, v, ctx), 0)
        b.mc['evade_model'] = 'rate_minus_acc'
        self.assertAlmostEqual(b.evade_rate(a, v, ctx), .2)
        b.mc['evade_model'] = 'client'
        give(v, '강제 회피')
        self.assertEqual(b.evade_rate(a, v, ctx), 1)
        give(a, '필중')
        self.assertEqual(b.evade_rate(a, v, ctx), 0)  # both flags: roll normal stats
        give(v, '회피', {'회피율': 60})
        self.assertAlmostEqual(b.evade_rate(a, v, ctx), .3)
        del v.eff['강제 회피']; b.dirty(v)
        self.assertEqual(b.evade_rate(a, v, ctx), 0)
        del a.eff['필중']; b.dirty(a)
        ctx.acc = .2
        self.assertAlmostEqual(b.evade_rate(a, v, ctx), .1)

    def test_hit_evade_nonnegative_final_stats(self):
        b = battle([unit('target')], [unit('boss', hit=7000)])
        a, v = b.foes[0], b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        give(v, '회피 감소', {'회피율': -50})
        self.assertAlmostEqual(b.evade_rate(a, v, ctx), .3)
        a.d.stats['hit'] = -2000
        self.assertEqual(b.evade_rate(a, v, ctx), 1)

    def test_evade_damage_and_debuff_integration(self):
        for mode in ('rate_minus_acc', 'client'):
            b = battle([unit('target')], [unit('boss', hit=13000)], mc={'evade_model': mode})
            a, v = b.foes[0], b.allies[0]
            a.d.lines = [Line('[스킬 사용 후] 스킬 대상에게 〈공격력 감소〉 (2턴 / 공격력% -20%)', '기본기', 'active')]
            give(v, '회피', {'회피율': 30})
            with patch.object(b.R(1), 'random', return_value=.05):
                ctx = b.cast(a, a.d.skills['기본기'], target=v)
            self.assertEqual(v in ctx.evaded, mode != 'client')
            self.assertEqual(v.has('공격력 감소'), mode == 'client')
            self.assertGreater(v.taken, 0)
            if mode == 'client':
                self.assertGreater(b.rule_hits['evade_model'], 0)

    def test_revived_spawn_cooldowns_before_after_spawn(self):
        b = battle([unit('ally')], [unit('reviver'), unit('spawn', skills=[
            dict(slot='기본기', dm=100), dict(slot='특수기', dm=100, cd=4), dict(slot='궁극기', dm=100, cd=6)])])
        a, v = b.foes
        v.d.spawn = 'S'
        b.kill(v, b.allies[0])
        v.cd.update(특수기=3, 궁극기=2)
        v.d.lines = [Line('[등장 후] 자신에게 〈관측〉 (1턴)', '고유 패시브', 'passive')]
        seen = []
        original = b.run_line
        def observe(owner, ln, ctx):
            if ln.phase == '등장 후': seen.append(dict(owner.cd))
            return original(owner, ln, ctx)
        ctx = Ctx(a, a, a.d.skills['기본기']); ctx.target, ctx.targets = v, [v]
        with patch.object(b, 'run_line', observe):
            b.run_line(a, Line('[스킬 사용 후] 스킬 대상에게 부활(생명력 50%)', '기본기', 'active'), ctx)
        self.assertEqual(seen[0]['특수기'], 0)
        self.assertEqual(seen[0]['궁극기'], 6)
        self.assertGreater(v.hp, 0)

    def test_all_aggro_flag_effects_cleanup(self):
        b = battle([unit('ally')], [unit('caster'), unit('foe')])
        a, caster = b.allies[0], b.foes[0]
        give(a, '다른 이름의 도발', src=caster, harmful=True)
        give(a, '일반 약화', src=caster, harmful=True)
        b.kill(caster, a)
        flags = dict(buff_flags(), cc=dict(buff_flags()['cc'], aggro={'effects': ['도발', '다른 이름의 도발'], 'immune': []}))
        with patch('battlesim.mc.buff_flags', return_value=flags):
            b.cast(a, a.d.skills['기본기'])
        self.assertFalse(a.has('다른 이름의 도발'))
        self.assertTrue(a.has('일반 약화'))

    def test_guard_over_100_and_fixed_fraction(self):
        b = battle([unit('target'), unit('guard')], [unit('foe')])
        v, g = b.allies
        give(g, '수호', {'피해 분담(수호)': 125})
        b.fixed_true_damage(b.foes[0], v, 101)
        self.assertEqual(g.taken, 126)
        self.assertEqual(b._chain_guard(v, 101)[1], 126.25)
        self.assertEqual(v.taken, 1)

    def test_heal_fallback_is_counted_only_when_used(self):
        b = battle([unit('a'), unit('b')], [unit('foe')])
        a, v = b.allies
        v.hp = 100
        ctx = Ctx(a, a, a.d.skills['기본기'])
        self.assertEqual(b.resolve(a, '아군 1명', ctx, 'heal'), [v])
        self.assertEqual(b.rule_hits['heal_target_fallback'], 1)
        self.assertEqual(b.resolve(a, '아군 전체', ctx, 'heal'), [a, v])
        self.assertEqual(b.rule_hits['heal_target_fallback'], 1)


def mutations():
    cases = [
        ('evade_rate', "a.d.stats.get('hit', 10000)", '10000', 'test_base_hit_and_force_flags'),
        ('evade_rate', 'if force_hit != force_evade:', 'if force_hit or force_evade:', 'test_base_hit_and_force_flags'),
        ('evade_rate', "max(0, math.floor(v.d.stats.get('evade', 0) + v.mods()['evade'] * 10000))", "math.floor(v.d.stats.get('evade', 0) + v.mods()['evade'] * 10000)", 'test_hit_evade_nonnegative_final_stats'),
        ('deal', 'self.evade_rate(a, v, ctx)', '0.5', 'test_evade_damage_and_debuff_integration'),
        ('run_special', 'x.reset_initial_cooldowns()', 'None', 'test_revived_spawn_cooldowns_before_after_spawn'),
        ('cast', "buff_flags()['cc']['aggro']['effects']", "['도발']", 'test_all_aggro_flag_effects_cleanup'),
        ('fixed_true_damage', 'damage * self.guard_share(share)', 'damage * min(1.0, share)', 'test_guard_over_100_and_fixed_fraction'),
        ('fixed_true_damage', 'max(1, int(value))', 'max(1, value)', 'test_guard_over_100_and_fixed_fraction'),
        ('resolve', "self.rule_hits['heal_target_fallback'] += 1", 'pass', 'test_heal_fallback_is_counted_only_when_used'),
    ]
    for method, old, new, test in cases:
        original = getattr(Battle, method)
        source = textwrap.dedent(inspect.getsource(original))
        assert old in source, (method, old)
        ns = {}; exec(source.replace(old, new), original.__globals__, ns)
        run = lambda: unittest.TextTestRunner(stream=io.StringIO()).run(Round2Test(test))
        assert run().wasSuccessful(), test
        with patch.object(Battle, method, ns[method]): result = run()
        assert result.failures and not result.errors, (test, result.errors)
        print(test, 'mutation rejected')
    original = hit_stats.rates
    with patch.object(hit_stats, 'rates', return_value=(10000, 0)):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(Round2Test('test_public_hit_mapping_and_nondefault_loader'))
    assert result.failures and not result.errors
    assert hit_stats.rates is original
    print('nondefault loader mutation rejected')


if __name__ == '__main__':
    if '--mutations' in sys.argv: mutations()
    else: unittest.main()
