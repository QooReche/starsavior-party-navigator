# -*- coding: utf-8 -*-
"""시나리오·지표: 개인 지표(단일/광역 기대 피해, 아군 피해 증가), 파티 시뮬, 대표 스테이지, damage_index 생성."""
import math
from collections import defaultdict

from .engine import DummyDef, Sim
from .rules import ASSUMPTIONS, DEFAULT_OPTS, FOE_ELEM, INF_HP, KNOWN_DOT, TICK_PER_TURN
from .starsavior.data import get_db
from .starsavior.parser import UnitDef

_CACHE = {}
def unit_def(key, level=200, res_stage=10, star=0, mode='fixed', db=None):
    ck = (key, level, res_stage, star, mode)
    if ck not in _CACHE:
        _CACHE[ck] = UnitDef(db or get_db(), key, level, res_stage, star, mode)
    return _CACHE[ck]

# ------------------------------------------------------------------ 시나리오 / 지표
def ref_enemies(n, opts=None):
    o = dict(DEFAULT_OPTS)
    if opts:
        o.update(opts)
    return [dict(name='ref%d' % i, hp=INF_HP, **{'def': o['enemy_def']}, spd=o['enemy_spd'], element=o['enemy_element'],
                 resist=o['enemy_resist']) for i in range(n)]


def solo_run(key, n_enemies, turns=10, opts=None, star=0, partners=3):
    d = unit_def(key, star=star)
    defs = [d] + [DummyDef(name='dummy%d' % i) for i in range(partners)]
    sim = Sim(defs, ref_enemies(n_enemies, opts), turns, opts)
    sim.run()
    return sim


def unit_metrics(key, turns=10, opts=None, star=0):
    o = dict(DEFAULT_OPTS)
    if opts:
        o.update(opts)
    s1 = solo_run(key, 1, turns, o, star)
    s3 = solo_run(key, o['ref_enemy_count'], turns, o, star)
    a1, a3 = s1.party[0], s3.party[0]
    res = dict(
        single_dpt=a1.dmg / turns, aoe_dpt=a3.dmg / turns,
        single_hits_pt=a1.hits / turns, aoe_hits_pt=a3.hits / turns,
        actions_pt=a1.actions / turns,
        extra_share=(a1.dmg_src['extra'] + a1.dmg_src['chain'] + a1.dmg_src['dot']) / a1.dmg if a1.dmg > 0 else 0.0,
        casts={k: round(v / 1.0, 2) for k, v in a1.cast_count.items()},
        unmodeled=dict(s1.unmodeled),
    )
    return res


def ally_gain(key, turns=10, opts=None, star=0, n_synth=3):
    """key 가 합성 딜러 3명에게 주는 피해 증가율 (버프형 지원 가치). 합성 딜러만 4명인 기준 대비 3명분 비교"""
    o = dict(DEFAULT_OPTS)
    if opts:
        o.update(opts)
    d = unit_def(key, star=star)
    synth = lambda: [DummyDef(name='s%d' % i) for i in range(n_synth)]
    # 합성 딜러는 DummyDef 라 아군 효과(공격력 증가 등)를 받는지 mods()로 확인: DummyDef 도 Actor 로 감싸므로 받는다.
    base_sim = Sim(synth() + [DummyDef(name='x')], ref_enemies(1, o), turns, o).run()
    base = sum(a.dmg for a in base_sim.party[:n_synth])
    sim = Sim([d] + synth(), ref_enemies(1, o), turns, o).run()
    withu = sum(a.dmg for a in sim.party[1:])
    return withu / base - 1 if base else 0.0


# ------------------------------------------------------------------ 파티 시뮬 / 스테이지
STAGES = [
    ('cosmo', '길레', '길레 1단계'),
    ('cosmo', '길레', '길레 2단계'),
    ('cosmo', '길레', '길레 3단계'),
    ('rush', '매니저 그레고리', '매니저 그레고리 Ⅰ'),
    ('rush', '매니저 그레고리', '매니저 그레고리 Ⅱ'),
]


def stage_enemies(db, content, tab, name):
    st = db.find_stage(content, tab, name)
    out = []
    for e in st['enemies']:
        for _ in range(e.get('count', 1)):
            out.append(dict(name=e['name'], hp=e['stats']['hp'], **{'def': e['stats']['def']}, spd=e['stats']['spd'],
                            element=FOE_ELEM.get(e['element']), boss=e['boss'],
                            resist=e['stats'].get('evade', 0) / 10000.0, abs_resist=e['stats'].get('abs_evade', 0) / 10000.0))
    return st, out


