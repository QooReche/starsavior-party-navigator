# -*- coding: utf-8 -*-
"""행동 게이지 방식 이벤트 시뮬레이터(기대값). 런타임 개체(Buff/Actor/Enemy/Ctx), Sim, 더미 딜러(DummyDef)."""
import math
import re
from collections import defaultdict

from .rules import AOE_DIV, BASE_MULT, COOP_CAP, DEF_K, DEFAULT_OPTS, ELEM_BEATS, ELEM_LOSES, INF_HP, KNOWN_DOT, TICK_PER_TURN  # noqa: F401
from .starsavior.parser import Line, Skill, _map_prop

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

    # cond_weight 가 해석하는 조건 키 (Line 덤프의 unparsed 판정용; 아래 분기를 고치면 함께 고칠 것)
    COND_KEYS = ('사용 스킬', '추가발동 스킬', '추가발동 스킬이 아님', '자기 추가발동 트리거', '자신이 보유', '자신이 미보유',
                 '중첩수', '효과 개수', '중첩수 이상', '효과 개수 이상', '대상이 보유', '대상 효과 중첩수', '대상 약화효과 보유',
                 '대상 강인도 없음', '결과', '대상 HP% 초과', '대상 HP% 미만', '적 처치', '적을 처치하지 못함', '내 턴', '자신 포함',
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



def dummy_dmg_hook():
    pass


# DummyDef 는 실제 데미지를 deal_damage 에서 계산해야 buff 효과를 받는다 -> cast_dummy 대신 일반 cast 사용
def _patch_dummy():
    def cast_dummy(self, a, sk):
        self.cast(a, sk)
    Sim.cast_dummy = cast_dummy
_patch_dummy()
