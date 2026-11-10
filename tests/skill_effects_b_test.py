# -*- coding: utf-8 -*-
"""구원자 효과 B: 실제 시전·조건·대상 분산 및 표준 육성 경로 검사.

python -X utf8 -I tests/skill_effects_b_test.py
python -X utf8 -I tests/skill_effects_b_test.py --mutations
python -X utf8 -I tests/skill_effects_b_test.py --ab
"""
import collections
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from simkit import battle, give, unit
from battlesim.api import simulate
from battlesim.mc import Battle, Ctx, ally_auto_lines, normalized_lines
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS
from battlesim.starsavior.data import get_db

SNOW = '설중화(해제불가)'
STATE = '급급여율령(해제불가)'
NOVA = '기본기2 피해 증가 중첩'
THORN = '참극의 가시(해제불가)'


def setup(key, seed=3, **rules):
    b = battle([unit_def(key)], [unit('one', hp=10**9, sa=1000),
                               unit('two', hp=10**9, sa=1000)], mc=rules, seed=seed)
    b.allies[0].acting = True
    return b, b.allies[0]


def measured(party, stage, runs=2, **rules):
    """효과를 바꾸지 않고 실제로 실행된 시전/중첩 해제/줄을 센다."""
    counts = collections.Counter()
    cast, execute = Battle.cast, Battle.exec_line

    def watch_cast(b, u, sk, *args, **kwargs):
        ctx = cast(b, u, sk, *args, **kwargs)
        if ctx is not None and ctx.skill.name == '제압부·참':
            counts['variant_casts'] += 1
        return ctx

    def watch_line(b, owner, ln, ctx):
        before = owner.has(STATE)
        result = execute(b, owner, ln, ctx)
        if owner.key == 'lugh':
            if before and not owner.has(STATE):
                counts['state_removals'] += 1
            if ln.eff['kind'] == 'gauge' and ('자신이 미보유', STATE) in ln.params:
                counts['gauge_lines'] += 1
        if any(k == 'TurnUnitNegativeBuff' for k, _ in ln.params):
            counts['debuff_lines'] += 1
        if ln.eff.get('auto_marker_candidate'):
            counts['marker_lines'] += 1
        return result

    with patch.object(Battle, 'cast', watch_cast), patch.object(Battle, 'exec_line', watch_line):
        r = simulate(party, {'stage': stage}, dict(seed=3, n_runs=runs, build='standard', rules_override=rules))
    return dict(outcome=r['outcome'], counts=dict(counts), ally_via=r['ally_via'])


