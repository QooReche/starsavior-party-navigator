# -*- coding: utf-8 -*-
"""P3 확률(몬테카를로) 전투 엔진 — 양 진영 대칭(구원자 4명 vs 스테이지 적 웨이브).

설계 = docs/battlesim_design.md 「P3 상세」. 기대값 엔진(engine.Sim)은 동결(웹 화력 지표·골든 유지)하고, 새 규칙은 여기에만 구현한다.
- 같은 줄 파서(parser.Line)·스킬(Skill)·스탯(calc_stats)·효과 적중 판정(engine.calc_hit)·피해식 상수(rules)를 쓴다.
- 치명·효과 적중·확률 효과·협공·대상 선택·피해 난수를 실제로 굴린다. 중첩은 정수.
- 시간: 시뮬 틱(게이지) / 개체별 행동 횟수(Unit.actions) / 「모델 기준 턴」 = 틱 / turn_ticks(100). 턴 제한은 모델 기준 턴으로 비교.
- 이벤트 한도 초과는 EventLimitError(정상 결과를 돌려주지 않는다).
P3 규칙 값은 rules/default.json 의 "mc" 절(MC_OPTS)."""
import copy
import json
import math
import os
import random
import re
from collections import defaultdict

from . import rules as _rules
from .engine import calc_hit
from .rules import DEFAULT_OPTS, ELEM_BEATS, ELEM_LOSES, MC_OPTS
from .starsavior.data import SRC
from .starsavior.parser import Line, _map_prop, split_head, supported_trigger
from .starsavior.mc_semantics import normalized_lines, normalized_definition, trigger_rule, variant_rules


class EventLimitError(RuntimeError):
    """판당 이벤트 상한(max_events) 초과 — 무한 연쇄 의심. 결과를 돌려주지 않는다."""


# ------------------------------------------------------------------ 자동 전투 대상 규칙(게임 AutoSkillController)
# NKM.decompiled.cs 6561~6587: 스킬에 AutoSkillId 가 없으면 구원자 = 규칙 1, 적 = 규칙 1001. 필터 본문 6786~7130.
# tools/build_auto_skill.py 가 표의 규칙 1·1001 이 아래와 같은지 확인한다(다르면 빌드 실패).
RULE1 = ('not_invincible', 'boss', 'elite', 'advantage', 'low_hp_rate', 'low_max_hp')
RULE1001 = (('front', 0.8), ('defender', 0.8))
_AUTO = {}


def auto_skill_rules(src=SRC):
    """data/auto_skill.json(tools/build_auto_skill.py) -> {구원자 key: {칸: 규칙}}. 없으면 빈 dict"""
    if src not in _AUTO:
        p = os.path.join(src, 'data', 'auto_skill.json')
        _AUTO[src] = {}
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                _AUTO[src] = json.load(f).get('units', {})
    return _AUTO[src]


# ------------------------------------------------------------------ 줄 분류(반응 트리거)
# parser.trig_kind 가 'unmodeled' 로 두는 피격·사망 등 반응 시점을 확률 엔진에서만 해석한다(기대값 엔진·웹 출력 불변).
REACT_TRIG = [
    ('내가 피격될 때', 'hit_self'), ('피격 시', 'hit_self'),
    ('내가 피해를 받기 직전', 'prehit_self'), ('내가 피해 받기 직전', 'prehit_self'),
    ('아군이 피격될 때', 'hit_ally'), ('아군이 피해 받기 직전', 'prehit_ally'), ('아군이 피해를 받기 직전', 'prehit_ally'),
    ('적 공격 시', 'foe_pre'), ('적 공격 후', 'foe_post'), ('적 비공격 스킬 시', 'foe_pre_na'), ('적 비공격 스킬 후', 'foe_post_na'),
    ('내가 사망할 때', 'death_self'), ('아군 사망 시', 'death_ally'), ('적 사망 시', 'death_enemy'),
    # P5: 「행동」 시점(공격·비공격 구분 없음) — 잠재력 24줄·마르실/페트라 3줄
    ('내 행동 시', 'own_pre'), ('내 행동 후', 'own_post'), ('아군 행동 시', 'ally_pre'), ('아군 행동 후', 'ally_post'),
    ('적 행동 후', 'foe_post_any'),
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
COND_KEYS = set(['사용 스킬', '추가발동 스킬', '추가발동 스킬이 아님', '자기 추가발동 트리거', '자기 추가발동 트리거 스킬',
                 '자신 미보유 효과 중첩수', '시전자 턴', '자신이 보유', '자신이 미보유',
                 '중첩수', '효과 개수', '중첩수 이상', '효과 개수 이상', '효과 개수 미만', '대상이 보유', '대상이 미보유',
                 '대상 효과 중첩수', '대상 약화효과 보유', '대상 강화효과 보유', '대상 강인도 없음', '대상 브레이크', '결과',
                 '대상 HP% 초과', '대상 HP% 미만', '적 처치', '적을 처치하지 못함', '내 턴', '자신 포함', '시전자 속성', '시전자가 보유',
                 '자신에게 약화효과 없음', '자신 약화효과 보유', '자신 강화효과 보유', '스킬 쿨타임 아님', '턴 유닛이 보유',
                 '스킬 대상 유형', '단일 대상 공격', '대상 속성', '적 약화효과 보유', '적 강화효과 보유', '특정 효과 보유 적 존재',
                 '턴 유닛 속성', 'EnemyAdjustType', 'NotEnemyAdjustType', 'IsTargetSuperArmor',
                 '피해 증가(조건부)', 'NotTargetPositiveBuff', 'NotEnemyPositiveBuff', 'ExistAllySpecificBuff', '이번 타격 격파', '대상 클래스'])

# 회복·보호막·부활·해제·무작위 효과 원문 해석(parser 는 이 줄들을 'ignored' 로 둔다)
RX_HEAL = re.compile(r'^(.+?)에게 회복 = (자신|대상) (최대 생명력|생명력|공격력|방어력)×([\d.]+)%')
RX_SHIELD = re.compile(r'^(.+?)에게 〈([^〉]+)〉\s*\((\d+턴|지속 무한)(?:\s*/\s*([^)]*))?\)\s*보호막 = 자신 (생명력|공격력|방어력)×([\d.]+)%')
RX_REVIVE = re.compile(r'^(.+?)에게 부활\(생명력 (\d+)%\)')
RX_HOT = re.compile(r'‹턴마다 회복: 대상 최대 생명력×([\d.]+)%›')
RX_DISPEL = re.compile(r'^(.+?)에게 (?:\(대상마다 (\d+)% 판정\) )?〈[^〉]+〉\s*\((?:\d+턴 / )?(약화|강화)효과 해제\)')
RX_DISPEL_N = re.compile(r'^(.+?)에게 (?:(\d+)% 확률로 )?\((약화|강화)효과 해제\) 효과 (\d+)개 해제')
# P5 적 효과(대표 스테이지에서 자주 나오는 것)
RX_GAUGE_SET = re.compile(r'^(.+?)에게 행동 게이지를 (\d+)%로 설정')
RX_CHAIN_T = re.compile(r'^(.+?)에게 연쇄 피해 = 대상 (최대 생명력|생명력)×([\d.]+)% \(×1\.85, 방어력 적용\)(?: ×(\d+))?')
RX_CD_UP = re.compile(r'^(.+?)에게 스킬 쿨타임 (\d+)턴 증가')
RX_LOCAL_PER = re.compile(r'^자신에게 능력치 보정 피해 증가 ([+-]?[\d.]+)% \((자신|적 전체|공격 대상|아군 전체)의 (강화|약화) 효과 1개당 위 수치만큼 적용, 개수 상한 없음\)')
CD_RESET_NAMES = {'궁극기 쿨타임 초기화': '궁극기', '특수기 쿨타임 감소': '특수기'}   # 설명문 「쿨타임이 초기화」·「최대로 감소한 상태로 시작」
RX_RANDOM = re.compile(r'^(.+?)에게\s*(?:\(대상마다 (\d+)% 판정\)\s*)?무작위 효과 〈[^〉]+〉: \[(.+)\] 중 1개')
RX_RECV_HEAL = re.compile(r'^(.+?)에게 능력치 보정 받는 회복량 ([+-][\d.]+)%')
RX_GAUGE_P = re.compile(r'^(.+?)에게 (\d+)% 확률로 행동 게이지 ([\d.]+)%p (증가|감소)')
RX_EXTRA_P = re.compile(r'^자신에게 (\d+)% 확률로 (기본기|특수기|궁극기) 추가 발동')
RX_RECAST = re.compile(r'발동 후 (\d+)턴 재발동 불가')
RX_TOUGH_HEAL = re.compile(r'^(.+?)에게 강인도 (\d+) 회복')          # P5: 「자신에게 강인도 N 회복」(적 42줄)
RX_HEAL_P = re.compile(r'^(.+?)에게 (\d+)% 확률로 회복 = (자신|대상) (최대 생명력|생명력|공격력|방어력)×([\d.]+)%')   # 잠재력 BX 「25% 확률로 회복」
RX_NOVA = re.compile(r'^(.+?)에게 노바 포스 ([+-]\d+)(?:\s|$)')
SPECIAL_RX = (RX_SHIELD, RX_HEAL, RX_REVIVE, RX_DISPEL, RX_DISPEL_N, RX_RANDOM, RX_RECV_HEAL, RX_GAUGE_P, RX_EXTRA_P, RX_TOUGH_HEAL,
              RX_HEAL_P, RX_GAUGE_SET, RX_CHAIN_T, RX_CD_UP, RX_LOCAL_PER, RX_NOVA)
# P5 「피해 제한」: 효과마다 설명문에 적힌 동작을 그대로(일반화하지 않는다 — codex 설계 상담). 여기 없는 「피해 제한」 효과는 미지원(적이면 중요 미지원).
#  floor  = 한 번의 피해로 현재 생명력이 pct 아래로 내려가지 않음(로자리아 「대미지 브레이크」: 「현재 생명력이 40% 이하로 떨어지지 않습니다 … 전투 중 1회」)
#  lethal = 사망에 이르는 피해 -> 최대 생명력 keep 만큼 남기고 〈불사〉 n턴(적 「불사의 육신」·카넬리아 「바큇살」 설명문)
DAMAGE_LIMIT = {
    '대미지 브레이크': dict(kind='floor', pct=0.40, once=True, grade='data'),
    '불사의 육신': dict(kind='lethal', keep=0.01, undying=1, once=True, grade='assumed(1회 소모)'),
    '바큇살': dict(kind='lethal', keep=0.01, undying=1, once=True, grade='data', then=[('칠흑의 잔향(해제불가)', 3, {'공격력%': 20.0, '효과 저항': 20.0})],
                 reset_cd=True),
}


def line_rest(ln):
    """줄에서 시점·조건 머리를 뗀 효과 문장"""
    return split_head(ln.raw, decimal_hp=True)[2].strip()


def heal_burst_rank(d, sk):
    """2=슬롯별 노바가 회복/보호막 추가·강화, 1=기본 회복/보호막, 0=대상 아님.

    공격 스킬도 노바로 회복이 붙으면 포함. 강인도 회복·보호막 조건·패시브/반응은 제외.
    조건부 회복은 스킬의 성격으로 판정하고 실제 조건/확률은 시전 중 기존 엔진이 평가한다.
    """
    if sk.ty != '액티브':
        return 0

    def lines(raws):
        return [ln for raw in raws for ln in [Line(raw, sk.slot, 'active')]
                if line_kind(ln) in ('own_pre', 'own_post', 'before_heal')]

    def restores(ln):
        rest = line_rest(ln)
        return bool(RX_HEAL.match(rest) or RX_HEAL_P.match(rest) or RX_SHIELD.match(rest) or RX_HOT.search(rest))

    base = bool(sk.raw.get('hl')) or any(restores(ln) for ln in lines(sk.raw.get('ef') or []))
    for ln in lines(getattr(d, 'nb', {}).get(sk.slot + ' 사용 시') or []):
        eff = ln.eff
        bonus = (eff.get('kind') == 'local' and eff.get('stat') in ('주는 회복량', '받는 회복량')
                 and eff.get('val', 0) > 0)
        recv = RX_RECV_HEAL.match(line_rest(ln))
        if restores(ln) or (base and (bonus or (recv and float(recv.group(2)) > 0))):
            return 2
    return int(base)


RX_HP_COND = re.compile(r'\(자신 HP ([\d.]+)% (이상|이하|미만)')
CHECK_NAME = re.compile(r'확인용|체크용|카운팅|확인 용')
HARD_CC = ('기절', '수면')
UNTARGETABLE = ('은신', '현장 대기')
CRITICAL_RX = re.compile(r'피해 감소|보호막|회복|부활|불사|무효|면역|피해 제한|분담')


def _dur(v):
    return math.inf if v is None else v


TARGET_KEYS = set(['대상 속성', '대상 클래스', '대상이 보유', '대상이 미보유', '대상 HP% 초과', '대상 HP% 미만', '대상 약화효과 보유',
                   '대상 강화효과 보유', '대상 효과 중첩수', 'NotTargetPositiveBuff'])


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
                return sk.get('dx') or sk.get('d1') or ''
    return (getattr(d, 'desc', None) or {}).get(slot, '')


_ELEM = '(태양|달|별|질서|혼돈)'


def auto_rule(d, ln, kind):
    """자동 지정 대상 규칙을 스킬 설명문에서 읽는다 -> dict(mode, excl_self, element) 또는 None(못 찾음)"""
    desc = ((getattr(d, 'nb', {}).get('desc') or {}).get(ln.slot, '')
            if ln.src_kind == 'nova' else skill_desc(d, ln.slot))
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
                 'check', 'fixed', 'clock', 'category')

    def __init__(self, name, props, maxs, dur, src, harmful):
        self.name, self.props, self.maxs, self.dur, self.src, self.harmful = name, props, maxs, dur, src, harmful
        self.category = 'debuff' if harmful else 'buff'
        self.stacks = 0
        self.fresh = False
        self.shield = 0.0
        self.dot = None      # (stat, coef)
        self.inst = None     # 지속 피해 중첩별 [시전자, 남은 턴]
        self.hot = 0.0       # 턴마다 회복 계수(대상 최대 생명력 비율)
        self.check = False   # 확인용 버프(행동 끝에 사라짐)
        self.fixed = False   # 해제 불가
        self.clock = 'owner_turn'   # 영역은 파티 공용 ally_turn/round 로 차감


