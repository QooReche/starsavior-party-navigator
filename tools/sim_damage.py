# -*- coding: utf-8 -*-
"""
sim_damage.py - 스타세이비어 구원자 화력 지표 / 파티 시뮬레이터 (기대값 기반 이벤트 시뮬레이터)

구성
  1) calc_stats()      databook app.js 의 sCalc 와 같은 스탯 공식 (Lv/공명/각인/동기화) + 장비 확장 훅(gear)
  2) UnitDef           databook_main.json 의 스킬(cf/cd/nv/ef 줄)을 파싱해 만든 구원자 정의
  3) Sim               행동 게이지(10,000, 필요 틱=(10000-게이지)/속도) 방식의 이벤트 시뮬레이터. 난수 없이 기대값(확률 가중) 계산
  4) build_index()     구원자별 단일/광역 N턴 기대 피해 + 0~10 정규화 점수 (damage_index.json)
  5) simulate_party()  파티 4명 N턴 총 피해 + 적 총 HP 대비 처치 턴 수
  6) CLI               python -X utf8 -I sim_damage.py {index,party,stage,stats,validate} ...

가정/단순화는 sim_report.md 와 ASSUMPTIONS 상수에 명시. 데이터는 읽기 전용.
"""
import argparse
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict

SRC = os.environ.get('PN_SRC', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))  # 저장소 루트
OUT_DIR = os.path.join(SRC, 'tools', 'raw')  # 큰 중간 산출물(저장소 제외)

BASE_MULT = 1.85            # 피해식 상수 (databook 계산기)
DEF_K = 3000.0              # 방어율 = def/(def+3000) (PvE)
AOE_DIV = 4.0               # 전체 대상 스킬은 /4 (대상 1명당)
TICK_PER_TURN = 100.0       # 속도 100 유닛이 1턴(=1라운드)에 한 번 행동하는 틱 수
INF_HP = 1e15
COOP_CAP = 0.30             # stat.cap.NST_RATE_CROSS_ATTACK = 3000 (협공 확률 상한 30%)

ASSUMPTIONS = {
    'level': 'Lv200 고정, 공명 10단계 (코스모 게이트/플래시 포인트/랭크전 고정 조건). 각인(star)=0 기본, 인자로 0~7 변경.',
    'equipment': '장비/아르카나/잠재력 제외 (gear 훅으로 확장 가능).',
    'skill_level': '모든 스킬 최대 레벨 (ef 줄은 최대 레벨 기준, 쿨타임은 cdm(최대 레벨) 우선).',
    'damage_formula': '기본피해=(공격력x계수+생명력x계수+방어력x계수)x(1+속도/100x계수)x1.85, 전체공격 /4, x(1-방어율), x(1+증가합-감소합+치명확률x치명피해). 난수는 평균(1.0) 사용.',
    'enemy_ref': '지표용 기준 적: 방어력 1400(코스모 2단계 수준), 속도 100, 속성 없음(상성 0), 약화/브레이크 없음, HP 무한.',
    'single': '단일 시나리오 = 적 1체. 단일 스킬은 그 1체, 전체 스킬은 대상 1명당 cf/4 만 들어감.',
    'aoe': '광역 시나리오 = 적 3체(총합 피해). 단일 스킬은 1체만, 전체 스킬은 3체 각각 cf/4.',
    'turn': '1턴 = 속도 100 유닛이 1회 행동하는 기간(100틱). N턴 = N*100틱. 게이지 시작 0, 쿨타임 시작은 만충(cd 턴 후 첫 사용).',
    'ai': '스킬 선택은 궁극기 > 특수기 > 기본기 중 쿨타임이 찬 것 (자동 전투 가정).',
    'buff_duration': 'N턴 버프는 버프 보유자의 행동 N회 동안 유지 (자기가 건 버프는 건 행동 다음 행동부터 카운트).',
    'allies_solo': '개인 지표는 속성 없는 더미 딜러 3명(기본기/특수기/궁극기 순환, 속도 100)과 함께 계산: 아군 공격 트리거를 받되 버프는 주지 않음.',
    'conditions': '조건은 확률 가중(기대값). 스택은 실수 스택. 해석 못 한 조건 키는 0.5 가중(unknown_cond_p) 후 unmodeled 에 기록.',
    'debuff': '디버프 성공률 0.9 가정(효과 적중-저항 판정은 적 저항을 몰라 상수).',
    'not_modeled': '반응(피격/회피/수호) 트리거 스킬, 변형(교체) 스킬, 무작위 효과, 브레이크(강인도), 카운터(+10%), 힐/보호막, 협공(확률 스탯만 단순 반영), 적 공격/피해 감소.',
    'nova': '노바 포스는 구원자 개인 단위로 모아 4개면 다음 스킬 피해 +15% (팀 공용 여부는 미확인 추정).',
}

ELEM_BEATS = {'태양': '별', '별': '달', '달': '태양', '질서': '혼돈', '혼돈': '질서'}
ELEM_LOSES = {'태양': '달', '별': '태양', '달': '별'}   # 질서/혼돈은 서로 유리만 (불리 없음 추정)
FOE_ELEM = {'sun': '태양', 'moon': '달', 'star': '별', 'order': '질서', 'chaos': '혼돈'}
KNOWN_DOT = {'연소': ('atk', 0.20), '출혈': ('atk', 0.25), '빙결': ('atk', 0.15), '중독': ('hp', 0.05)}
DEFAULT_OPTS = dict(
    unknown_cond_p=0.5, debuff_success=0.9, inf_hp_frac=0.6, break_p=0.0, kill_p_inf=0.15,
    no_debuff_p=0.85, nova=True, coop=True, forced_coop=True, init_cd_frac=1.0, enemy_element=None,
    enemy_def=1400.0, enemy_spd=100.0, ref_enemy_count=3,
)

# ------------------------------------------------------------------ 데이터 로딩
class DB:
    def __init__(self, src=SRC):
        self.src = src
        with open(os.path.join(src, 'rawdata', 'databook_main.json'), encoding='utf-8') as f:
            self.main = json.load(f)
        with open(os.path.join(src, 'data', 'synergy_tags.json'), encoding='utf-8') as f:
            tg = json.load(f)
        self.tags = {(s['id'], s['variant']): s for s in tg['saviors']}
        self.units = {}
        for u in self.main['units']:
            t = self.tags.get((u['id'], u['v']))
            key = t['key'] if t else ('%s@%s' % (u['id'], u['v']))
            self.units[key] = u
        self._foe = None

    @property
    def foe(self):
        if self._foe is None:
            with open(os.path.join(self.src, 'data', 'foe_stages.json'), encoding='utf-8') as f:
                self._foe = json.load(f)
        return self._foe

    def find_stage(self, content, tab, name):
        for c in self.foe['contents']:
            if c['key'] != content:
                continue
            for t in c['tabs']:
                if t['tab'] != tab:
                    continue
                for s in t['stages']:
                    if s['name'] == name:
                        return s
        raise KeyError((content, tab, name))


_DB = None
def get_db():
    global _DB
    if _DB is None:
        _DB = DB()
    return _DB

