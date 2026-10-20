# -*- coding: utf-8 -*-
"""P3 확률 엔진(battlesim/mc.py) 시험: 대상 선택 가중·도발·대상 불가·수호 분담·보호막 합산·회복 공식·사망·카운터·리더 속도·
결정성(같은 시드)·이벤트 한도·적 스탯 로더·회피·확인용 버프·추가 발동 순서.

  python -X utf8 -I tests/p3_test.py            # 전부
  python -X utf8 -I tests/p3_test.py guard      # 이름에 이 글자가 든 시험만

각 시험은 해당 구현을 일부러 깨뜨렸을 때 실패하는 것을 확인했다(docs/sim_p3_report.md 「안전 시험」)."""
import json
import math
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.api import _CustomFoe, simulate  # noqa: E402
from battlesim.mc import Battle, Ctx, Eff, EventLimitError  # noqa: E402
from battlesim.rules import DEFAULT_OPTS, MC_OPTS  # noqa: E402
from battlesim.starsavior.foe import load_foe, stage_waves  # noqa: E402
from battlesim.starsavior.parser import Line  # noqa: E402

FIXED = dict(rand_range=[1.0, 1.0])   # 난수 고정(정확한 값 비교용)


def unit(name='u', role='스트라이커', hp=10000, atk=1000, df=1000, spd=100, cr=0, skills=None, **kw):
    return _CustomFoe(dict(name=name, role=role, hp=hp, atk=atk, **{'def': df}, spd=spd, cr=cr, cd=0, er=0, der=0,
                           skills=skills or [dict(slot='기본기', dm=100)], **kw), 0)


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


# ---------------------------------------------------------------- 대상 선택
def test_target_weights():
    """적 단일 공격: 전열 0.8 / 후열 0.2, 열 안 디펜더 x2 -> 전열 스트라이커 0.267, 전열 디펜더 0.533, 후열 각 0.1(2만 회)"""
    roles = ['스트라이커', '디펜더', '스트라이커', '스트라이커']
    b = battle([unit('a%d' % i, role=r) for i, r in enumerate(roles)], [unit('foe')], seed=7)
    n = 20000
    cnt = [0] * 4
    for _ in range(n):
        cnt[b.weighted_pick(b.targetable(0)).pos] += 1
    fr = [c / n for c in cnt]
    exp = [0.8 / 3, 0.8 * 2 / 3, 0.1, 0.1]
    ok1 = all(abs(f - e) < 0.015 for f, e in zip(fr, exp))
    b2 = battle([unit('a%d' % i, role=r) for i, r in enumerate(roles)], [unit('foe')], mc=dict(target_mode='unit_weight'), seed=7)
    cnt2 = [0] * 4
    for _ in range(n):
        cnt2[b2.weighted_pick(b2.targetable(0)).pos] += 1
    fr2 = [c / n for c in cnt2]
    exp2 = [0.4 / 1.4, 0.8 / 1.4, 0.1 / 1.4, 0.1 / 1.4]
    ok2 = all(abs(f - e) < 0.015 for f, e in zip(fr2, exp2))
    return ok1 and ok2, '열 2단계 %s (기대 %s) / 개인 가중 %s' % ([round(x, 3) for x in fr], [round(x, 3) for x in exp],
                                                         [round(x, 3) for x in fr2])


def test_untargetable():
    """현장 대기·은신 아군은 다른 아군이 살아 있으면 대상이 안 되고, 전원이 그 상태면 다시 대상이 된다"""
    al = [unit('a%d' % i) for i in range(4)]
    b = battle(al, [unit('foe')], seed=3)
    give(b.allies[0], '현장 대기')
    hit0 = sum(1 for _ in range(3000) if b.weighted_pick(b.targetable(0)) is b.allies[0])
    for u in b.allies:
        give(u, '은신')
    hit_all = sum(1 for _ in range(3000) if b.weighted_pick(b.targetable(0)) is b.allies[0])
    return hit0 == 0 and hit_all > 500, '현장 대기 1명: %d회 / 전원 은신: %d회' % (hit0, hit_all)


