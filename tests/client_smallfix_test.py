"""빌드 26610546의 작은 경계 차이. --mutate로 구현/생성 경로의 결함 검출 확인."""
import contextlib
import io
import json
import os
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, Ctx, level_buff
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS
from battlesim.starsavior.parser import Line


class ClientSmallfixTest(unittest.TestCase):
    def condition(self, text):
        return Line('[스킬 사용 후] (조건: 내 공격 후 [' + text + ']) 자신에게 행동 게이지 10%p 증가', '기본기', 'active')

    def test_hp_basis_points_and_target_set(self):
        b = battle([unit()], [unit('first', hp=100000), unit('second', hp=100000)])
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = b.foes[0], b.foes
        b.foes[0].hp = 90000
        for hp, le, ge in [(49999, True, False), (50000, True, True), (50009, True, True), (50010, False, True)]:
            b.foes[1].hp = hp
            self.assertEqual(b.cond_ok(a, self.condition('대상 HP% 이하: 5000'), ctx), le)
            ctx.target, ctx.targets = b.foes[1], [b.foes[1]]
            self.assertEqual(b.cond_ok(a, self.condition('대상 HP% 이상: 5000'), ctx), ge)
            ctx.target, ctx.targets = b.foes[0], b.foes
        self.assertGreater(b.rule_hits['target_hp_condition'], 0)
        b.foes[1].hp = 50009
        with patch.dict(b.mc, target_hp_condition='ratio'):
            self.assertFalse(b.cond_ok(a, self.condition('대상 HP% 이하: 5000'), ctx))
        for bp, hp in [(0, 0), (10000, 100000)]:
            ctx.target, ctx.targets = b.foes[1], [b.foes[1]]
            b.foes[1].hp = hp
            for op in ('이하', '이상'):
                self.assertTrue(b.cond_ok(a, self.condition(f'대상 HP% {op}: {bp}'), ctx))

    def test_not_self_stack_exact_not_sum(self):
        b = battle([unit()], [unit('foe')])
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ln = self.condition('자신이 미보유: 격동, 통찰; 자신 미보유 효과 중첩수: 3')
        for stacks, expected in [(None, True), (2, True), (3, False), (4, True)]:
            a.eff.clear()
            if stacks is not None:
                give(a, '격동', stacks=stacks).maxs = 5
            self.assertEqual(b.cond_ok(a, ln, ctx), expected)
        a.eff.clear()
        give(a, '격동', stacks=1).maxs = 5
        give(a, '통찰', stacks=2).maxs = 5
        self.assertTrue(b.cond_ok(a, ln, ctx))  # 1+2를 3으로 합산하지 않음
        a.eff['통찰'].stacks = 3
        self.assertFalse(b.cond_ok(a, ln, ctx))
        self.assertGreater(b.rule_hits['not_self_stack'], 0)
        a.eff.clear()
        give(a, '격동', stacks=4).maxs = 5
        with patch.dict(b.mc, not_self_stack='ge'):
            self.assertFalse(b.cond_ok(a, ln, ctx))

    def test_hp_float32_conversion_before_truncation(self):
        for hp, maxhp, bp, expected in [(25010, 100000, 2500, True), (50009999, 100000000, 5000, False)]:
            b = battle([unit()], [unit('foe', hp=maxhp)])
            a, f = b.allies[0], b.foes[0]
            f.hp = hp
            ctx = Ctx(a, a, a.d.skills['기본기'])
            ctx.target, ctx.targets = f, [f]
            self.assertEqual(b.cond_ok(a, self.condition(f'대상 HP% 이하: {bp}'), ctx), expected)

    def test_non_level_and_zero_count(self):
        b = battle([unit()], [unit('foe')])
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        self.assertIs(level_buff('공격력 증가'), False)
        give(a, '공격력 증가')
        for n in (0, 3):
            self.assertFalse(b.cond_ok(a, self.condition(f'자신이 미보유: 공격력 증가; 자신 미보유 효과 중첩수: {n}'), ctx))
        a.eff.clear()
        self.assertTrue(b.cond_ok(a, self.condition('자신이 미보유: 공격력 증가; 자신 미보유 효과 중첩수: 0'), ctx))

    def test_target_attack_uses_each_live_receiver(self):
        b = battle([unit(atk=9000)], [unit('one', hp=100000, atk=1000), unit('two', hp=100000, atk=2000)])
        a = b.allies[0]
        give(b.foes[0], '공격력 증가', {'공격력%': 30})
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.atkp = 2  # 시전자의 이번 스킬 공격력 보정을 대상에게 넘기지 않음
        ln = Line('[스킬 사용 후] 적 전체에게 연쇄 피해 = 대상 공격력×50%', '기본기', 'active', damage_type='ADT_STAT_TRUE')
        self.assertEqual(ln.eff['stat'], 'target_atk')
        b.chain(a, ln.eff, ctx)
        self.assertEqual([v.taken for v in b.foes], [650, 1000])
        self.assertEqual(b.rule_hits['chain_target_stat'], 2)
        self.assertGreater(b.progress(), 0)
        before = [v.hp for v in b.foes]
        with patch.dict(b.mc, chain_target_stat='off'):
            b.chain(a, ln.eff, ctx)
        self.assertEqual([v.hp for v in b.foes], before)

    def test_target_attack_normal_keeps_caster_damage_modifiers(self):
        b = battle([unit(atk=9000)], [unit('foe', hp=100000, atk=1000, df=0)])
        a, f = b.allies[0], b.foes[0]
        give(a, 'damage', {'피해 증가': 20})
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = f, [f]
        ln = Line('[스킬 사용 후] 스킬 대상에게 연쇄 피해 = 대상 공격력×50%', '기본기', 'active')
        b.chain(a, ln.eff, ctx)
        self.assertEqual(f.taken, 1110)  # 1000*.5*1.2*1.85
        self.assertGreater(b.progress(), 0)

    def test_expected_engine_reports_missing_target_stat_model(self):
        from battlesim import engine
        s = engine.Sim([engine.DummyDef(atk=9000)], [dict(hp=100000)])
        a = s.party[0]
        ctx = engine.Ctx(a, a, a.d.skills['기본기'], False, 1.0)
        for stat, key in [('공격력', 'target_atk'), ('방어력', 'target_def')]:
            ln = Line(f'[스킬 사용 후] 적 전체에게 연쇄 피해 = 대상 {stat}×50%', '기본기', 'active')
            s.chain_damage(a, ln.eff, ctx, 1.0)
            self.assertEqual(s.unmodeled['effect: ' + key + ' chain'], 1)
        self.assertEqual(a.dmg, 0)

    def test_extra_turn_increments_global_turn_and_limit(self):
        b = battle([unit_def('asherah-order-striker')], [unit('boss', hp=10**9, sa=1, spd=1)],
                   turn_limit=4, opts={'coop': False, 'nova': False})
        selected = []
        original = b.act
        def record(u):
            selected.append((b.global_turns, u.extra_turn))
            return original(u)
        with patch.object(b, 'act', record):
            b.run()
        self.assertEqual(b.result, 'timeout')
        self.assertEqual([t for t, _ in selected], [1, 2, 3, 4])
        self.assertTrue(any(extra for _, extra in selected))
        self.assertEqual(sum(u.actions for u in b.allies + b.all_foes), 4)
        self.assertGreater(b.progress(), 0)

    def test_client_tables_and_level_metadata(self):
        static = os.environ.get('STARSAVIOR_STATIC')
        if not static:
            self.skipTest('STARSAVIOR_STATIC 없음')
        tables = Path(static) / 'tables'
        rows = json.loads((tables / 'SE_TEMPLET_SKILL_2.json').read_text(encoding='utf8'))['Data']
        row = next(r for r in rows if r.get('m_SEStrID') == 'COND_MON_SHADOW_MINA_BLACK_BOSS_EVENT_ATTACK_01')
        self.assertEqual((row['AddDamageTargetType'], row['AddDamageStatType'], row['AddDamageRate']), ('NSETT_TARGET', 'NST_ATK', 5000))
        from tools.build_buff_count import build_levels
        data = json.loads((ROOT / 'data/buff_count.json').read_text(encoding='utf8'))
        self.assertEqual(build_levels(static), data['levels'])
        self.assertIsNone(data['levels']['참극의 가시(해제불가)'])
        from tools.build_auto_skill import jsonc
        rows = json.loads((tables / 'SE_TEMPLET_SKILL_1.json').read_text(encoding='utf8'))['Data']
        by = {r['m_SEStrID']: r for r in rows}
        grant = by['COND_DARK_UNKNOWN_HYPER_01_01']
        self.assertEqual((grant['m_BuffTargetType'], grant['m_BuffStrID'], grant['m_BuffLifeTurn']), ('NSETT_SELF', 'BI_CRUSH', 3))
        for sid in ('COND_APOSTLE_GILLE_HYPER_01_02', 'COND_APOSTLE_GILLE_HYPER_01_03', 'COND_APOSTLE_GILLE_UNIQUE_PASSIVE_01_08'):
            self.assertEqual((by[sid]['m_BuffTargetType'], by[sid]['AutoTargetId']), ('NSETT_AUTO_ALLY', 10201))
        auto = next(r for r in jsonc(tables / 'Plain/AUTO_SKILL_TARGET_TEMPLET.json')['Data'] if r['Id'] == 10201)
        self.assertEqual(auto['TargetCondition']['IsSpecificBuff'], ['BI_CRUSH'])

    def test_synergy_generator_and_other_candidate_report(self):
        # 실제 생성 경로를 실행하되 저장은 메모리에서 검사함.
        written = {}
        def save(path, data, **kw):
            written[Path(path).name] = data
        stdout = io.StringIO()
        with patch('battlesim.fileio.atomic_json', save), patch('battlesim.fileio.atomic_text'), patch.object(sys, 'argv', ['build_synergy_pairs.py']), contextlib.redirect_stdout(stdout):
            runpy.run_path(str(ROOT / 'tools/build_synergy_pairs.py'), run_name='__main__')
        pairs = written['synergy_pairs.json']
        row = next(r for r in pairs if (r['a'], r['b'], r['type']) == ('asherah-order-striker', 'gille', '1:부여→소비'))
        self.assertIn('파쇄', row['reason'])
        self.assertEqual(row['conf'], '확인')
        self.assertTrue(any('3턴' in e and '파쇄' in e for e in row['evidence']))
        self.assertTrue(any('서곡' in e for e in row['evidence']))
        self.assertTrue(any('게이지' in e for e in row['evidence']))
        self.assertTrue(any('속도 증가' in e for e in row['evidence']))
        tyria = next(r for r in pairs if (r['a'], r['b'], r['type']) == ('tyria', 'gille', '1:부여→소비'))
        self.assertNotIn('파쇄', tyria['reason'])
        self.assertIn("('tyria', 'gille', '파쇄')", stdout.getvalue())
        self.assertEqual(pairs, json.loads((ROOT / 'data/synergy_pairs.json').read_text(encoding='utf8')))


