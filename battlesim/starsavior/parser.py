# -*- coding: utf-8 -*-
"""스킬 문장(ef 줄) 파서와 구원자 정의(UnitDef). 파싱 결과 Line 이 곧 중간 표현이다(docs/battlesim_design.md 1절)."""
import math
import re
from collections import defaultdict

from .stats import calc_stats

# ------------------------------------------------------------------ 줄(ef) 파싱
NUM = r'[+-]?\d+(?:\.\d+)?'

def split_head(raw, decimal_hp=False):
    """decimal_hp는 확률 전투의 정밀 조건용. 기본값은 기대값 계산 호환용."""
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
                        number = r'\d+(?:\.\d+)?' if decimal_hp else r'\d+'
                        compare = r'이상|이하|미만' if decimal_hp else r'이상|이하'
                        hm = re.match(r'^자신 HP (' + number + r')% (' + compare + r')(?:\s*·\s*조건:\s*(.*))?$', inner, re.S)
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
    # 「N% 확률로 능력치 보정」(큐브 펌웨어 복제체 리디아): MC 기대값으로 처리
    # 「{해제 불가}」(올베로스 하수인 등장 후 속도% -1000%): 영구 버프로 변환
    m = re.match(r'^자신에게 (?:(\d+)% 확률로 )?능력치 보정 (.+?) (' + NUM + r')%?\s*(\{.*\})?$', rest)
    if m:
        chance = int(m.group(1)) / 100.0 if m.group(1) else 1.0
        stat, val = m.group(2).strip(), float(m.group(3))
        flags_s = m.group(4) or ''
        if '해제 불가' in flags_s and '이번 스킬' not in flags_s:
            return dict(kind='buff', target='자신', name='능력치보정(%s)' % stat,
                        chance=1.0, dur=None, props={stat: val}, max=None, times=1, judge=False)
        return dict(kind='local', stat=stat, val=val * chance)
    # 타 대상 능력치 보정(오르트로스 「적 전체에게 피해 증가 +30%」 — 이번 스킬에만): 자신과 같은 효과
    m = re.match(r'^(.+?)에게 (?:(\d+)% 확률로 )?능력치 보정 (.+?) (' + NUM + r')%?\s*(\{.*\})?$', rest)
    if m:
        tgt = m.group(1)
        flags_s = m.group(5) or ''
        # 조건 접두어가 target에 섞인 경우(「(자신 HP 49.99% 이하) 자신에게」 등)는 무시
        if '이번 스킬' in flags_s and not tgt.startswith('('):
            chance = int(m.group(2)) / 100.0 if m.group(2) else 1.0
            return dict(kind='local', stat=m.group(3).strip(), val=float(m.group(4)) * chance, target=tgt)
        return dict(kind='ignored', why='타 대상 능력치 보정')
    m = re.match(r'^(.+?)에게 행동 게이지 ([\d.]+)%p (증가|감소)', rest)
    if m:
        v = float(m.group(2)) * (1 if m.group(3) == '증가' else -1)
        return dict(kind='gauge', target=m.group(1), val=v, judge='효과 적중 판정' in rest)
    m = re.match(r'^(.+?)에게 스킬 쿨타임 (\d+)턴 감소', rest)
    if m:
        return dict(kind='cdr', target=m.group(1), val=int(m.group(2)))
    m = re.match(r'^(자신|.+?)에게 (기본기|특수기|궁극기) 추가 발동(?:\s*×(\d+))?', rest)
    if m:
        return dict(kind='extra_cast', slot=m.group(2), times=int(m.group(3) or 1), target=m.group(1))
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
    # 효과 지속 턴 +N(오르트로스: 적의 약화 지속 연장). 해제/교체/무작위 catch-all 전에 잡는다.
    m = re.match(r'^(.+?)에게 효과 지속 턴 \+?(\d+)', rest)
    if m:
        return dict(kind='extend', target=m.group(1), val=int(m.group(2)), name='', judge='효과 적중 판정' in rest)
    # 행동 게이지 조건부 설정(티리아 시계태엽 인형: 0%보다 높으면 0%로 낮춤)
    m = re.match(r'^(.+?)에게 행동 게이지가? (\d+)%보다 높으면 (\d+)%로 낮춤', rest)
    if m:
        return dict(kind='gauge_set_if', target=m.group(1), threshold=float(m.group(2)), val=float(m.group(3)),
                    judge='효과 적중 판정' in rest)
    if '해제' in rest or '스킬 교체' in rest or '효과 지속 턴' in rest or '무작위' in rest:
        return dict(kind='ignored', why='해제/교체/무작위')
    m = re.match(r'^자신에게 소환:\s*(.+?)\s*×\s*(\d+)$', rest)
    if m:
        return dict(kind='summon', name=m.group(1), count=int(m.group(2)))
    return dict(kind='ignored', why='미해석')


def trig_kind(phase, trig):
    """줄의 발동 시점 분류"""
    if phase == '상시':
        return 'perm'
    if phase in ('전투 시작 시', '웨이브 시작 시', '등장 후'):
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

    def __init__(self, raw, slot, src_kind, decimal_hp=False):
        self.raw, self.slot, self.src_kind = raw, slot, src_kind
        phase, cond, rest, self.hpw = split_head(raw, decimal_hp=decimal_hp)
        self.phase = phase
        self.trig, self.params = parse_cond(cond)
        self.kind = trig_kind(phase, self.trig)
        self.na = bool(self.trig and '비공격' in self.trig)
        if self.kind == 'perm':
            # 쉼표로 구분된 다중 상시 능력치(힐데 「생명력% +15%, 선제 방어 확률 +30%」)
            inner = re.sub(r'^능력치:\s*', '', rest)
            parts = [p.strip() for p in inner.split(',') if p.strip()]
            parsed = []
            for p in parts:
                pm = re.match(r'^(.+?)\s+(' + NUM + r')(%?)$', p)
                if pm:
                    parsed.append((pm.group(1).strip(), float(pm.group(2))))
            if len(parsed) == 1:
                self.eff = dict(kind='perm', stat=parsed[0][0], val=parsed[0][1])
            elif parsed:
                self.eff = dict(kind='perm_multi', stats=parsed)
            else:
                self.eff = dict(kind='ignored', why='상시미해석')
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


