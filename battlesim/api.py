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
  선택: "turn_limit"(스테이지 lt 를 덮어씀, 격전 의뢰 기본 규칙에서는 무시), "stage_fx"(문장 목록, 스테이지 fx 를 덮어씀),
       "max_turns"(모델 턴 안전 상한, 기본 50·격전 의뢰 200; 도달 시 전멸이 아닌 timeout 미결)
options
  {"seed": 1, "n_runs": 100, "rules_override": {mc·opts 키: 값}, "nova_policy": "auto"|"manual"|"heal", "timeline": false,
   "enemy_lines": true, "run_offset": 0, "per_run": false, "formula_override": {"COOP_CAP": 1.0}, "rekindle": 0,
   "break_skill": {"name": "큐브 과부하", "level": 5}}
  break_skill = 생략/None 이면 미장착. 큐브 과부하·특이점 관측·스타피어서·차원 강습·행성 정화 지원(레벨 1~10 = 계수 가산, mc.break_skill_level), 다른 이름은 unsupported.runtime 에 기록.
  rekindle = 작전(op·oph) 재점화 단계 0~5: 피해 증가·감소 항에 +x, x = REKINDLE[단계](rekindle_apply=multiply면 옛 별도 곱)
       (26610546 클라·표 확인: docs/rekindle_1112.md. 전투력 보정은 별도 배율로 유지)
  run_offset = 판 번호 시작값(판 r 의 난수 = seed*1000003 + run_offset + r; timeline 은 첫 판 = run_offset 번 판)
  per_run = true 면 result.runs = [[결과, 처치 턴 또는 null], ...](판 순서)
  raw_runs = true 면 result.raw_runs = [[결과, 처치 턴(반올림 전) 또는 null, 전체 행동 수 또는 null, 적 진척도(반올림 전)], ...](판 순서).
       나눠 돌린 판을 합쳐 «처음부터 한 번에 돌린 것»과 같은 요약을 내는 재료(battlesim/web.py merge_summary)
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
import json
from collections import OrderedDict, defaultdict

from . import rules as _rules
from .mc import Battle, EventLimitError, support_report
from .rules import DEFAULT_OPTS, MC_NOTE_KEYS, MC_OPTS, MC_RULES, RULES
from .starsavior.data import _find_key, get_db
from .starsavior.foe import FoeDef, load_foe, parse_fx, stage_waves, sudden_death, battle_end, stage_fx_cond
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
        self.react = {}


# 능력치 화면에 이미 들어 있는 상시 % (parser._perm_apply) — 입력 능력치 -> 뺄 passive 키
FINAL_PASSIVE_KEYS = {'atk': ('atkp',), 'hp': ('hpp',), 'def': ('defp',), 'spd': ('spdp', 'spdf'), 'cr': ('cr',), 'cd': ('cd',), 'eh': ('eh',)}


class _LRU:
    """크기 제한 LRU. 키는 호출 입력(구원자 설정·인카운터 설정)이라 시전마다 새로 생기지 않지만, 입력이 계속 달라져도 maxsize 를 넘지 못한다."""

    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.d = OrderedDict()

    def get(self, k):
        v = self.d.get(k)
        if v is not None:
            self.d.move_to_end(k)
        return v

    def put(self, k, v):
        self.d[k] = v
        self.d.move_to_end(k)
        while len(self.d) > self.maxsize:
            self.d.popitem(last=False)

    def clear(self):
        self.d.clear()

    def __len__(self):
        return len(self.d)


# 구원자 정의(파티 한 칸) 캐시: 코스모 전수 탐색은 같은 40명을 수만 번 정규화한다. 정의는 전투에서 읽기 전용(한 simulate 의 n_runs 판이 이미 공유)이라 호출 간 공유해도 결과가 같다.
UNIT_CACHE_MAX = 256
ENC_CACHE_MAX = 64
_UNIT_CACHE = _LRU(UNIT_CACHE_MAX)
_ENC_CACHE = _LRU(ENC_CACHE_MAX)


