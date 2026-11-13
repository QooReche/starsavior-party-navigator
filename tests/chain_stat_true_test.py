"""능력치 고정 연쇄·대상 집합 강인도. 계정 자료 없이 검증, --mutate로 결함 주입."""
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS
from battlesim.starsavior.data import get_db
from battlesim.starsavior.myinfo_combat import select_skills
from battlesim.starsavior.parser import Line, UnitDef, explicit_target
from battlesim.starsavior.mc_semantics import normalized_lines


class ChainStatTrueTest(unittest.TestCase):
    def test_type_survives_every_passive_level(self):
        db = get_db()
        key = 'asherah-order-striker'
        coefs = set()
        for level in range(1, 5):
            raw = select_skills(db.units[key], key, {'skills': {'passive': level}})
            d = UnitDef(db, key, unit_data=raw)
            chains = [ln.eff for ln in normalized_lines(d) if ln.eff['kind'] == 'chain']
            self.assertEqual(len(chains), 4)
            self.assertEqual({e['damage_type'] for e in chains}, {'ADT_STAT_TRUE'})
            coefs.update(e['coef'] for e in chains)
        self.assertEqual(coefs, {0.2, 0.25, 0.3, 1.0, 1.25, 1.5})
        normal = [ln.eff for ln in unit_def('cristelle').lines if ln.eff['kind'] == 'chain']
        self.assertTrue(normal)
        self.assertEqual({e['damage_type'] for e in normal}, {'ADT_NORMAL'})

    def test_generated_types_match_tables(self):
        static = os.environ.get('STARSAVIOR_STATIC')
        if not static:
            self.skipTest('STARSAVIOR_STATIC 없음')
        from tools.build_chain_damage import build
        data = json.loads((ROOT / 'data/chain_damage.json').read_text(encoding='utf8'))
        self.assertEqual(build(static), data['units'])
        self.assertEqual(set(data['units']), {'asherah-order-striker'})

    def test_stat_true_ignores_defense_increase_and_rng(self):
        for side in (0, 1):
            b = battle([unit(atk=1003)], [unit('foe', hp=10**8, atk=1003, df=10**7)],
                       pen=[0.73, 0.73])
            a, f = (b.allies[0], b.foes[0]) if side == 0 else (b.foes[0], b.allies[0])
            give(a, 'increases', {'피해 증가': 100, '방어 관통': 99, '브레이크 대상 피해 증가': 100})
            give(f, 'reduction', {'피해 감소': 99})
            ctx = Ctx(a, a, a.d.skills['기본기'])
            ctx.target, ctx.targets, ctx.inc = f, [f], 2.0
            ctx.local_by[f]['inc'] = 3.0
            eff = dict(target='스킬 대상', stat='atk', coef=0.333, damage_type='ADT_STAT_TRUE')
            state = b.R(side).getstate()
            # 클라는 생성 시 int(1003*.333)=333, 팀 보정 뒤 int(333*.73)=243.
            with patch.object(b, 'rand', side_effect=AssertionError('true damage consumed RNG')):
                b.chain(a, eff, ctx)
            self.assertEqual(f.taken, 243)
            self.assertEqual(b.R(side).getstate(), state)
            self.assertEqual(b.rule_hits['chain_stat_true'], 1)

    def test_legacy_and_normal_use_same_formula(self):
        values = []
        for mode, kind in [('legacy', 'ADT_STAT_TRUE'), ('client', 'ADT_NORMAL'), ('client', 'ADT_STAT_TRUE')]:
            b = battle([unit(atk=1000)], [unit('foe', hp=10**8, df=10000)], mc={'chain_stat_true': mode})
            a, f = b.allies[0], b.foes[0]
            b.chain(a, dict(target='적 전체', stat='atk', coef=1, damage_type=kind), Ctx(a, a, None))
            values.append(f.taken)
        self.assertEqual(values[0], values[1])
        self.assertNotEqual(values[0], values[2])
        self.assertEqual(values[2], 1000)

    def test_stat_true_still_uses_shield(self):
        b = battle([unit(atk=1000)], [unit('foe', hp=10000)])
        a, f = b.allies[0], b.foes[0]
        shield = give(f, 'shield')
        shield.shield = 600
        b.chain(a, dict(target='적 전체', stat='atk', coef=1, damage_type='ADT_STAT_TRUE'), Ctx(a, a, None))
        self.assertEqual(f.hp, 9600)
        self.assertEqual(f.shield_total(), 0)