def test_taunt():
    """도발 걸린 적은 도발자(후열이라도)에게 기본기. 도발자가 죽으면 일반 대상 선택"""
    al = [unit('a%d' % i, hp=10 ** 6) for i in range(4)]
    b = battle(al, [unit('foe', hp=10 ** 6)], seed=5)
    foe = b.foes[0]
    give(foe, '도발', src=b.allies[3], harmful=True, dur=50)
    for _ in range(20):
        b.act(foe)
    t3 = b.allies[3].taken
    others = sum(u.taken for u in b.allies[:3])
    b.allies[3].dead = True
    for _ in range(20):
        b.act(foe)
    others2 = sum(u.taken for u in b.allies[:3])
    return t3 > 0 and others == 0 and others2 > 0, '도발자 받은 피해 %d, 다른 아군 %d -> 도발자 사망 뒤 %d' % (t3, others, others2)


def test_ally_target_lowest():
    """구원자 오토 단일 공격 = 보호막+HP 합이 가장 낮은 적"""
    b = battle([unit('a')], [unit('f0', hp=5000), unit('f1', hp=3000)])
    e = give(b.foes[1], '보호막')
    e.shield = 3000
    pick = b.pick_attack_target(b.allies[0])
    b.foes[1].eff = {}
    b.foes[1]._m = None
    pick2 = b.pick_attack_target(b.allies[0])
    return pick is b.foes[0] and pick2 is b.foes[1], '보호막 3000 있을 때 %s / 없을 때 %s' % (pick.name, pick2.name)


# ---------------------------------------------------------------- 수호·보호막·회복
def test_guard_split():
    """수호 30%: 방어 전 기본 피해 1850 을 7:3 으로 나눠 각자 방어율로 -> 대상 971, 수호자 333 (final_transfer: 970/416)"""
    out = {}
    for mode in ('pre_defense_split', 'final_transfer'):
        v, g = unit('v', df=1000), unit('g', df=2000)
        b = battle([v, g], [unit('foe', atk=1000)], mc=dict(guard_mode=mode))
        give(b.allies[1], '수호', {'피해 분담(수호)': 30.0})
        b.cast(b.foes[0], b.foes[0].d.skills['기본기'], target=b.allies[0])
        out[mode] = (b.allies[0].taken, b.allies[1].taken)
    ok = out['pre_defense_split'] == (971, 333) and out['final_transfer'] == (970, 416)
    return ok, str(out)


def test_guard_highest_only():
    """분담 효과가 둘이면 가장 높은 1명만(40% 가 앞 칸, 30% 가 뒤 칸이어도 40% 쪽)"""
    b = battle([unit('v'), unit('g40'), unit('g30')], [unit('foe', atk=1000)])
    give(b.allies[1], '수호2', {'피해 분담(수호)': 40.0})
    give(b.allies[2], '수호', {'피해 분담(수호)': 30.0})
    b.cast(b.foes[0], b.foes[0].d.skills['기본기'], target=b.allies[0])
    return b.allies[2].taken == 0 and b.allies[1].taken > 0, '40%%: %d / 30%%: %d' % (b.allies[1].taken, b.allies[2].taken)


def test_shield_sum():
    """같은 보호막 재부여 = 남은 양에 합산(생명력 10000 x 20% x 2 = 4000), 지속 피해는 보호막을 무시"""
    b = battle([unit('a', hp=10000)], [unit('foe')])
    a = b.allies[0]
    ln = Line('[스킬 사용 후] 자신에게 〈보호막〉 (2턴) 보호막 = 자신 생명력×20%', '특수기', 'active')
    b.run_line(a, ln, Ctx(a, a, None))
    b.run_line(a, ln, Ctx(a, a, None))
    sh = a.shield_total()
    dot = Line('[스킬 사용 후] 스킬 대상에게 〈연소〉 (2턴) {효과 적중 판정}', '기본기', 'active')
    foe = b.foes[0]
    c = Ctx(foe, foe, foe.d.skills['기본기'])
    c.targets, c.target = [a], a
    b.mc['rand_range'] = [1.0, 1.0]
    give(a, '연소', harmful=True)   # 판정 없이 바로 시험하려고 직접 붙인 뒤 지속 피해 정보만 채움
    a.eff['연소'].dot = ('atk', 0.20)
    a.eff['연소'].inst = [[foe, 2]]
    hp0 = a.hp
    b._tick_dot_hot(a)
    return sh == 4000 and a.shield_total() == 4000 and a.hp < hp0, '보호막 %d, 지속 피해 뒤 보호막 %d, HP %d -> %d' % (
        sh, a.shield_total(), hp0, a.hp)