def ally_stack_trigger(sk, lines):
    """설명문이 명시한 다른 아군 타격 후 최대 스택 트리거와 스택 상한."""
    if sk.slot != '특수기' or sk.ty != '트리거':
        return None
    desc = sk.raw.get('dx') or sk.raw.get('d1') or ''
    m = re.match(r'자신을 제외한 아군 누군가 타격 후 자신의 \[([^]]+)\][이가] 최대 스택이면 \['
                 + re.escape(sk.name) + r'\][을를] 발동합니다\.', desc)
    if not m:
        return None
    name = m.group(1)
    caps = {ln.eff['max'] for ln in lines if ln.eff.get('name') == name and ln.eff.get('max')}
    return (name, caps.pop()) if len(caps) == 1 else None


def supported_trigger(d, sk):
    """확률 엔진이 시전 조건을 연결한 트리거. 기대값 엔진의 실행 규칙은 바꾸지 않는다."""
    from .mc_semantics import trigger_rule
    if trigger_rule(sk, d.lines):
        return True
    if (d.key, sk.name) in {('professor-m', '악에서 악으로'), ('wedding-carmen', '수호의 기사'),
                             ('white-pearl-luna', '썸머 템테이션♡')}:
        return True
    # 적 반응 스킬: foe_react.json 데이터가 있으면 지원
    if getattr(d, 'react', {}).get(sk.slot):
        return True
    return False


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
    elif st == '효과 적중':
        passive['eh'] += v / 100
    elif st == '선제 방어 확률':
        passive['preempt'] += v / 100
    else:
        return False
    return True


class UnitDef:
    def __init__(self, db, key, level=200, res_stage=10, star=0, mode='fixed', gear=None, build=None, unit_data=None):
        """build(P5, 확률 엔진용): None/'none' = 육성 없음(기존과 같음), 'light'·'standard' = 육성 프리셋(starsavior/build.py)."""
        self.key = key
        u = unit_data if unit_data is not None else db.units[key]
        self.u = u
        self.id, self.variant, self.name = u['id'], u['v'], u['n']
        self.role, self.element, self.grade, self.attack_kind = u['r'], u['a'], u['g'], u['k']
        self.stats = calc_stats(db, u, level, res_stage, star, mode, gear)
        self.build = None
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
            else:
                src = 'active'
                self.skills[slot] = sk
            for raw in s['ef']:
                ln = Line(raw, slot, src)
                self.lines.append(ln)
                if ln.kind == 'perm':
                    if ln.eff['kind'] == 'perm':
                        _perm_apply(self.stats, self.passive, ln.eff)
                    elif ln.eff['kind'] == 'perm_multi':
                        for st, val in ln.eff['stats']:
                            _perm_apply(self.stats, self.passive, dict(kind='perm', stat=st, val=val))
                elif ln.kind == 'unmodeled':
                    self.unmodeled.append('조건 미해석 줄: ' + raw[:70])
                elif ln.eff['kind'] == 'ignored' and ln.eff.get('why') == '미해석':
                    self.unmodeled.append('효과 미해석 줄: ' + raw[:70])
        for sk in self.trigger_skills.values():
            if not supported_trigger(self, sk):
                prefix = '반응 트리거' if sk.tg.startswith('반응') else '트리거'
                self.unmodeled.append('%s 스킬 미반영: %s' % (prefix, sk.name))
        if self.id == 1039 and '특수기' in self.trigger_skills:
            self.manual = 'profM'
        if build not in (None, 'none'):
            # 육성 프리셋: 장비·세트·부옵·잠재력 상시 스탯은 databook 순서(Σ%·Σ정수 한 번)로, 여정은 기본값 쪽에 넣어 스탯을 다시 계산.
            # 특수 잠재력의 나머지 줄(조건부 버프·회복 등)은 이 구원자의 줄로 추가한다(전투 중 passive 배율로 넘기지 않음).
            from .build import make_build
            bd = make_build(db, key, u, build, base_stats=self.stats, passive_cr=self.passive['cr'])
            gear2 = dict(gear or {})
            for k, v in bd['gear'].items():
                gear2[k] = gear2.get(k, 0) + v
            self.stats = calc_stats(db, u, level, res_stage, star, mode, gear2, journey=bd['journey'])
            self.stats['sa'] = self.stats['sa'] + bd['sa_bonus']
            for raw in bd['pot_lines']:
                ln = Line(raw, '잠재력', 'passive')
                self.lines.append(ln)
                if ln.kind == 'unmodeled':
                    self.unmodeled.append('조건 미해석 줄: ' + raw[:70])
                elif ln.eff['kind'] == 'ignored' and ln.eff.get('why') == '미해석':
                    self.unmodeled.append('효과 미해석 줄: ' + raw[:70])
            self.build = bd['summary']
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
    if k == '효과 적중': return ('eh', None)
    m = re.match(r'^vs (.+) 속성 피해 증가$', k)
    if m: return ('inc_vs', m.group(1))
    m = re.match(r'^(기본기|특수기|궁극기) 피해 증가$', k)
    if m: return ('inc_slot', m.group(1))
    if k == '선제 방어 확률': return ('preempt', None)
    return (None, None)
