# -*- coding: utf-8 -*-
"""바스커빌의 괴수(코스모 시즌 1023) 시나리오 시험 — 블랙박스(구현 함수명에 기대지 않음).

실행: python -X utf8 -I tests/baskerville_scenario_test.py [--mutations]
저장소는 이 파일의 상위 폴더, 다른 작업 트리는 환경변수 SSPN_ROOT로 지정.
도우미 가정 교정·실제 PC 클라 파일:줄 근거는 docs/baskerville_scenarios_26752678.md.

근거 표기: a~h = codex_design_baskerville.md 의 클라 확정 사실, 2-x = baskerville_research.md 의 절.
  a 최대 HP 가 줄면 현재 HP 는 새 최대치를 넘을 때만 절삭(비율 유지 아님), 효과 해제만으로는 회복 없음
  b 4회 부여 = 독립 인스턴스 4개, 학살의 달밤 배율은 적 전체의 «카운팅» 객체 수 합산
  c 패시브1(불완전한 육체)의 Caster = 공격자
  d 속도 0 이어도 +25/+50%p 게이지는 받고 턴을 얻음
  e 스킬 교체: 슬롯 즉시 교체·유지, 궁극기 종료 시 역교체
  f 같은 피격에서 SE 가 순서대로 즉시 실행·조건 재판정(_01 표지를 _05~_07 이 읽음)
  g 강제 기절은 면역 그룹·기절 면역 우회
  h 회복 = 감소 후 현재 최대 HP 기준, 주는/받는 회복량 보정은 받음
"""
import os
import random
import sys
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager

ROOT = os.environ.get('SSPN_ROOT') or str(Path(__file__).resolve().parents[1])
sys.path.insert(0, ROOT)
from battlesim import simulate                                   # noqa: E402
from battlesim.api import _norm_party                            # noqa: E402
from battlesim.mc import Battle                                  # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior import cosmo_raid as C                 # noqa: E402
from battlesim.starsavior.data import get_db                     # noqa: E402

PARTY = ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']
DB = get_db()


# ---------------------------------------------------------------- 도우미
def battle(seed=1, step=3, level=0):
    waves, meta = C.build_waves('baskerville', step, level)
    defs, _ = _norm_party({'units': PARTY}, DB, 'fixed', 'standard')
    b = Battle(defs, waves, random.Random(seed), mc=dict(MC_OPTS, cosmo_raid_boss='on'), leader=0,
               turn_limit=meta['turn_limit'], battle_mode='boss_kill')
    b.spawn_wave()
    return b


def _is_heart(k):      # 표시용 «심장 마비(해제불가)» — 숨은 카운팅·피해 증가 체크 버프는 제외
    return '심장 마비' in k and '카운팅' not in k and '체크' not in k


def hearts(u):
    return sum(e.stacks for k, e in u.eff.items() if _is_heart(k) and e.stacks > 0)


def counts(u):
    """숨은 «심장 마비 중첩 카운팅 버프» 개수 = 인스턴스 여러 개든 중첩 하나든 stacks 합 (b)"""
    return sum(e.stacks for k, e in u.eff.items() if '카운팅' in k and e.stacks > 0)


def stk(u, name):
    return sum(e.stacks for k, e in u.eff.items() if name in k and e.stacks > 0)


def has(u, name):
    return stk(u, name) > 0


@contextmanager
def healing_log(b):
    """실제 회복 호출의 출처·효과 줄·실효량. HP 상한 변경은 이 기록에 포함되지 않는다."""
    records = []
    original = b.heal
    def traced(src, target, amount, give):
        real = original(src, target, amount, give)
        records.append((src, target, b._cur_line.raw if b._cur_line else '', real))
        return real
    with patch.object(b, 'heal', traced):
        yield records


def boss_of(b):
    return b.gb.boss


def scream(b):
    """보스가 특수기 칸(핏빛 절규)을 쓴다. 쿨 0, 보스 자기 턴 흉내(acting)."""
    boss = boss_of(b)
    boss.cd['특수기'] = 0
    boss.acting = True
    b.cast(boss, boss.d.skills['특수기'])
    boss.acting = False