class Unit:
    def __init__(self, d, side, pos, b, leader=False, fx=None):
        d = normalized_definition(d)
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
        frac = b.mc['enemy_init_cd'] if side == 1 else b.mc['ally_init_cd']
        # 적 시작 쿨: 배치 표시(게임 코드 — AllSkillAvailable 이면 전부 0, 아니면 전부 가득, Special/Hyper 는 그 스킬만 0).
        # 표시가 없는 스테이지는 등급 규칙(보스 S, 그 밖 A — 배치 2만여 기 중 95% 가 이 꼴). legacy = 옛 규칙(enemy_init_cd*)
        code = None
        if side == 1 and b.mc.get('enemy_spawn', 'data') == 'data':
            code = getattr(d, 'spawn', None) or ('S' if getattr(d, 'boss', False) else 'A')
        for slot, sk in d.skills.items():
            if code is not None:
                zero = code == 'A' or (slot == '특수기' and code in 'SB') or (slot == '궁극기' and code in 'HB')
                f = 0.0 if zero else 1.0
            else:
                f = b.mc['enemy_init_cd_special'] if side == 1 and slot == '특수기' else frac
            self.cd[slot] = (sk.cd * f) if sk.cd else 0
            # legacy 근사에서만 시작 감소를 보완하는 +1을 적용함.
            # 적의 고유 턴 종료 방식은 표시된 쿨타임을 그대로 저장함.
            if (side == 1 and self.cd[slot] > 0 and b.mc['enemy_cd_tick'] == 'turn_end'
                    and not b.mc['enemy_cd_native']):
                self.cd[slot] += 1
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
        self.sa_max = int(st.get('sa') or 0)    # P5 강인도(적 b[9]+변형 보정, 구원자 3/코즈믹 5 + 잠재력)
        self.sa = self.sa_max
        self.broken = False
        self.breaks = 0
        self._m = None

    # ---- 버프 합산(캐시: 효과가 바뀌면 b.dirty())
    def mods(self):
        if self._m is not None:
            return self._m
        m = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0, coop=0.0, eh=0.0, er=0.0,
                 der=0.0, critred=0.0, guard=0.0, heal_give=0.0, heal_recv=0.0, inc_single=0.0, inc_aoe=0.0, evade=0.0, acc=0.0,
                 tough=0.0, tough_fixed=0.0, inc_break=0.0, revenge=0.0, inc_vs={}, inc_slot={}, red={})
        blocked = '강화 불가' in self.eff and self.eff['강화 불가'].stacks > 0   # 〈강화 불가〉: 모든 강화 효과가 적용되지 않음(gloss)
        for e in self.eff.values():
            if e.stacks <= 0 or (blocked and e.category == 'buff'):
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

    def buff_blocked(self):
        """〈강화 불가〉: 지속 동안 모든 강화 효과가 적용되지 않음(gloss) — 수치(mods)·이름으로 동작하는 강화(불사·면역·은신·보호막 …) 모두"""
        e = self.eff.get('강화 불가')
        return e is not None and e.stacks > 0

    def on(self, name):
        """그 효과가 지금 작동하는가: 있음 + (약화이거나 〈강화 불가〉 상태가 아님)"""
        e = self.eff.get(name)
        if e is None or e.stacks <= 0:
            return False
        return e.category != 'buff' or not self.buff_blocked()

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
        # Native negative-buff counts enumerate live buff objects, not names.
        # IsUniqueID DoTs have one object per application (NKM:4123-4139).
        # Level stacks on a single non-DoT buff must still count only once.
        return sum(len(e.inst) if self.b.mc['debuff_instance_count'] and e.inst is not None else 1
                   for e in self.eff.values() if e.category == 'debuff' and e.stacks > 0 and not e.check)

    def n_good(self):
        return sum(1 for e in self.eff.values() if e.category == 'buff' and e.stacks > 0 and not e.check)


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
    elif k == '강인도 피해':            # P5: 정수(타격마다 +N)
        m['tough'] += v * stacks
    elif k == '강인도 고정 피해':
        m['tough_fixed'] += v * stacks
    elif k == '브레이크 대상 피해 증가':
        m['inc_break'] += val
    elif k in ('받는 피해 감소', '피해 감소'):
        m['red']['all'] = m['red'].get('all', 0.0) + val
    elif k == '전체 대상 피해 감소':
        m['red']['aoe'] = m['red'].get('aoe', 0.0) + val
    elif k == '단일 대상 피해 감소':
        m['red']['single'] = m['red'].get('single', 0.0) + val
    elif k == '반격 확률':                 # NST_RATE_REVENGE_ATTACK(〈반격 증가〉·〈경계 모드〉·〈강화 반격〉)
        m['revenge'] += val
    else:
        mm = re.match(r'^(기본기|특수기|궁극기) 피해 감소$', k)
        if mm:
            m['red'][mm.group(1)] = m['red'].get(mm.group(1), 0.0) + val


