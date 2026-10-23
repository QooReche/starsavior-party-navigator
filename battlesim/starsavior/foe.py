# -*- coding: utf-8 -*-
"""적 데이터 로더(P3 확률 엔진용): rawdata/foe.js(window.__SSD.foe)를 직접 읽어 스테이지 적의 스탯·스킬·패시브·면역을 만든다.

웹용 data/foe_stages.json 은 건드리지 않는다(스킬을 넣으면 웹 용량이 커짐). 스탯 공식은 tools/build_foe.py 의 stats() 와 같다
(tests/p3_test.py 가 foe_stages.json 값과 일치하는지 확인).
스킬: sl(기본기/특수기/궁극기/패시브), tg, dm('공격력×N%'), all(전체), cd(쿨타임), ab(강인도 파괴), ef(구원자와 같은 문법의 효과 줄)."""
import json
import os
import re
from collections import defaultdict

from .data import SRC
from .parser import Line, Skill

SKEY = ['hp', 'atk', 'def', 'spd', 'crit', 'critdmg', 'hit', 'evade', 'abs_evade', 'tough']
SK_NST = ['NST_HP', 'NST_ATK', 'NST_DEF', 'NST_TURN_SPEED', 'NST_RATE_CRITICAL', 'NST_RATE_CRITICAL_DAMAGE',
          'NST_RATE_EFFECT_HIT', 'NST_RATE_EFFECT_EVADE', 'NST_RATE_DEFINITE_EFFECT_EVADE', 'NST_SUPER_ARMOR']
RATE = {'NST_NV_RATE_HP': 0, 'NST_NV_RATE_ATK': 1, 'NST_NV_RATE_DEF': 2, 'NST_NV_RATE_TURN_SPEED': 3}
ROLE_EN = {'스트라이커': 'striker', '캐스터': 'caster', '어쌔신': 'assassin', '레인저': 'ranger', '디펜더': 'defender', '서포터': 'supporter'}

_FOE = None
_SPAWN = {}


def spawn_flags(src=SRC):
    """data/foe_spawn.json(tools/build_foe_spawn.py) -> {'콘텐츠|탭|스테이지': ['웨이브별 칸 표시', ...]}. 없으면 빈 dict"""
    if src not in _SPAWN:
        p = os.path.join(src, 'data', 'foe_spawn.json')
        _SPAWN[src] = json.load(open(p, encoding='utf-8')).get('stages', {}) if os.path.exists(p) else {}
    return _SPAWN[src]


_AUTO = {}


def foe_auto(src=SRC):
    """data/foe_auto.json(tools/build_foe_auto.py) -> {'foe:유닛[:변형]': {skills, lines}}. 없으면 빈 dict"""
    if src not in _AUTO:
        p = os.path.join(src, 'data', 'foe_auto.json')
        _AUTO[src] = {}
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                _AUTO[src] = json.load(f).get('units', {})
    return _AUTO[src]


_REACT = {}


def foe_react(src=SRC):
    """data/foe_react.json(tools/build_foe_react.py) -> {'foe:유닛[:변형]': {칸: 규칙}}. 없으면 빈 dict"""
    if src not in _REACT:
        p = os.path.join(src, 'data', 'foe_react.json')
        _REACT[src] = {}
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                _REACT[src] = json.load(f).get('units', {})
    return _REACT[src]


_SUDDEN = {}


def sudden_death(src=SRC):
    """data/sudden_death.json(tools/build_sudden_death.py) -> {'groups': {그룹: 단계표}, 'stages': {'콘텐츠|탭|스테이지': 그룹}}. 없으면 빈 표"""
    if src not in _SUDDEN:
        p = os.path.join(src, 'data', 'sudden_death.json')
        _SUDDEN[src] = {'groups': {}, 'stages': {}}
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                d = json.load(f)
            _SUDDEN[src] = {'groups': d.get('groups', {}), 'stages': d.get('stages', {})}
    return _SUDDEN[src]


def load_foe(src=SRC):
    """foe.js 원본(dict: g/u/s/ak/x/star). 한 번만 읽는다."""
    global _FOE
    if _FOE is None or _FOE[0] != src:
        with open(os.path.join(src, 'rawdata', 'foe.js'), encoding='utf-8') as f:
            s = f.read()
        m = re.search(r'__SSD\.foe=', s)
        d, _ = json.JSONDecoder().raw_decode(s[m.end():])
        _FOE = (src, d)
    return _FOE[1]