class TargetToughnessTest(unittest.TestCase):
    def test_not_broken_fallback_has_no_empty_status_filter(self):
        text = '브레이크 상태가 아닌 적 전체'
        self.assertEqual(explicit_target(text)['f'], ['not_broken'])
        b = battle([unit()], [unit('boss'), unit('soldier')], mc={'ally_auto_lines': 'off'})
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        b.foes[0].broken = True
        self.assertEqual(b.resolve(a, text, ctx), [b.foes[1]])
        b.foes[1].broken = True
        self.assertEqual(b.resolve(a, text, ctx), [])

    def condition(self, key):
        return Line(f'[스킬 사용 후] (조건: 내 공격 후 [{key}: 예]) 자신에게 행동 게이지 10%p 증가', '기본기', 'active')

    def test_any_current_toughness_and_empty_set(self):
        b = battle([unit()], [unit('boss', sa=30), unit('soldier', sa=1)])
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.targets, ctx.target = list(b.foes), b.foes[0]
        ln = self.condition('대상 강인도 없음')
        self.assertFalse(b.cond_ok(a, ln, ctx))
        # broken 플래그가 없어도 현재 강인도 0이면 성립한다.
        b.foes[1].sa = 0
        self.assertTrue(b.cond_ok(a, ln, ctx))
        ctx.targets.reverse()
        ctx.target = ctx.targets[0]
        self.assertTrue(b.cond_ok(a, ln, ctx))
        self.assertTrue(b.cond_ok(a, self.condition('대상 강인도 있음'), ctx))
        b.foes[0].sa = 0
        self.assertFalse(b.cond_ok(a, self.condition('대상 강인도 있음'), ctx))
        ctx.targets, ctx.target = [], None
        self.assertTrue(b.cond_ok(a, ln, ctx))
        self.assertTrue(b.cond_ok(a, self.condition('대상 강인도 있음'), ctx))

    def test_soldier_break_grants_stack_cooldown_and_only_soldier_chain(self):
        b = battle([unit_def('asherah-order-striker')],
                   [unit('boss', hp=10**9, sa=30, boss=True), unit('soldier', hp=10**9, sa=1)],
                   opts={'coop': False, 'nova': False})
        a = b.allies[0]
        a.acting = True
        seen = []
        original = b.apply_damage
        def record(src, target, damage, kind, **kw):
            if kind == 'chain':
                seen.append((target.name, damage))
            return original(src, target, damage, kind, **kw)
        with patch.object(b, 'apply_damage', record):
            b.cast(a, a.d.skills['특수기'], target=b.foes[0])
        self.assertGreater(b.progress(), 0)
        self.assertEqual([f.broken for f in b.foes], [False, True])
        self.assertEqual(a.stack('마녀의 성흔(해제불가)'), 1)
        self.assertEqual(a.cd['특수기'], 0)
        self.assertEqual([name for name, _ in seen], ['soldier'])
        self.assertGreater(seen[0][1], 0)
        self.assertEqual(b.rule_hits['chain_stat_true'], 1)
        self.assertFalse(b.unsup, dict(b.unsup))

    def test_single_target_does_not_inspect_unhit_enemy(self):
        b = battle([unit()], [unit('target', sa=3), unit('unhit', sa=0)])
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = b.foes[0], [b.foes[0]]
        self.assertFalse(b.cond_ok(a, self.condition('대상 강인도 없음'), ctx))

    def test_legacy_first_target(self):
        b = battle([unit()], [unit('boss', sa=30), unit('soldier', sa=1)],
                   mc={'target_toughness_condition': 'first'})
        a = b.allies[0]
        b.foes[1].sa, b.foes[1].broken = 0, True
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.targets, ctx.target = list(b.foes), b.foes[0]
        self.assertFalse(b.cond_ok(a, self.condition('대상 강인도 없음'), ctx))


def mutations():
    cases = [('normal formula', ChainStatTrueTest('test_stat_true_ignores_defense_increase_and_rng'),
              patch.dict(MC_OPTS, chain_stat_true='legacy')),
             ('first target', TargetToughnessTest('test_soldier_break_grants_stack_cooldown_and_only_soldier_chain'),
              patch.dict(MC_OPTS, target_toughness_condition='first'))]
    original = Battle.chain
    def drop_type(b, owner, eff, ctx):
        return original(b, owner, dict(eff, damage_type='ADT_NORMAL'), ctx)
    cases.append(('lost type', ChainStatTrueTest('test_stat_true_ignores_defense_increase_and_rng'),
                  patch.object(Battle, 'chain', drop_type)))
    cases.append(('lost target mapping', TargetToughnessTest('test_soldier_break_grants_stack_cooldown_and_only_soldier_chain'),
                  patch('battlesim.mc.ally_auto_lines', return_value={})))
    def empty_status_filter(text):
        spec = explicit_target(text)
        if text == '브레이크 상태가 아닌 적 전체':
            return dict(spec, f=spec['f'] + [['not_has', []]])
        return spec
    cases.append(('empty status filter', TargetToughnessTest('test_not_broken_fallback_has_no_empty_status_filter'),
                  patch('battlesim.mc.explicit_target', empty_status_filter)))
    for name, test, mutation in cases:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(test)
        if result.errors or not result.failures:
            raise AssertionError(f'{name}: expected assertion failure, got {result}')
        print('detected:', name)


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations()
    else:
        unittest.main()
