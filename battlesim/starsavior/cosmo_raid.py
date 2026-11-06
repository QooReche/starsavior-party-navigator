# -*- coding: utf-8 -*-
"""코스모 게이트(RANKING_RAID) 시즌 전투: 보스 3종 x Step 1~3 x 난이도 레벨 0~18 (확률 엔진 mc.Battle 용).

수치는 전부 data/cosmo_raid.json(tools/build_cosmo_raid.py 가 게임 표에서 추출). 코드는 시즌 공통이다.
켜는 조건: mc.cosmo_raid_boss == 'on'(기본 off, api 의 encounter.cosmo_raid 전투에서만 자동 on) 이고 웨이브에 이 모듈이 만든 보스 정의가 있을 때만.

경로 재사용
- 티리아·카넬리아: 기존 `cosmo` 콘텐츠 N단계(stage_waves, 공개 databook 스킬 줄)를 그대로 쓰고 Step 3 난이도 배율·챌린지 효과·시즌 버프만 얹는다.
  Step 1~3 스탯이 표(Step 행)와 같음을 시험으로 확인한다.
- 벨그라스(+기록자·처단자): 공개 databook 에 없어 표에서 직접 만든 정의(CosmoFoe)와 상태 기계(Controller)로 돌린다.
- 챌린지 효과 12종은 보스 유닛에 붙는 효과/이벤트로 Controller 가 구현한다(길방 BFB 의 쇠락·시공·허무와 같은 방식).

«추정/근사»(docs/cosmo_raid.md 참고)
- 난이도 레벨 배율 = 능력치 x (1 + ScaleFactor/10000) (추정, 길방 별의 도전과 같은 형태).
- 시즌 버프는 해당 속성/직업 아군에게 상시 효과로 붙임(BCT_* 해석 추정). 생명력%는 전투 시작 때 최대 생명력까지 채움.
- 벨그라스: 침식/썩은 의지·잠행하는 뿌리 규칙은 스킬 설명문 기준. 「썩은 의지 방지 체크 버프(BOSS_6)」는 «효과 발생 전 상태로 판정»으로 근사.
  공허 붕괴의 추가 고정 피해(5000 x 썩은 의지, 최대 50)는 «타격한 아군 각각에게 방어 무시·보호막 적용»으로 근사(대상 범위·보호막 적용은 미확인).
  기록자·처단자의 응집된 생기 재충전(상대 턴 시작)은 «영양 과잉이 끝난 뒤 다음 시전 종료 때»로 근사.
- 엔진에 없는 효과 종류(타임 패러독스 판정 등)는 가장 가까운 기존 효과로 대신함."""
import copy
import json
import math
import os
from collections import defaultdict

from .data import SRC
from .parser import Skill

_DATA = {}

BOSS_KEYS = ('belgras', 'tyria', 'carnelia')
CAST_PROPS = ('특수기', '궁극기')

# 효과 이름(엔진 Eff 키)
SEASON = '코스모 시즌 버프'
CH_SINGLE = '폭주 : 분산'
CH_SPEED = '폭주 : 시공'
CH_TOUGH = '폭주 : 파쇄'
CH_DRAIN = '폭주 : 쇠락'
IMMUNE = '면역'
TOUGH_BAN = '강인도 피해 무효'
THORN = '잔멸의 가시'
BLEED = '출혈'
ERO = '침식된 의지(해제불가)'
ROT = '썩은 의지(해제불가)'
ROOT = '잠행하는 뿌리(해제불가)'
GROW = '끝없는 성장'
SEED = '생멸의 씨앗(해제불가)'
STACKS = '응집된 생기(해제불가)'
AMP = '상급 공격력 증가'
BARRIER = '보호막'


def load(src=SRC):
    if src not in _DATA:
        with open(os.path.join(src, 'data', 'cosmo_raid.json'), encoding='utf-8') as f:
            _DATA[src] = json.load(f)
    return _DATA[src]


def boss_data(key, src=SRC):
    for b in load(src)['bosses']:
        if b['key'] == key:
            return b
    raise ValueError('보스는 %s: %r' % ('|'.join(b['key'] for b in load(src)['bosses']), key))


