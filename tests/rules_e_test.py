"""11/10 과제 E: 공개 standard·합성 입력. --ab: 30판 쌍 비교, --mutate: 변이 검증."""
import collections
import inspect
import io
import json
import math
import os
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit, give
from battlesim import mc as mcmod
from battlesim.api import simulate
from battlesim.mc import Battle, Ctx, line_kind
from battlesim.rules import MC_OPTS, MC_RULES
from battlesim.metrics import unit_def
from battlesim.engine import Actor, Buff
from battlesim.starsavior.parser import Line, _map_prop, _perm_apply
from tools.runtime import static_path_or_none, skip_note

LEGACY = dict(buff_fresh_scope='self', break_gauge_actor='exclude', purify_nova_scope='main_only',
              preemptive_reduce='attacker_preempt', omega_dispel='fixed')
PARTY = ['sunshine-cat-smile', 'cristelle', 'white-pearl-luna', 'wedding-carmen']


def run_stage(stage, override=None, n=3, skill=None, party=None):
    hits = collections.Counter()
    original = Battle.__init__
    battles = []
    def record(self, *a, **kw):
        original(self, *a, **kw)
        battles.append(self)
    options = dict(seed=3, n_runs=n, build='standard', rules_override=override or {})
    if skill:
        options['break_skill'] = {'name': skill}
    with patch.object(Battle, '__init__', record):
        r = simulate(party or PARTY, {'stage': stage}, options)
    for b in battles:
        hits.update(b.rule_hits)
    return r, hits


class FreshTest(unittest.TestCase):
    def setup(self, mode, start=False):
        a, other = unit('A'), unit('B')
        if start:
            a.lines = [Line('[스킬 사용 시작 시] 자신에게 〈시험 강화〉 (2턴 / 공격력% +10%)', '기본기', 'active')]
        else:
            other.lines = [Line('[스킬 사용 후] (조건: 아군 공격 후) 아군 전체에게 〈시험 강화〉 (1턴 / 공격력% +10%)', '고유 패시브', 'passive')]
        b = battle([a, other], [unit('적', hp=10**8)], mc={'buff_fresh_scope': mode},
                   opts={'coop': False, 'nova': False})
        return b, b.allies[0], b.allies[1]

    def test_other_source_survives_current_end(self):
        for mode in ('client', 'self'):
            b, a, other = self.setup(mode)
            b.act(a)
            self.assertGreater(b.foes[0].taken, 0)
            self.assertEqual(a.has('시험 강화'), mode == 'client')
            if mode == 'client':
                self.assertEqual(a.eff['시험 강화'].dur, 1)
                self.assertGreater(b.rule_hits['buff_fresh_other'], 0)
            # Verify the real event boundary.
            other.d.lines = []
            seen = []
            fire = b.fire
            def observe(u, kind, ctx):
                if u is a and kind == 'own_ts':
                    seen.append(a.has('시험 강화'))
                return fire(u, kind, ctx)
            with patch.object(b, 'fire', observe):
                b.act(a)
            self.assertEqual(seen, [mode == 'client'])
            self.assertFalse(a.has('시험 강화'))

    def test_start_source_ticks_current_end(self):
        for mode in ('client', 'self'):
            b, a, _ = self.setup(mode, True)
            b.act(a)
            self.assertGreater(b.foes[0].taken, 0)
            self.assertEqual(a.eff['시험 강화'].dur, 1 if mode == 'client' else 2)
            a.d.lines = []
            b.act(a)
            self.assertEqual(a.has('시험 강화'), mode == 'self')
            b.act(a)
            self.assertFalse(a.has('시험 강화'))

    def test_reapply_resets_fresh_and_exceptions(self):
        b, a, other = self.setup('client')
        a.acting = True
        end = Line('[스킬 사용 후] 자신에게 〈시험 강화〉 (2턴 / 공격력% +10%)', '기본기', 'active')
        start = Line('[스킬 사용 시작 시] 자신에게 〈시험 강화〉 (2턴 / 공격력% +10%)', '기본기', 'active')
        ctx = Ctx(a, a, a.d.skills['기본기'])
        b.run_line(a, end, ctx)
        self.assertTrue(a.eff['시험 강화'].fresh)
        b.run_line(a, start, ctx)
        self.assertFalse(a.eff['시험 강화'].fresh)
        for phase, trig in [('턴 시작 시', None), ('전투 시작 시', None), ('웨이브 시작 시', None),
                            ('등장 후', None), ('스킬 사용 시작 시', '아군 공격 시'),
                            ('스킬 사용 시작 시', '적 공격 시')]:
            raw = '[' + phase + '] ' + ('(조건: ' + trig + ') ' if trig else '') + '자신에게 〈시험〉 (1턴)'
            ln = Line(raw, '고유 패시브', 'passive')
            self.assertFalse(b._buff_fresh(other, a, '시험', 'owner_turn', ln), raw)
        self.assertFalse(b._buff_fresh(None, a, '오메가 프로토콜', 'owner_turn', end))
        self.assertFalse(b._buff_fresh(other, a, '시험', 'any_turn', end))

    def test_client_start_mapping(self):
        # Verify the real event boundary.
        d = unit_def('cristelle')
        ln = next(x for x in d.lines if x.eff.get('name') == '복수심(해제불가)' and x.slot == '특수기')
        self.assertEqual((line_kind(ln), ln.eff['dur']), ('own_pre', 3))
        root = static_path_or_none(ROOT)
        if root is None:
            skip_note('rules_e_test: private SE mapping 없음')
            return
        rows = json.loads((root / 'tables/SE_TEMPLET_SKILL_1.json').read_text(encoding='utf8'))['Data']
        row = next(x for x in rows if x['m_SEID'] == 10172011)
        self.assertEqual((row['m_Condition']['m_ActiveType'], row['m_BuffTargetType'], row['m_BuffLifeTurn']),
                         ('NSEAT_SKILL_START', 'NSETT_SELF', ln.eff['dur']))


