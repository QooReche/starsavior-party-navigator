"""PC 26752678 support audit regressions. Sources: docs/unsupported_26752678.md.

--mutations disables each correction in memory; assertion failures are required.
"""
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
from battlesim import api, mc as M, web
from battlesim.mc import Battle, Ctx, line_rest, support_report
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS, DEFAULT_OPTS, MC_RULES, RULES
from battlesim.starsavior import marker_se


def setup(key, **modes):
    b = battle([unit_def(key)], [unit('first', hp=10**8), unit('second', hp=10**8)],
               mc=modes, opts={'coop': False, 'nova': False})
    return b, b.allies[0]


def context(a, slot, targets):
    ctx = Ctx(a, a, a.d.skills[slot])
    ctx.targets, ctx.target = targets, targets[0]
    return ctx


class UnsupportedTest(unittest.TestCase):
    def test_smile_10464017_10464021_empty_and_current_markers(self):
        for slot in ('기본기', '궁극기'):
            with self.subTest(slot=slot):
                b, a = setup('sunshine-cat-smile')
                ln = next(x for x in b.lines_of(a) if x.eff['kind'] == 'remove'
                          and x.eff.get('name') == '물폭탄' and dict(x.params).get('사용 스킬') == slot)
                ctx = context(a, slot, b.foes)
                for x in b.foes:
                    give(x, '물폭탄', harmful=True)
                b.exec_line(a, ln, ctx)
                self.assertTrue(all(x.has('물폭탄') for x in b.foes))
                self.assertFalse(b.unsup)
                give(b.foes[1], marker_se.OLD, harmful=True)
                b.exec_line(a, ln, ctx)
                self.assertEqual([x.has('물폭탄') for x in b.foes], [True, False])
                self.assertFalse(b.unsup)

    def test_gille_10201012_10202015_preserve_empty_filter(self):
        name = '길레 마지막 타격 체크용 버프'
        for slot in ('기본기', '특수기'):
            with self.subTest(slot=slot):
                b, a = setup('gille')
                ln = next(x for x in b.lines_of(a) if x.slot == slot and x.eff['kind'] == 'remove'
                          and x.eff.get('name') == name)
                ctx = context(a, slot, b.foes[:1])
                spec = b.line_spec(a, ln)
                self.assertEqual(spec, {'one': False, 'f': [['has', [name]]]})
                self.assertEqual(b.line_auto_targets(a, spec, ctx), [])
                b.exec_line(a, ln, ctx)
                self.assertFalse(b.unsup)
                # Current holders outside caster.TargetUid are also removed.
                for x in b.foes:
                    give(x, name, harmful=True)
                b.exec_line(a, ln, ctx)
                self.assertFalse(any(x.has(name) for x in b.foes))
                self.assertFalse(b.unsup)

    def test_marker_unrelated_scope(self):
        # Other U1 retains its previous line_spec contract.
        for _ in (0,):
            b, a = setup('lyn')
            ln = next(x for x in b.lines_of(a) if x.eff.get('name') == '치명타 피해 증가')
            self.assertIsNone(b.line_spec(a, ln))

    def test_claire_16093014_flag_lifetime_and_category(self):
        b, a = setup('bunny-claire@개화(SSR)')
        ln = next(x for x in b.lines_of(a) if x.eff.get('name') == '선제 방어 무시')
        ctx = context(a, '궁극기', b.foes[:1])
        guard = b.foes[1]
        give(guard, 'guard', {'선제 방어 확률': 100})
        # Remove the independent skill-level NoPreemptiveDefend bypass so this
        # test proves the buff flag itself works (NKM:9019, not 9025).
        flags = dict(M.no_preemptive(), skills={})
        with patch.object(M, 'no_preemptive', return_value=flags):
            self.assertEqual(b._preemptive_check(a, ctx.targets, ctx), [guard])
            # IsBuff=false / IsPositive=true passes both bans (NKM:4389-4398).
            give(a, '강화 불가', harmful=True)
            give(a, '면역')
            before = a.n_good()
            b.exec_line(a, ln, ctx)
            self.assertTrue(a.has('선제 방어 무시'))
            self.assertEqual(a.n_good(), before)
            self.assertEqual(a.eff['선제 방어 무시'].category, 'marker')
            self.assertEqual(b._preemptive_check(a, ctx.targets, ctx), ctx.targets)
            b._expire_checks(skill=True)
            self.assertFalse(a.has('선제 방어 무시'))
            self.assertEqual(b._preemptive_check(a, ctx.targets, ctx), [guard])
        self.assertFalse(support_report([unit_def('bunny-claire@개화(SSR)')]))

    def test_random_buff_three_forms_equal_candidates(self):
        # NKM:16468-16477 AddCase(10000, item). All three use BuffCount=1.
        # Scarlet's three SEs each make a new draw, so duplicates are allowed.
        for key, names, times in (
            ('scarlet', ['노멀볼(해제불가)', '세븐볼(해제불가)'], 3),
            ('vera', ['공격력 증가', '방어력 증가', '속도 증가', '지속 회복'], 1),
            ('vera@개화(SSR)', ['공격력 증가', '방어력 증가', '속도 증가', '지속 회복'], 1)):
            with self.subTest(key=key):
                b, a = setup(key)
                ln = next(x for x in b.lines_of(a) if '무작위 효과' in x.raw)
                ctx = context(a, '궁극기', b.foes[:1])
                seen = []
                def choose(pool):
                    self.assertEqual(pool, names)
                    return pool[-1]
                with patch.object(b, 'resolve', return_value=[a]), \
                     patch.object(b.R(0), 'choice', side_effect=choose) as draw, \
                     patch.object(b, 'add_effect', side_effect=lambda owner, target, eff, *args, **kw: seen.append(eff['name'])):
                    b._run_special_rest(a, ln, ctx, line_rest(ln))
                self.assertEqual(draw.call_count, times)
                self.assertEqual(seen, [names[-1]] * times)
        self.assertEqual(MC_RULES['random_buff_draw']['grade'], 'code')
        self.assertNotIn('model.random_choice', {x['rule'] for x in api.assumptions_used(MC_OPTS, DEFAULT_OPTS)})

    def test_assumptions_filter_all_rule_sections(self):
        out = api.assumptions_used(MC_OPTS, DEFAULT_OPTS)
        self.assertTrue(out)
        self.assertFalse(any(x['grade'] in ('code', 'data') for x in out))
        self.assertTrue(any(x['grade'] == 'assumed' for x in out))
        self.assertNotIn('선제 방어(', next(x['note'] for x in out if x['rule'] == 'model.effect_mapping'))
        for section, prefix in ((MC_RULES, 'mc.'), (RULES['mc']['break_skills'], 'mc.break_skills.'),
                                ({k: RULES['opts'][k] for k in ('coop_order', 'nova_policy')}, 'opts.')):
            for key, rule in section.items():
                if rule.get('grade') in ('code', 'data'):
                    self.assertNotIn(prefix + key, {x['rule'] for x in out})

    def test_runtime_approximation_reaches_api_and_web(self):
        original = Battle.run
        calls = []
        def recorded(b):
            result = original(b)
            b.unsup['selector: injected runtime approximation'] += 1
            calls.append(1)
            return result
        party = ['gwen', 'amora', 'frey', 'claire']
        opts = {'n_runs': 2, 'build': 'standard', 'seed': 19}
        with patch.object(Battle, 'run', recorded):
            r = api.simulate(party, {'stage': 'clo/달 회랑/FLOOR 100'}, opts)
            self.assertGreater(r['outcome']['progress'], 0)
            u = r['unsupported']
            self.assertFalse(u['critical'])
            self.assertFalse(u['gate_ok'])
            self.assertTrue(u['runtime_approx'])
            self.assertEqual(u['runs_affected'], 2)
            self.assertEqual(sum(u['runtime'].values()), 2)
            import json
            w = json.loads(web.run_auto('clo/달 회랑/FLOOR 100', {'units': party}, 1, 19, {'build': 'standard'}))
            self.assertFalse(w['gate'])
        self.assertEqual(len(calls), 3)
        clean = api.simulate(party, {'stage': 'clo/달 회랑/FLOOR 100'}, dict(opts, n_runs=1))
        self.assertTrue(clean['unsupported']['gate_ok'])
        self.assertFalse(clean['unsupported']['runtime_approx'])


