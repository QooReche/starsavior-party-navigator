# -*- coding: utf-8 -*-
"""자신이 시전하는 추가 발동(BI_ENFORCE, 대상 NSETT_SELF)의 적 대상 규칙 mc.self_enforce_target.
클라(build 26610546 NKM.decompiled.cs:5014-5030·13175-13183)는 EnforceAutoTargetId 가 가리키는 AUTO_SKILL_TARGET 규칙으로 실행할 때 적을 고른다
(0 이면 구원자 1·적 1001). 옛 엔진은 «시전자가 최근에 때린 적»(규칙 6)을 썼음 — 감시자 비틀린 시선(17 = 자신을 마지막으로 때린 적)이 힐데에게 갔던 원인.
실행: python -X utf8 -I tests/self_enforce_target_test.py"""
import json
import os
import random
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim import simulate, mc                               # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior import foe as F                        # noqa: E402
from battlesim.mc import Battle                                  # noqa: E402
from battlesim.metrics import unit_def                           # noqa: E402

# 광역기를 쓰는 표준 육성 편성(아모라·힐데 궁극기가 적 전체) — 성간 회랑 485 는 감시자 2기가 두 웨이브 모두 나옴
PARTY_AOE = ['amora', 'waltz-asherah', 'hilde', 'professor-m']
ST_SPOTTER = {'stage': 'clo/성간 회랑/FLOOR 485'}
RX_RECAST = re.compile(r'발동 후 (\d+)턴 재발동 불가')


def _data():
    with open(os.path.join(ROOT, 'data', 'foe_auto.json'), encoding='utf-8') as f:
        foe = json.load(f)['units']
    with open(os.path.join(ROOT, 'data', 'auto_skill.json'), encoding='utf-8') as f:
        ally = json.load(f)['self_enforce']
    return foe, ally


def test_default_client():
    assert MC_OPTS['self_enforce_target'] == 'client'


def test_spotter_data():
    """감시자(foe:1108:279) 비틀린 시선: COND_MON_SPOTTER_RING_PASSIVE_01 = EnforceAutoTargetId 17·SkillConditionId 5002·SeCoolTurn 3"""
    foe, _ = _data()
    got = foe['foe:1108:279']['enforce_self']['186:0']
    assert got == {'slot': '기본기', 'eat': 17, 'f': ['last_damager'], 'cool': 3, 'cond': 5002}, got


def test_table_matches_book_text():
    """표의 SeCoolTurn·조건 5002(광역 피격)가 엔진이 읽는 데이터북 문구와 같은지 — 엔진은 문구로 판정하므로 어긋나면 표만 맞고 동작은 틀림"""
    foe, ally = _data()
    raw = F.load_foe(ROOT)
    items = [(raw['s'][int(k.split(':')[0])]['ef'][int(k.split(':')[1])], sp)
             for v in foe.values() for k, sp in v.get('enforce_self', {}).items()]
    items += [(ln, sp) for rows in ally.values() for _sl, ln, sp in rows]
    assert len(items) > 200, len(items)
    bad = []
    for line, sp in items:
        m = RX_RECAST.search(line)
        if sp['cool'] is not None and (int(m.group(1)) if m else 0) != sp['cool']:
            bad.append(('cool', sp['cool'], line[:80]))
        if sp['cond'] == 5002 and '[스킬 대상 유형: 적 전체]' not in line:
            bad.append(('cond', line[:80]))
    assert not bad, bad[:5]


def _spotter_counters(mode, runs=24):
    """감시자 반격(추가 기본기) 기록: (대상, 그 순간 감시자를 마지막으로 때린 아군, 부모 시전이 광역인가, 감시자 행동 횟수)"""
    rec = []
    orig = mc.Battle.cast

    def cast(self, u, sk, extra=False, target=None, **kw):
        if extra and u.side == 1 and u.name == '감시자' and kw.get('via') is None and kw.get('parent') is not None:
            p = kw['parent']
            ld = getattr(u, 'last_damager', None)
            rec.append(dict(unit=id(u), battle=id(self), target=target, ld=ld if (ld is not None and not ld.dead) else None,
                            aoe=bool(p.skill is not None and p.skill.all), acts=getattr(u, 'actions', None)))
        return orig(self, u, sk, extra=extra, target=target, **kw)
    mc.Battle.cast = cast
    try:
        r = simulate(PARTY_AOE, ST_SPOTTER, {'seed': 5, 'n_runs': runs, 'build': 'standard',
                                             'rules_override': {'self_enforce_target': mode}})
    finally:
        mc.Battle.cast = orig
    assert r['outcome']['progress'] > 0, r['outcome']
    return rec


def test_spotter_counter_hits_last_damager():
    rec = _spotter_counters('client')
    assert len(rec) >= 20, len(rec)             # 경로가 실제로 탔는지
    with_ld = [x for x in rec if x['ld'] is not None]
    assert with_ld and all(x['target'] is x['ld'] for x in with_ld), sum(x['target'] is not x['ld'] for x in with_ld)
    # 조건 5002: 반격은 광역 공격에 맞았을 때만
    assert all(x['aoe'] for x in rec), sum(not x['aoe'] for x in rec)


