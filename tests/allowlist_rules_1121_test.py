"""PC 26752678 D: defaults must exercise the client lifecycle, not only metadata."""
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
from battlesim.mc import Battle, Ctx, Unit
from battlesim.rules import MC_RULES, MC_OPTS, DEFAULT_OPTS
from battlesim.api import assumptions_used
from battlesim.starsavior.parser import Line, Skill


def passive(phase, effect):
    return Line(f'[{phase}] {effect}', '고유 패시브', 'passive')


class Rules1121Test(unittest.TestCase):
    def test_inactive_legacy_assumptions_return_when_selected(self):
        keys = lambda m, o: {x['rule'] for x in assumptions_used(m, o)}
        old_enemy = {'mc.enemy_init_cd', 'mc.enemy_init_cd_special',
                     'mc.target_row_weight', 'mc.target_defender_mult', 'mc.target_mode'}
        current = keys(MC_OPTS, DEFAULT_OPTS)
        self.assertTrue(current)
        self.assertFalse(current & (old_enemy | {'mc.manual_burst', 'opts.init_cd_frac'}))
        legacy = keys(dict(MC_OPTS, enemy_spawn='legacy', enemy_auto_target='weighted'),
                      dict(DEFAULT_OPTS, nova_policy='manual'))
        # enemy_init_cd 는 11/21 code 승격(클라 OBF_7817 가득과 같음) -> legacy 를 골라도 가정 보고 안 함
        self.assertTrue((old_enemy - {'mc.enemy_init_cd'}) | {'mc.manual_burst'} <= legacy)
        self.assertNotIn('mc.enemy_init_cd', legacy)
        self.assertNotIn('opts.init_cd_frac', legacy)
        # Even explicit expected-value options cannot affect this MC API.
        self.assertEqual(current, keys(MC_OPTS, dict(DEFAULT_OPTS, init_cd_frac=.75)))

    def test_wave_default_does_not_repeat_battle_start(self):
        foe = unit('foe', hp=100000)
        foe.lines = [passive('등장 후', '자신에게 〈등장〉 (3턴 / 공격력% +10%)'),
                     passive('전투 시작 시', '자신에게 〈개전〉 (3턴 / 공격력% +20%)'),
                     passive('웨이브 시작 시', '자신에게 〈웨이브〉 (3턴 / 공격력% +30%)')]
        b = battle([unit('ally')], [foe])
        self.assertTrue(b.foes[0].has('개전'))
        b.cast(b.allies[0], b.allies[0].d.skills['기본기'])
        self.assertGreater(b.progress(), 0)
        b.waves.append([foe])
        b.spawn_wave()
        self.assertTrue(b.foes[0].has('등장'))
        self.assertTrue(b.foes[0].has('웨이브'))
        self.assertFalse(b.foes[0].has('개전'))
        self.assertGreater(b.rule_hits['wave_foe_battle_start'], 0)

    def test_summon_runs_only_after_spawn_and_respects_occupied_slots(self):
        child = unit('child', hp=100000)
        child.spawn, child.slot = 'S', 0
        child.lines = [passive('등장 후', '자신에게 〈등장〉 (3턴 / 공격력% +10%)'),
                       passive('전투 시작 시', '자신에게 행동 게이지 +50%'),
                       passive('웨이브 시작 시', '자신에게 〈웨이브〉 (3턴 / 공격력% +30%)')]
        boss = unit('summoner', hp=100000)
        boss.slot = 2
        boss.summon_groups = [{'slots': [{'pos': 0, 'foe_def': child}]}]
        b = battle([unit('ally')], [boss])
        b._do_summon(b.foes[0])
        spawned = b._foe_slots[0]
        self.assertTrue(spawned.has('등장'))
        self.assertEqual(spawned.gauge, 0)
        self.assertFalse(spawned.has('웨이브'))
        self.assertGreater(b.rule_hits['summon'], 0)
        b._do_summon(b.foes[0])
        self.assertEqual(len(b.foes), 2)
        b.cast(b.allies[0], b.allies[0].d.skills['기본기'], target=spawned)
        self.assertGreater(spawned.taken, 0)
        b.kill(b.foes[0], b.allies[0])
        self.assertEqual(b.alive(1), [spawned])  # ordinary kill-all wave still has a target

    def test_revive_after_spawn_precedes_hp_assignment(self):
        b = battle([unit('reviver'), unit('target')], [unit('foe')])
        a, v = b.allies
        v.d.lines = [passive('등장 후', '자신에게 〈등장〉 (3턴 / 생명력% +20%)'),
                     passive('전투 시작 시', '자신에게 〈개전〉 (3턴 / 공격력% +20%)')]
        b.kill(v, b.foes[0])
        seen = []
        original = b.run_line
        def observe(owner, ln, ctx):
            if ln.phase == '등장 후':
                seen.append(owner.hp)
            return original(owner, ln, ctx)
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = v, [v]
        with patch.object(b, 'run_line', observe):
            b.run_line(a, Line('[스킬 사용 후] 스킬 대상에게 부활(생명력 50%)', '기본기', 'active'), ctx)
        self.assertEqual(seen, [0])
        self.assertFalse(v.dead)
        self.assertTrue(v.has('등장'))
        self.assertFalse(v.has('개전'))
        self.assertEqual(v.hp, 6000)
        self.assertGreater(b.rule_hits['revive_after_spawn'], 0)

    def test_summon_flags_follow_after_spawn_cooldown_effects(self):
        child = unit('child', skills=[dict(slot=s, dm=100, cd=4)
                                     for s in ('특수기', '궁극기')])
        child.spawn = 'S'
        child.lines = [passive('등장 후', '자신에게 〈궁극기 쿨타임 초기화〉')]
        boss = unit('summoner')
        boss.slot = 2
        boss.summon_groups = [{'slots': [{'pos': 0, 'foe_def': child}]}]
        b = battle([unit('ally')], [boss])
        seen = []
        original = b.run_line
        def observe(owner, ln, ctx):
            if owner.summoned:
                seen.append(dict(owner.cd))
            return original(owner, ln, ctx)
        with patch.object(b, 'run_line', observe):
            b._do_summon(b.foes[0])
        self.assertEqual(seen, [{'특수기': 0, '궁극기': 0}])
        self.assertEqual(b._foe_slots[0].cd, {'특수기': 0, '궁극기': 4})
        self.assertEqual(b.rule_hits['summon'], 1)
        # A replacement at the same event boundary changes the maximum CD.
        b.kill(b._foe_slots[0], b.allies[0])
        replacement = Skill(dict(sl='궁극기', n='replacement', ty='액티브',
                                 act='공격', tg='적 단일', cf=[10000, 0, 0, 0], cd=7))
        def replace_on_spawn(owner, ln, ctx):
            result = original(owner, ln, ctx)
            if owner.summoned:
                owner.skill_overrides['궁극기'] = replacement
            return result
        with patch.object(b, 'run_line', replace_on_spawn):
            b._do_summon(b.foes[0])
        self.assertEqual(b._foe_slots[0].cd, {'특수기': 0, '궁극기': 7})
        self.assertEqual(b.rule_hits['summon'], 2)

    def test_enemy_skill_order_and_silence(self):
        sk = [dict(slot=s, dm=100, cd=4) for s in ('기본기', '특수기', '궁극기')]
        b = battle([unit('a')], [unit('f', skills=sk)])
        f = b.foes[0]
        f.cd = dict.fromkeys(f.cd, 0)
        self.assertEqual(b.choose_skill(f)[0].slot, '궁극기')
        f.d.skill_order = ['특수기', '궁극기', '기본기']
        self.assertEqual(b.choose_skill(f)[0].slot, '특수기')
        give(f, '침묵', harmful=True)
        self.assertEqual(b.choose_skill(f)[0].slot, '기본기')

    def test_dead_caster_taunt_is_removed_after_skill_ordinary_buff_stays(self):
        for mode in ('client', 'keep_buffs'):
            b = battle([unit('a'), unit('other')], [unit('caster'), unit('f', hp=100000)],
                       mc={'caster_death': mode}, opts={'coop': False})
            a, other = b.allies
            source, foe = b.foes
            give(a, '도발', src=source, harmful=True)
            give(other, '공격력 증가', {'공격력%': 20}, src=source)
            b.kill(source, a)
            self.assertTrue(a.has('도발'))  # cleanup is at skill end, not kill()
            b.cast(a, a.d.skills['기본기'], target=foe)
            self.assertGreater(foe.taken, 0)
            self.assertEqual(a.has('도발'), mode == 'keep_buffs')
            self.assertEqual(a.n_harmful(), int(mode == 'keep_buffs'))
            self.assertTrue(other.has('공격력 증가'))
            self.assertEqual(other.eff['공격력 증가'].dur, 3)
            self.assertEqual(b.rule_hits['caster_death'], int(mode == 'client'))

    def test_enemy_formula_is_symmetric(self):
        b = battle([unit('a', hp=100000)], [unit('f', hp=100000)], opts={'coop': False})
        a, f = b.allies[0], b.foes[0]
        b.cast(a, a.d.skills['기본기'], target=f)
        a.last_slot = None  # compare the same non-counter hit on both sides
        b.cast(f, f.d.skills['기본기'], target=a)
        self.assertGreater(a.taken, 0)
        self.assertEqual(a.taken, f.taken)

    def test_buff_count_includes_zero_and_undispellable(self):
        b = battle([unit('a')], [unit('f')])
        a, f = b.allies[0], b.foes[0]
        ln = passive('피격 후', '자신에게 〈판정〉 (2턴 / 공격력% +10%)')
        ln.params = [('적 강화효과 보유', '예'), ('효과 개수 미만', '2')]
        ctx = Ctx(f, a, a.d.skills['기본기'])
        ctx.target, ctx.targets = f, [f]
        for n in range(4):
            if n:
                e = give(a, f'강화{n}')
                e.fixed = True
            self.assertEqual(b.cond_ok(f, ln, ctx), n <= 2)

    def test_confirmed_grades_have_current_client_evidence(self):
        # wave_foe_battle_start·summon·revive_after_spawn·caster_death 는 스위치를 지움(엔진 다이어트 4단계, 항상 클라 동작)
        for key in ('enemy_skill_ai', 'enemy_same_formula', 'enemy_hit_buff_cmp'):
            self.assertEqual(MC_RULES[key]['grade'], 'code', key)
            self.assertIn('26752678', MC_RULES[key]['source'], key)