def hit(b, who=0, boss=None):
    boss = boss or boss_of(b)
    sk = C._skill('기본기', 'test', 100, 0, 0, attack=True, tg='적 단일')
    b.cast(b.allies[who], sk, target=boss)


def big_hp(b, k=1000.0):
    """궁극기 피해량 비교용 — 아군이 죽지 않게 전투 전 최대 생명력을 키운다(시험용 조작)."""
    for a in b.allies:
        a.maxhp0 = a.maxhp0 * k
        a.hp = a.maxhp0


def _hp_fraction_after_scream(b):
    return [(a.hp, a.maxhp, a.maxhp0) for a in b.allies]


# ---------------------------------------------------------------- 시나리오 1
def test_01_scream_hearts_and_maxhp():
    """근거: a, b, 2-2·2-3. 핏빛 절규(적 전체) → 아군 전원 〈심장 마비〉 4중첩 + 숨은 카운팅 4개(각 생명력 -15%) = 최대 생명력 -60%.
    현재 HP 는 새 최대치(전투 전 값의 40%)를 넘을 때만 깎이고, 원래 낮던 HP 는 그대로(비율 유지 아님).
    보스는 〈바스커빌의 역작〉·〈억제된 야성〉 보유(SPECIAL_03/04)."""
    b = battle()
    boss = boss_of(b)
    low = b.allies[1]
    low.hp = low.maxhp0 * 0.2          # 새 최대치(40%)보다 낮은 HP
    keep = low.hp
    scream(b)
    for a in b.allies:
        assert hearts(a) == 4, (a.name, {k: e.stacks for k, e in a.eff.items()})
        assert counts(a) == 4, (a.name, {k: e.stacks for k, e in a.eff.items()})
        want = int(a.maxhp0 * 0.4)
        assert abs(a.maxhp - want) <= 2, (a.name, a.maxhp, want)
    full = b.allies[0]
    assert abs(full.hp - full.maxhp) <= 2 and full.hp < full.maxhp0 * 0.41     # 넘친 만큼만 절삭
    assert abs(low.hp - keep) < 1e-6, (low.hp, keep)                             # 낮던 HP 는 그대로
    assert has(boss, '바스커빌의 역작') and has(boss, '억제된 야성')


# ---------------------------------------------------------------- 시나리오 2
def test_02_hit_boss_with_masterpiece():
    """근거: 2-5 패시브1 _01~_04, c(Caster=공격자), f. 역작 보스를 아군이 공격 → 그 아군만 심장 마비 -1·카운팅 1개 해제
    (최대 생명력 +15%p). 해제 자체의 회복은 없음(a); 카르멘 기본기 후 별도 회복은 허용.
    송곳니는 마지막 중첩 때만 증가(표 PASSIVE1_02, 조건 55181 CasterBuffLevelCount=1)."""
    b = battle()
    boss = boss_of(b)
    scream(b)
    a, other = b.allies[0], b.allies[1]
    hp0 = a.hp
    assert stk(boss, '무뎌진 송곳니') == 0
    with healing_log(b) as heals:
        hit(b, 0)
    assert hearts(a) == 3 and counts(a) == 3, (hearts(a), counts(a))
    assert hearts(other) == 4 and counts(other) == 4                 # 맞히지 않은 아군은 그대로
    assert abs(a.maxhp - int(a.maxhp0 * 0.55)) <= 2, (a.maxhp, a.maxhp0)
    actual = sum(real for _, target, _, real in heals if target is a)
    assert actual > 0 and all(src is a and '생명력×2.5%' in raw for src, _, raw, _ in heals), heals
    assert abs(a.hp - hp0 - actual) < 1e-6, ('해제만으로 회복하면 안 됨', a.hp, hp0, actual)
    assert stk(boss, '무뎌진 송곳니') == 0
    hit(b, 0)
    assert stk(boss, '무뎌진 송곳니') == 0 and hearts(a) == 2


