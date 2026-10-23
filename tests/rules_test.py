# -*- coding: utf-8 -*-
"""P2 규칙 스위치 시험: 스위치마다 한 번 뒤집어 기대한 방향으로 바뀌는지 확인한다(+ 교정 전 규칙이 P1 골든을 그대로 재현하는지).

  python -X utf8 -I tests/rules_test.py            # 전부
  python -X utf8 -I tests/rules_test.py coop_single  # 이름에 이 글자가 든 시험만

각 시험은 일부러 구현을 깨뜨렸을 때 실패하는 것을 확인했다(docs/sim_changes.md 「안전 시험」)."""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.engine import Buff, Ctx, DummyDef, Sim, calc_hit  # noqa: E402
from battlesim.metrics import ref_enemies, unit_def  # noqa: E402
from battlesim.api import assumptions_used  # noqa: E402
from battlesim.rules import DEFAULT_OPTS, LEGACY_OPTS, MC_NOTE_KEYS, MC_OPTS, MC_RULES, RULES  # noqa: E402
from battlesim.starsavior.data import get_db  # noqa: E402
from battlesim.starsavior.stats import calc_stats  # noqa: E402

DB = get_db()
LEG = dict(LEGACY_OPTS)


def dummies(n, start=0):
    return [DummyDef(name='dummy%d' % i) for i in range(start, start + n)]


def enemy(resist=0.0, element=None, hp=1e15):
    return [dict(name='t', hp=hp, **{'def': 1400.0}, spd=100.0, element=element, resist=resist)]


def coop_buff(actor, p):
    b = Buff('협공 시험', {'협공 확률': p * 100}, 1, math.inf)
    b.stacks = 1.0
    actor.buffs[b.name] = b


# ---------------------------------------------------------------- 1. 협공
def test_coop_trigger():
    """basic_only 는 특수기·궁극기 뒤 협공이 없어져 협공 시전(기본기(추가))이 줄어든다(더미 순환 = 기본 3 : 특수 1 : 궁극 1)."""
    out = {}
    for mode in ('any_attack', 'basic_only'):
        s = Sim([unit_def('waltz-asherah')] + dummies(3), ref_enemies(1), 10, dict(LEG, coop_trigger=mode)).run()
        out[mode] = s.party[0].cast_count['기본기(추가)']
    ok = 0 < out['basic_only'] < out['any_attack'] * 0.75
    return ok, '협공 시전 any_attack %.3f -> basic_only %.3f' % (out['any_attack'], out['basic_only'])


def test_coop_single():
    """협공 확률 0.3 인 아군 2명: 1명 규칙이면 두 번째는 0.3 x (1-0.3) = 0.21, 교정 전은 둘 다 0.3."""
    res = {}
    for single in (False, True):
        s = Sim([DummyDef(name='atk')] + [unit_def('gwen'), unit_def('fei')] + dummies(1, 5), ref_enemies(1), 10,
                dict(LEG, coop_single=single, coop_trigger='basic_only'))
        coop_buff(s.party[1], 0.3)
        coop_buff(s.party[2], 0.3)
        a = s.party[0]
        s.coop_followups(a, Ctx(a, a, a.d.skills['기본기'], False, 1.0))
        res[single] = (s.party[1].cast_count['기본기(추가)'], s.party[2].cast_count['기본기(추가)'])
    ok = (abs(res[False][0] - 0.3) < 1e-9 and abs(res[False][1] - 0.3) < 1e-9
          and abs(res[True][0] - 0.3) < 1e-9 and abs(res[True][1] - 0.21) < 1e-9)
    return ok, '교정 전 %s / 1명 규칙 %s' % (res[False], res[True])


