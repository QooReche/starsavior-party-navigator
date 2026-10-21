# -*- coding: utf-8 -*-
"""P5 시험: 육성 프리셋(장비 주옵·세트·부옵·여정·특수 잠재력, 스탯 순서), 강인도·브레이크, 「피해 제한」·〈불사〉, 전투력 보정,
새로 지원한 적 효과(게이지 설정·대상 생명력 연쇄·쿨타임 증가·개수당 피해·강화 불가·쿨 초기화·조건 키), 「행동 시/후」 시점,
사전 계산 연결(콘텐츠별 육성·민감도 행·연쇄 깊이 관문).

  python -X utf8 -I tests/p5_test.py            # 전부(운영 파일을 쓰지 않는다)
  python -X utf8 -I tests/p5_test.py tough      # 이름에 이 글자가 든 시험만

각 시험은 해당 구현을 일부러 깨뜨렸을 때 실패하는 것을 확인했다(docs/sim_p5_report.md 「시험」)."""
import math
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from battlesim.api import _CustomFoe, power_pen, simulate  # noqa: E402
from battlesim.mc import Battle, Ctx, Eff, support_report  # noqa: E402
from battlesim.starsavior import build as bld  # noqa: E402
from battlesim.starsavior.data import get_db  # noqa: E402
from battlesim.starsavior.parser import Line, UnitDef  # noqa: E402
from battlesim.starsavior.stats import calc_stats  # noqa: E402

FIXED = dict(rand_range=[1.0, 1.0])


def unit(name='u', role='스트라이커', hp=10000, atk=1000, df=1000, spd=100, cr=0, element=None, sa=10, skills=None):
    return _CustomFoe(dict(name=name, role=role, hp=hp, atk=atk, **{'def': df}, spd=spd, cr=cr, cd=0, er=0, der=0, element=element,
                           sa=sa, skills=skills or [dict(slot='기본기', dm=100)]), 0)


def battle(allies, foes, mc=None, seed=1, **kw):
    b = Battle(allies, [foes], random.Random(seed), mc=dict(FIXED, **(mc or {})), **kw)
    b.spawn_wave()
    return b


def give(u, name, props=None, src=None, harmful=False, dur=3, stacks=1):
    e = Eff(name, props or {}, 1, dur, src or u, harmful)
    e.stacks = stacks
    u.eff[name] = e
    u._m = None
    return e


def hit(b, a, v, slot='기본기', ab=None):
    """a 가 v 를 스킬 한 번 치고 (피해, 강인도 전후) 를 돌려준다"""
    sk = a.d.skills[slot]
    if ab is not None:
        sk.ab = ab
    hp0, sa0 = v.hp, v.sa
    ctx = Ctx(a, a, sk)
    ctx.targets, ctx.target = [v], v
    b.deal(a, ctx)
    return hp0 - v.hp, sa0, v.sa


# ---------------------------------------------------------------- 육성 프리셋
def test_build_light_values():
    """light = 주옵(T2 레전더리 +15) + 세트만: 페이(가이드 목걸이 속도·반지 공격력%·파괴4+투지2)의 장비 합이 데이터 값과 같다"""
    db = get_db()
    b = bld.make_build(db, 'fei', db.units['fei'], 'light')
    exp = {'atk': 150 + 15 * 15, 'hp': 600 + 120 * 15, 'def': 60 + 10 * 15, 'spd': (18 + 15) * 2, 'atkP': 250 + 100 * 15 + 500,
           'cd': 4000, 'er': 500}
    got = {k: round(v) for k, v in b['gear'].items()}
    return got == exp and b['summary']['sets'] == ['파괴(4)', '투지(2)'], '장비 합 %s (기대 %s)' % (got, exp)


def test_stat_order_journey():
    """스탯 순서: floor(((기본+레벨+여정) x (1+공명%) + 공명 정수) x (1+장비%) + 장비 정수) — 여정은 공명%·장비%를 받는다"""
    db = get_db()
    u = db.units['fei']
    ST = db.main['stat']
    m = ST['units'][str(u['id'])]
    t = ST['tmpl'][m['sid']]
    R = ST['res'].get(str(u['id']), [])[:10]
    rp = sum(v for _, sts in R for k, v in sts if k == 'atkP') * 1e-4
    rf = sum(v for _, sts in R for k, v in sts if k == 'atk')
    J, gp, gf = 1500, 2000, 375
    exp = math.floor(((t['base']['atk'] + t['grow']['atk'] * 199 + J) * (1 + rp) + rf) * (1 + gp * 1e-4) + gf)
    got = calc_stats(db, u, 200, 10, 0, 'fixed', {'atkP': gp, 'atk': gf}, journey={'atk': J})['atk']
    eh = calc_stats(db, u, 200, 10, 0, 'fixed', {}, journey={'eh': 2060})['eh'] - calc_stats(db, u)['eh']
    return got == exp and eh == 2060, '공격력 %s (기대 %s), 여정 효과 적중 단순 합 +%s' % (got, exp, eh)


