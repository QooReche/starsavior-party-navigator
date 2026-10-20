# -*- coding: utf-8 -*-
"""재사용 계약(docs/battlesim_design.md 2절): simulate(party_spec, encounter_spec, options) -> result.

party_spec
  ["professor-m", "gwen", "fei", "amora"]  또는  {"units": [...], "leader": 0}
  유닛 = key/이름 문자열 또는 {"key", "level"(200), "res"(10), "star"(0), "stats_override"{hp,atk,def,spd,cr,cd,eh,er}}
  순서 0·1 = 전열, 2·3 = 후열(인게임 편성 칸). leader = 리더 칸 번호(속도 +10), 없으면 리더 없음.
encounter_spec
  {"stage": {"content": "cosmo", "tab": "길레", "name": "길레 1단계"}}  또는  {"stage": "cosmo/길레/길레 1단계"}
  {"waves": [[적, ...], ...]}  적 = {"foe": u 번호, "variant": x 번호, "stats_override": {...}} 또는 명시
       {"name", "hp", "atk", "def", "spd", "cr", "cd", "eh", "er", "role", "element", "boss",
        "skills": [{"slot": "기본기", "dm": 80, "all": false, "cd": null, "tg": "적 단일"}]}
  선택: "turn_limit"(스테이지 lt 를 덮어씀), "stage_fx"(문장 목록, 스테이지 fx 를 덮어씀), "max_turns"(턴 제한 없을 때 시간 상한, 50)
options
  {"seed": 1, "n_runs": 100, "rules_override": {mc·opts 키: 값}, "nova_policy": "auto"|"manual", "timeline": false,
   "enemy_lines": true}
result
  {schema_version, outcome{clear_p, wipe_p, timeout_p, ci95{...}, n_runs, n_clear, ttk_median, ttk_p10_p90, ttk_basis},
   per_unit{이름#칸: {dmg_share, dmg, dmg_taken, heal, shield, death_p, death_turn_median, first_death_p, actions}},
   foes{...}, timeline?, assumptions_used[], unsupported{static[], runtime{}, critical, gate_ok}, runtime_ms_per_run}"""
import math
import random
import statistics
import time
from collections import defaultdict

from .mc import Battle, EventLimitError, support_report
from .rules import DEFAULT_OPTS, MC_OPTS, MC_RULES, RULES
from .starsavior.data import _find_key, get_db
from .starsavior.foe import FoeDef, load_foe, parse_fx, stage_waves
from .starsavior.parser import Skill, UnitDef

SCHEMA_VERSION = 'p3-1'


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


def _norm_party(party_spec, db, mode):
    if isinstance(party_spec, dict):
        units, leader = party_spec.get('units', []), party_spec.get('leader')
    else:
        units, leader = list(party_spec), None
    defs = []
    for u in units:
        if isinstance(u, str):
            u = dict(key=u)
        key = _find_key(db, u['key'])
        d = UnitDef(db, key, u.get('level', 200), u.get('res', 10), u.get('star', 0), u.get('mode', mode))
        if u.get('stats_override'):
            d.stats.update(u['stats_override'])
            d.spd_base = d.stats['spd']
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
    for k in ('coop_trigger', 'coop_single', 'nova_policy', 'nova_pool', 'forced_coop_target', 'init_cd_frac'):
        r = RULES['opts'].get(k, {})
        out.append(dict(rule='opts.' + k, value=opts.get(k), grade=r.get('grade'), note=r.get('note')))
    out.append(dict(rule='model.not_modeled', value=None, grade='assumed',
                    note='강인도·브레이크·브레이크 스킬, 반격·선제 방어(회피는 evade_model 로 지원), 피해 제한·불사 효과(실행 전 검사에서 중요 미지원으로 표시), 장비·잠재력·여정, 전투력 보정, 시즌 보너스, 변형 스킬, '
                         '대부분의 반응 트리거 스킬(웨딩 카르멘 「수호의 기사」·프로페서M 「악에서 악으로」만 지원), 연쇄 피해의 「턴 끝에 발생」 시점'))
    return out