# ---------------------------------------------------------------- 2. 노바
def test_nova_policy():
    """auto 는 노바 버스트가 0회(노바를 끈 것과 같은 피해), manual 은 버스트가 있고 피해가 더 크다."""
    team = [unit_def('gwen'), unit_def('amora')] + dummies(2)
    run = lambda o: Sim(team, ref_enemies(1), 10, dict(LEG, **o)).run()
    auto, manual, off = run(dict(nova_policy='auto')), run(dict(nova_policy='manual')), run(dict(nova=False))
    dmg = lambda s: sum(a.dmg for a in s.party)
    ok = (auto.nova_bursts == 0 and abs(dmg(auto) - dmg(off)) < 1e-6 and manual.nova_bursts > 0 and dmg(manual) > dmg(auto)
          and max(a.nova for a in auto.party) > 0)
    return ok, 'bursts auto %d / manual %d, 피해 auto %.0f / manual %.0f / 끔 %.0f' % (
        auto.nova_bursts, manual.nova_bursts, dmg(auto), dmg(manual), dmg(off))


def test_nova_pool():
    """수동에서 팀 공용 풀은 둘이 함께 모아 개인 풀보다 버스트가 많고, 개인 노바는 쌓이지 않는다."""
    team = [unit_def('gwen'), unit_def('amora')] + dummies(2)
    run = lambda pool: Sim(team, ref_enemies(1), 10, dict(LEG, nova_policy='manual', nova_pool=pool)).run()
    u, t = run('unit'), run('team')
    ok = t.nova_bursts > u.nova_bursts and all(a.nova == 0 for a in t.party) and u.team_nova == 0
    return ok, 'bursts unit %d -> team %d' % (u.nova_bursts, t.nova_bursts)


# ---------------------------------------------------------------- 3. 효과 적중
def test_debuff_hit_resist():
    """효과 적중 100% vs 저항 60% -> 0.4, 상성 유리(질서 vs 혼돈) +0.3 -> 0.7, 저항 150% -> 0, constant -> 0.9."""
    s = Sim([unit_def('gwen')] + dummies(3), enemy(0.6), 10, dict(LEG, debuff_model='hit_resist'))
    a, e = s.party[0], s.enemies[0]
    p_plain = s.hit_chance(a, None, e)                       # 그웬 = 별 속성, 적 속성 없음
    so = Sim([unit_def('waltz-asherah')] + dummies(3), enemy(0.6, '혼돈'), 10, dict(LEG, debuff_model='hit_resist'))
    p_elem = so.hit_chance(so.party[0], None, so.enemies[0])  # 아세라(왈츠) = 질서
    sh = Sim([unit_def('gwen')] + dummies(3), enemy(1.5), 10, dict(LEG, debuff_model='hit_resist'))
    p_zero = sh.hit_chance(sh.party[0], None, sh.enemies[0])
    sc = Sim([unit_def('gwen')] + dummies(3), enemy(0.6), 10, dict(LEG, debuff_model='constant'))
    p_const = sc.hit_chance(sc.party[0], None, sc.enemies[0])
    # 실제 전투: 유미나(출혈) 단일 피해는 저항 60% 에서 상수 0.9 보다 낮아야 함
    ym = lambda m: Sim([unit_def('yoo-mina')] + dummies(3), enemy(0.6), 10, dict(LEG, debuff_model=m)).run().party[0].dmg
    ok = (abs(p_plain - 0.4) < 1e-9 and abs(p_elem - 0.7) < 1e-9 and p_zero == 0.0 and p_const == 0.9
          and ym('hit_resist') < ym('constant') and calc_hit(0.7, -0.2) == 0.7 and calc_hit(-0.1, 0.2) == 0.2)
    return ok, 'p 0.6저항 %.3f / 상성 %.3f / 150%%저항 %.3f / 상수 %.3f, 유미나 %.0f < %.0f' % (
        p_plain, p_elem, p_zero, p_const, ym('hit_resist'), ym('constant'))