# ---------------------------------------------------------------- 시나리오 3
def _last_stack_heal(with_decrease):
    b = battle()
    scream(b)
    a = b.allies[2 if with_decrease else 0]
    if with_decrease:
        # 회복 감소: 받는 회복량 -50% (BI_HEAL_RECEIVE_DECREASE). props 키·단위는 구현 가정(엔진 mc.py:794 '받는 회복량', % 단위)
        b.put_eff(a, '회복 감소', {'받는 회복량': -50.0}, dur=5, maxs=1, add=1, src=boss_of(b), cat='debuff', fixed=False)
    for _ in range(3):
        hit(b, b.allies.index(a))
    assert hearts(a) == 1 and counts(a) == 1 and not has(a, '아드레날린')
    a.hp = 1.0
    hit(b, b.allies.index(a))
    return b, a


def test_03_last_stack_heal_adrenaline():
    """근거: 2-5 패시브1 _05~_07, f, h. 마지막 중첩을 지운 아군은 생명력 회복(현재 최대 = 원래 최대, 감소 후 기준) + 〈아드레날린〉.
    회복 감소(-50%)가 걸려 있으면 회복량이 줄어듦(주는/받는 회복량 보정 적용 — h)."""
    b, a = _last_stack_heal(False)
    assert hearts(a) == 0 and counts(a) == 0
    assert has(a, '아드레날린'), {k: e.stacks for k, e in a.eff.items()}
    assert stk(boss_of(b), '무뎌진 송곳니') == 1
    assert abs(a.maxhp - a.maxhp0) <= 2
    healed = a.hp - 1.0
    assert healed >= a.maxhp * 0.99 - 1, (a.hp, a.maxhp)             # 보정 없으면 사실상 전회복
    b2, a2 = _last_stack_heal(True)
    assert has(a2, '아드레날린') and hearts(a2) == 0
    healed2 = a2.hp - 1.0
    assert 0 < healed2 < healed * 0.75, (healed2, healed)             # 회복 감소로 줄어듦(-50% 기대, 여유 둠)


# ---------------------------------------------------------------- 시나리오 4
def _ally_turn_start(b, who=0):
    """아군(= 보스의 적) 턴 시작 처리. 구현 세부 의존: Battle._act_turn (엔진 내부, mc.py). 이름이 바뀌면 이 도우미만 고칠 것."""
    a = b.allies[who]
    b._act_turn(a)
    return a


def test_04_suppressed_speed_zero_but_gauge():
    """근거: 2-5 패시브2 _01·_02, 2-6, d. 억제된 야성 = 보스 속도 0. 그래도 아군 턴 시작(+25%p)·아군 비공격 스킬 후(+50%p)에는
    행동 게이지를 받는다(속도 0 때문에 증가가 막히면 안 됨 — 길방 〈들러리〉 zero_stats 와 다름)."""
    b = battle()
    boss = boss_of(b)
    scream(b)
    assert has(boss, '억제된 야성')
    assert boss.spd() == 0, boss.spd()
    # 비공격 후 (+50%p)
    boss.gauge = 0.0
    sk = C._skill('특수기', 'test-na', 0, 0, 0, attack=False, tg='자신')
    b.cast(b.allies[0], sk)
    g_na = boss.gauge
    assert g_na > 0, '적 비공격 스킬 후 게이지 증가 없음'
    # 턴 시작 (+25%p)
    boss.gauge = 0.0
    _ally_turn_start(b, 1)
    assert boss.gauge > 0, '적 턴 시작 게이지 증가 없음'
    assert boss.spd() == 0


