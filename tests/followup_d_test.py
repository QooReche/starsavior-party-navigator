# -*- coding: utf-8 -*-
"""11/10 과제 D. --mutations: 메모리 변형 검사, --ab: 표준 육성 24판 비교."""
import collections
import io
import json
import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from cosmo_fixture import use_1022  # noqa: E402
use_1022()  # 시즌 1022 fixture(벨그라스 등 지난 시즌 모델 회귀)
from simkit import battle, give, unit
from battlesim.api import simulate
from battlesim.mc import Battle, Ctx, dead_keep_name, line_rest
from battlesim.metrics import unit_def
from battlesim.starsavior import cosmo_raid as C
from battlesim.starsavior.parser import Line


def effect(b, owner, target, text):
    ln = Line('[스킬 사용 후] ' + text, '기본기', 'active')
    ctx = Ctx(owner, owner, owner.d.skills['기본기'])
    ctx.target, ctx.targets = target, [target]
    b.run_line(owner, ln, ctx)


def revive(b, owner, target):
    effect(b, owner, target, '스킬 대상에게 부활(생명력 50%)')


def passive(phase, text):
    return Line('[' + phase + '] ' + text, '고유 패시브', 'passive')


class FollowupTest(unittest.TestCase):

    def test_wave_extra_turn(self):
        for mode in ('clear',):
            for carry in ('client',):
                for gauge in ('reset',):
                    b = battle([unit('a'), unit('dead')], [unit('one')])
                    a, dead = b.allies
                    b.kill(dead, b.foes[0])
                    a.extra_turn, a.gauge = True, 10000
                    dead.extra_turn, dead.gauge = True, 123
                    b.waves.append([unit('two')])
                    b.spawn_wave()
                    self.assertEqual((a.extra_turn, a.gauge), (False, 0) if mode == 'clear' else (True, 10000))
                    self.assertEqual((dead.extra_turn, dead.gauge), (True, 123))
                    self.assertEqual(b.rule_hits['wave_extra_turn'], int(mode == 'clear'))

    def test_new_wave_reservation_survives(self):
        for carry in ('client',):
            b = battle([unit('a')], [unit('one')])
            a = b.allies[0]
            a.d.lines = [passive('웨이브 시작 시', '자신에게 〈추가 턴〉')]
            b.waves.append([unit('two')])
            b.spawn_wave()
            self.assertTrue(a.extra_turn)

    def test_wave_spawn_and_battle_start(self):
        for mode in ('after_spawn_only',):
            for wave in (0, 1):
                foe = unit('foe')
                foe.lines = [passive('등장 후', '적 전체에게 〈등장 약화〉 (2턴 / 방어력% -10%)'),
                             passive('전투 시작 시', '자신에게 〈개전〉 (지속 무한 / 공격력% +10%)'),
                             passive('웨이브 시작 시', '적 전체에게 〈웨이브 약화〉 (2턴 / 방어력% -10%)')]
                b = battle([unit('a')], [foe if wave == 0 else unit('one')])
                if wave:
                    b.waves.append([foe])
                    b.spawn_wave()
                a, f = b.allies[0], b.foes[0]
                self.assertEqual(f.has('개전'), mode == 'all' or wave == 0)
                self.assertEqual(a.eff['등장 약화'].dur, 1 if wave else 2)
                self.assertEqual(a.eff['웨이브 약화'].dur, 2)
                self.assertEqual(b.rule_hits['wave_foe_battle_start'], int(wave == 1 and mode == 'after_spawn_only'))

    def test_turn_start_order(self):
        for mode in ('client',):
            for lethal in (False, True):
                b = battle([unit_def('ceres-sun-supporter'), unit('turn')], [unit('foe')],
                           opts={'coop': False})
                ceres, turn = b.allies
                ceres.eff.clear()
                e = give(turn, '연소', harmful=True, dur=1)
                e.dot, e.inst = ('atk', .2), [[b.foes[0], 1]]
                if lethal:
                    turn.hp = 1
                events = []
                fire, tick = b.fire, b._tick_dot_hot

                def watch_fire(owner, kind, ctx):
                    if kind in ('own_ts', 'ally_ts', 'enemy_ts'):
                        events.append(kind)
                    return fire(owner, kind, ctx)

                def watch_tick(u):
                    events.append('dot')
                    return tick(u)

                with patch.object(b, 'fire', watch_fire), patch.object(b, '_tick_dot_hot', watch_tick):
                    b.act(turn)
                self.assertEqual(ceres.stack('점화'), int(mode == 'client' or not lethal))
                self.assertEqual(turn.dead, lethal)
                if mode == 'client':
                    self.assertEqual(events[:4], ['own_ts', 'ally_ts', 'enemy_ts', 'dot'])
                    self.assertEqual(b.rule_hits['turn_start_order'], 1)
                else:
                    self.assertEqual(events[0], 'dot')

    def test_guard_immune_and_vampirism(self):
        heals = {}
        for mode in ('client',):
            for immune in ('무적', '스킬 피해 무효', 'both', 'none'):
                b = battle([unit('target'), unit('guard')], [unit('attacker')],
                           opts={'coop': False})
                target, guard = b.allies
                attacker = b.foes[0]
                give(guard, '수호', {'피해 분담(수호)': 50})
                attacker.d.passive['vampirism'] = .5
                attacker.hp = 1000
                if immune in ('무적', 'both'):
                    give(target, '무적')
                if immune in ('스킬 피해 무효', 'both'):
                    give(target, '스킬 피해 무효')
                hp = guard.hp
                b.cast(attacker, attacker.d.skills['기본기'], target=target)
                self.assertEqual(guard.hp < hp, immune == 'none' or (mode == 'off' and immune in ('무적', 'both')))
                self.assertEqual(target.has('스킬 피해 무효'), immune == 'both')
                heals[mode, immune] = attacker.healed
                self.assertGreater(attacker.healed, 0)

    def test_dnp_and_stage_fx_revive(self):
        for mode in ('client',):
            b = battle([unit('owner'), unit('target')], [unit('foe')],
                       ally_fx=[({'공격력%': 20}, None, None)])
            owner, target = b.allies
            c = C.Controller(b)
            c.boss, c.cfg, c.fx = b.foes[0], {'model': 'test', 'mechanics': []}, {'drain': {'pct': 5, 'max': 10}}
            for _ in range(3):
                c.post_hit(target, c.boss)
            self.assertTrue(target.eff[C.CH_DRAIN].dead_keep)
            self.assertEqual(target.maxhp, 8500)
            give(target, 'ordinary')
            b.kill(target, c.boss)
            self.assertNotIn('ordinary', target.eff)
            self.assertEqual(target.has(C.CH_DRAIN), mode == 'client')
            b._tick_any_turn()
            revive(b, owner, target)
            self.assertFalse(target.dead)
            self.assertEqual(target.maxhp, 8500 if mode == 'client' else 10000)
            self.assertEqual(target.hp, 4250 if mode == 'client' else 5000)
            self.assertAlmostEqual(target.mods()['atkp'], .2)
            self.assertEqual(b.rule_hits['dead_keep_dnp_revive'], int(mode == 'client'))

    def test_dnp_names_and_aggro(self):
        self.assertTrue(dead_keep_name('폭주 : 쇠락'))
        self.assertFalse(dead_keep_name('전투 모드'))  # 표 동명 충돌
        b = battle([unit('owner'), unit('target')], [unit('foe')])
        owner, target = b.allies
        effect(b, owner, target, '스킬 대상에게 〈폭주 : 쇠락〉 (지속 무한 / 생명력% -5%)')
        self.assertTrue(target.eff['폭주 : 쇠락'].dead_keep)
        e = give(target, '도발', src=b.foes[0], harmful=True)
        e.dead_keep = True
        b.kill(target, b.foes[0])
        b.kill(b.foes[0], owner)
        revive(b, owner, target)
        self.assertNotIn('도발', target.eff)
        self.assertIn('폭주 : 쇠락', target.eff)

    def test_revive_after_spawn(self):
        for mode in ('client',):
            b = battle([unit('owner'), unit('target')], [unit('foe')])
            owner, target = b.allies
            target.d.lines = [passive('등장 후', '자신에게 〈등장〉 (지속 무한 / 생명력% +20%)'),
                              passive('전투 시작 시', '자신에게 〈개전〉 (지속 무한 / 공격력% +10%)')]
            b.kill(target, b.foes[0])
            revive(b, owner, target)
            self.assertFalse(target.has('개전'))
            self.assertEqual(target.has('등장'), mode == 'client')
            self.assertEqual(target.hp, 6000 if mode == 'client' else 5000)
            self.assertEqual(b.rule_hits['revive_after_spawn'], int(mode == 'client'))

    def test_add_damage_guard(self):
        for mode in ('client',):
            for immune in ('none', '무적', '스킬 피해 무효'):
                b = battle([unit('a')], [unit('boss'), unit('guard'), unit('less')])
                target, guard, less = b.foes
                give(guard, '수호', {'피해 분담(수호)': 50})
                give(less, '수호', {'피해 분담(수호)': 25})
                if immune != 'none':
                    give(target, immune)
                give(target, 'shield').shield = 100
                give(guard, 'shield').shield = 100
                c = b.gb = C.Controller(b)
                c.pending_damage.append((target, 1000))
                b.flush_add_damage()
                split = mode == 'client' and immune == 'none'
                self.assertEqual(target.hp, 10000 if immune == '무적' else (9600 if split else 9100))
                self.assertEqual(guard.hp, 9600 if split else 10000)
                self.assertEqual(less.hp, 10000)
                self.assertEqual(target.has('스킬 피해 무효'), immune == '스킬 피해 무효')
                self.assertEqual(b.rule_hits['add_damage_guard'], int(split))

    def test_stat_selection_and_buff_timing(self):
        # 선택 규칙(high_*/low_*)은 능력치를 정수로 비교함. 최종 능력치는 이미 정수(클라 Floor)라 소수 차이 장면이 안 생김 →
        # 능력치 조회를 소수 값으로 바꿔 선택 규칙의 정수 비교만 봄(1000.4 와 1000 은 같은 값)
        b = battle([unit('a'), unit('b')], [unit('foe')])
        a, other = b.allies
        frac = lambda v, *args, **kw: 1000.4 if v is other else 1000.0   # noqa: E731
        for name, positive, negative in [('def_stat', 'high_def', 'low_def'), ('live_atk', 'high_atk', 'low_atk')]:
            with patch.object(b, name, frac):
                self.assertEqual(b._filter(a, b.allies, positive), b.allies, name)
                self.assertEqual(b._filter(a, b.allies, negative), b.allies, name)
        with patch.object(other, 'spd', lambda: 100.4), patch.object(a, 'spd', lambda: 100.0):
            self.assertEqual(b._filter(a, b.allies, 'high_spd'), b.allies)
            self.assertEqual(b._filter(a, b.allies, 'low_spd'), b.allies)
        with patch.object(b, 'def_stat', lambda v, *args, **kw: 1001.0 if v is other else 1000.0):
            self.assertEqual(b._filter(a, b.allies, 'high_def'), [other])     # 정수 차이는 그대로 갈림
        self.assertGreater(b.rule_hits['stat_select_int'], 0)

    def test_erode_cast_boundary(self):
        b = battle([unit('a')], [unit('boss')])
        c = C.Controller(b)
        c.boss, c.cfg = b.foes[0], {'bel': {'rot': {'defPct': 5, 'max': 99}}}
        c._put(c.boss, C.ERO, {}, maxs=99)
        c._erode(5, 5)
        self.assertEqual(c.boss.stack(C.ERO), 0)
        self.assertEqual(c.stats['rot_gain'], 0)
        c._erode(5, 5)
        self.assertEqual(c.stats['rot_gain'], 5)

    def test_private_dnp_table(self):
        static = os.environ.get('STARSAVIOR_STATIC')
        if not static:
            self.skipTest('STARSAVIOR_STATIC 없음')
        from tools.build_buff_dead_keep import build
        self.assertEqual(build(static), json.loads((ROOT / 'data/buff_dead_keep.json').read_text(encoding='utf8')))


