# -*- coding: utf-8 -*-
"""길드 방어전 시즌4 EX 보스 BFB 전용 모듈(확률 엔진 mc.Battle 용). 범용 SE 해석기가 아니라 BFB 상태 기계를 직접 코딩한다.

수치: data/guild_bfb.json(tools/build_guild_bfb.py 가 게임 표에서 추출), 별의 도전 단계·선택 효과: data/guild_defense.json.
켜는 조건: mc.guild_boss == 'on'(기본 off) 이고 웨이브에 이 모듈이 만든 BFB 정의가 있을 때만. 다른 콘텐츠·골든에는 영향이 없다.
명세·확신도: AI/temp/partynavigator/work/guild_defense/bfb_skill_spec.md

상태 기계(게임 표 원문 기준, 괄호 = 조건 id):
- 질투의 시선(58801): 아군 유닛 스킬 후(협공·추가 발동·소환체 포함), 보스가 «정실 어필 상태»(ANIMSET2)가 아니면 공격력 최고 아군(이미 있으면 그 사람)에게 신부 경쟁 +1(공격력 +3%/중첩, 최대 10), 보스 카운트 +1.
- 정실 어필(52093): 보스 공격 후, 카운트 5 이상 + 신부 경쟁 보유자 있음 -> 강화 해제·게이지 0·나머지 아군 들러리(능력치 0·받는 피해 +100%·게이지 증가 무효)·
  보스 보호막(최대 생명력 22.5%, 강인도 피해 무효)·보스 공격 -70%·속도 -20%, 특수기 -> 독점 선언, 보호막 중 공격은 신부 경쟁 보유자에게.
- 캣파이트: 보호막 중 보스 공격 5회(52094) 또는 처치(52095) -> 상태 해제 + 축복의 대피로연 강제 발동(2144 후 원래 스킬).
  보호막을 깬 뒤 맞으면(55148) -> 상태 해제·아군 부케(공격 +30% 2턴)·아군 게이지 +100%·보스 게이지 -100%·보스 자신에게 최대 생명력 15% 연쇄 피해.
- 신부의 응징(55521): 보호막 중 들러리에게 맞으면 들러리 전원에게 보스 생명력 30% 연쇄 피해.
- 별의 도전(보스에게만): 스킬 후 피해 증가 중첩, 피격 후 타격자 최대 생명력 감소 중첩, 속도 증가, 시작 면역(약화 면역), 능력치 배율.
카운트 기본값 guild_count=all 은 클라 유닛 시전 경로 기준임(main 은 본 행동만 세던 옛 가정).
가정(추정): 연쇄 피해 = 엔진 chain 공식(최대 생명력 x 계수 x 1.85 x 방어 감소),
능력치 배율 = 1 + 표값/10000 을 배치 AddStat 보정 뒤에 곱함, 선택 효과 «쇠락»은 단계 효과와 별도 중첩."""
import copy
import json
import math
import os

from .data import SRC
from .parser import Line, Skill

_DATA = {}


def load(src=SRC):
    if src not in _DATA:
        with open(os.path.join(src, 'data', 'guild_bfb.json'), encoding='utf-8') as f:
            bfb = json.load(f)
        with open(os.path.join(src, 'data', 'guild_defense.json'), encoding='utf-8') as f:
            gd = json.load(f)
        _DATA[src] = (bfb, gd)
    return _DATA[src]


# 효과 이름(엔진 Eff 키)
B1 = '신부 경쟁(해제불가)'
B2 = '들러리(해제불가)'
B8 = '보호막(해제불가)'
B9 = 'BFB 공격력·속도 감소'
TOUGH_BAN = '강인도 피해 무효'
PEN = 'BFB 방어 관통'
STACK = '폭주 : 잠식'
DRAIN = '폭주 : 쇠락'
DRAIN_SET = '폭주 : 쇠락(선택)'
BOUQUET = '부케'
IMMUNE = '면역'
SPEED = '속도 비율 스탯(별의 도전)'
SET_DMG = '피해량 증가율(소멸)'
SET_RED = '피해량 감소율(불멸)'