def clear_engine_caches():
    _UNIT_CACHE.clear()
    _ENC_CACHE.clear()


def _cache_on():
    from . import mc as _mc
    return _mc.ENGINE_CACHE


def _unit_key(u, db, mode, build, use_combat):
    """한 칸의 정의를 정하는 입력 전부(칸 번호·리더는 정의에 영향 없음). JSON 으로 못 만들면 None(캐시 안 함)."""
    try:
        return (id(db), json.dumps(u, sort_keys=True, ensure_ascii=False), mode, build, bool(use_combat))
    except (TypeError, ValueError):
        return None


def _norm_party(party_spec, db, mode, build=None, mc=None):
    if isinstance(party_spec, dict):
        units, leader = party_spec.get('units', []), party_spec.get('leader')
    else:
        units, leader = list(party_spec), None
    if not _cache_on():
        return _norm_party_raw(party_spec, db, mode, build, mc)
    use_combat = (mc or MC_OPTS).get('myinfo_combat', True)
    defs = []
    for u in units:
        uu = dict(key=u) if isinstance(u, str) else u
        k = _unit_key(uu, db, mode, build, use_combat)
        if k is not None:
            k += (bool((mc or MC_OPTS).get('myinfo_potential_coverage', True)),)
        hit = _UNIT_CACHE.get(k) if k is not None else None
        if hit is not None and hit[0] is db and not any(hit[1] is x for x in defs):     # 같은 파티에 같은 구원자가 두 번이면 객체를 나눈다
            defs.append(hit[1])
            continue
        d = _norm_party_raw({'units': [u], 'leader': None}, db, mode, build, mc)[0][0]
        if k is not None and hit is None:
            _UNIT_CACHE.put(k, (db, d))
        defs.append(d)
    return defs, leader


def _norm_party_raw(party_spec, db, mode, build=None, mc=None):
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
            apply_potentials(d, db, combat, (mc or MC_OPTS).get('myinfo_potential_coverage', True))
        defs.append(d)
    return defs, leader


