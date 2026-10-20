# -*- coding: utf-8 -*-
"""P3 확률(몬테카를로) 전투 엔진 — 양 진영 대칭(구원자 4명 vs 스테이지 적 웨이브).

설계 = docs/battlesim_design.md 「P3 상세」. 기대값 엔진(engine.Sim)은 동결(웹 화력 지표·골든 유지)하고, 새 규칙은 여기에만 구현한다.
- 같은 줄 파서(parser.Line)·스킬(Skill)·스탯(calc_stats)·효과 적중 판정(engine.calc_hit)·피해식 상수(rules)를 쓴다.
- 치명·효과 적중·확률 효과·협공·대상 선택·피해 난수를 실제로 굴린다. 중첩은 정수.
- 시간: 시뮬 틱(게이지) / 개체별 행동 횟수(Unit.actions) / 「모델 기준 턴」 = 틱 / turn_ticks(100). 턴 제한은 모델 기준 턴으로 비교.
- 이벤트 한도 초과는 EventLimitError(정상 결과를 돌려주지 않는다).
P3 규칙 값은 rules/default.json 의 "mc" 절(MC_OPTS)."""
import math
import random
import re
from collections import defaultdict

from . import rules as _rules
from .engine import calc_hit
from .rules import DEFAULT_OPTS, ELEM_BEATS, ELEM_LOSES, MC_OPTS
from .starsavior.parser import _map_prop, split_head


class EventLimitError(RuntimeError):
    """판당 이벤트 상한(max_events) 초과 — 무한 연쇄 의심. 결과를 돌려주지 않는다."""


# ------------------------------------------------------------------ 줄 분류(반응 트리거)
# parser.trig_kind 가 'unmodeled' 로 두는 피격·사망 등 반응 시점을 확률 엔진에서만 해석한다(기대값 엔진·웹 출력 불변).
REACT_TRIG = [
    ('내가 피격될 때', 'hit_self'), ('피격 시', 'hit_self'),
    ('내가 피해를 받기 직전', 'prehit_self'), ('내가 피해 받기 직전', 'prehit_self'),
    ('아군이 피격될 때', 'hit_ally'), ('아군이 피해 받기 직전', 'prehit_ally'), ('아군이 피해를 받기 직전', 'prehit_ally'),
    ('적 공격 시', 'foe_pre'), ('적 공격 후', 'foe_post'), ('적 비공격 스킬 시', 'foe_pre_na'), ('적 비공격 스킬 후', 'foe_post_na'),
    ('내가 사망할 때', 'death_self'), ('아군 사망 시', 'death_ally'),
]


def line_kind(ln):
    """확률 엔진에서 쓰는 줄 시점. 기대값 엔진의 kind 에 반응 시점을 더한다."""
    if ln.kind != 'unmodeled':
        if ln.phase == '웨이브 시작 시' and ln.kind == 'battle_start':
            return 'wave_start'
        return ln.kind
    if ln.trig:
        for k, v in REACT_TRIG:
            if ln.trig.startswith(k):
                return v
        return 'unmodeled'
    if ln.phase == '피해 처리 직전':
        return 'prehit_self'
    if ln.phase == '피해 처리 후':
        return 'hit_self'      # 조건 없는 「피해 처리 후」 = 내가 피격된 뒤(적 설명문 「피격 후 …」와 일치, 가정)
    if ln.phase == '피격 시':
        return 'hit_self'
    return 'unmodeled'


# 확률 엔진이 해석하는 조건 키(이 밖의 키가 붙은 줄은 unknown_cond 규칙: 기본 skip + 기록)
COND_KEYS = set(['사용 스킬', '추가발동 스킬', '추가발동 스킬이 아님', '자기 추가발동 트리거', '자신이 보유', '자신이 미보유',
                 '중첩수', '효과 개수', '중첩수 이상', '효과 개수 이상', '효과 개수 미만', '대상이 보유', '대상이 미보유',
                 '대상 효과 중첩수', '대상 약화효과 보유', '대상 강화효과 보유', '대상 강인도 없음', '대상 브레이크', '결과',
                 '대상 HP% 초과', '대상 HP% 미만', '적 처치', '적을 처치하지 못함', '내 턴', '자신 포함', '시전자 속성', '시전자가 보유',
                 '자신에게 약화효과 없음', '자신 약화효과 보유', '자신 강화효과 보유', '스킬 쿨타임 아님', '턴 유닛이 보유',
                 '스킬 대상 유형', '단일 대상 공격', '대상 속성', '적 약화효과 보유', '적 강화효과 보유', '특정 효과 보유 적 존재',
                 '턴 유닛 속성', 'EnemyAdjustType', 'NotEnemyAdjustType'])

# 회복·보호막·부활·해제·무작위 효과 원문 해석(parser 는 이 줄들을 'ignored' 로 둔다)
RX_HEAL = re.compile(r'^(.+?)에게 회복 = (자신|대상) (최대 생명력|생명력|공격력|방어력)×([\d.]+)%')
RX_SHIELD = re.compile(r'^(.+?)에게 〈([^〉]+)〉\s*\((\d+턴|지속 무한)(?:\s*/\s*([^)]*))?\)\s*보호막 = 자신 (생명력|공격력|방어력)×([\d.]+)%')
RX_REVIVE = re.compile(r'^(.+?)에게 부활\(생명력 (\d+)%\)')
RX_HOT = re.compile(r'‹턴마다 회복: 대상 최대 생명력×([\d.]+)%›')
RX_DISPEL = re.compile(r'^(.+?)에게 〈[^〉]+〉\s*\((약화|강화)효과 해제\)')
RX_DISPEL_N = re.compile(r'^(.+?)에게 \((약화|강화)효과 해제\) 효과 (\d+)개 해제')
RX_RANDOM = re.compile(r'^(.+?)에게\s*(?:\(대상마다 (\d+)% 판정\)\s*)?무작위 효과 〈[^〉]+〉: \[(.+)\] 중 1개')
RX_RECV_HEAL = re.compile(r'^(.+?)에게 능력치 보정 받는 회복량 ([+-][\d.]+)%')
RX_GAUGE_P = re.compile(r'^(.+?)에게 (\d+)% 확률로 행동 게이지 ([\d.]+)%p (증가|감소)')
RX_EXTRA_P = re.compile(r'^자신에게 (\d+)% 확률로 (기본기|특수기|궁극기) 추가 발동')
SPECIAL_RX = (RX_SHIELD, RX_HEAL, RX_REVIVE, RX_DISPEL, RX_DISPEL_N, RX_RANDOM, RX_RECV_HEAL, RX_GAUGE_P, RX_EXTRA_P)


def line_rest(ln):
    """줄에서 시점·조건 머리를 뗀 효과 문장"""
    return split_head(ln.raw)[2].strip()
RX_HP_COND = re.compile(r'\(자신 HP ([\d.]+)% (이상|이하)')
CHECK_NAME = re.compile(r'확인용|체크용|카운팅|확인 용')
HARD_CC = ('기절', '수면')
UNTARGETABLE = ('은신', '현장 대기')
CRITICAL_RX = re.compile(r'피해 감소|보호막|회복|부활|불사|무효|면역|피해 제한|분담')


def _dur(v):
    return math.inf if v is None else v


TARGET_KEYS = set(['대상 속성', '대상이 보유', '대상이 미보유', '대상 HP% 초과', '대상 HP% 미만', '대상 약화효과 보유',
                   '대상 강화효과 보유', '대상 효과 중첩수'])


class _ParamView:
    """줄의 조건 일부만 판정할 때 쓰는 얇은 보기(raw 는 HP 조건 판정에 그대로)"""
    __slots__ = ('params', 'raw')

    def __init__(self, ln, params):
        self.params, self.raw = params, ''


def skill_desc(d, slot):
    """구원자·적 정의에서 스킬 칸의 설명문(d1)"""
    u = getattr(d, 'u', None)
    if u:
        for sk in u.get('sk', []):
            if sk.get('sl') == slot:
                return sk.get('d1') or ''
    return (getattr(d, 'desc', None) or {}).get(slot, '')


_ELEM = '(태양|달|별|질서|혼돈)'


def auto_rule(d, ln, kind):
    """자동 지정 대상 규칙을 스킬 설명문에서 읽는다 -> dict(mode, excl_self, element) 또는 None(못 찾음)"""
    desc = skill_desc(d, ln.slot)
    if not desc:
        return None
    sents = [x.strip() for x in re.split(r'(?<=다)\.\s*', desc) if x.strip()]
    e = ln.eff
    rest = line_rest(ln)
    mname = re.search(r'〈([^〉]+)〉', rest)
    name = e.get('name') if e.get('kind') == 'buff' else (mname.group(1) if mname else None)
    if kind == 'heal_bonus' or RX_RECV_HEAL.match(rest):
        keys = ['회복량이 증가']
    elif name:
        keys = ['[' + name, name]
    elif RX_HEAL.match(rest):
        keys = ['회복량이 증가', '생명력을 회복', '회복']
    elif RX_SHIELD.match(rest):
        keys = ['[보호막]', '보호막']
    elif e.get('kind') == 'gauge':
        keys = ['행동 게이지']
    else:
        keys = []
    for key in keys:              # 키워드가 든 문장을 앞에서부터 보고 규칙이 읽히는 첫 문장을 쓴다
        for sent in sents:
            if key in sent:
                r = _rule_from_sentence(sent)
                if r is not None:
                    return r
    return None


def _rule_from_sentence(sent):
    m = re.search(r'아군 대상이 ' + _ELEM + r' 속성이라면', sent)
    if m:
        return dict(mode='element_all', element=m.group(1))
    if '생명력 비율이 가장 낮은 아군' in sent:
        return dict(mode='lowest_hp', excl_self='자신을 제외한 현재 생명력 비율' in sent or '자신을 제외한 생명력 비율' in sent)
    m = re.search(r'공격력이 가장 높은 (?:' + _ELEM + r' 속성 )?아군', sent)
    if m:
        return dict(mode='highest_atk', excl_self='자신을 제외한' in sent, element=m.group(1))
    if '무작위 아군' in sent:
        return dict(mode='random', excl_self='자신을 제외한 무작위' in sent)
    m = re.search(r'자신을 제외한 ' + _ELEM + r' 속성 아군 전체', sent)
    if m:
        return dict(mode='element_all', excl_self=True, element=m.group(1))
    if '대상이 강화 효과 상태라면' in sent:
        return dict(mode='has_buff')
    if '아군 대상' in sent:
        return dict(mode='skill_target')
    if '아군 전체' in sent:
        return dict(mode='element_all')
    return None


def _shield_dur(t):
    return math.inf if t == '지속 무한' else int(t.replace('턴', ''))