CERES = ['ceres-sun-supporter', 'wedding-epindel', 'bunny-charlotte', 'cristelle']
WAVE_EXTRA = ['elisa', 'emily', 'epindel', 'fei']  # FLOOR 250(power_penalty off)에서 추가 턴 예약을 보유한 채 웨이브 전환


class StandardTest(unittest.TestCase):
    def test_wave_and_turn_start_paths(self):
        # «추가 턴 예약을 가진 채 웨이브 전환» 장면: 옛 self_enforce_target=last_target 고정은 스위치 삭제로 빼고
        # 기본 규칙에서 장면이 나는 편성(WAVE_EXTRA)으로 바꿈. power_penalty off 는 11/15 이전 흐름 고정(웨이브 경로와 무관).
        r = measured(WAVE_EXTRA, 'clo/태양 회랑/FLOOR 250', power_penalty='off')
        self.assertGreater(r['hits'].get('wave_extra_turn', 0), 0)
        r = measured(CERES, 'clo/태양 회랑/FLOOR 200')
        self.assertGreater(r['hits'].get('turn_start_order', 0), 0)

    def test_natural_drain_revive(self):
        counts = collections.Counter()
        original = Battle.run_special

        def watch(b, owner, ln, ctx, rest):
            pending = [(u, u.stack(C.CH_DRAIN), u.maxhp) for u in b.allies
                       if u.dead and u.has(C.CH_DRAIN)]
            result = original(b, owner, ln, ctx, rest)
            for u, stacks, maxhp in pending:
                if not u.dead:
                    self.assertEqual(u.stack(C.CH_DRAIN), stacks)
                    self.assertEqual(u.maxhp, maxhp)
                    self.assertLess(u.maxhp, u.maxhp0)
                    counts['drain_revive'] += 1
            return result

        with patch.object(Battle, 'run_special', watch):
            r = measured(REVIVE, COSMO)
        self.assertGreater(counts['drain_revive'], 0)
        self.assertGreater(r['hits'].get('dead_keep_dnp_revive', 0), 0)