def test_potential_pick():
    """잠재력: 「AX5(치확 부족)/AX6(95% 이상)」은 특수 잠재력 전 치명타 확률로 고름, 번호 없는 「BX」= BX2, 상시 스탯은 장비 단계로(passive 아님)"""
    db = get_db()
    R = bld.build_rules()
    saved = R['potential_pick']['crit_threshold']
    try:
        a5 = UnitDef(db, 'fei', build='standard').build['potential']    # 페이 = AX1 / XX2 -> AX1
        p_lo = UnitDef(db, 'professor-m', build='standard').build['potential']
        R['potential_pick']['crit_threshold'] = 0
        p_hi = UnitDef(db, 'professor-m', build='standard').build['potential']
    finally:
        R['potential_pick']['crit_threshold'] = saved
    bx = UnitDef(db, 'frey', build='standard')
    none = UnitDef(db, 'frey')
    lines = [ln.raw for ln in bx.lines if ln.slot == '잠재력']
    ok = (a5 == 'AX1' and p_lo == 'AX5' and p_hi == 'AX6' and bx.build['potential'] == 'BX2' and
          abs(bx.passive['hpp'] - none.passive['hpp']) < 1e-12 and any('25% 확률로 회복' in r for r in lines))
    return ok, '페이 %s, 프로페서M 기본 %s / 기준 0 이면 %s, 프레이 %s 잠재력 줄 %d개, passive 생명력%% 변화 %.3f' % (
        a5, p_lo, p_hi, bx.build['potential'], len(lines), bx.passive['hpp'] - none.passive['hpp'])


def test_build_missing_is_error():
    """가이드 세팅이 없는 구원자는 use_class_default 목록에 있을 때만 클래스 기본값, 아니면 BuildError(조용히 넘어가지 않음)"""
    db = get_db()
    R = bld.build_rules()
    ok1 = UnitDef(db, 'gwen', build='standard').build['source'] == 'class_default'
    saved = list(R['use_class_default'])
    try:
        R['use_class_default'].remove('gwen')
        try:
            UnitDef(db, 'gwen', build='standard')
            ok2 = False
        except bld.BuildError:
            ok2 = True
    finally:
        R['use_class_default'][:] = saved
    return ok1 and ok2, '목록에 있을 때 클래스 기본값 %s / 목록에서 빼면 오류 %s' % (ok1, ok2)


def test_build_speed_range():
    """standard 프리셋 속도(리더 제외)가 커뮤니티 엔드게임 실측 157~186 범위 안(대표 구원자 12명)"""
    db = get_db()
    keys = ['gwen', 'fei', 'professor-m', 'amora', 'waltz-asherah', 'wedding-carmen', 'frey', 'haydee', 'emily', 'ceres', 'elisa', 'luna']
    sp = {}
    for k in keys:
        d = UnitDef(db, k, build='standard')
        sp[k] = round(d.stats['spd'] * (1 + d.passive['spdp']) + d.passive['spdf'])
    return all(157 <= v <= 186 for v in sp.values()), '속도 %s' % sp


# ---------------------------------------------------------------- 강인도·브레이크
def test_toughness_break():
    """강인도 2 인 적을 ab 2 스킬로 치면 브레이크: 게이지 0, 다음 타격 감소 합 −15%p(피해 감소 30% -> 15%), 다음 자기 턴에 전회복"""
    a, f = unit('a', skills=[dict(slot='기본기', dm=100), dict(slot='특수기', dm=100, cd=3)]), unit('foe', hp=10 ** 9, sa=2)
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    give(F, '장막', {'받는 피해 감소': 30.0}, dur=9)
    F.gauge = 5000.0
    d1, s0, s1 = hit(b, A, F, '특수기', ab=2)
    broke, gauge0 = F.broken, F.gauge
    d2, _, _ = hit(b, A, F, '특수기', ab=2)
    b.act(F)
    ratio = d2 / d1
    ok = broke and gauge0 == 0 and abs(ratio - 0.85 / 0.70) < 0.01 and not F.broken and F.sa == 2
    return ok, '강인도 %s->%s, 브레이크 %s, 게이지 %s, 피해비 %.3f(기대 %.3f), 턴 뒤 강인도 %s·격파 %s' % (
        s0, s1, broke, gauge0, ratio, 0.85 / 0.70, F.sa, F.broken)