def simulate_party(keys, enemies=None, turns=10, opts=None, star=0, stars=None, max_turns=40, db=None):
    """파티 4명(구원자 key 목록) 시뮬. enemies=None 이면 기준 적 1체(HP 무한).
    반환: total_damage, per_unit, ttk_turns(처치 못하면 None), hp_total, frac_in_N"""
    defs = []
    for i, k in enumerate(keys):
        s = stars[i] if stars else star
        defs.append(unit_def(k, star=s, db=db))
    en = enemies if enemies is not None else ref_enemies(1, opts)
    hp_total = sum(e['hp'] for e in en)
    sim = Sim(defs, en, turns, opts).run()
    total = sum(a.dmg for a in sim.party)
    res = dict(total_damage=total, per_unit={a.name + ('#' + str(a.idx)): round(a.dmg) for a in sim.party},
               hits=sum(a.hits for a in sim.party), turns=turns, hp_total=hp_total,
               frac_in_N=min(1.0, total / hp_total) if hp_total < INF_HP / 2 else None,
               dmg_src={k: sum(a.dmg_src[k] for a in sim.party) for k in ('direct', 'extra', 'chain', 'dot')})
    if hp_total < INF_HP / 2:
        long = Sim(defs, en, max_turns, opts).run()
        res['ttk_turns'] = (long.kill_time / TICK_PER_TURN) if long.kill_time is not None else None
    return res


def stage_report(keys, turns=10, opts=None, star=0, stars=None, db=None):
    db = db or get_db()
    rows = []
    for (c, tab, nm) in STAGES:
        st, en = stage_enemies(db, c, tab, nm)
        r = simulate_party(keys, en, turns, dict(opts or {}, enemy_element=None), star, stars, db=db)
        rows.append(dict(stage=nm, hp=r['hp_total'], dmg=round(r['total_damage']), frac=r['frac_in_N'], ttk=r.get('ttk_turns')))
    return rows

# ------------------------------------------------------------------ 지표 / 인덱스
def describe(d):
    parts = []
    for slot in ('기본기', '특수기', '궁극기'):
        sk = d.skills.get(slot)
        if not sk:
            continue
        cf = sk.cf
        sc = []
        if cf[0]: sc.append('공%d%%' % (cf[0] / 100))
        if cf[1]: sc.append('생%d%%' % (cf[1] / 100))
        if cf[2]: sc.append('방%d%%' % (cf[2] / 100))
        if not sk.is_attack:
            sc = ['비공격']
        parts.append('%s %s%s%s' % (slot, '/'.join(sc), '(전체)' if sk.all else '', (' cd%s' % sk.cd) if sk.cd else ''))
    return ' | '.join(parts)


def mechanics(d):
    """파싱된 줄에서 화력에 영향을 주는 메커니즘 요약 (근거 표시용)"""
    c = defaultdict(int)
    for ln in d.lines:
        e = ln.eff
        k = e['kind']
        if k == 'local':
            if e['stat'] == '피해 증가' and ln.params:
                c['조건부 피해증가'] += 1
            elif e['stat'] in ('공격력%', '치명타 확률', '치명타 피해', '방어 관통'):
                c['스킬 한정 ' + e['stat']] += 1
        elif k == 'extra_cast':
            c['추가 발동'] += 1
        elif k == 'extra_turn':
            c['추가 턴'] += 1
        elif k == 'chain':
            c['연쇄 피해'] += 1
        elif k == 'gauge' and e['target'].startswith('자신') and e['val'] > 0:
            c['자기 행동게이지 증가'] += 1
        elif k == 'gauge' and e['val'] < 0:
            c['적 행동게이지 감소'] += 1
        elif k == 'cdr':
            c['쿨타임 감소'] += 1
        elif k == 'buff':
            if e.get('dot') or (e['name'] in KNOWN_DOT and not e['props']):
                c['지속 피해(DoT)'] += 1
            elif e['target'].startswith('적'):
                if '방어력%' in e['props']:
                    c['적 방어력 감소'] += 1
            elif any(p in e['props'] for p in ('공격력%', '치명타 확률', '치명타 피해', '속도%', '피해 증가')):
                c['아군 버프' if not e['target'].startswith('자신에') else '자버프'] += 1
            elif e['name'] == '강제 협공':
                c['강제 협공'] += 1
            elif e['props'] == {} and e['dur'] in (None, math.inf):
                pass
        elif k == 'perm' and e['stat'] == '공격력%':
            c['패시브 공격력%'] += 1
    return ['%s x%d' % (k, v) for k, v in sorted(c.items(), key=lambda kv: -kv[1])]


