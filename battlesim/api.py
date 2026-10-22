# -*- coding: utf-8 -*-
"""재사용 계약(docs/battlesim_design.md 2절): simulate(party_spec, encounter_spec, options) -> result.

party_spec
  ["professor-m", "gwen", "fei", "amora"]  또는  {"units": [...], "leader": 0}
  유닛 = key/이름 문자열 또는 {"key", "level"(200), "res"(10), "star"(0), "build", "stats_override"{hp,atk,def,spd,cr,cd,eh,er}, "stats_final"(false)}
  내정보 계산 결과: {"key": key, "build": "none", "stats_override": result["stats"], "stats_final": true, "power": result["power"], "myinfo_combat": result["combat"]}.
  power = 계산기 전투력(선택). 생략하면 기존 스킬 레벨 합 34 가정으로 계산한다.
       유닛 build 는 options.build 보다 우선한다. none 은 표준 장비·잠재력·그 조건부 효과를 추가하지 않는다.
       myinfo_combat 는 실제 스킬 레벨·습득 잠재력의 전투 효과만 추가하며 표준 build를 대체한다(mc.myinfo_combat=false로 종전 동작).
  stats_final = true 면 stats_override 를 인게임 능력치 화면의 «최종값»으로 보고 상시 패시브 능력치 %(고유 패시브 「능력치: 생명력% +15%」 등)를
       다시 곱하지 않는다(근거: 화면 값 그대로 넣은 전투력 공식이 화면 전투력에 더 가깝다 — 카르멘 94,650 vs 화면 94,920, 패시브를 곱하면 101,850. docs/ingame_samples.md)
  순서 0·1 = 전열, 2·3 = 후열(인게임 편성 칸). leader = 리더 칸 번호(속도 +10), 없으면 리더 없음.
encounter_spec
  {"stage": {"content": "cosmo", "tab": "길레", "name": "길레 1단계"}}  또는  {"stage": "cosmo/길레/길레 1단계"}
  {"waves": [[적, ...], ...]}  적 = {"foe": u 번호, "variant": x 번호, "stats_override": {...}} 또는 명시
       {"name", "hp", "atk", "def", "spd", "cr", "cd", "eh", "er", "role", "element", "boss",
        "skills": [{"slot": "기본기", "dm": 80, "all": false, "cd": null, "tg": "적 단일"}]}
  선택: "turn_limit"(스테이지 lt 를 덮어씀), "stage_fx"(문장 목록, 스테이지 fx 를 덮어씀), "max_turns"(턴 제한 없을 때 시간 상한, 50)
options
  {"seed": 1, "n_runs": 100, "rules_override": {mc·opts 키: 값}, "nova_policy": "auto"|"manual"|"heal", "timeline": false,
   "enemy_lines": true, "run_offset": 0, "per_run": false, "formula_override": {"COOP_CAP": 1.0}, "rekindle": 0,
   "break_skill": {"name": "큐브 과부하", "level": 5}}
  break_skill = 생략/None 이면 미장착. 큐브 과부하·특이점 관측·스타피어서·차원 강습 지원(모든 레벨 동일 계수), 다른 이름은 unsupported.runtime 에 기록.
  rekindle = 작전 재점화 버프 단계 0~5(작전 op 에서만): 아군 주는 피해 ×(1+x)·받는 피해 ×(1−x), x = REKINDLE[단계]
       (인게임 표 2026-10-21 사용자 제보, 전투력 보정과 곱으로 합침 — 곱인지 증감 합인지는 미확인)
  run_offset = 판 번호 시작값(판 r 의 난수 = seed*1000003 + run_offset + r; timeline 은 첫 판 = run_offset 번 판)
  per_run = true 면 result.runs = [[결과, 처치 턴 또는 null], ...](판 순서)
  formula_override = 공식 상수 임시 교체(민감도용, 지금은 COOP_CAP 만). 실행이 끝나면 원래 값으로 돌린다
result
  {schema_version, outcome{clear_p, wipe_p, timeout_p, ci95{...}, n_runs, n_clear, ttk_median, ttk_p10_p90, ttk_basis},
   per_unit{이름#칸: {dmg_share, dmg, dmg_taken, heal, shield, death_p, death_turn_median, first_death_p, actions}},
   foes{...}, break_skill{name, uses, dmg, supported, points_gained}(판 평균, dmg 는 개인 기여 제외, points_gained 는 상한 적용 후 실제 적립),
   nova_burst{total, uses, by_unit{이름#칸: {슬롯: 전체 판 횟수}}}(uses는 판 평균),
   timeline?, assumptions_used[], unsupported{static[], runtime{}, critical, gate_ok}, runtime_ms_per_run}"""
