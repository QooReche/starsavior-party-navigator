"""26752678 PC 자동 대상 불일치 12 SE. 공개 스킬 + 합성 상태, --mutate 지원."""
import io
import inspect
import sys
import textwrap
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.api import _norm_party
from battlesim.mc import Battle, Ctx, ally_auto_lines, line_rest, RX_HEAL, RX_SHIELD
from battlesim.metrics import get_db


LEGACY = dict(auto_unable_break='legacy', auto_remove_filter='legacy',
              auto_se_reselect='legacy', auto_hp_float32='legacy', auto_empty_marker='legacy')
MARK = '표본 행동 분석 대상 체크용 버프'


def selected(key, **skills):
    return _norm_party([dict(key=key, build='none', stats_final=True,
        stats_override=dict(hp=100000, atk=1000, spd=100, cr=0, cd=5000, eh=10000, er=0, **{'def': 100}),
        myinfo_combat=dict(skills=skills, potentials=[]))],
        get_db(), 'fixed', 'standard', {})[0][0]


def setup(key, slot, needle, **skills):
    b = battle([selected(key, **skills), unit('a', hp=5000, atk=5000, element='태양'),
                unit('b', hp=100000, atk=5000, element='태양')],
               [unit('low', hp=10**8, df=100), unit('high', hp=10**8, df=900)], seed=17)
    a = b.allies[0]
    rows = ally_auto_lines(variants=True, client=True)[key]
    ln = next(x for x in b.lines_of(a) if x.slot == slot and needle in x.raw and (x.slot, x.raw) in rows)
    b._cur_line = ln
    c = Ctx(a, a, a.d.skills.get(slot) or a.d.skills['기본기'])
    c.target, c.targets = b.foes[0], list(b.foes)
    return b, a, ln, c