def measured(party, stage, runs=24, **rules):
    counts = collections.Counter()
    original = Battle.run

    def watch(b):
        r = original(b)
        counts.update(b.rule_hits)
        return r

    with patch.object(Battle, 'run', watch):
        encounter = stage if isinstance(stage, dict) else {'stage': stage}
        r = simulate(party, encounter, {'build': 'standard', 'n_runs': runs, 'seed': 3, 'rules_override': rules})
    assert r['outcome']['progress'] > 0, r['outcome']
    return {'outcome': r['outcome'], 'hits': dict(counts)}



def mutations():
    # 합성 시험은 mode를 명시하므로 구현 메서드 안 분기를 메모리에서 강제 우회.
    import inspect
    import textwrap
    import battlesim.mc as M
    cases = [
        (Battle, 'spawn_wave', "if u.extra_turn:", 'if False:', ['test_wave_extra_turn']),
        (Battle, 'spawn_wave', "if (self.wave_i > 0", 'if (False', ['test_wave_spawn_and_battle_start']),
        (Battle, 'strike', "if (v.invincible() or v.on('스킬 피해 무효')):", 'if False:', ['test_guard_immune_and_vampirism']),
        (Battle, 'kill', "v.eff = {n: e for n, e in v.eff.items() if e.dead_keep}", 'v.eff = {}', ['test_dnp_and_stage_fx_revive']),
        (Battle, 'run_special', "if ln.phase == '등장 후':", 'if False:', ['test_revive_after_spawn']),
        (Battle, 'fixed_true_damage', "if not target.invincible() and not target.on('스킬 피해 무효'):", 'if False:', ['test_add_damage_guard']),
        (Battle, '_filter', "if st not in ('high_hp_rate', 'high_gauge', 'low_gauge'):", 'if False:', ['test_stat_selection_and_buff_timing']),
        (C.Controller, '_erode', 'if not pre:', "if not (self._stacks(boss, ERO) > 0 or self._stacks(boss, ROOT) > 0):", ['test_erode_cast_boundary']),
        (Battle, 'spawn_wave', 'self._carry_wave_effects()', 'pass', ['test_wave_spawn_and_battle_start']),
    ]
    for cls, name, old, new, tests in cases:
        good = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite(FollowupTest(t) for t in tests))
        assert good.wasSuccessful(), (name, '원본 시험부터 실패')
        src = textwrap.dedent(inspect.getsource(getattr(cls, name)))
        assert old in src, (name, old)
        ns = dict(vars(M if cls is Battle else C))
        exec(compile(src.replace(old, new), '<mutation>', 'exec'), ns)
        with patch.object(cls, name, ns[name]):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite(FollowupTest(t) for t in tests))
        assert result.failures and not result.errors, (name, result.failures, result.errors)
        print(name, tests, 'assertion failures:', len(result.failures))


REVIVE = ['elisa', 'wedding-epindel', 'bunny-charlotte', 'cristelle']
COSMO = {'cosmo_raid': {'boss': '벨그라스', 'step': 3, 'level': 6}}


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