def paren_after_name(raw):
    """〈이름〉 바로 뒤의 (…) 를 괄호 짝을 맞춰 꺼낸다 -> (괄호 안, 그 뒤 나머지). 없으면 (None, 뒤 문장)"""
    if '〉' not in raw:
        return None, ''
    rest = raw.split('〉', 1)[1]
    t = rest.lstrip()
    if not t.startswith('('):
        return None, rest
    depth = 0
    for i, ch in enumerate(t):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return t[1:i], t[i + 1:]
    return None, rest


def full_props(ln):
    """parser 는 속성 괄호 안의 괄호에서 끊긴다(「피해 분담(수호) +30%」 유실). 균형 괄호로 다시 읽은 속성"""
    from .starsavior.parser import parse_props
    inner, _ = paren_after_name(ln.raw)
    if inner is None or '(' not in inner:
        return ln.eff['props']
    return parse_props(inner)[1]


# ------------------------------------------------------------------ 런타임 개체
class Eff:
    """유닛에 붙은 효과 1개(강화·약화·보호막·지속 피해·지속 회복). stacks 는 정수."""
    __slots__ = ('name', 'props', 'stacks', 'maxs', 'dur', 'src', 'harmful', 'fresh', 'shield', 'dot', 'inst', 'hot',
                 'check', 'fixed')

    def __init__(self, name, props, maxs, dur, src, harmful):
        self.name, self.props, self.maxs, self.dur, self.src, self.harmful = name, props, maxs, dur, src, harmful
        self.stacks = 0
        self.fresh = False
        self.shield = 0.0
        self.dot = None      # (stat, coef)
        self.inst = None     # 지속 피해 중첩별 [시전자, 남은 턴]
        self.hot = 0.0       # 턴마다 회복 계수(대상 최대 생명력 비율)
        self.check = False   # 확인용 버프(행동 끝에 사라짐)
        self.fixed = False   # 해제 불가


class Unit:
    def __init__(self, d, side, pos, b, leader=False, fx=None):
        self.d = d
        self.side, self.pos = side, pos
        self.name = d.name
        self.key = getattr(d, 'key', d.name)
        self.element = d.element
        self.role = d.role
        self.b = b
        st = d.stats
        self.fx = dict(fx or {})                 # 스테이지 효과(상시)
        hpp = d.passive['hpp'] + self.fx.get('생명력%', 0.0) / 100.0
        self.maxhp = float(math.floor(st['hp'] * (1 + hpp)))
        self.hp = self.maxhp
        self.gauge = 0.0
        self.eff = {}
        self.cd = {}
        frac = b.mc['enemy_init_cd'] if side == 1 else b.opts['init_cd_frac']
        for slot, sk in d.skills.items():
            self.cd[slot] = (sk.cd * frac) if sk.cd else 0
        self.dead = False
        self.last_slot = None
        self.last_target = None
        self.extra_turn = False
        self.acting = False
        self.leader = leader
        self.actions = 0
        self.cast_count = defaultdict(int)
        self.dmg = 0.0
        self.taken = 0.0
        self.healed = 0.0
        self.shield_given = 0.0
        self.death_t = None
        self.nova = 0.0          # 개인 노바 포스(nova_pool='unit' 일 때만 씀)
        self._m = None

    # ---- 버프 합산(캐시: 효과가 바뀌면 b.dirty())
    def mods(self):
        if self._m is not None:
            return self._m
        m = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0, coop=0.0, eh=0.0, er=0.0,
                 der=0.0, critred=0.0, guard=0.0, heal_give=0.0, heal_recv=0.0, inc_single=0.0, inc_aoe=0.0, evade=0.0, acc=0.0,
                 inc_vs={}, inc_slot={}, red={})
        for e in self.eff.values():
            if e.stacks <= 0:
                continue
            for k, v in e.props.items():
                _add_prop(m, k, v, e.stacks)
        for k, v in self.fx.items():
            _add_prop(m, k, v, 1)
        self._m = m
        return m

    def stack(self, name):
        e = self.eff.get(name)
        return e.stacks if e else 0

    def has(self, name):
        return self.stack(name) > 0

    def spd(self):
        m = self.mods()
        p = self.d.passive
        s = self.d.spd_base * (1 + m['spdp'] + p['spdp']) + m['spdf'] + p['spdf']
        if self.leader:
            s += self.b.mc['leader_speed']
        return max(1.0, s)

    def shield_total(self):
        return sum(e.shield for e in self.eff.values() if e.shield > 0)

    def n_harmful(self):
        return sum(1 for e in self.eff.values() if e.harmful and e.stacks > 0)

    def n_good(self):
        return sum(1 for e in self.eff.values() if not e.harmful and e.stacks > 0 and not e.check)


def _add_prop(m, k, v, stacks):
    key, sub = _map_prop(k)
    val = v / 100.0 * stacks
    if key is not None:
        if key == 'spdf':
            m['spdf'] += v * stacks
        elif key in ('inc_vs', 'inc_slot'):
            m[key][sub] = m[key].get(sub, 0.0) + val
        else:
            m[key] += val
        return
    if k == '효과 저항':
        m['er'] += val
    elif k == '절대 저항':
        m['der'] += val
    elif k == '치명타 피해 감소':
        m['critred'] += val
    elif k == '피해 분담(수호)':
        m['guard'] += val
    elif k == '회피율':
        m['evade'] += val
    elif k == '명중률':
        m['acc'] += val
    elif k == '주는 회복량':
        m['heal_give'] += val
    elif k == '받는 회복량':
        m['heal_recv'] += val
    elif k == '단일 대상 피해 증가':
        m['inc_single'] += val
    elif k == '전체 대상 피해 증가':
        m['inc_aoe'] += val
    elif k in ('받는 피해 감소', '피해 감소'):
        m['red']['all'] = m['red'].get('all', 0.0) + val
    elif k == '전체 대상 피해 감소':
        m['red']['aoe'] = m['red'].get('aoe', 0.0) + val
    elif k == '단일 대상 피해 감소':
        m['red']['single'] = m['red'].get('single', 0.0) + val
    else:
        mm = re.match(r'^(기본기|특수기|궁극기) 피해 감소$', k)
        if mm:
            m['red'][mm.group(1)] = m['red'].get(mm.group(1), 0.0) + val


class Ctx:
    """시전 1회(또는 피격 반응 1회)의 문맥. owner = 줄 주인, src = 시전자(공격자), skill = 시전 스킬, target = 대상."""
    __slots__ = ('owner', 'src', 'skill', 'extra', 'targets', 'target', 'inc', 'atkp', 'cr', 'cd', 'pen', 'eh', 'crit',
                 'kill', 'coop_used', 'heal_give', 'heal_recv', 'local', 'nb', 'hit_victim', 'acc', 'evaded', 'recv_by',
                 'local_by')

    def __init__(self, owner, src, skill, extra=False):
        self.owner, self.src, self.skill, self.extra = owner, src, skill, extra
        self.targets, self.target = [], None
        self.inc = self.atkp = self.cr = self.cd = self.pen = self.eh = self.acc = 0.0
        self.heal_give = self.heal_recv = 0.0
        self.recv_by = defaultdict(float)      # 대상별 「받는 회복량」 보정(이번 스킬): 대상마다 따로(공유 금지)
        self.local_by = defaultdict(lambda: defaultdict(float))   # 대상별 「이번 스킬에만」 피해 보정(대상 조건이 붙은 줄, 전체 공격)
        self.evaded = set()   # 이 시전에서 회피한 대상(회피한 대상에는 약화가 걸리지 않음)
        self.crit = False
        self.kill = False
        self.coop_used = False
        self.local = None    # 피격 직전 줄의 이번 피격 한정 보정 {unit: {'defp':..,'guard':..}}
        self.nb = False
        self.hit_victim = None