# ------------------------------------------------------------------ 스탯 (app.js sCalc 재현)
STAT_MODES = {
    'normal': (1.0, 1.0),
    'fixed': (1.0, 0.0),     # 플래시 포인트/코스모 게이지: Lv200, 공명10, 200초과분 0
    'rank': (0.1, 0.0),      # 랭크전(PvP): 성장 능력치 10%만
}

def calc_stats(db, u, level=200, res_stage=10, star=0, mode='fixed', gear=None):
    ST = db.main['stat']
    m = ST['units'][str(u['id'])]
    sid = m['sid'] if u['v'] == '기본' else m.get('bsid', m['sid'])
    t = ST['tmpl'][sid]
    b, g = t['base'], t['grow']
    s1, s2 = STAT_MODES[mode]
    L = level
    n1 = min(L, 200) - 1
    n2 = max(0, L - 200)
    J = {'hp': 0, 'atk': 0, 'def': 0}
    if L >= 200:
        for lv, d in ST['sync']['jumps']:
            if lv <= L:
                for k, v in d.items():
                    J[k] = J.get(k, 0) + v
    R = ST['res'].get(str(u['id']), [])
    rn = 0
    for i in range(min(res_stage, len(R))):
        if R[i][0] > L:
            break
        rn += 1
    rf, rp = defaultdict(float), defaultdict(float)
    for ul, sts in R[:rn]:
        for k, v in sts:
            if k.endswith('P'):
                rp[k] += v
            else:
                rf[k] += v
    starP = sum(next((x[1] for x in sts if x[0] == 'atkP'), 0) for _, sts in ST['star'][:star])
    out = {}
    for k in ('hp', 'atk', 'def', 'spd'):
        main = k != 'spd'
        sc1 = s1 * 1.0 if main else 1.0
        sc2 = s2 * 1.0 if main else 1.0
        lv_int = g[k] * n1 if main else 0
        amp_int = (g[k] * n2 + J.get(k, 0)) if main else 0
        v = b[k] + lv_int * sc1 + amp_int * sc2
        v = v + rf.get(k, 0) * sc1 + v * (rp.get(k + 'P', 0) * 1e-4)
        if main:
            v = v + v * starP * 1e-4
        out[k] = max(0, math.floor(v))
    for k in ('cr', 'cd', 'eh', 'er', 'der'):
        v = math.floor(b[k] + rf.get(k, 0))
        cap = ST['cap'].get({'cr': 'NST_RATE_CRITICAL', 'cd': 'NST_RATE_CRITICAL_DAMAGE'}.get(k, ''), 0)
        if cap and v > cap:
            v = cap
        out[k] = max(0, v)
    out['sa'] = b['sa']
    if gear:   # 확장 훅: {'atk':flat,'hp':flat,'def':flat,'spd':flat,'cr':,'cd':}(cr/cd 는 1/10000 단위)
        for k, v in gear.items():
            if k in out:
                out[k] += v
    out['_template'] = sid
    return out

# ------------------------------------------------------------------ 줄(ef) 파싱
NUM = r'[+-]?\d+(?:\.\d+)?'

def split_head(raw):
    m = re.match(r'^\[([^\]]+)\]\s*(.*)$', raw, re.S)
    if not m:
        return None, None, raw, 1.0
    phase, rest = m.group(1), m.group(2)
    cond = None
    hpw = 1.0
    if rest.startswith('('):
        depth = 0
        for i, ch in enumerate(rest):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    inner = rest[1:i].strip()
                    if inner.startswith('조건:'):
                        cond = inner[len('조건:'):].strip()
                        rest = rest[i + 1:].strip()
                    else:
                        hm = re.match(r'^자신 HP (\d+)% (이상|이하)(?:\s*·\s*조건:\s*(.*))?$', inner, re.S)
                        if hm:
                            hpw = 0.8 if hm.group(2) == '이상' else 0.2   # 자신 HP 조건: 대체로 건강하다고 가정(추정)
                            cond = hm.group(3)
                            rest = rest[i + 1:].strip()
                    break
    return phase, cond, rest, hpw


def parse_cond(c):
    if c is None:
        return None, []
    m = re.match(r'^([^\[]*?)\s*(?:\[(.*)\])?\s*$', c, re.S)
    trig = m.group(1).strip()
    params = []
    inner = m.group(2)
    if inner:
        for part in inner.split(';'):
            k, _, v = part.partition(':')
            params.append((k.strip(), v.strip()))
    return trig, params


def parse_props(s):
    """'2턴 / 공격력% +30%, 속도% +20%' -> (dur, {key:val})"""
    dur, props = None, {}
    if s is None:
        return dur, props
    parts = [p.strip() for p in s.split('/')]
    for i, p in enumerate(parts):
        if i == 0:
            m = re.match(r'^(\d+)턴$', p)
            if m:
                dur = int(m.group(1))
                continue
            if p.startswith('지속 무한'):
                dur = math.inf
                continue
        for q in p.split(','):
            q = q.strip()
            m = re.match(r'^(.+?)\s+(' + NUM + r')%?$', q)
            if m:
                props[m.group(1).strip()] = float(m.group(2))
    return dur, props


def parse_flags(s):
    f = {'max': None, 'times': 1, 'judge': False}
    if not s:
        return f
    m = re.search(r'최대 (\d+)중첩', s)
    if m:
        f['max'] = int(m.group(1))
    m = re.search(r'(\d+)회 부여', s)
    if m:
        f['times'] = int(m.group(1))
    f['judge'] = '효과 적중 판정' in s
    return f