class LughTest(unittest.TestCase):
    def test_cycle(self):
        b, u = setup('lugh')
        give(u, SNOW, stacks=2)
        give(u, STATE)
        give(u, '노바 버스트 발동 확인용 버프')
        give(u, NOVA).maxs = 3
        ctx = b.cast(u, u.d.skills['기본기'])
        self.assertEqual(ctx.skill.name, '제압부·참')
        self.assertEqual(u.stack(SNOW), 1)
        self.assertTrue(u.has(STATE))
        self.assertEqual(u.stack(NOVA), 2)
        self.assertAlmostEqual(ctx.inc, .5)  # 변형 20% + 노바 비례 2중첩 30%
        self.assertEqual(u.stack('냉각'), 0)
        self.assertTrue(ctx.target.has('파사인'))
        b.cast(u, u.d.skills['기본기'])
        self.assertEqual(u.stack(SNOW), 0)
        self.assertFalse(u.has(STATE))
        self.assertFalse(u.has(NOVA))
        ctx = b.cast(u, u.d.skills['기본기'])
        self.assertEqual(ctx.skill.name, '제압부')
        self.assertEqual(u.stack('냉각'), 1)
        b.cast(u, u.d.skills['궁극기'])
        self.assertEqual(u.stack(SNOW), 1)  # 일반 부여가 감소로 바뀌면 안 됨

    def test_legacy_extra_and_not_own(self):
        for rules, acting, extra in [({'variant_self_state': 'off'}, True, False),
                                     ({}, True, True), ({}, False, False)]:
            with self.subTest(rules=rules, acting=acting, extra=extra):
                b, u = setup('lugh', **rules)
                u.acting = acting
                give(u, SNOW, stacks=2)
                give(u, STATE)
                ctx = b.cast(u, u.d.skills['기본기'], extra=extra)
                self.assertEqual(ctx.skill.name, '제압부')
                self.assertEqual(u.stack(SNOW), 2)
                self.assertTrue(u.has(STATE))

    def test_nova_damage_and_reset(self):
        b, u = setup('lugh')
        b.opts['nova_policy'] = 'manual'
        b.mc['manual_burst'] = 'any_attack'
        give(u, SNOW, stacks=3)
        give(u, STATE)
        for count, bonus in enumerate((.1, .3, .6), 1):
            b.nova_add(u, 4)
            ctx = b.cast(u, u.d.skills['기본기'])
            self.assertTrue(ctx.nb)
            self.assertAlmostEqual(ctx.inc, .15 + .2 + bonus)
            self.assertEqual(u.stack(NOVA), count if count < 3 else 0)
            b.fire(u, 'own_te', Ctx(u, u, None))
            self.assertFalse(u.has('노바 버스트 발동 확인용 버프'))
        self.assertFalse(u.has(STATE))
        # 노바를 쓰지 않은 변형 시전은 이전 중첩을 지운 뒤 피해를 판정한다.
        give(u, SNOW, stacks=3)
        give(u, STATE)
        give(u, NOVA, stacks=3).maxs = 3
        b.opts['nova_policy'] = 'auto'
        ctx = b.cast(u, u.d.skills['기본기'])
        self.assertAlmostEqual(ctx.inc, .2)
        self.assertFalse(u.has(NOVA))

    def test_existing_variants_survive_legacy(self):
        for key, slot, name, stacks in [('lyn', '궁극기', '명월(해제불가)', 1),
                                        ('bunny-frey', '기본기', '하이 롤러(해제불가)', 5)]:
            b, u = setup(key, variant_self_state='off')
            give(u, name, stacks=stacks).maxs = stacks
            ctx = b.cast(u, u.d.skills[slot])
            self.assertIsNot(ctx.skill, u.d.skills[slot])

    def test_live_cycle(self):
        r = measured(['lugh', 'emily', 'hilde', 'ceres-sun-supporter'], 'clo/달 회랑/FLOOR 100')
        self.assertGreater(r['outcome']['progress'], 0)
        for key in ('variant_casts', 'state_removals', 'gauge_lines'):
            self.assertGreater(r['counts'].get(key, 0), 0, r)


class CeresTest(unittest.TestCase):
    def test_turn_unit_debuff(self):
        for mode in (None, 'skip'):
            b = battle([unit_def('ceres-sun-supporter'), unit('ally')], [unit(hp=10**9)],
                       mc={} if mode is None else {'turn_unit_debuff_cond': mode})
            u, ally = b.allies
            u.eff.clear()
            ln, = [ln for ln in b.lines_of(u) if any(k == 'TurnUnitNegativeBuff' for k, _ in ln.params)]
            self.assertFalse(b.cond_ok(u, ln, Ctx(u, None, None)))
            give(u, '자신만 약화', harmful=True)
            b.fire(u, 'ally_ts', Ctx(u, ally, None))
            self.assertEqual(u.stack('점화'), 0)
            give(ally, '턴 유닛 약화', harmful=True)
            b.fire(u, 'ally_ts', Ctx(u, ally, None))
            self.assertEqual(u.stack('점화'), 1 if mode is None else 0)
            if mode is None:
                self.assertNotIn('cond: TurnUnitNegativeBuff', b.unsup)
                # 실제 자기 턴 배포는 ally_ts를 자기 자신에게 호출하지 않는다.
                with patch.object(b, 'fire', wraps=b.fire) as fire:
                    b.act(u)
                self.assertFalse(any(c.args[0] is u and c.args[1] == 'ally_ts' for c in fire.call_args_list))

    def test_check_marker_is_not_debuff(self):
        b = battle([unit_def('ceres-sun-supporter'), unit('ally')], [unit(hp=10**9)])
        u, ally = b.allies
        u.eff.clear()
        give(ally, '체크 표지', harmful=True).check = True
        b.fire(u, 'ally_ts', Ctx(u, ally, None))
        self.assertEqual(u.stack('점화'), 0)

    def test_live_debuff(self):
        r = measured(['emily', 'waltz-asherah', 'hilde', 'ceres-sun-supporter'], 'clo/달 회랑/FLOOR 100')
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertGreater(r['counts'].get('debuff_lines', 0), 0, r)


