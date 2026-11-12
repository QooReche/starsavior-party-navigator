# -*- coding: utf-8 -*-
"""행동 게이지 방식 이벤트 시뮬레이터(기대값). 런타임 개체(Buff/Actor/Enemy/Ctx), Sim, 더미 딜러(DummyDef)."""
import math
import re
import json
import os
from functools import lru_cache
from collections import defaultdict

from .rules import (AOE_DIV, BASE_MULT, BREAK_DEC, COOP_CAP, DEC_CAP, DEF_K, DEFAULT_OPTS, ELEM_BEATS, ELEM_HIT, ELEM_LOSES,  # noqa: F401
                    INF_HP, KNOWN_DOT, MC_OPTS, TICK_PER_TURN)

# 적에게 거는 약화 중 대상의 「받는 피해 감소」 값을 바꾸는 속성 -> 적용 범위(감소 합, dmg_reduction='sum_cap')
_RED_PROPS = {'받는 피해 감소': 'all', '피해 감소': 'all', '전체 대상 피해 감소': 'aoe', '단일 대상 피해 감소': 'single',
              '기본기 피해 감소': '기본기', '특수기 피해 감소': '특수기', '궁극기 피해 감소': '궁극기'}


def calc_hit(a, b=0.0):
    """databook app.js calcHit 최종 판정. a = 효과 적중 - 효과 저항 +-상성, b = 절대 적중 - (절대 저항 + 역상성 절대 저항)."""
    if (a > 0 and b > a) or (a < 0 and b > 0):
        f = b
    elif a > 0 and b < 0:
        f = min(a, 1 - abs(b))
    else:
        f = a
    return max(0.0, min(1.0, f))
from .starsavior.parser import Line, Skill, _map_prop, explicit_target
from .starsavior.data import SRC


@lru_cache(maxsize=1)
def _forced_coop_lines():
    """강제 협공의 대상 표지/해제/강화/부여에 쓰는 공개 자동 대상 규칙."""
    with open(os.path.join(SRC, 'data', 'auto_skill.json'), encoding='utf8') as f:
        rows = json.load(f)['client_variant_lines']
    return {(key, slot, raw): spec for key, lines in rows.items() for slot, raw, spec in lines
            if '표본 행동 분석' in raw or '〈강제 협공〉' in raw}

# ------------------------------------------------------------------ 런타임 개체
class Buff:
    __slots__ = ('name', 'stacks', 'maxs', 'dur', 'props', 'fresh')

    def __init__(self, name, props, maxs, dur):
        self.name, self.props, self.maxs, self.dur = name, props, maxs, dur
        self.stacks = 0.0
        self.fresh = False


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
        self.forced_coop = 0.0  # ForceCrossAttack 존재 확률. 턴 종료 때 초기화(NKM:13569–13572).
        for slot, sk in d.skills.items():
            if sk.cd:
                self.cd[slot] = sk.cd * opts['init_cd_frac']
            else:
                self.cd[slot] = 0
        self.manual_acted = 0

    # ---- 버프 합산
    def mods(self):
        m = dict(atkp=0.0, spdp=0.0, spdf=0.0, cr=0.0, cd=0.0, inc=0.0, pen=0.0, defp=0.0, hpp=0.0, coop=0.0, eh=0.0,
                 preempt_reduce=0.0, inc_vs={}, inc_slot={})
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
        self.deb = {}      # name -> dict(stacks,dur,defp,spdp,er,red,dot)
        self.dead = False
        self.resist = float(spec.get('resist', 0.0))          # 효과 저항(1.0 = 100%)
        self.abs_resist = float(spec.get('abs_resist', 0.0))  # 절대 저항(적은 전원 0)

    def resist_eff(self):
        return self.resist + sum(d.get('er', 0.0) * d['stacks'] for d in self.deb.values())

    def recv_red(self, scope):
        """약화로 바뀐 받는 피해 감소 합(음수 = 더 받음). scope: 'all'/'aoe'/'single'/슬롯 이름 묶음"""
        return sum(v * d['stacks'] for d in self.deb.values() for k, v in d.get('red', {}).items() if k in scope)

    def defp(self):
        return sum(d.get('defp', 0.0) * d['stacks'] for d in self.deb.values())

    def def_eff(self):
        return max(0.0, self.def_ * (1 + self.defp()))

    def spd_eff(self):
        s = sum(d.get('spdp', 0.0) * d['stacks'] for d in self.deb.values())
        return max(1.0, self.spd * (1 + s))