import math
import random
import statistics
import time
from collections import defaultdict

from . import rules as _rules
from .mc import Battle, EventLimitError, support_report
from .rules import DEFAULT_OPTS, MC_OPTS, MC_RULES, RULES
from .starsavior.data import _find_key, get_db
from .starsavior.foe import FoeDef, load_foe, parse_fx, stage_waves
from .starsavior.parser import Skill, UnitDef
from .starsavior.mc_semantics import normalized_definition

SCHEMA_VERSION = 'p5-1'   # p5-1: 육성 프리셋(build)·강인도/브레이크·피해 제한·전투력 보정 옵션, result.party.power·breaks·depth_runs


class _CustomFoe:
    """encounter_spec 에 직접 적은 적(시험·가상 보스용)"""
    is_foe = True

    def __init__(self, spec, i):
        from collections import defaultdict as dd
        self.key = 'custom:%d' % i
        self.name = spec.get('name', 'enemy%d' % i)
        self.id, self.variant = -1, '적'
        self.role = spec.get('role', '스트라이커')
        self.element = spec.get('element')
        self.boss = bool(spec.get('boss', False))
        self.grade = '보스' if self.boss else '일반'
        self.attack_kind = None
        self.stats = dict(hp=spec.get('hp', 100000), atk=spec.get('atk', 1000), **{'def': spec.get('def', 1000)},
                          spd=spec.get('spd', 100), cr=spec.get('cr', 1500), cd=spec.get('cd', 3000), eh=spec.get('eh', 10000),
                          er=spec.get('er', 0), der=spec.get('der', 0), sa=spec.get('sa', 10))
        self.immune = set(spec.get('immune', []))
        self.skills, self.trigger_skills, self.lines, self.unmodeled = {}, {}, [], []
        for s in spec.get('skills') or [dict(slot='기본기', dm=100)]:
            sk = Skill(dict(sl=s['slot'], n=s.get('name', s['slot']), ty='액티브', tg=s.get('tg', '적 전체' if s.get('all') else '적 단일'),
                            act='공격' if s.get('dm') else '비공격', cf=[round(float(s.get('dm') or 0) * 100), 0, 0, 0],
                            all=s.get('all'), cd=s.get('cd'), nv=0))
            self.skills[s['slot']] = sk
        self.passive = dd(float)
        self.nb = {}
        self.manual = None
        self.gear_atkp = 0.0
        self.spd_base = self.stats['spd']


# 능력치 화면에 이미 들어 있는 상시 % (parser._perm_apply) — 입력 능력치 -> 뺄 passive 키
FINAL_PASSIVE_KEYS = {'atk': ('atkp',), 'hp': ('hpp',), 'def': ('defp',), 'spd': ('spdp', 'spdf'), 'cr': ('cr',), 'cd': ('cd',), 'eh': ('eh',)}