def parse_effect(rest):
    """효과 문장 -> dict(kind=...). 해석 못 하면 kind='ignored'"""
    rest = rest.strip()
    m = re.match(r'^자신에게 능력치 보정 (.+?) (' + NUM + r')%?\s*(\{.*\})?$', rest)
    if m:
        return dict(kind='local', stat=m.group(1).strip(), val=float(m.group(2)))
    m = re.match(r'^(.+?)에게 능력치 보정 ', rest)
    if m:
        return dict(kind='ignored', why='타 대상 능력치 보정')
    m = re.match(r'^(.+?)에게 행동 게이지 ([\d.]+)%p (증가|감소)', rest)
    if m:
        v = float(m.group(2)) * (1 if m.group(3) == '증가' else -1)
        return dict(kind='gauge', target=m.group(1), val=v, judge='효과 적중 판정' in rest)
    m = re.match(r'^(.+?)에게 스킬 쿨타임 (\d+)턴 감소', rest)
    if m:
        return dict(kind='cdr', target=m.group(1), val=int(m.group(2)))
    m = re.match(r'^자신에게 (기본기|특수기|궁극기) 추가 발동(?:\s*×(\d+))?', rest)
    if m:
        return dict(kind='extra_cast', slot=m.group(1), times=int(m.group(2) or 1))
    if re.match(r'^자신에게 〈추가 턴〉', rest):
        return dict(kind='extra_turn')
    m = re.match(r'^(.+?)에게 연쇄 피해 = 자신 (공격력|생명력|방어력)×([\d.]+)%', rest)
    if m:
        return dict(kind='chain', target=m.group(1), stat={'공격력': 'atk', '생명력': 'hp', '방어력': 'def'}[m.group(2)],
                    coef=float(m.group(3)) / 100.0)
    m = re.match(r"^(.+?)에게 '([^']+)' 해제", rest)
    if m:
        return dict(kind='remove', target=m.group(1), name=m.group(2))
    m = re.match(r'^(.+?)에게\s*(?:\(대상마다 (\d+)% 판정\)\s*)?(?:(\d+)% 확률로\s*)?〈([^〉]+)〉\s*(?:\(([^)]*)\))?\s*(?:‹([^›]*)›)?\s*(\{[^}]*\})?', rest)
    if m:
        target, p1, p2, name, props, dot, flags = m.groups()
        chance = 1.0
        if p1:
            chance = int(p1) / 100.0
        if p2:
            chance = int(p2) / 100.0
        dur, pr = parse_props(props)
        fl = parse_flags(flags)
        eff = dict(kind='buff', target=target, name=name, chance=chance, dur=dur, props=pr,
                   max=fl['max'], times=fl['times'], judge=fl['judge'] or (props is not None and '효과 적중 판정' in rest))
        if dot:
            dm = re.search(r'턴마다 (공격력|생명력)×([\d.]+)%', dot)
            if dm:
                eff['dot'] = ({'공격력': 'atk', '생명력': 'hp'}[dm.group(1)], float(dm.group(2)) / 100.0)
        if props and re.search(r'약화효과 해제|강화효과 해제', props):
            eff['kind'] = 'ignored'
            eff['why'] = '해제류'
        if name == '추가 턴':
            return dict(kind='extra_turn')
        if re.search(r'보호막 =|회복 =', rest):
            return dict(kind='ignored', why='보호막/회복')
        return eff
    m = re.match(r'^(.+?)에게 회복 =|^(.+?)에게 .*보호막 =', rest)
    if m:
        return dict(kind='ignored', why='회복/보호막')
    if '해제' in rest or '스킬 교체' in rest or '효과 지속 턴' in rest or '무작위' in rest:
        return dict(kind='ignored', why='해제/교체/무작위')
    return dict(kind='ignored', why='미해석')


def trig_kind(phase, trig):
    """줄의 발동 시점 분류"""
    if phase == '상시':
        return 'perm'
    if phase in ('전투 시작 시', '웨이브 시작 시'):
        return 'battle_start'
    if phase == '즉시':
        return 'ignored'
    if trig:
        t = trig
        table = [('내 공격 시', 'own_pre'), ('내 공격 후', 'own_post'), ('내 비공격 스킬 시', 'own_pre'),
                 ('내 비공격 스킬 후', 'own_post'), ('아군 공격 시', 'ally_pre'), ('아군 공격 후', 'ally_post'),
                 ('내 턴 시작 시', 'own_ts'), ('내 턴 종료 시', 'own_te'), ('아군 턴 시작 시', 'ally_ts'),
                 ('적 턴 시작 시', 'enemy_ts')]
        for k, v in table:
            if t.startswith(k):
                return v
        return 'unmodeled'
    if phase == '스킬 사용 시작 시':
        return 'own_pre'
    if phase == '스킬 사용 후':
        return 'own_post'
    if phase == '턴 시작 시':
        return 'own_ts'
    if phase == '턴 종료 시':
        return 'own_te'
    return 'unmodeled'


class Line:
    __slots__ = ('raw', 'slot', 'src_kind', 'phase', 'trig', 'params', 'kind', 'eff', 'bound', 'na', 'hpw')

    def __init__(self, raw, slot, src_kind):
        self.raw, self.slot, self.src_kind = raw, slot, src_kind
        phase, cond, rest, self.hpw = split_head(raw)
        self.phase = phase
        self.trig, self.params = parse_cond(cond)
        self.kind = trig_kind(phase, self.trig)
        self.na = bool(self.trig and '비공격' in self.trig)
        if self.kind == 'perm':
            m = re.match(r'^능력치:\s*(.+?)\s+(' + NUM + r')(%?)$', rest)
            self.eff = dict(kind='perm', stat=m.group(1), val=float(m.group(2))) if m else dict(kind='ignored', why='상시미해석')
        else:
            self.eff = parse_effect(rest)
        self.bound = (src_kind in ('active', 'trigger')) and self.kind in ('own_pre', 'own_post')
        # 데이터가 '소비'를 '부여'로 표기한 줄 보정 (예: 그웬 전기 충격 5회 이상 -> 추가 발동 + 5회 감소)
        if self.eff['kind'] == 'buff' and self.eff['target'].startswith('자신'):
            pd = dict(self.params)
            nm, mn = pd.get('자신이 보유'), pd.get('중첩수 이상')
            if nm and mn and self.eff['name'] == nm and self.eff['times'] == int(float(mn)):
                self.eff['consume'] = True


class Skill:
    def __init__(self, s):
        self.slot = s['sl']
        self.name = s['n']
        self.ty = s['ty']
        self.tg = s['tg']
        self.is_attack = s.get('act') == '공격'
        self.cf = list(s.get('cf') or [0, 0, 0, 0])
        self.all = bool(s.get('all')) or s['tg'] == '적 전체'
        cd = s.get('cdm') if s.get('cdm') is not None else s.get('cd')
        self.cd = cd
        self.nv = s.get('nv') or 0
        self.dm = s.get('dm')
        self.raw = s


def _perm_apply(stats, passive, eff):
    st, v = eff['stat'], eff['val']
    if st == '공격력%':
        passive['atkp'] += v / 100
    elif st == '생명력%':
        passive['hpp'] += v / 100
    elif st == '방어력%':
        passive['defp'] += v / 100
    elif st == '치명타 확률':
        passive['cr'] += v / 100
    elif st == '치명타 피해':
        passive['cd'] += v / 100
    elif st == '속도%':
        passive['spdp'] += v / 100
    elif st == '속도':
        passive['spdf'] += v
    else:
        return False
    return True


class UnitDef:
    def __init__(self, db, key, level=200, res_stage=10, star=0, mode='fixed', gear=None):
        self.key = key
        u = db.units[key]
        self.u = u
        self.id, self.variant, self.name = u['id'], u['v'], u['n']
        self.role, self.element, self.grade, self.attack_kind = u['r'], u['a'], u['g'], u['k']
        self.stats = calc_stats(db, u, level, res_stage, star, mode, gear)
        self.skills = {}          # slot -> Skill (활성)
        self.trigger_skills = {}
        self.lines = []
        self.passive = defaultdict(float)
        self.unmodeled = []
        self.nb = u.get('nb') or {}
        self.manual = None
        for s in u['sk']:
            slot = s['sl']
            if slot.startswith('변형'):
                self.unmodeled.append('변형(교체) 스킬 미반영: %s' % s['n'])
                continue
            sk = Skill(s)
            if slot == '고유 패시브':
                src = 'passive'
            elif s['ty'] == '트리거':
                src = 'trigger'
                self.trigger_skills[slot] = sk
                if s['tg'].startswith('반응'):
                    self.unmodeled.append('반응 트리거 스킬 미반영: %s' % s['n'])
            else:
                src = 'active'
                self.skills[slot] = sk
            for raw in s['ef']:
                ln = Line(raw, slot, src)
                self.lines.append(ln)
                if ln.kind == 'perm':
                    if ln.eff['kind'] == 'perm':
                        _perm_apply(self.stats, self.passive, ln.eff)
                elif ln.kind == 'unmodeled':
                    self.unmodeled.append('조건 미해석 줄: ' + raw[:70])
                elif ln.eff['kind'] == 'ignored' and ln.eff.get('why') == '미해석':
                    self.unmodeled.append('효과 미해석 줄: ' + raw[:70])
        if self.id == 1039 and '특수기' in self.trigger_skills:
            self.manual = 'profM'
        self.spd_base = self.stats['spd']
        # 장비 확장용
        self.gear_atkp = 0.0