def mutated(owner, method, old, new):
    fn = getattr(owner, method)
    source = textwrap.dedent(inspect.getsource(fn))
    assert old in source, (method, old)
    scope = {}
    exec(source.replace(old, new, 1), fn.__globals__, scope)
    return patch.object(owner, method, scope[method])


def mutations():
    checks = [
        ('smile native filter removed', 'test_smile_10464017_10464021_empty_and_current_markers',
         mutated(marker_se, 'targets', "selected = [x for x in pool if x.has(name) != ('not_has' in kind)]", 'selected = list(pool)')),
        ('gille plural empty selects all', 'test_gille_10201012_10202015_preserve_empty_filter',
         patch.object(Battle, 'line_auto_targets', lambda b, owner, spec, ctx: b.alive(1 - owner.side))),
        ('unrelated native scope leak', 'test_marker_unrelated_scope',
         mutated(Battle, 'line_spec', "(owner.key == 'sunshine-cat-smile' and ln.eff.get('native_target'))", "ln.eff.get('native_target')")),
        ('claire flag removed', 'test_claire_16093014_flag_lifetime_and_category',
         mutated(Battle, '_preemptive_check', "if any(attacker.on(name) for name in rule['buffs']):", 'if False:')),
        ('claire lifetime removed', 'test_claire_16093014_flag_lifetime_and_category',
         mutated(marker_se, 'apply_hidden', 'b.check_pending.append((x, name))', 'pass')),
        ('random choice biased', 'test_random_buff_three_forms_equal_candidates',
         mutated(Battle, '_run_special_rest', 'self.R(owner.side).choice(names)', 'names[0]')),
        ('assumption code included', 'test_assumptions_filter_all_rule_sections',
         patch.object(api, 'ASSUMPTION_GRADES', api.ASSUMPTION_GRADES | {'code'})),
        ('runtime gate ignored', 'test_runtime_approximation_reaches_api_and_web',
         mutated(api, '_simulate', 'gate_ok=not crit_lines and not runtime', 'gate_ok=not crit_lines')),
    ]
    for label, method, mutation in checks:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(UnsupportedTest(method))
        expected = 2 if label.startswith(('smile ', 'gille ')) else 3 if label == 'random choice biased' else 1
        if result.errors or len(result.failures) != expected:
            raise AssertionError((label, 'must fail by assertion', result.errors))
        print('mutation caught:', label, 'assertions:', len(result.failures))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main(verbosity=2)