# ---------------------------------------------------------------- 4. 강제 협공 대상
def test_forced_coop_target():
    """프로페서M 강제 협공: 스탯 공격력 1위는 페이, 아모라에게 공격력 +50% 버프를 주면 live_atk 는 아모라로 바뀐다."""
    got = {}
    for mode in ('stat_atk', 'live_atk'):
        s = Sim([unit_def(k) for k in ('professor-m', 'gwen', 'fei', 'amora')], ref_enemies(1), 10,
                dict(LEG, forced_coop_target=mode))
        pm, amora = s.party[0], s.party[3]
        b = Buff('시험 공버프', {'공격력%': 50.0}, 1, math.inf)
        b.stacks = 1.0
        amora.buffs[b.name] = b
        ln = next(x for x in pm.d.lines if x.eff['kind'] == 'buff' and x.eff['name'] == '강제 협공')
        s.apply_line(pm, ln, Ctx(pm, pm, pm.d.skills['기본기'], False, 1.0), 1.0)
        got[mode] = [x.name for x in s.party if x.cast_count['기본기(추가)'] > 0]
    ok = got['stat_atk'] == ['페이'] and got['live_atk'] == ['아모라']
    return ok, '강제 협공 받은 아군 stat_atk %s / live_atk %s' % (got['stat_atk'], got['live_atk'])


# ---------------------------------------------------------------- 5. DoT
def test_dot_snapshot():
    """연소를 건 뒤 시전자 공격력 +50%: live 는 틱 피해가 커지고 on_apply 는 그대로."""
    out = {}
    for mode in ('on_apply', 'live'):
        s = Sim([unit_def('gwen')] + dummies(3), enemy(), 10, dict(LEG, dot_snapshot=mode))
        a, e = s.party[0], s.enemies[0]
        eff = dict(name='연소', props={}, max=None, times=1, dur=2, chance=1.0, judge=False)
        s.apply_debuff(a, e, eff, 1.0, None)
        b = Buff('시험 공버프', {'공격력%': 50.0}, 1, math.inf)
        b.stacks = 1.0
        a.buffs[b.name] = b
        s.act_enemy(e)
        out[mode] = a.dmg_src['dot']
    ok = out['live'] > out['on_apply'] * 1.3 > 0
    return ok, 'DoT 1틱 on_apply %.1f -> live %.1f' % (out['on_apply'], out['live'])


# ---------------------------------------------------------------- 6. 장비 순서
def test_gear_order():
    """장비 공격력 +300·공격력% +10%: databook = floor(X x 1.10 + 300), legacy = floor(X) + 300(비율 무시). 장비 없으면 둘이 같다."""
    u = DB.units['gwen']
    plain = calc_stats(DB, u, gear_order='databook')
    legacy_plain = calc_stats(DB, u, gear_order='legacy')
    gear = {'atk': 300, 'atkP': 1000}
    new = calc_stats(DB, u, gear=gear, gear_order='databook')
    old = calc_stats(DB, u, gear=gear, gear_order='legacy')
    pre = plain['atk']   # 각인 0 이라 X(공명 반영)의 버림값; X 는 정수가 아닐 수 있어 범위로 확인
    ok = (plain == legacy_plain and old['atk'] == pre + 300 and math.floor(pre * 1.1 + 300) <= new['atk'] <= math.floor((pre + 1) * 1.1 + 300)
          and new['atk'] > old['atk'])
    s3n = calc_stats(DB, u, star=3, gear={'atk': 300}, gear_order='databook')
    s3o = calc_stats(DB, u, star=3, gear={'atk': 300}, gear_order='legacy')
    ok = ok and s3n['atk'] == s3o['atk']   # 정수만이면 순서가 달라도 같은 값
    return ok, '공격력 장비 없음 %d / legacy %d / databook %d / 각인3+정수만 %d=%d' % (pre, old['atk'], new['atk'], s3n['atk'], s3o['atk'])