# ------------------------------------------------------------------ 전투
class Battle:
    def __init__(self, ally_defs, waves, rng, opts=None, mc=None, leader=None, fx=None, turn_limit=None,
                 timeline=False, enemy_lines=True, max_turns=50):
        self.opts = dict(DEFAULT_OPTS)
        self.opts.update(opts or {})
        self.mc = dict(MC_OPTS)
        self.mc.update(mc or {})
        self.rng = rng
        self.allies = [Unit(d, 0, i, self, leader=(leader == i)) for i, d in enumerate(ally_defs)]
        self.waves = waves
        self.wave_i = -1
        self.foes = []
        self.fx = fx or {}
        self.turn_ticks = float(self.mc['turn_ticks'])
        self.turn_limit = turn_limit
        self.max_turns = max_turns
        self.t = 0.0
        self.events = 0
        self.depth = 0
        self.team_nova = 0.0
        self.unsup = defaultdict(int)
        self.timeline = [] if timeline else None
        self.enemy_lines = enemy_lines
        self.result = None
        self.clear_t = None
        self.check_pending = []
        self.first_death = None
        self.all_foes = []
        self._cur_line = None    # 실행 중인 줄(자동 지정 대상 규칙을 그 스킬 설명에서 찾을 때 씀)
        self.once = set()        # {전투당 1회} 줄 사용 기록

    # ---------- 공용
    def tick(self):
        self.events += 1
        if self.events > self.mc['max_events']:
            raise EventLimitError('이벤트 %d 회 초과(시각 %.1f틱)' % (self.mc['max_events'], self.t))

    def side_units(self, side):
        return self.allies if side == 0 else self.foes

    def alive(self, side):
        return [u for u in self.side_units(side) if not u.dead]

    def turn_now(self):
        return self.t / self.turn_ticks

    def dirty(self, u):
        u._m = None

    def log(self, **kw):
        if self.timeline is not None and len(self.timeline) < 3000:
            kw['turn'] = round(self.turn_now(), 2)
            self.timeline.append(kw)

    def lines_of(self, u):
        if u.side == 1 and not self.enemy_lines:
            return ()
        return u.d.lines

    # ---------- 진행
    def spawn_wave(self):
        self.wave_i += 1
        defs = self.waves[self.wave_i]
        lead = None
        rule = self.mc['enemy_leader']
        if rule == 'boss':
            lead = next((i for i, d in enumerate(defs) if getattr(d, 'boss', False)), 0 if defs else None)
        elif rule == 'first':
            lead = 0
        self.foes = [Unit(d, 1, i, self, leader=(lead == i), fx=self.fx) for i, d in enumerate(defs)]
        self.all_foes.extend(self.foes)   # 웨이브별 적 기록(피해 집계는 전 웨이브 합)
        for u in self.foes:
            for ln in self.lines_of(u):
                if line_kind(ln) in ('battle_start', 'wave_start'):
                    self.run_line(u, ln, Ctx(u, u, None))
        if self.wave_i > 0:
            for u in self.alive(0):
                for ln in u.d.lines:
                    if line_kind(ln) == 'wave_start':
                        self.run_line(u, ln, Ctx(u, u, None))

    def run(self):
        if self.wave_i < 0:   # 시험에서 미리 첫 웨이브를 불러 상태를 만든 경우는 건너뜀
            self.spawn_wave()
            for u in self.allies:
                for ln in u.d.lines:
                    if line_kind(ln) in ('battle_start', 'wave_start'):
                        self.run_line(u, ln, Ctx(u, u, None))
        horizon = (self.turn_limit if self.turn_limit else self.max_turns) * self.turn_ticks
        while True:
            self.tick()
            if not self.alive(0):
                self.result = 'wipe'
                break
            if not self.alive(1):
                if self.wave_i + 1 < len(self.waves):
                    self.spawn_wave()
                    continue
                self.result = 'clear'
                self.clear_t = self.t
                break
            living = self.alive(0) + self.alive(1)
            best, bt = self.pick_next(living)
            if self.t + bt > horizon + 1e-9:
                self.result = 'timeout'
                break
            for x in living:
                x.gauge = min(10000.0, x.gauge + x.spd() * bt)
            self.t += bt
            self.act(best)
        return self

    def pick_next(self, living):
        """다음 행동 유닛과 그때까지 걸리는 틱. 동시 100% 는 _tie_before 순서"""
        best, bt = None, None
        for x in living:
            need = 0.0 if x.gauge >= 10000 else (10000 - x.gauge) / x.spd()
            if bt is None or need < bt - 1e-9:
                best, bt = x, need
            elif abs(need - bt) <= 1e-9 and self._tie_before(x, best):
                best = x
        return best, bt

    def _tie_before(self, x, y):
        """동시 100%: 추가 턴 > 게이지 높은 순 > 속도 높은 순 > 고정 순서(아군 먼저, 칸 순)"""
        if x.extra_turn != y.extra_turn:
            return x.extra_turn
        if abs(x.gauge - y.gauge) > 1e-9:
            return x.gauge > y.gauge
        if abs(x.spd() - y.spd()) > 1e-9:
            return x.spd() > y.spd()
        return (x.side, x.pos) < (y.side, y.pos)

    # ---------- 행동
    def act(self, u):
        u.gauge = 0.0
        u.extra_turn = False      # 추가 턴은 이 행동으로 소비(행동 끝에 지우면 다음 차례 판정에서 우선권이 사라짐)
        u.actions += 1
        u.acting = True
        if self.mc['shield_tick'] == 'turn_start':
            self._tick_shields(u)
        for k in u.cd:
            u.cd[k] = max(0.0, u.cd[k] - 1)
        self._tick_dot_hot(u)
        if u.dead:
            u.acting = False
            return
        self.fire(u, 'own_ts', Ctx(u, u, None))
        for v in self.alive(u.side):
            if v is not u:
                self.fire(v, 'ally_ts', Ctx(v, u, None))
        for v in self.alive(1 - u.side):
            self.fire(v, 'enemy_ts', Ctx(v, u, None))
        if not u.dead:
            if any(u.has(n) for n in HARD_CC):
                self.log(actor=u.name, skip='행동 불가')
            else:
                taunt = u.eff.get('도발')
                tsrc = taunt.src if (taunt and taunt.stacks > 0) else None
                if tsrc is not None and not tsrc.dead and u.d.skills.get('기본기') is not None:
                    self.cast(u, u.d.skills['기본기'], target=tsrc)
                else:
                    sk = self.choose_skill(u)
                    if sk is not None:
                        self.cast(u, sk)
        if not u.dead:
            self.fire(u, 'own_te', Ctx(u, u, None))
            for name in list(u.eff):
                e = u.eff[name]
                if e.fresh:
                    e.fresh = False
                    continue
                if e.inst is not None:
                    for it in e.inst:
                        it[1] -= 1
                    e.inst = [it for it in e.inst if it[1] > 0]
                    e.stacks = len(e.inst)
                    if not e.inst:
                        del u.eff[name]
                    continue
                if e.shield > 0 and self.mc['shield_tick'] == 'turn_start':
                    continue
                if e.dur != math.inf:
                    e.dur -= 1
                    if e.dur <= 0:
                        del u.eff[name]
            self.dirty(u)
        self._expire_checks()
        u.acting = False
        if u.extra_turn and not u.dead:
            u.gauge = 10000.0     # extra_turn 표시는 실제로 그 턴을 쓸 때(act 시작)까지 유지 -> 동시 100% 판정에서 최우선
        elif u.dead:
            u.extra_turn = False

    def _tick_shields(self, u):
        for name in list(u.eff):
            e = u.eff[name]
            if e.shield > 0 and e.dur != math.inf:
                e.dur -= 1
                if e.dur <= 0:
                    del u.eff[name]
        self.dirty(u)

    def _expire_checks(self):
        for holder, name in self.check_pending:
            e = holder.eff.get(name)
            if e is not None and e.check:
                del holder.eff[name]
                self.dirty(holder)
        self.check_pending = []

    def choose_skill(self, u):
        silenced = u.has('침묵')
        for slot in ('궁극기', '특수기', '기본기'):
            sk = u.d.skills.get(slot)
            if sk is None or u.cd.get(slot, 0) > 0:
                continue
            if silenced and sk.cd:
                continue
            return sk
        return u.d.skills.get('기본기')

    # ---------- 대상
    def targetable(self, side):
        al = self.alive(side)
        ok = [u for u in al if not any(u.has(n) for n in UNTARGETABLE)]
        return ok or al

    def pick_attack_target(self, att):
        pool = self.targetable(1 - att.side)
        if not pool:
            return None
        if att.side == 0:
            # 구원자 오토: boss_first = 살아 있는 보스가 있으면 보스(사용자 관찰 2026-10-20), 그다음 보호막+HP 합 최저(같으면 앞 칸)
            if self.mc['ally_auto_target'] == 'boss_first':
                bosses = [v for v in pool if getattr(v.d, 'boss', False)]
                if bosses:
                    pool = bosses
            return min(pool, key=lambda v: (v.hp + v.shield_total(), v.pos))
        return self.weighted_pick(pool)

    def weighted_pick(self, pool):
        rw = self.mc['target_row_weight']
        dm = float(self.mc['target_defender_mult'])
        w = lambda v: dm if v.role == '디펜더' else 1.0
        front = [v for v in pool if v.pos < 2]
        back = [v for v in pool if v.pos >= 2]
        if self.mc['target_mode'] == 'unit_weight':
            cands = []
            for row, share in ((front, rw[0]), (back, rw[1])):
                for v in row:
                    cands.append((v, share / len(row) * w(v)))
            if not front or not back:
                cands = [(v, w(v)) for v in pool]
            return self._roll(cands)
        if front and back:
            row = front if self.rng.random() < rw[0] / (rw[0] + rw[1]) else back
        else:
            row = front or back
        return self._roll([(v, w(v)) for v in row])

    def _roll(self, cands):
        tot = sum(x for _, x in cands)
        r = self.rng.random() * tot
        for v, x in cands:
            r -= x
            if r < 0:
                return v
        return cands[-1][0]

    def skill_targets(self, u, sk, target=None):
        """시전 대상 목록. 공격 = 적(단일은 고른 1명, 전체는 전원) / 비공격 = 아군 쪽 tg 기준."""
        if sk.is_attack:
            if sk.all:
                return list(self.alive(1 - u.side))
            if target is not None and not target.dead:
                return [target]
            v = self.pick_attack_target(u)
            return [v] if v else []
        if target is not None:
            return [target]
        tg = sk.tg or ''
        if tg == '자신':
            return [u]
        if tg == '아군 전체':
            return list(self.alive(u.side))
        if tg.startswith('적'):
            if '전체' in tg:
                return list(self.alive(1 - u.side))
            v = self.pick_attack_target(u)
            return [v] if v else []
        kind = self._skill_support_kind(sk)
        return [self.pick_ally(u, sk_kind=kind, exclude_self=(kind == 'buff'))]

    def _skill_support_kind(self, sk):
        raws = [s for s in (sk.raw.get('ef') or [])]
        if any('부활(' in r for r in raws):
            return 'revive'
        if sk.raw.get('hl') or any('회복 =' in r or '보호막 =' in r for r in raws):
            return 'heal'
        return 'buff'

    def pick_ally(self, u, sk_kind='buff', exclude_self=False):
        if sk_kind == 'revive':
            dead = [v for v in self.side_units(u.side) if v.dead]
            if dead:
                return dead[0]
        pool = [v for v in self.alive(u.side) if not (exclude_self and v is u)] or [u]
        if sk_kind in ('heal', 'revive') and self.mc['heal_target'] == 'lowest_hp_ratio':
            return min(pool, key=lambda v: (v.hp / v.maxhp, v.pos))
        return max(pool, key=lambda v: (self.live_atk(v), -v.pos))

    def live_atk(self, v):
        return v.d.stats['atk'] * (1 + v.d.passive['atkp'] + v.mods()['atkp'] + v.d.gear_atkp)

    def resolve(self, owner, text, ctx, kind='buff'):
        """줄의 대상 문구 -> 유닛 목록(owner 기준 상대 진영). 해석 못 하면 None."""
        t = text.strip()
        if t.startswith('스킬 대상'):
            if ctx.skill is None:
                return None
            if ctx.hit_victim is not None and ctx.owner is not ctx.src:
                return [ctx.hit_victim] if not ctx.hit_victim.dead else []
            return [x for x in ctx.targets if not x.dead or kind == 'revive']
        if t.startswith('적'):
            opp = self.alive(1 - owner.side)
            if not opp:
                return []
            if '전체' in t:
                return opp
            if ctx.target is not None and not ctx.target.dead and ctx.target.side != owner.side:
                return [ctx.target]
            if ctx.src is not None and ctx.src.side != owner.side and not ctx.src.dead:
                return [ctx.src]      # 반응 줄의 「적」 = 나를 친 적
            v = self.pick_attack_target(owner)
            return [v] if v else []
        cur = self._cur_line
        if ('자동 지정' in t and (t.startswith('아군') or t.startswith('자신 제외') or t.startswith('자신을 제외'))
                and not (cur is not None and cur.eff.get('name') == '강제 협공') and kind != 'remove'):
            got = self.select_auto(owner, t, ctx, kind)
            if got is not None:
                return got
        excl = t.startswith('자신 제외') or t.startswith('자신을 제외')
        pool = [x for x in self.alive(owner.side) if (x is not owner or not excl)]
        mm = re.search(r'(태양|달|별|질서|혼돈) 속성 아군', t)
        if mm:
            pool = [x for x in pool if x.element == mm.group(1)]
        if excl or t.startswith('아군'):
            if '전체' in t:
                return pool
            if not pool:
                return []
            n = re.search(r'(\d+)명', t)
            k = int(n.group(1)) if n else 1
            if kind in ('heal', 'shield') and self.mc['heal_target'] == 'lowest_hp_ratio':
                pool = sorted(pool, key=lambda v: (v.hp / v.maxhp, v.pos))
            else:
                pool = sorted(pool, key=lambda v: (-self.live_atk(v), v.pos))
            return pool[:k]
        if t.startswith('자신'):
            return [owner]
        return None

    def select_auto(self, owner, t, ctx, kind):
        """「아군(자동 지정)」·「아군 1명(자동 지정)」·「자신 제외 아군 1명(자동 지정)」의 대상을 그 줄이 달린 스킬의 설명문에서 읽는다
        (예: 세르팡 궁극기 「자신과 자신을 제외한 현재 생명력 비율이 가장 낮은 아군」, 다나 「자신을 제외한 공격력이 가장 높은 아군」,
        프레이 궁극기 「아군 대상이 별 속성이라면 회복량이 증가」). 규칙을 못 찾으면 기존 규칙(회복·보호막 = 생명력 비율 최저,
        그 밖 = 공격력 최고)으로 고르고 unsupported 에 「대상 규칙 미확인」을 남긴다. 같은 대상을 두 번 고르지 않는다."""
        ln = self._cur_line
        spec = auto_rule(owner.d, ln, kind) if ln is not None else None
        n = re.search(r'(\d+)명', t)
        k = int(n.group(1)) if n else None
        if spec is None:
            nm = ln.eff.get('name') or '' if ln is not None else ''
            if not (CHECK_NAME.search(nm) or '판별용' in nm):   # 내부 표지용 버프는 기록하지 않음
                self.unsup['selector: 대상 규칙 미확인(기본 규칙 사용) ' + (ln.raw[:50] if ln is not None else t)] += 1
            return None
        excl = spec.get('excl_self') or t.startswith('자신 제외') or t.startswith('자신을 제외')
        pool = [x for x in self.alive(owner.side) if not (excl and x is owner)]
        if spec.get('element'):
            pool = [x for x in pool if x.element == spec['element']]
        mode = spec['mode']
        if mode == 'skill_target':
            pool = [x for x in ctx.targets if x.side == owner.side]
            return list(dict.fromkeys(pool))
        if mode == 'has_buff':
            return [x for x in pool if x.n_good() > 0]
        if mode == 'element_all':
            return pool
        if not pool:
            return []
        if mode == 'random':
            return [self.rng.choice(pool)]
        if mode == 'lowest_hp':
            pool = sorted(pool, key=lambda v: (v.hp / v.maxhp, v.pos))
        else:
            pool = sorted(pool, key=lambda v: (-self.live_atk(v), v.pos))
        return pool[:k or 1]

    # ---------- 시전
    def cast(self, u, sk, extra=False, target=None, skip_lines=False, via=None):
        if u.dead:
            return None
        if self.incapacitated(u):
            # 기절·수면이면 어떤 시전도 없음(협공·반격·트리거·추가 발동 포함 — 추가 발동은 침묵·도발·쿨타임과 무관하지만 기절·수면은 불가, formulas_web.md 2.1)
            return None
        if self.depth >= self.mc['max_depth']:
            self.unsup['depth: 연쇄 깊이 상한으로 시전 생략'] += 1
            return None
        self.tick()
        self.depth += 1
        try:
            ctx = Ctx(u, u, sk, extra)
            u.cast_count[sk.slot + ('(추가)' if extra else '')] += 1
            if not extra and sk.cd:
                u.cd[sk.slot] = sk.cd
            if (u.side == 0 and self.opts['nova'] and self.opts['nova_policy'] == 'manual' and not extra and sk.is_attack
                    and self.nova_of(u) >= 4 and (self.mc['manual_burst'] == 'any_attack' or sk.slot == '궁극기')):
                self.nova_add(u, -4)
                ctx.inc += 0.15
                ctx.nb = True
            ctx.targets = self.skill_targets(u, sk, target)
            ctx.target = ctx.targets[0] if ctx.targets else None
            if self.timeline is not None:
                t0 = ctx.targets[0] if ctx.targets else None
                self.log(actor=u.name, side=u.side, pos=u.pos, skill=sk.slot + ('(추가)' if extra else ''),
                         targets=[x.name for x in ctx.targets], via=via or ('extra' if extra else None), nb=ctx.nb,
                         all=bool(sk.all), tgt_side=(t0.side if t0 is not None else None),
                         tgt_boss=bool(t0 is not None and getattr(t0.d, 'boss', False)))
            if not skip_lines:
                self.run_own(u, ctx, 'own_pre')
                self.fire_side(u, ctx, 'ally_pre')
                self.fire_foes(u, ctx, 'foe_pre' if sk.is_attack else 'foe_pre_na')
            if sk.is_attack and ctx.targets:
                self.deal(u, ctx)
            if not u.dead:
                self.skill_heal(u, sk, ctx)
            if not skip_lines and not u.dead:
                self.run_own(u, ctx, 'own_post')
            if not skip_lines:
                self.fire_side(u, ctx, 'ally_post')
                self.fire_foes(u, ctx, 'foe_post' if sk.is_attack else 'foe_post_na')
            if u.side == 0 and not extra and sk.slot in ('특수기', '궁극기'):
                self.nova_add(u, sk.nv)
            if u.side == 0 and self.opts['coop'] and sk.is_attack and not extra and not u.dead:
                self.coop(u, ctx)
            if u.side == 0 and sk.is_attack and not extra:
                self.prof_m(u, ctx)
            u.last_slot = sk.slot
            return ctx
        finally:
            self.depth -= 1

    def nova_of(self, u):
        """버스트 판정용 노바 포스: team = 파티 공용 풀, unit = 구원자 개인(opts.nova_pool)"""
        return u.nova if self.opts['nova_pool'] == 'unit' else self.team_nova

    def nova_add(self, u, v):
        if self.opts['nova_pool'] == 'unit':
            u.nova += v
        else:
            self.team_nova += v

    def incapacitated(self, u):
        """행동 불능(기절·수면). 강인도 격파는 브레이크 미구현(P5)이라 없음."""
        return any(u.has(n) for n in HARD_CC)

    def skill_heal(self, u, sk, ctx):
        """스킬 기본 회복(데이터 hl 필드, 예 프레이 특수기 '생명력×21%'). 회복량 = 버림(시전자 최대 생명력 x 계수 x (1+주는+받는)).
        대상: 아군 전체 스킬 = 아군 전체, 자신 = 자신, 아군 단일·반응 대상 = 스킬 대상, 적 대상 공격 스킬 = 아군 전체(왈츠 아세라 특수기 설명)."""
        hl = (sk.raw or {}).get('hl')
        if not hl:
            return
        m = re.match(r'^(생명력|공격력|방어력)×([\d.]+)%$', str(hl).strip())
        if not m:
            self.unsup['hl: 회복 계수 형식 미해석 ' + str(hl)[:30]] += 1
            return
        stat = {'생명력': u.maxhp, '공격력': self.atk_stat(u, ctx), '방어력': self.def_stat(u)}[m.group(1)]
        tg = sk.tg or ''
        if tg == '자신':
            targets = [u]
        elif tg == '아군 전체' or tg.startswith('적'):
            targets = list(self.alive(u.side))
        else:
            targets = [x for x in ctx.targets if x.side == u.side and not x.dead]
        give = u.mods()['heal_give'] + ctx.heal_give
        for x in targets:
            got = self.heal(u, x, stat * float(m.group(2)) / 100.0, give + ctx.recv_by.get(x, 0.0))
            self.log(heal=u.name, to=x.name, amount=got)

    def run_own(self, u, ctx, kind):
        sk = ctx.skill
        lines = [ln for ln in self.lines_of(u) if line_kind(ln) == kind and not (ln.bound and ln.slot != sk.slot)
                 and not (ln.trig and ln.na == sk.is_attack)]
        if lines:
            self.run_batch(u, lines, ctx)

    def fire(self, u, kind, ctx):
        lines = [ln for ln in self.lines_of(u) if line_kind(ln) == kind]
        if lines:
            self.run_batch(u, lines, ctx)

    def fire_side(self, actor, ctx, kind):
        for b in self.alive(actor.side):
            lines = [ln for ln in self.lines_of(b) if line_kind(ln) == kind
                     and not (b is actor and dict(ln.params).get('자신 포함') != '예')
                     and self._trig_matches_skill(ln, ctx.skill)]
            if lines:
                c2 = Ctx(b, actor, ctx.skill, ctx.extra)
                c2.targets, c2.target, c2.crit, c2.kill, c2.evaded = ctx.targets, ctx.target, ctx.crit, ctx.kill, ctx.evaded
                self.run_batch(b, lines, c2)

    def fire_foes(self, actor, ctx, kind):
        for b in self.alive(1 - actor.side):
            lines = [ln for ln in self.lines_of(b) if line_kind(ln) == kind]
            if lines:
                c2 = Ctx(b, actor, ctx.skill, ctx.extra)
                c2.targets, c2.target, c2.crit, c2.evaded = ctx.targets, ctx.target, ctx.crit, ctx.evaded
                self.run_batch(b, lines, c2)

    @staticmethod
    def _trig_matches_skill(ln, sk):
        """「아군 공격 후」 = 공격 스킬만, 「아군 비공격 스킬 후」 = 비공격만(기대값 엔진은 공격 여부를 비공격 줄만 구분)"""
        if not ln.trig or sk is None:
            return True
        if '비공격' in ln.trig:
            return not sk.is_attack
        if '공격' in ln.trig:
            return sk.is_attack
        return True

    def coop(self, actor, ctx):
        """협공: 아군 기본기 뒤에만, 공격 1번에 1명(확률 높은 순으로 굴림), 원 공격과 같은 대상(전체면 무작위 적)."""
        if self.opts['coop_trigger'] == 'basic_only' and ctx.skill.slot != '기본기':
            return
        if ctx.coop_used:
            return
        cands = []
        for b in self.alive(0):
            if b is actor or b.d.skills.get('기본기') is None or self.incapacitated(b):
                continue   # 기절·수면(강인도 격파 포함, 미구현)이면 협공 불가(공식 2026-09-10 NOA 가이드)
            p = min(_rules.COOP_CAP, max(0.0, b.mods()['coop']))
            if p > 0:
                cands.append((b, p))
        for b, p in sorted(cands, key=lambda bp: (-bp[1], bp[0].pos)):
            if self.rng.random() < p:
                self.cast(b, b.d.skills['기본기'], extra=True, target=self._coop_target(ctx), via='coop')
                return

    def _coop_target(self, ctx):
        if ctx.skill.all:
            al = self.alive(1)
            return self.rng.choice(al) if al else None
        return ctx.target if (ctx.target is not None and not ctx.target.dead) else None

    def prof_m(self, actor, ctx):
        """프로페서M 수동 트리거(기대값 엔진과 같은 규칙): 다른 아군 타격 뒤 [냉각] 5중첩이면 [악에서 악으로] 발동, 냉각 소거, 게이지 +15%."""
        for b in self.alive(0):
            if b is actor or b.d.manual != 'profM':
                continue
            if b.stack('냉각') >= 5:
                sk2 = b.d.trigger_skills['특수기']
                b.eff.pop('냉각', None)
                self.dirty(b)
                self.cast(b, sk2, extra=True, skip_lines=True, target=ctx.target, via='trigger')
                b.gauge = min(10000.0, b.gauge + 1500)

    # ---------- 피해
    def atk_stat(self, u, ctx=None):
        m = u.mods()
        return u.d.stats['atk'] * (1 + u.d.passive['atkp'] + m['atkp'] + (ctx.atkp if ctx else 0.0) + u.d.gear_atkp)

    def def_stat(self, u, local=0.0):
        m = u.mods()
        return max(0.0, u.d.stats['def'] * (1 + u.d.passive['defp'] + m['defp'] + local))

    def hp_stat(self, u):
        return u.maxhp

    def rand(self):
        lo, hi = self.mc['rand_range']
        steps = int(round((hi - lo) * 10000))
        return lo + self.rng.randint(0, steps) / 10000.0

    def deal(self, a, ctx):
        sk = ctx.skill
        m = a.mods()
        d = a.d
        A = self.atk_stat(a, ctx)
        H = d.stats['hp'] * (1 + d.passive['hpp'] + m['hpp'])
        D = d.stats['def'] * (1 + d.passive['defp'] + m['defp'])
        S = a.spd()
        fa, fh, fd, fs = [x / 10000.0 for x in sk.cf]
        base = (A * fa + H * fh + D * fd) * (1 + S / 100.0 * fs) * _rules.BASE_MULT
        if a.side == 1 and not self.mc['enemy_same_formula']:
            base /= _rules.BASE_MULT      # 민감도: 적 공격엔 x1.85 가 없다고 가정
        if sk.all:
            base /= _rules.AOE_DIV
        cr = min(1.0, max(0.0, d.stats['cr'] / 10000.0 + d.passive['cr'] + m['cr'] + ctx.cr))
        cdv = min(3.0, d.stats['cd'] / 10000.0 + d.passive['cd'] + m['cd'] + ctx.cd)
        pen = min(1.0, max(0.0, m['pen'] + ctx.pen))
        ctx.crit = False
        reactions = []
        for v in list(ctx.targets):
            if v.dead:
                continue
            ctx.target = v
            # 회피(가정: 회피율 - 공격자 명중률 보정, 필중이면 0). 회피하면 치명 없음·감소 합 +50%·약화 안 걸림
            ev = 0.0 if (a.has('필중') or self.mc['evade_model'] == 'off') else v.mods()['evade'] - (m['acc'] + ctx.acc)
            evaded = ev > 0 and self.rng.random() < ev
            by = ctx.local_by[v]
            crit = (not evaded) and self.rng.random() < min(1.0, cr + by['cr'])
            ctx.crit = ctx.crit or crit
            if evaded:
                ctx.evaded.add(v)
            self.strike(a, v, base, ctx, crit, min(3.0, cdv + by['cd']), min(1.0, pen + by['pen']), reactions, evaded)
        a.last_target = ctx.targets[0] if ctx.targets else None
        # 피격 반응은 전체 공격의 모든 대상 처리가 끝난 뒤(동시성 규칙)
        for v, hctx in reactions:
            if v.dead:
                continue
            self.fire(v, 'hit_self', hctx)
            for w in self.alive(v.side):
                if w is v:
                    continue
                lines = [ln for ln in self.lines_of(w) if line_kind(ln) == 'hit_ally']
                if lines:
                    c2 = Ctx(w, a, sk, ctx.extra)
                    c2.target, c2.targets, c2.crit, c2.hit_victim = v, [v], hctx.crit, v
                    self.run_batch(w, lines, c2)
            self.reaction_skills(v, a, sk)
        ctx.target = ctx.targets[0] if ctx.targets else None

    def strike(self, a, v, base, ctx, crit, cdv, pen, reactions, evaded=False):
        sk = ctx.skill
        self.tick()
        # 피격 직전 줄(대상·대상 아군)
        hctx = Ctx(v, a, sk, ctx.extra)
        hctx.target, hctx.targets, hctx.crit, hctx.hit_victim = v, [v], crit, v
        if evaded:
            hctx.evaded.add(v)
        hctx.local = defaultdict(lambda: defaultdict(float))
        self.fire(v, 'prehit_self', hctx)
        for w in self.alive(v.side):
            if w is not v:
                lines = [ln for ln in self.lines_of(w) if line_kind(ln) == 'prehit_ally']
                if lines:
                    c2 = Ctx(w, a, sk, ctx.extra)
                    c2.target, c2.targets, c2.crit, c2.hit_victim, c2.local = v, [v], crit, v, hctx.local
                    self.run_batch(w, lines, c2)
        # 수호: 대상 제외 같은 편 생존자 중 분담 비율이 가장 높은 1명
        guard, share = None, 0.0
        for w in self.alive(v.side):
            if w is v:
                continue
            s = w.mods()['guard'] + hctx.local[w]['guard']
            if s > share + 1e-12:
                guard, share = w, s
        share = min(1.0, share)
        r = self.rand()
        if v.has('스킬 피해 무효'):
            # 〈스킬 피해 무효〉 「스킬 무효화 1회」: 이번 스킬 피해 0, 효과 1회 소모(지속 피해는 스킬이 아니라 그대로)
            del v.eff['스킬 피해 무효']
            self.dirty(v)
            self.log(nullify=v.name)
            reactions.append((v, hctx))
            return
        if guard is None or share <= 0:
            pieces = [(v, base)]
        elif self.mc['guard_mode'] == 'final_transfer':
            full = self.final_dmg(a, v, base, ctx, crit, cdv, pen, r, hctx)
            pieces = [(v, None, full * (1 - share)), (guard, None, full * share)]
        else:
            pieces = [(v, base * (1 - share)), (guard, base * share)]
        killed = False
        for pc in pieces:
            w = pc[0]
            if len(pc) == 3:
                dmg = max(1.0, math.floor(pc[2]))
            else:
                dmg = self.final_dmg(a, w, pc[1], ctx, crit, cdv, pen, r, hctx)
            if w is guard:
                self.log(guard=guard.name, protects=v.name, dmg=dmg)
            killed = self.apply_damage(a, w, dmg, 'guard' if w is guard else 'hit', shieldable=True) or killed
        if killed and v.dead:
            ctx.kill = True
        reactions.append((v, hctx))

    def final_dmg(self, a, v, base, ctx, crit, cdv, pen, r, hctx):
        sk = ctx.skill
        m = a.mods()
        vm = v.mods()
        local_def = hctx.local[v]['defp'] if hctx is not None and hctx.local is not None else 0.0
        de = self.def_stat(v, local_def)
        dr = de / (de + _rules.DEF_K)
        dr = max(0.0, dr - dr * pen)
        inc = ctx.inc + ctx.local_by[v]['inc'] + m['inc'] + m['inc_slot'].get(sk.slot, 0.0) + m['inc_vs'].get(v.element, 0.0)
        inc += m['inc_aoe'] if sk.all else m['inc_single']
        if a.element and v.element:
            if ELEM_BEATS.get(a.element) == v.element:
                inc += 0.05
            elif ELEM_LOSES.get(a.element) == v.element:
                inc -= 0.05
        if v.last_slot is not None and v.last_slot == sk.slot:
            inc += self.mc['counter_inc']
        red = vm['red']
        dec = red.get('all', 0.0) + red.get('aoe' if sk.all else 'single', 0.0) + red.get(sk.slot, 0.0)
        if hctx is not None and hctx.local is not None:
            dec += hctx.local[v]['red']      # 피격 직전 「이번 스킬에만」 피해 감소(감소 합에 더함)
        if hctx is not None and v in hctx.evaded:
            dec += 0.5     # 회피 시 감소 합 +50%(databook #d-sum)
        dec = min(_rules.DEC_CAP, dec)
        mult = 1 + inc - dec
        if crit:
            mult += max(0.0, cdv - vm['critred'])
        dmg = base * (1 - dr) * mult * r
        return max(1.0, math.floor(dmg))

    def apply_damage(self, a, v, dmg, kind, shieldable=True):
        """보호막 -> HP 순. 사망하면 True."""
        if v.dead or dmg <= 0:
            return False
        rest = dmg
        absorbed = 0.0
        if shieldable:
            for name in list(v.eff):
                e = v.eff[name]
                if e.shield > 0 and rest > 0:
                    take = min(e.shield, rest)
                    e.shield -= take
                    rest -= take
                    absorbed += take
                    if e.shield <= 1e-9 and not e.props:
                        del v.eff[name]
                        self.dirty(v)
        real = min(rest, v.hp)
        v.hp -= real
        if a is not None:
            a.dmg += real + absorbed        # 넘친 피해(오버킬)는 제외
        v.taken += real + absorbed
        if v.hp <= 1e-9:
            self.kill(v, a)
            return True
        return False

    def kill(self, v, a):
        v.hp = 0.0
        v.dead = True
        v.death_t = self.t
        if v.side == 0 and self.first_death is None:
            self.first_death = v
        self.log(death=v.name)
        self.fire(v, 'death_self', Ctx(v, a, None))
        for w in self.alive(v.side):
            self.fire(w, 'death_ally', Ctx(w, a, None))
        v.eff = {}
        v.gauge = 0.0
        self.dirty(v)

    def reaction_skills(self, v, a, sk):
        """반응 트리거 스킬(지원 목록): 웨딩 카르멘 「수호의 기사」 — 사랑의 서약 아군이 피격되면 발동(쿨타임 적용)."""
        for w in self.alive(v.side):
            if w is v:
                continue
            ts = w.d.trigger_skills.get('특수기')
            if ts is None or not (ts.tg or '').startswith('반응 대상(아군)'):
                continue
            oath = v.eff.get('사랑의 서약(해제불가)')
            if oath is None or oath.src is not w or w.cd.get('특수기', 0) > 0:
                continue
            ctx = self.cast(w, ts, extra=True, target=v, via='reaction')
            w.cd['특수기'] = ts.cd or 0
            if ctx is not None:
                ctx.targets = [v]

    def _tick_dot_hot(self, u):
        """턴 시작: 지속 피해(시전자별 중첩, 매 틱 시전자 현재 스탯, 보호막 무시)와 지속 회복"""
        for name in list(u.eff):
            e = u.eff.get(name)
            if e is None:
                continue
            if e.inst:
                stat, c = e.dot
                for src, _left in list(e.inst):
                    if u.dead:
                        return
                    sm = src.mods()
                    val = self.atk_stat(src) if stat == 'atk' else src.maxhp
                    inc = sm['inc']
                    if src.last_slot is not None and src.last_slot == u.last_slot:
                        inc += self.mc['counter_inc']
                    vm = u.mods()
                    dec = min(_rules.DEC_CAP, vm['red'].get('all', 0.0))
                    de = self.def_stat(u)
                    dr = de / (de + _rules.DEF_K)
                    dmg = max(1.0, math.floor(val * c * _rules.BASE_MULT * (1 + inc - dec) * (1 - dr) * self.rand()))
                    self.apply_damage(src, u, dmg, 'dot', shieldable=False)
            if e.hot > 0 and not u.dead:
                self.heal(e.src or u, u, u.maxhp * e.hot, 0.0)

    # ---------- 회복·보호막
    def heal(self, src, v, amount, give):
        if v.dead:
            return 0.0
        recv = v.mods()['heal_recv']
        tot = 1 + give + recv
        if tot <= 0:
            return 0.0
        h = math.floor(amount * tot)
        real = max(0.0, min(h, v.maxhp - v.hp))
        v.hp += real
        if src is not None:
            src.healed += real
        return real

    # ---------- 조건
    def cond_ok(self, owner, ln, ctx):
        mh = RX_HP_COND.search(ln.raw)
        if mh:
            frac = owner.hp / owner.maxhp * 100
            thr = float(mh.group(1))
            if mh.group(2) == '이상' and not frac >= thr - 1e-9:
                return False
            if mh.group(2) == '이하' and not frac <= thr + 1e-9:
                return False
        last = None
        sk = ctx.skill
        tgt = ctx.target if ctx.target is not None else None
        for k, v in ln.params:
            if k not in COND_KEYS:
                self.unsup['cond: ' + k] += 1
                if self.mc['unknown_cond'] == 'roll':
                    if self.rng.random() >= self.opts['unknown_cond_p']:
                        return False
                    continue
                return False
            if k == '사용 스킬':
                if not (sk is not None and sk.slot == v):
                    return False
            elif k == '추가발동 스킬':
                if (v == '예') != bool(ctx.extra):
                    return False
            elif k == '추가발동 스킬이 아님':
                if (v == '예') != (not ctx.extra):
                    return False
            elif k == '자기 추가발동 트리거':
                pass
            elif k in ('자신이 보유', '자신이 미보유'):
                names = [x.strip() for x in v.split(',')]
                last = ('A', names)
                pres = any(owner.has(n) for n in names)
                if pres != (k == '자신이 보유'):
                    return False
            elif k in ('중첩수', '효과 개수'):
                n = float(v)
                st = self._count(owner, ctx, last)
                mx = 0
                if last and last[0] == 'A':
                    mx = max([owner.eff[x].maxs or 0 for x in last[1] if x in owner.eff] or [0])
                if mx and n >= mx:
                    if st < n:
                        return False
                elif st != n:
                    return False
            elif k in ('중첩수 이상', '효과 개수 이상', '대상 효과 중첩수'):
                if self._count(owner, ctx, last) < float(v):
                    return False
            elif k == '효과 개수 미만':
                if self._count(owner, ctx, last) >= float(v):
                    return False
            elif k in ('대상이 보유', '대상이 미보유'):
                names = [x.strip() for x in v.split(',')]
                last = ('E', names)
                pres = tgt is not None and any(tgt.has(n) for n in names)
                if pres != (k == '대상이 보유'):
                    return False
            elif k == '대상 약화효과 보유':
                last = ('TD', None)
                has = tgt is not None and tgt.n_harmful() > 0
                if has != (v == '예'):
                    return False
            elif k == '대상 강화효과 보유':
                last = ('TB', None)
                has = tgt is not None and tgt.n_good() > 0
                if has != (v == '예'):
                    return False
            elif k in ('대상 강인도 없음', '대상 브레이크'):
                if v == '예':     # 강인도·브레이크 미구현(P5): 브레이크 상태 없음
                    return False
            elif k == '결과':
                if v == '치명타' and not ctx.crit:
                    return False
                if v == '회피' and not (ctx.hit_victim is not None and ctx.hit_victim in ctx.evaded):
                    return False
            elif k == '대상 HP% 초과':   # 데이터 단위 1/10000 (7500 = 75%)
                if tgt is None or not (tgt.hp / tgt.maxhp > float(v) / 10000.0):
                    return False
            elif k == '대상 HP% 미만':
                if tgt is None or not (tgt.hp / tgt.maxhp < float(v) / 10000.0):
                    return False
            elif k == '적 처치':
                if bool(ctx.kill) != (v == '예'):
                    return False
            elif k == '적을 처치하지 못함':
                if (not ctx.kill) != (v == '예'):
                    return False
            elif k == '내 턴':
                if (v == '예') != (owner.acting and ctx.src is owner and not ctx.extra):
                    return False
            elif k == '자신 포함':
                pass
            elif k == '시전자 속성':
                if ctx.src is None or ctx.src.element != v:
                    return False
            elif k == '시전자가 보유':
                if ctx.src is None or not ctx.src.has(v):
                    return False
            elif k == '자신에게 약화효과 없음':
                if (owner.n_harmful() == 0) != (v == '예'):
                    return False
            elif k == '자신 약화효과 보유':
                last = ('SD', None)
                if (owner.n_harmful() > 0) != (v == '예'):
                    return False
            elif k == '자신 강화효과 보유':
                last = ('SB', None)
                if (owner.n_good() > 0) != (v == '예'):
                    return False
            elif k == '스킬 쿨타임 아님':
                if owner.cd.get(v, 0) > 0:
                    return False
            elif k == '턴 유닛이 보유':
                if ctx.src is None or not ctx.src.has(v):
                    return False
            elif k == '스킬 대상 유형':
                tgv = (sk.tg if sk is not None else '') or ''
                if not (tgv == v or (v == '적 전체' and sk is not None and sk.all)):
                    return False
            elif k == '단일 대상 공격':
                single = sk is not None and sk.is_attack and not sk.all
                if single != (v == '예'):
                    return False
            elif k in ('EnemyAdjustType', 'NotEnemyAdjustType'):   # 공격해 온 상대(시전자)의 속성이 v 인가(가정: 데이터 내부 키 이름)
                same = ctx.src is not None and ctx.src.element == v
                if same != (k == 'EnemyAdjustType'):
                    return False
            elif k == '턴 유닛 속성':
                if ctx.src is None or ctx.src.element != v:
                    return False
            elif k == '대상 속성':
                if tgt is None or tgt.element != v:
                    return False
            elif k in ('적 약화효과 보유', '적 강화효과 보유'):
                opp = self.alive(1 - owner.side)
                fn = (lambda x: x.n_harmful() > 0) if k == '적 약화효과 보유' else (lambda x: x.n_good() > 0)
                if any(fn(x) for x in opp) != (v == '예'):
                    return False
            elif k == '특정 효과 보유 적 존재':
                names = [x.strip() for x in v.split(',')]
                if not any(x.has(n) for x in self.alive(1 - owner.side) for n in names):
                    return False
        return True

    def _count(self, owner, ctx, last):
        if not last:
            return 0
        kind, names = last
        tgt = ctx.target
        if kind == 'A':
            return sum(owner.stack(x) for x in names)
        if kind == 'E':
            return sum(tgt.stack(n) for n in names) if tgt is not None else 0
        if kind == 'TD':
            return tgt.n_harmful() if tgt is not None else 0
        if kind == 'TB':
            return tgt.n_good() if tgt is not None else 0
        if kind == 'SD':
            return owner.n_harmful()
        if kind == 'SB':
            return owner.n_good()
        return 0

    # ---------- 줄 실행
    def run_line(self, owner, ln, ctx):
        self.run_batch(owner, [ln], ctx)

    def line_ok(self, owner, ln, ctx):
        if owner.dead and line_kind(ln) not in ('death_self',):
            return False
        if ln.eff['kind'] == 'perm':
            return False
        if '전투당 1회' in ln.raw and (id(owner), id(ln)) in self.once:
            return False
        if ln.params or RX_HP_COND.search(ln.raw):
            ok = self.cond_ok(owner, ln, ctx)
        else:
            ok = True
        if ok and '전투당 1회' in ln.raw:
            self.once.add((id(owner), id(ln)))
        return ok

    @staticmethod
    def _is_cast_line(ln):
        return ln.eff['kind'] == 'extra_cast' or (ln.eff['kind'] == 'ignored' and RX_EXTRA_P.match(line_rest(ln)) is not None)

    def run_batch(self, owner, lines, ctx):
        """같은 사건(시점·주인)에 걸린 줄 묶음: 조건은 사건 시점 상태로 한꺼번에 판정하고, 효과는 순서대로 실행하되
        추가 발동(시전)은 묶음의 나머지 효과(중첩 소비 등) 뒤에 실행한다(같은 사건에서 자기 자신을 다시 부르는 무한 연쇄 방지)."""
        ok = []
        for ln in lines:
            if self._per_target(owner, ln, ctx):
                self.run_per_target(owner, ln, ctx)
            elif self.line_ok(owner, ln, ctx):
                ok.append(ln)
        for ln in ok:
            if not self._is_cast_line(ln):
                self.exec_line(owner, ln, ctx)
        for ln in ok:
            if self._is_cast_line(ln):
                self.exec_line(owner, ln, ctx)

    def _per_target(self, owner, ln, ctx):
        """대상 조건(대상 속성·대상이 보유 등)이 붙은 「받는 회복량」 줄, 또는 여러 대상을 치는 내 공격의 「이번 스킬에만」 보정 줄:
        조건을 대상마다 따로 판정해야 한다(첫 대상 하나로 판정해 전원에게 적용하면 틀림)."""
        if not any(k in TARGET_KEYS for k, _ in ln.params) or ctx.skill is None or ctx.src is not owner:
            return False
        if ln.eff['kind'] == 'ignored' and RX_RECV_HEAL.match(line_rest(ln)):
            return True
        return ln.eff['kind'] == 'local' and len(ctx.targets) > 1

    def run_per_target(self, owner, ln, ctx):
        others = [(k, v) for k, v in ln.params if k not in TARGET_KEYS]
        if others or RX_HP_COND.search(ln.raw):
            probe = Ctx(owner, ctx.src, ctx.skill, ctx.extra)
            probe.targets, probe.target, probe.crit, probe.kill = ctx.targets, ctx.target, ctx.crit, ctx.kill
            if not self.cond_ok(owner, _ParamView(ln, others), probe):
                return
        tparams = [(k, v) for k, v in ln.params if k in TARGET_KEYS]
        rest = line_rest(ln)
        mrecv = RX_RECV_HEAL.match(rest) if ln.eff['kind'] == 'ignored' else None
        for x in list(ctx.targets):
            probe = Ctx(owner, ctx.src, ctx.skill, ctx.extra)
            probe.targets, probe.target = [x], x
            if not self.cond_ok(owner, _ParamView(ln, tparams), probe):
                continue
            if mrecv:
                ctx.recv_by[x] += float(mrecv.group(2)) / 100.0
            else:
                key = {'피해 증가': 'inc', '치명타 확률': 'cr', '치명타 피해': 'cd', '방어 관통': 'pen'}.get(ln.eff['stat'])
                if key is None:
                    self.unsup['local(대상별): ' + ln.eff['stat']] += 1
                else:
                    ctx.local_by[x][key] += ln.eff['val'] / 100.0

    def exec_line(self, owner, ln, ctx):
        prev = self._cur_line
        self._cur_line = ln
        try:
            self._exec_line(owner, ln, ctx)
        finally:
            self._cur_line = prev

    def _exec_line(self, owner, ln, ctx):
        if owner.dead and line_kind(ln) not in ('death_self',):
            return
        eff = ln.eff
        kd = eff['kind']
        if kd == 'ignored':
            self.run_special(owner, ln, ctx, line_rest(ln))
            return
        if kd == 'local':
            st, v = eff['stat'], eff['val'] / 100.0
            if ctx.local is not None and line_kind(ln) in ('prehit_self', 'prehit_ally'):
                if st == '방어력%':
                    ctx.local[owner]['defp'] += v
                elif st == '피해 분담(수호)':
                    ctx.local[owner]['guard'] += v
                elif st in ('피해 감소', '받는 피해 감소'):
                    ctx.local[owner]['red'] += v
                else:
                    self.unsup['local(피격 직전): ' + st] += 1
                return
            if ctx.src is not owner or ctx.skill is None:
                return
            if st == '피해 증가':
                ctx.inc += v
            elif st == '공격력%':
                ctx.atkp += v
            elif st == '치명타 확률':
                ctx.cr += v
            elif st == '치명타 피해':
                ctx.cd += v
            elif st == '방어 관통':
                ctx.pen += v
            elif st == '효과 적중':
                ctx.eh += v
            elif st == '주는 회복량':
                ctx.heal_give += v
            elif st == '명중률':
                ctx.acc += v
            return
        if kd == 'gauge':
            tg = self.resolve(owner, eff['target'], ctx)
            if not tg:
                return
            for x in tg:
                if x.side != owner.side and eff.get('judge') and not self.roll_hit(owner, ctx, x, None):
                    continue
                x.gauge = min(10000.0, max(0.0, x.gauge + eff['val'] * 100.0))
            return
        if kd == 'cdr':
            # 내 시전 문맥 = 그 스킬 칸. 피격 반응 등 남의 시전 문맥이면 공격자의 칸이 아니라 줄 주인 쪽 칸:
            # 줄이 달린 스킬 칸 -> (패시브면) 궁극기 -> 쿨타임이 가장 긴 칸 (에밀리·길레 설명은 모두 궁극기 쿨타임 감소, 가정)
            if ctx.src is owner and ctx.skill is not None:
                sl = ctx.skill.slot
            elif ln.slot in owner.cd:
                sl = ln.slot
            elif '궁극기' in owner.cd:
                sl = '궁극기'
            else:
                sl = max(owner.cd, key=lambda s: owner.cd[s]) if owner.cd else None
            if sl in owner.cd:
                owner.cd[sl] = max(0.0, owner.cd[sl] - eff['val'])
            return
        if kd == 'extra_cast':
            sk = owner.d.skills.get(eff['slot'])
            if sk is not None:
                tgt = owner.last_target if (owner.last_target is not None and not owner.last_target.dead) else None
                for _ in range(eff['times']):
                    self.cast(owner, sk, extra=True, target=tgt)
            return
        if kd == 'extra_turn':
            owner.extra_turn = True
            return
        if kd == 'chain':
            self.chain(owner, eff, ctx)
            return
        if kd == 'remove':
            # 「아군(자동 지정)에게 'X' 해제」 = 표지 효과를 가진 아군 누구에게서든 해제(가정)
            tg = self.resolve(owner, eff['target'], ctx, kind='remove')
            if tg and '자동 지정' in eff['target']:
                tg = [x for x in self.alive(owner.side) if (x is not owner or not eff['target'].startswith('자신 제외'))]
            for x in tg or []:
                if eff['name'] in x.eff:
                    del x.eff[eff['name']]
                    self.dirty(x)
            return
        if kd == 'buff':
            if '(' in (paren_after_name(ln.raw)[0] or ''):
                eff = dict(eff, props=full_props(ln))
            mh = RX_HOT.search(ln.raw)
            self.apply_buff(owner, eff, ctx, hot=float(mh.group(1)) / 100.0 if mh else 0.0, raw=ln.raw)
            return

    def run_special(self, owner, ln, ctx, rest):
        """parser 가 무시한 줄 중 확률 엔진이 해석하는 것: 회복·보호막·부활·해제·무작위 효과·받는 회복량"""
        m = RX_SHIELD.match(rest)
        if m:
            tg = self.resolve(owner, m.group(1), ctx, kind='shield')
            stat = {'생명력': owner.maxhp, '공격력': self.atk_stat(owner), '방어력': self.def_stat(owner)}[m.group(5)]
            amount = math.floor(stat * float(m.group(6)) / 100.0)
            props = {}
            if m.group(4):
                for q in m.group(4).split(','):
                    mm = re.match(r'^(.+?)\s+([+-]?\d+(?:\.\d+)?)%?$', q.strip())
                    if mm:
                        props[mm.group(1).strip()] = float(mm.group(2))
            for x in tg or []:
                e = x.eff.get(m.group(2))
                if e is None:
                    e = Eff(m.group(2), props, 1, _shield_dur(m.group(3)), owner, False)
                    e.stacks = 1
                    x.eff[m.group(2)] = e
                    e.fresh = (x is owner and owner.acting and self.mc['shield_tick'] != 'turn_start')
                e.shield += amount      # 같은 보호막 재부여 = 합산, 지속은 긴 쪽
                e.dur = max(e.dur, _shield_dur(m.group(3)))
                owner.shield_given += amount
                self.dirty(x)
            return
        m = RX_HEAL.match(rest)
        if m:
            tg = self.resolve(owner, m.group(1), ctx, kind='heal')
            own = ctx.src is owner
            for x in tg or []:
                base_u = owner if m.group(2) == '자신' else x
                stat = {'생명력': base_u.maxhp, '최대 생명력': base_u.maxhp, '공격력': self.atk_stat(base_u),
                        '방어력': self.def_stat(base_u)}[m.group(3)]
                give = owner.mods()['heal_give'] + (ctx.heal_give + ctx.recv_by.get(x, 0.0) if own else 0.0)
                self.heal(owner, x, stat * float(m.group(4)) / 100.0, give)
            return
        m = RX_REVIVE.match(rest)
        if m:
            tg = self.resolve(owner, m.group(1), ctx, kind='revive')
            for x in tg or []:
                if x.dead:
                    x.dead = False
                    x.hp = float(math.floor(x.maxhp * int(m.group(2)) / 100.0))
                    x.gauge = 0.0
                    x.death_t = None
                    self.log(revive=x.name)
            return
        m = RX_DISPEL.match(rest)
        if m:
            tg = self.resolve(owner, m.group(1), ctx)
            harmful = m.group(2) == '약화'
            for x in tg or []:
                for name in list(x.eff):
                    e = x.eff[name]
                    if e.harmful == harmful and not e.fixed and e.shield <= 0:
                        del x.eff[name]
                self.dirty(x)
            return
        m = RX_DISPEL_N.match(rest)
        if m:   # 효과 N개 해제: 해제 가능한 것 중 먼저 붙은 순(가정)
            tg = self.resolve(owner, m.group(1), ctx)
            harmful = m.group(2) == '약화'
            for x in tg or []:
                names = [n for n, e in x.eff.items() if e.harmful == harmful and not e.fixed and e.shield <= 0][:int(m.group(3))]
                for n in names:
                    del x.eff[n]
                self.dirty(x)
            return
        m = RX_RANDOM.match(rest)
        if m:
            from .starsavior.foe import gloss
            g = gloss()
            tg = self.resolve(owner, m.group(1), ctx)
            names = [x.strip() for x in m.group(3).split(',')]
            p = int(m.group(2)) / 100.0 if m.group(2) else 1.0
            for x in tg or []:
                if self.rng.random() >= p:
                    continue
                name = self.rng.choice(names)
                info = g.get(name)
                if info is None:
                    self.unsup['무작위 효과 사전 없음: ' + name] += 1
                    continue
                eff = dict(kind='buff', target='자신', name=name, chance=1.0, dur=info['dur'] or 2, props=info['props'],
                           max=None, times=1, judge=(x.side != owner.side))
                self.add_effect(owner, x, eff, ctx)
            return
        m = RX_RECV_HEAL.match(rest)
        if m:   # 받는 회복량 보정은 대상마다(대상 조건도 대상마다 판정 — run_batch 의 per_target)
            if ctx.src is owner:
                for x in self.resolve(owner, m.group(1), ctx, kind='heal_bonus') or []:
                    ctx.recv_by[x] += float(m.group(2)) / 100.0
            return
        m = RX_GAUGE_P.match(rest)
        if m:
            tg = self.resolve(owner, m.group(1), ctx)
            dv = float(m.group(3)) * 100.0 * (1 if m.group(4) == '증가' else -1)
            for x in tg or []:
                if self.rng.random() >= int(m.group(2)) / 100.0:
                    continue
                if x.side != owner.side and '효과 적중 판정' in rest and not self.roll_hit(owner, ctx, x, None):
                    continue
                x.gauge = min(10000.0, max(0.0, x.gauge + dv))
            return
        m = RX_EXTRA_P.match(rest)
        if m:
            sk = owner.d.skills.get(m.group(2))
            if sk is not None and self.rng.random() < int(m.group(1)) / 100.0:
                self.cast(owner, sk, extra=True, target=ctx.src if (ctx.src is not None and ctx.src.side != owner.side) else None)
            return
        self.unsup['effect: ' + rest[:60]] += 1

    def chain(self, owner, eff, ctx):
        tg = self.resolve(owner, eff['target'], ctx)
        if not tg:
            return
        m = owner.mods()
        val = {'atk': self.atk_stat(owner, ctx), 'hp': owner.maxhp, 'def': self.def_stat(owner)}[eff['stat']]
        for v in tg:
            if v.side == owner.side or v.dead:
                continue
            de = self.def_stat(v)
            dr = de / (de + _rules.DEF_K)
            dr = max(0.0, dr - dr * min(1.0, m['pen']))
            inc = m['inc'] + m['inc_vs'].get(v.element, 0.0)
            dmg = max(1.0, math.floor(val * eff['coef'] * (1 + inc) * _rules.BASE_MULT * (1 - dr) * self.rand()))
            self.apply_damage(owner, v, dmg, 'chain', shieldable=True)

    # ---------- 효과 부여
    def roll_hit(self, owner, ctx, x, name):
        """{효과 적중 판정}: 면역이면 실패, 아니면 databook calcHit 확률로 굴림"""
        if name is not None and name in getattr(x.d, 'immune', ()):
            return False
        hit = owner.d.stats.get('eh', 10000) / 10000.0 + owner.d.passive['eh'] + owner.mods()['eh']
        if ctx is not None and ctx.src is owner:
            hit += ctx.eh
        xm = x.mods()
        a = hit - (x.d.stats.get('er', 0) / 10000.0 + xm['er'])
        if owner.element and x.element:
            if ELEM_BEATS.get(owner.element) == x.element:
                a += _rules.ELEM_HIT
            elif ELEM_LOSES.get(owner.element) == x.element:
                a -= _rules.ELEM_HIT
        b = 0.0 - (x.d.stats.get('der', 0) / 10000.0 + xm['der'])
        return self.rng.random() < calc_hit(a, b)

    def apply_buff(self, owner, eff, ctx, hot=0.0, raw=''):
        tg = self.resolve(owner, eff['target'], ctx)
        if not tg:
            return
        if eff['name'] == '강제 협공':
            self.forced_coop(owner, ctx, len(tg))
            return
        if eff.get('consume'):
            for x in tg:
                e = x.eff.get(eff['name'])
                if e:
                    e.stacks = max(0, e.stacks - eff['times'])
                    if e.stacks <= 0:
                        del x.eff[eff['name']]
                    self.dirty(x)
            return
        for x in tg:
            if self.rng.random() >= eff['chance']:
                continue
            self.add_effect(owner, x, eff, ctx, hot=hot, fixed='해제 불가' in raw)

    def add_effect(self, owner, x, eff, ctx, hot=0.0, fixed=False):
        name = eff['name']
        opp = x.side != owner.side
        if opp and ctx is not None and x in ctx.evaded:
            return     # 회피한 대상에는 약화가 걸리지 않음(공식 2026-06-04 오류 수정 공지)
        if opp and x.has('면역'):
            return     # 〈면역〉 (약화효과 면역): 상대가 거는 효과(약화) 전부 막음
        if opp and (eff.get('judge') or name in getattr(x.d, 'immune', ())):
            if not self.roll_hit(owner, ctx, x, name):
                return
        dot = eff.get('dot')
        if dot is None and name in _rules.KNOWN_DOT and not eff['props']:
            dot = _rules.KNOWN_DOT[name]
        harmful = opp
        e = x.eff.get(name)
        dur = _dur(eff['dur'])
        if e is None:
            mx = eff['max'] or (5 if dot else 1)
            e = Eff(name, eff['props'], mx, dur, owner, harmful)
            e.fixed = fixed
            transient = eff['dur'] is None and ctx is not None and ctx.local is not None   # 피격 직전에 받은 지속 표기 없는 효과 = 이번 행동만
            if self.mc['check_buff_expiry'] == 'action' and (transient or (eff['dur'] is None and CHECK_NAME.search(name) and not eff['props'])):
                e.check = True
                self.check_pending.append((x, name))
            x.eff[name] = e
            e.fresh = (x is owner and owner.acting)
        else:
            if eff['dur'] is not None:
                e.dur = max(e.dur, dur) if e.dur != math.inf else e.dur
                if x is owner and owner.acting:
                    e.fresh = True
            e.props = eff['props'] or e.props
            e.src = owner
        if dot:
            e.dot = dot
            if e.inst is None:
                e.inst = []
            for _ in range(eff['times']):
                if len(e.inst) >= e.maxs:
                    e.inst.sort(key=lambda it: it[1])
                    e.inst.pop(0)
                e.inst.append([owner, dur if dur != math.inf else 10 ** 6])
            e.stacks = len(e.inst)
        else:
            e.stacks = min(e.maxs, e.stacks + eff['times'])
        if hot:
            e.hot = hot
        self.dirty(x)

    def forced_coop(self, owner, ctx, n):
        """프로페서M 〈강제 협공〉: 버프 포함 현재 공격력 1위 아군(자신 제외)이 같은 대상에게 기본기. 협공 1명 자리를 차지, 추가 시전에선 없음."""
        if not self.opts['forced_coop'] or ctx is None or ctx.extra or ctx.src is not owner:
            return
        pool = [x for x in self.alive(owner.side) if x is not owner and x.d.skills.get('기본기') is not None
                and not self.incapacitated(x)]
        pool.sort(key=lambda x: (-self.live_atk(x), -x.d.stats['atk'], x.pos))
        for x in pool[:n]:
            ctx.coop_used = True
            self.cast(x, x.d.skills['기본기'], extra=True, target=ctx.target, via='forced_coop')