def _norm_encounter(enc):
    """-> (waves[[def]], turn_limit, fx_props, fx_unknown, stage_meta). 코스모·길방 시즌 전투만 입력(JSON)별로 캐시(보스·난이도·세트 조합뿐이라 키가 적다)."""
    if not _cache_on() or not isinstance(enc, dict) or not ('cosmo_raid' in enc or 'guild' in enc):
        return _norm_encounter_raw(enc)
    try:
        k = json.dumps(enc, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return _norm_encounter_raw(enc)
    hit = _ENC_CACHE.get(k)
    if hit is None:
        hit = _norm_encounter_raw(enc)
        _ENC_CACHE.put(k, hit)
    waves, turn_limit, fx, unknown, meta = hit
    return [list(w) for w in waves], turn_limit, (dict(fx) if isinstance(fx, dict) else fx), unknown, dict(meta)


def _norm_encounter_raw(enc):
    meta = {}
    turn_limit = enc.get('turn_limit')
    fx_texts = enc.get('stage_fx')
    if 'guild' in enc:
        # 길드 방어전 EX(BFB): {"guild": {"level": 0~12(별의 도전), "sets": [소멸, 불멸, 쇠락, 허무](0~3)}} — starsavior/guild_bfb.py
        from .starsavior.guild_bfb import build_waves
        g = enc['guild'] or {}
        waves, meta = build_waves(int(g.get('level', 0)), g.get('sets'), support=g.get('support'))
        if turn_limit is None:
            turn_limit = meta['turn_limit']
        fx, unknown = parse_fx(fx_texts or [])
        return waves, turn_limit, fx, unknown, meta
    if 'cosmo_raid' in enc:
        # 코스모 게이트 시즌 전투: {"cosmo_raid": {"boss": "벨그라스|티리아|카넬리아"(또는 belgras|tyria|carnelia), "step": 1~3, "level": 0~18(Step 3 만)}} — starsavior/cosmo_raid.py
        from .starsavior.cosmo_raid import build_waves as cosmo_waves
        c = enc['cosmo_raid'] or {}
        waves, meta = cosmo_waves(c.get('boss', '벨그라스'), int(c.get('step', 3)), int(c.get('level', 0)))
        if turn_limit is None:
            turn_limit = meta['turn_limit']
        fx, unknown = parse_fx(fx_texts or [])
        return waves, turn_limit, fx, unknown, meta
    if 'stage' in enc:
        s = enc['stage']
        if isinstance(s, str):
            content, tab, name = s.split('/', 2)
        else:
            content, tab, name = s['content'], s['tab'], s['name']
        st, waves = stage_waves(content, tab, name)
        meta = dict(content=content, tab=tab, name=name, level=st.get('lv'), recommended_power=st.get('bp'),
                    wave_count=len(waves), fixed_player=st.get('fix'),
                    battle_mode='boss_kill' if '%s|%s|%s' % (content, tab, name) in battle_end() else 'all_kill',
                    sudden_death=sudden_death()['stages'].get('%s|%s|%s' % (content, tab, name)))
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
            # note 키는 MC_OPTS 에 없으므로 규칙 기본값으로 채워 출력 목록 유지
            out.append(dict(rule='mc.' + k, value=mc.get(k, v.get('value')), grade=v.get('grade'), note=v.get('note')))
    for k, v in RULES['mc'].get('break_skills', {}).items():
        out.append(dict(rule='mc.break_skills.' + k, value=mc['break_skills'].get(k), grade=v.get('grade'), note=v.get('note')))
    for k in ('coop_trigger', 'coop_single', 'coop_order', 'coop_dead_target', 'nova_policy', 'nova_pool', 'forced_coop_target', 'init_cd_frac'):
        r = RULES['opts'].get(k, {})
        out.append(dict(rule='opts.' + k, value=opts.get(k), grade=r.get('grade'), note=r.get('note')))
    out.append(dict(rule='model.not_modeled', value=None, grade='assumed',
                    note='선제 방어(회피는 evade_model, 반격은 mc.revenge 로 지원), 표에 없는 「피해 제한」 효과(실행 전 검사에서 중요 미지원으로 표시), '
                         '노바 버스트 슬롯 효과(+15% 외), 일반 잠재력(감각·솜씨)·전술 분석·호감도, 시즌 보너스, Lv200 초과 성장, '
                         '대부분의 반응 트리거 스킬(웨딩 카르멘 「수호의 기사」·프로페서M 「악에서 악으로」만 지원), 연쇄 피해의 「턴 끝에 발생」 시점'))
    out.append(dict(rule='model.random_choice', value='uniform', grade='assumed',
                    note='가중치가 명시되지 않은 무작위 효과·무작위 적은 균등 추첨. 핀볼 타임!·특급 배송의 실제 개별 확률은 자료 미기재로 미확인'))
    return out


def cosmo_approx(boss):
    """결과에 싣는 «근사/추정» 목록(docs/cosmo_raid.md 와 같은 항목)"""
    out = ['점수 합산식: 서버 계산이라 추정(남은 턴·생존 항은 클리어일 때만, 배율 사사오입, 달성 점수 배율 미적용)',
           '난이도 레벨 배율: 능력치 x (1 + ScaleFactor/10000) (추정)',
           '시즌 버프: 속성/직업 조건 아군에게 상시 효과 (BCT_* 해석 추정)',
           '전투력 보정(power_penalty)은 기존 코스모 N단계와 같은 권장 전투력으로 적용']
    if boss == 'belgras':
        out += ['벨그라스: 썩은 의지 발생 체크 버프(BOSS_6)는 변화 전 상태로 판정하는 근사',
                '벨그라스: 공허 붕괴 추가 고정 피해를 타격한 아군 각각에게 방어 무시·보호막 적용으로 근사(범위·보호막 적용 미확인)',
                '벨그라스: 기록자·처단자 응집된 생기 재충전은 영양 과잉이 끝난 뒤 다음 시전 종료 때로 근사']
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
    # MC_NOTE_KEYS 는 설명용이라 무시하고 받아줌(외부 호출 호환). 그 밖의 모르는 키는 오류.
    unknown_keys = [k for k in over if k not in MC_OPTS and k not in DEFAULT_OPTS and k not in MC_NOTE_KEYS]
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


REKINDLE = [0.0, 0.03, 0.07, 0.12, 0.18, 0.25]     # 작전 재점화 버프 단계별 (주는 피해 +x, 받는 피해 −x) — 26610546 BUFF_TEMPLET:55578-55937, NST_RATE_DAMAGE_UP/REDUCE


def _ally_stage_fx(encounter_spec, meta, fx):
    """stage_fx_target=allies: 스테이지 효과를 «속성·직업 조건에 맞는 아군»에게 건다(표: A팀 대상, B팀 없음). [(props, 속성|None, 직업|None)]
    조건은 데이터북 문장 순서대로 data/stage_fx.json 에 있다. 문장을 덮어썼거나 조건이 없으면 아군 전체(조건 없음)로 본다."""
    texts = encounter_spec.get('stage_fx')
    key = '%s|%s|%s' % (meta['content'], meta['tab'], meta['name']) if meta.get('name') and meta.get('content') else None
    if texts is None and key:
        from .starsavior.foe import find_raw_stage
        try:
            texts = find_raw_stage(meta['content'], meta['tab'], meta['name']).get('fx') or []
        except KeyError:        # 원본 스테이지 표에 없는 스테이지(코스모 게이트 등)는 스테이지 효과가 없음
            texts = []
    conds = stage_fx_cond().get(key) if (key and encounter_spec.get('stage_fx') is None) else None
    out = []
    for i, t in enumerate(texts or []):
        props, _ = parse_fx([t])
        if not props:
            continue
        adj, role = (conds[i] if conds and len(conds) == len(texts) else (None, None))
        out.append((props, adj, role))
    return out


def _simulate(party_spec, encounter_spec, o, seed, n_runs, mc, opts):
    db = get_db()
    build = o.get('build', 'none')
    defs, leader = _norm_party(party_spec, db, o.get('stat_mode', 'fixed'), build, mc)
    if not defs:
        raise ValueError('party_spec 이 비어 있음')
    if o.get('cosmo_raid') and 'cosmo_raid' not in encounter_spec:
        encounter_spec = dict(encounter_spec, cosmo_raid=o['cosmo_raid'])     # options.cosmo_raid 로도 받음(encounter 가 우선)
    waves, turn_limit, fx, fx_unknown, meta = _norm_encounter(encounter_spec)
    if meta.get('guild') and 'guild_boss' not in (o.get('rules_override') or {}):
        mc = dict(mc, guild_boss='on')     # 길방 전투에서만 BFB 상태 기계를 켠다(명시하면 그 값)
    if meta.get('cosmo_raid') and 'cosmo_raid_boss' not in (o.get('rules_override') or {}):
        mc = dict(mc, cosmo_raid_boss='on')    # 코스모 시즌 전투에서만 난이도 레벨·챌린지·벨그라스 상태 기계를 켠다(명시하면 그 값)
    clash_no_limit = meta.get('content') == 'clash' and mc['clash_no_turn_limit']
    if clash_no_limit:
        # 11/12 사용자 판단: 클라에 격전 의뢰 제한값 주입 경로 없음. 별 미션 턴과 별개.
        turn_limit = None
    max_turns = encounter_spec.get('max_turns', 200 if clash_no_limit else 50)
    if mc['stage_fx_target'] not in ('enemies', 'allies', 'off'):
        raise ValueError('stage_fx_target 은 enemies|allies|off: %r' % mc['stage_fx_target'])
    ally_fx = _ally_stage_fx(encounter_spec, meta, fx) if mc['stage_fx_target'] == 'allies' else None
    sudden = sudden_death()['groups'].get(meta.get('sudden_death')) if meta.get('sudden_death') else None
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
    if mc['rekindle_apply'] not in ('sum', 'multiply'):
        raise ValueError('rekindle_apply 는 sum|multiply: %r' % mc['rekindle_apply'])
    if rk and meta.get('content') in ('op', 'oph'):
        if not 0 < rk < len(REKINDLE):
            raise ValueError('rekindle 은 0~%d: %r' % (len(REKINDLE) - 1, rk))
        x = REKINDLE[rk]
        if mc['rekindle_apply'] == 'multiply':
            a0, e0 = pen or (1.0, 1.0)
            pen = (a0 * (1 + x), e0 * (1 - x))
        else:
            # IsBuff=false·ForceApplyEffect·TurnInfinite·DeadNotDispel: 강화 개수/해제/금지와
            # 독립인 상시 스탯. stage_fx_target=off여도 재점화는 별도로 적용한다.
            # NKM:2371,3885-3892,18864-18897 → mc.Unit.mods → 일반/지속/연쇄 피해.
            ally_fx = list(ally_fx or ()) + [({'피해 증가': x * 100, '피해 감소': x * 100}, None, None)]
    static = support_report(defs + [d for w in waves for d in w])
    names = ['%s#%d' % (d.name, i) for i, d in enumerate(defs)]
    agg = defaultdict(lambda: defaultdict(list))
    foe_agg = defaultdict(lambda: defaultdict(list))
    outcomes = defaultdict(int)
    ttk = []
    ttk_actions = []   # 클리어 판의 전체 행동 수(아군+적) = 게임 결과 화면의 TURN 에 해당(docs/ally_damage_audit.md)
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
    raw_runs = [] if o.get('raw_runs') else None
    raid_runs = [] if meta.get('cosmo_raid') else None     # 판별 점수 재료: 깎은 보스 HP 비율·남은 턴·생존 구원자 수·클리어
    raid_ctl = defaultdict(int)                             # 컨트롤러 경로 횟수 합계(시험이 «경로가 실제로 탔는지» 확인하는 용도)
    prog = []   # 판마다 적 진척도(0~1): 끝낸 웨이브 수 + 현재 웨이브에서 깎은 체력 비율, 웨이브 수로 나눔. 클리어 0% 팀끼리 순위를 가르는 데 쓴다
    via_tot = defaultdict(int)   # 아군 시전 경로별 합계(coop 등), 결과에는 판당 평균
    t0 = time.perf_counter()
    # 런 간 공유 의미 해석 캐시: 같은 def 객체의 normalized_lines 를 runs 전체에서 한 번만 계산한다.
    # 전역·모듈 캐시 없음 — _simulate 호출마다 새로 생성해 호출 간 격리를 보장한다.
    semantic_cache: dict = {}
    for r in range(n_runs):
        rng = random.Random(seed * 1000003 + offset + r)
        b = Battle(defs, waves, rng, opts, mc, leader=leader, fx=fx if mc['stage_fx_target'] == 'enemies' else {}, ally_fx=ally_fx,
                   turn_limit=turn_limit, timeline=bool(o.get('timeline')) and r == 0,
                   enemy_lines=o.get('enemy_lines', True), max_turns=max_turns, pen=pen, break_skill=o.get('break_skill'), rng_streams=bool(o.get('rng_streams')),
                   sudden=sudden, semantic_cache=semantic_cache, mc_overrides=o.get('rules_override') or {},
                   battle_mode=meta.get('battle_mode', 'all_kill'))
        b.run()   # EventLimitError 는 그대로 올린다(정상 결과 금지)
        for (pos, slot), count in b.nova_bursts.items():
            nova_counts[names[pos]][slot] += count
        break_uses += b.break_skill_uses
        break_dmg += b.break_skill_dmg
        break_points_gained += b.break_points_gained
        outcomes[b.result] += 1
        if b.result == 'clear':
            ttk.append(b.clear_t / b.turn_ticks)
            ttk_actions.append(sum(u.actions for u in b.allies) + sum(u.actions for u in b.all_foes))
        prog.append(b.progress())
        if raw_runs is not None:    # 요약(outcome·star_turn·progress)이 쓰는 값 그대로: 아래 ttk·ttk_actions·prog 에 넣은 것과 같은 객체
            raw_runs.append([b.result, ttk[-1] if b.result == 'clear' else None, ttk_actions[-1] if b.result == 'clear' else None, prog[-1]])
        if raid_runs is not None:
            for k, v in getattr(b.gb, 'stats', {}).items():
                raid_ctl[k] += v
            boss_u = getattr(b.gb, 'boss', None)
            frac = 1.0 if b.result == 'clear' else (0.0 if boss_u is None else max(0.0, min(1.0, 1 - max(0.0, boss_u.hp) / boss_u.maxhp)))
            clear = b.result == 'clear'
            raid_runs.append((round(frac, 6), max(0, turn_limit - b.global_turns) if (clear and turn_limit) else 0,
                              sum(1 for u in b.allies if not u.dead), clear, b.global_turns))
        for k, v in getattr(b, 'ally_via', {}).items():
            via_tot[k] += v
        if per_run is not None:
            per_run.append([b.result, round(b.clear_t / b.turn_ticks, 3) if b.result == 'clear' else None])
        tot = sum(u.dmg for u in b.allies) or 1.0
        for i, u in enumerate(b.allies):
            a = agg[names[i]]
            a['dmg'].append(u.dmg)
            a['share'].append(u.dmg / tot)
            a['taken'].append(u.taken)
            a['heal'].append(u.healed)
            a['heal_raw'].append(u.healed_raw)
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
                   rekindle=(rk if rk and meta.get('content') in ('op', 'oph') else 0)),
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
            ttk_actions_median=round(statistics.median(ttk_actions), 1) if ttk_actions else None,
            progress=round(sum(prog) / n, 4),
            ttk_basis='모델 기준 턴(100틱), 클리어한 판만' + ('' if turn_limit else ', 턴 제한 없음(상한 %d턴)' % max_turns)),
        per_unit=per_unit,
        star_turn=({'limit': int(o['star_turns']), 'p': round(sum(1 for a in ttk_actions if a <= int(o['star_turns'])) / n, 4)}
                   if o.get('star_turns') else None),   # N턴 이내 클리어율(미션 BMT_LIMIT_TURN: 전역 행동 수 <= 한도). outcome 밖: 결과 해시 시험이 outcome 전체를 봄
        heal_raw={nm: round(statistics.fmean(agg[nm]['heal_raw'])) for nm in names},   # per_unit 밖(해시 고정 시험이 per_unit 전체를 봄): 게임 통계 «회복»과 같은 집계(초과 회복 포함)
        prog_runs=[round(x, 4) for x in prog],   # 판별 진행도(outcome 밖): 길방 기대 점수는 판마다 점수식에 넣어 평균(평균 진행도를 넣으면 비선형 절단으로 틀림)
        ally_via={k: round(v / n, 3) for k, v in sorted(via_tot.items())},   # outcome 밖: 결과 해시 고정 시험이 outcome 전체를 봄
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
    if raid_runs is not None:
        from .starsavior.cosmo_raid import cosmo_score, load as cosmo_load
        cr = meta['cosmo_raid']
        G = cosmo_load()
        res['cosmo_raid'] = dict(
            cr, damage_frac_runs=[r[0] for r in raid_runs], remain_turns_runs=[r[1] for r in raid_runs],
            survivors_runs=[r[2] for r in raid_runs], clear_runs=[r[3] for r in raid_runs], turns_used_runs=[r[4] for r in raid_runs],
            score_runs=[cosmo_score(G, cr['level'], r[0], r[1], r[2], r[3], cr['boss'], cr['step']) for r in raid_runs],
            score_conf='추정', approx=cosmo_approx(cr['boss']), ctl=dict(raid_ctl))
    if timeline is not None:
        res['timeline'] = timeline
    if per_run is not None:
        res['runs'] = per_run
        res['run_offset'] = offset
    if raw_runs is not None:
        res['raw_runs'] = raw_runs
    return res


__all__ = ['simulate', 'EventLimitError', 'SCHEMA_VERSION']