def _norm_party(party_spec, db, mode, build=None, mc=None):
    if isinstance(party_spec, dict):
        units, leader = party_spec.get('units', []), party_spec.get('leader')
    else:
        units, leader = list(party_spec), None
    defs = []
    for u in units:
        if isinstance(u, str):
            u = dict(key=u)
        key = _find_key(db, u['key'])
        from .starsavior.myinfo_combat import select_skills, apply_potentials
        combat = u.get('myinfo_combat') if (mc or MC_OPTS).get('myinfo_combat', True) else None
        unit_data = select_skills(db.units[key], key, combat) if combat is not None else None
        d = UnitDef(db, key, u.get('level', 200), u.get('res', 10), u.get('star', 0), u.get('mode', mode),
                    build='none' if combat is not None else u.get('build', build), unit_data=unit_data)
        d = normalized_definition(d)
        d.power_override = u.get('power')
        if u.get('stats_override'):
            d.stats.update(u['stats_override'])
            d.spd_base = d.stats['spd']
            if u.get('stats_final'):
                for st in u['stats_override']:          # 입력한 능력치에 대응하는 상시 % 만 뺀다(부분 입력 시 나머지는 그대로 — codex 리뷰)
                    for k in FINAL_PASSIVE_KEYS.get(st, ()):
                        d.passive[k] = 0.0
        if combat is not None:
            apply_potentials(d, db, combat)
        defs.append(d)
    return defs, leader


def _norm_encounter(enc):
    """-> (waves[[def]], turn_limit, fx_props, fx_unknown, stage_meta)"""
    meta = {}
    turn_limit = enc.get('turn_limit')
    fx_texts = enc.get('stage_fx')
    if 'stage' in enc:
        s = enc['stage']
        if isinstance(s, str):
            content, tab, name = s.split('/', 2)
        else:
            content, tab, name = s['content'], s['tab'], s['name']
        st, waves = stage_waves(content, tab, name)
        meta = dict(content=content, tab=tab, name=name, level=st.get('lv'), recommended_power=st.get('bp'),
                    wave_count=len(waves), fixed_player=st.get('fix'))
        if turn_limit is None:
            turn_limit = st.get('lt')
        if fx_texts is None:
            fx_texts = st.get('fx') or []
    else:
        raw = None
        waves = []
        i = 0
        for w in enc['waves']:
            row = []
            for e in w:
                if 'foe' in e:
                    raw = raw or load_foe()
                    row.append(FoeDef(raw, e['foe'], e.get('variant'), {'lv': e.get('level')} if e.get('level') else {},
                                      e.get('stats_override')))
                else:
                    row.append(_CustomFoe(e, i))
                i += 1
            waves.append(row)
    fx, unknown = parse_fx(fx_texts or [])
    return waves, turn_limit, fx, unknown, meta


def _wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def assumptions_used(mc, opts):
    """이번 실행에서 쓴 규칙 중 근거 등급이 data 가 아닌 것(값 포함)"""
    out = []
    for k, v in MC_RULES.items():
        if v.get('grade') != 'data':
            out.append(dict(rule='mc.' + k, value=mc.get(k), grade=v.get('grade'), note=v.get('note')))
    for k, v in RULES['mc'].get('break_skills', {}).items():
        out.append(dict(rule='mc.break_skills.' + k, value=mc['break_skills'].get(k), grade=v.get('grade'), note=v.get('note')))
    for k in ('coop_trigger', 'coop_single', 'nova_policy', 'nova_pool', 'forced_coop_target', 'init_cd_frac'):
        r = RULES['opts'].get(k, {})
        out.append(dict(rule='opts.' + k, value=opts.get(k), grade=r.get('grade'), note=r.get('note')))
    out.append(dict(rule='model.not_modeled', value=None, grade='assumed',
                    note='행성 정화·브레이크 스킬 레벨 보정, 반격·선제 방어(회피는 evade_model 로 지원), 표에 없는 「피해 제한」 효과(실행 전 검사에서 중요 미지원으로 표시), '
                         '노바 버스트 슬롯 효과(+15% 외), 일반 잠재력(감각·솜씨)·전술 분석·호감도, 시즌 보너스, Lv200 초과 성장, '
                         '대부분의 반응 트리거 스킬(웨딩 카르멘 「수호의 기사」·프로페서M 「악에서 악으로」만 지원), 연쇄 피해의 「턴 끝에 발생」 시점'))
    out.append(dict(rule='model.random_choice', value='uniform', grade='assumed',
                    note='가중치가 명시되지 않은 무작위 효과·무작위 적은 균등 추첨. 핀볼 타임!·특급 배송의 실제 개별 확률은 자료 미기재로 미확인'))
    return out


