"""길드 공통 도전·가정 선택 효과·지원. BFB 호출 순서·난수 소비를 보존한다."""
import math
from .controller import BaseController

STACK = '폭주 : 잠식'
DRAIN = '폭주 : 쇠락'
DRAIN_SET = '폭주 : 쇠락(선택)'
BOUQUET = '부케'
IMMUNE = '면역'
SPEED = '속도 비율 스탯(별의 도전)'
NV_ADD = '보스 능력치 비율(AddStat)'
SET_DMG = '피해량 증가율(소멸)'
SET_RED = '피해량 감소율(불멸)'

# 알리시아의 지원(시즌 선택 1종, 표 근거: AI/temp/partynavigator/work/guild_defense/support_spec.md)
SUPPORTS = ('none', 'gust', 'focus', 'strike', 'mountain', 'fire')
SUP_STAT = '알리시아 지원(능력치)'
SUP_HIT = '알리시아 지원(불의 고동 적중)'
SUP_TMP_INC = '알리시아 지원(임시 피해 증가)'
SUP_TMP_RED = '알리시아 지원(임시 받는 피해 감소)'


def _stats(u, scale=(0, 0, 0)):
    s = dict(u['stats'])
    a = u['addStat']
    hp = math.floor(s['hp'] * (1 + a['hpp'] / 10000) * (1 + scale[1] / 10000))
    atk = math.floor(s['atk'] * (1 + a['atkp'] / 10000) * (1 + scale[0] / 10000))
    df = math.floor(s['def'] * (1 + a['defp'] / 10000) * (1 + scale[2] / 10000))
    spd = math.floor(s['spd'] * (1 + a['spdp'] / 10000) + 1e-9)
    return dict(hp=hp, atk=atk, **{'def': df}, spd=spd, cr=s['cr'], cd=s['cd'], eh=s['eh'], er=s['er'], der=s['der'], sa=s['sa'])


class GuildController(BaseController):
    def __init__(self, b):
        super().__init__(b)
        cfg = next((getattr(d, 'guild', None) or getattr(d, 'bfb', None) for w in b.waves for d in w
                    if getattr(d, 'guild', None) or getattr(d, 'bfb', None)), {})
        self.support = cfg.get('support', 'none')
        self.sup_done = False
        self.focus_turn = {}
        self.strike_roll = {}

    def _put(self, x, name, props, dur=math.inf, cat='buff', fixed=True, maxs=1, add=1):
        return self.b.put_eff(x, name, props, dur=dur, maxs=maxs, add=add, src=self.boss, cat=cat, fixed=fixed)


    def _drop(self, x, name):
        if x.eff.pop(name, None) is not None:
            self.b.dirty(x)


    def _sup_has(self, u):
        """이 유닛에 걸리는 지원인가(직업 전용은 해당 직업만. 대상 필터는 TargetRoleType 근거, 표 해석은 추정)"""
        s = self.support
        if s in ('mountain', 'fire'):
            return True
        return u.role == {'gust': '서포터', 'focus': '캐스터', 'strike': '스트라이커'}.get(s)


    def _sup_put(self, x, name, props, maxs=1):
        """지원 효과. 강화 효과 개수에 안 세도록 marker(보스 관통 표지와 같은 방식)"""
        self.b.put_eff(x, name, props, maxs=maxs, src=x, cat='marker')


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


    def _challenge_start(self):
        boss = self.boss
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


    def _challenge_after_cast(self):
        boss = self.boss
        row = self.cfg['row']
        if row and row['skillStack']:
            self._put(boss, STACK, {'피해 증가': row['skillStack']}, maxs=10)    # 940001~3

    def _challenge_post_hit(self, a):
        row = self.cfg['row']
        if row and row['hpDrain'] and not a.dead:
            self._put(a, DRAIN, {'생명력%': -row['hpDrain']}, cat='debuff', maxs=10)     # 940011~13
        if self.cfg['set_drain'] and not a.dead:
            self._put(a, DRAIN_SET, {'생명력%': -self.cfg['set_drain']}, cat='debuff', maxs=10)


class Controller(GuildController):
    """적 스킬·자동 대상은 범용 엔진이 실행하며 길드 효과만 더한다."""
    def on_wave(self):
        self._sup_start()
        self.bosses = [u for u in self.b.foes if u.d.boss]
        for boss in self.bosses:
            self.boss, self.cfg = boss, boss.d.guild
            self._challenge_start()

    def after_cast(self, u, sk, ctx, extra):
        if self.support != 'none':
            self._sup_after_cast(u, sk, extra)
        if u in getattr(self, 'bosses', ()) and not u.dead:
            self.boss, self.cfg = u, u.d.guild
            self._challenge_after_cast()

    def pre_hit(self, a, v):
        if self.support != 'none':
            self._sup_pre_hit(a, v)

    def post_hit(self, a, v):
        if self.support != 'none':
            self._sup_post_hit(a, v)
        if v in getattr(self, 'bosses', ()) and a is not None and a.side == 0 and not v.dead:
            self.boss, self.cfg = v, v.d.guild
            self._challenge_post_hit(a)


def scale_stats(stats, row):
    s = dict(stats)
    if row:
        for key in ('atk', 'hp', 'def'):
            s[key] = math.floor(s[key] * (1 + row[key] / 100))
    return s


def config(g, options, st):
    level = int(options.get('level', 0))
    levels = g['challenge']['levels'] if st.get('difficultyGroupId') else []
    if not 0 <= level <= len(levels):
        raise ValueError('이 단계의 별의 도전 범위: 0~%d' % len(levels))
    support = options.get('support') or 'none'
    ids = {'gust': 40152, 'focus': 40031, 'strike': 40111, 'mountain': 45041, 'fire': 45011}
    allowed = {s['id'] for s in g['supports']}
    if support != 'none' and ids.get(support) not in allowed:
        raise ValueError('이 시즌에서 실행할 수 없는 지원: ' + str(support))
    sets = list(options.get('sets') or [0, 0, 0, 0])
    if len(sets) != 4 or any(type(x) is not int or not 0 <= x <= 3 for x in sets):
        raise ValueError('선택 효과는 0~3 정수 4개')
    return dict(level=level, row=levels[level-1] if level else None, support=support, sets=sets,
                set_dmg=(0, 10, 20, 30)[sets[0]], set_red=(0, 20, 30, 40)[sets[1]],
                set_drain=(0, 3, 4, 5)[sets[2]], set_immune=sets[3])