class BreakTest(unittest.TestCase):
    def setup(self, name, **mc):
        b = battle([unit('a'), unit('b')], [unit('f', hp=10**8)], break_skill={'name': name},
                   mc=mc, opts={'coop': False, 'nova': False})
        b.break_points = 3
        return b

    def test_actor_gauge_survives_normal_action_and_kill(self):
        for mode in ('client', 'exclude'):
            for kill in (False, True):
                b = self.setup('스타피어서', break_gauge_actor=mode)
                a = b.allies[0]
                a.gauge = 10000
                if kill:
                    b.foes[0].hp = 1
                b.act(a)
                self.assertEqual(b.break_skill_uses, 1)
                self.assertEqual(a.gauge, 2000 if mode == 'client' else (10000 if kill else 0))
                self.assertEqual(a.actions, 0 if kill else 1)
                self.assertGreater(b.foes[0].taken, 0)

    def test_purify_extra_and_empty_targets(self):
        for scope in ('all_casts', 'main_only'):
            for via in ('coop', 'reaction', 'trigger', 'revenge'):
                b = self.setup('행성 정화', purify_nova_scope=scope)
                a, f = b.allies[0], b.foes[0]
                b._use_break_skill(a)
                b.team_nova = 0
                ctx = b.cast(a, a.d.skills['기본기'], extra=True, via=via, target=f)
                self.assertTrue(ctx.targets)
                self.assertGreater(f.taken, 0)
                self.assertEqual(b.team_nova, int(scope == 'all_casts'))
                self.assertEqual(b.rule_hits['purify_extra'], int(scope == 'all_casts'))
                b.team_nova = 0
                with patch.object(b, 'skill_targets', return_value=[]):
                    b.cast(a, a.d.skills['기본기'], extra=True, via=via)
                self.assertEqual(b.team_nova, 0)

    def test_omega_dispel_leaves_domain(self):
        for mode in ('client', 'fixed'):
            b = self.setup('큐브 과부하', omega_dispel=mode)
            a, f = b.allies[0], b.foes[0]
            b.act(a)
            self.assertEqual(b.break_skill_uses, 1)
            ctx = Ctx(f, f, f.d.skills['기본기'])
            ctx.targets, ctx.target = [a], a
            b.run_line(f, Line('[스킬 사용 후] 스킬 대상에게 (강화효과 해제) 효과 1개 해제', '기본기', 'active'), ctx)
            self.assertEqual(a.has('오메가 프로토콜'), mode == 'fixed')
            self.assertTrue(a.has('치트 매트릭스'))


class PreemptTest(unittest.TestCase):
    def rate(self, mode, own=-50, reduce=0, side=1):
        b = battle([unit('a'), unit('guard')], [unit('f'), unit('fguard')],
                   mc={'preemptive_reduce': mode}, seed=7)
        attacker = (b.foes if side else b.allies)[0]
        target, guard = b.allies if side else b.foes
        give(guard, '시험 강화', {'선제 방어 확률': 30})
        give(attacker, '고립', {'선제 방어 확률': own}, harmful=True)
        give(attacker, '무시', {'선제 방어 무시 확률': reduce})
        ctx = Ctx(attacker, attacker, attacker.d.skills['기본기'])
        return sum(b._preemptive_check(attacker, [target], ctx)[0] is guard for _ in range(1000))

    def test_isolation_does_not_reduce_opposing_defense(self):
        for side in (0, 1):
            self.assertTrue(250 <= self.rate('client', side=side) <= 350)
            self.assertEqual(self.rate('attacker_preempt', side=side), 0)
        self.assertEqual(self.rate('client', reduce=30), 0)
        self.assertTrue(550 <= self.rate('client', reduce=-30) <= 650)
        self.assertEqual(self.rate('client', own=50), self.rate('client', own=-50))
        self.assertEqual(_map_prop('선제 방어 무시 확률'), ('preempt_reduce', None))
        p = collections.defaultdict(float)
        self.assertTrue(_perm_apply({}, p, dict(stat='선제 방어 무시 확률', val=30)))
        self.assertAlmostEqual(p['preempt_reduce'], .3)

    def test_prop_consumers(self):
        self.assertTrue(mcmod._prop_known('선제 방어 무시 확률'))
        actor = Actor(unit('a'), 0, {'init_cd_frac': 0})
        buff = Buff('무시', {'선제 방어 무시 확률': 30}, 1, 2)
        buff.stacks = 1
        actor.buffs['무시'] = buff
        self.assertAlmostEqual(actor.mods()['preempt_reduce'], .3)