def party_power(defs):
    """입력 전투력 또는 databook 공식의 합. 입력 없으면 스킬 레벨 합 34·전투력 잠재력 0 가정."""
    from .starsavior.build import unit_power
    tot = 0
    for d in defs:
        if getattr(d, 'power_override', None) is not None:
            tot += d.power_override
            continue
        s = dict(d.stats)
        p = d.passive
        s['atk'] = s['atk'] * (1 + p['atkp'])
        s['hp'] = s['hp'] * (1 + p['hpp'])
        s['def'] = s['def'] * (1 + p['defp'])
        s['spd'] = s['spd'] * (1 + p['spdp']) + p['spdf']
        s['cr'] = s['cr'] + p['cr'] * 10000
        s['cd'] = s['cd'] + p['cd'] * 10000
        s['eh'] = s.get('eh', 10000) + p['eh'] * 10000
        tot += unit_power(s)
    return tot


def power_pen(power, rec, db):
    """(비율%, 아군 피해 배율, 적 피해 배율) — databook topics.pen(비율 = floor(전투력 x 10000 / 권장))"""
    if not rec or not power:
        return None
    r = math.floor(power * 10000 / rec)
    for lo, hi, a, e in db.main['topics']['pen']:
        if lo <= r < hi:
            return r / 100.0, a / 10000.0, e / 10000.0
    if r >= max(row[1] for row in db.main['topics']['pen']):
        return r / 100.0, 1.0, 1.0
    row = min(db.main['topics']['pen'], key=lambda x: x[0])
    return r / 100.0, row[2] / 10000.0, row[3] / 10000.0


def simulate(party_spec, encounter_spec, options=None):
    o = dict(options or {})
    seed = int(o.get('seed', 1))
    n_runs = o.get('n_runs', 100)
    if isinstance(n_runs, bool) or not isinstance(n_runs, int) or n_runs < 1:
        raise ValueError('n_runs 는 양의 정수여야 함')
    over = dict(o.get('rules_override') or {})
    if 'nova_policy' in o:
        over['nova_policy'] = o['nova_policy']
    mc = dict(MC_OPTS, **{k: v for k, v in over.items() if k in MC_OPTS})
    opts = dict(DEFAULT_OPTS, **{k: v for k, v in over.items() if k in DEFAULT_OPTS})
    unknown_keys = [k for k in over if k not in MC_OPTS and k not in DEFAULT_OPTS]
    if unknown_keys:
        raise ValueError('모르는 규칙 키: %s' % ', '.join(unknown_keys))
    fo = dict(o.get('formula_override') or {})
    bad = [k for k in fo if k not in ('COOP_CAP',)]
    if bad:
        raise ValueError('바꿀 수 없는 공식 상수: %s' % ', '.join(bad))
    saved = {k: getattr(_rules, k) for k in fo}
    try:
        for k, v in fo.items():
            setattr(_rules, k, v)
        return _simulate(party_spec, encounter_spec, o, seed, n_runs, mc, opts)
    finally:
        for k, v in saved.items():
            setattr(_rules, k, v)


REKINDLE = [0.0, 0.03, 0.07, 0.12, 0.18, 0.25]     # 작전 재점화 버프 단계별 (주는 피해 +x, 받는 피해 −x) — 인게임 표(2026-10-21 사용자 제보)