def _spotter_battle(mode):
    """감시자 1기(데이터북 foe:1108:279, 성간 회랑 485 배치) vs 아모라(궁극기 = 적 전체)·프로페서M. 표준 판에선 감시자가
    한 번 반격하고 곧 끝나 재발동 제한을 못 보므로, 행동 시점을 직접 조종하는 전투 하나로 본다."""
    defs = [unit_def(k) for k in ('amora', 'professor-m')]
    spotter = F.FoeDef(F.load_foe(ROOT), 1108, 279)
    b = Battle(defs, [[spotter]], random.Random(7), opts=dict(nova_policy='auto', coop=False),
               mc={'self_enforce_target': mode})
    b.spawn_wave()
    s = b.foes[0]
    s.hp = s.maxhp = 1e12        # 시험 중 쓰러지지 않게
    for a in b.allies:
        a.hp = a.maxhp = 1e12
    return b, s


def _counters_of(b, fn):
    got = []
    orig = Battle.cast

    def cast(self, u, sk, extra=False, target=None, **kw):
        if extra and u.side == 1:
            got.append(target)
        return orig(self, u, sk, extra=extra, target=target, **kw)
    Battle.cast = cast
    try:
        fn()
    finally:
        Battle.cast = orig
    return got


def test_spotter_recast_and_condition():
    """조건 5002(광역 피격만)·SeCoolTurn 3({발동 후 3턴 재발동 불가} = 감시자 행동 3번 동안 막힘)·대상 = 마지막 타격자"""
    b, s = _spotter_battle('client')
    amora, pm = b.allies
    ult, basic = amora.d.skills['궁극기'], amora.d.skills['기본기']
    assert ult.all and not basic.all
    got = _counters_of(b, lambda: b.cast(amora, ult))
    assert got == [amora], got                               # 광역에 맞음 → 아모라에게 반격
    got = _counters_of(b, lambda: b.cast(amora, ult))
    assert got == [], got                                    # 같은 턴 다시: 재발동 제한
    s.actions += 2
    got = _counters_of(b, lambda: b.cast(amora, ult))
    assert got == [], got                                    # 2턴 뒤: 아직 막힘
    s.actions += 1
    got = _counters_of(b, lambda: b.cast(pm, pm.d.skills['기본기']))
    assert got == [], got                                    # 단일 공격엔 반격 없음(조건 5002)
    got = _counters_of(b, lambda: b.cast(amora, ult))
    assert got == [amora], got                               # 3턴 뒤 광역 → 다시 반격


def test_spotter_unit_legacy_differs():
    """옛 동작은 감시자가 «최근에 때린» 적을 고름 — 같은 장면에서 대상이 갈려야 시험이 차이를 봄"""
    for mode, want in (('client', 'amora'), ('last_target', 'pm')):
        b, s = _spotter_battle(mode)
        amora, pm = b.allies
        s.last_target = pm
        got = _counters_of(b, lambda: b.cast(amora, amora.d.skills['궁극기']))
        assert got == [amora if want == 'amora' else pm], (mode, got)


def test_ally_default_rule1_boss_first():
    """구원자 EnforceAutoTargetId 0 = 규칙 1(무적 아님 → 보스 → 정예 → 유리 상성 → 생명력 비율 최저 → 최대 생명력 최저):
    세레스(해바라기 서포터) «먼지 포착» 추가 특수기는 살아 있는 보스가 있으면 보스를 친다"""
    rec = []
    orig = mc.Battle.cast

    def cast(self, u, sk, extra=False, target=None, **kw):
        if extra and u.side == 0 and u.key == 'ceres-sun-supporter' and kw.get('via') is None and target is not None:
            bosses = [v for v in self.targetable(1) if getattr(v.d, 'boss', False)]
            rec.append((target, bosses))
        return orig(self, u, sk, extra=extra, target=target, **kw)
    mc.Battle.cast = cast
    try:
        r = simulate(['ceres-sun-supporter', 'carnelia', 'sunshine-cat-smile', 'hilde'], {'stage': 'clo/달 회랑/FLOOR 100'},
                     {'seed': 1, 'n_runs': 10, 'build': 'standard'})
    finally:
        mc.Battle.cast = orig
    assert r['outcome']['progress'] > 0
    boss_cases = [(t, b) for t, b in rec if b]
    assert len(boss_cases) >= 8, (len(rec), len(boss_cases))
    assert all(t in b for t, b in boss_cases), sum(t not in b for t, b in boss_cases)


