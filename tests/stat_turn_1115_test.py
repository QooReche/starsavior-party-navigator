# -*- coding: utf-8 -*-
"""클라 대조 후속(build 26610546):
- guard_tie 적 쪽: 게임 칸 번호(배치 SpawnPosIndex)로 전열(칸 1·2) 우선 (NKM:1286-1311·13247-13253).
- stat_stage: 최종 공격력·방어력·속도 = 2단(패시브·장비) 곱 뒤 3단(버프) 곱 (NKM:18783-18905).
- stat_floor: 속도도 최종 정수.
- turn_gauge: 게이지 정수 증가 (int)(속도 x 틱), 동률은 등장 때 굴린 우선순위 (NKM:12286-12431·1962).
실행: python -X utf8 -I tests/stat_turn_1115_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit, give                            # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402


def test_defaults_client():
    assert MC_OPTS['stat_stage'] == 'client' and MC_OPTS['turn_gauge'] == 'client'


# ---------------- guard_tie 적 쪽
def _foe_tie(mode, slots):
    """적 3기: 대상 칸 slots[0], 수호 후보 둘(같은 비율) 칸 slots[1]·slots[2]. 먼저 보는 쪽 = 두 번째 적"""
    b = battle([unit('a')], [unit('t'), unit('g1'), unit('g2')],
               mc={'guard_tie': mode, 'chain_guard': 'client', 'living_slot_order': 'legacy'})
    t, g1, g2 = b.foes
    for u, sl in zip((t, g1, g2), slots):
        u.d.game_slot = sl
    for w in (g1, g2):
        give(w, '수호', {'피해 분담(수호)': 30})
    return b, b._chain_guard(t, 1000.0)[0], (t, g1, g2)


def test_foe_guard_tie_front_slot():
    # 485 꼴(칸 0·2·4): 칸 4(전열·후열 모두 아님)가 먼저 보여도 칸 2(전열)가 수호
    b, g, (t, g1, g2) = _foe_tie('client', (0, 4, 2))
    assert g is g2, g.name
    assert b.rule_hits['guard_tie'] >= 1


def test_foe_guard_tie_both_front_smaller():
    _, g, (t, g1, g2) = _foe_tie('client', (0, 2, 1))
    assert g is g2, g.name


def test_foe_guard_tie_first_or_unknown():
    _, g, (t, g1, g2) = _foe_tie('first', (0, 4, 2))
    assert g is g1
    _, g, (t, g1, g2) = _foe_tie('client', (0, None, 2))     # 칸을 모르는 후보가 있으면 먼저 본 쪽
    assert g is g1


def test_front_slot_deck():
    from battlesim.mc import Battle
    f = Battle._front_slot
    assert [i for i in range(5) if f(i, 'BATTLE_SLOT_4')] == [1, 2]
    assert [i for i in range(5) if f(i, 'BATTLE_SLOT_1')] == [0]
    assert [i for i in range(5) if f(i, 'BATTLE_SLOT_2')] == [0, 1]
    assert [i for i in range(5) if f(i, 'BATTLE_SLOT_3')] == [1]


# ---------------- stat_stage / stat_floor
def _stats(stage, floor='client'):
    b = battle([unit('a', atk=1000, df=1000, spd=100)], [unit('f')], mc={'stat_stage': stage, 'stat_floor': floor})
    a = b.allies[0]
    a.d.passive['atkp'] += 0.2
    a.d.passive['defp'] += 0.2
    a.d.passive['spdp'] += 0.1
    give(a, '버프', {'공격력%': 30, '방어력%': 30, '속도%': 20})
    return b, a


def test_stat_stage_client_multiplies_buff_stage():
    b, a = _stats('client')
    assert (b.atk_stat(a), b.def_stat(a), a.spd()) == (1560.0, 1560.0, 132), (b.atk_stat(a), b.def_stat(a), a.spd())
    assert b.live_atk(a) == 1560.0


def test_stat_stage_add_legacy():
    b, a = _stats('add')
    assert (b.atk_stat(a), b.def_stat(a), a.spd()) == (1500.0, 1500.0, 130), (b.atk_stat(a), b.def_stat(a), a.spd())


def test_speed_floor():
    b = battle([unit('a', spd=101)], [unit('f')], mc={'stat_floor': 'client'})
    a = b.allies[0]
    give(a, '버프', {'속도%': 7})
    assert a.spd() == 108, a.spd()                              # 101 x 1.07 = 108.07
    b = battle([unit('a', spd=101)], [unit('f')], mc={'stat_floor': 'float', 'stat_stage': 'add'})
    a = b.allies[0]
    give(a, '버프', {'속도%': 7})
    assert abs(a.spd() - 108.07) < 1e-6, a.spd()


def test_stage2_merges_gear_and_passive():
    # calc_stats 가 남긴 1단 1000·각인/장비 30%·장비 정수 50 → 전투 전 공격력 floor(1000 x 1.3 + 50) = 1350.
    # 클라 2단 = 1000 + 50 + 1000 x (0.3 + 패시브 0.2) = 1550 (각인/장비 % 와 패시브 % 가 한 합). 근사(옛 곱) = 1350 x 1.2 = 1620
    b = battle([unit('a', atk=1350)], [unit('f')], mc={'stat_stage': 'client', 'stat_floor': 'client'})
    a = b.allies[0]
    a.d.stat_stage = {'atk': (1000.0, 0.3, 50)}
    a.d.passive['atkp'] += 0.2
    assert b.atk_stat(a) == 1550.0, b.atk_stat(a)
    a.d.stats['atk'] = 1400                                      # 내정보 덮어쓰기 등으로 값이 바뀌면 단 정보를 안 씀
    assert b.atk_stat(a) == 1680.0, b.atk_stat(a)


# ---------------- turn_gauge
def _first_actor(mode, seed):
    b = battle([unit('a', spd=100)], [unit('f', spd=100)], mc={'turn_gauge': mode}, seed=seed)
    order = []
    orig = b.act
    b.act = lambda u: (order.append(u.name), orig(u))
    b.turn_limit = 1
    b.run()
    return b, order


def test_turn_gauge_tie_by_priority():
    firsts = set()
    for seed in range(1, 30):
        b, order = _first_actor('client', seed)
        assert order, seed
        firsts.add(order[0])
        # 우선순위는 등장 때 이미 굴려 둠(NKM:1962)
        assert all(u._turn_prio is not None for u in b.allies + b.foes)
    assert firsts == {'a', 'f'}, firsts                          # 같은 속도·게이지면 우선순위 난수로 갈림
    for seed in range(1, 10):
        b, order = _first_actor('float', seed)
        assert order[:1] == ['a'], order                         # legacy: 아군 먼저
        assert all(u._turn_prio is None for u in b.allies + b.foes)


def _gauges_at_first_act(mc, a_spd=333, f_spd=100, a_gauge=0.0, f_gauge=0.0):
    b = battle([unit('a', spd=a_spd)], [unit('f', spd=f_spd)], mc=mc)
    b.allies[0].gauge, b.foes[0].gauge = a_gauge, f_gauge
    b.turn_limit = 1
    seen = []
    orig = b.act
    b.act = lambda u: (seen.append((u.name, [x.gauge for x in b.allies + b.foes])), orig(u))
    b.run()
    return seen


def test_turn_gauge_integer_increments():
    seen = _gauges_at_first_act({'turn_gauge': 'client'})
    assert seen and all(float(g).is_integer() for g in seen[0][1]), seen
    assert seen[0][1][1] == int(100 * (10000 / 333)), seen      # (int)(100 x 30.03…) = 3003
    seen = _gauges_at_first_act({'turn_gauge': 'float'})
    assert not float(seen[0][1][1]).is_integer(), seen


def test_turn_gauge_no_advance_when_ready():
    # 누가 100% 이상이면 이번 계산에서 아무도 게이지가 안 오름(NKM:12415-12421)
    seen = _gauges_at_first_act({'turn_gauge': 'client', 'gauge_overflow': True}, a_gauge=10500.0, f_gauge=1234.0)
    assert seen[0] == ('a', [10500.0, 1234.0]), seen


def test_set_gauge_stores_int():
    b = battle([unit('a')], [unit('f')], mc={'turn_gauge': 'client'})
    b.set_gauge(b.allies[0], 1234.9)
    assert b.allies[0].gauge == 1234.0
    b = battle([unit('a')], [unit('f')], mc={'turn_gauge': 'float'})
    b.set_gauge(b.allies[0], 1234.9)
    assert abs(b.allies[0].gauge - 1234.9) < 1e-9


def test_round_split_truncates_once():
    # 브레이크 라운드 경계(break_skill_cd_unit=round, 100틱)로 구간이 나뉘어도 절삭은 다음 행동까지 한 번
    # (codex 리뷰 재현: 속도 101·100 — 아군 99.0099틱 행동 뒤 적 행동 때 아군 게이지 101, 경계마다 자르면 100)
    b = battle([unit('a', spd=101)], [unit('f', spd=100, hp=10 ** 9)],
               mc={'turn_gauge': 'client', 'break_skill_cd_unit': 'round'}, break_skill={'name': '큐브 과부하'})
    assert b.break_skill_enabled
    seen, orig = [], b.act
    b.act = lambda u: (seen.append((u.name, [x.gauge for x in b.allies + b.foes])), orig(u))
    b.turn_limit = 2
    b.run()
    assert [n for n, _ in seen] == ['a', 'f'], seen
    assert seen[1][1] == [101.0, 10000.0], seen

if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