def mutations():
    cases = [('HP integer removed', 'test_hp_basis_points_and_target_set', patch.dict(MC_OPTS, target_hp_condition='ratio')),
             ('HP float32 removed', 'test_hp_float32_conversion_before_truncation', patch('battlesim.mc._float32', side_effect=lambda value: value)),
             ('stack >= restored', 'test_not_self_stack_exact_not_sum', patch.dict(MC_OPTS, not_self_stack='ge')),
             ('chain disabled', 'test_target_attack_uses_each_live_receiver', patch.dict(MC_OPTS, chain_target_stat='off')),
             ('synergy link dropped', 'test_synergy_generator_and_other_candidate_report', patch('tools.synergy_self_status.links', return_value=[]))]
    original = Battle.chain
    def self_atk(b, owner, eff, ctx):
        return original(b, owner, dict(eff, stat='atk'), ctx)
    cases.append(('caster attack substituted', 'test_target_attack_uses_each_live_receiver', patch.object(Battle, 'chain', self_atk)))
    act = Battle.act
    def skip_one_extra(b, u):
        if u.extra_turn and not getattr(b, '_mutated_extra', False):
            b.global_turns -= 1
            b._mutated_extra = True
        return act(b, u)
    cases.append(('extra turn not counted', 'test_extra_turn_increments_global_turn_and_limit', patch.object(Battle, 'act', skip_one_extra)))
    for name, test, mutation in cases:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(ClientSmallfixTest(test))
        if result.errors or not result.failures:
            raise AssertionError((name, result.errors, result.failures))
        print('detected:', name)


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations()
    else:
        unittest.main()
