# -*- coding: utf-8 -*-
"""기대값 엔진(engine.Sim)의 행동 게이지가 몬테카를로 엔진(mc.Battle)의 turn_gauge=client 와 같은 계산인지
(build 26610546 NKM.decompiled.cs:12286-12431 — 정수 증가 (int)(속도 x 틱), 100% 이상이면 증가 없음, 정렬 키).
실행: python -X utf8 -I tests/ev_gauge_test.py"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit                                   # noqa: E402
from battlesim import engine, gauge, mc                           # noqa: E402
from battlesim.engine import DummyDef, Sim                        # noqa: E402
from battlesim.rules import DEFAULT_OPTS, INF_HP, MC_OPTS         # noqa: E402


def _ev_order(spds, espd, mode, n=40, turns=30):
    o = dict(DEFAULT_OPTS, turn_gauge=mode)
    sim = Sim([DummyDef(name='a%d' % i, spd=s) for i, s in enumerate(spds)],
              [dict(name='f', hp=INF_HP, **{'def': 0}, spd=espd)], turns, o)
    log, oa, oe = [], sim.act_ally, sim.act_enemy
    sim.act_ally = lambda a: (log.append(a.name), oa(a))
    sim.act_enemy = lambda e: (log.append('f'), oe(e))
    sim.run()
    return log[:n]


def _mc_order(spds, espd, mode, n=40):
    b = battle([unit('a%d' % i, spd=s, hp=10 ** 9, atk=1) for i, s in enumerate(spds)],
               [unit('f', spd=espd, hp=10 ** 9, atk=1)], mc={'turn_gauge': mode})
    log, orig = [], b.act
    b.act = lambda u: (log.append(u.name), orig(u))
    b.turn_limit = n
    b.run()
    return log[:n]


def test_default_reads_mc_rule():
    assert MC_OPTS['turn_gauge'] == 'client'
    assert Sim([DummyDef()], [dict(name='f', hp=INF_HP, spd=100)], 1).turn_gauge == 'client'
    assert Sim([DummyDef()], [dict(name='f', hp=INF_HP, spd=100)], 1, {'turn_gauge': 'float'}).turn_gauge == 'float'


def test_shared_helpers():
    # 두 엔진이 같은 모듈의 식을 씀
    assert mc._gauge is gauge and engine._gauge is gauge
    assert gauge.int_gain(9999.99) == 9999
    assert gauge.turn_key(True, 0, 1, 0) < gauge.turn_key(False, 10000, 999, 9999)     # 추가 턴 먼저
    assert gauge.turn_key(False, 9000, 100, 0) < gauge.turn_key(False, 8999, 300, 9999)  # 게이지 높은 순
    assert gauge.turn_key(False, 9000, 101, 0) < gauge.turn_key(False, 9000, 100, 9999)  # 속도 높은 순


def test_order_matches_mc_client():
    # 정수 절삭 때문에 실수 게이지와 순서가 갈리는 꼴(속도 123·119·114 / 적 153): 클라 방식끼리는 같고, 옛 실수와는 다름
    spds, e = [123, 119, 114], 153
    want = _mc_order(spds, e, 'client')
    assert _ev_order(spds, e, 'client') == want
    assert _ev_order(spds, e, 'float') != want


def test_order_matches_mc_client_sweep():
    # 속도가 모두 다른 무작위 편성 60개: 첫 40행동 순서가 두 엔진에서 같음(우선순위 난수가 갈림에 안 끼는 꼴)
    rng = random.Random(3)
    for _ in range(60):
        spds = rng.sample(range(90, 160), 3)
        e = rng.choice([x for x in range(90, 160) if x not in spds])
        assert _ev_order(spds, e, 'client') == _mc_order(spds, e, 'client'), (spds, e)


def test_horizon_keeps_last_action():
    # 정수 절삭으로 1000틱 바로 뒤로 밀린 속도 100 유닛의 10번째 행동이 잘리지 않음(지평선 여유)
    o = dict(DEFAULT_OPTS, turn_gauge='client')
    sim = Sim([DummyDef(name='x', spd=132.5)] + [DummyDef(name='s%d' % i) for i in range(3)],
              [dict(name='f', hp=INF_HP, **{'def': 0}, spd=97.12)], 10, o).run()
    assert [p.actions for p in sim.party[1:]] == [10, 10, 10], [p.actions for p in sim.party]


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