# ------------------------------------------------------------------ 지원성 검사
# 속성 숫자가 없어도 엔진이 이름으로 동작을 아는 효과
HANDLED_NAMES = set(['도발', '은신', '현장 대기', '기절', '수면', '침묵', '필중', '면역', '강제 협공', '추가 턴', '보호막', '스킬 피해 무효'])
LOCAL_OK = ('피해 증가', '공격력%', '치명타 확률', '치명타 피해', '방어 관통', '효과 적중', '주는 회복량', '명중률')
LOCAL_PREHIT_OK = ('방어력%', '피해 분담(수호)', '피해 감소', '받는 피해 감소')


def _prop_known(k):
    """Unit.mods() 가 이 속성 이름을 어떤 값으로든 반영하는가"""
    probe = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0, coop=0.0, eh=0.0,
                 er=0.0, der=0.0, critred=0.0, guard=0.0, heal_give=0.0, heal_recv=0.0, inc_single=0.0, inc_aoe=0.0,
                 evade=0.0, acc=0.0, inc_vs={}, inc_slot={}, red={})
    before = repr(probe)
    _add_prop(probe, k, 1.0, 1)
    return repr(probe) != before


def _meaning_gap(ln, k, markers):
    """줄이 파싱은 됐지만 엔진이 그 의미(속성·이름)를 실행하지 못하는 경우의 사유. 없으면 None."""
    e = ln.eff
    if e['kind'] == 'local':
        ok = LOCAL_PREHIT_OK if k in ('prehit_self', 'prehit_ally') else LOCAL_OK
        return None if e['stat'] in ok else 'effect: 이번 스킬 한정 보정 미지원 「%s」' % e['stat']
    if e['kind'] != 'buff' or e.get('consume'):
        return None
    name = e['name']
    props = full_props(ln)
    unknown = [p for p in props if not _prop_known(p)]
    if unknown:
        return 'effect: 속성 미지원 %s 〈%s〉' % (','.join(unknown), name)
    tail = re.sub(r'\{[^}]*\}', '', paren_after_name(ln.raw)[1]).strip()
    if tail.startswith('스킬 무효화') and name == '스킬 피해 무효':
        tail = ''
    if tail and not RX_HOT.search(ln.raw) and not e.get('dot') and '보호막 =' not in tail:
        return 'effect: 효과 뒤 문구 미해석 〈%s〉 %s' % (name, tail[:30])
    if (not props and not e.get('dot') and name not in _rules.KNOWN_DOT and name not in HANDLED_NAMES
            and name not in markers and not CHECK_NAME.search(name) and not RX_HOT.search(ln.raw)):
        return 'effect: 의미 미해석 효과 〈%s〉(속성 없음)' % name
    return None