def foe_stats(raw, u, x, st):
    """tools/build_foe.py stats() 와 같은 공식: b + gw x (L-1), 변형 x.a 의 % 보정은 hp/atk/def/spd 만 곱하고 정수 보정은 더함."""
    L = (x and x.get('lv')) or st.get('lv') or 1
    b = list(u['b'])
    for i in range(3):
        b[i] += u['gw'][i] * (L - 1)
    mul = [1, 1, 1, 1]
    for a in (x or {}).get('a', []):
        k = raw['ak'][a[0]][1]
        v = a[1]
        if k in RATE:
            mul[RATE[k]] += v / 10000
        elif k in SK_NST:
            b[SK_NST.index(k)] += v
    for i in range(4):
        b[i] = int(b[i] * mul[i] + 1e-9)
    return dict(zip(SKEY, b)), L


def _gloss_props(xs):
    """상태 효과 설명 'x' 문자열('공격력% -30% / 2턴') -> (dur, props)"""
    dur, props = None, {}
    for part in (xs or '').split('/'):
        p = part.strip()
        m = re.match(r'^(\d+)턴$', p)
        if m:
            dur = int(m.group(1))
            continue
        for q in p.split(','):
            mm = re.match(r'^(.+?)\s+([+-]?\d+(?:\.\d+)?)%?$', q.strip())
            if mm:
                props[mm.group(1).strip()] = float(mm.group(2))
    return dur, props


_GLOSS = {}


def gloss(raw=None):
    """상태 효과 이름 -> dict(kind 강화/약화, props, dur). 적 스킬 gl 사전 + 데이터북 dict.eff 의 사용 예. 무작위 효과(〈데드 스핀〉: [...] 중 1개) 해석용"""
    raw = load_foe() if raw is None else raw
    key = id(raw)
    if key not in _GLOSS:
        g = {}
        for s in raw['s']:
            for e in s.get('gl') or []:
                if e.get('n') and e['n'] not in g:
                    dur, props = _gloss_props(e.get('x'))
                    g[e['n']] = dict(kind=e.get('k'), props=props, dur=dur)
        _GLOSS[key] = (raw, g)  # 원본도 보유하여 id 재사용을 막음
    return _GLOSS[key][1]


class FoeDef:
    """적 1체 정의 — 구원자 UnitDef 와 같은 모양(stats/skills/lines/passive/nb/role/element)이라 같은 시전 경로를 탄다.
    stats 단위: hp/atk/def/spd 정수, cr/cd/eh/er/der 1/10000(구원자와 같음), sa = 강인도."""
    is_foe = True

    def __init__(self, raw, ui, xi=None, st=None, stats_override=None):
        u = raw['u'][ui]
        x = raw['x'][xi] if xi is not None else None
        st = st or {}
        self.ui, self.xi = ui, xi
        self.key = 'foe:%d' % ui + (':%d' % xi if xi is not None else '')
        self.name = u['n']
        self.id, self.variant = ui, '적'
        self.role = u['r']
        self.element = (x and x.get('el')) or u['el']
        self.grade = '보스' if ((x and x.get('b')) or u['g'] == '보스') else ('정예' if ((x and x.get('e')) or u['g'] == '정예') else '일반')
        self.boss = self.grade == '보스'
        self.attack_kind = u['k']
        s, L = foe_stats(raw, u, x, st)
        self.level = L
        self.stats = dict(hp=s['hp'], atk=s['atk'], **{'def': s['def']}, spd=s['spd'], cr=s['crit'], cd=s['critdmg'],
                          eh=s['hit'], er=s['evade'], der=s['abs_evade'], sa=s['tough'])
        if stats_override:
            self.stats.update(stats_override)
        self.immune = set(i['n'] for i in u.get('im', []))
        self.skills, self.trigger_skills, self.lines, self.unmodeled = {}, {}, [], []
        self.desc = {}          # 스킬 칸 -> 설명문(자동 지정 대상 규칙을 읽을 때, mc.auto_rule)
        self.passive = defaultdict(float)
        self.nb = {}
        self.manual = None
        self.gear_atkp = 0.0
        for si in u['sk']:
            sd = raw['s'][si]
            slot = sd['sl']
            self.desc[slot] = (self.desc.get(slot, '') + ' ' + (sd.get('d1') or '')).strip()
            dm = sd.get('dm') or ''
            mm = re.match(r'^공격력×([\d.]+)%$', dm)
            cf = [round(float(mm.group(1)) * 100), 0, 0, 0] if mm else [0, 0, 0, 0]
            sk = Skill(dict(sl=slot, n=sd['n'], ty=sd['ty'], tg=sd['tg'], act='공격' if mm else '비공격', cf=cf,
                            all=sd.get('all'), cd=sd.get('cd'), nv=0))
            sk.ab = sd.get('ab') or 0
            src = 'passive' if slot == '패시브' else ('trigger' if sd['ty'] == '트리거' else 'active')
            if src == 'active':
                self.skills[slot] = sk
            elif src == 'trigger':
                self.trigger_skills[slot] = sk
            if dm and not mm:
                self.unmodeled.append('적 피해 계수 형식 미해석: %s' % dm)
            for raw_line in sd.get('ef') or []:
                self.lines.append(Line(raw_line, slot, src))
        self.spd_base = self.stats['spd']
        # 적 반응(트리거) 스킬 발동 조건(mc.foe_react): 칸 -> {timing, conds, target}
        react_data = foe_react().get(self.key) or {}
        self.react = {}
        for slot, tsk in self.trigger_skills.items():
            if slot in react_data:
                self.react[slot] = react_data[slot]
            else:
                self.unmodeled.append('적 트리거 스킬 미반영: %s' % tsk.name)
        # 게임 자동 대상 규칙(mc.foe_auto): 스킬 칸 -> 규칙 행, (칸, 효과 줄 원문) -> 효과 줄 자동 대상. 같은 원문에 다른 규칙이면 버림
        rules = foe_auto().get(self.key) or {}
        self.auto = rules.get('skills', {})
        self.auto_lines, clash = {}, set()
        for k, spec in rules.get('lines', {}).items():
            si, li = (int(x) for x in k.split(':'))
            sd = raw['s'][si]
            key = (sd['sl'], (sd.get('ef') or [])[li])
            if key in self.auto_lines and self.auto_lines[key] != spec:
                clash.add(key)
            self.auto_lines[key] = spec
        for key in clash:
            del self.auto_lines[key]