def test_tough_elem_and_fixed():
    """강인도 상성 옛 규칙(on): 불리하면 ab 몫 0, 유리하면 +1(ab>0 일 때), 「강인도 고정 피해」는 상성과 무관. 회피하면 안 깎임.
    기본 규칙(db, starsavior-db): 기본값(유리 1, 아니면 0) + ab + 고정 — 유리하면 ab 0 기본기도 1, 불리해도 ab 는 그대로"""
    out, db = {}, {}
    for el, fixed in (('태양', 0), ('별', 0), ('달', 0), ('달', 1)):
        for mode, dst in (('on', out), ('db', db)):
            a, f = unit('a', element=el), unit('foe', hp=10 ** 9, sa=10, element='별')
            b = battle([a], [f], mc=dict(toughness_elem=mode))
            A, F = b.allies[0], b.foes[0]
            if fixed:
                give(A, '파쇄', {'강인도 고정 피해': 1.0})
            hit(b, A, F, '기본기', ab=1)
            dst[(el, fixed)] = 10 - F.sa
    a, f = unit('a', element='태양'), unit('foe', hp=10 ** 9, sa=10, element='별')
    b = battle([a], [f], mc=dict(toughness_elem='db'))
    hit(b, b.allies[0], b.foes[0], '기본기', ab=0)
    db_basic0 = 10 - b.foes[0].sa
    a, f = unit('a'), unit('foe', hp=10 ** 9, sa=10)
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    give(F, '회피', {'회피율': 100.0})
    hit(b, A, F, '기본기', ab=2)
    ev = 10 - F.sa
    # 태양 -> 별 유리(+1), 별 -> 별 보통, 달 -> 별 불리(0), 불리 + 고정 1 = 1
    ok = (out == {('태양', 0): 2, ('별', 0): 1, ('달', 0): 0, ('달', 1): 1} and ev == 0
          and db == {('태양', 0): 2, ('별', 0): 1, ('달', 0): 1, ('달', 1): 2} and db_basic0 == 1)
    return ok, '옛 규칙 %s, db %s, db 유리 ab0 %s, 회피 시 %s' % (out, db, db_basic0, ev)


def test_ally_break_gauge_and_coop():
    """구원자 브레이크: 기본(skip)은 게이지 유지 + 다음 자기 턴은 회복에 쓰고 행동 없음(사용자 설명 2026-10-21), reset 이면 즉시 게이지 0,
    keep 이면 유지·정상 행동. 격파 중에는 협공 후보에서 빠짐"""
    res = {}
    for mode in ('keep', 'reset', None):
        a, f = unit('a', sa=1), unit('foe', hp=10 ** 9)
        b = battle([a], [f], mc=dict(ally_break_gauge=mode) if mode else None)
        A, F = b.allies[0], b.foes[0]
        A.gauge = 6000.0
        hit(b, F, A, '기본기', ab=1)
        res[mode] = (A.broken, A.gauge)
    no_react = b.no_react(b.allies[0])
    acted = {}
    for mode in ('skip', 'keep'):
        a, f = unit('a', sa=1), unit('foe', hp=10 ** 9)
        bb = battle([a], [f], mc=dict(ally_break_gauge=mode))
        A, F = bb.allies[0], bb.foes[0]
        hit(bb, F, A, '기본기', ab=1)
        hp0 = F.hp
        bb.act(A)
        acted[mode] = (A.broken, F.hp < hp0)      # 회복했는가, 그 턴에 공격했는가
    ok = (res == {'keep': (True, 6000.0), 'reset': (True, 0.0), None: (True, 6000.0)} and no_react
          and acted == {'skip': (False, False), 'keep': (False, True)})
    return ok, '결과 %s / 다음 턴 %s' % (res, acted)