# ------------------------------------------------------------------ 런타임 개체
class Buff:
    __slots__ = ('name', 'stacks', 'maxs', 'dur', 'props', 'fresh')

    def __init__(self, name, props, maxs, dur):
        self.name, self.props, self.maxs, self.dur = name, props, maxs, dur
        self.stacks = 0.0
        self.fresh = False


def _map_prop(k):
    if k == '공격력%': return ('atkp', None)
    if k == '속도%': return ('spdp', None)
    if k == '속도': return ('spdf', None)
    if k == '치명타 확률': return ('cr', None)
    if k == '치명타 피해': return ('cd', None)
    if k == '피해 증가': return ('inc', None)
    if k == '방어 관통': return ('pen', None)
    if k == '방어력%': return ('defp', None)
    if k == '생명력%': return ('hpp', None)
    if k == '협공 확률': return ('coop', None)
    m = re.match(r'^vs (.+) 속성 피해 증가$', k)
    if m: return ('inc_vs', m.group(1))
    m = re.match(r'^(기본기|특수기|궁극기) 피해 증가$', k)
    if m: return ('inc_slot', m.group(1))
    return (None, None)


class Actor:
    """아군 런타임 상태"""
    def __init__(self, d, idx, opts):
        self.d = d
        self.idx = idx
        self.name = d.name
        self.element = d.element
        self.is_ally = True
        self.gauge = 0.0
        self.buffs = {}
        self.cd = {}
        self.nova = 0.0
        self.extra_turn = False
        self.dmg = 0.0
        self.hits = 0.0
        self.dmg_src = defaultdict(float)
        self.cast_count = defaultdict(float)
        self.actions = 0
        self.acting = False
        for slot, sk in d.skills.items():
            if sk.cd:
                self.cd[slot] = sk.cd * opts['init_cd_frac']
            else:
                self.cd[slot] = 0
        self.manual_acted = 0

    # ---- 버프 합산
    def mods(self):
        m = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0, coop=0.0,
                 inc_vs={}, inc_slot={})
        for b in self.buffs.values():
            for k, v in b.props.items():
                key, sub = _map_prop(k)
                if key is None:
                    continue
                val = v / 100.0 * b.stacks if key not in ('spdf',) else v * b.stacks
                if key == 'inc_vs':
                    m['inc_vs'][sub] = m['inc_vs'].get(sub, 0.0) + val
                elif key == 'inc_slot':
                    m['inc_slot'][sub] = m['inc_slot'].get(sub, 0.0) + val
                else:
                    m[key] += val
        return m

    def stack(self, name):
        b = self.buffs.get(name)
        return b.stacks if b else 0.0

    def spd(self):
        m = self.mods()
        p = self.d.passive
        return self.d.spd_base * (1 + m['spdp'] + p['spdp']) + m['spdf'] + p['spdf']


class Enemy:
    def __init__(self, spec, idx):
        self.idx = idx
        self.name = spec.get('name', 'enemy')
        self.maxhp = float(spec.get('hp', INF_HP))
        self.hp = self.maxhp
        self.def_ = float(spec.get('def', 1400))
        self.spd = float(spec.get('spd', 100))
        self.element = spec.get('element')
        self.boss = spec.get('boss', False)
        self.is_ally = False
        self.gauge = 0.0
        self.deb = {}      # name -> dict(stacks,dur,defp,spdp,dot)
        self.dead = False

    def defp(self):
        return sum(d.get('defp', 0.0) * d['stacks'] for d in self.deb.values())

    def def_eff(self):
        return max(0.0, self.def_ * (1 + self.defp()))

    def spd_eff(self):
        s = sum(d.get('spdp', 0.0) * d['stacks'] for d in self.deb.values())
        return max(1.0, self.spd * (1 + s))


class Ctx:
    __slots__ = ('owner', 'src', 'skill', 'extra', 'w', 'inc', 'atkp', 'cr', 'cd', 'pen', 'crit_p', 'kill', 'target',
                 'is_ally_event', 'nb_burst')

    def __init__(self, owner, src, skill, extra, w):
        self.owner, self.src, self.skill, self.extra, self.w = owner, src, skill, extra, w
        self.inc = self.atkp = self.cr = self.cd = self.pen = 0.0
        self.crit_p = 0.0
        self.kill = 0.0
        self.target = None
        self.is_ally_event = owner is not src
        self.nb_burst = False


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