def test_heal_formula():
    """회복 = 버림(10000 x 10% x (1 + 주는 20% + 받는 -50%)) = 700, 최대 HP 를 넘지 않음"""
    b = battle([unit('h', hp=10000), unit('t', hp=10000)], [unit('foe')])
    h, t = b.allies
    give(h, '주는 회복 버프', {'주는 회복량': 20.0})
    give(t, '회복 감소', {'받는 회복량': -50.0}, harmful=True)
    t.hp = 5000
    ln = Line('[스킬 사용 후] 아군 전체에게 회복 = 자신 생명력×10%', '특수기', 'active')
    b.run_line(h, ln, Ctx(h, h, None))
    healed = t.hp - 5000
    t.hp = 9950
    b.run_line(h, ln, Ctx(h, h, None))
    return healed == 700 and t.hp == 10000, '회복량 %d, 최대 HP 상한 %d' % (healed, t.hp)


# ---------------------------------------------------------------- 사망·카운터·리더
def test_death_stops_actions():
    """죽은 아군은 행동하지 않고 대상이 되지 않으며 자기 효과가 사라진다"""
    al = [unit('weak', hp=1), unit('tank', hp=10 ** 7, atk=1)]
    b = Battle(al, [[unit('foe', hp=10 ** 7, atk=1000, spd=300)]], random.Random(2), mc=FIXED, max_turns=20)
    b.spawn_wave()
    give(b.allies[0], '공격력 증가', {'공격력%': 30.0})
    b.apply_damage(b.foes[0], b.allies[0], 5, 'hit')
    acts = b.allies[0].actions
    b.run()
    weak = b.allies[0]
    picks = sum(1 for _ in range(500) if b.pick_attack_target(b.foes[0]) is weak)
    return weak.dead and weak.actions == acts and picks == 0 and not weak.eff and b.allies[1].actions > 5, \
        '사망 후 행동 %d -> %d, 대상 선택 %d, 남은 효과 %d' % (acts, weak.actions, picks, len(weak.eff))


def test_counter():
    """카운터: 지금 칸(기본기) = 대상이 마지막으로 쓴 칸이면 +10% (1387 -> 1526)"""
    b = battle([unit('a')], [unit('foe', df=1000)])
    a, f = b.allies[0], b.foes[0]
    sk = a.d.skills['기본기']
    b.cast(a, sk, target=f)
    d0 = f.taken
    f.last_slot = '기본기'
    b.cast(a, sk, target=f)
    d1 = f.taken - d0
    f.last_slot = '특수기'
    b.cast(a, sk, target=f)
    d2 = f.taken - d0 - d1
    return d0 == 1387 and d1 == 1526 and d2 == 1387, '칸 없음 %d / 같은 칸 %d / 다른 칸 %d' % (d0, d1, d2)


def test_leader_speed():
    """리더 속도 +10(아군 리더 칸, 적은 웨이브의 보스)"""
    b = Battle([unit('a', spd=100), unit('b', spd=100)], [[unit('f0', spd=100), unit('boss', spd=100, boss=True)]],
               random.Random(1), mc=FIXED, leader=1)
    b.spawn_wave()
    s = [u.spd() for u in b.allies] + [u.spd() for u in b.foes]
    return s == [100, 110, 100, 110], '속도 %s' % s


