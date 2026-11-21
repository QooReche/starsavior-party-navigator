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
- 난이도 배율은 서버가 적용해 전송하고 클라는 표시만 함(NKC:51440·355809·411611).
  엔진 현행 능력치 x (1 + ScaleFactor/10000)는 서버 덮어쓰기 2단 → 버프 3단 경로와 일치함. 서버 내부 산식은 미확인.
- 시즌 버프는 해당 속성/직업 아군에게 상시 효과로 붙임(BCT 매핑 NKM.Templets:32990-33013, 아군만 적용 PM 확정).
  생명력%는 전투 시작 때 최대 생명력까지 채움. 중도 소환물 적용은 서버 경로 미확인.
- 전투력 보정은 적용됨(NKM:479-482·18369-18426). 배율 산출은 서버임.
- HUD 점수·반/처치 달성 판정은 클라 확인. 생존 점수 RemainingSaviorPoint는 서버 전용이며 최종 합산은 추정임.
- 벨그라스: 침식/썩은 의지·잠행하는 뿌리 규칙은 스킬 설명문 기준. 「썩은 의지 방지 체크 버프(BOSS_6)」는 «효과 발생 전 상태로 판정»으로 근사.
  공허 붕괴는 시전 시작의 썩은 의지로 자기 대상 피해를 예약하고 턴 종료 전에 보호막·HP에 적용한다(NKM:4688,13537).
  기록자·처단자의 응집된 생기 재충전(상대 턴 시작)은 «영양 과잉이 끝난 뒤 다음 시전 종료 때»로 근사.