def test_break_recovery_turn_effects():
    """연속 회복 턴도 지속 효과·턴 이벤트를 처리하며 스킬/행동 이벤트는 발생하지 않는다."""
    out = {}
    for mode in ('skip', 'keep', 'reset'):
        for shield_tick in ('turn_start', 'turn_end'):
            b = battle([unit('a', hp=10**9), unit('ally')], [unit('foe', hp=10**9)],
                       mc=dict(ally_break_gauge=mode, shield_tick=shield_tick), opts=dict(coop=False))
            a, ally = b.allies
            f = b.foes[0]
            a.d.lines = [Line('[턴 종료 시] 자신에게 행동 게이지 1%p 증가', '고유 패시브', 'passive')]
            for owner, triggers in ((a, ('내 턴 시작 시', '내 행동 시', '내 행동 후')),
                                    (ally, ('아군 턴 시작 시', '아군 행동 시', '아군 행동 후')),
                                    (f, ('적 턴 시작 시', '적 행동 후'))):
                owner.d.lines.extend(Line('[스킬 사용 후] (조건: %s) 자신에게 〈%s〉 (지속 무한) {최대 9중첩}'
                                          % (trig, trig), '고유 패시브', 'passive') for trig in triggers)
            give(a, '공격력 증가', {'공격력%': 10}, dur=2)
            give(a, '무한 효과', dur=math.inf)
            give(a, '새 효과', dur=1).fresh = True
            give(a, '보호막', dur=2).shield = 1000
            dot = give(a, '연소', src=f, harmful=True, dur=2, stacks=2)
            dot.dot, dot.inst = ('atk', 0.1), [[f, 1], [f, 2]]
            give(a, '체크용 효과').check = True
            b.check_pending.append((a, '체크용 효과'))
            a.cd['특수기'] = 3
            states, losses = [], []
            for _ in range(3):
                a.broken, a.sa = True, 0
                hp0 = a.hp
                b.act(a)
                losses.append(hp0 - a.hp)
                states.append((a.eff['공격력 증가'].dur if a.has('공격력 증가') else 0,
                               a.stack('연소'), a.has('새 효과'), a.has('보호막')))
                assert not a.broken and a.sa == a.sa_max and not a.acting
            assert states == [(1, 1, True, True), (0, 0, False, False), (0, 0, False, False)], states
            assert a.has('무한 효과') and not a.has('체크용 효과') and not b.check_pending
            assert a.gauge == 100, a.gauge
            assert losses[0] == 2 * losses[1] and losses[1] > 0 and losses[2] == 0, losses
            assert a.cd['특수기'] == 0
            assert (a.stack('내 턴 시작 시'), ally.stack('아군 턴 시작 시'), f.stack('적 턴 시작 시')) == (3, 3, 3)
            actions = 0 if mode == 'skip' else 3
            assert sum(a.cast_count.values()) == actions, dict(a.cast_count)
            assert (a.stack('내 행동 시'), a.stack('내 행동 후'), ally.stack('아군 행동 시'),
                    ally.stack('아군 행동 후'), f.stack('적 행동 후')) == (actions,) * 5
            out[(mode, shield_tick)] = states
    return True, str(out)


def test_break_conditions():
    """「대상 브레이크: 예」·「대상 강인도 없음: 예」 조건은 격파 상태에서만 참(P4 까지는 늘 거짓)"""
    a, f = unit('a'), unit('foe', hp=10 ** 9, sa=1)
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    ln = Line('[스킬 사용 시작 시] (조건: 내 공격 시 [대상 브레이크: 예]) 자신에게 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}', '고유 패시브', 'passive')
    sk = A.d.skills['기본기']
    c = Ctx(A, A, sk)
    c.targets, c.target = [F], F
    before = b.cond_ok(A, ln, c)
    hit(b, A, F, '기본기', ab=1)
    after = b.cond_ok(A, ln, c)
    return (not before) and after, '격파 전 %s / 후 %s' % (before, after)


# ---------------------------------------------------------------- 피해 제한·불사
def test_damage_limit():
    """「피해 제한」: 대미지 브레이크(40% 아래로 안 떨어짐, 1회) / 불사의 육신(사망 피해 -> 1% + 〈불사〉 1턴, 1회 소모) / 〈불사〉 중엔 1 남김"""
    a, f = unit('a', atk=10 ** 7), unit('foe', hp=10000)
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    give(F, '불사의 육신', {}, dur=math.inf)
    b.apply_damage(A, F, 50000, 'hit')
    s1 = (F.dead, F.hp, F.has('불사'), '불사의 육신' in F.eff)
    b.apply_damage(A, F, 50000, 'hit')
    s2 = (F.dead, F.hp)
    F.eff.pop('불사')
    F._m = None
    b.apply_damage(A, F, 50000, 'hit')
    s3 = F.dead
    g = unit('g', hp=10000)
    b2 = battle([unit('x')], [g])
    G = b2.foes[0]
    give(G, '대미지 브레이크', {}, dur=math.inf)
    b2.apply_damage(None, G, 9000, 'hit')
    t1 = G.hp
    b2.apply_damage(None, G, 3500, 'hit')
    t2 = G.hp
    ok = s1 == (False, 100.0, True, False) and s2 == (False, 1.0) and s3 and t1 == 4000 and t2 == 500
    return ok, '불사의 육신 %s -> 불사 중 %s -> 불사 끝 사망 %s / 대미지 브레이크 %s -> %s' % (s1, s2, s3, t1, t2)