def simulate(party_spec, encounter_spec, options=None):
    o = dict(options or {})
    seed = int(o.get('seed', 1))
    n_runs = int(o.get('n_runs', 100))
    over = dict(o.get('rules_override') or {})
    if 'nova_policy' in o:
        over['nova_policy'] = o['nova_policy']
    mc = dict(MC_OPTS, **{k: v for k, v in over.items() if k in MC_OPTS})
    opts = dict(DEFAULT_OPTS, **{k: v for k, v in over.items() if k in DEFAULT_OPTS})
    unknown_keys = [k for k in over if k not in MC_OPTS and k not in DEFAULT_OPTS]
    if unknown_keys:
        raise ValueError('모르는 규칙 키: %s' % ', '.join(unknown_keys))
    db = get_db()
    defs, leader = _norm_party(party_spec, db, o.get('stat_mode', 'fixed'))
    if not defs:
        raise ValueError('party_spec 이 비어 있음')
    waves, turn_limit, fx, fx_unknown, meta = _norm_encounter(encounter_spec)
    max_turns = encounter_spec.get('max_turns', 50)
    static = support_report(defs + [d for w in waves for d in w])
    names = ['%s#%d' % (d.name, i) for i, d in enumerate(defs)]
    agg = defaultdict(lambda: defaultdict(list))
    foe_agg = defaultdict(lambda: defaultdict(list))
    outcomes = defaultdict(int)
    ttk = []
    runtime = defaultdict(int)
    runs_affected = 0
    timeline = None
    first = defaultdict(int)
    t0 = time.perf_counter()
    for r in range(n_runs):
        rng = random.Random(seed * 1000003 + r)
        b = Battle(defs, waves, rng, opts, mc, leader=leader, fx=fx if mc['stage_fx_target'] == 'enemies' else {},
                   turn_limit=turn_limit, timeline=bool(o.get('timeline')) and r == 0,
                   enemy_lines=o.get('enemy_lines', True), max_turns=max_turns)
        b.run()   # EventLimitError 는 그대로 올린다(정상 결과 금지)
        outcomes[b.result] += 1
        if b.result == 'clear':
            ttk.append(b.clear_t / b.turn_ticks)
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
            for k, v in b.unsup.items():
                runtime[k] += v
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
        party=dict(units=names, leader=leader),
        outcome=dict(
            n_runs=n, n_clear=outcomes['clear'],
            clear_p=round(outcomes['clear'] / n, 4), wipe_p=round(outcomes['wipe'] / n, 4), timeout_p=round(outcomes['timeout'] / n, 4),
            ci95=dict(clear=_wilson(outcomes['clear'], n), wipe=_wilson(outcomes['wipe'], n)),
            ttk_median=round(statistics.median(ttk), 2) if ttk else None,
            ttk_p10_p90=[round(_pct(ttk, 0.1), 2), round(_pct(ttk, 0.9), 2)] if ttk else None,
            ttk_basis='모델 기준 턴(100틱), 클리어한 판만' + ('' if turn_limit else ', 턴 제한 없음(상한 %d턴)' % max_turns)),
        per_unit=per_unit,
        foes={k: dict(dmg=round(sum(v['dmg']) / n), appeared_p=round(len(v['seen']) / n, 4)) for k, v in foe_agg.items()},
        assumptions_used=assumptions_used(mc, opts),
        unsupported=dict(static=static[:300], static_count=len(static), runtime=dict(runtime), runs_affected=runs_affected,
                         critical=crit_lines[:50], gate_ok=not crit_lines),
        runtime_ms_per_run=round(elapsed * 1000 / max(1, n), 2),
        seed=seed,
    )
    if timeline is not None:
        res['timeline'] = timeline
    return res


__all__ = ['simulate', 'EventLimitError', 'SCHEMA_VERSION']