- 엔진에 없는 효과 종류(타임 패러독스 판정 등)는 가장 가까운 기존 효과로 대신함."""
import copy
import json
import math
import os
from collections import defaultdict

from .. import datafile
from .data import SRC
from .parser import Skill

_DATA = datafile._CACHE   # 경로 -> 자료(datafile.load_path 캐시 그대로). 시험이 data_path() 열쇠로 바꿔 끼운다

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
CH_GROW_EX = '피해 증가(EX)'
CH_GUARD = '폭주 : 장벽'


_DATA_FILE = None      # None = <src>/data/cosmo_raid.json(현재 시즌). 시험이 지난 시즌 fixture 를 쓸 때만 use_data 로 지정


def use_data(path=None):
    """이 프로세스의 코스모 시즌 자료 파일을 바꾼다(None = 기본 실자료). 시험 전용 — 지난 시즌 모델(벨그라스 등) 회귀 시험이
    tests/fixtures/cosmo_raid_<시즌>.json 을 읽게 한다. 자료·전투 입력 캐시는 경로를 키에 넣고, 바꿀 때 엔진 캐시도 비운다."""
    global _DATA_FILE
    _DATA_FILE = os.path.normcase(os.path.abspath(path)) if path else None
    from .. import api
    api.clear_engine_caches()


def data_path(src=SRC):
    return _DATA_FILE or os.path.normcase(os.path.abspath(os.path.join(src, 'data', 'cosmo_raid.json')))


def load(src=SRC):
    return datafile.load_path(data_path(src))   # 경로가 캐시 열쇠 — use_data 로 바꾼 fixture 와 실자료가 섞이지 않는다


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


def cosmo_score(G, level, damage_frac, remain_turns, survivors, clear, boss=None, step=3):
    """코스모 게이트 최종 점수(정수). **합산식은 서버 계산이라 «추정»**, 클라 HUD 식은 clamp(기본 + 최대 피해 점수 x floor((maxHP-HP)x10000/maxHP)/10000 내림, 0, 기본+최대 피해 점수)로 매번 내림(NKM:16914 확인).
      HUD    = BasePoint + MaxDamagePoint x (깎은 HP 비율)            (비율은 1/10000 내림 후 정수 나눗셈 내림, 길방 boss_points 와 같은 방식)
      클리어 = HUD + RemainTurnPoint x 남은 턴 + RemainingSaviorPoint x 생존 구원자 수   (남은 턴·생존 항은 클리어일 때만: 추정)
      최종   = (위 합) x (1 + DifficultyValue/10000) 를 사사오입(정수 연산) + 달성 점수(HalfHPScore: 깎은 비율 >= 0.5 / KillScore: 클리어, 배율 미적용)
    level = Step 3 난이도 레벨(0 = 난이도 없음 → 배율·달성 점수 0). step 1·2 는 level 을 무시한다(난이도 그룹 없음)."""
    if boss is None:                     # 기본 보스 = 시즌 데이터의 첫 보스(시즌마다 달라질 수 있어 이름을 코드에 고정하지 않음)
        boss = G['season']['bossOrder'][0]
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


def _donor_immune(b, src):
    """벨그라스 모델 보스는 면역 목록 표가 따로 없어 «같은 면역 그룹(immuneGroup)의 기존 databook 보스 마지막 단계»의 면역을 쓴다.
    그 보스는 데이터(bosses)에서 찾는다(이름·단계 수를 코드에 고정하지 않음)."""
    from .foe import stage_waves
    for o in load(src)['bosses']:
        if o['key'] != b['key'] and o.get('immuneGroup') == b.get('immuneGroup'):
            return stage_waves('cosmo', o['name'], '%s %d단계' % (o['name'], len(o['steps'])), src)[1][0][0].immune
    raise ValueError('면역 목록을 빌려 올 같은 면역 그룹 보스가 없음: %r' % (b['key'],))


def build_waves(boss, step, level=0, src=SRC):
    """-> (waves[[def]], meta). boss = key/한글 이름, step 1~3, level 0~(레벨 수; Step 3 에서만)"""
    b = boss_by_name(boss, src) if not isinstance(boss, dict) else boss
    if step not in (1, 2, 3):
        raise ValueError('Step 은 1~3: %r' % (step,))
    if isinstance(level, bool) or not isinstance(level, int):
        raise ValueError('난이도 레벨은 정수: %r' % (level,))
    if level and step != 3:
        raise ValueError('난이도 레벨은 Step 3 에서만 선택할 수 있음(Step %d)' % step)
    if b.get('sim') is False:          # 빌더가 databook 적 정의 유무로 정함(시즌 1023 바스커빌의 괴수)
        raise ValueError(b.get('simNote') or '%s 은(는) 아직 계산할 수 없음' % b['name'])
    row = level_row(b, level)
    st = b['steps'][step - 1]
    G = load(src)
    cfg = dict(boss=b['key'], step=step, level=level, row=row, season_buffs=b['seasonBuffs'], effects=effect_table(src),
               model='belgras' if b['key'] == 'belgras' else 'stage', bel=G.get('belgras'))
    if b['key'] == 'belgras':
        bm = cfg['bel']
        sk = bm['skills']
        skills = {'기본기': _skill('기본기', '연쇄 파열', sk['attack']['coef'], sk['attack']['cd'], sk['attack']['tough'], all_=True),
                  '특수기': _skill('특수기', '생기 약탈', 0, sk['special']['cd'], 0, attack=False, tg='자신'),
                  '궁극기': _skill('궁극기', '공허 붕괴', sk['hyper']['coef'], sk['hyper']['cd'], sk['hyper']['tough'], all_=True)}
        spawn = 'B' if st['bossSpecial'] and st['bossHyper'] else ('S' if st['bossSpecial'] else 'H' if st['bossHyper'] else 'N')
        boss_def = CosmoFoe('cosmo:belgras', '벨그라스', dict(role=b['role'], element=b['element'], attackKind=b['attackKind']),
                            _scale_stats(st['stats'], row), skills, True, spawn, 2, immune=_donor_immune(b, src), cosmo=cfg)
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
        self.pending_damage = []      # (대상, 시전 시작 때 확정한 고정 피해)
        self._shield_amp_ctx = None   # no_shield_amp: 시전당 한 번만 적용하기 위한 ctx 참조
        self._guard_ctx = None        # few_buff_guard: 시전당 한 번만 판정
        self._punish_q = []           # punish: (대상, 생성 때 정한 공격자 쪽 값) — 반격·반응 뒤 flush_damage 에서 처리

    def before_cast(self, u, sk, ctx):
        if (u is self.boss and self.cfg['model'] == 'belgras' and sk.slot == '궁극기'
                and self.b.mc['cosmo_hyper_true_target'] == 'self'):
            p = self.cfg['bel']['hyperTrueDamage']
            n = min(self._stacks(u, ROT), p['max'])
            if n > 0:
                self.pending_damage.append((u, p['perStack'] * n))
                self.b.queue_add('cosmo_fixed', self.pending_damage[-1])
                self.stats['self_damage_queued'] += 1
        # EX: debuff_amp — NSEAT_SKILL_START, 자신 약화 개수당 피해 증가 (SE 9402101)
        if u is self.boss and not self.boss.dead and 'debuff_amp' in self.fx and sk.is_attack:
            p = self.fx['debuff_amp']
            count = min(self.boss.n_harmful(), p['max'])
            if count > 0:
                ctx.inc += p['pct'] / 100.0 * count
                self.stats['debuff_amp'] += count

    def execute_se(self, owner, ln, ctx):
        """조각에서 실행 담당이 cosmo인 SE만 처리. 일반 버프·회복·게이지는 mc가 실행함."""
        if getattr(owner.d, 'client_model', None) != 'baskerville':
            raise ValueError('코스모 SE의 적 정의가 다름')
        b, p = self.b, ln.eff['meta']
        op = p['op']
        if op == 'change_skill':
            # NKM:2922-2933,3084-3090,2412: 즉시 슬롯 교체·유지, RESET은 쿨 0.
            before = owner.d.client_skills[p['before']]
            current = owner.skill_overrides.get(before.slot, owner.d.skills[before.slot])
            if current is before:
                owner.skill_overrides[before.slot] = owner.d.client_skills[p['after']]
                owner.cd[before.slot] = 0
                self.stats['bask_change'] += 1
        elif op == 'specific_count':
            # NKM:5663-5678: 적 전체의 버프 객체 수 합, IsLevel 중첩수 합이 아님.
            count = 0
            for x in b.alive(1 - owner.side):
                e = x.eff.get(p['name'])
                if e is not None and e.stacks > 0:
                    count += len(e.inst) if e.inst is not None else 1
            ctx.inc += p['rate'] * count
            self.stats['bask_count'] += count
        elif op == 'cool_up':
            # NKM:3105-3109: 최대 쿨로 제한. COOL_TURN_UP_2는 면역 그룹 1001의 ID가 아님.
            slot = p['slot']
            sk = owner.skill_overrides.get(slot, owner.d.skills[slot])
            owner.cd[slot] = min(sk.cd, owner.cd.get(slot, 0) + p['value'])
            self.stats['bask_cool_up'] += 1
        elif op == 'delete_count':
            targets = b.line_auto_targets(owner, p['auto'], ctx) if p.get('auto') else [owner]
            for x in targets:
                if p['name'] in x.eff:
                    b._dispel_n_ordered(x, [p['name']], p['count'])
                    b.dirty(x)   # NKM:3070-3081: 상한만 갱신, 해제로 회복하지 않음.
                    self.stats['bask_delete_one'] += 1
        else:
            raise ValueError('코스모 SE 미지원: ' + op)

    def skill_start(self, u, sk, ctx):
        # EX: punish(SET_31, SE 9403101) — NSEAT_SKILL_START(대상 확정 직후·타격 전). 조건 1161 OnMyAttack(SkillIndex 궁극기,
        # TargetNegativeBuff: 스킬 대상 유형대로 모은 대상 중 하나라도 약화 1개 이상 — NKM:9590-9700, NKM.Templets OBF_2765)이 참이면
        # AutoTargetId 10(IsNegativeBuffUnit: 약화 상태인 적 전원, 스킬 대상만이 아님)에게 BI_ADD_DAMAGE_1(공격력 30%).
        # 생성 때 공격자 쪽 값(공격력·피해 증가·관통)만 정하고(NKM:4734·6226), 대상 방어·분담은 넣을 때 계산(NKM:8168·17797).
        # 넣는 시점 = 반격·예약 반응이 끝난 뒤 추가 피해 처리 단계(NKM:15382·13961 → flush_damage).
        boss = self.boss
        if (u is boss and not boss.dead and 'punish' in self.fx and sk.is_attack and sk.slot == '궁극기'):
            pool = [x for x in (ctx.targets or []) if x.side != u.side]
            if any(x.n_harmful() > 0 for x in pool):
                coef = self.fx['punish']['atkRate'] / 100.0
                if self.b.mc['chain_timing'] == 'client_queue':
                    # 같은 클라 추가 피해 큐(BI_ADD_DAMAGE_1, NKM:4721-4742 → 6244-6320). 일반 연쇄와 같은 생성·실행 식.
                    self.b.queue_punish(boss, [x for x in self.b.alive(1 - boss.side) if x.n_harmful() > 0], coef, ctx)
                    return
                # 누적(클라 추가 피해 목록 Add, NKM:6239-6241): 같은 행동 안 반응으로 궁극기가 다시 시작되면 따로 쌓임
                self._punish_q.extend((x, self._chain_pre(boss, x, coef, ctx)) for x in self.b.alive(1 - boss.side) if x.n_harmful() > 0)

    def flush_damage(self):
        # NKM:13539-13544: 반응 종료 → 예약 피해 → 보유자 턴 종료 효과.
        queue, self._punish_q = self._punish_q, []
        for x, pre in queue:                       # 응징 추가 피해(생성 뒤 죽은 대상은 건너뜀)
            boss = self.boss
            if not x.dead and boss is not None:
                self.b.apply_damage(boss, x, self._chain_hit(boss, x, pre), 'chain', shieldable=True)
                self.stats['punish'] += 1
        pending, self.pending_damage = self.pending_damage, []
        for target, damage in pending:
            self.apply_pending(target, damage)

    def apply_pending(self, target, damage):
        """예약 고정 피해 1건(BI_ADD_TRUE_DAMAGE). 통합 큐(mc.flush_add_damage)도 이 함수를 부름."""
        if target.dead:
            return
        hp, shield = target.hp, target.shield_total()
        damage = self.b.fixed_true_damage(None, target, damage, source_side=target.side)
        self.stats['true_damage_hits'] += 1
        self.stats['self_damage_hp'] += hp - target.hp
        self.stats['self_damage_shield'] += shield - target.shield_total()
        self.b.log(self_damage=target.name, damage=damage, hp_damage=hp - target.hp,
                   absorbed=shield - target.shield_total())

    # ---------- 효과 도우미
    def _put(self, x, name, props, dur=math.inf, cat='marker', maxs=1, add=1, fixed=True, src=None, dead_keep=False):
        return self.b.put_eff(x, name, props, dur=dur, maxs=maxs, add=add, src=src or self.boss or x, cat=cat,
                              fixed=fixed, refresh_props=True, dead_keep=dead_keep)

    def _gt(self):
        return getattr(self.b, 'global_turns', 0)        # run() 이 시작하기 전(시험이 직접 cast)에는 속성이 없음

    def _stacks(self, x, name):
        return x.stack(name)

    def _set_stacks(self, x, name, n):
        e = x.eff.get(name)
        if e is None:
            return
        old_stacks = e.stacks
        e.stacks = max(0, min(e.maxs, n))
        if e.stacks <= 0:
            del x.eff[name]
        # Empty markers affect mechanics via stack/on, not mods. The only
        # name-dependent mods input is 강화 불가 in suppress mode.
        if e.stacks != old_stacks and (e.props or (name == '강화 불가' and not x.ban_refuse)):
            self.b.dirty(x)

    def _drop(self, x, name):
        e = x.eff.pop(name, None)
        if e is not None and (e.props or (name == '강화 불가' and not x.ban_refuse)):
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
        if getattr(boss.d, 'client_model', None) == 'baskerville':
            b.mc['fixstats_speed_zero'] = 'client'
            b.mc['superarmor_damage_ban'] = 'client'
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
            elif k == 'armor':
                boss.sa_max += p['add']
                boss.sa += p['add']
            elif k in ('drain', 'bleed', 'pressure', 'rewind', 'backflow', 'thorn', 'punish', 'march',
                       'grow', 'hit_gauge', 'debuff_amp', 'ult_cd', 'no_shield_amp', 'no_shield_chain', 'strip', 'few_buff_guard'):
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
    @staticmethod
    def _no_shield(x, names):
        """조건 NotTargetBuffStrId(31010·32167): 보호막 계열 버프(이름 목록)를 하나도 갖지 않음(NKM.Templets:43294-43306)"""
        return not any(x.has(n) for n in names)

    def _cur_ctx(self):
        return getattr(self.b, '_cast_ctx', None)

    def after_cast(self, u, sk, ctx, extra):
        boss = self.boss
        if boss is None:
            return
        b = self.b
        if self.cfg['model'] == 'belgras':
            self._minion_tick()
        if boss.eff.get(CH_GUARD) is not None:
            self._drop(boss, CH_GUARD)            # few_buff_guard: 지속 0턴 — 그 시전 동안만
        if u.side == 0:
            # EX: hit_gauge — SE 9400701 NSEAT_DAMAGE_END: 공격 스킬 처리 끝에 시전자의 대상 목록 각자에게 1회(NKM:15742 → 21183).
            # 타격·다단 히트마다가 아니라 «보스를 대상으로 한 아군 공격 스킬 1번당 1회»
            if 'hit_gauge' in self.fx and sk.is_attack and not boss.dead and boss in (getattr(ctx, 'targets', None) or []):
                self.stats['hit_gauge'] += 1
                b.set_gauge(boss, boss.gauge + self.fx['hit_gauge']['pct'] * 100)
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
                        # 압박(SE 9401801)은 비강제 게이지 감소 — 회피·면역 대상은 거부(NKM:4394-4398·4540-4566, mc.gauge_cd_immune)
                        if not x.dead and not b._harm_evaded(x, ctx) and not b._harm_immune(x):
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
            # EX: ult_cd — NSEAT_SKILL_END, 타격 후 대상 궁극기 쿨 증가 (SE 9402201, AutoTargetId 21)
            if 'ult_cd' in fx:
                for x in hit:
                    # BI_HYPER_COOL_TURN_UP(2505): EffectHitCheck=false 라 저항 판정만 없고, 비강제(ForceApplyEffect=false)라
                    # 회피·면역 거부는 받음(NKM:4323·4394·4559 — 압박과 같음, codex 2차 리뷰)
                    if not x.dead and '궁극기' in x.cd and not b._harm_evaded(x, ctx) and not b._harm_immune(x):
                        x.cd['궁극기'] = x.cd['궁극기'] + fx['ult_cd']['turns']
                        self.stats['ult_cd'] += 1
            # EX: no_shield_chain — NSEAT_SKILL_END cond 32167, 기본기 타격 후 보호막 없는 대상이면 적 전체 연쇄 (SE 9402501)
            if 'no_shield_chain' in fx and sk.slot == '기본기':
                for x in hit:
                    # AfterMyAttack(NKM:8037 → 15963): 피해 기록 중 하나라도 «처치 안 됨 + 보호막 계열 없음(이번 타격에 깨진 것 포함)»이면 참
                    if not x.dead and self._no_shield(x, fx['no_shield_chain']['names']):
                        coef = fx['no_shield_chain']['atkRate'] / 100.0
                        if b.mc['chain_timing'] == 'client_queue':
                            # SE9402501 = BI_ADD_DAMAGE_1(2510, 응징과 같음): 같은 클라 추가 피해 큐·같은 묶음(NKM:4721-4742 → 6244-6320)
                            b.queue_punish(boss, b.alive(0), coef, ctx, se='cosmo_no_shield_chain')
                        else:
                            for v in b.alive(0):
                                self._chain_atk(boss, v, coef, ctx)
                        self.stats['no_shield_chain'] += 1
                        break
            # EX: strip — NSEAT_SKILL_END cond 2107, 타격 후 대상 강화 1개 해제 저항 무시 (SE 9402801)
            if 'strip' in fx:
                for x in hit:
                    if not x.dead and not b._harm_evaded(x, ctx):
                        names = [n for n, e in x.eff.items() if e.category == 'buff' and not e.fixed
                                 and b._dispel_shield_ok(e)]
                        if names:
                            b._dispel_n_ordered(x, names, fx['strip']['count'])
                            b.dirty(x)
                            self.stats['strip'] += 1
        # EX: grow — NSEAT_SKILL_END, 스킬 사용 후 주는 피해 중첩 증가 (SE 9400101)
        if 'grow' in fx and not boss.dead:
            self._put(boss, CH_GROW_EX, {'피해 증가': fx['grow']['pct']}, maxs=fx['grow']['max'])
            self.stats['grow'] += 1
        if self.cfg['model'] == 'belgras':
            self._belgras_cast(sk, ctx, hit)

    def _thorn(self, x, ctx, times, turns):
        bm = self.cfg['bel']['thorn']
        self.stats['thorn'] += 1
        self.b.add_effect(self.boss, x, dict(kind='buff', target='', name=THORN, chance=1.0, dur=turns, props={}, max=5, times=times,
                                             judge=False, ignore_resist=True, dot=('atk', bm['atkRatePct'] / 100.0)), ctx)

    def _chain_atk(self, owner, v, coef, ctx=None):
        """공격력 비례 연쇄 피해: mc.Battle.chain 과 같은 식(대상 1명). ctx 를 주면 시전자의 이번 스킬 피해 증가(ctx.inc·대상별)도 읽음 —
        클라는 연쇄 생성 때 현재 NST_RATE_DAMAGE_UP 을 읽음(NKM:4734·6226, mc.chain_skill_damage_up 과 같은 조건)"""
        self.b.apply_damage(owner, v, self._chain_dmg(owner, v, coef, ctx), 'chain', shieldable=True)

    def _chain_dmg(self, owner, v, coef, ctx=None):
        """연쇄 피해량(즉시 넣는 경로): 공격자 쪽 값(_chain_pre) + 대상 쪽 계산(_chain_hit)"""
        return self._chain_hit(owner, v, self._chain_pre(owner, v, coef, ctx))

    def _chain_pre(self, owner, v, coef, ctx=None):
        """클라 AddDamage 생성 때 정하는 공격자 쪽 값(NKM:4734·6226): 공격력 x 계수 x (1 + 주는 피해 증가), 관통"""
        b = self.b
        m = owner.mods()
        inc = m['inc']
        if ctx is not None and ctx.src is owner and b.mc['chain_skill_damage_up']:
            inc += ctx.inc + ctx.local_by[v]['inc']
        return dict(base=b.atk_stat(owner) * coef * (1 + inc), pen=m['pen'], side=owner.side)

    def _chain_hit(self, owner, v, pre):
        """넣을 때 계산하는 대상 쪽(NKM:8168·17797): 대상 방어(그때 값)·난수·전투력 보정"""
        from .. import rules as R
        b = self.b
        de = b.def_stat(v)
        dr = de / (de + R.DEF_K)
        dr = max(0.0, dr - dr * min(1.0, pre['pen']))
        return max(1.0, math.floor(pre['base'] * R.BASE_MULT * (1 - dr) * b.rand(pre['side']) * b.pen[pre['side']]))

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
                e.shield = max(e.shield, math.floor(boss.maxhp * self.b.cosmo_boss_barrier_pct(mm) / 100.0))
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
                d = bm['hyperGauge']['enemy'] * 100
                # 벨그라스 궁극기 적 게이지 감소(SE 930082355)도 비강제 — 회피·면역 대상은 거부(mc.gauge_cd_immune)
                if d < 0 and (b._harm_evaded(x, ctx) or b._harm_immune(x)):
                    continue
                b.set_gauge(x, x.gauge + d)
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
        # EX: few_buff_guard(SET_33, SE 9403301) — NSEAT_DAMAGE_START 는 스킬 피해 처리 직전 1회(NKM:15689). 조건 5509
        # MyEffectiveDamageStart(NKM:10171): 시전자가 다른 편·스킬이 SAT_ATTACK·시전자 강화 효과 수 <= maxBuffs(0개도 참,
        # NKM.Templets:43320). 참이면 보스 자신에게 받는 피해 감소(지속 0턴 = 그 행동 동안) → 그 시전의 보스 피해 전부에 적용,
        # 시전이 끝나면(after_cast) 지운다. 판정은 시전당 한 번, 그 시전의 첫 보스 타격 직전 상태로.
        boss = self.boss
        if 'few_buff_guard' in self.fx and v is boss and a is not None and a.side != boss.side:
            ctx = self._cur_ctx()
            if (ctx is not None and ctx is not self._guard_ctx and getattr(ctx, 'src', None) is a
                    and ctx.skill is not None and ctx.skill.is_attack):
                self._guard_ctx = ctx
                p = self.fx['few_buff_guard']
                if a.n_good() <= p['maxBuffs']:
                    self.stats['few_buff_guard'] += 1
                    self._put(boss, CH_GUARD, {'받는 피해 감소': p['pct']}, cat='marker', src=boss)
        # EX: no_shield_amp — NSEAT_SKILL_START cond 31010, 보호막 없는 대상 단일 타격 시 피해 증가 (SE 9402401)
        # OnMyAttack(NKM:9590-9606 → 9675 → NKM.Templets 42715): 스킬 대상 유형대로 모은 대상 중 하나라도 보호막 계열이 없으면 참 —
        # 표 주석의 «광역이면 미동작»과 달리 코드는 광역도 대상 전원으로 판정(클라 코드 우선). 첫 타격 전 = 스킬 시작 때 상태
        if a is self.boss and 'no_shield_amp' in self.fx:
            ctx = self._cur_ctx()
            if ctx is not None and ctx is not self._shield_amp_ctx and ctx.skill is not None and ctx.skill.is_attack:
                self._shield_amp_ctx = ctx
                pool = [x for x in (ctx.targets or []) if x.side != a.side] or ([v] if v is not None else [])
                if any(self._no_shield(x, self.fx['no_shield_amp']['names']) for x in pool):
                    ctx.inc += self.fx['no_shield_amp']['pct'] / 100.0
                    self.stats['no_shield_amp'] += 1

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
                self._put(a, CH_DRAIN, {'생명력%': -fx['drain']['pct']}, cat=b.mc['cosmo_drain_category'], maxs=fx['drain']['max'], fixed=True, dead_keep=True)
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
                    self.stats['thorn_gauge'] += 1
                    b.set_gauge(boss, boss.gauge + bm['passive1']['thornHitGaugePct'] * 100)    # 패시브1: 가시 상태 적의 단일 공격에 피격 후 게이지 +20%
        elif a.side == 0 and v.side == 1 and self.cfg['model'] == 'belgras' and getattr(v.d, 'cosmo', None) and v.d.cosmo.get('model') == 'minion':
            self._minion_hit(a, v)
        elif (a is boss and v.side == 0 and self.cfg['model'] == 'belgras' and sk is not None and sk.slot == '궁극기'
              and b.mc['cosmo_hyper_true_target'] == 'enemy_all'):
            n = min(self._stacks(boss, ROT), self.cfg['bel']['hyperTrueDamage']['max'])
            if n > 0:
                damage = self.cfg['bel']['hyperTrueDamage']['perStack'] * n
                if b.mc['fixed_true_formula'] == 'client':
                    b.fixed_true_damage(boss, v, damage)
                else:
                    b.apply_damage(boss, v, damage, 'true', shieldable=True)
                self.stats['true_damage_hits'] += 1