# ---------------------------------------------------------------- 시나리오 5
def _ult_damage(remaining_total, with_immunity=False, normalize_fangs=True, remaining_by_ally=None):
    """보스 타격으로 카운팅을 준비. 피해는 회복과 독립인 taken 통계 차로 측정한다."""
    b = battle()
    big_hp(b)
    boss = boss_of(b)
    scream(b)
    tot = sum(counts(a) for a in b.allies)                           # 16
    assert tot == 16, tot
    if remaining_by_ally is not None:
        assert len(remaining_by_ally) == 4 and sum(remaining_by_ally) == remaining_total
        assert all(0 <= n <= 4 for n in remaining_by_ally)
    i = 0
    while tot > remaining_total:
        a = b.allies[i % 4]
        i += 1
        minimum = remaining_by_ally[(i - 1) % 4] if remaining_by_ally is not None else 0
        if counts(a) > minimum:
            hit(b, b.allies.index(a))
            tot -= 1
    assert sum(counts(a) for a in b.allies) == remaining_total
    # 마지막 중첩을 해제한 사람 수만큼 송곳니가 생긴다(매 타격이 아님).
    assert stk(boss, '무뎌진 송곳니') == sum(hearts(a) == 0 for a in b.allies)
    if normalize_fangs:
        # +10%/객체만 비교하기 위한 시험 조작: 별도 가산항(-5%/송곳니)을 0으로 통일.
        for name in list(boss.eff):
            if '무뎌진 송곳니' in name:
                del boss.eff[name]
        b.dirty(boss)
    stun_probe = {}
    if with_immunity:
        for a in b.allies:
            b.put_eff(a, '기절 면역', {}, dur=5, maxs=1, add=1, src=a, cat='buff', fixed=False)
    had_heart = [hearts(a) > 0 for a in b.allies]
    # 치명타·명중 난수를 맞추려고 시전 직전 난수 고정.
    b.rng.seed(12345)
    before = [a.taken for a in b.allies]
    hp_before = sum(a.hp for a in b.allies)
    boss.cd['궁극기'] = 0
    boss.acting = True
    with healing_log(b) as heals:
        b.cast(boss, boss.d.skills['궁극기'])
    boss.acting = False
    lost = sum(a.taken - x for x, a in zip(before, b.allies))
    assert all(not a.dead for a in b.allies)
    healed = sum(real for _, target, _, real in heals if target.side == 0)
    assert all(src.side == 0 for src, _, _, _ in heals), heals  # 궁극기에는 보스의 BI_HEAL 없음.
    assert abs(sum(a.hp for a in b.allies) - hp_before - healed + lost) < 1e-6
    b.scenario_heals = heals
    for a, h in zip(b.allies, had_heart):
        stun_probe[a.name] = (h, a.has('기절'))  # 부분 일치로 «기절 면역»을 세지 않는다.
    return lost, b, stun_probe


def test_05_ult_damage_scaling_and_forced_stun():
    """근거: 2-5 HYPER_01·_03·_04~08, b, g. 학살의 달밤: 적 전체 카운팅 개수 합 × 10% 피해 증가.
    남은 개수 0·2·4에서 피해가 단조 증가하고 비율이 1.0 : 1.2 : 1.4(정수 절삭 오차 허용).
    무뎌진 송곳니는 시험에서 0중첩으로 통일. 난수는 시전 직전 고정."""
    d0, _, _ = _ult_damage(0)
    d2, _, _ = _ult_damage(2)
    d4, _, _ = _ult_damage(4)
    assert d0 > 0 and d0 < d2 < d4, (d0, d2, d4)
    assert abs(d2 / d0 - 1.2) < .002, (d0, d2, d4)
    assert abs(d4 / d0 - 1.4) < .002, (d0, d2, d4)
    concentrated, _, _ = _ult_damage(4, remaining_by_ally=(4, 0, 0, 0))
    assert abs(concentrated / d4 - 1) < .002, (concentrated, d4)  # 보유자 수가 아닌 객체 수 합.
    # 원래 실패를 재현하는 조건에서도 회복은 피해 통계를 깎지 않는다.
    damage, b, _ = _ult_damage(4, normalize_fangs=False)
    assert damage > 0
    assert any(real > damage and src is target and '생명력×8%' in raw
               for src, target, raw, real in b.scenario_heals), b.scenario_heals


