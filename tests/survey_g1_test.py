"""11/15 client regressions, synthetic stats; --mutate disables each fix."""
import copy
import io
import inspect
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.api import _norm_party
from battlesim.mc import Battle, Ctx, line_kind
from battlesim.metrics import unit_def, get_db
from battlesim.starsavior.parser import Line, Skill
from battlesim.starsavior.myinfo_combat import apply_potentials


def selected(key, **skills):
    return _norm_party([dict(key=key, build='none', stats_final=True,
        stats_override=dict(hp=100000, atk=1000, spd=100, cr=0, cd=5000, eh=10000, er=0, **{'def': 100}),
        myinfo_combat=dict(skills=skills, potentials=[]))],
        get_db(), 'fixed', 'standard', {'myinfo_combat': True})[0][0]


def setup(key, **skills):
    d = selected(key, **skills) if skills else unit_def(key)
    b = battle([d], [unit('enemy', hp=10**9, sa=99)], opts={'coop': False, 'nova': False})
    b.allies[0].acting = True
    return b, b.allies[0], b.foes[0]


class SurveyG1(unittest.TestCase):
    def test_cast_fires_hit_allies_at_skill_end(self):
        b = battle([unit('owner'), unit('victim1'), unit('victim2')],
                   [unit('attacker', skills=[dict(slot='기본기', dm=1, all=True)])],
                   opts={'coop': False, 'nova': False})
        owner = b.allies[0]
        owner.d.lines = [Line('[스킬 사용 후] (조건: 아군이 피격될 때 [자신 포함: 아니오]) 자신에게 〈냉각〉 (지속 무한) {최대 5중첩}', '고유 패시브', 'passive')]
        seen = []
        deal = b.deal
        def record(actor, ctx):
            deal(actor, ctx)
            seen.append((len(ctx.hit_targets), owner.stack('냉각')))
        b.deal = record
        attacker = b.foes[0]
        b.cast(attacker, attacker.d.skills['기본기'])
        self.assertEqual(seen, [(3, 0)])
        self.assertTrue(all(x.taken > 0 for x in b.allies))
        self.assertEqual(owner.stack('냉각'), 1, '실제 cast의 SKILL_END에서 한 번 발동')
        self.assertEqual(b.rule_hits['hit_ally_skill_end'], 1)

    def test_repeat_buff_stops_only_after_whole_iteration_fails(self):
        # SE10172012/41/81: one RepeatBuffCount=2 SE, not two SEs.
        for level in (1, 4, 8, 10):
            with self.subTest(level=level):
                b, a, v = setup('cristelle', special=level)
                ln = next(x for x in b.lines_of(a) if x.slot == '특수기' and x.eff.get('name') == '연소')
                c = Ctx(a, a, Skill(next(s for s in a.d.u['sk'] if s['sl'] == '특수기')))
                c.target, c.targets = v, [v]
                with patch.object(b.R(0), 'random', return_value=0), patch.object(b, 'roll_hit', side_effect=[False, True]) as hit:
                    b.run_line(a, ln, c)
                self.assertEqual(v.stack('연소'), 0)
                self.assertEqual(hit.call_count, 1)
        # One failed target must not abort the other target or next repeat.
        d = selected('cristelle', special=1)
        b = battle([d], [unit('first'), unit('second')])
        a, (v, w) = b.allies[0], b.foes
        ln = next(x for x in b.lines_of(a) if x.slot == '특수기' and x.eff.get('name') == '연소')
        c = Ctx(a, a, Skill(next(s for s in a.d.u['sk'] if s['sl'] == '특수기')))
        c.target, c.targets = v, [v, w]
        with patch.object(b.R(0), 'random', return_value=0), patch.object(b, 'roll_hit', side_effect=[False, True, True, False]) as hit:
            b.run_line(a, ln, c)
        self.assertEqual([v.stack('연소'), w.stack('연소')], [1, 1])
        self.assertEqual(hit.call_count, 4)
        # Separate Ceres SEs: a failed first freeze does not stop the second.
        b, a, v = setup('ceres', special=1)
        ln = next(x for x in b.lines_of(a) if x.slot == '특수기' and x.eff.get('name') == '빙결')
        c = Ctx(a, a, a.d.skills['특수기'])
        c.target, c.targets = v, [v]
        with patch.object(b.R(0), 'random', return_value=0), patch.object(b, 'roll_hit', side_effect=[False, True]) as hit:
            b.run_line(a, ln, c)
        self.assertEqual(v.stack('빙결'), 1)
        self.assertEqual(hit.call_count, 2)

    def test_potential_chain_after_active_and_after_active_passive(self):
        d = selected('luna', ultimate=1, passive=0)
        apply_potentials(d, get_db(), {'potentials': [[11003, 1]]})
        b = battle([d], [unit('chaos', hp=10**9, df=1000, element='혼돈', sa=99)],
                   opts={'coop': False, 'nova': False})
        a = b.allies[0]
        give(a, '지금이니!(해제불가)')
        self.assertEqual(a.stack('통찰'), 0)
        with patch.object(b, 'apply_damage', wraps=b.apply_damage) as damage:
            b.cast(a, a.d.skills['궁극기'])
        chains = [call.args[2] for call in damage.call_args_list if call.args[3] == 'chain']
        self.assertEqual(chains, [452])  # pre-active potential used to deal 444
        self.assertEqual(a.stack('통찰'), 2)
        self.assertEqual(a.stack('지금이니!(해제불가)'), 0)
        self.assertGreater(b.foes[0].taken, 452)
        # Trish's AfterActiveSkillSe grants leap after active consumes five;
        # the potential must see the newly granted three, not zero or five.
        b, a, v = setup('trish')
        a.d.lines = list(a.d.lines)  # keep cached unit_def clean across mutations
        apply_potentials(a.d, get_db(), {'potentials': [[11003, 1]]})
        give(a, '도약', stacks=5)
        give(a, '지금이니!(해제불가)')
        c = Ctx(a, a, a.d.skills['궁극기'])
        c.target, c.targets, c.kill = v, [v], True
        seen = []
        run = b.run_batch
        def record(owner, lines, ctx):
            if any(x.slot == '잠재력' for x in lines):
                seen.append(owner.stack('도약'))
            return run(owner, lines, ctx)
        b.run_batch = record
        b.run_own(a, c, 'own_post')
        self.assertEqual(seen, [3])

    def test_hit_ally_once_and_same_victim(self):
        b = battle([unit('owner'), unit('moon', element='달'), unit('sun', element='태양')],
                   [unit('attacker', skills=[dict(slot='기본기', dm=1, all=True)])],
                   opts={'coop': False, 'nova': False})
        a, moon, sun = b.allies
        a.d.lines = [Line('[스킬 사용 후] (조건: 아군이 피격될 때 [자신 포함: 아니오]) 자신에게 〈냉각〉 (지속 무한) {최대 5중첩}', '고유 패시브', 'passive')]
        c = Ctx(b.foes[0], b.foes[0], b.foes[0].d.skills['기본기'])
        c.targets = [moon, sun]
        b.deal(b.foes[0], c)
        self.assertEqual(a.stack('냉각'), 0, 'SKILL_END 이전에는 부여하지 않음')
        b.fire_hit_allies(b.foes[0], c)
        self.assertEqual(a.stack('냉각'), 1)
        a.d.lines = [Line('[스킬 사용 후] (조건: 아군이 피격될 때 [자신 포함: 아니오; 대상 속성: 달; 결과: 치명타]) 자신에게 〈점화〉 (지속 무한) {최대 5중첩}', '고유 패시브', 'passive')]
        c.crit_targets = {sun}
        b.fire_hit_allies(b.foes[0], c)
        self.assertEqual(a.stack('점화'), 0)
        c.crit_targets.add(moon)
        b.fire_hit_allies(b.foes[0], c)
        self.assertEqual(a.stack('점화'), 1)
        self.assertGreater(b.rule_hits['hit_ally_skill_end'], 0)

    def test_stack_consumption_at_end(self):
        for key, name in [('kyra', '점화'), ('harley', '점화'), ('wedding-carmen', '냉각')]:
            with self.subTest(key=key):
                b, a, v = setup(key)
                give(a, name, stacks=5)
                c = Ctx(a, a, a.d.skills['기본기'])
                c.target, c.targets = v, [v]
                b.run_own(a, c, 'own_pre')
                self.assertEqual(a.stack(name), 5)
                b.run_own(a, c, 'own_post')
                self.assertEqual(a.stack(name), 1)
                self.assertGreater(b.rule_hits['skill_end_timing'], 0)

    def test_gauge_snapshot_then_end(self):
        for key, slot, state in [('lydia', '특수기', '수배 전단'), ('wedding-epindel', '궁극기', '보호막')]:
            with self.subTest(key=key):
                b, a, v = setup(key)
                # Preserve the old snapshot rule; native marker sets are tested in marker_se_test.
                b.mc['marker_se_flow'] = 'legacy'
                lines = [ln for ln in b.lines_of(a) if ln.eff.get('start_filter')]
                self.assertTrue(lines)
                state = lines[0].eff['start_filter']
                mark = give(v, '보호막' if state == 'shield' else state)
                if state == 'shield':
                    mark.shield = 1
                v.gauge = 9000
                seen = []
                original = b.deal
                def deal(actor, ctx):
                    seen.append(v.gauge)
                    v.eff.clear()  # the hit destroys the start-time mark/barrier
                    b.dirty(v)
                    original(actor, ctx)
                b.deal = deal
                b.cast(a, a.d.skills[slot])
                self.assertEqual(seen[0], 9000)
                self.assertLess(v.gauge, 9000)
                self.assertGreater(b.rule_hits['skill_end_timing'], 0)

    def test_passive_precedes_new_debuff_and_stack(self):
        b, a, v = setup('lydia')
        # Observe passive checks at SKILL_END before active effects execute.
        seen = []
        run = b.run_batch
        def record(owner, lines, ctx):
            if any(x.src_kind == 'passive' and line_kind(x) == 'own_post' for x in lines):
                seen.append(v.n_harmful())
            return run(owner, lines, ctx)
        b.run_batch = record
        with patch.object(b.R(0), 'random', return_value=0), patch.object(b, 'roll_hit', return_value=True):
            b.cast(a, a.d.skills['특수기'])
        self.assertEqual(seen[0], 0)
        self.assertEqual(a.stack('공허의 추구자'), 0)
        self.assertGreater(v.n_harmful(), 0)
        self.assertGreater(b.rule_hits['passive_se_order'], 0)
        b, a, v = setup('rosaria')
        with patch.object(b.R(0), 'random', return_value=0):
            b.cast(a, a.d.skills['기본기'])
        self.assertEqual(a.stack('격동'), 1)
        self.assertEqual(a.stack('업화(해제불가)'), 0)
        # AfterActiveSkillSe is an explicit exception: Trish gets leap after
        # her ultimate removes the old stacks (SE 10154022).
        b, a, v = setup('trish')
        give(a, '도약', stacks=5)
        c = Ctx(a, a, a.d.skills['궁극기'])
        c.target, c.targets, c.kill = v, [v], True
        b.run_own(a, c, 'own_post')
        self.assertEqual(a.stack('도약'), 3)

    def test_independent_cooling(self):
        b, a, v = setup('epindel', special=1)
        ln = next(x for x in b.lines_of(a) if x.slot == '특수기' and x.eff.get('name') == '냉각')
        c = Ctx(a, a, a.d.skills['특수기'])
        with patch.object(b.R(0), 'random', side_effect=[0.1, 0.99, 0.1]):
            b.run_line(a, ln, c)
        self.assertEqual(a.stack('냉각'), 2)
        self.assertGreater(b.rule_hits['se_independent_roll'], 0)

    def test_independent_freeze_resistance(self):
        b, a, v = setup('ceres', special=1)
        ln = next(x for x in b.lines_of(a) if x.slot == '특수기' and x.eff.get('name') == '빙결')
        c = Ctx(a, a, a.d.skills['특수기'])
        c.target, c.targets = v, [v]
        with patch.object(b.R(0), 'random', return_value=0), patch.object(b, 'roll_hit', side_effect=[True, False]):
            b.run_line(a, ln, c)
        self.assertEqual(v.stack('빙결'), 1)
        self.assertGreater(b.rule_hits['se_independent_roll'], 0)

    def test_extend_probability_preserved(self):
        b, a, v = setup('muriel', special=1)
        ln = next(x for x in b.lines_of(a) if x.eff['kind'] == 'extend')
        e = give(v, '공격력 감소', harmful=True, dur=2)
        c = Ctx(a, a, a.d.skills['특수기'])
        c.target, c.targets = v, [v]
        with patch.object(b.R(0), 'random', return_value=0.99), patch.object(b, 'roll_hit', return_value=True):
            b.run_line(a, ln, c)
        self.assertEqual(e.dur, 2)
        self.assertGreater(b.rule_hits['se_independent_roll'], 0)