# ------------------------------------------------------------------ 시뮬레이터
class Sim:
    def __init__(self, defs, enemies, turns=10, opts=None, dummies=0):
        self.opts = dict(DEFAULT_OPTS)
        if opts:
            self.opts.update(opts)
        self.party = [Actor(d, i, self.opts) for i, d in enumerate(defs)]
        self.enemies = [Enemy(e, i) for i, e in enumerate(enemies)]
        self.turns = turns
        self.horizon = turns * TICK_PER_TURN
        self.t = 0.0
        self.unmodeled = defaultdict(int)
        self.depth = 0
        self.log = []
        self.kill_time = None
        self.applied_buff_names = set()
        self.dummy_cycle = ['기본기', '특수기', '기본기', '기본기', '궁극기']
        self.dummy_i = defaultdict(int)

    # ---------- 유틸
    def alive(self):
        return [e for e in self.enemies if not e.dead]

    def primary(self):
        a = self.alive()
        return a[0] if a else None

    def hp_frac(self, e):
        if e is None:
            return 1.0
        if e.maxhp >= INF_HP / 2:
            return self.opts['inf_hp_frac']
        return e.hp / e.maxhp

    # ---------- 시작
    def start(self):
        for a in self.party:
            for ln in a.d.lines:
                if ln.kind == 'battle_start':
                    ctx = Ctx(a, a, None, False, 1.0)
                    self.apply_line(a, ln, ctx, 1.0)

    def run(self):
        self.start()
        actors = self.party + self.enemies
        guard = 0
        while guard < 5000:
            guard += 1
            living = [x for x in actors if getattr(x, 'dead', False) is False]
            best, bt = None, None
            for x in living:
                spd = x.spd() if x.is_ally else x.spd_eff()
                need = 0.0 if x.gauge >= 10000 else (10000 - x.gauge) / max(spd, 1e-6)
                if bt is None or need < bt - 1e-9:
                    best, bt = x, need
            if best is None or self.t + bt > self.horizon + 1e-9:
                break
            for x in living:
                spd = x.spd() if x.is_ally else x.spd_eff()
                x.gauge = min(10000.0, x.gauge + spd * bt)
            self.t += bt
            if best.is_ally:
                self.act_ally(best)
            else:
                self.act_enemy(best)
            if not self.alive():
                self.kill_time = self.t
                break
        return self

    # ---------- 적 행동
    def act_enemy(self, e):
        e.gauge = 0.0
        # DoT
        for name, d in list(e.deb.items()):
            if d.get('dot') and d.get('src') is not None:
                dmg = d['mult'] * d['stacks'] * (1 - self.dr(e, 0.0))
                self.hurt(e, dmg, d['src'], 'dot', hit=0.0)
        if e.dead:
            return
        # 적 턴 시작 트리거
        for a in self.party:
            for ln in a.d.lines:
                if ln.kind == 'enemy_ts':
                    self.apply_line(a, ln, Ctx(a, a, None, False, 1.0), 1.0)
        # 디버프 지속 감소
        for name in list(e.deb):
            d = e.deb[name]
            if d['dur'] != math.inf:
                d['dur'] -= 1
                if d['dur'] <= 0:
                    del e.deb[name]

    def dr(self, e, pen):
        de = e.def_eff()
        dr = de / (de + DEF_K)
        dr -= dr * clamp(pen)
        return max(0.0, dr)

    def hurt(self, e, dmg, src, kind, hit=1.0):
        if e.dead or dmg <= 0:
            return 0.0
        real = min(dmg, e.hp)
        e.hp -= real
        if e.hp <= 1e-9:
            e.dead = True
            e.hp = 0
        src.dmg += real
        src.dmg_src[kind] += real
        src.hits += hit
        return real

    # ---------- 아군 행동
    def act_ally(self, a):
        a.gauge = 0.0
        a.actions += 1
        a.acting = True
        # 쿨타임 감소(턴 시작)
        for k in a.cd:
            a.cd[k] = max(0.0, a.cd[k] - 1)
        # 턴 시작 트리거
        for ln in a.d.lines:
            if ln.kind == 'own_ts':
                self.apply_line(a, ln, Ctx(a, a, None, False, 1.0), 1.0)
        for b in self.party:
            if b is a:
                continue
            for ln in b.d.lines:
                if ln.kind == 'ally_ts':
                    self.apply_line(b, ln, Ctx(b, a, None, False, 1.0), 1.0)
        sk = self.choose_skill(a)
        if sk is not None:
            if getattr(a.d, 'dummy', False):
                self.cast_dummy(a, sk)
            else:
                self.cast(a, sk)
        # 턴 종료
        for ln in a.d.lines:
            if ln.kind == 'own_te':
                self.apply_line(a, ln, Ctx(a, a, None, False, 1.0), 1.0)
        for name in list(a.buffs):
            b = a.buffs[name]
            if b.fresh:
                b.fresh = False
            elif b.dur != math.inf:
                b.dur -= 1
                if b.dur <= 0:
                    del a.buffs[name]
        a.acting = False
        if a.extra_turn:
            a.extra_turn = False
            a.gauge = 10000.0

    def choose_skill(self, a):
        if getattr(a.d, 'dummy', False):
            slot = self.dummy_cycle[self.dummy_i[a.idx] % len(self.dummy_cycle)]
            self.dummy_i[a.idx] += 1
            sk = a.d.skills.get(slot)
            if sk is None or a.cd.get(slot, 0) > 0:
                sk = a.d.skills['기본기']
            return sk
        for slot in ('궁극기', '특수기', '기본기'):
            sk = a.d.skills.get(slot)
            if sk is not None and a.cd.get(slot, 0) <= 0:
                return sk
        return a.d.skills.get('기본기')

    def cast_dummy(self, a, sk):
        ctx = Ctx(a, a, sk, False, 1.0)
        if sk.cd:
            a.cd[sk.slot] = sk.cd
        self.fire_allies(a, ctx, 'ally_pre')
        self.fire_allies(a, ctx, 'ally_post')

    # ---------- 시전
    def cast(self, a, sk, w=1.0, extra=False, force_basic=False, skip_lines=False):
        if w <= 1e-6 or self.depth > 2:
            return
        self.depth += 1
        try:
            ctx = Ctx(a, a, sk, extra, w)
            a.cast_count[sk.slot + ('(추가)' if extra else '')] += w
            if not extra and sk.cd:
                a.cd[sk.slot] = sk.cd
            # 노바 버스트
            if self.opts['nova'] and not extra and sk.is_attack and a.nova >= 4:
                a.nova -= 4
                ctx.inc += 0.15
                ctx.nb_burst = True
                for raw in (a.d.nb.get(sk.slot + ' 사용 시') or []):
                    ln = Line(raw, sk.slot, 'active')
                    if ln.eff['kind'] == 'gauge':
                        self.apply_line(a, ln, ctx, 1.0)
            if not skip_lines:
                self.run_own(a, ctx, 'own_pre')
                self.fire_allies(a, ctx, 'ally_pre')
            if sk.is_attack:
                self.deal_damage(a, ctx)
            if not skip_lines:
                self.run_own(a, ctx, 'own_post')
                self.fire_allies(a, ctx, 'ally_post')
            if not extra and sk.slot in ('특수기', '궁극기'):
                a.nova += sk.nv
            if self.opts['coop'] and sk.is_attack and not extra:
                self.coop_followups(a, ctx)
        finally:
            self.depth -= 1

    def run_own(self, a, ctx, kind):
        sk = ctx.skill
        for ln in a.d.lines:
            if ln.kind != kind:
                continue
            if ln.bound and ln.slot != sk.slot:
                continue
            if ln.trig and ln.na == sk.is_attack:
                continue
            self.apply_line(a, ln, ctx, 1.0)

    def fire_allies(self, actor, ctx, kind):
        for b in self.party:
            for ln in b.d.lines:
                if ln.kind != kind:
                    continue
                incl = dict(ln.params).get('자신 포함')
                if b is actor and incl != '예':
                    continue
                if b is not actor and incl == '예' and False:
                    continue
                c2 = Ctx(b, actor, ctx.skill, ctx.extra, ctx.w)
                c2.crit_p, c2.kill = ctx.crit_p, ctx.kill
                if ln.na == ctx.skill.is_attack and ln.trig and '비공격' in ln.trig:
                    continue
                self.apply_line(b, ln, c2, 1.0)
        # 수동 트리거(프로페서M): 다른 아군이 타격한 뒤 [냉각] 최대 중첩이면 [악에서 악으로] 발동
        if kind == 'ally_post' and ctx.skill.is_attack and not ctx.extra:
            for b in self.party:
                if b is not actor and b.d.manual == 'profM':
                    wt = clamp(b.stack('냉각') - 4.0)
                    if wt > 0:
                        sk2 = b.d.trigger_skills['특수기']
                        b.stacks_clear = True
                        self.cast(b, sk2, w=wt, extra=True, skip_lines=True)
                        bu = b.buffs.get('냉각')
                        if bu:
                            bu.stacks *= (1 - wt)
                        b.gauge = min(10000.0, b.gauge + 1500 * wt)

    def coop_followups(self, actor, ctx):
        for b in self.party:
            if b is actor or getattr(b.d, 'dummy', False):
                continue
            p = clamp(b.mods()['coop'], 0.0, COOP_CAP)
            if p > 0:
                self.cast(b, b.d.skills['기본기'], w=p * ctx.w, extra=True)

    # ---------- 피해
    def deal_damage(self, a, ctx):
        sk = ctx.skill
        w = ctx.w
        alive = self.alive()
        if not alive:
            return
        targets = alive if sk.all else [alive[0]]
        m = a.mods()
        d = a.d
        st = d.stats
        atkp = d.passive['atkp'] + m['atkp'] + ctx.atkp + d.gear_atkp
        A = st['atk'] * (1 + atkp)
        H = st['hp'] * (1 + d.passive['hpp'] + m['hpp'])
        D = st['def'] * (1 + d.passive['defp'] + m['defp'])
        S = a.spd()
        fa, fh, fd, fs = [x / 10000.0 for x in sk.cf]
        base = (A * fa + H * fh + D * fd) * (1 + S / 100.0 * fs) * BASE_MULT
        if sk.all:
            base /= AOE_DIV
        cr = clamp(st['cr'] / 10000.0 + d.passive['cr'] + m['cr'] + ctx.cr)
        cdv = min(3.0, st['cd'] / 10000.0 + d.passive['cd'] + m['cd'] + ctx.cd)
        ctx.crit_p = cr
        pen = clamp(m['pen'] + ctx.pen)
        killed = 0.0
        for e in targets:
            ctx.target = e
            dr = self.dr(e, pen)
            inc = ctx.inc + m['inc'] + m['inc_slot'].get(sk.slot, 0.0) + m['inc_vs'].get(e.element, 0.0)
            ea = self.opts['enemy_element'] if e.element is None else e.element
            if ea and d.element:
                if ELEM_BEATS.get(d.element) == ea:
                    inc += 0.05
                elif ELEM_LOSES.get(d.element) == ea:
                    inc -= 0.05
            if self.opts['break_p']:
                inc += 0.15 * self.opts['break_p']
            mult = (1 + inc) + cr * cdv
            dmg = base * (1 - dr) * mult * w
            before_dead = e.dead
            self.hurt(e, dmg, a, 'extra' if ctx.extra else 'direct', hit=w)
            if e.dead and not before_dead:
                killed += 1.0
        ctx.kill = clamp(killed)
        ctx.target = targets[0]

    def chain_damage(self, a, eff, ctx, w):
        side_targets = self.resolve_targets(a, eff['target'], ctx)
        if not side_targets or side_targets[0] != 'e':
            return
        m = a.mods()
        d = a.d
        atkp = d.passive['atkp'] + m['atkp'] + ctx.atkp
        val = {'atk': d.stats['atk'] * (1 + atkp), 'hp': d.stats['hp'] * (1 + d.passive['hpp'] + m['hpp']),
               'def': d.stats['def'] * (1 + d.passive['defp'] + m['defp'])}[eff['stat']]
        for e in side_targets[1]:
            dr = self.dr(e, clamp(m['pen']))
            inc = m['inc'] + m['inc_vs'].get(e.element, 0.0)
            dmg = val * eff['coef'] * BASE_MULT * (1 - dr) * (1 + inc) * w
            self.hurt(e, dmg, a, 'chain', hit=w)

    # ---------- 대상 선택
    def resolve_targets(self, owner, text, ctx):
        t = text
        sk = ctx.skill
        if t.startswith('적'):
            al = self.alive()
            if not al:
                return None
            if '전체' in t:
                return ('e', al)
            return ('e', [al[0]])
        if t.startswith('스킬 대상'):
            if sk is None:
                return None
            if sk.tg.startswith('아군') or sk.tg == '자신':
                return ('a', self.skill_allies(ctx.src, sk))
            al = self.alive()
            if not al:
                return None
            return ('e', al if sk.all else ([ctx.target] if ctx.target and not ctx.target.dead else [al[0]]))
        excl = t.startswith('자신 제외') or t.startswith('자신을 제외')
        pool = [x for x in self.party if (x is not owner or not excl)]
        mm = re.search(r'(' + '|'.join(['태양', '달', '별', '질서', '혼돈']) + r') 속성 아군', t)
        if mm:
            pool = [x for x in pool if x.element == mm.group(1)]
        if excl or t.startswith('아군'):
            if '전체' in t:
                return ('a', pool)
            n = re.search(r'(\d+)명', t)
            k = int(n.group(1)) if n else 1
            pool = sorted(pool, key=lambda x: -x.d.stats['atk'])
            return ('a', pool[:k])
        if t.startswith('자신'):
            return ('a', [owner])
        return None

    def skill_allies(self, src, sk):
        if sk.tg == '자신':
            return [src]
        if sk.tg == '아군 전체':
            return list(self.party)
        pool = sorted([x for x in self.party if x is not src] or [src], key=lambda x: -x.d.stats['atk'])
        return pool[:1]

    def _count(self, owner, ctx, last):
        if not last:
            return 0.0
        kind, names = last
        if kind == 'A':
            return sum(owner.stack(x) for x in names)
        e = ctx.target or self.primary()
        if e is None:
            return 0.0
        if kind == 'E':
            return sum(e.deb[n]['stacks'] for n in names if n in e.deb)
        return sum(d['stacks'] for d in e.deb.values())

    # ---------- 조건 평가 (0~1 가중)
    def cond_weight(self, owner, ln, ctx):
        w = 1.0
        last_name = None
        sk = ctx.skill
        for k, v in ln.params:
            if k == '사용 스킬':
                w *= 1.0 if (sk is not None and sk.slot == v) else 0.0
            elif k == '추가발동 스킬':
                w *= 1.0 if (v == '예') == bool(ctx.extra) else 0.0
            elif k == '추가발동 스킬이 아님':
                w *= 1.0 if (v == '예') == (not ctx.extra) else 0.0
            elif k == '자기 추가발동 트리거':
                w *= 0.5
            elif k in ('자신이 보유', '자신이 미보유'):
                names = [x.strip() for x in v.split(',')]
                last_name = ('A', names)
                pres = clamp(sum(owner.stack(n) for n in names))
                w *= pres if k == '자신이 보유' else (1 - pres)
            elif k in ('중첩수', '효과 개수'):
                n = float(v)
                st = self._count(owner, ctx, last_name)
                mx = 0
                if last_name and last_name[0] == 'A':
                    mx = max([owner.buffs[x].maxs or 0 for x in last_name[1] if x in owner.buffs] or [0])
                if mx and n >= mx:
                    w *= clamp(st - n + 1)
                else:
                    w *= clamp(1 - abs(st - n))
            elif k in ('중첩수 이상', '효과 개수 이상'):
                n = float(v)
                st = self._count(owner, ctx, last_name)
                w *= clamp(st - n + 1)
            elif k == '대상이 보유':
                names = [x.strip() for x in v.split(',')]
                e = ctx.target or self.primary()
                pres = 0.0
                if e is not None:
                    pres = clamp(sum(e.deb[n]['stacks'] for n in names if n in e.deb))
                last_name = ('E', names)
                w *= pres
            elif k == '대상 효과 중첩수':
                st = self._count(owner, ctx, last_name)
                w *= clamp(st - float(v) + 1)
            elif k == '대상 약화효과 보유':
                e = ctx.target or self.primary()
                has = clamp(sum(d['stacks'] for d in e.deb.values())) if e else 0.0
                last_name = ('D', None)
                w *= has if v == '예' else (1 - has)
            elif k == '대상 강인도 없음':
                w *= self.opts['break_p'] if v == '예' else (1 - self.opts['break_p'])
            elif k == '결과':
                if v == '치명타':
                    w *= ctx.crit_p
            elif k == '대상 HP% 초과':
                e = ctx.target or self.primary()
                w *= 1.0 if self.hp_frac(e) * 100 > float(v) else 0.0
            elif k == '대상 HP% 미만':
                e = ctx.target or self.primary()
                w *= 1.0 if self.hp_frac(e) * 100 < float(v) else 0.0
            elif k == '적 처치':
                kp = ctx.kill if (ctx.target and ctx.target.maxhp < INF_HP / 2) else self.opts['kill_p_inf']
                w *= kp if v == '예' else (1 - kp)
            elif k == '적을 처치하지 못함':
                kp = ctx.kill if (ctx.target and ctx.target.maxhp < INF_HP / 2) else self.opts['kill_p_inf']
                w *= (1 - kp) if v == '예' else kp
            elif k == '내 턴':
                w *= 1.0 if v == '예' else 0.0
            elif k == '자신 포함':
                pass
            elif k == '시전자 속성':
                w *= 1.0 if (ctx.src is not None and ctx.src.element == v) else 0.0
            elif k == '시전자가 보유':
                w *= clamp(ctx.src.stack(v)) if ctx.src is not None else 0.0
            elif k == '자신에게 약화효과 없음':
                w *= self.opts['no_debuff_p'] if v == '예' else (1 - self.opts['no_debuff_p'])
            elif k == '자신 약화효과 보유':
                w *= (1 - self.opts['no_debuff_p']) if v == '예' else self.opts['no_debuff_p']
            elif k == '자신 강화효과 보유':
                has = clamp(sum(b.stacks for b in owner.buffs.values()))
                w *= has if v == '예' else (1 - has)
            elif k == '스킬 쿨타임 아님':
                w *= 1.0 if owner.cd.get(v, 0) <= 0 else 0.0
            elif k == '턴 유닛이 보유':
                e = self.primary()
                w *= clamp(sum(e.deb[n]['stacks'] for n in [v] if e and n in e.deb)) if e else 0.0
            else:
                self.unmodeled['cond:' + k] += 1
                w *= self.opts['unknown_cond_p']
            if w <= 1e-9:
                return 0.0
        return w

    # ---------- 줄 적용
    def apply_line(self, owner, ln, ctx, w0):
        eff = ln.eff
        kd = eff['kind']
        if kd in ('ignored', 'perm'):
            return
        cw = (self.cond_weight(owner, ln, ctx) if ln.params else 1.0) * ln.hpw
        if cw <= 0:
            return
        w = cw * w0
        wf = w * ctx.w     # 부수효과 가중
        if kd == 'local':
            if ctx.src is not owner or ctx.skill is None:
                return
            st, v = eff['stat'], eff['val'] / 100.0
            if st == '피해 증가':
                ctx.inc += v * w
            elif st == '공격력%':
                ctx.atkp += v * w
            elif st == '치명타 확률':
                ctx.cr += v * w
            elif st == '치명타 피해':
                ctx.cd += v * w
            elif st == '방어 관통':
                ctx.pen += v * w
            elif st in ('브레이크 대상 피해 증가',):
                ctx.inc += v * w * 0.0   # 브레이크 미모델(break_p 로 처리)
            else:
                pass   # 효과 적중/명중/강인도/주는 회복량/vs 디펜더 등 무시
            return
        if kd == 'gauge':
            tg = self.resolve_targets(owner, eff['target'], ctx)
            if not tg:
                return
            p = self.opts['debuff_success'] if eff.get('judge') else 1.0
            if tg[0] == 'a':
                for x in tg[1]:
                    x.gauge = clamp(x.gauge + eff['val'] * 100.0 * wf, 0, 10000)
            else:
                for x in tg[1]:
                    x.gauge = clamp(x.gauge + eff['val'] * 100.0 * wf * p, 0, 10000)
            return
        if kd == 'cdr':
            sl = ctx.skill.slot if ctx.skill is not None else None
            if sl in owner.cd:
                owner.cd[sl] = max(0.0, owner.cd[sl] - eff['val'] * wf)
            return
        if kd == 'extra_cast':
            sk = owner.d.skills.get(eff['slot'])
            if sk is not None:
                self.cast(owner, sk, w=wf * eff['times'], extra=True)
            return
        if kd == 'extra_turn':
            if wf > 0.5 or True:
                owner.extra_turn = True if wf >= 0.5 else owner.extra_turn
                if wf < 0.5:
                    owner.gauge = clamp(owner.gauge + 10000 * wf, 0, 10000)
            return
        if kd == 'chain':
            self.chain_damage(owner, eff, ctx, wf)
            return
        if kd == 'remove':
            tg = self.resolve_targets(owner, eff['target'], ctx)
            if not tg:
                return
            for x in tg[1]:
                if tg[0] == 'a':
                    b = x.buffs.get(eff['name'])
                    if b:
                        b.stacks *= (1 - wf)
                        if b.stacks < 1e-6:
                            del x.buffs[eff['name']]
                else:
                    if eff['name'] in x.deb:
                        x.deb[eff['name']]['stacks'] *= (1 - wf)
            return
        if kd == 'buff':
            self.apply_buff(owner, eff, ctx, wf)
            return

    def apply_buff(self, owner, eff, ctx, wf):
        tg = self.resolve_targets(owner, eff['target'], ctx)
        if not tg:
            return
        side, targets = tg
        chance = eff['chance']
        if side == 'e':
            if not eff['props'] and not eff.get('dot') and eff['name'] not in KNOWN_DOT and not eff['dur']:
                pass
            p = chance * (self.opts['debuff_success'] if eff['judge'] else 1.0)
            for e in targets:
                self.apply_debuff(owner, e, eff, p * wf, ctx)
            return
        if eff['name'] == '강제 협공':      # 대상 아군이 기본기로 추가 공격(추정: 협공 = 기본기 1회)
            if not self.opts['forced_coop']:
                return
            for x in targets:
                if x.d.skills.get('기본기') is not None:
                    self.cast(x, x.d.skills['기본기'], w=wf, extra=True)
            return
        # 아군 버프
        mx = eff['max'] or 1
        if eff.get('consume'):
            for x in targets:
                b = x.buffs.get(eff['name'])
                if b:
                    b.stacks = max(0.0, b.stacks - eff['times'] * wf)
            return
        for x in targets:
            b = x.buffs.get(eff['name'])
            if b is None:
                b = Buff(eff['name'], eff['props'], mx, eff['dur'] if eff['dur'] is not None else math.inf)
                x.buffs[eff['name']] = b
                b.fresh = (x is owner and owner.acting)
            if eff['dur'] is not None and eff['dur'] != math.inf:
                b.dur = max(b.dur, eff['dur'])
                if x is owner and owner.acting:
                    b.fresh = True
            b.stacks = min(mx, b.stacks + chance * eff['times'] * wf)
            b.props = eff['props'] or b.props
            b.maxs = mx
        # 협공 확률 같은 잔여 처리 없음

    def apply_debuff(self, owner, e, eff, p, ctx):
        name = eff['name']
        dot = eff.get('dot')
        coef_kind = None
        if dot:
            coef_kind = dot
        elif name in KNOWN_DOT and not eff['props']:
            coef_kind = KNOWN_DOT[name]
        d = e.deb.get(name)
        if d is None:
            d = dict(stacks=0.0, dur=eff['dur'] if eff['dur'] is not None else math.inf)
            e.deb[name] = d
        mx = eff['max'] or (5 if coef_kind else 1)
        d['stacks'] = min(mx, d['stacks'] + p * eff['times'])
        if eff['dur'] is not None:
            d['dur'] = max(d['dur'], eff['dur'])
        for k, v in eff['props'].items():
            if k == '방어력%':
                d['defp'] = v / 100.0
            elif k == '속도%':
                d['spdp'] = v / 100.0
        if coef_kind:
            m = owner.mods()
            stat, c = coef_kind
            val = owner.d.stats['atk'] * (1 + owner.d.passive['atkp'] + m['atkp']) if stat == 'atk' else owner.d.stats['hp']
            d['dot'] = True
            d['src'] = owner
            d['mult'] = val * c * BASE_MULT * (1 + m['inc'])

