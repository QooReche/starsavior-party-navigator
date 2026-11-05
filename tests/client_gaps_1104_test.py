# -*- coding: utf-8 -*-
"""2026-11-04 클라(build 26314877) 근거 후보 스위치. 같은 날 4개(preemptive_defense·toughness_elem·break_point_hits·
break_auto_blocked_cc)는 기본=클라 값, legacy=옛 값으로 전환했고, 3개(dot_formula·react_hist_unit·immune_force_apply)는 옛 값 유지.
새 값과 legacy 값의 경로를 모두 명시해 검사한다.
실행: python -X utf8 -I tests/client_gaps_1104_test.py (계정 자료 없음, 공개 표준 육성·합성 유닛만)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p5_test import battle, give, hit, unit        # noqa: E402
import battlesim.mc as mcmod                       # noqa: E402
from battlesim.api import simulate                 # noqa: E402
from battlesim.mc import Ctx, FORCE_BUFF_NAMES     # noqa: E402
from battlesim.rules import MC_OPTS, MC_RULES      # noqa: E402

# 기본 = 클라 값으로 전환한 스위치: (기본, legacy)
SWITCHED = {'preemptive_defense': ('client_main', 'recognize'), 'toughness_elem': ('client', 'db'),
            'break_point_hits': ('window', 'once'), 'break_auto_blocked_cc': ('on', 'off'),
            # 11/05 전환(dot_formula·react_hist_unit·immune_force_apply)
            'dot_formula': ('client', 'legacy'), 'react_hist_unit': ('unit', 'slot'),
            'immune_force_apply': ('client', 'legacy')}
# 옛 값 유지(기본 == legacy): 없음
KEPT = {}
CUBE = {'name': '큐브 과부하', 'level': 1}
PARTY = ['sunshine-cat-smile', 'cristelle', 'white-pearl-luna', 'wedding-carmen']


def run_stage(stage, override, n_runs=4, seed=3, **extra):
    """표준 육성 시뮬을 돌리고 (결과, 판별 Battle의 rule_hits 합)을 돌려준다."""
    seen = []
    orig = mcmod.Battle.__init__

    def spy(self, *a, **kw):
        orig(self, *a, **kw)
        seen.append(self)
    mcmod.Battle.__init__ = spy
    try:
        r = simulate(PARTY, {'stage': stage}, dict({'seed': seed, 'n_runs': n_runs, 'build': 'standard',
                                                     'rules_override': override}, **extra))
    finally:
        mcmod.Battle.__init__ = orig
    hits = {}
    for b in seen:
        for k, v in b.rule_hits.items():
            hits[k] = hits.get(k, 0) + v
    return r, hits


def eff(name, dur=2):
    return {'name': name, 'props': {}, 'dur': dur, 'max': None, 'times': 1}


class DefaultsTest(unittest.TestCase):
    def test_defaults(self):
        for k, (value, legacy) in SWITCHED.items():
            self.assertEqual(MC_OPTS[k], value, k)
            self.assertEqual(MC_RULES[k]['legacy'], legacy, k)
            self.assertIn(legacy, MC_RULES[k]['alt'], k)
            self.assertEqual(MC_RULES[k]['grade'], 'code', k)
            self.assertTrue(MC_RULES[k]['source'] and MC_RULES[k]['note'], k)
        for k, v in KEPT.items():
            self.assertEqual(MC_OPTS[k], v, k)
            self.assertEqual(MC_RULES[k]['legacy'], v, k)
            self.assertTrue(MC_RULES[k]['source'] and MC_RULES[k]['note'], k)
        self.assertIn('legacy', MC_RULES['immune_force_apply']['alt'])


class PreemptiveClientMainTest(unittest.TestCase):
    def setup(self, mode, attacker_side=1):
        allies = [unit('victim', hp=10 ** 7), unit('guard', hp=10 ** 7)]
        foes = [unit('attacker', hp=10 ** 7)]
        if attacker_side == 0:
            allies, foes = foes, allies
        b = battle(allies, foes, mc={} if mode is None else {'preemptive_defense': mode})
        team = b.foes if attacker_side == 0 else b.allies
        attacker = b.allies[0] if attacker_side == 0 else b.foes[0]
        team[1].d.passive['preempt'] = 1.0
        return b, attacker, team[0], team[1]

    def test_main_action_only(self):
        # None = 규칙 기본값(client_main), recognize = legacy(가로채기 없음)
        for mode, buff, want_guard in [('client_main', None, True), ('client_main', '필중', False),
                                       ('client_main', '선제 방어 무시', False), ('on', None, True),
                                       (None, None, True), ('recognize', None, False)]:
            b, attacker, victim, guard = self.setup(mode)
            if buff:
                give(attacker, buff)            # 필중·은신·선제 방어 무시 = NoPreemptiveDefend 플래그 버프
            attacker.acting = True
            b.cast(attacker, attacker.d.skills['기본기'], target=victim)
            self.assertEqual(guard.hp < guard.maxhp, want_guard, (mode, buff))
            self.assertEqual(victim.hp < victim.maxhp, not want_guard, (mode, buff))
            self.assertEqual(b.rule_hits['preemptive_client_main'], int(mode in ('client_main', None) and want_guard))
        # 협공·반격 등 추가 시전(extra)·턴 밖 시전에는 클라 호출이 없음
        for acting, extra in [(True, True), (False, False)]:
            b, attacker, victim, guard = self.setup('client_main')
            attacker.acting = acting
            b.cast(attacker, attacker.d.skills['기본기'], extra=extra, target=victim)
            self.assertLess(victim.hp, victim.maxhp)
            self.assertEqual(guard.hp, guard.maxhp)

    def test_ally_attack_intercepted(self):
        for mode, want_guard in [('client_main', True), ('client', False)]:
            b, attacker, victim, guard = self.setup(mode, attacker_side=0)
            attacker.acting = True
            b.cast(attacker, attacker.d.skills['기본기'], target=victim)
            self.assertEqual(guard.hp < guard.maxhp, want_guard, mode)


class BreakPointWindowTest(unittest.TestCase):
    def test_repeat_hits_in_same_cast(self):
        got = {}
        for mode in ('once', 'window', None):          # None = 규칙 기본값(window), once = legacy
            foe = unit('f', hp=10 ** 9, sa=1, skills=[dict(slot='기본기', dm=0)])
            mc = {'break_skill_level': 'off'}
            if mode is not None:
                mc['break_point_hits'] = mode
            b = battle([unit('a')], [foe], break_skill=CUBE, mc=mc)
            a, f = b.allies[0], b.foes[0]
            sk = a.d.skills['기본기']
            sk.ab = 1
            ctx = Ctx(a, a, sk)
            ctx.targets, ctx.target = [f], f
            b.deal(a, ctx)                     # 격파 타격(+1)
            b.deal(a, ctx)                     # 같은 시전의 재타격: window 면 +1
            hit(b, a, f)                       # 다른 시전: 이미 격파 상태라 둘 다 적립 없음
            got[mode] = (b.break_points_gained, b.rule_hits['break_point_window'], f.broken)
        self.assertEqual(got['once'], (1, 0, True))
        self.assertEqual(got['window'], (2, 1, True))
        self.assertEqual(got[None], got['window'])


class ToughnessClientTest(unittest.TestCase):
    def tough(self, mode, ae, ve, ab, fixed=0):
        b = battle([unit('a', element=ae)], [unit('f', element=ve, sa=10)],
                   mc={} if mode is None else {'toughness_elem': mode})
        a, f = b.allies[0], b.foes[0]
        if fixed:
            give(a, '고정', {'강인도 고정 피해': fixed})
        _dmg, before, after = hit(b, a, f, ab=ab)
        return before - after, b.rule_hits['tough_client_lose']

    def test_elements(self):
        # 태양→달 불리: db 는 ab 유지, client 는 스킬값 0·고정 피해만
        self.assertEqual(self.tough('db', '태양', '달', 2), (2, 0))
        self.assertEqual(self.tough('client', '태양', '달', 2), (0, 1))
        self.assertEqual(self.tough('client', '태양', '달', 2, fixed=1), (1, 1))
        self.assertEqual(self.tough(None, '태양', '달', 2), (0, 1))       # 규칙 기본값 = client, legacy = db
        self.assertEqual(self.tough(None, '태양', '별', 0)[0], 1)
        # 태양→별 유리: client 는 ab 0 이어도 +1, on 은 ab>0 일 때만
        self.assertEqual(self.tough('client', '태양', '별', 0)[0], 1)
        self.assertEqual(self.tough('on', '태양', '별', 0)[0], 0)
        # 동일 속성: 가산 없음
        self.assertEqual(self.tough('client', '태양', '태양', 1)[0], 1)

    def test_reduce_stat(self):
        b = battle([unit('a', element='태양')], [unit('f', element='별', sa=10)], mc={'toughness_elem': 'client'})
        a, f = b.allies[0], b.foes[0]
        give(f, '감소', {'강인도 피해 감소': 2})
        _dmg, before, after = hit(b, a, f, ab=2)
        self.assertEqual(before - after, 1)       # 2 + 유리 1 - 감소 2


class DotClientTest(unittest.TestCase):
    def tick(self, mode, ae='태양', ve='별', pen=0, same_side=False):
        b = battle([unit('a', element=ae), unit('ally2')], [unit('f', element=ve, hp=10 ** 8, df=3000)],
                   mc={'dot_formula': mode, 'rand_range': [1.0, 1.0]})
        a, f = b.allies[0], b.foes[0]
        if pen:
            give(a, '관통', {'방어 관통': pen})
        tgt = b.allies[1] if same_side else f
        e = give(tgt, '연소', harmful=True)
        e.dot, e.inst = ('atk', 0.2), [[a, 3]]
        hp0 = tgt.hp
        b._tick_dot_hot(tgt)
        return hp0 - tgt.hp, b.rule_hits['dot_client']

    def test_elem_pen_same_side(self):
        legacy, n0 = self.tick('legacy')
        client, n1 = self.tick('client')
        self.assertGreater(legacy, 0)
        self.assertEqual((n0, n1), (0, 1))
        self.assertAlmostEqual(client / legacy, 1.05, delta=0.002)     # 유리 +5%
        lose, _ = self.tick('client', ae='별', ve='태양')
        self.assertLess(lose, legacy)
        pen_l, _ = self.tick('legacy', pen=50)
        pen_c, _ = self.tick('client', pen=50)
        self.assertEqual(pen_l, legacy)                                 # legacy 는 관통 무시
        self.assertGreater(pen_c, client)
        self.assertGreater(self.tick('legacy', same_side=True)[0], 0)
        self.assertEqual(self.tick('client', same_side=True)[0], 0)    # 같은 편 다른 유닛 지속 피해 0


class DotGuardTest(unittest.TestCase):
    """11/05: 지속 피해 수호 분담(NKM:1286-1308,7925-7928,17315-17319). 대상 몫은 방어 전 기본 피해에서 뗌, 수호자 몫은 수호자 기준."""

    def tick(self, mode, share=30, invincible=False, g_def=3000):    # share 는 퍼센트 단위(30 = 30%)
        b = battle([unit('a')], [unit('f', hp=10 ** 8, df=3000), unit('g', hp=10 ** 8, df=g_def)],
                   mc={'dot_formula': mode, 'rand_range': [1.0, 1.0]})
        a, f, g = b.allies[0], b.foes[0], b.foes[1]
        if share:
            give(g, '수호', {'피해 분담(수호)': share})
        if invincible:
            give(f, '무적')
        e = give(f, '연소', harmful=True)
        e.dot, e.inst = ('atk', 0.2), [[a, 3]]
        f0, g0 = f.hp, g.hp
        b._tick_dot_hot(f)
        return f0 - f.hp, g0 - g.hp, b.rule_hits['dot_guard']

    def test_split(self):
        none_f, none_g, _ = self.tick('client', share=0)
        legacy_f, legacy_g, n0 = self.tick('legacy')
        f, g, n1 = self.tick('client')
        self.assertGreater(none_f, 0)
        self.assertEqual((legacy_f, legacy_g, n0), (none_f, 0, 0))     # legacy 는 분담 없음
        self.assertEqual(n1, 1)
        self.assertAlmostEqual(f / none_f, 0.7, delta=0.01)             # 대상 몫 70%
        self.assertAlmostEqual(g / none_f, 0.3, delta=0.01)             # 같은 방어면 수호자 몫 30%
        # 수호자 몫은 수호자 방어로 다시 계산(방어가 낮으면 더 아픔)
        _f2, g_low, _ = self.tick('client', g_def=0)
        self.assertGreater(g_low, g)

    def test_invincible_target_not_shared(self):
        f, g, n = self.tick('client', invincible=True)
        self.assertEqual((f, g, n), (0, 0, 0))                          # 무적 대상은 지속 피해 0, 분담 없음


class ReactHistTest(unittest.TestCase):
    def test_unit_blocks_other_slot(self):
        got = {}
        for mode in ('slot', 'unit'):
            b = battle([unit('a', skills=[dict(slot='기본기', dm=100), dict(slot='특수기', dm=100)])], [unit('f')],
                       mc={'react_hist_unit': mode})
            a = b.allies[0]
            b._react_q, b._react_seen = [], set()
            b._react(a, a.d.skills['기본기'], None)
            b._react(a, a.d.skills['특수기'], None)
            b._react(a, a.d.skills['기본기'], None)
            got[mode] = (len(b._react_q), b.rule_hits['react_hist_unit'])
        self.assertEqual(got['slot'], (2, 0))
        self.assertEqual(got['unit'], (1, 2))


class ImmuneForceTest(unittest.TestCase):
    def test_force_apply_passes_immune(self):
        force = '기절(해제불가)'
        self.assertIn(force, FORCE_BUFF_NAMES)
        got = {}
        for mode in ('legacy', 'client'):
            b = battle([unit('a')], [unit('f')], mc={'immune_force_apply': mode})
            a, f = b.allies[0], b.foes[0]
            give(f, '면역')
            b.add_effect(a, f, dict(eff(force), ignore_resist=False), Ctx(a, a, a.d.skills['기본기']))
            b.add_effect(a, f, dict(eff('표적'), ignore_resist=True), Ctx(a, a, a.d.skills['기본기']))
            got[mode] = (force in f.eff, '표적' in f.eff, b.rule_hits['immune_force_pass'])
        self.assertEqual(got['legacy'], (False, True, 0))   # 현재: 저항 판정 약화만 거부
        self.assertEqual(got['client'], (True, False, 1))   # 클라: 강제 적용 통과, 그 밖 비양성 거부

    def test_pass_list_covers_delete_and_mixed_rejected(self):
        """11/05 통과 목록(IsPositive|DeleteBuff|ForceApplyEffect): 버프 해제(DeleteBuff)는 통과, 혼재 이름은 거부"""
        self.assertIn('버프 해제', mcmod.IMMUNE_PASS_NAMES)
        self.assertEqual(FORCE_BUFF_NAMES - mcmod.IMMUNE_PASS_NAMES, set())      # 기존 강제 강화 이름은 전부 포함
        self.assertNotIn('행동 게이지 감소', mcmod.IMMUNE_PASS_NAMES)      # 같은 이름에 거부 행(X)과 통과 행(X_FORCE) 혼재
        self.assertNotIn('공격력 감소', mcmod.IMMUNE_PASS_NAMES)
        b = battle([unit('a')], [unit('f')], mc={'immune_force_apply': 'client'})
        a, f = b.allies[0], b.foes[0]
        give(f, '면역')
        for name in ('버프 해제', '행동 게이지 감소'):
            b.add_effect(a, f, dict(eff(name), ignore_resist=False), Ctx(a, a, a.d.skills['기본기']))
        self.assertTrue('버프 해제' in f.eff and '행동 게이지 감소' not in f.eff, list(f.eff))

    def test_wave_start_mark_passes(self):
        """전투·웨이브 시작 표식(unique_enemy+ignore_resist, 물폭탄 SE 강제 행)은 면역을 통과"""
        b = battle([unit('a')], [unit('f')], mc={'immune_force_apply': 'client'})
        a, f = b.allies[0], b.foes[0]
        give(f, '면역')
        b.add_effect(a, f, dict(eff('표시'), ignore_resist=True, unique_enemy=True), Ctx(a, a, None))
        b.add_effect(a, f, dict(eff('표시2'), ignore_resist=True), Ctx(a, a, None))
        self.assertTrue('표시' in f.eff and '표시2' not in f.eff, list(f.eff))


class BreakBlockedCcTest(unittest.TestCase):
    def test_stun_and_taunt_block(self):
        for cc in ('기절', '수면', '도발'):
            for mode, uses in [('off', 1), ('on', 0), (None, 0)]:     # None = 규칙 기본값(on), off = legacy
                b = battle([unit('a')], [unit('f', hp=10 ** 9)], break_skill=CUBE,
                           mc={} if mode is None else {'break_auto_blocked_cc': mode})
                a = b.allies[0]
                give(a, cc, harmful=True)
                b.break_points = 3
                b._use_break_skill(a)
                self.assertEqual(b.break_skill_uses, uses, (cc, mode))
                self.assertEqual(b.break_points, 3 - 3 * uses)
                self.assertEqual(b.rule_hits['break_auto_blocked_cc'], 1 - uses)


class StageTest(unittest.TestCase):
    """표준 육성 실제 전투에서 새 값의 경로를 탔는지(횟수 > 0)와 진행도 > 0."""

    def test_stage_paths(self):
        stage = 'clo/태양 회랑/FLOOR 250'
        # 브레이크 두 스위치는 이 편성·스테이지에서 0회(엔진에 타수 모델이 없고 턴 유닛 CC 중 포인트 3이 드묾) — 경로는 위 합성 시험이 지킴.
        # 선제 방어(client_main)·면역(client)은 표준 편성에 확률/면역 보유자가 없어 합성 시험만 둠.
        cases = [({}, 'tough_client_lose', {}),                       # 규칙 기본값(client)이 실제 전투에서 탐
                 ({'toughness_elem': 'client'}, 'tough_client_lose', {}),
                 ({'dot_formula': 'client'}, 'dot_client', {}),
                 ({'react_hist_unit': 'unit'}, 'react_hist_unit', {}),
                 ({'break_auto_blocked_cc': 'on', 'break_point_hits': 'window'}, None, {'break_skill': CUBE})]
        report = {}
        for override, key, extra in cases:
            r, hits = run_stage(stage, override, **extra)
            prog = r['outcome']['progress']
            report[str(override)] = (prog, hits)
            self.assertGreater(prog, 0, override)
            if key:
                self.assertGreater(hits.get(key, 0), 0, (override, hits))
        print('  ', report)


if __name__ == '__main__':
    unittest.main()