def boss_by_name(name, src=SRC):
    """한글 이름(벨그라스 등) 또는 key"""
    for b in load(src)['bosses']:
        if name in (b['key'], b['name']):
            return b
    raise ValueError('모르는 코스모 보스: %r' % (name,))


def level_row(boss, level):
    if not level:
        return None
    rows = boss['levels']
    if not 1 <= level <= len(rows):
        raise ValueError('난이도 레벨은 0~%d: %r' % (len(rows), level))
    return rows[level - 1]


def effect_table(src=SRC):
    return {e['id']: e for e in load(src)['effects']}


# ---------------------------------------------------------------- 점수(추정). cosmo_raid.js cosmoScore 와 경계값까지 같아야 한다.
RATIO_UNIT = 10000


def cosmo_score(G, level, damage_frac, remain_turns, survivors, clear, boss='belgras', step=3):
    """코스모 게이트 최종 점수(정수). **합산식은 서버 계산이라 «추정»**, 클라 HUD 식은 기본 + 최대 피해 점수 x 깎은 HP 비율.
      HUD    = BasePoint + MaxDamagePoint x (깎은 HP 비율)            (비율은 1/10000 내림 후 정수 나눗셈 내림, 길방 boss_points 와 같은 방식)
      클리어 = HUD + RemainTurnPoint x 남은 턴 + RemainingSaviorPoint x 생존 구원자 수   (남은 턴·생존 항은 클리어일 때만: 추정)
      최종   = (위 합) x (1 + DifficultyValue/10000) 를 사사오입(정수 연산) + 달성 점수(HalfHPScore: 깎은 비율 >= 0.5 / KillScore: 클리어, 배율 미적용)
    level = Step 3 난이도 레벨(0 = 난이도 없음 → 배율·달성 점수 0). step 1·2 는 level 을 무시한다(난이도 그룹 없음)."""
    b = boss if isinstance(boss, dict) else _boss_of(G, boss)
    st = b['steps'][step - 1]
    f = max(0.0, min(1.0, 1.0 if clear else damage_frac))
    q = math.floor(f * RATIO_UNIT + 1e-9)
    raw = st['base'] + st['maxDamage'] * q // RATIO_UNIT
    if clear:
        raw += st['remainTurn'] * max(0, int(remain_turns)) + st['survivor'] * max(0, int(survivors))
    row = level_row(b, level) if step == 3 else None
    bonus = row['scoreBonus'] if row else 0
    total = (raw * (RATIO_UNIT + bonus) + RATIO_UNIT // 2) // RATIO_UNIT
    if row:
        if f >= 0.5 - 1e-12:
            total += row['half']
        if clear:
            total += row['kill']
    return total


def _boss_of(G, key):
    for b in G['bosses']:
        if b['key'] == key or b['name'] == key:
            return b
    raise ValueError('모르는 코스모 보스: %r' % (key,))


# ---------------------------------------------------------------- 보스 정의
def _scale_stats(stats, row):
    s = dict(stats)
    if row:
        s['atk'] = math.floor(s['atk'] * (1 + row['atk'] / 10000))
        s['hp'] = math.floor(s['hp'] * (1 + row['hp'] / 10000))
        s['def'] = math.floor(s['def'] * (1 + row['def'] / 10000))
    return s


def _skill(slot, name, coef, cd, tough, all_=False, attack=True, tg=None):
    sk = Skill(dict(sl=slot, n=name, ty='액티브', tg=tg or ('적 전체' if all_ else '자신'), act='공격' if attack else '비공격',
                    cf=[round(float(coef) * 100), 0, 0, 0], all=all_, cd=cd or None, nv=0))
    sk.ab = tough
    sk.semantic_lines = []
    return sk


class CosmoFoe:
    """FoeDef/GuildFoe 와 같은 모양의 적 정의(벨그라스·기록자·처단자)"""
    is_foe = True

    def __init__(self, key, name, meta, stats, skills, boss, spawn, slot, immune=(), cosmo=None):
        self.key, self.name = key, name
        self.id, self.variant = -1, '적'
        self.role, self.element = meta['role'], meta['element']
        self.boss = boss
        self.grade = '보스' if boss else '일반'
        self.attack_kind = meta.get('attackKind')
        self.stats = stats
        self.immune = set(immune)
        self.skills = skills
        self.trigger_skills, self.unmodeled = {}, []
        self.lines = []
        self.desc = {}
        self.passive = defaultdict(float)
        self.nb, self.manual, self.gear_atkp = {}, None, 0.0
        self.effect_info = {}
        self.spd_base = stats['spd']
        self.react, self.auto, self.auto_lines = {}, {}, {}
        self.spawn = spawn
        self.slot = slot
        self.cosmo = cosmo


def _tyria_immune(src):
    from .foe import stage_waves
    return stage_waves('cosmo', '티리아', '티리아 3단계', src)[1][0][0].immune


def build_waves(boss, step, level=0, src=SRC):
    """-> (waves[[def]], meta). boss = key/한글 이름, step 1~3, level 0~(레벨 수; Step 3 에서만)"""
    b = boss_by_name(boss, src) if not isinstance(boss, dict) else boss
    if step not in (1, 2, 3):
        raise ValueError('Step 은 1~3: %r' % (step,))
    if isinstance(level, bool) or not isinstance(level, int):
        raise ValueError('난이도 레벨은 정수: %r' % (level,))
    if level and step != 3:
        raise ValueError('난이도 레벨은 Step 3 에서만 선택할 수 있음(Step %d)' % step)
    row = level_row(b, level)
    st = b['steps'][step - 1]
    G = load(src)
    cfg = dict(boss=b['key'], step=step, level=level, row=row, season_buffs=b['seasonBuffs'], effects=effect_table(src),
               model='belgras' if b['key'] == 'belgras' else 'stage', bel=G['belgras'])
    if b['key'] == 'belgras':
        bm = cfg['bel']
        sk = bm['skills']
        skills = {'기본기': _skill('기본기', '연쇄 파열', sk['attack']['coef'], sk['attack']['cd'], sk['attack']['tough'], all_=True),
                  '특수기': _skill('특수기', '생기 약탈', 0, sk['special']['cd'], 0, attack=False, tg='자신'),
                  '궁극기': _skill('궁극기', '공허 붕괴', sk['hyper']['coef'], sk['hyper']['cd'], sk['hyper']['tough'], all_=True)}
        spawn = 'B' if st['bossSpecial'] and st['bossHyper'] else ('S' if st['bossSpecial'] else 'H' if st['bossHyper'] else 'N')
        boss_def = CosmoFoe('cosmo:belgras', '벨그라스', dict(role=b['role'], element=b['element'], attackKind=b['attackKind']),
                            _scale_stats(st['stats'], row), skills, True, spawn, 2, immune=_tyria_immune(src), cosmo=cfg)
        mm = bm['minions']
        foes = []
        for kind, nm in (('recorder', '기록자'), ('executioner', '처단자')):
            m = mm[kind]
            d = CosmoFoe('cosmo:' + kind, nm, m['unit'], dict(m['stats']), {'기본기': _skill('기본기', nm, 0, 0, 0, attack=False, tg='자신')},
                         False, 'N', m['pos'], cosmo=dict(model='minion', kind=kind, mm=mm))
            foes.append(d)
        waves = [[foes[0], boss_def, foes[1]]]
    else:
        from .foe import stage_waves
        nm = b['name']
        _, w = stage_waves('cosmo', nm, '%s %d단계' % (nm, step), src)
        d = w[0][0]
        need = dict(hp=st['stats']['hp'], atk=st['stats']['atk'], **{'def': st['stats']['def']}, spd=st['stats']['spd'])
        for k, v in need.items():
            if d.stats[k] != v:       # 공개 databook 스탯이 표와 다르면(패치) 표를 따른다
                d.stats[k] = v
        d.stats.update(_scale_stats({k: d.stats[k] for k in ('hp', 'atk', 'def')}, row))
        d.spd_base = d.stats['spd']
        d.cosmo = cfg
        waves = [[d]]
    meta = dict(content='cosmo_raid', tab=b['name'], name='%s Step %d%s' % (b['name'], step, (' Lv%d' % level) if level else ''),
                level=None, recommended_power=st['battlePower'], wave_count=1, battle_mode='boss_kill', turn_limit=st['turnLimit'],
                cosmo_raid=dict(boss=b['key'], step=step, level=level, season=G['season']['id']))
    return waves, meta


# ---------------------------------------------------------------- 상태 기계
class Controller:
    """mc.Battle 훅(guild_bfb.Controller 와 같은 계약): on_wave / after_cast / pre_hit / post_hit. Battle 이 cosmo_raid_boss=on 일 때만 만든다."""

    def __init__(self, b):
        self.b = b
        self.boss = None
        self.cfg = None
        self.fx = {}                 # 이벤트형 챌린지 효과 kind -> params
        self.minions = {}            # kind -> 유닛
        self.over = {}               # 부속 유닛 -> 영양 과잉이 끝나는 전역 턴
        self.stats = defaultdict(int)

    # ---------- 효과 도우미
    def _put(self, x, name, props, dur=math.inf, cat='marker', maxs=1, add=1, fixed=True, src=None):
        from ..mc import Eff
        e = x.eff.get(name)
        if e is None:
            e = Eff(name, dict(props), maxs, dur, src or self.boss or x, cat == 'debuff')
            e.category, e.fixed = cat, fixed
            e.fresh = x.acting
            x.eff[name] = e
        else:
            e.dur = max(e.dur, dur)
            e.props = dict(props)
        e.stacks = max(0, min(e.maxs, e.stacks + add))
        self.b.dirty(x)
        return e

    def _gt(self):
        return getattr(self.b, 'global_turns', 0)        # run() 이 시작하기 전(시험이 직접 cast)에는 속성이 없음

    def _stacks(self, x, name):
        return x.stack(name)

    def _set_stacks(self, x, name, n):
        e = x.eff.get(name)
        if e is None:
            return
        e.stacks = max(0, min(e.maxs, n))
        if e.stacks <= 0:
            del x.eff[name]
        self.b.dirty(x)

    def _drop(self, x, name):
        if x.eff.pop(name, None) is not None:
            self.b.dirty(x)

    def barrier(self):
        return False

    def is_boss(self, u):
        return False

    def after_break_skill(self, had_barrier):
        return

    # ---------- 웨이브
    def on_wave(self):
        b = self.b
        boss = next((u for u in b.foes if getattr(u.d, 'cosmo', None) and u.d.cosmo.get('model') in ('stage', 'belgras')), None)
        if boss is None:
            return
        self.boss, self.cfg = boss, boss.d.cosmo
        cfg = self.cfg
        # 시즌 전투 보너스 BUFF: 조건(속성/직업)에 맞는 아군에게 상시 효과(마커: 강화 개수·해제에 안 셈)
        for sb in cfg['season_buffs']:
            kind, val = next(iter(sb['filter'].items()))
            for x in b.allies:
                if (x.element if kind == 'element' else x.role) == val:
                    props = {}
                    for p in sb['props']:
                        props[p['prop']] = props.get(p['prop'], 0.0) + p['value']
                    self._put(x, '%s %d' % (SEASON, sb['id']), props, src=x)
        # 난이도 레벨의 챌린지 효과
        row = cfg['row']
        for eid in (row['effects'] if row else []):
            e = cfg['effects'][eid]
            k, p = e['kind'], e['params']
            if k == 'single_red':
                self._put(boss, CH_SINGLE, {'단일 대상 피해 감소': p['pct']})
            elif k == 'speed':
                self._put(boss, CH_SPEED, {'속도%': p['pct']})
            elif k == 'immune':
                self._put(boss, IMMUNE, {}, dur=p['turns'])
            elif k == 'tough':
                self._put(boss, CH_TOUGH, {'강인도 피해': p['add']})
            elif k in ('drain', 'bleed', 'pressure', 'rewind', 'backflow', 'thorn', 'punish', 'march'):
                self.fx[k] = p
            else:
                b.unsup['cosmo_raid: 미지원 챌린지 효과 %s' % e['name']] += 1
        if cfg['model'] == 'belgras':
            self._belgras_start()

    def _belgras_start(self):
        b, boss, bm = self.b, self.boss, self.cfg['bel']
        e, r = bm['erosion'], bm['rot']
        self._put(boss, ERO, {'속도%': e['speedPct'], '방어력%': e['defPct'], '궁극기 피해 증가': e['hyperIncPct']}, maxs=e['max'], add=0)
        self._put(boss, ROT, {'방어력%': r['defPct']}, maxs=r['max'], add=0)
        self._put(boss, GROW, {'피해 증가': bm['growth']['incPct']}, maxs=bm['growth']['max'], add=0)
        b.set_gauge(boss, boss.gauge + bm['passive1']['waveGaugePct'] * 100)        # 패시브1: 전투 시작 시 행동 게이지 +50%
        mm = bm['minions']
        for u in b.foes:
            c = getattr(u.d, 'cosmo', None)
            if c and c.get('model') == 'minion':
                self.minions[c['kind']] = u
                self._put(u, SEED, {})                                     # 무적(INVINCIBLE_NAMES)
                u.zero_stats = True                                        # 속도 0 고정: 행동하지 않음
                self._put(u, STACKS, {}, maxs=mm['stacks'], add=mm['initStacks'])
        self._sync_ban()

    def _sync_ban(self):
        boss = self.boss
        if self._stacks(boss, ERO) > 0 or self._stacks(boss, ROOT) > 0:
            self._put(boss, TOUGH_BAN, {})
        else:
            self._drop(boss, TOUGH_BAN)

    # ---------- 벨그라스: 침식·썩은 의지
    def _erode(self, dec, rot_gain):
        boss, bm = self.boss, self.cfg['bel']
        pre = self._stacks(boss, ERO) > 0 or self._stacks(boss, ROOT) > 0     # 체크 버프(BOSS_6) 근사: 변화 전 상태로 썩은 의지 발생 여부 판정
        self._set_stacks(boss, ERO, self._stacks(boss, ERO) - dec) if boss.eff.get(ERO) else None
        if not pre:
            self._put(boss, ROT, {'방어력%': bm['rot']['defPct']}, maxs=bm['rot']['max'], add=rot_gain)
            self.stats['rot_gain'] += rot_gain
        self._sync_ban()

    def _ensure(self, name, props, maxs):
        if self.boss.eff.get(name) is None:
            self._put(self.boss, name, props, maxs=maxs, add=0)

    # ---------- 시전 후
    def _cur_ctx(self):
        return getattr(self.b, '_cast_ctx', None)

    def after_cast(self, u, sk, ctx, extra):
        boss = self.boss
        if boss is None:
            return
        b = self.b
        if self.cfg['model'] == 'belgras':
            self._minion_tick()
        if u.side == 0:
            if self.cfg['model'] == 'belgras' and not boss.dead and not sk.is_attack:
                bm = self.cfg['bel']
                self._ensure_belgras_eff()
                self._erode(bm['erosion']['decayNonAttack'], bm['rot']['gainAoe'])      # 적이 공격이 아닌 스킬 사용 후: 침식 -5, 썩은 의지 +5(발생 조건 동일)
            return
        if u is not boss or boss.dead:
            return
        fx = self.fx
        hit = [x for x in getattr(ctx, 'hit_targets', []) if x.side == 0]
        if sk.is_attack:
            if 'bleed' in fx:
                for x in hit:
                    if not x.dead:
                        self.stats['bleed'] += 1
                        b.add_effect(boss, x, dict(kind='buff', target='', name=BLEED, chance=1.0, dur=fx['bleed']['turns'], props={}, max=None,
                                                   times=1, judge=False, ignore_resist=True), ctx)
            if sk.slot == '기본기':
                if 'pressure' in fx:
                    for x in hit:
                        if not x.dead:
                            self.stats['pressure'] += 1
                            b.set_gauge(x, x.gauge - fx['pressure']['pct'] * 100)
                if 'march' in fx:
                    for y in b.alive(1):
                        if y is not boss:
                            self.stats['march'] += 1
                            b.set_gauge(y, y.gauge + fx['march']['pct'] * 100)
            if sk.slot == '궁극기':
                if 'thorn' in fx:
                    for x in hit:
                        if not x.dead:
                            self._thorn(x, ctx, fx['thorn'].get('count', 1), fx['thorn'].get('turns', 3))
                if 'punish' in fx:
                    for x in hit:
                        if not x.dead and x.n_harmful() > 0:
                            self._chain_atk(boss, x, fx['punish']['atkRate'] / 100.0)
                            self.stats['punish'] += 1
        if self.cfg['model'] == 'belgras':
            self._belgras_cast(sk, ctx, hit)

    def _thorn(self, x, ctx, times, turns):
        bm = self.cfg['bel']['thorn']
        self.stats['thorn'] += 1
        self.b.add_effect(self.boss, x, dict(kind='buff', target='', name=THORN, chance=1.0, dur=turns, props={}, max=5, times=times,
                                             judge=False, ignore_resist=True, dot=('atk', bm['atkRatePct'] / 100.0)), ctx)

    def _chain_atk(self, owner, v, coef):
        """공격력 비례 연쇄 피해: mc.Battle.chain 과 같은 식(대상 1명)"""
        from .. import rules as R
        b = self.b
        m = owner.mods()
        de = b.def_stat(v)
        dr = de / (de + R.DEF_K)
        dr = max(0.0, dr - dr * min(1.0, m['pen']))
        dmg = max(1.0, math.floor(b.atk_stat(owner) * coef * (1 + m['inc']) * R.BASE_MULT * (1 - dr) * b.rand(owner.side) * b.pen[owner.side]))
        b.apply_damage(owner, v, dmg, 'chain', shieldable=True)

    def _ensure_belgras_eff(self):
        bm = self.cfg['bel']
        self._ensure(ERO, {'속도%': bm['erosion']['speedPct'], '방어력%': bm['erosion']['defPct'], '궁극기 피해 증가': bm['erosion']['hyperIncPct']}, bm['erosion']['max'])
        self._ensure(ROT, {'방어력%': bm['rot']['defPct']}, bm['rot']['max'])

    def _belgras_cast(self, sk, ctx, hit):
        b, boss, bm = self.b, self.boss, self.cfg['bel']
        self._ensure_belgras_eff()
        # 패시브3: 스킬 사용 후 피해량 +5% 중첩
        self._put(boss, GROW, {'피해 증가': bm['growth']['incPct']}, maxs=bm['growth']['max'])
        mm = bm['minions']
        if sk.is_attack:
            if '기본기' == sk.slot:
                for x in hit:
                    if not x.dead:
                        self._thorn(x, ctx, 1, bm['thorn']['turns'])        # 연쇄 파열: 적 전체에 잔멸의 가시 3턴
            # 기록자/처단자: 응집된 생기가 남아 있으면 «아군이 타격할 때» 벨그라스에게 공격력 증가 / 보호막
            rec, exe = self.minions.get('recorder'), self.minions.get('executioner')
            if rec is not None and self._stacks(rec, STACKS) > 0:
                self._put(boss, AMP, {'공격력%': mm['attackAmpPct']}, dur=mm['attackAmpTurnsBoss'], cat='buff', fixed=False)
            if exe is not None and self._stacks(exe, STACKS) > 0:
                e = self._put(boss, BARRIER + '(처단자)', {}, dur=mm['barrierTurns'], cat='buff', fixed=False)
                e.shield = max(e.shield, math.floor(boss.maxhp * mm['barrierHpPct'] / 100.0))
        if sk.slot == '특수기' and not sk.is_attack:
            self._put(boss, ERO, {'속도%': bm['erosion']['speedPct'], '방어력%': bm['erosion']['defPct'],
                                  '궁극기 피해 증가': bm['erosion']['hyperIncPct']}, maxs=bm['erosion']['max'], add=bm['erosion']['perSpecial'])
            self._drop(boss, ROOT)
            self.stats['special'] += 1
        elif sk.slot == '궁극기':
            self._set_stacks(boss, ERO, 0) if boss.eff.get(ERO) else None
            self._set_stacks(boss, ROT, 0) if boss.eff.get(ROT) else None
            self._put(boss, ROOT, {'속도%': bm['root']['speedPct']}, dur=bm['root']['turns'], cat='marker')
            b.set_gauge(boss, boss.gauge + bm['hyperGauge']['self'] * 100)
            for x in b.alive(0):
                b.set_gauge(x, x.gauge + bm['hyperGauge']['enemy'] * 100)
            self.stats['hyper'] += 1
        self._sync_ban()

    # ---------- 부속 유닛(기록자·처단자)
    def _minion_tick(self):
        mm = self.cfg['bel']['minions']
        gt = self._gt()
        for u in self.minions.values():
            if self._stacks(u, STACKS) == 0 and gt >= self.over.get(u, 0):
                self._put(u, STACKS, {}, maxs=mm['stacks'], add=mm['regen'])

    def _minion_hit(self, a, v):
        mm = self.cfg['bel']['minions']
        ctx = self._cur_ctx()
        sk = ctx.skill if ctx is not None else None
        if sk is None or not sk.is_attack:
            return
        n = self._stacks(v, STACKS)
        if n <= 0:
            return
        n = max(0, n - (mm['decayAoe'] if sk.all else mm['decaySingle']))
        self._set_stacks(v, STACKS, n)
        if n == 0 and self._gt() >= self.over.get(v, 0):
            self.over[v] = self._gt() + mm['overfeedTurns']
            self.stats['minion_break'] += 1
            kind = v.d.cosmo['kind']
            if kind == 'recorder':
                self._put(a, AMP, {'공격력%': mm['attackAmpPct']}, dur=mm['attackAmpTurnsHit'], cat='buff', fixed=False, src=v)
            else:
                for x in self.b.alive(0):
                    e = self._put(x, BARRIER + '(처단자)', {}, dur=mm['barrierTurns'], cat='buff', fixed=False, src=v)
                    e.shield = max(e.shield, math.floor(x.maxhp * mm['barrierHpPct'] / 100.0))

    # ---------- 피격
    def pre_hit(self, a, v):
        return

    def post_hit(self, a, v):
        boss = self.boss
        if boss is None or a is None:
            return
        b = self.b
        ctx = self._cur_ctx()
        sk = ctx.skill if ctx is not None else None
        if a.side == 0 and v is boss and not boss.dead:
            fx = self.fx
            if 'drain' in fx and not a.dead:
                self.stats['drain'] += 1
                self._put(a, CH_DRAIN, {'생명력%': -fx['drain']['pct']}, cat='debuff', maxs=fx['drain']['max'], fixed=True)
            if 'rewind' in fx and boss.has(fx['rewind']['state']):
                self.stats['rewind'] += 1
                b.set_gauge(boss, boss.gauge + fx['rewind']['pct'] * 100)
            if 'backflow' in fx and a.n_harmful() > 0:
                self.stats['backflow'] += 1
                b.set_gauge(boss, boss.gauge + fx['backflow']['pct'] * 100)
            if self.cfg['model'] == 'belgras' and sk is not None and sk.is_attack:
                bm = self.cfg['bel']
                self._ensure_belgras_eff()
                single = not sk.all
                e = bm['erosion']
                self._erode(e['decaySingle'] if single else e['decayAoe'], bm['rot']['gainSingle'] if single else bm['rot']['gainAoe'])
                if single and a.has(THORN):
                    b.set_gauge(boss, boss.gauge + bm['passive1']['thornHitGaugePct'] * 100)    # 패시브1: 가시 상태 적의 단일 공격에 피격 후 게이지 +20%
        elif a.side == 0 and v.side == 1 and self.cfg['model'] == 'belgras' and getattr(v.d, 'cosmo', None) and v.d.cosmo.get('model') == 'minion':
            self._minion_hit(a, v)
        elif a is boss and v.side == 0 and self.cfg['model'] == 'belgras' and sk is not None and sk.slot == '궁극기':
            n = min(self._stacks(boss, ROT), self.cfg['bel']['hyperTrueDamage']['max'])
            if n > 0:
                b.apply_damage(boss, v, self.cfg['bel']['hyperTrueDamage']['perStack'] * n, 'true', shieldable=True)
                self.stats['true_damage_hits'] += 1