def build_index(turns=10, opts=None, star=0, db=None):
    db = db or get_db()
    o = dict(DEFAULT_OPTS, **(opts or {}))   # 실제로 쓴 옵션(설명·_meta 도 이 값으로)
    out = {}
    for key in db.units:
        d = unit_def(key, star=star, db=db)
        m = unit_metrics(key, turns, opts, star)
        g = ally_gain(key, turns, opts, star)
        st = d.stats
        out[key] = dict(
            name=d.name, variant=d.variant, id=d.id, role=d.role, grade=d.grade, element=d.element,
            stats=dict(hp=st['hp'], atk=st['atk'], def_=st['def'], spd=st['spd'], cr=st['cr'] / 100, cd=st['cd'] / 100,
                       passive_atk_pct=round(d.passive['atkp'] * 100, 1)),
            single_dpt=round(m['single_dpt']), aoe_dpt=round(m['aoe_dpt']),
            hits_per_turn=round(m['single_hits_pt'], 2), actions_per_turn=round(m['actions_pt'], 2),
            extra_hit_dmg_share=round(m['extra_share'], 3), ally_dmg_gain_pct=round(g * 100, 1),
            casts=m['casts'],
            summary=describe(d),
            evidence=mechanics(d),
            ally_dependent=bool(d.manual or any(ln.kind in ('ally_pre', 'ally_post', 'ally_ts') for ln in d.lines)
                                or any(ln.eff['kind'] == 'buff' and '협공 확률' in ln.eff['props'] for ln in d.lines)),
            assumptions=['Lv200/공명10/각인%d/장비 없음/스킬 최대 레벨' % star,
                         '기준 적: 방어력 %d, 효과 저항 %d%%, 속성 없음, 단일=1체/광역=3체, 10턴(=1000틱)'
                         % (o['enemy_def'], round(o['enemy_resist'] * 100)),
                         '오토 전투(노바 버스트 안 씀)' if o['nova_policy'] == 'auto' else '수동(노바 버스트 사용)',
                         '파트너: 더미 딜러 3명(아군 공격 트리거 공급, 버프 없음)'] +
                        (['반응(피격/회피) 트리거 스킬은 피해에 미반영'] if any('반응' in x for x in d.unmodeled) else []) +
                        (['변형(교체) 스킬 미반영'] if any('변형' in x for x in d.unmodeled) else []),
            unmodeled=sorted(set(d.unmodeled))[:8],
            unparsed_conditions=m['unmodeled'],
        )
    # 정규화
    dealers = ('스트라이커', '레인저', '캐스터', '어쌔신')
    comb = {k: 0.5 * v['single_dpt'] + 0.5 * v['aoe_dpt'] for k, v in out.items()}
    ref_pool = sorted([comb[k] for k, v in out.items() if v['role'] in dealers and v['grade'] == 'SSR'])
    ref95 = ref_pool[min(len(ref_pool) - 1, int(0.95 * len(ref_pool)))]
    ref_s = sorted([out[k]['single_dpt'] for k in out if out[k]['role'] in dealers and out[k]['grade'] == 'SSR'])
    ref_a = sorted([out[k]['aoe_dpt'] for k in out if out[k]['role'] in dealers and out[k]['grade'] == 'SSR'])
    rs95 = ref_s[min(len(ref_s) - 1, int(0.95 * len(ref_s)))]
    ra95 = ref_a[min(len(ref_a) - 1, int(0.95 * len(ref_a)))]
    role_max = defaultdict(float)
    for k, v in out.items():
        role_max[v['role']] = max(role_max[v['role']], comb[k])
    for k, v in out.items():
        v['combined_dpt'] = round(comb[k])
        v['norm_global'] = round(min(10.0, 10 * comb[k] / ref95), 2)
        v['norm_single_global'] = round(min(10.0, 10 * v['single_dpt'] / rs95), 2)
        v['norm_aoe_global'] = round(min(10.0, 10 * v['aoe_dpt'] / ra95), 2)
        v['norm_role'] = round(10 * comb[k] / role_max[v['role']], 2) if role_max[v['role']] else 0.0
    out['_meta'] = dict(
        turns=turns, star=star, level=200, res_stage=10, ref_enemy_def=o['enemy_def'],
        normalization=dict(norm_global='10 * (0.5*단일+0.5*광역 dpt) / (SSR 딜러 4역할 상위 95% 값), 10 상한',
                           norm_role='10 * dpt / 같은 역할 최대치', ref95_combined=round(ref95)),
        assumptions=ASSUMPTIONS, opts=dict(o),
    )
    return out