class Ctx:
    """시전 1회(또는 피격 반응 1회)의 문맥. owner = 줄 주인, src = 시전자(공격자), skill = 시전 스킬, target = 대상."""
    __slots__ = ('owner', 'src', 'skill', 'extra', 'targets', 'target', 'inc', 'atkp', 'cr', 'cd', 'pen', 'eh', 'crit',
                 'kill', 'coop_used', 'heal_give', 'heal_recv', 'local', 'nb', 'hit_victim', 'acc', 'evaded', 'recv_by',
                 'local_by', 'tough', 'tough_fixed', 'inc_break', 'force_crit', 'via', 'parent', 'hit_targets',
                 'crit_targets', 'break_targets', 'markers', 'dead_targets', 'tough_targets')

    def __init__(self, owner, src, skill, extra=False):
        self.owner, self.src, self.skill, self.extra = owner, src, skill, extra
        self.via, self.parent = None, None
        self.hit_targets = []    # 실제 피해 처리한 개체: 사망/회피도 포함, 다단 히트는 한 명
        self.crit_targets, self.break_targets = set(), set()
        self.tough_targets = set()  # video: 시전·대상당 1회. 추가 발동은 별도 Ctx.
        self.markers = {}
        self.dead_targets = set()
        self.targets, self.target = [], None
        self.inc = self.atkp = self.cr = self.cd = self.pen = self.eh = self.acc = 0.0
        self.tough = self.tough_fixed = self.inc_break = 0.0   # P5 「이번 스킬에만」 강인도 (고정) 피해·브레이크 대상 피해 증가
        self.force_crit = False
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
                 timeline=False, enemy_lines=True, max_turns=50, pen=None, break_skill=None, rng_streams=False):
        self.pen = tuple(pen) if pen else (1.0, 1.0)    # P5 전투력 보정(아군이 주는 피해 배율, 적이 주는 피해 배율) — 스킬·지속·연쇄만
        self.opts = dict(DEFAULT_OPTS)
        self.opts.update(opts or {})
        self.mc = dict(MC_OPTS)
        self.mc.update(mc or {})
        self.rng = rng
        # 공통 난수(선택): 아군 쪽(0)·적 쪽(1) 결정에 서로 다른 흐름을 쓴다. 같은 판 번호면 적의 대상 선택·치명 등이
        # 아군 행동 수와 무관하게 같은 순서로 나와 팀끼리 비교할 때 운의 차이가 줄어든다(예선 전용, 기본 꺼짐)
        self._rs = None
        if rng_streams:
            base = rng.getrandbits(64)
            self._rs = (random.Random(base * 2 + 1), random.Random(base * 2 + 2))
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
        self.enemy_nova = 0.0
        self.nova_bursts = defaultdict(int)  # (아군 칸, 슬롯)별 실제 사용 횟수
        self.unsup = defaultdict(int)
        self.timeline = [] if timeline else None
        self.enemy_lines = enemy_lines
        self.result = None
        self.clear_t = None
        self.check_pending = []
        self.first_death = None
        self.death_seq = 0
        self._hit_log = None      # 이번 행동의 유효 타격 [(공격자, 피격자)] — 반격 후보(mc.revenge)
        self.revenges = [0, 0]    # 진영별 반격 횟수
        self.all_foes = []
        self._cur_line = None    # 실행 중인 줄(자동 지정 대상 규칙을 그 스킬 설명에서 찾을 때 씀)
        self.once = set()        # {전투당 1회} 줄 사용 기록
        self.recast = {}         # {발동 후 N턴 재발동 불가} 줄: (주인, 줄) -> 발동한 때의 주인 행동 횟수
        self._semantic_lines = {}
        self._triggering = set()  # 쿨이 없는 트리거도 동일 시전 중 재진입 방지
        self.break_skill = dict(break_skill or {})
        self.break_skill_name = self.break_skill.get('name')
        self.break_skill_rule = self._break_skill_rule(self.break_skill_name)
        self.break_skill_enabled = self.break_skill_rule is not None
        self.break_points = self.break_points_gained = self.break_skill_uses = 0
        self.break_skill_dmg = 0
        self.break_skill_cd = 0
        self._break_round = 0
        if self.break_skill_name and not self.break_skill_enabled:
            self.unsup['break_skill:' + self.break_skill_name] += 1
        if self.break_skill_enabled and self.mc['break_skill_cd_unit'] not in ('ally_turn', 'round'):
            raise ValueError('break_skill_cd_unit 은 ally_turn|round')

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
        key = id(u.d)
        cached = self._semantic_lines.get(key)
        if cached is None or cached[0] is not u.d.lines or cached[1] != len(u.d.lines):
            cached = (u.d.lines, len(u.d.lines), normalized_lines(u.d))
            self._semantic_lines[key] = cached
        return cached[2]

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
                for ln in self.lines_of(u):
                    if line_kind(ln) == 'wave_start':
                        self.run_line(u, ln, Ctx(u, u, None))

    def progress(self):
        """적 진척도 0~1: (끝낸 웨이브 + 현재 웨이브에서 깎은 체력 비율) / 웨이브 수. 클리어면 1"""
        if self.result == 'clear':
            return 1.0
        if not self.waves or self.wave_i < 0:
            return 0.0
        tot = sum(u.maxhp for u in self.foes) or 1.0
        cur = sum(u.maxhp - max(0.0, u.hp) for u in self.foes) / tot
        return (self.wave_i + min(1.0, max(0.0, cur))) / len(self.waves)

    def run(self):
        if self.wave_i < 0:   # 시험에서 미리 첫 웨이브를 불러 상태를 만든 경우는 건너뜀
            self.spawn_wave()
            for u in self.allies:
                for ln in self.lines_of(u):
                    if line_kind(ln) in ('battle_start', 'wave_start'):
                        self.run_line(u, ln, Ctx(u, u, None))
        # 턴 제한 단위: actions = 게임 전역 턴(유닛 행동마다 +1, 적 포함 — NKM.decompiled.cs 13796~13798·599~623·755~762,
        # 코스모 게이트 = RANKING_RAID LimitTurn 50·CountEnemyTurnOnly false). model = 옛 동작(모델 기준 턴 = 100틱)
        by_actions = bool(self.turn_limit) and self.mc['turn_limit_unit'] == 'actions'
        horizon = (self.turn_limit if (self.turn_limit and not by_actions) else self.max_turns) * self.turn_ticks
        self.global_turns = 0
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
            round_tick = False
            if self.break_skill_enabled and self.mc['break_skill_cd_unit'] == 'round':
                boundary = (self._break_round + 1) * self.turn_ticks
                if boundary <= self.t + bt + 1e-9 and boundary <= horizon:
                    # 영역 만료 순간부터 새 속도로 게이지를 쌓도록 시간 진행을 나눈다.
                    bt = max(0.0, boundary - self.t)
                    round_tick = True
            if self.t + bt > horizon + 1e-9:
                self.result = 'timeout'
                break
            for x in living:
                self.set_gauge(x, x.gauge + x.spd() * bt)
            self.t += bt
            if round_tick:
                self._break_round += 1
                self._tick_break_skill()
                continue
            if by_actions and self.global_turns >= self.turn_limit:
                self.result = 'timeout'   # 게임: 전역 턴이 제한을 넘는 턴은 시작하지 않고 전투 종료
                break
            self.global_turns += 1
            self.act(best)
        return self

    def set_gauge(self, u, value):
        """Gauge buffs may exceed 100%; overflow orders already-ready actors.

        NKM.decompiled.cs:3323-3330 (lower clamp only), 4648-4675
        (buff changes), 12309-12317 (descending gauge), 13821 (actor reset).
        """
        u.gauge = max(0.0, value)
        if not self.mc['gauge_overflow']:
            u.gauge = min(10000.0, u.gauge)

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
        if u.side == 0 and self.break_skill_enabled:
            if self.mc['break_skill_cd_unit'] == 'ally_turn':
                self._tick_break_skill()
            self._use_break_skill(u)
            if not self.alive(0) or not self.alive(1):
                # 일반 공격 뒤와 동일하게 run에서 종료/웨이브 전환을 판정한다.
                # 브레이크는 일반 턴 밖의 행동이므로 게이지·쿨·지속 효과를 소비하지 않는다.
                return
        u.gauge = 0.0
        u.extra_turn = False      # 추가 턴은 이 행동으로 소비(행동 끝에 지우면 다음 차례 판정에서 우선권이 사라짐)
        u.actions += 1
        u.acting = True
        skip = False
        if u.broken:
            # 브레이크(강인도 격파)는 그 유닛의 다음 자기 턴 시작에 끝나고 강인도 전회복, 그 턴은 정상 행동(mc.break_recover, assumed)
            # 구원자 + ally_break_gauge=skip: 게이지는 그대로 두었다가, 자기 턴이 오면 회복하는 데 그 턴을 쓴다(행동 없음)
            # — 사용자 인게임 설명 2026-10-21 「브레이크돼도 턴은 안 밀리는데, 자기 턴 왔을 때 회복되고 턴이 밀린다」
            skip = u.side == 0 and self.mc['ally_break_gauge'] == 'skip'
            u.broken = False
            u.sa = u.sa_max
            self.dirty(u)
            self.log(recover=u.name, skip=skip)
        if self.mc['shield_tick'] == 'turn_start':
            self._tick_shields(u)
        end_cd = (u.side == 1 and self.mc['enemy_cd_tick'] == 'turn_end'
                  and self.mc['enemy_cd_native'])
        if not end_cd:
            self._tick_cooldowns(u)
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
        # 회복 턴도 턴 이벤트·지속 차감은 처리하고, 스킬 행동만 생략한다.
        if self.mc['revenge'] == 'on':
            self._hit_log = []
        if not u.dead and not skip:
            if any(u.has(n) for n in HARD_CC):
                self.log(actor=u.name, skip='행동 불가')
            else:
                taunt = u.eff.get('도발')
                tsrc = taunt.src if (taunt and taunt.stacks > 0) else None
                if tsrc is not None and not tsrc.dead and u.d.skills.get('기본기') is not None:
                    self.cast(u, u.d.skills['기본기'], target=tsrc)
                else:
                    sk, tgt = self.choose_skill(u)
                    if sk is not None:
                        self.cast(u, sk, target=tgt)
        if self._hit_log:
            self.revenge(self._hit_log)   # 반격에서 이어진 공격(반응·추가 발동)의 타격도 같은 목록에 쌓여 차례로 판정
        self._hit_log = None
        if not u.dead:
            if end_cd:
                # NKM:1840-1848 -> 3348-3360: owner action end, before
                # NSEAT_TURN_END, including the skill just used this turn.
                self._tick_cooldowns(u)
            self.fire(u, 'own_te', Ctx(u, u, None))
            for name in list(u.eff):
                e = u.eff[name]
                if e.clock != 'owner_turn':
                    continue
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

    @staticmethod
    def _tick_cooldowns(u):
        for slot in u.cd:
            u.cd[slot] = max(0.0, u.cd[slot] - 1)

    def _tick_break_skill(self):
        """공용 쿨·영역 차감. 발동 턴에는 차감하지 않고 다음 단위 경계부터 센다."""
        self.break_skill_cd = max(0, self.break_skill_cd - 1)
        for u in self.allies:
            for name, e in list(u.eff.items()):
                if e.clock == self.mc['break_skill_cd_unit']:
                    e.dur -= 1
                    if e.dur <= 0:
                        del u.eff[name]
                    self.dirty(u)

    def _break_skill_rule(self, name):
        """큐브의 기존 평면 규칙/override 계약은 유지하며 신규 표와 같은 모양으로 읽는다."""
        if name == '큐브 과부하':
            return dict(heal_ratio=self.mc['break_skill_heal_ratio'], domain='치트 매트릭스',
                        props={'속도%': self.mc['break_skill_speed_pct']},
                        bonus_roles=('디펜더', '서포터'), role_props={'속도%': self.mc['break_skill_role_speed_pct']},
                        domain_turns=self.mc['break_skill_domain_turns'], buff='오메가 프로토콜',
                        buff_props={'공격력%': self.mc['break_skill_atk_pct'], '효과 적중': self.mc['break_skill_hit_pct']},
                        buff_turns=self.mc['break_skill_buff_turns'])
        return self.mc['break_skills'].get(name)

    def _break_dmg(self, v, base):
        """파티 광역 피해: 공격자·치명·증가 합·피격/강인도 처리 없는 final_dmg 축약판."""
        de = self.def_stat(v)
        dr = de / (de + _rules.DEF_K)
        red = v.mods()['red']
        dec = red.get('all', 0.0) + red.get('aoe', 0.0)
        if v.broken:
            dec -= _rules.BREAK_DEC
        dec = min(_rules.DEC_CAP, dec)
        return max(1.0, math.floor(base * (1 - dr) * (1 - dec) * self.rand(0) * self.pen[0]))

    def _use_break_skill(self, actor=None):
        cost = self.mc['break_skill_cost']
        if not self.break_skill_enabled or self.break_skill_cd > 0 or self.break_points < cost:
            return
        self.break_points -= cost
        self.break_skill_cd = self.mc['break_skill_cooldown']
        self.break_skill_uses += 1
        self.log(bskill=self.break_skill_name)
        rule = self.break_skill_rule
        if rule.get('damage_ratio'):
            base = sum(self.live_atk(u) for u in self.alive(0)) * rule['damage_ratio'] / _rules.AOE_DIV
            for v in list(self.alive(1)):
                before = v.taken
                self.apply_damage(None, v, self._break_dmg(v, base), 'bskill')
                dmg = v.taken - before
                self.break_skill_dmg += dmg
                self.log(bskill_damage=self.break_skill_name, to=v.name, amount=dmg)
        nova = rule.get('nova', 0)
        if self.opts['nova_pool'] == 'team':
            self.team_nova += nova
        # 큐브 회복의 합에는 사망자도 포함(기존 가정). 효과는 생존자에게만.
        amount = sum(u.maxhp for u in self.allies) * rule.get('heal_ratio', 0)
        for u in self.alive(0):
            if 'heal_ratio' in rule:
                got = self.heal(None, u, amount, 0.0)
                self.log(heal=self.break_skill_name, to=u.name, amount=got)
            if self.opts['nova_pool'] == 'unit':
                self.nova_add(u, nova)
            if u is not actor and rule.get('gauge'):
                self.set_gauge(u, u.gauge + rule['gauge'])
            props = dict(rule['props'])
            if u.role in rule.get('bonus_roles', ()):
                for k, v in rule['role_props'].items():
                    props[k] = props.get(k, 0) + v
            effects = []
            if rule.get('buff'):
                effects.append((rule['buff'], rule['buff_props'], rule['buff_turns'], 'owner_turn'))
            effects.append((rule['domain'], props, rule['domain_turns'], self.mc['break_skill_cd_unit']))
            for name, props, dur, clock in effects:
                e = Eff(name, props, 1, dur, None, False)
                e.stacks, e.fixed, e.clock = 1, self.mc['break_skill_fixed'], clock
                u.eff[name] = e
            self.dirty(u)

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
        """(스킬, 미리 고른 대상 또는 None). 게임 자동 전투(NKM.decompiled.cs 6360~6390·6588~6620): 침묵이면 기본기,
        아니면 궁극기 -> 특수기 -> 기본기 중 쿨이 찼고 규칙 행(data/auto_skill.json)의 조건이 맞고 대상이 있는 첫 스킬.
        다 안 되면 기본기(조건 무시). auto_skill=off 는 옛 동작(쿨만 보고, 침묵이면 쿨 있는 스킬만 건너뜀)."""
        silenced = u.has('침묵')
        table = self.mc['auto_skill'] == 'data'
        if silenced and table:
            return u.d.skills.get('기본기'), None
        specs = {}
        if table and u.side == 0:
            # 개화 변형(key@...)은 규칙이 기본 키에 있다(비공개 표에서 변형 스킬도 같은 AutoSkillId 확인)
            rules = auto_skill_rules()
            specs = rules.get(u.key) or rules.get(u.key.split('@')[0], {})
        for slot in ('궁극기', '특수기', '기본기'):
            sk = u.d.skills.get(slot)
            if sk is None or u.cd.get(slot, 0) > 0:
                continue
            if silenced and sk.cd:
                continue
            spec = specs.get(slot)
            if spec is None or spec.get('react'):
                return sk, None
            for row in spec['rows']:
                if all(self.auto_cond_ok(u, c) for c in row['c']):
                    if spec['t'] != 'ally_one':
                        return sk, None
                    v = self.auto_pick_ally(u, row['f'])
                    if v is not None:
                        return sk, v
                    break
        return u.d.skills.get('기본기'), None

    def auto_cond_ok(self, u, c):
        if c[0] == 'ally_hp_le_bp':
            return any(int(v.hp / v.maxhp * 10000) <= c[1] for v in self.alive(u.side))
        if c[0] == 'ally_dead':
            return any(v.dead for v in self.side_units(u.side))
        if c[0] == 'self_stack_eq':
            return u.stack(c[1]) == c[2]
        raise ValueError('auto_skill 조건 미지원: %r' % (c,))

    def auto_pick_ally(self, u, steps):
        """아군 단일 스킬의 주 대상(게임 대상 필터). 후보 = 살아 있는 아군, dead_ally 는 마지막으로 쓰러진 아군으로 바꾼다."""
        pool = self.alive(u.side)
        if not pool:
            return None
        return self.filter_pick(u, pool, steps)

    def filter_pick(self, att, pool, steps):
        """게임 대상 필터 사슬(NKM.decompiled.cs 6500~6536): 차례로 거르고, 결과가 0명이면 목록 유지, 1명이 되면 멈춤, 끝에 여럿이면 무작위.
        확률 필터((이름, p))는 주사위가 성공할 때만 거른다. 무적(not_invincible)은 엔진에 무적 상태가 없어 거르지 않는다."""
        rng = self.R(att.side)
        for st in steps:
            if isinstance(st, tuple):
                st, p = st
                if rng.random() >= p:
                    continue
            got = self._filter(att, pool, st)
            if got:
                pool = got
                if len(pool) == 1:
                    return pool[0]
        return pool[0] if len(pool) == 1 else rng.choice(pool)

    def _filter(self, att, pool, st):
        if st == 'not_invincible':
            return None
        if st == 'boss':
            return [v for v in pool if getattr(v.d, 'boss', False)]
        if st == 'elite':
            return [v for v in pool if getattr(v.d, 'grade', '') == '정예']
        if st == 'advantage':
            good = [v for v in pool if att.element and ELEM_BEATS.get(att.element) == v.element]
            return good or [v for v in pool if not (att.element and ELEM_BEATS.get(v.element) == att.element)]
        if st in ('low_hp_rate', 'low_max_hp'):
            key = (lambda v: int(v.hp / v.maxhp * 10000)) if st == 'low_hp_rate' else (lambda v: v.maxhp)
            best = min(key(v) for v in pool)
            return [v for v in pool if key(v) == best]
        if st == 'not_self':
            return [v for v in pool if v is not att]
        if st == 'dead_ally':
            dead = [v for v in self.side_units(att.side) if v.dead]
            return [max(dead, key=lambda v: getattr(v, 'death_n', 0))] if dead else None
        if st == 'front':
            return [v for v in pool if v.pos < 2]
        if st == 'defender':
            return [v for v in pool if v.role == '디펜더']
        raise ValueError('auto_skill 필터 미지원: %r' % (st,))

    # ---------- 대상
    def targetable(self, side):
        al = self.alive(side)
        ok = [u for u in al if not any(u.on(n) for n in UNTARGETABLE)]
        return ok or al

    def ranked_enemies(self, desc, pool, priority=False):
        """공격 우선 문구와 효과 자동 지정의 순위 계산을 공유. 동률 후보는 유지한다."""
        suffix = r'(?:을|에게)?\s*우선' if priority else ''
        # 긴 조건을 먼저 매칭해 최대 생명력/HP를 현재 HP로 잘못 읽지 않는다.
        rank = re.search(r'(?<!\w)(최대 생명력|최대 HP|생명력 비율|HP 비율|생명력|HP|공격력|방어력|행동 게이지|속도)[이가]\s*가장 (높은|낮은) 적' + suffix, desc)
        if not rank or not pool:
            return None
        stat = {'최대 생명력': lambda x: x.maxhp, '최대 HP': lambda x: x.maxhp,
                '생명력 비율': lambda x: x.hp / x.maxhp, 'HP 비율': lambda x: x.hp / x.maxhp,
                '생명력': lambda x: x.hp, 'HP': lambda x: x.hp, '공격력': self.live_atk,
                '방어력': self.def_stat, '행동 게이지': lambda x: x.gauge, '속도': lambda x: x.spd()}[rank[1]]
        best = (max if rank[2] == '높은' else min)(stat(x) for x in pool)
        return [x for x in pool if stat(x) == best]

    def pick_attack_target(self, att, sk=None):
        pool = self.targetable(1 - att.side)
        if not pool:
            return None
        if att.side == 0:
            # 구원자 오토: table = 게임 규칙 1(보스 -> 정예 -> 유리 속성 -> 생명력 비율 최저 -> 최대 생명력 최저 -> 무작위)
            if self.mc['ally_auto_target'] == 'table':
                return self.filter_pick(att, pool, RULE1)
            # boss_first = 살아 있는 보스가 있으면 보스(사용자 관찰 2026-10-20), 그다음 보호막+HP 합 최저(같으면 앞 칸)
            if self.mc['ally_auto_target'] == 'boss_first':
                bosses = [v for v in pool if getattr(v.d, 'boss', False)]
                if bosses:
                    pool = bosses
            return min(pool, key=lambda v: (v.hp + v.shield_total(), v.pos))
        ranked = self.ranked_enemies(skill_desc(att.d, sk.slot), pool, priority=True) if sk is not None else None
        if self.mc['enemy_auto_target'] == 'table':
            # 설명문 「~가 가장 높은 적 우선」 = 그 스킬 고유 규칙의 근사(게임은 고유 규칙이 있으면 1001 을 안 씀) -> 동률은 무작위
            if ranked:
                return ranked[0] if len(ranked) == 1 else self.R(att.side).choice(ranked)
            return self.filter_pick(att, pool, RULE1001)
        return self.weighted_pick(ranked or pool)

    def R(self, side):
        """결정 주체 쪽(side 0 아군·1 적)의 난수. 공통 난수가 꺼져 있으면 하나뿐인 self.rng"""
        return self._rs[side] if self._rs is not None and side in (0, 1) else self.rng

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
            row = front if self.R(1 - pool[0].side).random() < rw[0] / (rw[0] + rw[1]) else back
        else:
            row = front or back
        return self._roll([(v, w(v)) for v in row])

    def _roll(self, cands):
        tot = sum(x for _, x in cands)
        r = self.R(1 - cands[0][0].side if cands else None).random() * tot
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
            v = self.pick_attack_target(u, sk)
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
            elem = self._cur_line.eff.get('beneficiary_element') if self._cur_line else None
            return [x for x in ctx.targets if (not x.dead or kind == 'revive') and (not elem or x.element == elem)]
        if t.startswith('적'):
            opp = self.alive(1 - owner.side)
            if not opp:
                return []
            cur = self._cur_line
            if cur is not None and cur.eff.get('target_state'):
                return [x for x in opp if x.has(cur.eff['target_state'])]
            if '자동 지정' in t and cur is not None:
                desc = skill_desc(owner.d, cur.slot)
                ranked = self.ranked_enemies(desc, opp)
                if ranked:
                    return [min(ranked, key=lambda x: x.pos)]
                self.unsup['selector: 적 자동 지정 규칙 미확인 ' + cur.raw[:50]] += 1
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
        if excl or t.startswith('아군') or mm:
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
            return [self.R(owner.side).choice(pool)]
        if mode == 'lowest_hp':
            pool = sorted(pool, key=lambda v: (v.hp / v.maxhp, v.pos))
        else:
            pool = sorted(pool, key=lambda v: (-self.live_atk(v), v.pos))
        return pool[:k or 1]

    # ---------- 시전
    def cast(self, u, sk, extra=False, target=None, skip_lines=False, via=None, local_pre=False, parent=None):
        if u.dead:
            return None
        if self.incapacitated(u):
            # 기절·수면이면 어떤 시전도 없음(협공·반격·트리거·추가 발동 포함 — 추가 발동은 침묵·도발·쿨타임과 무관하지만 기절·수면은 불가, formulas_web.md 2.1)
            return None
        if self.depth >= self.mc['max_depth']:
            self.unsup['depth: 연쇄 깊이 상한으로 시전 생략'] += 1
            return None
        variant = getattr(u.d, 'variants', {}).get(sk.slot)
        if variant:
            rule, replacement = variant
            if u.stack(rule['name']) >= rule['count'] and (not rule['own'] or (u.acting and not extra)):
                sk = replacement
        self.tick()
        self.depth += 1
        previous_cast = getattr(self, '_cast_ctx', None)
        suspended = {}
        if previous_cast is not None:
            for x, name in previous_cast.markers:
                if name in x.eff:
                    suspended[(x, name)] = x.eff.pop(name)
                    self.dirty(x)
        try:
            ctx = Ctx(u, u, sk, extra)
            self._cast_ctx = ctx
            ctx.via, ctx.parent = via or ('extra' if extra else None), parent
            u.cast_count[sk.slot + ('(추가)' if extra else '')] += 1
            if not extra and sk.cd:
                u.cd[sk.slot] = sk.cd
            policy = self.opts['nova_policy']
            burst_skill = (policy == 'manual' and sk.is_attack
                           and (self.mc['manual_burst'] == 'any_attack' or sk.slot == '궁극기'))
            if policy == 'heal' and u.side == 0 and not extra:
                rank = heal_burst_rank(u.d, sk)
                pool = self.alive(0) if self.opts['nova_pool'] == 'team' else [u]
                preferred = any(heal_burst_rank(v.d, s) == 2 for v in pool for s in v.d.skills.values())
                burst_skill = rank == 2 or (rank == 1 and not preferred)
            if (u.side == 0 and self.opts['nova'] and not extra and burst_skill and self.nova_of(u) >= 4):
                self.nova_add(u, -4)
                ctx.inc += 0.15
                ctx.nb = True
                self.nova_bursts[u.pos, sk.slot] += 1
            ctx.targets = self.skill_targets(u, sk, target)
            ctx.target = ctx.targets[0] if ctx.targets else None
            ctx.dead_targets = {x for x in ctx.targets if x.dead}
            if self.timeline is not None:
                t0 = ctx.targets[0] if ctx.targets else None
                self.log(actor=u.name, side=u.side, pos=u.pos, skill=sk.slot + ('(추가)' if extra else ''), skill_name=sk.name,
                         targets=[x.name for x in ctx.targets], via=via or ('extra' if extra else None), nb=ctx.nb,
                         all=bool(sk.all), tgt_side=(t0.side if t0 is not None else None),
                         tgt_boss=bool(t0 is not None and getattr(t0.d, 'boss', False)))
            if not skip_lines:
                self.run_own(u, ctx, 'own_pre')
            elif local_pre:   # 줄을 건너뛰는 트리거 시전이라도 그 스킬의 「이번 스킬에만」 피해 보정은 적용(프로페서M 브레이크 대상 +30%·스킬 레벨 +15%)
                lines = [ln for ln in self.lines_of(u) if line_kind(ln) == 'own_pre' and ln.eff['kind'] == 'local' and ln.slot == sk.slot]
                if lines:
                    self.run_batch(u, lines, ctx)
            # 자기 효과 생략과 타 유닛에 대한 사용 통지는 별개다.
            self.fire_side(u, ctx, 'ally_pre')
            self.fire_foes(u, ctx, 'foe_pre' if sk.is_attack else 'foe_pre_na')
            if sk.is_attack and ctx.targets:
                self.deal(u, ctx)
            if not u.dead:
                if not skip_lines:
                    self.run_own(u, ctx, 'before_heal')
                self.skill_heal(u, sk, ctx)
            if not skip_lines and not u.dead:
                self.run_own(u, ctx, 'own_post')
            self.event_triggers(u, ctx, 'own_post')
            self.fire_side(u, ctx, 'ally_post')
            self.fire_foes(u, ctx, 'foe_post' if sk.is_attack else 'foe_post_na')
            self.fire_foes(u, ctx, 'foe_post_any')      # 「적 행동 후」(공격·비공격 모두)
            # GetNovaForceValue is paid at every skill end, including reactions
            # and extra casts (NKM:15325-15331,15487,15706-15709).
            if self.mc['nova_skill_gain'] or (u.side == 0 and not extra and sk.slot in ('특수기', '궁극기')):
                self.nova_add(u, sk.nv)
            if u.side == 0 and self.opts['coop'] and sk.is_attack and not extra and not u.dead:
                self.coop(u, ctx)
            u.last_slot = sk.slot
            return ctx
        finally:
            for (x, name), old in ctx.markers.items():
                if old is None or x.dead:
                    x.eff.pop(name, None)
                else:
                    x.eff[name] = old
                self.dirty(x)
            for (x, name), effect in suspended.items():
                if not x.dead:
                    x.eff[name] = effect
                    self.dirty(x)
            self._cast_ctx = previous_cast
            self.depth -= 1

    def nova_of(self, u):
        """버스트 판정용 노바 포스: team = 파티 공용 풀, unit = 구원자 개인(opts.nova_pool)"""
        return u.nova if self.opts['nova_pool'] == 'unit' else (self.team_nova if u.side == 0 else self.enemy_nova)

    def nova_add(self, u, v):
        value = self.nova_of(u) + v
        if self.mc['nova_force_effects']:
            value = max(0, value)  # Native decrease floors at zero (NKM:1199).
        # Native upper bound exists, but MaxNovaForceValue is absent from the
        # supplied tables. Do not invent a numeric cap from battle outcomes.
        if self.opts['nova_pool'] == 'unit':
            u.nova = value
        elif u.side == 1:
            self.enemy_nova = value
        else:
            self.team_nova = value

    def incapacitated(self, u):
        """행동 불능(기절·수면). 강인도 격파(브레이크)는 행동 불능이 아니다(게이지 0 초기화로 차례가 늦어질 뿐)."""
        return any(u.has(n) for n in HARD_CC)

    def no_react(self, u):
        """협공·강제 협공·반응·트리거 스킬 불가: 기절·수면 또는 강인도 격파(공식 2026-09-10 NOA 가이드). 추가 발동은 격파와 무관."""
        return self.incapacitated(u) or u.broken

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
            if x in ctx.dead_targets:
                continue
            got = self.heal(u, x, stat * float(m.group(2)) / 100.0, give + ctx.recv_by.get(x, 0.0))
            self.log(heal=u.name, to=x.name, amount=got)

    def run_own(self, u, ctx, kind):
        sk = ctx.skill
        source = self.lines_of(u)
        if hasattr(sk, 'semantic_lines'):
            source = [ln for ln in source if not (ln.src_kind == 'active' and ln.slot == sk.slot)] + sk.semantic_lines
        # Slot effects depend on activation, not on the selection policy.
        if ctx.nb and (self.mc['nova_slot_effects'] or self.opts['nova_policy'] == 'heal'):
            source = source + [Line(raw, sk.slot, 'nova')
                               for raw in (getattr(u.d, 'nb', {}).get(sk.slot + ' 사용 시') or [])]
        lines = [ln for ln in source if line_kind(ln) == kind and not (ln.bound and ln.slot != sk.slot)
                 and not (ln.trig and '공격' in ln.trig and ln.na == sk.is_attack)]   # 「내 행동 시/후」는 공격·비공격 모두
        if kind == 'own_post':
            # 「기본기 사용 후 최대 스택」은 그 기본기의 스택 부여까지 끝낸 상태로 판정.
            self.run_batch(u, [ln for ln in lines if ln.src_kind in ('active', 'trigger', 'nova')], ctx)
            self.run_batch(u, [ln for ln in lines if ln.src_kind not in ('active', 'trigger', 'nova')], ctx)
        elif lines:
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
                c2.break_targets, c2.crit_targets = ctx.break_targets, ctx.crit_targets
                c2.hit_targets, c2.via, c2.parent = ctx.hit_targets, ctx.via, ctx.parent
                self.run_batch(b, lines, c2)
        if kind == 'ally_post' and ctx.skill.is_attack and ctx.targets:
            self.ally_stack_triggers(actor, ctx)

    def ally_stack_triggers(self, actor, ctx):
        self.event_triggers(actor, ctx, 'ally_post')

    def trigger_cast(self, owner, sk, target=None, **kw):
        """반응·트리거 공통 진입점: 상태와 쿨 확인 후 재진입 전에 예약."""
        key = (id(owner), sk.slot)
        if (owner.dead or self.no_react(owner) or owner.cd.get(sk.slot, 0) > 0
                or key in self._triggering or (owner.side == 1 and not self.enemy_lines)):
            return None
        owner.cd[sk.slot] = sk.cd or 0
        self._triggering.add(key)
        try:
            return self.cast(owner, sk, extra=True, target=target, **kw)
        finally:
            self._triggering.remove(key)

    def event_triggers(self, actor, ctx, event):
        if not ctx.skill.is_attack or not ctx.hit_targets:
            return
        for owner in ([actor] if event == 'own_post' else list(self.alive(actor.side))):
            for sk in owner.d.trigger_skills.values():
                rule = trigger_rule(sk, self.lines_of(owner))
                if not rule or rule['event'] != event or (rule.get('exclude_self') and owner is actor):
                    continue
                if (self.no_react(owner) or owner.dead or owner.cd.get(sk.slot, 0) > 0
                        or (id(owner), sk.slot) in self._triggering or (owner.side == 1 and not self.enemy_lines)):
                    continue
                if rule.get('skill') and ctx.skill.name != rule['skill']:
                    continue
                if 'stack' in rule and owner.stack(rule['stack'][0]) < rule['stack'][1]:
                    continue
                target = None
                if 'hp' in rule or 'mark' in rule:
                    target = next((v for v in ctx.hit_targets if not v.dead
                                   and ('hp' not in rule or v.hp <= v.maxhp * rule['hp'])
                                   and ('mark' not in rule or v.has(rule['mark']))), None)
                    if target is None:
                        continue
                if rule.get('recent'):
                    target = owner.last_target
                    if target is not None and target.dead:
                        target = None
                # 소거를 먼저 확정해 다른 아군의 연쇄로 같은 스택을 재사용하지 않는다.
                if rule.get('consume_all'):
                    owner.eff.pop(rule['stack'][0], None)
                    self.dirty(owner)
                self.trigger_cast(owner, sk, target, via='trigger', skip_lines=bool(rule.get('consume_all')),
                                  local_pre=bool(rule.get('consume_all')))
                if rule.get('consume_all'):
                    for ln in self.lines_of(owner):
                        if ln.slot == sk.slot and ln.src_kind == 'trigger' and line_kind(ln) == 'own_post' and ln.eff['kind'] == 'gauge':
                            self.run_line(owner, ln, Ctx(owner, owner, sk, True))

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
            if b is actor or b.d.skills.get('기본기') is None or self.no_react(b):
                continue   # 기절·수면(강인도 격파 포함, 미구현)이면 협공 불가(공식 2026-09-10 NOA 가이드)
            p = min(_rules.COOP_CAP, max(0.0, b.mods()['coop']))
            if p > 0:
                cands.append((b, p))
        for b, p in sorted(cands, key=lambda bp: (-bp[1], bp[0].pos)):
            if self.R(actor.side).random() < p:
                self.cast(b, b.d.skills['기본기'], extra=True, target=self._coop_target(ctx), via='coop')
                return

    def revenge(self, hits):
        """반격(NKM.decompiled.cs 11990~12075 판정·15227~15360 처리): 이번 행동에서 유효 타격을 받은 쪽마다 한 번,
        공격 스킬이고 피격자 생존·브레이크 아님·공격자 생존(적)·기본기 사용 가능이면 반격 확률(NST_RATE_REVENGE_ATTACK)로
        공격자에게 기본기. 반격에는 반격·협공이 없다. 공격자가 쓰러지면 남은 반격은 끝.
        공격(시전) 하나의 후보는 추첨을 먼저 모두 끝낸 뒤 차례로 반격하고(NKM 7775~7784 ToArray), 공격자가 쓰러지면 그 공격의 남은 반격만 끝.
        근사: 게임은 본 행동·협공·반응 스킬마다 그 직후에 반격하지만 엔진은 반응 스킬이 시전 안에 겹쳐 있어 행동 끝에 시전 순서대로 처리."""
        done = set()
        order, groups, used = [], {}, set()
        i = 0
        while True:
            # hits 는 반격 중에 늘어날 수 있다(반격에서 이어진 공격). 같은 시전(ctx)의 타격은 사이에 다른 시전이 끼어도 한 묶음
            while i < len(hits):
                a, v, c = hits[i]
                if id(c) not in groups:
                    groups[id(c)] = []
                    order.append(id(c))
                groups[id(c)].append((a, v))
                i += 1
            key = next((k for k in order if k not in used), None)
            if key is None:
                break
            used.add(key)
            picks, seen = [], set()
            for a, v in groups[key]:
                if v in done or v in seen or v.dead or v.broken or a.dead or a.side == v.side:
                    continue
                seen.add(v)
                p = v.mods()['revenge']
                if (p <= 0 or v.d.skills.get('기본기') is None or v.cd.get('기본기', 0) > 0
                        or self.incapacitated(v)):
                    continue
                if self.R(v.side).random() < min(1.0, p):
                    picks.append((a, v))
            for a, v in picks:
                if v.dead or v in done:
                    continue
                done.add(v)
                self.revenges[v.side] += 1
                self.cast(v, v.d.skills['기본기'], extra=True, target=a, via='revenge')
                if a.dead:
                    break

    def _coop_target(self, ctx):
        if ctx.skill.all:
            al = self.alive(1)
            return self.R(ctx.src.side if ctx.src is not None else None).choice(al) if al else None
        return ctx.target if (ctx.target is not None and not ctx.target.dead) else None

    # ---------- 피해
    def atk_stat(self, u, ctx=None):
        m = u.mods()
        return u.d.stats['atk'] * (1 + u.d.passive['atkp'] + m['atkp'] + (ctx.atkp if ctx else 0.0) + u.d.gear_atkp)

    def def_stat(self, u, local=0.0):
        m = u.mods()
        return max(0.0, u.d.stats['def'] * (1 + u.d.passive['defp'] + m['defp'] + local))

    def hp_stat(self, u):
        return u.maxhp

    def rand(self, side=None):
        lo, hi = self.mc['rand_range']
        steps = int(round((hi - lo) * 10000))
        return lo + self.R(side).randint(0, steps) / 10000.0

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
            ctx.hit_targets.append(v)
            ctx.target = v
            # 회피(가정: 회피율 - 공격자 명중률 보정, 필중이면 0). 회피하면 치명 없음·감소 합 +50%·약화 안 걸림
            ev = 0.0 if (a.on('필중') or self.mc['evade_model'] == 'off') else v.mods()['evade'] - (m['acc'] + ctx.acc)
            evaded = ev > 0 and self.R(a.side).random() < ev
            by = ctx.local_by[v]
            crit = (not evaded) and (self.R(a.side).random() < min(1.0, cr + by['cr']) or ctx.force_crit)
            ctx.crit = ctx.crit or crit
            if crit:
                ctx.crit_targets.add(v)
            if evaded:
                ctx.evaded.add(v)
            t0 = v.taken
            self.strike(a, v, base, ctx, crit, min(3.0, cdv + by['cd']), min(1.0, pen + by['pen']), reactions, evaded)
            if self._hit_log is not None and ctx.via != 'revenge' and v.taken > t0:
                # 반격 후보 = 피해(보호막 흡수 포함)가 0보다 큰 타격(NKM 7203~7215, 회피도 피해가 남으면 포함). 반격으로 낸 타격은 제외
                self._hit_log.append((a, v, ctx))
        if ctx.hit_targets:
            a.last_target = ctx.hit_targets[-1]
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
            self.reaction_skills(v, a, sk, hctx.crit, v in hctx.evaded)
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
        r = self.rand(a.side)
        if v.on('스킬 피해 무효'):
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
                # Native shared damage re-enters GetFinalDamage with a supplied
                # base; that path forces NormalHit (NKM:7494,17384,17418).
                shared_normal = w is guard and self.mc['guard_normal_hit']
                dmg = self.final_dmg(a, w, pc[1], ctx, crit and not shared_normal, cdv, pen, r, hctx)
            if w is guard:
                self.log(guard=guard.name, protects=v.name, dmg=dmg)
            killed = self.apply_damage(a, w, dmg, 'guard' if w is guard else 'hit', shieldable=True) or killed
        if killed and v.dead:
            ctx.kill = True
        if self.mc['toughness'] == 'on' and not evaded and not v.dead:
            self.tough_hit(a, v, ctx)      # 피해 처리 뒤(격파시킨 타격 자체는 −15%p 를 받지 않음, assumed). 회피하면 강인도 안 깎임(community)
        reactions.append((v, hctx))

    def tough_hit(self, a, v, ctx):
        """video: 구원자 공격 시전·대상당 ab + 상성 기본값 + 강인도 보정 + 버스트 1.
        기본값은 유리/동일 1, 그 외 0(동일은 ChgzulK7VI4 헤이디 관측으로 추론).
        협공 0, 추가 발동은 별도 시전. 적 공격은 미측정이므로 종전 db를 유지한다.
        db/on/off는 종전 타격별 계산을 보존. 상세 근거·미확인 범위는 규칙 파일 참조.
        〈강인도 피해 무효〉·회피·스킬 피해 무효는 강인도를 깎지 않는다."""
        if v.broken or v.sa_max <= 0 or v.has('강인도 피해 무효'):
            return
        mode = self.mc['toughness_elem']
        video = mode == 'video' and a.side == 0
        if video:
            if not ctx.skill.is_attack or ctx.via in ('coop', 'forced_coop') or v in ctx.tough_targets:
                return
            ctx.tough_targets.add(v)
        sk = ctx.skill
        m = a.mods()
        ab = getattr(sk, 'ab', None)
        if ab is None:
            ab = (sk.raw or {}).get('ab')
        if ab is None:          # 데이터에 값이 «없을» 때만 가정값(적의 명시적 ab=0 은 그대로 0 — codex 검토 2026-10-21)
            ab = self.mc['basic_tough'] if sk.slot == '기본기' else 0
        normal = ab + m['tough'] + ctx.tough
        fixed = m['tough_fixed'] + ctx.tough_fixed
        if video:
            if a.element and v.element and (a.element == v.element or ELEM_BEATS.get(a.element) == v.element):
                normal += 1
            if not self.mc['nova_slot_effects']:
                fixed += int(ctx.nb)  # Legacy video approximation; native slot lines already add this.
        elif mode in ('db', 'video'):
            # starsavior-db mechanics(2026-10-21 확인): 기본값(상성 유리 1, 아니면 0) + 강인도 피해(스킬 ab·버프) + 고정 피해 − 감소
            if a.element and v.element and ELEM_BEATS.get(a.element) == v.element:
                normal += 1
        elif mode == 'on' and a.element and v.element:
            if ELEM_LOSES.get(a.element) == v.element:
                normal = 0
            elif ELEM_BEATS.get(a.element) == v.element and normal > 0:
                normal += 1
        td = int(round(max(0.0, normal) + max(0.0, fixed)))
        if td <= 0:
            return
        v.sa = max(0, v.sa - td)
        if v.sa == 0:
            ctx.break_targets.add(v)
            v.broken = True
            v.breaks += 1
            if v.side == 1 and self.break_skill_enabled:
                points = self.mc['break_skill_boss_points' if getattr(v.d, 'boss', False) else 'break_skill_normal_points']
                gained = max(0, min(points, self.mc['break_skill_point_cap'] - self.break_points))
                self.break_points += gained
                self.break_points_gained += gained
            if v.side == 1 or self.mc['ally_break_gauge'] == 'reset':
                v.gauge = 0.0      # 몬스터는 행동 게이지 0(databook #d-break). 구원자도 기본 0(사용자 인게임 확인 2026-10-21, mc.ally_break_gauge)
            self.dirty(v)
            self.log(brk=v.name, by=a.name)

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
        if v.broken:
            inc += m['inc_break'] + ctx.inc_break      # 「브레이크 대상 피해 증가」(공격자 쪽, 증가 합)
        red = vm['red']
        dec = red.get('all', 0.0) + red.get('aoe' if sk.all else 'single', 0.0) + red.get(sk.slot, 0.0)
        if hctx is not None and hctx.local is not None:
            dec += hctx.local[v]['red']      # 피격 직전 「이번 스킬에만」 피해 감소(감소 합에 더함)
        if hctx is not None and v in hctx.evaded:
            dec += 0.5     # 회피 시 감소 합 +50%(databook #d-sum)
        if v.broken:
            dec -= _rules.BREAK_DEC          # 브레이크 대상: 감소 합 −15%p 후 상한(databook #d-break)
        dec = min(_rules.DEC_CAP, dec)
        mult = 1 + inc - dec
        if crit:
            mult += max(0.0, cdv - vm['critred'])
        dmg = base * (1 - dr) * mult * r * self.pen[a.side]
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
                if e.shield > 0 and rest > 0 and not (v.buff_blocked() and not e.harmful):   # 〈강화 불가〉 중엔 보호막도 꺼짐
                    take = min(e.shield, rest)
                    e.shield -= take
                    rest -= take
                    absorbed += take
                    if e.shield <= 1e-9 and not e.props:
                        del v.eff[name]
                        self.dirty(v)
        real = min(rest, v.hp)
        forced = None
        if real > 0 and (DAMAGE_LIMIT.keys() & v.eff.keys() or '불사' in v.eff):
            real, forced = self._limit_damage(v, real)
        v.hp -= real
        if forced is not None:
            v.hp = forced          # 「최대 생명력의 1% 만큼 강제로 회복」: 지금 생명력이 그보다 낮아도 그 값으로(회복량은 집계 안 함)
        if a is not None:
            a.dmg += real + absorbed        # 넘친 피해(오버킬)는 제외
        v.taken += real + absorbed
        if v.hp <= 1e-9:
            self.kill(v, a)
            return True
        return False

    def _limit_damage(self, v, real):
        """〈불사〉(지속 동안 사망하지 않음: 생명력 1 남김)와 「피해 제한」 효과(DAMAGE_LIMIT 의 효과별 동작).
        -> (깎을 생명력, 강제로 맞출 생명력 또는 None). 〈강화 불가〉 중이면 강화 효과인 이것들도 작동하지 않는다."""
        left = v.hp - real
        forced = None
        for name in [n for n in DAMAGE_LIMIT if v.on(n)]:
            rule = DAMAGE_LIMIT[name]
            if rule['kind'] == 'floor':
                floor_hp = math.floor(v.maxhp * rule['pct'])
                if v.hp > floor_hp and left < floor_hp:
                    left = floor_hp
                    self._consume_limit(v, name, rule)
            elif rule['kind'] == 'lethal' and left <= 1e-9:
                forced = max(1.0, math.floor(v.maxhp * rule['keep']))
                left = forced
                self._consume_limit(v, name, rule)
                e = Eff('불사', {}, 1, rule['undying'], v, False)
                e.stacks = 1
                e.fresh = v.acting
                v.eff['불사'] = e
                for nm, dur, props in rule.get('then', ()):
                    e2 = Eff(nm, dict(props), 1, dur, v, False)
                    e2.stacks, e2.fixed, e2.fresh = 1, True, v.acting
                    v.eff[nm] = e2
                if rule.get('reset_cd'):
                    for k in v.cd:
                        v.cd[k] = 0
                self.dirty(v)
        if left <= 1e-9 and v.on('불사'):
            left = 1.0
        if forced is not None:
            return v.hp, forced     # 사망 피해는 그대로 받고(지금 생명력 전부) 강제 회복값으로 맞춤
        return max(0.0, v.hp - left), None

    def _consume_limit(self, v, name, rule):
        self.log(limit=v.name, eff=name)
        if rule.get('once'):
            del v.eff[name]
            self.dirty(v)

    def kill(self, v, a):
        v.hp = 0.0
        v.dead = True
        v.death_t = self.t
        self.death_seq += 1
        v.death_n = self.death_seq   # 사망 순서(같은 틱의 광역 사망도 구분 — 게임 사망 목록의 추가 순서)
        if v.side == 0 and self.first_death is None:
            self.first_death = v
        self.log(death=v.name)
        self.fire(v, 'death_self', Ctx(v, a, None))
        for w in self.alive(v.side):
            self.fire(w, 'death_ally', Ctx(w, a, None))
        for w in self.alive(1 - v.side):
            self.fire(w, 'death_enemy', Ctx(w, a, None))
        v.eff = {}
        v.gauge = 0.0
        self.dirty(v)

    def reaction_skills(self, v, a, sk, crit=False, evaded=False):
        """반응 트리거 스킬(지원 목록): 웨딩 카르멘 「수호의 기사」 — 사랑의 서약 아군이 피격되면 발동(쿨타임 적용).
        화이트 펄 루나 「썸머 템테이션♡」 — 자신을 제외한 아군이 치명타 피격 후 타격자에게 발동(쿨타임 1, 보호막·방어력 감소, 2026-10-21)."""
        if a is not None and not a.dead and a.side != v.side:
            for ts in v.d.trigger_skills.values():
                rule = trigger_rule(ts, self.lines_of(v))
                if rule and rule['event'] == 'hit' and (not rule.get('aoe') or sk.all) and (not rule.get('evade') or evaded):
                    self.trigger_cast(v, ts, a, via='reaction')
        if crit and a is not None and not a.dead and a.side != v.side:
            for w in self.alive(v.side):
                if w is v or self.no_react(w):
                    continue
                ts = w.d.trigger_skills.get('특수기')
                if ts is None or not (ts.tg or '').startswith('반응 대상(적)') or '아군이 치명타 피격 후' not in (ts.raw.get('d1') or ''):
                    continue
                self.trigger_cast(w, ts, a, via='reaction')
        for w in self.alive(v.side):
            if w is v:
                continue
            ts = w.d.trigger_skills.get('특수기')
            if ts is None or not (ts.tg or '').startswith('반응 대상(아군)'):
                continue
            oath = v.eff.get('사랑의 서약(해제불가)')
            if oath is None or oath.src is not w:
                continue
            ctx = self.trigger_cast(w, ts, v, via='reaction')
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
                    dec = vm['red'].get('all', 0.0)
                    if u.broken:
                        inc += sm['inc_break']
                        dec -= _rules.BREAK_DEC
                    dec = min(_rules.DEC_CAP, dec)
                    de = self.def_stat(u)
                    dr = de / (de + _rules.DEF_K)
                    dmg = max(1.0, math.floor(val * c * _rules.BASE_MULT * (1 + inc - dec) * (1 - dr) * self.rand(src.side) * self.pen[src.side]))
                    self.apply_damage(src, u, dmg, 'dot', shieldable=False)
            if e.hot > 0 and not u.dead and u.on(name):
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
            if mh.group(2) == '미만' and not frac < thr:
                return False
        last = None
        sk = ctx.skill
        tgt = ctx.target if ctx.target is not None else None
        for k, v in ln.params:
            if k not in COND_KEYS:
                self.unsup['cond: ' + k] += 1
                if self.mc['unknown_cond'] == 'roll':
                    if self.R(owner.side).random() >= self.opts['unknown_cond_p']:
                        return False
                    continue
                return False
            if k == '사용 스킬':
                if not (sk is not None and sk.slot == v):
                    return False
            elif k == '추가발동 스킬':
                if (v == '예') != bool(ctx.extra and ctx.via not in ('trigger', 'reaction')):
                    return False
            elif k == '추가발동 스킬이 아님':
                if (v == '예') != (not ctx.extra or ctx.via in ('trigger', 'reaction')):
                    return False
            elif k == '자기 추가발동 트리거':
                if (v == '예') != bool(ctx.extra and ctx.parent is not None and ctx.parent.src is owner):
                    return False
            elif k == '자기 추가발동 트리거 스킬':
                if ctx.parent is None or ctx.parent.src is not owner or ctx.parent.skill is None or ctx.parent.skill.slot != v:
                    return False
            elif k == '시전자 턴':
                if (v == '예') != bool(ctx.src is not None and ctx.src.acting):
                    return False
            elif k in ('자신이 보유', '자신이 미보유'):
                names = [x.strip() for x in v.split(',')]
                last = ('A', names)
                pres = any(owner.has(n) for n in names)
                # 「미보유 + 효과 중첩수 N」는 효과 자체 부재가 아니라 N중첩 미달.
                if k == '자신이 미보유' and '자신 미보유 효과 중첩수' in dict(ln.params):
                    if any(owner.stack(n) >= float(dict(ln.params)['자신 미보유 효과 중첩수']) for n in names):
                        return False
                    continue
                if pres != (k == '자신이 보유'):
                    return False
            elif k == '자신 미보유 효과 중첩수':
                if self._count(owner, ctx, last) >= float(v):
                    return False
            elif k in ('중첩수', '효과 개수', '대상 효과 중첩수'):
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
            elif k in ('중첩수 이상', '효과 개수 이상'):
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
            elif k == '이번 타격 격파':
                if bool(ctx.break_targets) != (v == '예'):
                    return False
            elif k in ('대상 강인도 없음', '대상 브레이크'):    # P5: 강인도 격파 상태
                if (tgt is not None and tgt.broken) != (v == '예'):
                    return False
            elif k == '피해 증가(조건부)':     # 「이 줄은 조건부 피해 증가」 표지로 봄(값 '예'만 나옴, assumed)
                pass
            elif k == 'NotTargetPositiveBuff':   # 대상에게 강화 효과가 없음(내부 키 이름 해석, assumed)
                if (tgt is not None and tgt.n_good() == 0) != (v == '예'):
                    return False
            elif k == 'NotEnemyPositiveBuff':    # 상대(나를 친 적, 없으면 상대 전원)에게 강화 효과가 없음(assumed)
                pool = [ctx.src] if (ctx.src is not None and ctx.src.side != owner.side) else self.alive(1 - owner.side)
                if all(x.n_good() == 0 for x in pool) != (v == '예'):
                    return False
            elif k == 'ExistAllySpecificBuff':   # 같은 편(나 포함)에 그 효과를 가진 유닛이 있음(assumed)
                names = [x.strip() for x in v.split(',')]
                if not any(x.has(n) for x in self.alive(owner.side) for n in names):
                    return False
            elif k == 'IsTargetSuperArmor':      # 「강인한 의지」: 대상(피격자)이 강인도 격파 상태가 아니면(내부 키 이름 해석, assumed)
                if (tgt is not None and not tgt.broken) != (v == '예'):
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
                last = ('XS', [x.strip() for x in v.split(',')])    # 뒤따르는 「효과 개수/중첩수」는 시전자(나를 친 상대)의 중첩수
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
            elif k == '대상 클래스':
                if tgt is None or tgt.role != v:
                    return False
            elif k in ('적 약화효과 보유', '적 강화효과 보유'):
                lim = dict(ln.params).get('효과 개수 미만')
                cmp_ = self.mc['enemy_hit_buff_cmp']
                if (k == '적 강화효과 보유' and v == '예' and lim is not None and cmp_ != 'legacy'
                        and ctx.src is not None and ctx.src.side != owner.side):
                    # 「강화 효과가 N개 이하(미만)인 적에게 피격」: 때린 상대 한 명의 강화 효과 수로 판정(옛 방식은 상대 전원 중 하나라도 있으면 참)
                    if cmp_.endswith('_disp'):    # 해제 불가 표식(고정 강화)은 세지 않음(실험: 게임이 센다고 보장 못 함)
                        n = sum(1 for e in ctx.src.eff.values() if e.category == 'buff' and e.stacks > 0 and not e.check and not e.fixed)
                    else:
                        n = ctx.src.n_good()
                    if not (n < float(lim) if cmp_.startswith('lt') else n <= float(lim)):
                        return False
                    continue
                if (k == '적 약화효과 보유' and '효과 개수 이상' in dict(ln.params)
                        and ctx.src is not None and ctx.src.side != owner.side):
                    # 「약화 효과가 N개 이상인 적에게 피격」: 때린 상대 한 명의 약화 효과 수로 판정
                    last = ('XD', None)
                    if (ctx.src.n_harmful() > 0) != (v == '예'):
                        return False
                    continue
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
        src = ctx.src
        if kind == 'XS':
            return sum(src.stack(n) for n in names) if src is not None else 0
        if kind == 'XD':
            return src.n_harmful() if src is not None else 0
        return 0

    # ---------- 줄 실행
    def run_line(self, owner, ln, ctx):
        self.run_batch(owner, [ln], ctx)

    def line_ok(self, owner, ln, ctx):
        if owner.dead and line_kind(ln) not in ('death_self',):
            return False
        if ln.eff['kind'] == 'perm':
            return False
        branch = ln.eff.get('life_branch')
        if branch and ((ctx.target in ctx.dead_targets) != (branch == 'dead')):
            return False
        if '전투당 1회' in ln.raw and (id(owner), id(ln)) in self.once:
            return False
        mrc = RX_RECAST.search(ln.raw) if '재발동 불가' in ln.raw else None
        if mrc and owner.actions < self.recast.get((id(owner), id(ln)), -10 ** 9) + int(mrc.group(1)):
            return False      # P5 {발동 후 N턴 재발동 불가}: 발동한 자기 턴부터 N턴(주인의 행동 횟수) 동안 다시 안 걸림(설명문 「1턴에 1번만」)
        if ln.params or RX_HP_COND.search(ln.raw):
            ok = self.cond_ok(owner, ln, ctx)
        else:
            ok = True
        if ok and '전투당 1회' in ln.raw:
            self.once.add((id(owner), id(ln)))
        if ok and mrc and not ('확률로' in ln.raw or '% 판정)' in ln.raw):
            self.recast[(id(owner), id(ln))] = owner.actions   # 확률 효과는 실제로 발동했을 때 _fired 가 기록(실패하면 같은 턴 재시도 가능)
        return ok

    def _fired(self, owner):
        """지금 실행 중인 확률 줄이 실제로 발동함 -> {발동 후 N턴 재발동 불가} 기록(재귀 시전 전에 부른다)"""
        ln = self._cur_line
        if ln is not None and '재발동 불가' in ln.raw:
            self.recast[(id(owner), id(ln))] = owner.actions

    @staticmethod
    def _is_cast_line(ln):
        return ln.eff['kind'] in ('extra_cast', 'random_ally_basic') or (ln.eff['kind'] == 'ignored' and RX_EXTRA_P.match(line_rest(ln)) is not None)

    def run_batch(self, owner, lines, ctx):
        """같은 사건(시점·주인)에 걸린 줄 묶음: 조건은 사건 시점 상태로 한꺼번에 판정하고, 효과는 순서대로 실행하되
        추가 발동(시전)은 묶음의 나머지 효과(중첩 소비 등) 뒤에 실행한다(같은 사건에서 자기 자신을 다시 부르는 무한 연쇄 방지)."""
        # 같은 시점의 선행 부여를 참조하는 조건은 부여가 끝난 뒤 판정한다.
        # 나머지 조건은 소거 전에 함께 판정하여 조건부 효과 묶음의 일관성을 지킨다.
        count_grants = [ln for ln in lines if ln.eff.get('pre_grant') or
                        (ln.eff['kind'] == 'buff' and
                         (ln.eff.get('per_hit') or ln.eff.get('per_crit') or ln.eff.get('cast_marker')))]
        for ln in count_grants:
            if self.line_ok(owner, ln, ctx):
                self.exec_line(owner, ln, ctx)
        ok = []
        for ln in lines:
            if ln in count_grants:
                continue
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
            probe.via, probe.parent, probe.hit_targets = ctx.via, ctx.parent, ctx.hit_targets
            probe.targets, probe.target, probe.crit, probe.kill = ctx.targets, ctx.target, ctx.crit, ctx.kill
            if not self.cond_ok(owner, _ParamView(ln, others), probe):
                return
        tparams = [(k, v) for k, v in ln.params if k in TARGET_KEYS]
        rest = line_rest(ln)
        mrecv = RX_RECV_HEAL.match(rest) if ln.eff['kind'] == 'ignored' else None
        for x in list(ctx.targets):
            probe = Ctx(owner, ctx.src, ctx.skill, ctx.extra)
            probe.via, probe.parent, probe.hit_targets = ctx.via, ctx.parent, ctx.hit_targets
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
        if kd == 'random_ally_basic':
            # AutoTargetId=5 / EnforceAutoTargetId=4: random ally (self allowed),
            # random enemy. Extra cast, not ordinary cooperation.
            allies = [u for u in self.alive(owner.side) if '기본기' in u.d.skills]
            enemies = self.alive(1 - owner.side)
            if allies and enemies and self.R(owner.side).random() < eff['chance']:
                self._fired(owner)
                actor = self.R(owner.side).choice(allies)
                self.cast(actor, actor.d.skills['기본기'], extra=True,
                          target=self.R(owner.side).choice(enemies), parent=ctx, via='potential')
            return
        if kd == 'count_damage':
            if ctx.src is owner and ctx.skill is not None:
                if eff['scope'] == 'shield_all':
                    n = sum(sum(e.shield > 0 for e in x.eff.values()) for x in self.alive(1 - owner.side))
                    ctx.inc += min(n, eff['cap']) * eff['val'] / 100
                elif eff['scope'] == 'self_good':
                    ctx.inc += min(owner.n_good(), eff['cap']) * eff['val'] / 100
                else:
                    for x in ctx.targets:
                        n = (x.n_harmful() if eff['scope'] == 'target_harmful' else x.stack(eff['name'])
                             if eff['scope'] == 'target_named' else x.n_good())
                        ctx.local_by[x]['inc'] += min(n, eff['cap']) * eff['val'] / 100
            return
        if kd == 'extend':
            for x in self.resolve(owner, eff['target'], ctx) or []:
                if eff['judge'] and not self.roll_hit(owner, ctx, x, None):
                    continue
                for name, e in x.eff.items():
                    if not e.harmful or (eff['name'] and name != eff['name']):
                        continue
                    e.dur += eff['val']
                    for instance in e.inst or []:
                        instance[1] += eff['val']
            return
        if kd == 'stack_promote':
            upgrade = eff['upgrade']
            if owner.stack(eff['source']) >= eff['threshold'] and owner.stack(upgrade['name']) < upgrade['max']:
                owner.eff.pop(eff['source'], None)
                self.dirty(owner)
                self.apply_buff(owner, upgrade, ctx, raw=eff['upgrade_raw'])
            return
        if eff.get('per_hit') or eff.get('per_crit'):
            n = min(eff['hit_cap'], len(ctx.crit_targets if eff.get('per_crit') else set(ctx.hit_targets)))
            if not n:
                return
            eff = dict(eff, **({'times': n} if kd == 'buff' else {'val': eff['val'] * n}))
        # 조건 발동한 트리거의 소비는 ef에 잘못 기재된 같은 스택 부여를 대체한다.
        if ctx.skill is not None and ln.src_kind == 'trigger' and ctx.skill.slot == ln.slot:
            rule = trigger_rule(ctx.skill, self.lines_of(owner))
            if rule and rule.get('trigger_only') and line_kind(ln) == 'own_post':
                if ctx.via != 'trigger':
                    return
                if kd == 'buff' and eff.get('name') == rule['stack'][0]:
                    eff = dict(eff, consume=True, times=rule['consume'])
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
            elif st == '강인도 피해':
                ctx.tough += eff['val']
            elif st == '강인도 고정 피해':
                ctx.tough_fixed += eff['val']
            elif st == '브레이크 대상 피해 증가':
                ctx.inc_break += v
            elif st == '대상 약화효과 1개당 피해 증가':    # 대상마다 그 대상의 약화 개수(P5)
                for x in ctx.targets:
                    ctx.local_by[x]['inc'] += v * x.n_harmful()
            return
        if kd == 'gauge':
            tg = self.resolve(owner, eff['target'], ctx)
            if not tg:
                return
            for x in tg:
                if eff.get('shield_only') and x.shield_total() <= 0:
                    continue
                if x.side != owner.side and eff.get('judge') and not self.roll_hit(owner, ctx, x, None):
                    continue
                self.set_gauge(x, x.gauge + eff['val'] * 100.0)
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
            sk = owner.d.skills.get(eff['slot']) or owner.d.trigger_skills.get(eff['slot'])
            if sk is not None:
                tgt = owner.last_target if (owner.last_target is not None and not owner.last_target.dead) else None
                rule = trigger_rule(sk, self.lines_of(owner))
                if rule and rule.get('mark'):
                    tgt = next((v for v in self.alive(1 - owner.side) if v.has(rule['mark'])), tgt)
                for _ in range(eff['times']):
                    if eff.get('random_enemy'):
                        pool = self.alive(1 - owner.side)
                        if not pool:
                            break
                        tgt = self.R(owner.side).choice(pool)
                    self.cast(owner, sk, extra=True, target=tgt, parent=ctx)
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
            if tg and '자동 지정' in eff['target'] and not eff['target'].startswith('적'):
                tg = [x for x in self.alive(owner.side) if (x is not owner or not eff['target'].startswith('자신 제외'))]
            for x in tg or []:
                if eff['name'] in x.eff:
                    del x.eff[eff['name']]
                    self.dirty(x)
            return
        if kd == 'buff':
            if owner.d.key == 'cristelle' and eff['name'] == '점화':
                # units.sk d1/dx: 태양 시전자면 기본 1개에 추가 1개(ef의 2회는 합계).
                # 특수기가 나눠 주는 2개 역시 자신을 제외한 태양 아군에게만 적용.
                if ln.slot == '고유 패시브' and line_kind(ln) == 'ally_pre' and dict(ln.params).get('시전자 속성') == '태양':
                    eff = dict(eff, times=1)
                elif ln.slot == '특수기' and eff['target'] == '자신 제외 아군 전체':
                    eff = dict(eff, target='자신 제외 태양 속성 아군 전체')
            if eff['name'] in CD_RESET_NAMES:      # P5 〈궁극기 쿨타임 초기화〉·〈특수기 쿨타임 감소〉 = 그 칸 쿨타임 0(설명문)
                for x in self.resolve(owner, eff['target'], ctx) or []:
                    sl = CD_RESET_NAMES[eff['name']]
                    if sl in x.cd:
                        x.cd[sl] = 0
                return
            if eff['name'] == '강제 치명타 발생':    # 〈강제 치명타 발생〉 (확정 치명타): 이번 스킬은 치명타
                if ctx.src is owner and ctx.skill is not None:
                    ctx.force_crit = True
                return
            if '(' in (paren_after_name(ln.raw)[0] or ''):
                eff = dict(eff, props=full_props(ln))
            mh = RX_HOT.search(ln.raw)
            self.apply_buff(owner, eff, ctx, hot=float(mh.group(1)) / 100.0 if mh else 0.0, raw=ln.raw)
            return

    def run_special(self, owner, ln, ctx, rest):
        """Execute effect lines outside the expected-value parser's model."""
        m = RX_NOVA.match(rest)
        if m and self.mc['nova_force_effects']:
            # The effect targets a unit, then changes that unit's team pool.
            for x in self.resolve(owner, m.group(1), ctx) or []:
                self.nova_add(x, int(m.group(2)))
            return
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
        if m:   # (P5: 「(1턴 / 약화효과 해제)」·「(대상마다 N% 판정)」·{효과 적중 판정}도 읽음 — 해제는 즉시 1회, 지속 턴은 무시)
            tg = self.resolve(owner, m.group(1), ctx)
            harmful = m.group(3) == '약화'
            p = int(m.group(2)) / 100.0 if m.group(2) else 1.0
            for x in tg or []:
                if not self._dispel_ok(owner, ctx, x, p, rest):
                    continue
                for name in list(x.eff):
                    e = x.eff[name]
                    if e.category == ('debuff' if harmful else 'buff') and not e.fixed and e.shield <= 0:
                        del x.eff[name]
                self.dirty(x)
            return
        m = RX_DISPEL_N.match(rest)
        if m:   # 효과 N개 해제: 해제 가능한 것 중 먼저 붙은 순(가정)
            tg = self.resolve(owner, m.group(1), ctx)
            harmful = m.group(3) == '약화'
            p = int(m.group(2)) / 100.0 if m.group(2) else 1.0
            for x in tg or []:
                if not self._dispel_ok(owner, ctx, x, p, rest):
                    continue
                names = [n for n, e in x.eff.items() if e.category == ('debuff' if harmful else 'buff') and not e.fixed and e.shield <= 0][:int(m.group(4))]
                for n in names:
                    del x.eff[n]
                self.dirty(x)
            return
        m = RX_GAUGE_SET.match(rest)
        if m:   # 행동 게이지를 N%로 설정
            for x in self.resolve(owner, m.group(1), ctx) or []:
                if x.side != owner.side and '효과 적중 판정' in rest and not self.roll_hit(owner, ctx, x, None):
                    continue
                x.gauge = float(m.group(2)) * 100.0
            return
        m = RX_CHAIN_T.match(rest)
        if m:   # 대상 생명력 비례 연쇄 피해(「대상 생명력」 = 최대 생명력으로 봄, assumed), ×N 이면 N번
            for _ in range(int(m.group(4) or 1)):
                self.chain(owner, dict(target=m.group(1), stat='target_hp', coef=float(m.group(3)) / 100.0), ctx)
            return
        m = RX_CD_UP.match(rest)
        if m:   # 스킬 쿨타임 N턴 증가: 대상의 쿨타임 있는 스킬 전부(assumed). 면역 「스킬 쿨타임 증가」면 무시
            for x in self.resolve(owner, m.group(1), ctx) or []:
                if '스킬 쿨타임 증가' in getattr(x.d, 'immune', ()):
                    continue
                if x.side != owner.side and '효과 적중 판정' in rest and not self.roll_hit(owner, ctx, x, None):
                    continue
                for slot, sk in x.d.skills.items():
                    if sk.cd and (not ln.eff.get('cd_slot') or slot == ln.eff['cd_slot']):
                        x.cd[slot] = x.cd.get(slot, 0) + int(m.group(2))
            return
        m = RX_LOCAL_PER.match(rest)
        if m:   # 「피해 증가 +N% (○의 강화/약화 효과 1개당 …)」: 이번 스킬, 개수 = 그 시점
            if ctx.src is owner and ctx.skill is not None:
                v, who, kind = float(m.group(1)) / 100.0, m.group(2), m.group(3)
                cnt = (lambda u: u.n_good()) if kind == '강화' else (lambda u: u.n_harmful())
                if who == '공격 대상':
                    for x in ctx.targets:
                        ctx.local_by[x]['inc'] += v * cnt(x)
                else:
                    pool = [owner] if who == '자신' else (self.alive(1 - owner.side) if who == '적 전체' else self.alive(owner.side))
                    ctx.inc += v * sum(cnt(x) for x in pool)
            return
        self._run_special_rest(owner, ln, ctx, rest)

    def _dispel_ok(self, owner, ctx, x, p, rest):
        if p < 1.0 and self.R(owner.side).random() >= p:
            return False
        if x.side != owner.side and '효과 적중 판정' in rest and not self.roll_hit(owner, ctx, x, None):
            return False
        self._fired(owner)
        return True

    def _run_special_rest(self, owner, ln, ctx, rest):
        """run_special 의 나머지 분기(무작위 효과·받는 회복량·확률 게이지·확률 추가 발동·강인도 회복·확률 회복)"""
        m = RX_RANDOM.match(rest)
        if m:
            from .starsavior.foe import gloss
            g = dict(gloss(), **getattr(owner.d, 'effect_info', {}))
            tg = self.resolve(owner, m.group(1), ctx)
            names = [x.strip() for x in m.group(3).split(',')]
            p = int(m.group(2)) / 100.0 if m.group(2) else 1.0
            for x in tg or []:
                if self.R(owner.side).random() >= p:
                    continue
                self._fired(owner)
                repeats = ln.eff.get('random_times', 1)
                for _ in range(repeats):
                    name = self.R(owner.side).choice(names)
                    info = g.get(name)
                    if info is None:
                        self.unsup['무작위 효과 사전 없음: ' + name] += 1
                        continue
                    eff = dict(kind='buff', target='자신', name=name, chance=1.0,
                               dur=ln.eff.get('random_dur', info['dur'] or (math.inf if repeats > 1 else 2)),
                               props=info['props'], max=repeats if repeats > 1 else None, times=1, judge=(x.side != owner.side))
                    self.add_effect(owner, x, eff, ctx, hot=info.get('hot', 0), fixed='해제불가' in name)
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
                if self.R(owner.side).random() >= int(m.group(2)) / 100.0:
                    continue
                if x.side != owner.side and '효과 적중 판정' in rest and not self.roll_hit(owner, ctx, x, None):
                    continue
                self._fired(owner)
                self.set_gauge(x, x.gauge + dv)
            return
        m = RX_EXTRA_P.match(rest)
        if m:
            sk = owner.d.skills.get(m.group(2)) or owner.d.trigger_skills.get(m.group(2))
            if sk is not None and self.R(owner.side).random() < int(m.group(1)) / 100.0:
                self._fired(owner)
                target = ctx.src if (ctx.src is not None and ctx.src.side != owner.side) else None
                if ln.eff.get('random_enemy'):
                    pool = self.alive(1 - owner.side)
                    if not pool:
                        return
                    target = self.R(owner.side).choice(pool)
                self.cast(owner, sk, extra=True, target=target, parent=ctx)
            return
        m = RX_TOUGH_HEAL.match(rest)
        if m:   # 강인도 N 회복(격파 중이면 회복하지 않음 — 격파는 다음 자기 턴에 전회복, assumed)
            for x in self.resolve(owner, m.group(1), ctx) or []:
                if self.mc['toughness'] == 'on' and not x.broken:
                    x.sa = min(x.sa_max, x.sa + int(m.group(2)))
            return
        m = RX_HEAL_P.match(rest)
        if m:   # N% 확률로 회복(잠재력 「별빛의 궤적-BX」 피격 시 25%)
            tg = self.resolve(owner, m.group(1), ctx, kind='heal')
            for x in tg or []:
                if self.R(owner.side).random() >= int(m.group(2)) / 100.0:
                    continue
                self._fired(owner)
                base_u = owner if m.group(3) == '자신' else x
                stat = {'생명력': base_u.maxhp, '최대 생명력': base_u.maxhp, '공격력': self.atk_stat(base_u),
                        '방어력': self.def_stat(base_u)}[m.group(4)]
                self.heal(owner, x, stat * float(m.group(5)) / 100.0, owner.mods()['heal_give'])
            return
        self.unsup['effect: ' + rest[:60]] += 1

    def chain(self, owner, eff, ctx):
        if eff.get('random_enemy'):
            pool = self.alive(1 - owner.side)
            tg = [self.R(owner.side).choice(pool)] if pool else []
        else:
            tg = self.resolve(owner, eff['target'], ctx)
        if not tg:
            return
        m = owner.mods()
        tstat = eff['stat'] == 'target_hp'      # P5 「대상 생명력×N%」 연쇄 피해
        val = 0.0 if tstat else {'atk': self.atk_stat(owner, ctx), 'hp': owner.maxhp, 'def': self.def_stat(owner)}[eff['stat']]
        for v in tg:
            if v.side == owner.side or v.dead:
                continue
            if tstat:
                val = v.maxhp
            de = self.def_stat(v)
            dr = de / (de + _rules.DEF_K)
            dr = max(0.0, dr - dr * min(1.0, m['pen']))
            inc = m['inc'] + m['inc_vs'].get(v.element, 0.0) + (m['inc_break'] if v.broken else 0.0)
            # AddDamageController reads the caster's live DAMAGE_UP, including
            # skill-local stat effects (NKM:5601-5611). Do not inherit the
            # incoming attack's modifiers when a defender reacts.
            if self.mc['chain_skill_damage_up'] and ctx is not None and ctx.src is owner:
                inc += ctx.inc + ctx.local_by[v]['inc']
            dmg = max(1.0, math.floor(val * eff['coef'] * (1 + inc) * _rules.BASE_MULT * (1 - dr) * self.rand(owner.side) * self.pen[owner.side]))
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
        return self.R(owner.side).random() < calc_hit(a, b)

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
            if self.R(owner.side).random() >= eff['chance']:
                continue
            self._fired(owner)
            self.add_effect(owner, x, eff, ctx, hot=hot, fixed='해제 불가' in raw)

    def add_effect(self, owner, x, eff, ctx, hot=0.0, fixed=False):
        name = eff['name']
        opp = x.side != owner.side
        info = getattr(owner.d, 'effect_info', {}).get(name, {})
        marker = eff.get('cast_marker') or bool(CHECK_NAME.search(name)) or '판별용' in name
        category = ('marker' if marker else info.get('category')) or ('debuff' if opp else 'buff')
        resist = category == 'debuff' and not eff.get('ignore_resist')
        if resist and ctx is not None and x in ctx.evaded:
            return     # 회피한 대상에는 약화가 걸리지 않음(공식 2026-06-04 오류 수정 공지)
        if resist and x.on('면역'):
            return     # 〈면역〉 (약화효과 면역): 상대가 거는 효과(약화) 전부 막음
        if resist and (eff.get('judge') or name in getattr(x.d, 'immune', ())):
            if not self.roll_hit(owner, ctx, x, name):
                return
        dot = eff.get('dot')
        if dot is None and name in _rules.KNOWN_DOT and not eff['props']:
            dot = _rules.KNOWN_DOT[name]
        harmful = category == 'debuff'
        if eff.get('unique_enemy'):
            for other in self.alive(x.side):
                if other is not x and name in other.eff:
                    del other.eff[name]
                    self.dirty(other)
        e = x.eff.get(name)
        cast_ctx = getattr(self, '_cast_ctx', None)
        if eff.get('cast_marker') and cast_ctx is not None and (x, name) not in cast_ctx.markers:
            cast_ctx.markers[(x, name)] = copy.copy(e) if e is not None else None
        dur = _dur(eff['dur'])
        # A reaction's SKILL_END can taunt the unit whose turn is still in
        # progress. Native duration ticking excludes that application turn
        # (NKM:3723,4234-4252); otherwise a one-turn taunt never gets used.
        fresh = (x is owner and owner.acting) or (
            self.mc['taunt_skill_end_duration'] and name == '도발' and x.acting
            and self._cur_line is not None and self._cur_line.phase == '스킬 사용 후')
        if e is None:
            mx = eff['max'] or (5 if dot else 1)
            e = Eff(name, eff['props'], mx, dur, owner, harmful)
            e.category = category
            e.fixed = fixed
            transient = eff['dur'] is None and ctx is not None and ctx.local is not None   # 피격 직전에 받은 지속 표기 없는 효과 = 이번 행동만
            if self.mc['check_buff_expiry'] == 'action' and (transient or (eff['dur'] is None and CHECK_NAME.search(name) and not eff['props'])):
                e.check = True
                self.check_pending.append((x, name))
            x.eff[name] = e
            e.fresh = fresh
        else:
            e.category, e.harmful = category, harmful
            if eff['dur'] is not None:
                e.dur = max(e.dur, dur) if e.dur != math.inf else e.dur
                if fresh:
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
                and not self.no_react(x)]
        pool.sort(key=lambda x: (-self.live_atk(x), -x.d.stats['atk'], x.pos))
        for x in pool[:n]:
            ctx.coop_used = True
            self.cast(x, x.d.skills['기본기'], extra=True, target=ctx.target, via='forced_coop')