class CheckTest(unittest.TestCase):
    def test_reapply_updates_zero_turn_expiry(self):
        for dur in (2, math.inf):
            for scope in ('name', 'all'):
                b = battle([unit('a')], [unit('f')], mc={'check_buff_expiry': 'skill', 'check_buff_scope': scope})
                a = b.allies[0]
                def apply(turns):
                    b.add_effect(a, a, dict(name='시험 체크용 버프', props={}, max=1, dur=turns, times=1), None)
                apply(None)
                self.assertTrue(a.eff['시험 체크용 버프'].check)
                apply(dur)
                b._expire_checks(skill=True)
                self.assertTrue(a.has('시험 체크용 버프'))
                self.assertEqual(a.eff['시험 체크용 버프'].dur, dur)
                apply(None)
                b._expire_checks(skill=True)
                self.assertFalse(a.has('시험 체크용 버프'))

    def test_skill_expiry_precedes_coop_condition(self):
        for mode in ('action', 'skill'):
            a, other = unit('a'), unit('b')
            a.lines = [Line('[스킬 사용 후] 아군 전체에게 〈시험 체크용 버프〉', '기본기', 'active')]
            other.lines = [Line('[스킬 사용 시작 시] (조건: 내 공격 시 [자신이 보유: 시험 체크용 버프]) 자신에게 〈조건 통과〉 (1턴)',
                                '기본기', 'active')]
            b = battle([a, other], [unit('f', hp=10**8)], mc={'check_buff_expiry': mode},
                       opts={'coop': True, 'nova': False})
            a, other = b.allies
            give(other, '협공', {'협공 확률': 100})
            # Verify the real event boundary.
            seen = []
            own = b.run_own
            def observe(u, ctx, kind):
                if u is other and ctx.extra and kind == 'own_pre':
                    seen.append(a.has('시험 체크용 버프'))
                return own(u, ctx, kind)
            with patch.object(b, 'run_own', observe):
                b.act(a)
            self.assertEqual(seen, [mode == 'action'])
            self.assertEqual(other.has('조건 통과'), mode == 'action')
            self.assertGreater(b.foes[0].taken, 0)
            self.assertFalse(a.has('시험 체크용 버프'))
            self.assertEqual(b.rule_hits['check_expire_skill'], 2 * int(mode == 'skill'))

    def test_all_scope_keeps_explicit_infinite_and_finite(self):
        for scope in ('name', 'all'):
            a = unit('a')
            a.lines = [Line('[스킬 사용 후] 자신에게 〈무지속 강화〉 (공격력% +10%)', '기본기', 'active'),
                       Line('[스킬 사용 후] 자신에게 〈유한 강화〉 (2턴 / 공격력% +10%)', '기본기', 'active'),
                       Line('[스킬 사용 후] 자신에게 〈무한 강화〉 (지속 무한 / 공격력% +10%)', '기본기', 'active')]
            b = battle([a], [unit('f', hp=10**8)], mc={'check_buff_expiry': 'skill', 'check_buff_scope': scope})
            b.act(b.allies[0])
            self.assertEqual(b.allies[0].has('무지속 강화'), scope == 'name')
            self.assertTrue(b.allies[0].has('유한 강화'))
            self.assertTrue(b.allies[0].has('무한 강화'))