# ---------------------------------------------------------------- 7. 감소 합
def test_dmg_reduction():
    """대상 감소 합 80% -> 상한 50%: 피해 비율 = (1+0-0.5+cr x cd)/(1+cr x cd). 받는 피해 +20%(전체 대상)는 전체 스킬에만.
    브레이크(break_p=1)만 있으면 교정 전(+15% 증가)과 같다."""
    def hit_once(mode, red, skill_all=False, break_p=0.0):
        s = Sim(dummies(4), enemy(), 10, dict(LEG, dmg_reduction=mode, break_p=break_p))
        a, e = s.party[0], s.enemies[0]
        if red:
            e.deb['감소 시험'] = dict(stacks=1.0, dur=math.inf, red=red)
        sk = a.d.skills['기본기']
        if skill_all:
            sk = DummyDef().skills['기본기']
            sk.all = True
        s.deal_damage(a, Ctx(a, a, sk, False, 1.0))
        return a.dmg
    crit = 0.05 * 0.5
    r_cap = hit_once('sum_cap', {'all': 0.8}) / hit_once('none', {'all': 0.8})
    aoe_up = hit_once('sum_cap', {'aoe': -0.2}, True) / hit_once('none', {'aoe': -0.2}, True)
    single_same = hit_once('sum_cap', {'aoe': -0.2}) / hit_once('none', {'aoe': -0.2})
    brk = hit_once('sum_cap', None, break_p=1.0) / hit_once('none', None, break_p=1.0)
    ok = (abs(r_cap - (0.5 + crit) / (1 + crit)) < 1e-9 and abs(aoe_up - (1.2 + crit) / (1 + crit)) < 1e-9
          and abs(single_same - 1) < 1e-12 and abs(brk - 1) < 1e-12)
    return ok, '감소80%%->비율 %.4f(기대 %.4f), 전체+20%% %.4f, 단일 %.4f, 브레이크만 %.4f' % (
        r_cap, (0.5 + crit) / (1 + crit), aoe_up, single_same, brk)


# ---------------------------------------------------------------- 0. 교정 전 = P1 골든
def test_legacy_reproduces_p1_golden():
    """rules 의 legacy 값만 모으면 P1 골든(tests/golden/sim_golden_p1.json)을 정확히 재현해야 한다."""
    sys.path.insert(0, os.path.join(ROOT, 'tests'))
    import rank_check as rc
    with open(os.path.join(ROOT, 'tests', 'golden', 'sim_golden_p1.json'), encoding='utf-8') as f:
        golden = json.load(f)
    try:
        r = rc.run_one(golden, DB, 'legacy', None, 3)
    finally:
        rc.apply_rules('default', None)
    return r['exact'], '골든 정확 일치 %s (지표 Spearman %.4f, 150팀 %.4f, 처치 턴 바뀐 칸 %d)' % (
        r['exact'], r['index_spearman'], r['party_spearman'], r['stage_changed'])


# ---------------------------------------------------------------- 8. 강제 협공과 협공 1명 자리 (codex 2차 검토 차단 1)
def test_forced_coop_slot():
    """프로페서M 기본기 -> 페이 강제 협공(가중 1.0)이면 같은 공격에 왈츠 아세라(협공 30%) 일반 협공은 0 이어야 한다.
    프로페서M 기본기가 추가 시전(협공·추가 발동)이면 강제 협공이 다시 일어나지 않아야 한다. independent(교정 전)는 둘 다 일어남."""
    out = {}
    for mode in ('independent', 'shared'):
        o = dict(DEFAULT_OPTS, forced_coop_slot=mode)
        s = Sim([unit_def(k) for k in ('professor-m', 'gwen', 'fei', 'waltz-asherah')], ref_enemies(1), 10, o)
        pm, fei, wa = s.party[0], s.party[2], s.party[3]
        coop_buff(wa, 0.3)
        s.cast(pm, pm.d.skills['기본기'])
        normal = (fei.cast_count['기본기(추가)'], wa.cast_count['기본기(추가)'])
        s2 = Sim([unit_def(k) for k in ('professor-m', 'gwen', 'fei', 'waltz-asherah')], ref_enemies(1), 10, o)
        pm2, fei2 = s2.party[0], s2.party[2]
        s2.cast(pm2, pm2.d.skills['기본기'], w=1.0, extra=True)   # 협공·추가 발동으로 나간 프로페서M 기본기
        out[mode] = (normal, fei2.cast_count['기본기(추가)'])
    ok = (out['independent'][0] == (1.0, 0.3) and out['independent'][1] == 1.0
          and out['shared'][0] == (1.0, 0.0) and out['shared'][1] == 0.0)
    return ok, '(페이 강제, 아세라 일반), 추가시전 뒤 페이 강제: independent %s / shared %s' % (out['independent'], out['shared'])