class AutoTarget12(unittest.TestCase):
    def professor(self, needle):
        b, a, ln, c = setup('professor-m', '고유 패시브', needle, passive=1)
        good, broken = b.allies[1:]
        good.d.stats['atk'], broken.d.stats['atk'] = 100, 500
        broken.broken = True
        give(broken, MARK)
        self.assertEqual(b.resolve(a, ln.eff['target'], c), [good])
        b._exec_line(a, ln, c)
        if ln.eff['name'] == '강제 협공':
            self.assertEqual(b._forced_coop_candidates, {good})
        else:
            self.assertTrue(good.has(ln.eff['name']))
        self.assertGreater(b.rule_hits['auto_unable_break'], 0)

    def test_10394011_professor_marker_excludes_break(self):
        self.professor('〈표본 행동 분석 대상 체크용 버프〉')

    def test_10394013_professor_analysis_excludes_break(self):
        self.professor('〈표본 행동 분석〉')

    def test_10394014_professor_coop_excludes_break(self):
        self.professor('〈강제 협공〉')

    def test_10394012_remove_preserves_selected_analysis(self):
        b, a, ln, c = setup('professor-m', '고유 패시브', "'표본 행동 분석' 해제", passive=1)
        selected_unit = b.allies[1]
        for v in b.allies:
            give(v, '표본 행동 분석', dur=7)
        give(selected_unit, MARK)
        original = selected_unit.eff['표본 행동 분석']
        self.assertCountEqual(b.resolve(a, ln.eff['target'], c, kind='remove'), [a, b.allies[2]])
        b._exec_line(a, ln, c)
        self.assertIs(selected_unit.eff['표본 행동 분석'], original)
        self.assertEqual(original.dur, 7)
        self.assertFalse(a.has('표본 행동 분석'))
        self.assertFalse(b.allies[2].has('표본 행동 분석'))
        # 복수 필터 전 실패 = 빈 대상; 해제 경로에서 전체로 되돌리지 않음.
        for v in b.allies:
            give(v, MARK)
        self.assertEqual(b.resolve(a, ln.eff['target'], c, kind='remove'), [])

    def harley(self, index):
        b, a, ln, c = setup('harley', '특수기', '〈점화〉', special=1)
        x, y = b.allies[1:]
        self.assertEqual(ln.eff['times'], 3)
        # 각 독립 SE의 호출 순서까지 확인. 첫 SE 결과를 재사용하면 2·3번째 실패.
        order = [x, y, x]
        with patch.object(b.R(0), 'choice', side_effect=order) as choose, \
                patch.object(b, 'add_effect', wraps=b.add_effect) as apply:
            b._exec_line(a, ln, c)
        self.assertEqual(choose.call_count, 3)
        self.assertIs(apply.call_args_list[index].args[1], order[index])
        self.assertEqual([call.args[2]['times'] for call in apply.call_args_list], [1, 1, 1])
        self.assertEqual([x.stack('점화'), y.stack('점화')], [2, 1])

    def test_10412012_harley_first_se(self):
        self.harley(0)

    def test_10412013_harley_second_se(self):
        self.harley(1)

    def test_10412014_harley_third_se(self):
        self.harley(2)

    def test_harley_ties_distribute_independently(self):
        b, a, ln, c = setup('harley', '특수기', '〈점화〉', special=1)
        x, y = b.allies[1:]
        counts = Counter()
        for _ in range(800):
            x.eff.clear()
            y.eff.clear()
            b.dirty(x)
            b.dirty(y)
            b._exec_line(a, ln, c)
            counts[x.stack('점화')] += 1
            self.assertEqual(x.stack('점화') + y.stack('점화'), 3)
        for n, probability in enumerate((.125, .375, .375, .125)):
            self.assertAlmostEqual(counts[n] / 800, probability, delta=.06)

    def hp_row(self, key, slot, needle, **skills):
        b, a, ln, c = setup(key, slot, needle, **skills)
        x, y = b.allies[1:]
        x.hp, y.hp = 3900, 77995
        self.assertEqual((x.maxhp, y.maxhp), (5000, 100000))
        give(y, '보호막').shield = 10**8
        match = RX_HEAL.match(line_rest(ln)) or RX_SHIELD.match(line_rest(ln))
        target = match.group(1) if match else ln.eff['target']
        self.assertEqual(b.resolve(a, target, c), [x])
        hp_before = x.hp
        b._exec_line(a, ln, c)
        if RX_HEAL.match(line_rest(ln)):
            self.assertGreater(x.hp, hp_before)
        else:
            self.assertTrue(x.has(ln.eff.get('name', '보호막')))
        self.assertEqual(y.hp, 77995)
        self.assertGreater(b.rule_hits['auto_hp_float32'], 0)

    def test_10192013_serpang_heal_float32(self):
        self.hp_row('serpang', '특수기', '회복 =', special=1)

    def test_10193013_serpang_nullifier_float32(self):
        self.hp_row('serpang', '궁극기', '〈스킬 피해 무효〉', ultimate=1)

    def test_10544021_waltz_heal_float32(self):
        self.hp_row('waltz-asherah', '고유 패시브', '회복 =', passive=2)

    def test_16012013_bloom_besta_shield_float32(self):
        self.hp_row('besta@개화(SSR)', '특수기', '〈보호막〉', special=1)

    def test_10253015_tyria_absent_marker_random(self):
        b, a, ln, c = setup('tyria', '궁극기', '〈참극의 가시', ultimate=1)
        counts = Counter()
        for _ in range(1000):
            counts[b.resolve(a, ln.eff['target'], c)[0].name] += 1
        self.assertAlmostEqual(counts['low'] / 1000, .5, delta=.06)
        self.assertFalse(any('설명문 근사' in k for k in b.unsup))
        give(b.foes[0], '티리아 체크용 버프')
        for _ in range(20):
            self.assertEqual(b.resolve(a, ln.eff['target'], c), [b.foes[0]])

    def test_tyria_repeat_stops_after_failed_iteration(self):
        # SE10253015 RepeatBuffCount=2, NKM:16396-16404.
        b, a, ln, c = setup('tyria', '궁극기', '〈참극의 가시', ultimate=1)
        self.assertTrue(b.line_spec(a, ln)['repeat_buff'])
        with patch.object(b, 'add_effect', side_effect=[False, True]) as apply:
            b._exec_line(a, ln, c)
        self.assertEqual(apply.call_count, 1)
        # 독립 SE인 할리는 첫 부여 실패 후에도 다음 SE를 실행함.
        b, a, ln, c = setup('harley', '특수기', '〈점화〉', special=1)
        self.assertNotIn('repeat_buff', b.line_spec(a, ln))
        with patch.object(b, 'add_effect', side_effect=[False, True, True]) as apply:
            b._exec_line(a, ln, c)
        self.assertEqual(apply.call_count, 3)

    def test_float32_multiply_and_high_hp_filter(self):
        b, a, _, c = setup('serpang', '특수기', '회복 =', special=1)
        # 1/10: float32 비율을 double로 곱하면 1000.0000149,
        # 7/10: float32 곱은 7000, double 곱은 6999.9998808.
        self.assertEqual(b.auto_hp_basis_points(7, 10), 7000)
        self.assertEqual(b.auto_hp_basis_points(39, 50), 7799)
        self.assertEqual(b.auto_hp_basis_points(0, 0), 0)
        x, y = b.allies[1:]
        x.hp, y.hp = 3900, 77995
        self.assertEqual(b._filter(a, [x, y], 'high_hp_rate', ctx=c), [x, y])

    def test_filter_failures_and_stop_at_one_preserved(self):
        b, a, _, c = setup('professor-m', '고유 패시브', '〈강제 협공〉', passive=1)
        x, y = b.allies[1:]
        x.broken = y.broken = True
        spec = dict(one=True, ally=True, exclude_self=True, f=['not_unable_to_act', 'high_atk'])
        with patch.object(b.R(0), 'choice', return_value=y):
            self.assertEqual(b.line_auto_targets(a, spec, c), [y])
        # 성공한 단일 필터에서 종료: 뒤의 has가 거짓이어도 x.
        y.broken = False
        spec['f'] += [['has', ['없는 표지']]]
        self.assertEqual(b.line_auto_targets(a, spec, c), [y])

    def test_unsupported_multi_marker_fallback_unchanged(self):
        # U1 린의 원형 미지원 대체식은 다른 레인 범위. 단일 D5 수정이
        # 복수 대상 설명문 대체를 끄지 않는지 실제 정규화된 줄로 확인.
        b, a, ln, _ = setup('lyn', '궁극기', '〈치명타 피해 증가〉', ultimate=1)
        self.assertFalse(ally_auto_lines(variants=True, client=True)['lyn'][(ln.slot, ln.raw)]['one'])
        for mode in ('client', 'legacy'):
            b.mc['auto_empty_marker'] = mode
            self.assertIsNone(b.line_spec(a, ln))