# ------------------------------------------------------------------ 더미(개인 지표용 파트너, 합성 딜러)
class DummyDef:
    """속성 없는 더미 딜러: 기본기/특수기/궁극기 순환, 효과 줄 없음"""
    def __init__(self, atk=2800, spd=100, name='dummy'):
        self.dummy = True
        self.key = name
        self.name = name
        self.id, self.variant = 0, '기본'
        self.role, self.element, self.grade, self.attack_kind = '레인저', None, 'SSR', None
        self.stats = dict(hp=10000, atk=atk, **{'def': 400}, spd=spd, cr=500, cd=5000, eh=10000, er=0, der=2000, sa=3)
        mk = lambda sl, cf, cd: Skill(dict(sl=sl, n=sl, ty='액티브', tg='적 단일', act='공격', cf=[cf, 0, 0, 0], cd=cd, ef=[]))
        self.skills = {'기본기': mk('기본기', 6500, None), '특수기': mk('특수기', 10000, 3), '궁극기': mk('궁극기', 11500, 5)}
        self.trigger_skills = {}
        self.lines = []
        self.passive = defaultdict(float)
        self.unmodeled = []
        self.nb = {}
        self.manual = None
        self.spd_base = spd
        self.gear_atkp = 0.0


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
    return [dict(name='ref%d' % i, hp=INF_HP, **{'def': o['enemy_def']}, spd=o['enemy_spd'], element=o['enemy_element']) for i in range(n)]


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