def find_raw_stage(content, tab, name, src=SRC):
    """(콘텐츠 key, 탭 이름, 스테이지 이름) -> foe.js 의 스테이지 원본 dict"""
    raw = load_foe(src)
    for g in raw['g']:
        if g['k'] != content:
            continue
        for t in g['tabs']:
            if t['t'] != tab:
                continue
            for s in t['s']:
                if s['n'] == name:
                    return s
    raise KeyError((content, tab, name))


def stage_waves(content, tab, name, src=SRC):
    """스테이지 -> (스테이지 원본, 웨이브 목록[ [FoeDef, ...], ... ]). 웨이브 안 순서 = 원본 순서(배치 칸)."""
    raw = load_foe(src)
    st = find_raw_stage(content, tab, name, src)
    flags = spawn_flags(src).get('%s|%s|%s' % (content, tab, name))
    waves = []
    for wi, w in enumerate(st['w']):
        row = []
        for pi, e in enumerate(w):
            ui, xi = e[0], (e[1] if len(e) > 1 else None)
            d = FoeDef(raw, ui, xi, st)
            # 배치의 시작 쿨 표시(A·S·H·B·N). 없으면 None -> 엔진이 등급 규칙으로 대신함(mc.enemy_spawn)
            d.spawn = flags[wi][pi] if flags and wi < len(flags) and pi < len(flags[wi]) else None
            row.append(d)
        waves.append(row)
    return st, waves


# 스테이지 효과(fx) 문장 -> 적 능력치 보정(가정: fx 는 그 스테이지의 적에게 적용). 모르는 문장은 미지원 목록에 남긴다.
FX_RULES = [
    (r'^방어력이 (\d+)% 증가합니다\.$', '방어력%'),
    (r'^공격력이 (\d+)% 증가합니다\.$', '공격력%'),
    (r'^생명력이 (\d+)% 증가합니다\.$', '생명력%'),
    (r'^속도가 (\d+)% 증가합니다\.$', '속도%'),
    (r'^치명타 확률이 (\d+)% 증가합니다\.$', '치명타 확률'),
    (r'^치명타 피해가 (\d+)% 증가합니다\.$', '치명타 피해'),
    (r'^효과 저항이 (\d+)% 증가합니다\.$', '효과 저항'),
    (r'^효과 적중이 (\d+)% 증가합니다\.$', '효과 적중'),
    (r'^받는 피해량이 (\d+)% 감소합니다\.$', '받는 피해 감소'),
    (r'^단일 공격으로 주는 피해량이 (\d+)% 증가합니다\.$', '단일 대상 피해 증가'),
    (r'^전체 공격으로 주는 피해량이 (\d+)% 증가합니다\.$', '전체 대상 피해 증가'),
]


def parse_fx(texts):
    """-> (props{이름: 값(%)}, 미해석 문장 목록)"""
    props, unknown = {}, []
    for t in texts or []:
        for pat, key in FX_RULES:
            m = re.match(pat, t.strip())
            if m:
                props[key] = props.get(key, 0.0) + float(m.group(1))
                break
        else:
            unknown.append(t)
    return props, unknown