# ---------------------------------------------------------------- 9. 약화 상태(여러 시전자) (codex 2차 검토 차단 2)
def _burn(dur):
    return dict(name='연소', props={}, max=None, times=1, dur=dur, chance=1.0, judge=False)


def test_debuff_state_zero_p():
    """스마일 연소 0.52 중첩·1턴 뒤 크리스텔 연소가 성공 0 이면: per_caster 는 아무것도 안 바뀜(지속 1, 시전자 스마일),
    overwrite(교정 전)는 지속 2·시전자 크리스텔로 덮어씀."""
    out = {}
    for mode in ('overwrite', 'per_caster'):
        s = Sim([unit_def('smile'), unit_def('cristelle')] + dummies(2), enemy(), 10, dict(DEFAULT_OPTS, debuff_state=mode))
        sm, cr, e = s.party[0], s.party[1], s.enemies[0]
        s.apply_debuff(sm, e, _burn(1), 0.52, None)
        s.apply_debuff(cr, e, _burn(2), 0.0, None)
        d = e.deb['연소']
        srcs = [x['src'].name for x in d['subs'].values()] if 'subs' in d else [d['src'].name]
        out[mode] = (round(d['stacks'], 3), d['dur'] if 'subs' not in d else max(x['dur'] for x in d['subs'].values()), srcs)
    ok = out['per_caster'] == (0.52, 1, ['스마일']) and out['overwrite'] == (0.52, 2, ['크리스텔'])
    return ok, 'overwrite %s / per_caster %s' % (out['overwrite'], out['per_caster'])


def test_debuff_state_multi_caster():
    """두 시전자 연소(각 1중첩, 스마일 1턴·크리스텔 2턴): 틱 피해는 둘 다에게 각자 몫, 적 턴이 지나면 스마일 몫만 사라져 1중첩.
    같은 시전자 재시도: 성공 0.3 은 지속 갱신 안 함, 0.7 은 갱신."""
    s = Sim([unit_def('smile'), unit_def('cristelle')] + dummies(2), enemy(), 10, dict(DEFAULT_OPTS, debuff_state='per_caster'))
    sm, cr, e = s.party[0], s.party[1], s.enemies[0]
    s.apply_debuff(sm, e, _burn(1), 1.0, None)
    s.apply_debuff(cr, e, _burn(2), 1.0, None)
    exp_sm = sum(x['base'] for x in e.deb['연소']['subs'].values() if x['src'] is sm)
    s.act_enemy(e)
    d = e.deb['연소']
    after = (round(d['stacks'], 6), [x['src'].name for x in d['subs'].values()])
    both = sm.dmg_src['dot'] > 0 and cr.dmg_src['dot'] > 0 and sm.dmg_src['dot'] < exp_sm * 1.01
    s.apply_debuff(cr, e, _burn(3), 0.3, None)
    low = d['subs'][id(cr)]['dur']
    s.apply_debuff(cr, e, _burn(3), 0.7, None)
    high = d['subs'][id(cr)]['dur']
    # 지속 피해가 아닌 약화(방어력 감소)도 같은 지속 갱신 규칙
    dd = dict(name='방어력 감소', props={'방어력%': -30.0}, max=None, times=1, dur=1, chance=1.0, judge=False)
    s.apply_debuff(sm, e, dd, 1.0, None)
    s.apply_debuff(sm, e, dict(dd, dur=3), 0.3, None)
    nd_low = e.deb['방어력 감소']['dur']
    s.apply_debuff(sm, e, dict(dd, dur=3), 0.7, None)
    nd_high = e.deb['방어력 감소']['dur']
    ok = both and after == (1.0, ['크리스텔']) and low == 1 and high == 3 and nd_low == 1 and nd_high == 3
    return ok, '틱 스마일 %.0f / 크리스텔 %.0f, 적 턴 뒤 %s, 재시도 지속 p0.3 %s / p0.7 %s, 방깎 p0.3 %s / p0.7 %s' % (
        sm.dmg_src['dot'], cr.dmg_src['dot'], after, low, high, nd_low, nd_high)


