# -*- coding: utf-8 -*-
"""스킬 문장(ef 줄) 파서와 구원자 정의(UnitDef). 파싱 결과 Line 이 곧 중간 표현이다(docs/battlesim_design.md 1절)."""
import math
import re
from collections import defaultdict

from .stats import calc_stats

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