def dummy_dmg_hook():
    pass


# DummyDef 는 실제 데미지를 deal_damage 에서 계산해야 buff 효과를 받는다 -> cast_dummy 대신 일반 cast 사용
def _patch_dummy():
    def cast_dummy(self, a, sk):
        self.cast(a, sk)
    Sim.cast_dummy = cast_dummy
_patch_dummy()

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
                            element=FOE_ELEM.get(e['element']), boss=e['boss']))
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
                         '기준 적: 방어력 %d, 속성 없음, 단일=1체/광역=3체, 10턴(=1000틱)' % DEFAULT_OPTS['enemy_def'],
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
        turns=turns, star=star, level=200, res_stage=10, ref_enemy_def=DEFAULT_OPTS['enemy_def'],
        normalization=dict(norm_global='10 * (0.5*단일+0.5*광역 dpt) / (SSR 딜러 4역할 상위 95% 값), 10 상한',
                           norm_role='10 * dpt / 같은 역할 최대치', ref95_combined=round(ref95)),
        assumptions=ASSUMPTIONS, opts={k: v for k, v in (dict(DEFAULT_OPTS, **(opts or {}))).items()},
    )
    return out

# ------------------------------------------------------------------ CLI
def _find_key(db, q):
    if q in db.units:
        return q
    cands = [k for k, u in db.units.items() if u['n'] == q and u['v'] == '기본']
    if len(cands) == 1:
        return cands[0]
    if q.isdigit():
        c = [k for k, u in db.units.items() if str(u['id']) == q]
        if c:
            return c[0]
    cands = [k for k in db.units if q in k]
    if cands:
        return cands[0]
    raise SystemExit('구원자를 찾을 수 없음: %s (이름 중복은 key 로: %s ...)' % (q, ', '.join(list(db.units)[:6])))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('index', help='damage_index.json 생성')
    p.add_argument('--out', default=os.path.join(OUT_DIR, 'damage_index.json'))
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('stats', help='구원자 스탯 출력')
    p.add_argument('unit')
    p.add_argument('--level', type=int, default=200)
    p.add_argument('--res', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('party', help='파티 4명 시뮬: party a,b,c,d')
    p.add_argument('units')
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p.add_argument('--stages', action='store_true', help='대표 스테이지 처치 턴 수도 출력')
    p = sub.add_parser('stage', help='구원자 key 목록으로 대표 스테이지 5개 처치 턴')
    p.add_argument('units')
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    p = sub.add_parser('unit', help='구원자 1명 지표 상세')
    p.add_argument('unit')
    p.add_argument('--turns', type=int, default=10)
    p.add_argument('--star', type=int, default=0)
    args = ap.parse_args(argv)
    db = get_db()
    if args.cmd == 'index':
        idx = build_index(args.turns, None, args.star, db)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
        print('wrote', args.out, len(idx) - 1, 'units')
    elif args.cmd == 'stats':
        k = _find_key(db, args.unit)
        d = unit_def(k, args.level, args.res, args.star)
        print(k, d.name, d.role, d.element, json.dumps(d.stats, ensure_ascii=False), dict(d.passive))
    elif args.cmd == 'party':
        keys = [_find_key(db, x) for x in args.units.split(',')]
        r = simulate_party(keys, None, args.turns, None, args.star)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        if args.stages:
            for row in stage_report(keys, args.turns, None, args.star):
                print(row)
    elif args.cmd == 'stage':
        keys = [_find_key(db, x) for x in args.units.split(',')]
        for row in stage_report(keys, args.turns, None, args.star):
            print(row)
    elif args.cmd == 'unit':
        k = _find_key(db, args.unit)
        d = unit_def(k, star=args.star)
        m = unit_metrics(k, args.turns, None, args.star)
        print(k, describe(d))
        print(json.dumps(m, ensure_ascii=False, indent=1))
        print('ally_gain', ally_gain(k, args.turns, None, args.star))
        for u in sorted(set(d.unmodeled)):
            print('  unmodeled:', u)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