class StandardTest(unittest.TestCase):
    def test_actor_gauge_at_real_turn_start(self):
        use, fire = Battle._use_break_skill, Battle.fire
        for mode in ('client', 'exclude'):
            pending, gauges = {}, []
            def observe_use(b, actor=None):
                before = b.break_skill_uses
                result = use(b, actor)
                if b.break_skill_uses > before:
                    pending[b] = actor
                return result
            def observe_start(b, u, kind, ctx):
                if kind == 'own_ts' and pending.get(b) is u:
                    gauges.append(u.gauge)
                    del pending[b]
                return fire(b, u, kind, ctx)
            with patch.object(Battle, '_use_break_skill', observe_use), patch.object(Battle, 'fire', observe_start):
                r, _ = run_stage('clo/태양 회랑/FLOOR 200', {'break_gauge_actor': mode}, n=5,
                                 skill='스타피어서', party=['hilde', 'professor-m', 'cristelle', 'wedding-carmen'])
            self.assertGreater(r['outcome']['progress'], 0)
            self.assertGreater(r['break_skill']['uses'], 0)
            self.assertTrue(gauges)
            self.assertEqual(set(gauges), {2000.0} if mode == 'client' else {0.0})

    def test_defaults_and_real_paths(self):
        for k, old in LEGACY.items():
            self.assertNotEqual(MC_OPTS[k], old)
            self.assertEqual(MC_RULES[k]['legacy'], old)
        # 11/14 기본 전환(클라 수명 0 효과 전수 대조 뒤): skill/all
        self.assertEqual((MC_OPTS['check_buff_expiry'], MC_OPTS['check_buff_scope']), ('skill', 'all'))
        cases = [('clo/달 회랑/FLOOR 100', None, {'check_buff_expiry': 'skill'},
                  ['buff_fresh_other', 'buff_fresh_start', 'check_expire_skill']),
                 ('clo/태양 회랑/FLOOR 200', '행성 정화', {}, ['purify_extra']),
                 ('clo/태양 회랑/FLOOR 200', '스타피어서', {}, ['break_gauge_actor', 'preemptive_client_main'])]
        for stage, skill, override, expected in cases:
            r, hits = run_stage(stage, override, n=5, skill=skill,
                               party=['hilde', 'professor-m', 'cristelle', 'wedding-carmen'])
            self.assertGreater(r['outcome']['progress'], 0, r['outcome'])
            if skill:
                self.assertGreater(r['break_skill']['uses'], 0)
            for key in expected:
                self.assertGreater(hits[key], 0, (stage, key, hits))


def ab():
    for stage in ('clo/달 회랑/FLOOR 100', 'clo/태양 회랑/FLOOR 200', 'clo/태양 회랑/FLOOR 250'):
        for mode in ('self', 'client'):
            r, hits = run_stage(stage, {'buff_fresh_scope': mode}, n=30, skill='스타피어서')
            assert r['outcome']['progress'] > 0
            print(json.dumps(dict(stage=stage, mode=mode, outcome=r['outcome'], hits=hits), ensure_ascii=False))


def mutate():
    mutations = [
        ('_buff_fresh', "if shield or self.mc['buff_fresh_scope'] == 'client':", 'if shield:',
         [FreshTest('test_other_source_survives_current_end'), FreshTest('test_start_source_ticks_current_end')]),
        ('_use_break_skill', "u is not actor or self.mc['break_gauge_actor'] == 'client'", 'u is not actor',
         [BreakTest('test_actor_gauge_survives_normal_action_and_kill')]),
        ('cast', "purify = self.mc['purify_nova_scope']", "purify = 'main_only'",
         [BreakTest('test_purify_extra_and_empty_targets')]),
        ('_preemptive_check', "if self.mc['preemptive_reduce'] == 'client':", 'if False:',
         [PreemptTest('test_isolation_does_not_reduce_opposing_defense')]),
        ('_use_break_skill', "if name == '오메가 프로토콜' and self.mc['omega_dispel'] == 'client':", 'if False:',
         [BreakTest('test_omega_dispel_leaves_domain')]),
        ('cast', "if self.mc['check_buff_expiry'] == 'skill':", 'if False:',
         [CheckTest('test_skill_expiry_precedes_coop_condition')]),
        ('add_effect', "self.mc['check_buff_scope'] == 'all'", 'False',
         [CheckTest('test_all_scope_keeps_explicit_infinite_and_finite')]),
        ('add_effect', "refresh_check = self.mc['check_buff_expiry'] == 'skill' or self.mc['check_buff_scope'] == 'all'", 'refresh_check = False',
         [CheckTest('test_reapply_updates_zero_turn_expiry')]),
    ]
    for method, before, after, tests in mutations:
        src = textwrap.dedent(inspect.getsource(getattr(Battle, method)))
        assert before in src
        namespace = dict(mcmod.__dict__)
        exec(compile(src.replace(before, after), '<mutation>', 'exec'), namespace)
        with patch.object(Battle, method, namespace[method]):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite(tests))
        assert not result.errors, result.errors
        assert len(result.failures) == len(tests), (method, result.failures)
        print(method, ': assertion failures', len(result.failures), '/', len(tests))


if __name__ == '__main__':
    if '--ab' in sys.argv:
        ab()
    elif '--mutate' in sys.argv:
        mutate()
    else:
        unittest.main()