# ---------------------------------------------------------------- 10. 게이지 기대값 (codex 2차 검토 비차단 3)
def test_gauge_expect():
    """적 게이지 5%(500)에 -25%p 를 성공 0.4 로: exact = 0.4 x 0 + 0.6 x 500 = 300, linear(교정 전) = clamp(500 - 1000) = 0."""
    out = {}
    hl = unit_def('harley')
    hit = hl.stats['eh'] / 10000.0 + hl.passive['eh']
    for mode in ('linear', 'exact'):
        s = Sim([hl] + dummies(3), enemy(resist=hit - 0.4), 10, dict(DEFAULT_OPTS, gauge_expect=mode, debuff_model='hit_resist'))
        a, e = s.party[0], s.enemies[0]
        e.gauge = 500.0
        ln = next(x for x in a.d.lines if x.slot == '특수기' and x.eff['kind'] == 'gauge' and x.eff['val'] == -25)
        s.apply_line(a, ln, Ctx(a, a, a.d.skills['특수기'], False, 1.0), 1.0)
        out[mode] = e.gauge
    ok = abs(out['exact'] - 300) < 1e-6 and out['linear'] == 0
    return ok, 'linear %.1f / exact %.1f' % (out['linear'], out['exact'])


# ---------------------------------------------------------------- 11. 지표 설명은 실제 쓴 옵션으로 (비차단 5)
def test_index_uses_merged_opts():
    from battlesim.metrics import build_index
    idx = build_index(10, {'enemy_resist': 0.2, 'nova_policy': 'manual', 'enemy_def': 700.0}, 0, DB)
    a = idx['gwen']['assumptions']
    ok = (any('효과 저항 20%' in x and '방어력 700' in x for x in a) and any('수동' in x for x in a)
          and idx['_meta']['opts']['enemy_resist'] == 0.2 and idx['_meta']['ref_enemy_def'] == 700.0)
    return ok, '설명 %s / _meta 저항 %s' % (a[1:3], idx['_meta']['opts']['enemy_resist'])


# ---------------------------------------------------------------- 12. MC_OPTS·assumptions_used 목록 스냅샷 + note/alt/legacy 일관성
# note 키 4개를 MC_OPTS 에서 뺐을 때 기존 출력이 그대로인지 고정한다.
# 일부러 깨뜨리기: MC_NOTE_KEYS 를 빈 set() 로 바꾸면 note 키가 MC_OPTS 에 들어가 아래 test_mc_note_not_in_opts 가 실패한다.
_EXPECTED_MC_OPTS_KEYS = frozenset([
    'ally_auto_lines', 'ally_auto_target', 'ally_break_gauge', 'ally_init_cd',
    'auto_skill', 'basic_tough',
    'break_skill_atk_pct', 'break_skill_boss_points', 'break_skill_buff_turns',
    'break_skill_cd_unit', 'break_skill_cooldown', 'break_skill_cost',
    'break_skill_domain_turns', 'break_skill_fixed', 'break_skill_heal_ratio',
    'break_skill_hit_pct', 'break_skill_level', 'break_skill_normal_points',
    'break_skill_point_cap', 'break_skill_role_speed_pct', 'break_skill_scale',
    'break_skill_speed_pct', 'break_skills',
    'buff_maxhp', 'chain_skill_damage_up', 'check_buff_expiry', 'counter_inc',
    'debuff_instance_count', 'effect_dur_extend', 'enemy_auto_target', 'enemy_cd_native',
    'enemy_cd_tick', 'enemy_hit_buff_cmp', 'enemy_init_cd', 'enemy_init_cd_special',
    'enemy_leader', 'enemy_same_formula', 'enemy_spawn', 'evade_model',
    'foe_auto', 'foe_react', 'gauge_conditional', 'gauge_overflow', 'guard_mode', 'guard_normal_hit',
    'heal_target', 'instant_damage', 'leader_speed', 'local_vs_element', 'manual_burst',
    'max_depth', 'max_events', 'myinfo_combat',
    'nova_force_effects', 'nova_skill_gain', 'nova_slot_effects',
    'power_penalty', 'preemptive_defense', 'rand_range', 'reaction_timing', 'revenge',
    'shield_tick', 'stage_fx_target', 'sudden_death', 'summon',
    'target_defender_mult', 'target_mode', 'target_row_weight',
    'taunt_skill_end_duration', 'toughness', 'toughness_elem',
    'turn_limit_unit', 'turn_ticks', 'unknown_cond',
])
_NOTE_KEYS = frozenset({'enemy_skill_ai', 'caster_death', 'wave_carry', 'break_skill_model'})