# 알리시아의 지원(시즌 선택 1종, 표 근거: AI/temp/partynavigator/work/guild_defense/support_spec.md)
SUPPORTS = ('none', 'gust', 'focus', 'strike', 'mountain', 'fire')
SUP_STAT = '알리시아 지원(능력치)'
SUP_HIT = '알리시아 지원(불의 고동 적중)'
SUP_TMP_INC = '알리시아 지원(임시 피해 증가)'
SUP_TMP_RED = '알리시아 지원(임시 받는 피해 감소)'


class GuildFoe:
    """FoeDef 와 같은 모양의 길방 적 정의(시험·api 의 _CustomFoe 와 같은 계약)."""
    is_foe = True

    def __init__(self, key, name, u, stats, skills, lines, boss, bfb=None):
        self.key, self.name = key, name
        self.id, self.variant = -1, '적'
        self.role, self.element = u['role'], u['element']
        self.boss = boss
        self.grade = '보스' if boss else '일반'
        self.attack_kind = '충격'
        self.stats = stats
        self.immune = set()
        self.skills = skills
        self.trigger_skills, self.unmodeled = {}, []
        self.lines = lines
        self.desc = {}
        from collections import defaultdict
        self.passive = defaultdict(float)
        self.nb, self.manual, self.gear_atkp = {}, None, 0.0
        self.effect_info = {}
        self.spd_base = stats['spd']
        self.react, self.auto, self.auto_lines = {}, {}, {}
        self.spawn = u['spawn']
        self.slot = u['pos']
        self.bfb = bfb


def _skill(slot, name, coef, cd, tough, all_=False, tg='적 단일', lines=()):
    sk = Skill(dict(sl=slot, n=name, ty='액티브', tg='적 전체' if all_ else tg, act='공격', cf=[int(coef), 0, 0, 0],
                    all=all_, cd=cd or None, nv=0))
    sk.ab = tough
    sk.semantic_lines = [Line(r, slot, 'active') for r in lines]
    return sk


def _stats(u, scale=(0, 0, 0)):
    s = dict(u['stats'])
    a = u['addStat']
    hp = math.floor(s['hp'] * (1 + a['hpp'] / 10000) * (1 + scale[1] / 10000))
    atk = math.floor(s['atk'] * (1 + a['atkp'] / 10000) * (1 + scale[0] / 10000))
    df = math.floor(s['def'] * (1 + a['defp'] / 10000) * (1 + scale[2] / 10000))
    spd = math.floor(s['spd'] * (1 + a['spdp'] / 10000) + 1e-9)
    return dict(hp=hp, atk=atk, **{'def': df}, spd=spd, cr=s['cr'], cd=s['cd'], eh=s['eh'], er=s['er'], der=s['der'], sa=s['sa'])


def level_row(level, src=SRC):
    """별의 도전 단계 행(data/guild_defense.json challenge.levels). 0 = 없음"""
    if not level:
        return None
    _, gd = load(src)
    rows = gd['challenge']['levels']
    if not 1 <= level <= len(rows):
        raise ValueError('별의 도전 단계는 0~%d: %r' % (len(rows), level))
    return rows[level - 1]