def test_05b_ult_forced_stun_ignores_immunity():
    """근거: 2-5 HYPER_03, 2-6, g. 궁극기 시전 순간 심장 마비를 가진 아군은 기절 면역(·면역 그룹)이 있어도 기절. 마비가 없는 아군은 안 걸림.
    기절은 심장 마비 해제(HYPER_04)보다 먼저 판정되므로, 시전 후 마비가 지워져도 기절은 남는다."""
    _, b, probe = _ult_damage(4, with_immunity=True, normalize_fangs=False)
    stunned = [n for n, (h, s) in probe.items() if s]
    holders = [n for n, (h, s) in probe.items() if h]
    assert holders and set(stunned) == set(holders), probe
    assert all(hearts(a) == 0 and counts(a) == 0 for a in b.allies)   # 궁극기가 심장 마비·카운팅 정리(HYPER_04~08)
    assert not has(boss_of(b), '바스커빌의 역작') and stk(boss_of(b), '무뎌진 송곳니') == 0
    # 마비 보유자가 하나도 없으면(개수 0) 아무도 기절하지 않음
    _, b0, probe0 = _ult_damage(0, with_immunity=True, normalize_fangs=False)
    assert not any(s for _, s in probe0.values()), probe0
    assert stk(boss_of(b0), '무뎌진 송곳니') == 0  # 시전 전 4중첩의 실제 해제 검사.
    # 일부만 보유한 경계도 검사: 면역 판독 오류/전원 대상 대체를 함께 검출.
    _, bm, mixed = _ult_damage(2, with_immunity=True, normalize_fangs=False)
    assert sum(h for h, _ in mixed.values()) == 2
    assert all(h == s for h, s in mixed.values()), mixed
    assert all(hearts(a) == 0 and counts(a) == 0 for a in bm.allies)
    assert stk(boss_of(bm), '무뎌진 송곳니') == 0


# ---------------------------------------------------------------- 시나리오 6
def test_06_skill_swap_roundtrip():
    """근거: e, 2-2 특수기(교체), 2-5 SPECIAL_05·HYPER_09. 핏빛 절규 후 특수기 칸 = 파멸의 숨결(공격 단일: 공격력 감소·속도 감소 부여,
    심장 마비 추가 부여 없음), 궁극기 뒤 원래 칸 = 핏빛 절규(심장 마비 다시 부여). 쿨은 직접 0 으로 두고 시험(쿨 +1 규칙은 시험 안 함).
    구분은 효과로만 한다(스킬 이름 속성에 기대지 않음)."""
    b = battle()
    boss = boss_of(b)
    scream(b)
    a0 = b.allies[0]
    h_before = hearts(a0)
    assert h_before == 4
    scream(b)                                    # 같은 칸을 다시 → 교체돼 있어야 함
    assert hearts(a0) == h_before, ('교체 안 됨: 심장 마비가 늘었음', hearts(a0))
    debuffed = [a for a in b.allies if has(a, '공격력 감소') or has(a, '속도 감소')]
    assert debuffed, '파멸의 숨결 디버프(공격력/속도 감소) 없음'
    # 궁극기 → 역교체
    boss.cd['궁극기'] = 0
    boss.acting = True
    b.cast(boss, boss.d.skills['궁극기'])
    boss.acting = False
    assert hearts(a0) == 0
    scream(b)
    assert hearts(a0) == 4, ('궁극기 뒤 핏빛 절규로 돌아오지 않음', hearts(a0))
    assert has(boss, '바스커빌의 역작')


# ---------------------------------------------------------------- 시나리오 7
def test_07_simulate_whole():
    """근거: 2-1(배치 1웨이브·보스 칸), 조사 결론(sim=true 로 전환). 시뮬 전체가 오류 없이 돌고 progress>0,
    미지원(unsupported.runtime)에 «미지원» 문구 없음."""
    r = simulate({'units': PARTY}, {'cosmo_raid': {'boss': 'baskerville', 'step': 3, 'level': 0}},
                 {'seed': 1, 'n_runs': 2, 'build': 'standard'})
    assert r['encounter']['cosmo_raid']['boss'] == 'baskerville'
    assert r['outcome']['progress'] > 0, r['outcome']
    un = r.get('unsupported') or {}
    assert not any('미지원' in k for k in (un.get('runtime') or {})), un