class Ctx:
    __slots__ = ('owner', 'src', 'skill', 'extra', 'w', 'inc', 'atkp', 'cr', 'cd', 'pen', 'crit_p', 'kill', 'target',
                 'is_ally_event', 'nb_burst', 'eh', 'coop_used')

    def __init__(self, owner, src, skill, extra, w):
        self.owner, self.src, self.skill, self.extra, self.w = owner, src, skill, extra, w
        self.inc = self.atkp = self.cr = self.cd = self.pen = self.eh = 0.0
        self.coop_used = 0.0   # 이 공격에서 협공 1명 자리가 이미 쓰인 기대 비율(강제 협공이 먼저 차지, forced_coop_slot='shared')
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
        # MC와 같은 규칙 원본. 지표/골든은 opts로 옛 값을 명시할 수 있다.
        self.dmg_cap_scope = self.opts.get('dmg_cap_scope', MC_OPTS['dmg_cap_scope'])
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
        self.team_nova = 0.0      # 노바 포스 파티 공용 풀(nova_pool='team')
        self.nova_bursts = 0      # 노바 버스트 횟수(확인용)

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
            if not d.get('dot'):
                continue
            # debuff_state='per_caster' 는 시전자별 몫(subs), 교정 전은 마지막 시전자 하나(src)
            parts = list(d['subs'].values()) if 'subs' in d else ([d] if d.get('src') is not None else [])
            for part in parts:
                base, inc = self.dot_parts(part['src'], part['coef']) if self.opts['dot_snapshot'] == 'live' else (part['base'], part['inc'])
                dec = 0.0
                if self.opts['dmg_reduction'] == 'sum_cap':   # DoT 는 단일/전체·스킬 종류별 증감이 없어 'all' 감소만
                    dec = e.recv_red(('all',)) - BREAK_DEC * self.opts['break_p']
                dmg = base * self._damage_mult(inc, dec) * part['stacks'] * (1 - self.dr(e, 0.0))
                self.hurt(e, dmg, part['src'], 'dot', hit=0.0)
        if e.dead:
            for a in self.party:
                a.forced_coop = 0.0
            return
        # 적 턴 시작 트리거
        for a in self.party:
            for ln in a.d.lines:
                if ln.kind == 'enemy_ts':
                    self.apply_line(a, ln, Ctx(a, a, None, False, 1.0), 1.0)
        # 디버프 지속 감소
        for name in list(e.deb):
            d = e.deb[name]
            if 'subs' in d:
                for k in list(d['subs']):
                    sub = d['subs'][k]
                    if sub['dur'] != math.inf:
                        sub['dur'] -= 1
                        if sub['dur'] <= 0:
                            del d['subs'][k]
                d['stacks'] = sum(sub['stacks'] for sub in d['subs'].values())
                if not d['subs']:
                    del e.deb[name]
                continue
            if d['dur'] != math.inf:
                d['dur'] -= 1
                if d['dur'] <= 0:
                    del e.deb[name]
        for a in self.party:
            a.forced_coop = 0.0

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
        for b in self.party:
            b.forced_coop = 0.0
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
        self.cast(a, sk)

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
            # 노바 버스트: 오토(nova_policy='auto')는 쓰지 않는다. 수동이면 풀(팀 공용 또는 개인)에 4개가 있을 때 이 스킬에 +15%
            team = self.opts['nova_pool'] == 'team'
            if (self.opts['nova'] and self.opts['nova_policy'] == 'manual' and not extra and sk.is_attack
                    and (self.team_nova if team else a.nova) >= 4 and not (team and getattr(a.d, 'dummy', False))):
                if team:
                    self.team_nova -= 4
                else:
                    a.nova -= 4
                self.nova_bursts += 1
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
                if self.opts['nova_pool'] == 'team':
                    self.team_nova += sk.nv
                else:
                    a.nova += sk.nv
            if (sk.is_attack and not extra and (self.opts['coop']
                    or (self.opts['forced_coop'] and self.opts['forced_coop_target'] == 'random'))):
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
        """협공. basic_only: 아군 기본기 뒤에만(이 함수는 추가 발동·협공 시전에서는 불리지 않음).
        coop_single: 공격 1번에 1명. random_success는 성공 집합에서 균등 추첨한 기대값."""
        if self.opts['coop_trigger'] == 'basic_only' and ctx.skill.slot != '기본기':
            return
        if (self.opts['coop_dead_target'] == 'cancel' and not ctx.skill.all
                and ctx.target is not None and ctx.target.dead):
            return  # NKM:15495-15504: 단일 본대상 사망 시 협공 취소
        forced_rest = 1.0
        if self.opts['forced_coop_target'] == 'random' and self.opts['forced_coop']:
            forced = [(b, clamp(b.forced_coop)) for b in self.party
                      if b is not actor and b.forced_coop > 0 and self._coop_available(b)]
            weights = self._uniform_success_weights(forced)
            for (b, _), weight in zip(forced, weights):
                self.cast(b, b.d.skills['기본기'], w=weight * ctx.w, extra=True)
            if self.opts['forced_coop_slot'] == 'shared':
                forced_rest = max(0.0, 1.0 - sum(weights))
            if forced_rest <= 1e-12:
                return
        if not self.opts['coop']:
            return
        if not self.opts['coop_single']:   # 교정 전: 확률이 있는 아군 전원이 편성 순서대로 각자 협공
            for b in self.party:
                if b is actor or getattr(b.d, 'dummy', False):
                    continue
                p = clamp(b.mods()['coop'], 0.0, COOP_CAP)
                if p > 0:
                    self.cast(b, b.d.skills['기본기'], w=p * forced_rest * ctx.w, extra=True)
            return
        stat_order = self.opts['coop_order'] == 'stat'
        random_success = self.opts['coop_order'] == 'random_success'
        cands = []
        for b in self.party:
            if b is actor or getattr(b.d, 'dummy', False):
                continue
            if (stat_order or random_success) and (b.d.skills.get('기본기') is None
                               or b.d.skills['기본기'].ty != '액티브' or b.cd.get('기본기', 0) > 0):
                continue
            if random_success and not self._coop_available(b):
                continue
            stat = b.mods()['coop']
            p = clamp(stat, 0.0, COOP_CAP)
            if p > 0:
                cands.append((b, p, stat if stat_order else p))
        rest = (1.0 - ctx.coop_used) * forced_rest
        if random_success:
            # i가 성공하고 다른 성공자가 k명일 확률 × 1/(k+1).
            # 성공자 수의 분포를 합성해 확률 평균을 비선형 선택식에 넣지 않는다.
            weights = self._uniform_success_weights([(b, p) for b, p, _ in cands])
            for (b, p, _), weight in zip(cands, weights):
                self.cast(b, b.d.skills['기본기'], w=weight * rest * ctx.w, extra=True)
            return
        for b, p, _ in sorted(cands, key=lambda bp: -bp[2]):   # 같은 능력치이면 편성 순서(안정 정렬)
            self.cast(b, b.d.skills['기본기'], w=p * rest * ctx.w, extra=True)
            rest *= 1 - p

    @staticmethod
    def _uniform_success_weights(cands):
        """독립 존재/성공 확률을 성공 집합별 1/N으로 합산한다(평균 N으로 나누지 않음)."""
        weights = []
        for i, (_, p) in enumerate(cands):
            counts = [1.0]
            for j, (_, q) in enumerate(cands):
                if i == j:
                    continue
                updated = [0.0] * (len(counts) + 1)
                for k, mass in enumerate(counts):
                    updated[k] += mass * (1 - q)
                    updated[k + 1] += mass * q
                counts = updated
            weights.append(p * sum(mass / (k + 1) for k, mass in enumerate(counts)))
        return weights

    @staticmethod
    def _coop_available(b):
        # 기대값 모델에서 표현되는 상태만 검사. 아군 HP/브레이크 상태기는 MC에 있음.
        sk = b.d.skills.get('기본기')
        return (not getattr(b, 'dead', False) and not getattr(b, 'broken', False)
                and sk is not None and sk.ty == '액티브' and b.cd.get('기본기', 0) <= 0
                and not any(b.stack(name) > 0 for name in ('기절', '수면', '협공 불가')))

    def _forced_effect_targets(self, owner, ln):
        """효과 부여 대상을 먼저 고른다. 최종 강제 후보 균등 추첨과 별개임."""
        if self.opts['forced_coop_target'] != 'random':
            return None
        if '표본 행동 분석' not in ln.raw and '〈강제 협공〉' not in ln.raw:
            return None
        spec = _forced_coop_lines().get((owner.d.key, ln.slot, ln.raw))
        if spec is None:
            return None
        pool = [b for b in self.party if not getattr(b, 'dead', False)
                and (not spec.get('exclude_self') or b is not owner)]
        matched = False
        for filt in spec['f']:
            if filt == 'not_unable_to_act':
                got = [b for b in pool if not any(b.stack(n) > 0 for n in ('기절', '수면'))]
            elif filt == 'high_atk':
                high = max((self.live_atk(b) for b in pool), default=0)
                got = [b for b in pool if self.live_atk(b) == high]
            elif isinstance(filt, list) and filt[0] in ('has', 'not_has'):
                got = [b for b in pool if any(b.stack(n) > 0 for n in filt[1]) == (filt[0] == 'has')]
            else:
                raise ValueError('강제 협공 대상 필터 미지원: %r' % (filt,))
            # 클라 우선 필터: 0명이면 이전 풀 유지, 단일 대상에서 1명이 되면 중단.
            if got:
                pool, matched = got, True
                if spec['one'] and len(pool) == 1:
                    break
        # 동률/확률 상태의 상관은 기대값 엔진의 기존 대상 근사(슬롯순)를 유지한다.
        return ('a', pool[:1] if spec['one'] else (pool if matched else []))

    # ---------- 피해
    def _damage_mult(self, inc, dec, cr=0.0, cdv=0.0):
        """26610546 NKM:18187-18193,18534-18547: 치명별 순합 하한 뒤 기대값.

        상한은 비선형이므로 치명 확률을 먼저 곱하지 않는다.
        reduce 및 잘림이 없는 경우에는 종전 연산 순서를 유지한다.
        """
        if self.dmg_cap_scope != 'net':
            if self.opts['dmg_reduction'] == 'sum_cap':
                dec = min(DEC_CAP, dec)
            return (1 + inc - dec) + cr * cdv
        normal = 1 + inc - dec
        if DEC_CAP > 0 and min(normal, normal + cdv) < 1 - DEC_CAP:
            return ((1 - cr) * max(1 - DEC_CAP, normal)
                    + cr * max(1 - DEC_CAP, normal + cdv))
        return normal + cr * cdv

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
            dec = 0.0
            if self.opts['dmg_reduction'] == 'sum_cap':
                # 감소 합: 대상 약화(전체/단일·슬롯별) - 브레이크 15%p. 상한은 _damage_mult에서.
                scope = ('all', 'aoe' if sk.all else 'single', sk.slot)
                dec = e.recv_red(scope) - BREAK_DEC * self.opts['break_p']
            elif self.opts['break_p']:
                inc += 0.15 * self.opts['break_p']
            mult = self._damage_mult(inc, dec, cr, cdv)
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
        spec = explicit_target(t)
        if spec is not None:
            # 기대값 모델은 원래 자동 지정 근사(공격력순)를 유지한다.
            t = ('자신 제외 ' if spec['exclude_self'] else '') + ('아군' if spec['ally'] else '적')
            t += ' 1명(자동 지정)' if spec['one'] else ' 전체'
            for f in spec['f']:
                if isinstance(f, list) and f[0] == 'elem':
                    t = f[1] + ' 속성 ' + t
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
        if excl or t.startswith('아군') or mm:
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

    # cond_weight 가 해석하는 조건 키 (Line 덤프의 unparsed 판정용; 아래 분기를 고치면 함께 고칠 것)
    COND_KEYS = ('사용 스킬', '추가발동 스킬', '추가발동 스킬이 아님', '자기 추가발동 트리거', '자신이 보유', '자신이 미보유',
                 '중첩수', '효과 개수', '중첩수 이상', '효과 개수 이상', '대상이 보유', '대상 효과 중첩수', '대상 약화효과 보유',
                 '대상 강인도 없음', '결과', '대상 HP% 초과', '대상 HP% 미만', '대상 HP% 이상', '대상 HP% 이하', '적 처치', '적을 처치하지 못함', '내 턴', '자신 포함',
                 '시전자 속성', '시전자가 보유', '자신에게 약화효과 없음', '자신 약화효과 보유', '자신 강화효과 보유',
                 '스킬 쿨타임 아님', '턴 유닛이 보유')

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
            elif k in ('대상 HP% 이상', '대상 HP% 이하'):
                e = ctx.target or self.primary()
                ratio = self.hp_frac(e) * 10000
                w *= float(ratio >= float(v) if k.endswith('이상') else ratio <= float(v))
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
            elif st == '효과 적중':
                ctx.eh += v * w          # 이번 스킬의 효과 적중 판정에만(debuff_model='hit_resist')
            else:
                pass   # 명중/강인도/주는 회복량/vs 디펜더 등 무시
            return
        if kd == 'gauge':
            tg = self.resolve_targets(owner, eff['target'], ctx)
            if not tg:
                return
            # gauge_expect='exact': 효과 적중 판정(독립된 성공/실패)만 q x clamp(g+d) + (1-q) x g 로 처리한다.
            # 조건·시전 가중치(wf)는 대부분 서로 배타적인 갈래(중첩 1~5 줄 등)라 선형 합이 더 가깝다 -> 교정 전처럼 선형.
            exact = self.opts['gauge_expect'] == 'exact'
            if tg[0] == 'a':
                for x in tg[1]:
                    x.gauge = clamp(x.gauge + eff['val'] * 100.0 * wf, 0, 10000)
            else:
                for x in tg[1]:
                    p = self.hit_chance(owner, ctx, x) if eff.get('judge') else 1.0
                    if exact:
                        self.gauge_expect(x, eff['val'] * 100.0 * wf, p)
                    else:
                        x.gauge = clamp(x.gauge + eff['val'] * 100.0 * wf * p, 0, 10000)
            return
        if kd == 'cdr':
            sl = eff.get('slot') or (ctx.skill.slot if ctx.skill is not None else None)
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
            tg = self._forced_effect_targets(owner, ln)
            if tg is None:
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
                        for sub in x.deb[eff['name']].get('subs', {}).values():
                            sub['stacks'] *= (1 - wf)
            return
        if kd == 'buff':
            self.apply_buff(owner, eff, ctx, wf, targets=self._forced_effect_targets(owner, ln))
            return

    def apply_buff(self, owner, eff, ctx, wf, targets=None):
        tg = targets if targets is not None else self.resolve_targets(owner, eff['target'], ctx)
        if not tg:
            return
        side, targets = tg
        chance = eff['chance']
        if side == 'e':
            if not eff['props'] and not eff.get('dot') and eff['name'] not in KNOWN_DOT and not eff['dur']:
                pass
            for e in targets:
                p = chance * (self.hit_chance(owner, ctx, e) if eff['judge'] else 1.0)
                self.apply_debuff(owner, e, eff, p * wf, ctx)
            return
        if eff['name'] == '강제 협공':      # 대상 아군이 기본기로 추가 공격(추정: 협공 = 기본기 1회)
            if not self.opts['forced_coop']:
                return
            if self.opts['forced_coop_target'] == 'random':
                # NKM:5230–5232는 플래그만 부여. 15508–15521에서 본행동 뒤 추첨.
                for x in targets:
                    x.forced_coop = 1 - (1 - x.forced_coop) * (1 - clamp(chance * wf))
                return
            if self.opts['forced_coop_target'] == 'live_atk':
                # 공격력 1위 = 그 순간 버프 포함 공격력(같으면 스탯 공격력, 그다음 편성 순서). 대상 수는 문장 그대로
                pool = [x for x in self.party if x is not owner]
                targets = sorted(pool, key=lambda x: (-self.live_atk(x), -x.d.stats['atk']))[:len(targets)]
            shared = self.opts['forced_coop_slot'] == 'shared'
            if shared and (ctx is None or ctx.extra or ctx.src is not owner or ctx.w <= 1e-12):
                return   # 추가 발동·협공·강제 협공으로 나간 기본기에서는 강제 협공 없음(협공은 연쇄되지 않음)
            for x in targets:
                if x.d.skills.get('기본기') is None:
                    continue
                if shared:   # 이 공격의 협공 1명 자리를 먼저 차지(기대값), 일반 협공은 남은 몫만
                    frac = min(1.0 - ctx.coop_used, wf / ctx.w)
                    if frac <= 1e-12:
                        continue
                    ctx.coop_used += frac
                    self.cast(x, x.d.skills['기본기'], w=frac * ctx.w, extra=True)
                else:
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
        if self.opts['debuff_state'] == 'per_caster':
            self.apply_debuff_pc(owner, e, eff, p, coef_kind)
            return
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
            elif k == '효과 저항':
                d['er'] = v / 100.0
            elif k in _RED_PROPS:
                d.setdefault('red', {})[_RED_PROPS[k]] = v / 100.0
        if coef_kind:
            d['dot'] = True
            d['src'] = owner
            d['coef'] = coef_kind
            d['base'], d['inc'] = self.dot_parts(owner, coef_kind)   # dot_snapshot='on_apply' 는 이 값 고정

    def apply_debuff_pc(self, owner, e, eff, p, coef_kind):
        """debuff_state='per_caster': 성공 가중치 p(0~1, 기대값).
        p=0 이면 아무것도 바꾸지 않는다. 새로 생기면 그 지속 턴으로, 이미 있으면 p>=0.5 일 때만 지속 턴(최댓값)·스냅샷을 갱신한다.
        지속 피해는 시전자별 몫(subs: 중첩·지속·계수·시전자)을 따로 두고, 전체 중첩(d['stacks'])은 그 합. 중첩 상한은 전체에 적용."""
        if p <= 1e-12:
            return
        name = eff['name']
        dur = eff['dur'] if eff['dur'] is not None else math.inf
        d = e.deb.get(name)
        new = d is None
        if new:
            d = dict(stacks=0.0, dur=dur)
            e.deb[name] = d
        refresh = new or p >= 0.5
        if refresh and eff['dur'] is not None:
            d['dur'] = max(d['dur'], dur)
        mx = eff['max'] or (5 if coef_kind else 1)
        add = max(0.0, min(p * eff['times'], mx - d['stacks']))
        d['stacks'] += add
        for k, v in eff['props'].items():
            if k == '방어력%':
                d['defp'] = v / 100.0
            elif k == '속도%':
                d['spdp'] = v / 100.0
            elif k == '효과 저항':
                d['er'] = v / 100.0
            elif k in _RED_PROPS:
                d.setdefault('red', {})[_RED_PROPS[k]] = v / 100.0
        if coef_kind:
            d['dot'] = True
            subs = d.setdefault('subs', {})
            sub = subs.get(id(owner))
            if sub is None:
                sub = dict(stacks=0.0, dur=dur, src=owner, coef=coef_kind)
                sub['base'], sub['inc'] = self.dot_parts(owner, coef_kind)
                subs[id(owner)] = sub
            elif p >= 0.5:
                sub['dur'] = max(sub['dur'], dur)
                sub['coef'] = coef_kind
                sub['base'], sub['inc'] = self.dot_parts(owner, coef_kind)   # dot_snapshot='on_apply' 스냅샷
            sub['stacks'] += add

    def gauge_expect(self, x, delta, q):
        """확률 q 로 게이지 delta 변화의 기대값: q x clamp(g+delta) + (1-q) x g. q>1(추가 발동 x2 등)은 1씩 나눠 적용."""
        while q > 1e-12:
            step = min(1.0, q)
            x.gauge = step * clamp(x.gauge + delta, 0, 10000) + (1 - step) * x.gauge
            q -= step

    # ---------- P2 규칙 보조
    def dot_parts(self, src, coef_kind):
        """지속 피해 1틱(1중첩)의 (기본값, 피해 증가) = 시전자 현재 스탯·버프 기준"""
        m = src.mods()
        stat, c = coef_kind
        val = src.d.stats['atk'] * (1 + src.d.passive['atkp'] + m['atkp']) if stat == 'atk' else src.d.stats['hp']
        return val * c * BASE_MULT, m['inc']

    def live_atk(self, x):
        """버프 포함 현재 공격력(강제 협공 대상 선정용)"""
        return x.d.stats['atk'] * (1 + x.d.passive['atkp'] + x.mods()['atkp'] + x.d.gear_atkp)

    def hit_chance(self, owner, ctx, e):
        """{효과 적중 판정} 성공률. hit_resist: databook calcHit(적 절대 저항 0, 구원자 절대 적중 0) / constant: debuff_success"""
        if self.opts['debuff_model'] != 'hit_resist':
            return self.opts['debuff_success']
        hit = owner.d.stats.get('eh', 10000) / 10000.0 + owner.d.passive['eh'] + owner.mods()['eh']
        if ctx is not None and ctx.src is owner:
            hit += ctx.eh
        a = hit - e.resist_eff()
        ea = self.opts['enemy_element'] if e.element is None else e.element
        if ea and owner.element:
            if ELEM_BEATS.get(owner.element) == ea:
                a += ELEM_HIT
            elif ELEM_LOSES.get(owner.element) == ea:
                a -= ELEM_HIT
        return calc_hit(a, 0.0 - e.abs_resist)

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


def dummy_dmg_hook():
    """tools.sim_damage 재수출 호환용. 더미 피해는 Sim.cast 에서 계산함."""


def _patch_dummy():
    """옛 재수출 이름 유지. Sim.cast_dummy에 최종 구현이 있어 패치할 필요 없음."""