class TyriaTest(unittest.TestCase):
    def distribution(self, mode=None, unequal=False):
        selected = collections.Counter()
        for seed in range(40):
            b, u = setup('tyria', seed=seed, **({} if mode is None else {'auto_marker_lines': mode}))
            if unequal:
                give(b.foes[1], '방어력 시험', props={'방어력%': 100})
            b.cast(u, u.d.skills['궁극기'])
            levels = [v.stack(THORN) for v in b.foes]
            self.assertEqual(sorted(levels), [1, 3])
            if mode != 'drop':
                self.assertFalse(any('표지 보유자 없음' in key for key in b.unsup), b.unsup)
            selected[levels.index(3)] += 1
        return selected

    def test_ties_random(self):
        counts = self.distribution()
        self.assertGreaterEqual(counts[0], 10)
        self.assertGreaterEqual(counts[1], 10)

    def test_legacy_and_unique_max(self):
        self.assertEqual(self.distribution('drop'), {0: 40})
        for mode in ('keep', 'drop'):
            self.assertEqual(self.distribution(mode, unequal=True), {1: 40})

    def test_automatic_mapping_scope(self):
        changed = set()
        for key in get_db().units:
            d = unit_def(key)
            for ln in normalized_lines(d):
                if not ln.eff.get('auto_marker_candidate'):
                    continue
                rows = ally_auto_lines(variants=True, client=True).get(key, {})
                if any(isinstance(f, list) and f[0] == 'has' and ln.eff['name'] in f[1]
                       for spec in rows.values() for f in spec['f']):
                    changed.add((key, ln.eff['name']))
        self.assertEqual(changed, {('tyria', '티리아 체크용 버프')})

    def test_live_marker(self):
        r = measured(['tyria', 'emily', 'hilde', 'ceres-sun-supporter'], 'clo/태양 회랑/FLOOR 200')
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertGreater(r['counts'].get('marker_lines', 0), 0, r)


def mutation_check():
    cases = [('variant_self_state', 'off', LughTest, ['test_cycle', 'test_nova_damage_and_reset', 'test_live_cycle']),
             ('turn_unit_debuff_cond', 'skip', CeresTest, ['test_turn_unit_debuff', 'test_live_debuff']),
             ('auto_marker_lines', 'drop', TyriaTest, ['test_ties_random', 'test_live_marker'])]
    for key, value, cls, names in cases:
        with patch.dict(MC_OPTS, {key: value}):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite(cls(n) for n in names))
        assert len(result.failures) == len(names) and not result.errors, (key, result.failures, result.errors)
        print('%s=%s: %d/%d개 시험 실패 확인' % (key, value, len(result.failures), len(names)))


def ab_report():
    party = ['lugh', 'emily', 'hilde', 'ceres-sun-supporter']
    for floor in (100, 250):
        for mode in ('off', 'client'):
            r = measured(party, 'clo/달 회랑/FLOOR %d' % floor, runs=24, variant_self_state=mode)
            assert r['outcome']['progress'] > 0, r
            print(json.dumps(dict(floor=floor, mode=mode, runs=24, party=party, **r), ensure_ascii=False))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutation_check()
    elif '--ab' in sys.argv:
        ab_report()
    else:
        unittest.main()