# ------------------------------------------------------------------ 지원성 검사
# 속성 숫자가 없어도 엔진이 이름으로 동작을 아는 효과
HANDLED_NAMES = set(['도발', '은신', '현장 대기', '기절', '수면', '침묵', '필중', '면역', '강제 협공', '추가 턴', '보호막', '스킬 피해 무효',
                     '강인도 피해 무효', '불사', '강화 불가', '강제 치명타 발생']) | set(CD_RESET_NAMES)
LOCAL_OK = ('피해 증가', '공격력%', '치명타 확률', '치명타 피해', '방어 관통', '효과 적중', '주는 회복량', '명중률',
            '강인도 피해', '강인도 고정 피해', '브레이크 대상 피해 증가', '대상 약화효과 1개당 피해 증가')
LOCAL_PREHIT_OK = ('방어력%', '피해 분담(수호)', '피해 감소', '받는 피해 감소')


def _prop_known(k):
    """Unit.mods() 가 이 속성 이름을 어떤 값으로든 반영하는가"""
    probe = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0, coop=0.0, eh=0.0,
                 er=0.0, der=0.0, critred=0.0, guard=0.0, heal_give=0.0, heal_recv=0.0, inc_single=0.0, inc_aoe=0.0,
                 evade=0.0, acc=0.0, tough=0.0, tough_fixed=0.0, inc_break=0.0, revenge=0.0, inc_vs={}, inc_slot={}, red={})
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
    if name in DAMAGE_LIMIT:
        return None      # 「피해 제한」: 효과별 동작을 Battle._limit_damage 가 실행
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
    """전투에 나오는 유닛들의 미지원 줄(시점·효과·조건) + 일반/반응 트리거·변형 스킬. 실행 전 검사."""
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
        for ln in normalized_lines(d):
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
            if (not reason and '자동 지정' in tgt and not tgt.startswith('적') and nm != '강제 협공' and ln.eff['kind'] not in ('remove', 'random_ally_basic')
                    and not (CHECK_NAME.search(nm) or '판별용' in nm) and auto_rule(d, ln, None) is None):
                reason = 'selector: 자동 지정 대상 규칙을 설명문에서 못 찾음(기본 규칙 사용)'
            bad = [p for p, _ in ln.params if p not in COND_KEYS]
            if not reason and bad:
                reason = 'condition: ' + ','.join(bad)
            if reason:
                out.append(dict(unit=d.name, foe=foe, slot=ln.slot, reason=reason, raw=ln.raw,
                                critical=bool(foe and CRITICAL_RX.search(rest) and '강인도' not in rest)))
        for ts in d.trigger_skills.values():
            if not supported_trigger(d, ts):
                out.append(dict(unit=d.name, foe=foe, slot=ts.slot, reason='skill',
                                raw='트리거 스킬 미반영: ' + ts.name, critical=False))
        supported_variants = {sk.name for _, sk in variant_rules(d).values()}
        for msg in getattr(d, 'unmodeled', []):
            if msg.startswith('myinfo '):
                out.append(dict(unit=d.name, foe=foe, slot='잠재력', reason='data', raw=msg, critical=False))
            if msg.startswith('변형'):
                if msg.split(': ', 1)[-1] in supported_variants:
                    continue
                out.append(dict(unit=d.name, foe=foe, slot=None, reason='skill', raw=msg, critical=False))
    return out