def build_waves(level=0, sets=None, src=SRC, support=None):
    """EX(7단계) 배치 -> (waves[[GuildFoe]], meta). level = 별의 도전 0~12, sets = 선택 효과 단계 [소멸, 불멸, 쇠락, 허무](0~3),
    support = 알리시아의 지원 none|gust|focus|strike|mountain|fire(None = none)."""
    support = support or 'none'
    if support not in SUPPORTS:
        raise ValueError('지원은 %s: %r' % ('|'.join(SUPPORTS), support))
    bfb, gd = load(src)
    lv = level_row(level, src)
    sets = list(sets or [0, 0, 0, 0])
    if len(sets) != 4 or any(not isinstance(t, int) or not 0 <= t <= 3 for t in sets):
        raise ValueError('선택 효과는 0~3 정수 4개: %r' % (sets,))
    m = bfb['minion']
    ma, ms = m['attack'], m['special']
    mlines = []
    waves = [[], []]
    for i in range(2):
        sk = {'기본기': _skill('기본기', '불청객의 인사', ma['coef'], ma['cd'], 1, lines=[
                  '[스킬 사용 후] 스킬 대상에게 %g%% 확률로 행동 게이지 %g%%p 감소 {효과 적중 판정}' % (ma['chance'] / 100, ma['gaugeDown'] / 100)]),
              '특수기': _skill('특수기', '축의금 강탈', ms['coef'], ms['cd'], 2, lines=[
                  '[스킬 사용 후] 자신에게 〈속도 증가〉 (%d턴 / 속도%% +%g%%)' % (ms['dur'], ms['speedUp'] / 100)])}
        u = dict(m, pos=m['pos'] + i)
        waves[0].append(GuildFoe('guild:minion:%d' % i, m['names'], u, _stats(m), sk, mlines, False))
    b = bfb['boss']
    scale = (lv['atk'] * 100, lv['hp'] * 100, lv['def'] * 100) if lv else (0, 0, 0)
    st = _stats(b, scale)
    st['cr'] = max(0, st['cr'] + b['critRate'])
    at, hy = b['attack'], b['hyper']
    skills = {'기본기': _skill('기본기', '퍼스트 댄스', at['coef'], at['cd'], at['tough']),
              '궁극기': _skill('궁극기', '황홀한 허니문', hy['coef'], hy['cd'], hy['tough'],
                            lines=['[스킬 사용 후] 자신에게 행동 게이지 %g%%p 증가' % (hy['gaugeUp'] / 100)])}
    s2, h2 = b['special2'], b['hyper2']
    alt = {
        'special2': _skill('특수기', '독점 선언', s2['coef'], s2['cd'], s2['tough'], lines=[
            '[스킬 사용 후] 스킬 대상에게 〈공격력 감소〉 (%d턴 / 공격력%% %g%%) {효과 적중 판정}' % (s2['atkDownDur'], s2['atkDown'] / 100),
            '[스킬 사용 후] 자신에게 〈공격력 증가〉 (%d턴 / 공격력%% +%g%%)' % (s2['atkUpDur'], s2['atkUp'] / 100)]),
        'hyper2': _skill('궁극기', '축복의 대피로연', h2['coef'], h2['cd'], h2['tough'], all_=True, lines=[
            '[스킬 사용 후] 적 전체에게 〈공격력 감소〉 (%d턴 / 공격력%% %g%%) {효과 적중 판정}' % (h2['dur'], h2['atkDown'] / 100),
            '[스킬 사용 후] 적 전체에게 〈속도 감소〉 (%d턴 / 속도%% %g%%) {효과 적중 판정}' % (h2['dur'], h2['spdDown'] / 100),
            '[스킬 사용 후] 자신에게 행동 게이지 %g%%p 증가' % (h2['gaugeUp'] / 100)]),
    }
    items = gd['sets']['items']
    cfg = dict(data=b, alt=alt, level=level, row=lv, sets=sets, support=support,
               set_dmg=_set_value(items[0], sets[0]), set_red=_set_value(items[1], sets[1]),
               set_drain=_set_value(items[2], sets[2]), set_immune=_set_value(items[3], sets[3]))
    waves[1].append(GuildFoe('guild:bfb', b['name'], b, st, skills, [], True, bfb=cfg))
    meta = dict(content='guild', tab='길드 방어전', name='EX 별의 도전 %d단계' % level, level=bfb['battleLevel'],
                recommended_power=bfb['power'], wave_count=2, battle_mode='boss_kill', guild=dict(level=level, sets=sets, support=support),
                turn_limit=bfb['limitTurn'])
    return waves, meta