def test_mc_note_not_in_opts():
    """MC_NOTE_KEYS 가 정확히 4개이며 MC_OPTS 에 없고 MC_RULES 에는 있어야 한다."""
    wrong_note = MC_NOTE_KEYS ^ _NOTE_KEYS          # 대칭 차: 예상과 다른 키
    in_opts = [k for k in MC_NOTE_KEYS if k in MC_OPTS]
    not_in_rules = [k for k in MC_NOTE_KEYS if k not in MC_RULES]
    ok = not wrong_note and not in_opts and not not_in_rules
    return ok, 'note 불일치=%s / opts 잔류=%s / rules 누락=%s' % (sorted(wrong_note), in_opts, not_in_rules)


def test_mc_opts_keys_snapshot():
    """MC_OPTS 키 목록이 고정 집합과 일치해야 한다(note 4개 제거 반영)."""
    got = frozenset(MC_OPTS)
    extra = sorted(got - _EXPECTED_MC_OPTS_KEYS)
    missing = sorted(_EXPECTED_MC_OPTS_KEYS - got)
    ok = not extra and not missing
    return ok, 'extra=%s missing=%s' % (extra, missing)


def test_assumptions_used_note_keys_present():
    """assumptions_used 출력에 note 키 4개가 여전히 포함되고 값이 규칙 기본값이어야 한다."""
    mc_for_test = dict(MC_OPTS)   # note 키 없는 상태
    out = assumptions_used(mc_for_test, dict(DEFAULT_OPTS))
    rules_in_out = {x['rule'] for x in out}
    missing = [k for k in _NOTE_KEYS if ('mc.' + k) not in rules_in_out]
    # 값은 규칙 기본값(MC_OPTS 에 없어서 v['value'] 로 채워야 함)
    wrong_val = []
    for x in out:
        k = x['rule'].replace('mc.', '', 1)
        if k in _NOTE_KEYS:
            expected_val = RULES['mc'][k]['value']
            if x['value'] != expected_val:
                wrong_val.append('%s:%r!=%r' % (k, x['value'], expected_val))
    ok = not missing and not wrong_val
    return ok, 'note 누락=%s / 값 불일치=%s' % (missing, wrong_val)


def test_toughness_elem_no_legacy():
    """toughness_elem 의 legacy==value 표기를 삭제했는지 확인한다."""
    entry = RULES['mc'].get('toughness_elem', {})
    ok = 'legacy' not in entry
    return ok, 'toughness_elem legacy 필드: %s' % entry.get('legacy', '(없음)')