def mutations():
    import battlesim.api as api
    original_report = api.assumptions_used
    source = inspect.getsource(original_report)
    ns = {}
    exec(source.replace('k not in inactive and ', ''), original_report.__globals__, ns)
    with patch.dict(globals(), assumptions_used=ns['assumptions_used']):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(
            Rules1121Test('test_inactive_legacy_assumptions_return_when_selected'))
    assert result.failures and not result.errors, result.errors
    print('inactive assumptions assertion failures:', len(result.failures))
    cases = [
        ('spawn_wave', "if (self.wave_i > 0", 'if (False', 'test_wave_default_does_not_repeat_battle_start'),
        ('_do_summon', "self.mc['summon'] == 'client'", 'False', 'test_summon_runs_only_after_spawn_and_respects_occupied_slots'),
        ('_do_summon', 'u.cd = dict.fromkeys(u.cd, 0.0)', 'pass', 'test_summon_flags_follow_after_spawn_cooldown_effects'),
        ('_do_summon', 'u.reset_initial_cooldowns()', 'pass', 'test_summon_flags_follow_after_spawn_cooldown_effects'),
        ('reset_initial_cooldowns', 'self.skill_overrides.get(slot, original)', 'original', 'test_summon_flags_follow_after_spawn_cooldown_effects'),
        ('run_special', "if ln.phase == '등장 후':", 'if False:', 'test_revive_after_spawn_precedes_hp_assignment'),
        ('choose_skill', "slots = ('궁극기', '특수기', '기본기')", "slots = ('기본기', '특수기', '궁극기')", 'test_enemy_skill_order_and_silence'),
        ('deal', "not self.mc['enemy_same_formula']", 'True', 'test_enemy_formula_is_symmetric'),
        ('_cond_values', 'else n <= float(lim)', 'else n < float(lim)', 'test_buff_count_includes_zero_and_undispellable'),
        ('cast', "self.mc['caster_death'] == 'client'", 'False', 'test_dead_caster_taunt_is_removed_after_skill_ordinary_buff_stays'),
    ]
    for method, old, new, test in cases:
        cls = Unit if method == 'reset_initial_cooldowns' else Battle
        original = getattr(cls, method)
        source = textwrap.dedent(inspect.getsource(original))
        assert old in source, (method, old)
        ns = {}
        exec(source.replace(old, new), original.__globals__, ns)
        suite = lambda: unittest.TextTestRunner(stream=io.StringIO()).run(Rules1121Test(test))
        assert suite().wasSuccessful(), test
        with patch.object(cls, method, ns[method]):
            result = suite()
        assert result.failures and not result.errors, (test, result.errors)
        print(method, 'assertion failures:', len(result.failures))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