def test_ally_unit_rule_vs_legacy():
    """구원자 쪽 결정적 확인: 세레스(해바라기 서포터) 자신 추가 특수기(EnforceAutoTargetId 0 = 규칙 1, 보스 우선)를 직접 실행.
    최근에 때린 적을 졸개로 두면 client 는 보스, 옛 동작은 졸개. (카르넬리아 4 = 무작위는 옛 엔진도 설명문 «무작위 적»으로 이미 무작위라 차이 없음)"""
    from battlesim.mc import Ctx
    raw = F.load_foe(ROOT)
    for key, mode in (('ceres-sun-supporter', 'client'), ('ceres-sun-supporter', 'last_target')):
        boss, minion = F.FoeDef(raw, 1157, 281), F.FoeDef(raw, 1108, 279)
        b = Battle([unit_def(key)], [[minion, boss]], random.Random(3), opts=dict(nova_policy='auto', coop=False),
                   mc={'self_enforce_target': mode})
        b.spawn_wave()
        me = b.allies[0]
        for u in b.allies + b.foes:
            u.hp = u.maxhp = 1e12
        m_u = next(f for f in b.foes if not f.d.boss)
        ln = next(x for x in b.lines_of(me) if x.eff.get('kind') == 'extra_cast' and x.eff.get('target') == '자신')
        assert b.self_enforce_spec(me, ln) is not None or mode == 'last_target', key
        for i in range(12):
            me.last_target = m_u
            got = _counters_of_ally(b, lambda: b._exec_line(me, ln, Ctx(me, me, me.d.skills[ln.eff['slot']])))[:1]   # 첫 시전만(그 안에서 이어진 시전 제외)
            want = m_u if mode == 'last_target' else next(f for f in b.foes if f.d.boss)
            assert got and all(t is want for t in got), (key, mode, [getattr(t, 'name', None) for t in got])


def _counters_of_ally(b, fn):
    got = []
    orig = Battle.cast

    def cast(self, u, sk, extra=False, target=None, **kw):
        if extra and u.side == 0:
            got.append(target)
        return orig(self, u, sk, extra=extra, target=target, **kw)
    Battle.cast = cast
    try:
        fn()
    finally:
        Battle.cast = orig
    return got


def test_foe_probabilistic_random():
    """확률 자신 추가 발동도 같은 경로: 살육의 포식자(foe:309:4) «내 공격 후 50% 확률로 기본기 추가 발동» = EnforceAutoTargetId 4(무작위).
    client 는 실행할 때 무작위로 정해 대상을 넘기고(두 아군 모두 나옴), 옛 동작은 대상 없이 넘겨 시전 쪽 기본 규칙에 맡김."""
    from battlesim.mc import Ctx
    raw = F.load_foe(ROOT)
    for mode in ('client', 'last_target'):
        b = Battle([unit_def(k) for k in ('amora', 'professor-m')], [[F.FoeDef(raw, 309, 4)]], random.Random(11),
                   opts=dict(nova_policy='auto', coop=False), mc={'self_enforce_target': mode})
        b.spawn_wave()
        foe = b.foes[0]
        for u in b.allies + b.foes:
            u.hp = u.maxhp = 1e12
        ln = next(x for x in b.lines_of(foe) if '확률로 기본기 추가 발동' in x.raw)
        assert (b.self_enforce_spec(foe, ln) is not None) == (mode == 'client')
        targets = []
        for _ in range(40):
            b.recast.clear()
            got = []
            orig = Battle.cast

            def cast(self, u, sk, extra=False, target=None, **kw):
                if extra and u is foe and not got:
                    got.append(target)
                return orig(self, u, sk, extra=extra, target=target, **kw)
            Battle.cast = cast
            try:
                b._exec_line(foe, ln, Ctx(foe, foe, foe.d.skills['기본기']))
            finally:
                Battle.cast = orig
            targets += got
        assert 8 <= len(targets) <= 32, len(targets)            # 50% 확률
        if mode == 'client':
            assert None not in targets and len({id(t) for t in targets}) == 2, [getattr(t, 'name', None) for t in targets]
        else:
            assert set(targets) == {None}, targets


def test_pick_timing_exec_vs_book():
    """대상 고르는 때는 enforce_target 을 따름: exec(클라) = 실행 직전 규칙 재적용, book = 예약 때 고른 대상.
    예약 뒤 «마지막 타격자»가 바뀌면 exec 는 새 타격자, book 은 옛 타격자. _exec_pick 을 끄면 exec 단언이 실패함."""
    from battlesim.mc import Ctx
    for et, want_new in (('exec', True), ('book', False)):
        b, s = _spotter_battle('client')
        b.mc['enforce_target'] = et
        b.mc['enforce_timing'] = 'queue'
        b._react_q = []                         # 행동 안(예약 큐가 있는 상태)
        amora, pm = b.allies
        s.last_damager = amora
        fn = b._self_enforce_fn(s, s.d.skills['기본기'], ['last_damager'], Ctx(s, s, s.d.skills['기본기']))
        s.last_damager = pm                     # 예약 뒤 다른 아군이 때림
        b._react_q = None
        got = _counters_of(b, fn)
        assert got == [pm if want_new else amora], (et, got)


TESTS = [test_default_client, test_spotter_data, test_table_matches_book_text, test_spotter_counter_hits_last_damager,
         test_spotter_recast_and_condition, test_spotter_unit_legacy_differs, test_ally_default_rule1_boss_first, test_ally_unit_rule_vs_legacy, test_foe_probabilistic_random, test_pick_timing_exec_vs_book]

if __name__ == '__main__':
    for t in TESTS:
        t()
        print('OK', t.__name__)
    print('ALL OK', len(TESTS))