def support_report(defs):
    """전투에 나오는 유닛들의 줄 중 확률 엔진이 실행하지 못하는 것(시점·효과·조건) + 반응/변형 스킬. 실행 전 검사."""
    out = []
    markers = {}
    for d in defs:   # 조건에서 이름으로 확인하는 효과(표지용 버프: 낮의 주기 등)는 속성이 없어도 의미가 있다
        names = set()
        for ln in d.lines:
            for p, v in ln.params:
                if p in ('자신이 보유', '자신이 미보유', '대상이 보유', '대상이 미보유', '시전자가 보유', '턴 유닛이 보유', '특정 효과 보유 적 존재'):
                    names.update(x.strip() for x in v.split(','))
        markers[id(d)] = names
    for d in defs:
        foe = getattr(d, 'is_foe', False)
        for ln in d.lines:
            k = line_kind(ln)
            rest = line_rest(ln)
            reason = None
            if k == 'unmodeled':
                reason = 'trigger: ' + (ln.trig or ln.phase or '')
            elif ln.eff['kind'] == 'ignored' and k != 'ignored' and not any(rx.match(rest) for rx in SPECIAL_RX):
                reason = 'effect: ' + (ln.eff.get('why') or '')
            if not reason and k != 'unmodeled':
                reason = _meaning_gap(ln, k, markers[id(d)])
            tgt = rest.split('에게', 1)[0] if '에게' in rest else ''
            nm = ln.eff.get('name') or ''
            if (not reason and '자동 지정' in tgt and not tgt.startswith('적') and nm != '강제 협공' and ln.eff['kind'] != 'remove'
                    and not (CHECK_NAME.search(nm) or '판별용' in nm) and auto_rule(d, ln, None) is None):
                reason = 'selector: 자동 지정 대상 규칙을 설명문에서 못 찾음(기본 규칙 사용)'
            bad = [p for p, _ in ln.params if p not in COND_KEYS]
            if not reason and bad:
                reason = 'condition: ' + ','.join(bad)
            if reason:
                out.append(dict(unit=d.name, foe=foe, slot=ln.slot, reason=reason, raw=ln.raw,
                                critical=bool(foe and CRITICAL_RX.search(rest) and '강인도' not in rest)))
        for msg in getattr(d, 'unmodeled', []):
            if msg.startswith('변형') or msg.startswith('반응') or msg.startswith('적 트리거'):
                if ('수호의 기사' in msg and getattr(d, 'key', '') == 'wedding-carmen') or ('악에서 악으로' in msg and d.manual == 'profM'):
                    continue    # 엔진이 직접 지원하는 반응 스킬(Battle.reaction_skills / prof_m)
                out.append(dict(unit=d.name, foe=foe, slot=None, reason='skill', raw=msg, critical=False))
    return out