# ---------------------------------------------------------------- 결정성·한도·로더
def test_determinism():
    """같은 시드 = 같은 결과, 다른 시드 = 다른 판 결과"""
    party = {'units': ['professor-m', 'gwen', 'fei', 'amora'], 'leader': 0}
    enc = {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'}
    strip = lambda r: json.dumps({k: v for k, v in r.items() if k != 'runtime_ms_per_run'}, sort_keys=True, ensure_ascii=False)
    a = simulate(party, enc, {'seed': 11, 'n_runs': 15})
    b = simulate(party, enc, {'seed': 11, 'n_runs': 15})
    c = simulate(party, enc, {'seed': 12, 'n_runs': 15})
    return strip(a) == strip(b) and strip(a) != strip(c), '같은 시드 동일 %s / 다른 시드 다름 %s' % (strip(a) == strip(b), strip(a) != strip(c))


def test_event_limit():
    """이벤트 상한을 넘으면 EventLimitError(정상 결과를 돌려주지 않음)"""
    try:
        r = simulate(['professor-m', 'gwen', 'fei', 'amora'], {'stage': 'cosmo/길레/길레 3단계'},
                     {'n_runs': 2, 'rules_override': {'max_events': 30}})
    except EventLimitError as ex:
        return True, '예외: %s' % ex
    return False, '예외 없이 결과 반환 clear_p=%s' % r['outcome']['clear_p']


def test_foe_loader_matches_stages_json():
    """foe.js 로더 스탯 = data/foe_stages.json 스탯(대표 스테이지 + 작전·회랑)"""
    with open(os.path.join(ROOT, 'data', 'foe_stages.json'), encoding='utf-8') as f:
        fs = json.load(f)
    keys = ['hp', 'atk', 'def', 'spd', 'crit', 'critdmg', 'hit', 'evade', 'abs_evade', 'tough']
    mine = ['hp', 'atk', 'def', 'spd', 'cr', 'cd', 'eh', 'er', 'der', 'sa']
    cases = [('cosmo', '길레', '길레 1단계'), ('cosmo', '길레', '길레 3단계'), ('rush', '매니저 그레고리', '매니저 그레고리 Ⅳ'),
             ('op', 'NOA 상업지구', 'SECTOR 1-1'), ('clo', '성간 회랑', 'FLOOR 1')]
    n = bad = 0
    for c, t, s in cases:
        st = next(x for cc in fs['contents'] if cc['key'] == c for tt in cc['tabs'] if tt['tab'] == t for x in tt['stages'] if x['name'] == s)
        _, waves = stage_waves(c, t, s)
        seen, mine_list = set(), []
        for w in waves:
            for d in w:
                if d.key not in seen:
                    seen.add(d.key)
                    mine_list.append(d)
        for e, d in zip(st['enemies'], mine_list):
            n += 1
            if e['name'] != d.name or [e['stats'][k] for k in keys] != [d.stats[k] for k in mine]:
                bad += 1
        if len(st['enemies']) != len(mine_list):
            bad += 1
    return n > 5 and bad == 0, '적 %d 체 비교, 불일치 %d' % (n, bad)


def test_evade():
    """회피율 100%: 피해 감소 합 +50% (1387 -> 693), 회피한 대상에는 약화가 안 걸림"""
    b = battle([unit('a')], [unit('foe', df=1000)])
    a, f = b.allies[0], b.foes[0]
    give(f, '회피율 증가', {'회피율': 100.0})
    b.cast(a, a.d.skills['기본기'], target=f)
    ctx = Ctx(a, a, a.d.skills['기본기'])
    ctx.targets, ctx.target = [f], f
    ctx.evaded.add(f)
    b.add_effect(a, f, dict(name='방어력 감소', props={'방어력%': -30.0}, dur=2, max=None, times=1, judge=False, chance=1.0), ctx)
    return f.taken == 693 and '방어력 감소' not in f.eff, '피해 %d, 약화 %s' % (f.taken, '방어력 감소' in f.eff)


# ---------------------------------------------------------------- 줄 실행 규칙
def test_check_buff_expiry():
    """길레 「주기 확인용 버트」(지속 표기 없음) 는 그 행동이 끝나면 사라지고, 낮/밤 주기가 번갈아 바뀐다"""
    raw = load_foe()
    from battlesim.starsavior.foe import FoeDef
    gile = FoeDef(raw, 18, 0, {})
    b = Battle([unit('a', hp=10 ** 7)], [[gile]], random.Random(1), mc=FIXED)
    b.spawn_wave()
    g = b.foes[0]
    seq = []
    for _ in range(4):
        b.act(g)
        seq.append(('낮' if g.has('낮의 주기(해제불가)') else '') + ('밤' if g.has('밤의 주기(해제불가)') else ''))
    return seq == ['밤', '낮', '밤', '낮'] and not g.has('주기 확인용 버트'), '행동별 주기 %s, 확인용 버트 남음 %s' % (seq, g.has('주기 확인용 버트'))


def test_extra_cast_after_consume():
    """같은 사건의 줄 묶음에서 추가 발동은 중첩 소비 뒤에 실행(그웬 전기 충격 5회 -> 진실을 밝히는 빛 무한 연쇄 없음)"""
    r = simulate({'units': ['professor-m', 'gwen', 'fei', 'amora'], 'leader': 0}, {'stage': 'rush/매니저 그레고리/매니저 그레고리 Ⅰ'},
                 {'seed': 1, 'n_runs': 20})
    depth = r['unsupported']['runtime'].get('depth: 연쇄 깊이 상한으로 시전 생략', 0)
    return depth == 0, '깊이 상한 걸림 %d 회' % depth


def test_ev_engine_opts_untouched():
    """확률 엔진 규칙은 DEFAULT_OPTS(기대값 엔진·damage_index _meta)에 섞이지 않는다"""
    return not (set(MC_OPTS) & set(DEFAULT_OPTS)), '겹치는 키 %s' % sorted(set(MC_OPTS) & set(DEFAULT_OPTS))


# ---------------------------------------------------------------- codex 2차 검토 차단 7건 회귀 시험
def real(key):
    from battlesim.starsavior.data import get_db
    from battlesim.starsavior.parser import UnitDef
    return UnitDef(get_db(), key)


def test_skill_heal_hl():
    """[차단1] 스킬 기본 회복(hl): 프레이 특수기 = 버림(프레이 최대 HP x 21% x (1 + 주는 회복량 20%)), 대상 = 지정한 아군"""
    frey = real('frey')
    b = battle([frey, unit('t', hp=30000)], [unit('foe')])
    f, t = b.allies
    t.hp = 1000
    b.cast(f, frey.skills['특수기'], target=t)
    exp = math.floor(f.maxhp * 0.21 * 1.2)
    return t.hp - 1000 == exp and f.healed == exp, '회복 %d (기대 %d)' % (t.hp - 1000, exp)


def test_enemy_immunity_and_gate():
    """[차단2] 〈면역〉(약화효과 면역) 이면 기절 등 약화가 안 걸림 / 「불사의 육신·피해 제한」 적(516)은 중요 미지원 -> gate_ok=false"""
    b = battle([unit('a')], [unit('foe')])
    a, f = b.allies[0], b.foes[0]
    give(f, '면역', {}, dur=3)
    b.add_effect(a, f, dict(name='기절', props={}, dur=1, max=None, times=1, judge=False, chance=1.0), None)
    stunned = f.has('기절')
    r = simulate(['gwen', 'fei', 'professor-m', 'amora'], {'waves': [[{'foe': 516, 'stats_override': {'hp': 1}}]]},
                 {'n_runs': 3})
    crit = [x['raw'][:40] for x in r['unsupported']['critical']]
    return (not stunned) and r['unsupported']['gate_ok'] is False and any('피해 제한' in x for x in crit), \
        '면역 중 기절 %s, gate_ok %s, 중요 미지원 %s' % (stunned, r['unsupported']['gate_ok'], crit)


def test_hp_condition_units():
    """[차단3] 대상 HP% 조건 단위 1/10000: 세이라 「초과 7500」 만피 +15%·50% 0, 스마일 「미만 5000」 40% 발동·60% 미발동"""
    b = battle([unit('a')], [unit('foe', hp=10000)])
    a, f = b.allies[0], b.foes[0]
    sk = a.d.skills['기본기']
    over = Line('[스킬 사용 시작 시] (조건: 내 공격 시 [대상 HP% 초과: 7500]) 자신에게 능력치 보정 피해 증가 +15% {이번 스킬에만 적용}', '고유 패시브', 'passive')
    under = Line('[스킬 사용 후] (조건: 내 공격 후 [대상 HP% 미만: 5000; 사용 스킬: 기본기]) 자신에게 행동 게이지 15%p 증가', '고유 패시브', 'passive')
    out = []
    for hp in (10000, 5000):
        f.hp = hp
        c = Ctx(a, a, sk)
        c.targets, c.target = [f], f
        b.run_line(a, over, c)
        out.append(round(c.inc, 3))
    g = []
    for hp in (4000, 6000):
        f.hp = hp
        a.gauge = 0.0
        c = Ctx(a, a, sk)
        c.targets, c.target = [f], f
        b.run_line(a, under, c)
        g.append(a.gauge)
    return out == [0.15, 0.0] and g == [1500.0, 0.0], '초과 조건 피해 증가 %s / 미만 조건 게이지 %s' % (out, g)


def test_reaction_cdr_slot():
    """[차단4] 에밀리 피격 -> 자기 궁극기 쿨타임 감소(공격자 스킬 칸 아님): 단일 공격 7 -> 6, 전체 공격 7 -> 5(설명: 전체 공격이면 추가 1턴)"""
    emily = real('emily')
    res = []
    for aoe in (False, True):
        b = battle([emily, unit('x', hp=10 ** 6)], [unit('foe', atk=10, skills=[dict(slot='기본기', dm=50, all=aoe)])])
        e = b.allies[0]
        before = e.cd.get('궁극기')
        b.cast(b.foes[0], b.foes[0].d.skills['기본기'], target=e)
        res.append((before, e.cd.get('궁극기')))
    return res == [(7, 6), (7, 5)], '궁극기 쿨타임 (단일, 전체) %s' % res


def test_extra_turn_priority():
    """[차단5] 추가 턴을 얻은 아군은 이미 100% 인 더 빠른 적보다 먼저 행동(우선권은 실제로 쓸 때까지 유지)"""
    a = unit('a', hp=10 ** 6)
    a.lines.append(Line('[스킬 사용 후] 자신에게 〈추가 턴〉', '기본기', 'active'))
    b = battle([a], [unit('foe', hp=10 ** 6, spd=300)])
    au, f = b.allies[0], b.foes[0]
    f.gauge = 10000.0
    b.act(au)
    a.lines.pop()        # 추가 턴은 한 번만 얻게
    nxt, _ = b.pick_next(b.alive(0) + b.alive(1))
    b.act(nxt)
    nxt2, _ = b.pick_next(b.alive(0) + b.alive(1))
    return nxt is au and not au.extra_turn and nxt2 is f, '추가 턴 뒤 다음 %s, 그다음 %s' % (nxt.name, nxt2.name)


def test_no_coop_when_stunned():
    """[차단6] 기절한 아군은 협공하지 않고, 추가 발동 시전도 막힌다(기절·수면은 추가 발동도 불가)"""
    out = {}
    for stun in (False, True):
        b = battle([unit('a', hp=10 ** 6), unit('c', hp=10 ** 6)], [unit('foe', hp=10 ** 9)], seed=4)
        a, c = b.allies
        give(c, '협공 버프', {'협공 확률': 30.0}, dur=999)
        if stun:
            give(c, '기절', {}, harmful=True, dur=999)
        for _ in range(200):
            b.cast(a, a.d.skills['기본기'])
        out[stun] = c.cast_count['기본기(추가)']
    b2 = battle([unit('a')], [unit('foe')])
    give(b2.allies[0], '수면', {}, harmful=True)
    blocked = b2.cast(b2.allies[0], b2.allies[0].d.skills['기본기'], extra=True) is None
    # 기절한 아군은 협공 후보에서 빠진다 -> 협공 1명 자리를 차지하지 않아 다른 후보(20%)가 온전히 20% 로 협공(2000회 중 약 400, 빠지지 않으면 약 280)
    b3 = battle([unit('a', hp=10 ** 6), unit('c', hp=10 ** 6), unit('d', hp=10 ** 6)], [unit('foe', hp=10 ** 9)], seed=9)
    a3, c3, d3 = b3.allies
    give(c3, '협공 버프', {'협공 확률': 30.0}, dur=999)
    give(c3, '기절', {}, harmful=True, dur=999)
    give(d3, '협공 버프', {'협공 확률': 20.0}, dur=999)
    for _ in range(2000):
        b3.cast(a3, a3.d.skills['기본기'])
    dn = d3.cast_count['기본기(추가)']
    return out[False] > 20 and out[True] == 0 and blocked and dn > 340, \
        '협공 횟수 평소 %d / 기절 %d, 수면 중 추가 발동 차단 %s, 기절 동료 옆 다른 후보 협공 %d/2000' % (out[False], out[True], blocked, dn)


def test_multiwave_foe_damage():
    """[차단7] 적 피해 집계는 모든 웨이브 합(1웨이브 적이 준 피해도 남음)"""
    enc = {'waves': [[dict(name='w1', hp=3000, atk=500, spd=200)], [dict(name='w2', hp=3000, atk=500, spd=50)]], 'max_turns': 30}
    r = simulate([{'key': 'gwen'}], enc, {'n_runs': 5, 'seed': 2})
    w1 = r['foes'].get('w1', {}).get('dmg', 0)
    return w1 > 0 and 'w2' in r['foes'], 'foes %s' % r['foes']


def test_guard_real_ede_line():
    """(수호 원문 파싱) 에데 「〈수호〉 (3턴 / 피해 분담(수호) +30%)」 — 괄호 안 괄호에서 끊기지 않고 분담 30% 가 붙는다"""
    ede = real('haydee')
    b = battle([unit('v'), ede], [unit('foe', atk=1000)])
    g = b.allies[1]
    ln = Line('[스킬 사용 후] 자신에게 〈수호〉 (3턴 / 피해 분담(수호) +30%)', '궁극기', 'active')
    b.run_line(g, ln, Ctx(g, g, ede.skills['궁극기']))
    share = g.mods()['guard']
    b.cast(b.foes[0], b.foes[0].d.skills['기본기'], target=b.allies[0])
    return abs(share - 0.3) < 1e-9 and g.taken > 0, '분담 %.2f, 수호자 받은 피해 %d' % (share, g.taken)


# ---------------------------------------------------------------- codex 3차(재검토) 차단 2건 + 사용자 관찰
def test_heal_bonus_per_target():
    """[재검토1] 프레이 궁극기 「아군 대상이 별 속성이라면 회복량 증가(+30%)」는 별 속성 대상만: 별 = 버림(최대 HP x 12.5% x 1.5),
    달·태양 = 버림(x 1.2). 전체 공격의 「대상 속성: 달」 피해 +20% 도 달 속성 대상에게만(달 416 / 태양 346)"""
    frey = real('frey')
    b = battle([frey, unit('s', hp=30000, element='별'), unit('m', hp=30000, element='달'), unit('t', hp=30000, element='태양')],
               [unit('foe')])
    f = b.allies[0]
    for x in b.allies[1:]:
        x.hp = 1.0
    b.cast(f, frey.skills['궁극기'])
    got = [int(x.hp - 1) for x in b.allies[1:]]
    hi, lo = math.floor(f.maxhp * 0.125 * 1.5), math.floor(f.maxhp * 0.125 * 1.2)
    att = unit('att', skills=[dict(slot='기본기', dm=100, all=True)])
    att.lines.append(Line('[스킬 사용 시작 시] (조건: 내 공격 시 [대상 속성: 달]) 자신에게 능력치 보정 피해 증가 +20% {이번 스킬에만 적용}',
                          '기본기', 'active'))
    b2 = battle([att], [unit('fm', element='달', df=1000), unit('fs', element='태양', df=1000)])
    b2.cast(b2.allies[0], att.skills['기본기'])
    dm = [int(x.taken) for x in b2.foes]
    return got == [hi, lo, lo] and dm == [416, 346], '회복 별/달/태양 %s (기대 %s) / 전체 공격 피해 달·태양 %s' % (got, [hi, lo, lo], dm)


def test_serpang_nullify_target():
    """[재검토2] 세르팡 궁극기 〈스킬 피해 무효〉 = 자신 + 자신 제외 생명력 비율 최저 아군(공격력 순 아님, 같은 대상 두 번 없음).
    세르팡이 공격력 1위여도 동료 1명이 받는다"""
    res = []
    for serpang_strong in (False, True):
        sp = real('serpang')
        a = unit('a_hiatk', hp=30000, atk=9000)
        bb = unit('b_low', hp=30000, atk=100 if not serpang_strong else 50)
        if serpang_strong:
            a = unit('a_hiatk', hp=30000, atk=10)
        b = battle([sp, a, bb], [unit('foe')])
        s, ua, ub = b.allies
        ua.hp, ub.hp = 0.93 * ua.maxhp, 0.04 * ub.maxhp
        b.cast(s, sp.skills['궁극기'])
        res.append((s.has('스킬 피해 무효'), ua.has('스킬 피해 무효'), ub.has('스킬 피해 무효')))
    return res == [(True, False, True), (True, False, True)], '(세르팡, 고공격 93%%, 저HP 4%%) 보유 %s' % res


def test_auto_selector_unknown_flagged():
    """설명문에서 자동 지정 규칙을 못 찾으면 기존 규칙으로 고르되 unsupported 에 「대상 규칙 미확인」을 남긴다"""
    b = battle([unit('a'), unit('b')], [unit('foe')])
    a = b.allies[0]
    ln = Line('[스킬 사용 후] 아군 1명(자동 지정)에게 〈수수께끼 버프〉 (2턴 / 공격력% +10%)', '특수기', 'active')
    b.run_line(a, ln, Ctx(a, a, a.d.skills['기본기']))
    flagged = any(k.startswith('selector:') for k in b.unsup)
    applied = sum(1 for u in b.allies if u.has('수수께끼 버프'))
    return flagged and applied == 1, '기록 %s, 부여 %d명' % (flagged, applied)


def test_ally_boss_first():
    """[사용자 관찰] 오토 아군은 살아 있는 보스를 먼저(쫄몹 HP 가 낮아도), lowest_hp 규칙이면 쫄몹"""
    b = battle([unit('a')], [unit('minion', hp=1000), unit('boss', hp=50000, boss=True)])
    p1 = b.pick_attack_target(b.allies[0]).name
    b2 = battle([unit('a')], [unit('minion', hp=1000), unit('boss', hp=50000, boss=True)], mc=dict(ally_auto_target='lowest_hp'))
    p2 = b2.pick_attack_target(b2.allies[0]).name
    b.foes[1].dead = True
    p3 = b.pick_attack_target(b.allies[0]).name
    return (p1, p2, p3) == ('boss', 'minion', 'minion'), '보스 우선 %s / 최저 HP %s / 보스 사망 뒤 %s' % (p1, p2, p3)


def test_nullify_prehit_reduction_infinite_shield():
    """〈스킬 피해 무효〉 1회 = 피해 0 후 소모 / 피격 직전 「피해 감소 +50% 이번 스킬에만」 = 1387 -> 693 / 「(지속 무한) 보호막」 해석"""
    b = battle([unit('a')], [unit('foe', df=1000)])
    a, f = b.allies[0], b.foes[0]
    give(f, '스킬 피해 무효', {}, dur=math.inf)
    b.cast(a, a.d.skills['기본기'], target=f)
    t0 = f.taken
    f.d.lines.append(Line('[피해 처리 직전] 자신에게 능력치 보정 피해 감소 +50% {이번 스킬에만 적용}', '패시브', 'passive'))
    b.cast(a, a.d.skills['기본기'], target=f)
    t1 = f.taken - t0
    f.d.lines.pop()
    ln = Line('[스킬 사용 후] 자신에게 〈공허 방패(해제불가)〉 (지속 무한) 보호막 = 자신 생명력×25% {해제 불가}', '특수기', 'active')
    b.run_line(f, ln, Ctx(f, f, None))
    sh = f.shield_total()
    return t0 == 0 and '스킬 피해 무효' not in f.eff and t1 == 693 and sh == 2500, '무효 피해 %d, 감소 뒤 %d, 무한 보호막 %d' % (t0, t1, sh)


TESTS = [test_target_weights, test_untargetable, test_taunt, test_ally_target_lowest, test_guard_split, test_guard_highest_only,
         test_shield_sum, test_heal_formula, test_death_stops_actions, test_counter, test_leader_speed, test_determinism,
         test_event_limit, test_foe_loader_matches_stages_json, test_evade, test_check_buff_expiry, test_extra_cast_after_consume,
         test_ev_engine_opts_untouched, test_skill_heal_hl, test_enemy_immunity_and_gate, test_hp_condition_units,
         test_reaction_cdr_slot, test_extra_turn_priority, test_no_coop_when_stunned, test_multiwave_foe_damage,
         test_guard_real_ede_line, test_nullify_prehit_reduction_infinite_shield, test_heal_bonus_per_target,
         test_serpang_nullify_target, test_auto_selector_unknown_flagged, test_ally_boss_first]


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