TESTS = [test_01_scream_hearts_and_maxhp, test_02_hit_boss_with_masterpiece, test_03_last_stack_heal_adrenaline,
         test_04_suppressed_speed_zero_but_gauge, test_05_ult_damage_scaling_and_forced_stun,
         test_05b_ult_forced_stun_ignores_immunity, test_06_skill_swap_roundtrip, test_07_simulate_whole]


def mutations():
    """클라 사실을 어긴 실행 경로를 주입하고 단언 실패로 검출하는지 확인한다."""
    auto, execute, forced = Battle.line_auto_targets, Battle.exec_line, Battle._forced
    se = C.Controller.execute_se

    def fallback(self, owner, spec, ctx):
        targets = auto(self, owner, spec, ctx)
        if self._cur_line and self._cur_line.eff.get('name') == '기절' and not targets:
            return self.alive(1 - owner.side)
        return targets

    def restore_hp(self, owner, ln, ctx):
        before = [(a, a.maxhp) for a in self.allies]
        result = execute(self, owner, ln, ctx)
        for a, maximum in before:
            if a.maxhp > maximum:
                a.hp = min(a.maxhp, a.hp + a.maxhp - maximum)
        return result

    def restore_hp_ult(self, owner, ln, ctx):
        if owner.side == 1 and ln.slot == '궁극기':
            return restore_hp(self, owner, ln, ctx)
        return execute(self, owner, ln, ctx)

    def no_count(self, owner, ln, ctx):
        if ln.eff['meta']['op'] != 'specific_count':
            return se(self, owner, ln, ctx)

    def count_holders(self, owner, ln, ctx):
        p = ln.eff['meta']
        if p['op'] == 'specific_count':
            ctx.inc += p['rate'] * sum(x.has(p['name']) for x in self.b.alive(1 - owner.side))
        else:
            return se(self, owner, ln, ctx)

    def no_force(self, owner, name=None):
        return False if name == '기절' else forced(self, owner, name)

    cases = [
        ('빈 자동 대상 전원 대체', Battle, 'line_auto_targets', fallback, test_05b_ult_forced_stun_ignores_immunity),
        ('개별 HP 감소 해제 시 회복', Battle, 'exec_line', restore_hp, test_02_hit_boss_with_masterpiece),
        ('궁극기 HP 감소 해제 시 회복', Battle, 'exec_line', restore_hp_ult, test_05_ult_damage_scaling_and_forced_stun),
        ('카운팅 피해 배율 제거', C.Controller, 'execute_se', no_count, test_05_ult_damage_scaling_and_forced_stun),
        ('객체 수 대신 보유자 수', C.Controller, 'execute_se', count_holders, test_05_ult_damage_scaling_and_forced_stun),
        ('면역 무시 제거', Battle, '_forced', no_force, test_05b_ult_forced_stun_ignores_immunity),
    ]
    for name, cls, attr, fn, test in cases:
        with patch.object(cls, attr, fn):
            try:
                test()
            except AssertionError:
                print('검출', name)
            else:
                raise AssertionError('변이를 검출하지 못함: ' + name)
    for test in TESTS:
        test()
    print('변이 %d/%d 검출, 원복 후 시나리오 %d/%d 통과' % (len(cases), len(cases), len(TESTS), len(TESTS)))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
        sys.exit(0)
    bad = 0
    for t in TESTS:
        try:
            t()
            print('ok', t.__name__)
        except Exception as e:      # noqa: BLE001
            bad += 1
            print('FAIL', t.__name__, type(e).__name__, e)
    sys.exit(1 if bad else 0)