def _simulate(party_spec, encounter_spec, o, seed, n_runs, mc, opts):
    db = get_db()
    build = o.get('build', 'none')
    defs, leader = _norm_party(party_spec, db, o.get('stat_mode', 'fixed'), build, mc)
    if not defs:
        raise ValueError('party_spec 이 비어 있음')
    waves, turn_limit, fx, fx_unknown, meta = _norm_encounter(encounter_spec)
    max_turns = encounter_spec.get('max_turns', 50)
    power = party_power(defs)
    pp = power_pen(power, meta.get('recommended_power'), db)
    pen = None
    pen_note = None
    if mc['power_penalty'] == 'model' and pp:
        if meta.get('content') == 'rush':
            pen_note = '플래시 포인트는 전투력 보정 미적용'
        else:
            pen = (pp[1], pp[2])
    elif mc['power_penalty'] not in ('off', 'model'):
        raise ValueError('power_penalty 는 off|model: %r' % mc['power_penalty'])
    rk = int(o.get('rekindle') or 0)
    if rk and meta.get('content') == 'op':
        if not 0 < rk < len(REKINDLE):
            raise ValueError('rekindle 은 0~%d: %r' % (len(REKINDLE) - 1, rk))
        x = REKINDLE[rk]
        a0, e0 = pen or (1.0, 1.0)
        pen = (a0 * (1 + x), e0 * (1 - x))
    static = support_report(defs + [d for w in waves for d in w])
    names = ['%s#%d' % (d.name, i) for i, d in enumerate(defs)]
    agg = defaultdict(lambda: defaultdict(list))
    foe_agg = defaultdict(lambda: defaultdict(list))
    outcomes = defaultdict(int)
    ttk = []
    runtime = defaultdict(int)
    runs_affected = 0
    depth_runs = 0
    breaks = [0, 0]
    break_uses = break_points_gained = break_dmg = 0
    nova_counts = defaultdict(lambda: defaultdict(int))
    timeline = None
    first = defaultdict(int)
    offset = int(o.get('run_offset', 0))
    per_run = [] if o.get('per_run') else None
    t0 = time.perf_counter()
    for r in range(n_runs):
        rng = random.Random(seed * 1000003 + offset + r)
        b = Battle(defs, waves, rng, opts, mc, leader=leader, fx=fx if mc['stage_fx_target'] == 'enemies' else {},
                   turn_limit=turn_limit, timeline=bool(o.get('timeline')) and r == 0,
                   enemy_lines=o.get('enemy_lines', True), max_turns=max_turns, pen=pen, break_skill=o.get('break_skill'))
        b.run()   # EventLimitError 는 그대로 올린다(정상 결과 금지)
        for (pos, slot), count in b.nova_bursts.items():
            nova_counts[names[pos]][slot] += count
        break_uses += b.break_skill_uses
        break_dmg += b.break_skill_dmg
        break_points_gained += b.break_points_gained
        outcomes[b.result] += 1
        if b.result == 'clear':
            ttk.append(b.clear_t / b.turn_ticks)
        if per_run is not None:
            per_run.append([b.result, round(b.clear_t / b.turn_ticks, 3) if b.result == 'clear' else None])
        tot = sum(u.dmg for u in b.allies) or 1.0
        for i, u in enumerate(b.allies):
            a = agg[names[i]]
            a['dmg'].append(u.dmg)
            a['share'].append(u.dmg / tot)
            a['taken'].append(u.taken)
            a['heal'].append(u.healed)
            a['shield'].append(u.shield_given)
            a['dead'].append(1 if u.dead else 0)
            a['actions'].append(u.actions)
            if u.dead and u.death_t is not None:
                a['death_turn'].append(u.death_t / b.turn_ticks)
        if b.first_death is not None:
            first[names[b.first_death.pos]] += 1
        per_foe = defaultdict(float)
        for u in b.all_foes:          # 모든 웨이브의 적(같은 이름은 합산)
            per_foe[u.name] += u.dmg
        for k, v in per_foe.items():
            foe_agg[k]['dmg'].append(v)
            foe_agg[k]['seen'].append(1)
        if b.unsup:
            runs_affected += 1
            if any(k.startswith('depth:') for k in b.unsup):
                depth_runs += 1
            for k, v in b.unsup.items():
                runtime[k] += v
        for u in b.allies:
            breaks[0] += u.breaks
        for u in b.all_foes:
            breaks[1] += u.breaks
        if b.timeline is not None:
            timeline = b.timeline
    elapsed = time.perf_counter() - t0
    n = n_runs
    per_unit = {}
    for nm in names:
        a = agg[nm]
        per_unit[nm] = dict(
            dmg_share=round(statistics.fmean(a['share']), 4), dmg=round(statistics.fmean(a['dmg'])),
            dmg_taken=round(statistics.fmean(a['taken'])), heal=round(statistics.fmean(a['heal'])),
            shield=round(statistics.fmean(a['shield'])), death_p=round(statistics.fmean(a['dead']), 4),
            death_turn_median=round(statistics.median(a['death_turn']), 2) if a['death_turn'] else None,
            first_death_p=round(first[nm] / n, 4), actions=round(statistics.fmean(a['actions']), 2))
    crit_lines = [x for x in static if x['critical']]
    res = dict(
        schema_version=SCHEMA_VERSION,
        encounter=dict(meta, turn_limit=turn_limit, stage_fx=fx, stage_fx_unparsed=fx_unknown,
                       waves=[[d.name for d in w] for w in waves]),
        party=dict(units=names, leader=leader, build=build, builds=[d.build for d in defs], power=power,
                   power_ratio=(pp[0] if pp else None), penalty=(list(pen) if pen else None), penalty_note=pen_note,
                   rekindle=(rk if rk and meta.get('content') == 'op' else 0)),
        breaks=dict(ally=round(breaks[0] / max(1, n_runs), 3), foe=round(breaks[1] / max(1, n_runs), 3)),
        break_skill=dict(name=(o.get('break_skill') or {}).get('name'), uses=round(break_uses / n, 3),
                         dmg=round(break_dmg / n, 3), supported=b.break_skill_enabled,
                         points_gained=round(break_points_gained / n, 3)),
        outcome=dict(
            n_runs=n, n_clear=outcomes['clear'],
            clear_p=round(outcomes['clear'] / n, 4), wipe_p=round(outcomes['wipe'] / n, 4), timeout_p=round(outcomes['timeout'] / n, 4),
            ci95=dict(clear=_wilson(outcomes['clear'], n), wipe=_wilson(outcomes['wipe'], n)),
            ttk_median=round(statistics.median(ttk), 2) if ttk else None,
            ttk_p10_p90=[round(_pct(ttk, 0.1), 2), round(_pct(ttk, 0.9), 2)] if ttk else None,
            ttk_basis='모델 기준 턴(100틱), 클리어한 판만' + ('' if turn_limit else ', 턴 제한 없음(상한 %d턴)' % max_turns)),
        per_unit=per_unit,
        nova_burst=dict(total=sum(sum(slots.values()) for slots in nova_counts.values()),
                        uses=round(sum(sum(slots.values()) for slots in nova_counts.values()) / n, 3),
                        by_unit={nm: dict(slots) for nm, slots in nova_counts.items()}),
        foes={k: dict(dmg=round(sum(v['dmg']) / n), appeared_p=round(len(v['seen']) / n, 4)) for k, v in foe_agg.items()},
        assumptions_used=assumptions_used(mc, opts),
        unsupported=dict(static=static[:300], static_count=len(static), runtime=dict(runtime), runs_affected=runs_affected,
                         depth_runs=depth_runs, critical=crit_lines[:50], gate_ok=not crit_lines),
        runtime_ms_per_run=round(elapsed * 1000 / max(1, n), 2),
        seed=seed,
    )
    if timeline is not None:
        res['timeline'] = timeline
    if per_run is not None:
        res['runs'] = per_run
        res['run_offset'] = offset
    return res


__all__ = ['simulate', 'EventLimitError', 'SCHEMA_VERSION']