def _set_value(item, tier):
    """선택 효과 문구의 숫자(%) — 소멸 +10/20/30, 불멸 -20/30/40, 쇠락 -3/4/5, 허무 1/2/3턴"""
    if not tier:
        return 0
    import re
    return int(re.findall(r'\d+', item['tiers'][tier - 1]['text'])[-1])


class Controller:
    """mc.Battle 훅: on_wave / pick_target / after_cast / pre_hit / post_hit. Battle 이 guild_boss=on 일 때만 만든다."""

    def __init__(self, b):
        self.b = b
        self.boss = None
        self.cfg = None
        self.count = 0          # 신부 경쟁 카운팅(BOSS_7)
        self.anim = False       # 정실 어필 상태(ANIMSET2)
        self.shield_hits = 0    # 보호막 중 공격 수(BOSS_3)
        self.mark = None        # 보호막 중 우선 공격 대상(BOSS_6)
        self.stats = dict(appeal=0, shield_break=0, shield_timeout=0, punish=0)
        self.support = next((d.bfb['support'] for w in b.waves for d in w if getattr(d, 'bfb', None)), 'none')
        self.sup_done = False
        self.focus_turn = {}    # 날카로운 집중력: 유닛별 «1턴에 1번» 기록
        self.strike_roll = {}   # 강인한 타격: 유닛별 이번 시전 발동 여부(50%)

    # ---------- 효과 도우미
    def _put(self, x, name, props, dur=math.inf, cat='buff', fixed=True, maxs=1, add=1):
        from ..mc import Eff
        e = x.eff.get(name)
        if e is None:
            e = Eff(name, dict(props), maxs, dur, self.boss, cat == 'debuff')
            e.category, e.fixed = cat, fixed
            e.fresh = x.acting
            x.eff[name] = e
        else:
            e.dur = max(e.dur, dur)
        e.stacks = min(e.maxs, e.stacks + add)
        self.b.dirty(x)
        return e

    def _drop(self, x, name):
        if x.eff.pop(name, None) is not None:
            self.b.dirty(x)

    def barrier(self):
        e = self.boss.eff.get(B8) if self.boss is not None else None
        return e is not None and e.shield > 0

    # ---------- 알리시아의 지원
    def _sup_has(self, u):
        """이 유닛에 걸리는 지원인가(직업 전용은 해당 직업만. 대상 필터는 TargetRoleType 근거, 표 해석은 추정)"""
        s = self.support
        if s in ('mountain', 'fire'):
            return True
        return u.role == {'gust': '서포터', 'focus': '캐스터', 'strike': '스트라이커'}.get(s)

    def _sup_put(self, x, name, props, maxs=1):
        """지원 효과. 강화 효과 개수에 안 세도록 marker(보스 관통 표지와 같은 방식)"""
        from ..mc import Eff
        e = x.eff.get(name)
        if e is None:
            e = Eff(name, dict(props), maxs, math.inf, x, False)
            e.category, e.fixed = 'marker', True
            e.fresh = x.acting
            x.eff[name] = e
        e.stacks = min(e.maxs, e.stacks + 1)
        self.b.dirty(x)

    def _sup_start(self):
        """전투 시작 시 한 번: 방어·치명·공격 상승(40152 방어 +50%, 40031 치명 +30%, 40111 치명 피해 +30%, 45011 공격 +15%)"""
        if self.sup_done or self.support == 'none':
            return
        self.sup_done = True
        props = {'gust': {'방어력%': 50}, 'focus': {'치명타 확률': 30}, 'strike': {'치명타 피해': 30},
                 'fire': {'공격력%': 15}}.get(self.support)
        if props:
            for u in self.b.allies:
                if self._sup_has(u):
                    self._sup_put(u, SUP_STAT, props)

    def _sup_after_cast(self, u, sk, extra):
        s = self.support
        if u.side != 0 or u.dead or not self._sup_has(u):
            return
        if s == 'gust' and not sk.is_attack:
            for x in self.b.alive(0):         # 4015202: 비타격 스킬 후 자신 제외 아군 전체 행동 게이지 +30%
                if x is not u:
                    self.b.set_gauge(x, x.gauge + 3000)
        elif s == 'focus' and sk.slot == '기본기' and self.focus_turn.get(id(u)) != self.b.global_turns:
            self.focus_turn[id(u)] = self.b.global_turns
            for slot in u.cd:                 # 기본기 사용 시 모든 스킬 쿨 -1(1턴에 1번)
                u.cd[slot] = max(0.0, u.cd[slot] - 1)
        elif s == 'fire':
            self._sup_put(u, SUP_HIT, {'효과 적중': 6}, maxs=5)

    def _sup_pre_hit(self, a, v):
        s = self.support
        if s == 'strike' and a is not None and a.side == 0 and self._sup_has(a):
            # 강인한 타격(4011102): 스킬 시작 때 m_fActiveRate 5000 = 50% 로 굴려(NKM 16466 BuffActivateRate) 그 시전 동안 강화 효과 개수당 피해 +10%.
            # 시전마다 한 번 굴림 — 지금 시전(Battle._cast_ctx)이 바뀌면 다시 굴림(겹친 추가 발동도 따로)
            cur = getattr(self.b, '_cast_ctx', None)
            got = self.strike_roll.get(id(a))
            if got is None or got[0] is not cur:
                got = self.strike_roll[id(a)] = (cur, self.b.R(0).random() < 0.5)
            ok = got[1]
            n = a.n_good() if ok else 0
            if n:
                self._sup_put_tmp(a, SUP_TMP_INC, {'피해 증가': 10 * n})
            else:
                a.eff.pop(SUP_TMP_INC, None)
        elif s == 'mountain':
            if a is not None and a.side == 0 and a.hp * 2 > a.maxhp:
                self._sup_put_tmp(a, SUP_TMP_INC, {'피해 증가': 10})              # 45041: 생명력 50% 초과면 피해 +10%
            if v.side == 0 and v.hp * 2 < v.maxhp:
                self._sup_put_tmp(v, SUP_TMP_RED, {'받는 피해 감소': 10})         # 피격 시 50% 미만이면 받는 피해 -10%

    def _sup_put_tmp(self, x, name, props):
        x.eff.pop(name, None)
        self._sup_put(x, name, props)

    def _sup_post_hit(self, a, v):
        for x in (a, v):
            if x is not None and (x.eff.pop(SUP_TMP_INC, None) is not None or x.eff.pop(SUP_TMP_RED, None) is not None):
                self.b.dirty(x)

    # ---------- 웨이브
    def on_wave(self):
        b = self.b
        self._sup_start()
        boss = next((u for u in b.foes if getattr(u.d, 'bfb', None)), None)
        if boss is None:
            return
        # 스킬 교체가 다른 판·정의에 새지 않게 정의를 판마다 얕게 복사
        boss.d = copy.copy(boss.d)
        boss.d.skills = dict(boss.d.skills)
        self.boss, self.cfg = boss, boss.d.bfb
        self.base = dict(boss.d.skills)
        d = self.cfg['data']
        self._put(boss, PEN, {'방어 관통': d['pen'] / 100}, cat='marker')
        row = self.cfg['row']
        if row and row['speed']:
            self._put(boss, SPEED, {'속도%': row['speed']})
        immune = max(row['immune'] if row else 0, self.cfg['set_immune'])
        if immune:
            self._put(boss, IMMUNE, {}, dur=immune)
        if self.cfg['set_dmg']:
            self._put(boss, SET_DMG, {'피해 증가': self.cfg['set_dmg']})
        if self.cfg['set_red']:
            self._put(boss, SET_RED, {'받는 피해 감소': self.cfg['set_red']})

    # ---------- 대상
    def is_boss(self, u):
        return u is self.boss

    def pick_target(self, att, sk, pool):
        """보호막 중 «신부 경쟁 확인용» 보유자 우선(자동 대상 1020/1021/1025), 없으면 전열 80%·디펜더 80%(1020 나머지 = 규칙 1001 과 같은 필터)"""
        if self.mark is not None and not self.mark.dead and self.mark in pool:
            return self.mark
        from ..mc import RULE1001
        return self.b.filter_pick(att, pool, RULE1001)

    # ---------- 시전 후
    def after_cast(self, u, sk, ctx, extra):
        if self.support != 'none':
            self._sup_after_cast(u, sk, extra)
        boss = self.boss
        if boss is None or boss.dead:
            return
        if u.side == 0:
            # 질투의 시선(58801 AfterEnemyAction): 클라 코드상 시전이 끝날 때마다 발행되고 협공·반격·반응·엔포스(추가 발동)도 같은 경로라
            # 시전 종류를 가리지 않는다(DoSkill.cs:3025·3695, 조건에 IsNotEnforceSkill 없음).
            # 소환체도 OBF_26401로 생성(NKM:5198)되어 SKILL_END → AfterEnemyAction 발행(NKM:15662·15705·16040~16079)에 포함.
            # guild_count=main 이면 옛 가정(본 행동만) 재현
            if not self.anim and (not extra and ctx.via is None or self.b.guild_count == 'all'):
                self._compete()
            if sk.is_attack and self.anim and not self.barrier():
                self._restore()                     # 37201
            return
        if u is not boss:
            return
        row = self.cfg['row']
        if row and row['skillStack']:
            self._put(boss, STACK, {'피해 증가': row['skillStack']}, maxs=10)    # 940001~3
        if sk is self.cfg['alt']['hyper2']:
            self._restore(full=True)               # 2144
            return
        if not sk.is_attack:
            return
        if self.barrier():
            self.shield_hits = min(self.cfg['data']['shieldHits'], self.shield_hits + 1)   # 32002
        if self.shield_hits and (self.shield_hits >= self.cfg['data']['shieldHits'] or ctx.kill):
            self.stats['shield_timeout'] += 1
            self._end_phase()                       # 52094 / 52095
            return
        if self._appeal_ready():
            # 정실 어필은 반응 스킬: 보스 시전이 끝날 때 예약되고 반응 큐에서 실행된다(DoSkill:3234~3245, 큐 2833~).
            # 이번 행동에 대한 반격은 그보다 먼저 나가므로 반격하는 아군은 아직 들러리·보호막이 없는 상태로 친다.
            self._defer(lambda: self._appeal() if self._appeal_ready() and not self.boss.dead else None)    # 52093

    def _appeal_ready(self):
        return self.count >= self.cfg['data']['bridal']['trigger'] and any(v.has(B1) for v in self.b.alive(0))

    def _defer(self, fn):
        """반응 큐가 열려 있으면 예약(큐 밖이면 바로 실행) — mc.reaction_timing=queue 일 때만 큐가 있음"""
        q = getattr(self.b, '_react_q', None)
        if q is None:
            fn()
        else:
            q.append((None, fn, None, None))

    def _compete(self):
        """질투의 시선(58801·1021): 신부 경쟁 보유자 중(없으면 전원 중) 공격력 최고에게 +1, 카운트 +1"""
        pool = self.b.alive(0)
        if not pool:
            return
        cand = [v for v in pool if v.has(B1)] or pool
        best = max(self.b.live_atk(v) for v in cand)
        top = [v for v in cand if self.b.live_atk(v) == best]
        v = top[0] if len(top) == 1 else self.b.R(1).choice(top)
        br = self.cfg['data']['bridal']
        self._put(v, B1, {'공격력%': br['atkPerStack'] / 100}, maxs=br['max'])
        self.count = min(br['countMax'], self.count + 1)

    def _appeal(self):
        b, boss, d = self.b, self.boss, self.cfg['data']
        ap = d['appeal']
        self.stats['appeal'] += 1
        b.log(actor=boss.name, side=1, pos=boss.pos, skill='특수기', skill_name='정실 어필', targets=[], via='reaction', nb=False,
              all=True, tgt_side=0, tgt_boss=False)
        boss.d.skills['특수기'] = self.cfg['alt']['special2']
        boss.cd['특수기'] = 0
        self.anim = True
        allies = b.alive(0)
        for v in allies:
            for name in [n for n, e in v.eff.items() if e.category == 'buff' and not e.fixed and not e.check]:
                del v.eff[name]
            b.dirty(v)
            v.gauge = 0.0
        for v in allies:
            if not v.has(B1):
                self._put(v, B2, {'받는 피해 감소': -ap['maidDmgTaken'] / 100}, cat='debuff')
                v.zero_stats = True
                b.dirty(v)
        for name in [n for n, e in boss.eff.items() if e.category == 'debuff' and not e.fixed]:
            del boss.eff[name]
        boss.gauge = 0.0
        e = self._put(boss, B8, {})
        e.shield = math.floor(boss.maxhp * ap['barrierRate'] / 10000)
        self._put(boss, TOUGH_BAN, {}, cat='marker')
        holders = [v for v in allies if v.has(B1)]
        if holders:
            best = max(b.live_atk(v) for v in holders)
            self.mark = next(v for v in holders if b.live_atk(v) == best)
        self._put(boss, B9, {'속도%': ap['slowSpd'] / 100, '공격력%': ap['slowAtk'] / 100}, cat='marker')
        self.count = 0                               # 패시브1 03(4001)
        self.shield_hits = 0
        row = self.cfg['row']
        if row and row['skillStack']:
            self._put(boss, STACK, {'피해 증가': row['skillStack']}, maxs=10)

    def _clear_marks(self):
        for v in self.b.side_units(0):
            self._drop(v, B1)
            if v.has(B2):
                self._drop(v, B2)
            v.zero_stats = False
            self.b.dirty(v)
        self.mark = None

    def _end_phase(self):
        """52094/52095: 상태 해제 후 축복의 대피로연 강제 발동"""
        boss = self.boss
        self._clear_marks()
        for n in (B8, TOUGH_BAN, B9):
            self._drop(boss, n)
        self.shield_hits = 0
        boss.d.skills['궁극기'] = self.cfg['alt']['hyper2']

        def cast():
            self.b.cast(boss, self.cfg['alt']['hyper2'], extra=True, via='enforce')
            if not boss.dead and boss.d.skills.get('궁극기') is self.cfg['alt']['hyper2']:
                self._restore(full=True)
        # 상태 해제(52094)는 즉시, 축복의 대피로연 강제 시전은 예약 큐: 이번 행동에 대한 반격이 먼저 나가 보호막이 없는 보스를 치면 부케가 나온다
        self._defer(cast)

    def _restore(self, full=False):
        """37201(특수기만) / 2144(궁극기·특수기): 원래 스킬, ANIMSET2 해제"""
        sk = self.boss.d.skills
        sk.pop('특수기', None)
        if full:
            sk['궁극기'] = self.base['궁극기']
        self.anim = False

    # ---------- 피격
    def pre_hit(self, a, v):
        """신부의 응징(55521): 보호막 중 들러리에게 맞으면 들러리 전원에게 연쇄 피해"""
        if self.support != 'none':
            self._sup_pre_hit(a, v)
        if v is not self.boss or a.side != 0 or not self.barrier() or not a.has(B2):
            return
        self.stats['punish'] += 1
        coef = self.cfg['data']['punishChainHp'] / 10000
        for x in [x for x in self.b.alive(0) if x.has(B2)]:
            self._chain(v, x, coef, v)

    def post_hit(self, a, v):
        if self.support != 'none':
            self._sup_post_hit(a, v)
        boss = self.boss
        if v is not boss or a is None or a.side != 0 or boss.dead:
            return
        row = self.cfg['row']
        if row and row['hpDrain'] and not a.dead:
            self._put(a, DRAIN, {'생명력%': -row['hpDrain']}, cat='debuff', maxs=10)     # 940011~13
        if self.cfg['set_drain'] and not a.dead:
            self._put(a, DRAIN_SET, {'생명력%': -self.cfg['set_drain']}, cat='debuff', maxs=10)
        if self.anim and not self.barrier():
            self._drop(boss, TOUGH_BAN)
            if boss.eff.get(B8) is not None:
                self._drop(boss, B8)
            self._bouquet(a)                        # 55148 (표에 타격자·신부 경쟁 조건 없음)

    def after_break_skill(self, had_barrier):
        """브레이크 스킬(오비탈) 피해 뒤: 클라는 같은 시전 경로(DoSkill:2974)라 보호막이 깨지면 부케(55148)가 나온다.
        피해는 apply_damage 직접 호출이라 pre_hit/post_hit 을 안 거치므로 보호막 파괴 판정만 여기서 한다(드레인·쇠락은 캐스터가 없어 생략).
        질투의 시선(58801 AfterEnemyAction) 카운트는 하지 않는다: 클라 SKILL_END 처리(DoSkill:3232)가 부르는 After*Action 발행 함수(DoSkill:3654)는
        시전자가 유닛 클래스(sealed ഉഈഅഇ…)가 아니면 바로 반환하는데, 브레이크 스킬 시전자는 별도 클래스(ഌഇആഅ…, DoSkill:2958)다."""
        boss = self.boss
        if boss is None or boss.dead or not (had_barrier and self.anim and not self.barrier()):
            return
        self._drop(boss, TOUGH_BAN)
        if boss.eff.get(B8) is not None:
            self._drop(boss, B8)
        self._bouquet(None)

    def _bouquet(self, a):
        b, boss, bq = self.b, self.boss, self.cfg['data']['bouquet']
        self.stats['shield_break'] += 1
        self._clear_marks()
        for x in b.alive(0):
            self._put(x, BOUQUET, {'공격력%': bq['atk'] / 100}, dur=bq['dur'], fixed=False)
            b.set_gauge(x, x.gauge + bq['allyGauge'])
        b.set_gauge(boss, boss.gauge - bq['selfGaugeDown'])
        self.shield_hits = 0
        self._drop(boss, B9)
        self._chain(boss, boss, bq['selfChainHp'] / 10000, None)     # 보스가 자기에게 주는 연쇄: 아군 딜로 세지 않음(영상 전투 통계 합계 대조, work/guild_defense/dmg_split.md)

    def _chain(self, owner, v, coef, credit):
        """연쇄 피해: mc.Battle.chain 과 같은 식(시전자 최대 생명력 x 계수 x 피해 증가 x 1.85 x 방어 감소 x 난수 x 전투력 보정)"""
        from .. import rules as R
        b = self.b
        m = owner.mods()
        de = b.def_stat(v)
        dr = de / (de + R.DEF_K)
        inc, pen = m['inc'], 1.0          # 시전자 피해 증가는 대상 진영과 무관하게 반영(NKM 5605 연쇄 피해 계산) — 부케 보스 자해에도
        if v.side != owner.side:
            dr = max(0.0, dr - dr * min(1.0, m['pen']))
            pen = b.pen[owner.side]
        dmg = max(1.0, math.floor(owner.maxhp * coef * (1 + inc) * R.BASE_MULT * (1 - dr) * b.rand(owner.side) * pen))
        b.log(chain=owner.name, to=v.name, dmg=dmg)
        b.apply_damage(credit, v, dmg, 'chain', shieldable=True)