# ---------------------------------------------------------------- 전투력 보정
def test_power_penalty():
    """전투력 보정: databook 표(비율 80% = 아군 0.85·적 1.15, 50% 미만 = 0.10·1.90, 90% 이상 없음), model 이면 결과에 배율, 플래시 미적용"""
    db = get_db()
    p80, p40, p95 = power_pen(8000, 10000, db), power_pen(4000, 10000, db), power_pen(9500, 10000, db)
    r = simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'op/버려진 요새/SECTOR 40-1'},
                 {'n_runs': 1, 'build': 'standard', 'rules_override': {'power_penalty': 'model'}})
    r0 = simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'op/버려진 요새/SECTOR 40-1'}, {'n_runs': 1, 'build': 'standard'})
    rr = simulate(['gwen', 'fei', 'professor-m', 'amora'], {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅳ'},
                  {'n_runs': 1, 'build': 'standard', 'rules_override': {'power_penalty': 'model'}})
    ok = (p80[1:] == (0.85, 1.15) and p40[1:] == (0.1, 1.9) and p95[1:] == (1.0, 1.0) and r['party']['penalty'] == [0.1, 1.9]
          and r0['party']['penalty'] is None and rr['party']['penalty'] is None and rr['party']['penalty_note'])
    return ok, '80%% %s, 40%% %s, 95%% %s / 작전 40-1 비율 %s 배율 %s(끔 %s) / 플래시 %s' % (
        p80, p40, p95, r['party']['power_ratio'], r['party']['penalty'], r0['party']['penalty'], rr['party']['penalty_note'])


# ---------------------------------------------------------------- 새 적 효과·조건·시점
def test_new_enemy_effects():
    """게이지 0% 설정 / 대상 생명력 3% 연쇄 / 스킬 쿨타임 +1 / 자신 강화 1개당 피해 +10% / 〈강화 불가〉 중 강화 무효 / 〈궁극기 쿨타임 초기화〉"""
    a = unit('a', skills=[dict(slot='기본기', dm=100), dict(slot='궁극기', dm=100, cd=4)])
    f = unit('foe', hp=10 ** 6, df=0)
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    out = {}
    A.gauge = 7000.0
    c = Ctx(F, F, F.d.skills['기본기'])
    c.targets, c.target = [A], A
    b.run_line(F, Line('[스킬 사용 후] 스킬 대상에게 행동 게이지를 0%로 설정', '기본기', 'active'), c)
    out['gauge'] = A.gauge
    hp0 = A.hp
    b.run_line(F, Line('[스킬 사용 후] 스킬 대상에게 연쇄 피해 = 대상 생명력×3% (×1.85, 방어력 적용)', '기본기', 'active'), c)
    out['chain'] = hp0 - A.hp
    A.cd['궁극기'] = 2
    b.run_line(F, Line('[스킬 사용 후] 스킬 대상에게 스킬 쿨타임 1턴 증가', '기본기', 'active'), c)
    out['cd'] = A.cd['궁극기']
    give(F, '강1', {'공격력%': 10.0})
    give(F, '강2', {'공격력%': 10.0})
    c2 = Ctx(F, F, F.d.skills['기본기'])
    c2.targets, c2.target = [A], A
    b.run_line(F, Line('[스킬 사용 시작 시] 자신에게 능력치 보정 피해 증가 +10% (자신의 강화 효과 1개당 위 수치만큼 적용, 개수 상한 없음) {이번 스킬에만 적용}',
                       '기본기', 'active'), c2)
    out['per'] = round(c2.inc, 3)
    atk0 = F.mods()['atkp']
    give(F, '강화 불가', {}, src=A, harmful=True)
    out['blocked'] = (round(atk0, 2), round(F.mods()['atkp'], 2))
    b.run_line(A, Line('[웨이브 시작 시] 자신에게 〈궁극기 쿨타임 초기화〉', '고유 패시브', 'passive'), Ctx(A, A, None))
    out['reset'] = A.cd['궁극기']
    exp = dict(gauge=0.0, chain=math.floor(10000 * 0.03 * 1.85 * (1 - 1000 / 4000)), cd=3, per=0.2, blocked=(0.2, 0.0), reset=0)
    return out == exp, '%s (기대 %s)' % (out, exp)


def test_new_conditions():
    """조건 키: NotTargetPositiveBuff(대상 강화 없음)·ExistAllySpecificBuff(같은 편에 그 효과)·피해 증가(조건부)(표지) 판정"""
    a, f = unit('a'), unit('foe')
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    sk = F.d.skills['기본기']
    c = Ctx(F, F, sk)
    c.targets, c.target = [A], A
    l1 = Line('[스킬 사용 시작 시] (조건: 내 공격 시 [NotTargetPositiveBuff: 예]) 자신에게 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}', '기본기', 'active')
    l2 = Line('[스킬 사용 후] (조건: 내 공격 후 [ExistAllySpecificBuff: 표식; 피해 증가(조건부): 예]) 자신에게 행동 게이지 30%p 증가', '기본기', 'active')
    r = [b.cond_ok(F, l1, c), b.cond_ok(F, l2, c)]
    give(A, '보호', {'방어력%': 10.0})
    give(F, '표식', {})
    r += [b.cond_ok(F, l1, c), b.cond_ok(F, l2, c)]
    return r == [True, False, False, True], '판정 %s (기대 [True, False, False, True])' % r


def test_action_trigger():
    """「내 행동 후」 줄은 공격·비공격 스킬 모두에서 실행(P4 까지는 시점 미해석)"""
    a = unit('a', skills=[dict(slot='기본기', dm=100), dict(slot='특수기', dm=0, cd=3, tg='자신')])
    b = battle([a], [unit('foe', hp=10 ** 9)])
    A = b.allies[0]
    A.d.lines = [Line('[스킬 사용 후] (조건: 내 행동 후) 자신에게 〈표시〉 (지속 무한) {최대 9중첩}', '잠재력', 'passive')]
    b.cast(A, A.d.skills['특수기'])
    n1 = A.stack('표시')
    b.cast(A, A.d.skills['기본기'])
    n2 = A.stack('표시')
    return (n1, n2) == (1, 2), '비공격 뒤 %d, 공격 뒤 %d (기대 1, 2)' % (n1, n2)


def test_cast_pre_events():
    """자기 효과를 생략한 시전도 아군/적 사전 이벤트를 통지한다."""
    out = {}
    for mode in ('normal', 'extra', 'reaction', 'trigger', 'skip', 'local'):
        for attack in (True, False):
            a = unit('actor', skills=[dict(slot='기본기', dm=100 if attack else 0, tg='적 단일' if attack else '자신')])
            b = battle([a, unit('ally')], [unit('foe', hp=10 ** 9)], opts=dict(coop=False))
            A, B = b.allies
            F = b.foes[0]
            for u, trig in ((A, '내 행동 시'), (B, '아군 행동 시'), (F, '적 공격 시' if attack else '적 비공격 스킬 시')):
                u.d.lines = [Line('[스킬 사용 시작 시] (조건: %s) 자신에게 〈표시〉 (지속 무한)' % trig, '고유 패시브', 'passive')]
            # 같은 아군 이벤트가 시전자 자신에게도 중복 발송되면 실패.
            A.d.lines.append(Line('[스킬 사용 시작 시] (조건: 아군 행동 시) 자신에게 〈중복〉 (지속 무한)', '고유 패시브', 'passive'))
            b.cast(A, A.d.skills['기본기'], extra=mode != 'normal', via=mode,
                   skip_lines=mode in ('skip', 'local'), local_pre=mode == 'local')
            out[(mode, attack)] = (A.stack('표시'), B.stack('표시'), F.stack('표시'), A.stack('중복'))
    ok = all(v == ((0, 1, 1, 0) if k[0] in ('skip', 'local') else (1, 1, 1, 0)) for k, v in out.items())
    return ok, '공격/비공격 × 시전 경로 6종: %s' % out


def test_cristelle_stack_trigger():
    """아군 타격 완료 뒤 1회 발동·선행 쿨·스택 소거, 쿨/행동불가/자기 타격/비공격은 차단."""
    out = {}
    for mode in ('ready', 'below', 'cooldown', 'broken', 'stun', 'sleep', 'self', 'nonattack', 'post_stack', 'extra', 'sun_fill', 'generic'):
        d = UnitDef(get_db(), 'cristelle')
        if mode == 'generic':
            d.key = 'generic-stack-unit'   # 캐릭터 이름에 의존하지 않고 설명문으로 연결.
        b = battle([unit('actor', element='태양', skills=[dict(slot='기본기', dm=100), dict(slot='특수기', dm=0, tg='자신'),
                                                       dict(slot='궁극기', dm=100)]), d],
                   [unit('foe', hp=10 ** 9)], opts=dict(coop=False), timeline=True)
        A, C = b.allies
        F = b.foes[0]
        stacks = 3 if mode == 'sun_fill' else 4 if mode in ('below', 'post_stack') else 5
        give(C, '점화', stacks=stacks).maxs = 5
        if mode == 'cooldown':
            C.cd['특수기'] = 2
        if mode == 'broken':
            C.broken = True
        if mode in ('stun', 'sleep'):
            give(C, '기절' if mode == 'stun' else '수면', harmful=True)
        if mode == 'post_stack':
            C.d.lines.append(Line('[스킬 사용 후] (조건: 아군 공격 후) 자신에게 〈점화〉 (지속 무한) {최대 5중첩}', '고유 패시브', 'passive'))
        # 진입 순간에 쿨이 이미 걸렸고 원 공격 피해 처리가 끝났는지 확인.
        calls = []
        original = b.cast
        def traced(u, sk, **kw):
            if kw.get('via') == 'trigger':
                calls.append((u.cd.get('특수기'), F.hp < F.maxhp, kw.get('extra')))
            return original(u, sk, **kw)
        b.cast = traced
        actor = C if mode == 'self' else A
        slot = '궁극기' if mode == 'sun_fill' else '특수기' if mode == 'nonattack' else '기본기'
        b.cast(actor, actor.d.skills[slot], extra=mode == 'extra')
        expected = mode in ('ready', 'post_stack', 'extra', 'sun_fill', 'generic')
        first_ok = (C.cast_count['특수기(추가)'] == int(expected)
                    and calls == ([(d.trigger_skills['특수기'].cd, True, True)] if expected else []))
        if expected:
            first_ok = first_ok and C.stack('점화') == 0 and C.has('복수심(해제불가)') and C.gauge == 5000
            give(C, '점화', stacks=5).maxs = 5
            b.cast(A, A.d.skills['기본기'])
            first_ok = first_ok and C.cast_count['특수기(추가)'] == 1 and C.cd['특수기'] == 3
        out[mode] = first_ok
    return all(out.values()), '발동·차단 12조건 %s' % out


def test_cristelle_ignite_amount():
    """설명문: 다른 아군 특수기/궁극기 공격 시 태양 +2, 나머지 +1. 특수기 분배는 태양만 +2."""
    out = {}
    for element in ('태양', '달', '별'):
        for slot, attack in (('기본기', True), ('특수기', True), ('궁극기', True), ('특수기', False)):
            d = UnitDef(get_db(), 'cristelle')
            a = unit('actor', element=element, skills=[dict(slot=slot, dm=100 if attack else 0, tg='적 단일' if attack else '자신')])
            b = battle([a, d], [unit('foe', hp=10 ** 9)], opts=dict(coop=False))
            A, C = b.allies
            C.cd['특수기'] = 3
            b.cast(A, A.d.skills[slot])
            expected = (2 if element == '태양' else 1) if attack and slot != '기본기' else 0
            out[(element, slot, attack)] = (C.stack('점화'), expected)
    b = battle([unit('sun', element='태양'), unit('moon', element='달'), UnitDef(get_db(), 'cristelle')],
               [unit('foe', hp=10 ** 9)], opts=dict(coop=False))
    S, M, C = b.allies
    give(C, '점화', stacks=5)
    b.cast(S, S.d.skills['기본기'])
    shared = (S.stack('점화'), M.stack('점화'), C.stack('점화'))
    # 공유 파서의 ef는 그대로여야 기대값 엔진에 영향이 없다.
    unchanged = [ln.eff['times'] for ln in C.d.lines if ln.slot == '고유 패시브' and dict(ln.params).get('시전자 속성') == '태양'] == [2, 2]
    return all(got == want for got, want in out.values()) and shared == (2, 0, 0) and unchanged, '획득 12조건 %s / 분배 %s' % (out, shared)


def test_trigger_support_report():
    """연결된 트리거는 미지원에서 제외, 미지원 일반/반응 트리거는 모두 보고."""
    supported = ['cristelle', 'professor-m', 'wedding-carmen', 'white-pearl-luna',
                 'smile', 'sunshine-cat-smile', 'roberta', 'fei']
    unsupported = []
    out = {}
    for key in supported + unsupported:
        d = UnitDef(get_db(), key)
        names = {s.name for s in d.trigger_skills.values()}
        parsed = any('트리거 스킬 미반영' in msg and any(n in msg for n in names) for msg in d.unmodeled)
        reported = any(r['reason'] == 'skill' and any(n in r['raw'] for n in names) for r in support_report([d]))
        out[key] = (parsed, reported)
    return all(v == ((False, False) if k in supported else (True, True)) for k, v in out.items()), '파서/보고 %s' % out


def test_recast_limit():
    """{발동 후 1턴 재발동 불가}: 같은 자기 턴 안에서는 한 번만(추가 발동이 자기 자신을 다시 부르는 연쇄 차단), 다음 자기 턴엔 다시 걸림"""
    a = unit('a', skills=[dict(slot='기본기', dm=100), dict(slot='특수기', dm=100, cd=3)])
    b = battle([a], [unit('foe', hp=10 ** 9)])
    A = b.allies[0]
    A.d.lines = [Line('[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: 특수기]) 자신에게 특수기 추가 발동 {발동 후 1턴 재발동 불가}', '특수기', 'active')]
    A.actions = 1
    b.cast(A, A.d.skills['특수기'])
    n1 = A.cast_count['특수기(추가)']
    b.cast(A, A.d.skills['특수기'])
    n2 = A.cast_count['특수기(추가)']
    A.actions = 2
    b.cast(A, A.d.skills['특수기'])
    n3 = A.cast_count['특수기(추가)']
    depth = b.unsup.get('depth: 연쇄 깊이 상한으로 시전 생략', 0)
    return (n1, n2, n3, depth) == (1, 1, 2, 0), '추가 발동 누적 %d -> 같은 턴 %d -> 다음 턴 %d, 깊이 생략 %d (기대 1, 1, 2, 0)' % (n1, n2, n3, depth)


def test_review_fixes():
    """codex P5 리뷰 차단 수정: 〈강화 불가〉면 불사·보호막·면역도 꺼짐 / 생명력이 1% 아래여도 「강제 회복」으로 1% /
    확률 줄의 재발동 제한은 실제 발동 때 기록 / NotTargetPositiveBuff 는 광역에서 대상마다 / 프로페서M 트리거도 「이번 스킬」 보정"""
    out = {}
    a, f = unit('a'), unit('foe', hp=10000)
    b = battle([a], [f])
    A, F = b.allies[0], b.foes[0]
    give(F, '불사', {})
    give(F, '보호막', {})
    F.eff['보호막'].shield = 5000.0
    give(F, '면역', {})
    give(F, '강화 불가', {}, src=A, harmful=True)
    b.add_effect(A, F, dict(name='기절', props={}, dur=1, max=None, times=1, judge=False, chance=1.0), None)
    out['stun'] = F.has('기절')
    b.apply_damage(A, F, 20000, 'hit')
    out['dead'] = F.dead
    g = unit('g', hp=10000)
    b2 = battle([unit('x')], [g])
    G = b2.foes[0]
    G.hp = 50.0
    give(G, '불사의 육신', {}, dur=math.inf)
    b2.apply_damage(None, G, 999, 'hit')
    out['forced'] = G.hp
    ln = Line('[스킬 사용 후] (조건: 내 공격 후) 자신에게 50% 확률로 특수기 추가 발동 {발동 후 1턴 재발동 불가}', '특수기', 'active')
    c = Ctx(A, A, A.d.skills['기본기'])
    b.line_ok(A, ln, c)
    out['rec_before'] = len(b.recast)
    b._cur_line = ln
    b._fired(A)
    b._cur_line = None
    out['rec_after'] = len(b.recast)
    t1, t2 = unit('t1'), unit('t2')
    b3 = battle([unit('x', skills=[dict(slot='기본기', dm=100, all=True)])], [t1, t2])
    X, T1, T2 = b3.allies[0], b3.foes[0], b3.foes[1]
    give(T1, '버프', {'공격력%': 10.0})
    c3 = Ctx(X, X, X.d.skills['기본기'])
    c3.targets, c3.target = [T1, T2], T1
    b3.run_batch(X, [Line('[스킬 사용 시작 시] (조건: 내 공격 시 [NotTargetPositiveBuff: 예]) 자신에게 능력치 보정 피해 증가 +20% {이번 스킬에만 적용}',
                          '기본기', 'active')], c3)
    out['per_target'] = (round(c3.local_by[T1]['inc'], 2), round(c3.local_by[T2]['inc'], 2), round(c3.inc, 2))
    db = get_db()
    pm = UnitDef(db, 'professor-m')
    b4 = Battle([pm], [[unit('foe', hp=10 ** 9, sa=1)]], random.Random(1), mc=dict(FIXED))
    b4.spawn_wave()
    P, E = b4.allies[0], b4.foes[0]
    E.broken = True
    ctx4 = b4.cast(P, pm.trigger_skills['특수기'], extra=True, skip_lines=True, target=E, via='trigger', local_pre=True)
    out['profm'] = (round(ctx4.inc, 2), round(ctx4.inc_break, 2))
    exp = dict(stun=True, dead=True, forced=100.0, rec_before=0, rec_after=1, per_target=(0.0, 0.2, 0.0), profm=(0.15, 0.3))
    return out == exp, '%s (기대 %s)' % (out, exp)


# ---------------------------------------------------------------- 사전 계산 연결
TESTS = [test_build_light_values, test_stat_order_journey, test_potential_pick, test_build_missing_is_error, test_build_speed_range,
         test_toughness_break, test_tough_elem_and_fixed, test_ally_break_gauge_and_coop, test_break_recovery_turn_effects,
         test_break_conditions, test_damage_limit,
         test_power_penalty, test_new_enemy_effects, test_new_conditions, test_action_trigger, test_cast_pre_events,
         test_cristelle_stack_trigger, test_cristelle_ignite_amount, test_trigger_support_report,
         test_recast_limit, test_review_fixes]   # 옛 사전 계산 시험(test_precompute_build_and_gate)은 사전 계산 퇴역으로 뺌(2026-10-20)


def main():
    sel = sys.argv[1:]
    ok_all = True
    for t in TESTS:
        if sel and not any(x in t.__name__ for x in sel):
            continue
        try:
            ok, msg = t()
        except Exception as ex:   # 시험 자체 오류도 실패로
            ok, msg = False, '오류: %r' % (ex,)
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', t.__name__, msg))
        ok_all = ok_all and ok
    print('ALL', 'OK' if ok_all else 'FAILED')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