def test_note_keys_not_in_code():
    """note 키 4개는 battlesim/*.py·tools/*.py·sim_worker.js·party_template.html 에서 읽지 않아야 한다.
    grep 기반: 키 이름이 문자열로 나타나면 안 됨(JSON 의 키 정의 자체는 제외, 파이썬·JS 소비 코드만 체크)."""
    import re
    check_dirs = [os.path.join(ROOT, 'battlesim'), os.path.join(ROOT, 'tools')]
    check_files = [os.path.join(ROOT, 'sim_worker.js'), os.path.join(ROOT, 'party_template.html')]
    sources = []
    for d in check_dirs:
        for dirpath, _dirs, fnames in os.walk(d):
            for fn in fnames:
                if fn.endswith('.py'):
                    sources.append(os.path.join(dirpath, fn))
    for f in check_files:
        if os.path.exists(f):
            sources.append(f)
    # 패턴: mc['키'] / self.mc['키'] / mc.get('키') / self.mc.get('키') 형태로 읽는 경우
    found = []
    for path in sources:
        try:
            text = open(path, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for k in _NOTE_KEYS:
            # mc['key'] 또는 mc.get('key') 두 형태를 모두 검사
            pat = r"""(?:mc\s*\[|mc\.get\s*\()\s*['"]""" + re.escape(k) + r"""['"]"""
            if re.search(pat, text):
                found.append('%s:%s' % (os.path.basename(path), k))
    ok = not found
    return ok, '코드에서 note 키 소비: %s' % found


def test_alt_legacy_keys_in_code():
    """alt 또는 legacy 가 있는 mc 키는 battlesim/*.py·tools/*.py·sim_worker.js·party_template.html 중
    한 곳 이상에서 읽어야 한다(grep 기반: 코드에 없으면 dead 스위치)."""
    import re
    check_dirs = [os.path.join(ROOT, 'battlesim'), os.path.join(ROOT, 'tools')]
    check_files = [os.path.join(ROOT, 'sim_worker.js'), os.path.join(ROOT, 'party_template.html')]
    sources = []
    for d in check_dirs:
        for fn in os.listdir(d):
            if fn.endswith('.py'):
                sources.append(os.path.join(d, fn))
    for f in check_files:
        if os.path.exists(f):
            sources.append(f)
    combined = ''
    for path in sources:
        try:
            combined += open(path, encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    alt_legacy_keys = [k for k, v in MC_RULES.items()
                       if ('alt' in v or 'legacy' in v) and k not in MC_NOTE_KEYS]
    missing = []
    for k in alt_legacy_keys:
        if not re.search(r"""['"]""" + re.escape(k) + r"""['"]""", combined):
            missing.append(k)
    ok = not missing
    return ok, 'alt/legacy 키인데 코드에 없음: %s' % missing


TESTS = [test_coop_trigger, test_coop_single, test_nova_policy, test_nova_pool, test_debuff_hit_resist, test_forced_coop_target,
         test_dot_snapshot, test_gear_order, test_dmg_reduction, test_forced_coop_slot, test_debuff_state_zero_p,
         test_debuff_state_multi_caster, test_gauge_expect, test_index_uses_merged_opts, test_legacy_reproduces_p1_golden,
         test_mc_note_not_in_opts, test_mc_opts_keys_snapshot, test_assumptions_used_note_keys_present,
         test_toughness_elem_no_legacy, test_note_keys_not_in_code, test_alt_legacy_keys_in_code]


def main():
    sel = sys.argv[1:]
    ok_all = True
    before = dict(DEFAULT_OPTS)
    for t in TESTS:
        if sel and not any(x in t.__name__ for x in sel):
            continue
        try:
            ok, msg = t()
        except Exception as ex:   # 시험 자체 오류도 실패로
            ok, msg = False, '오류: %r' % (ex,)
        print('%s %s - %s' % ('PASS' if ok else 'FAIL', t.__name__, msg))
        ok_all = ok_all and ok
    if dict(DEFAULT_OPTS) != before:
        print('FAIL DEFAULT_OPTS 가 시험 뒤에 바뀌어 있음')
        ok_all = False
    print('ALL', 'OK' if ok_all else 'FAILED')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