MUTATIONS = {
    'hit_ally_skill_end': ['test_hit_ally_once_and_same_victim'],
    'skill_end_timing': ['test_stack_consumption_at_end', 'test_gauge_snapshot_then_end'],
    'passive_se_order': ['test_passive_precedes_new_debuff_and_stack'],
    'se_independent_roll': ['test_independent_cooling', 'test_independent_freeze_resistance', 'test_extend_probability_preserved'],
}

def mutations(cls, cases):
    original = Battle.__init__
    for key, names in cases.items():
        def init(self, *args, **kw):
            kw['mc'] = dict(kw.get('mc') or {}, **{key: 'legacy'})
            original(self, *args, **kw)
        for name in names:
            with patch.object(Battle, '__init__', init):
                result = unittest.TextTestRunner(stream=io.StringIO()).run(cls(name))
            assert not result.wasSuccessful(), (key, name, 'mutation survived')
            assert not result.errors, (key, name, result.errors)
            print('KILLED', key, name)


def source_mutation(method, old, new, test):
    """Remove just the reviewed change; patch restores the live method afterward."""
    original = getattr(Battle, method)
    source = textwrap.dedent(inspect.getsource(original))
    assert old in source, (method, 'mutation anchor missing')
    namespace = {}
    exec(compile(source.replace(old, new, 1), '<G1 mutation>', 'exec'), original.__globals__, namespace)
    with patch.object(Battle, method, namespace[method]):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(SurveyG1(test))
    assert not result.wasSuccessful() and not result.errors, (method, test, result.errors)
    assert getattr(Battle, method) is original
    print('KILLED', method, test)

if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations(SurveyG1, MUTATIONS)
        with patch('battlesim.mc.after_active_se', return_value=False):
            r = unittest.TextTestRunner(stream=io.StringIO()).run(SurveyG1('test_passive_precedes_new_debuff_and_stack'))
        assert not r.wasSuccessful() and not r.errors
        print('KILLED AfterActiveSkillSe exception')
        source_mutation('apply_buff', "if eff.get('repeat_buff') and not applied:",
                        'if False:', 'test_repeat_buff_stops_only_after_whole_iteration_fails')
        source_mutation('run_own',
                        "potentials = [ln for ln in passive if ln.slot == '잠재력']\n"
                        "            passive = [ln for ln in passive if ln.slot != '잠재력']",
                        'potentials = []',
                        'test_potential_chain_after_active_and_after_active_passive')
        source_mutation('run_own', "[ln for ln in passive if after_active_se(u.key, ln)], potentials)",
                        "potentials, [ln for ln in passive if after_active_se(u.key, ln)])",
                        'test_potential_chain_after_active_and_after_active_passive')
        source_mutation('cast', 'self.fire_hit_allies(u, ctx)', 'pass',
                        'test_cast_fires_hit_allies_at_skill_end')
    else:
        unittest.main()