def mutations():
    cases = {
        'auto_unable_break': ['10394011', '10394013', '10394014'],
        'auto_remove_filter': ['10394012'],
        'auto_se_reselect': ['10412012', '10412013', '10412014', 'harley_ties'],
        'auto_hp_float32': ['10192013', '10193013', '10544021', '16012013'],
        'auto_empty_marker': ['10253015'],
    }
    names = unittest.defaultTestLoader.getTestCaseNames(AutoTarget12)
    original = Battle.__init__
    for rule, matches in cases.items():
        def broken(self, *args, **kw):
            kw['mc'] = dict(kw.get('mc') or {}, **{rule: 'legacy'})
            original(self, *args, **kw)
        for name in names:
            if not any(m in name for m in matches):
                continue
            with patch.object(Battle, '__init__', broken):
                result = unittest.TextTestRunner(stream=io.StringIO()).run(AutoTarget12(name))
            assert result.failures and not result.errors, (rule, name, result.errors)
            print('KILLED', rule, name)
    # 곱셈 반올림 누락은 legacy 전환만으로 잡히지 않아 별도 실제 소스 변이.
    source = textwrap.dedent(inspect.getsource(Battle.auto_hp_basis_points))
    mutant = source.replace('int(_float32(ratio * 10000.0))', 'int(ratio * 10000.0)')
    assert mutant != source
    ns = dict(Battle.auto_hp_basis_points.__globals__)
    exec(mutant, ns)
    with patch.object(Battle, 'auto_hp_basis_points', ns['auto_hp_basis_points']):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(
            AutoTarget12('test_float32_multiply_and_high_hp_filter'))
    assert result.failures and not result.errors, result.errors
    print('KILLED float32 multiplication rounding')
    source = textwrap.dedent(inspect.getsource(Battle.line_spec))
    mutant = source.replace(" == 'client' and spec.get('one'):", " == 'client':")
    assert mutant != source
    ns = dict(Battle.line_spec.__globals__)
    exec(mutant, ns)
    with patch.object(Battle, 'line_spec', ns['line_spec']):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(
            AutoTarget12('test_unsupported_multi_marker_fallback_unchanged'))
    assert result.failures and not result.errors, result.errors
    print('KILLED unsupported multi marker scope leak')
    source = textwrap.dedent(inspect.getsource(Battle.apply_buff))
    mutant = source.replace('if repeat_buff and not applied:', 'if False:')
    assert mutant != source
    ns = dict(Battle.apply_buff.__globals__)
    exec(mutant, ns)
    with patch.object(Battle, 'apply_buff', ns['apply_buff']):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(
            AutoTarget12('test_tyria_repeat_stops_after_failed_iteration'))
    assert result.failures and not result.errors, result.errors
    print('KILLED RepeatBuffCount failure continuation')


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations()
    else:
        unittest.main()
