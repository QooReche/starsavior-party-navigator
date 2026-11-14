# -*- coding: utf-8 -*-
"""단계 그룹 «다음 차감 1회 건너뜀»(클라 OBF_6935)은 행동이 끝날 때마다 모든 유닛에서 비워진다.
build 26610546 NKM.decompiled.cs 13961-13969(턴 유닛 OBF_2849, 나머지 OBF_16373), 13637-13643, 3999-4014(OBF_29028 끝 OBF_6935.Clear()).
옛 엔진은 남의 행동 중에 붙은 건너뜀을 그 유닛의 다음 자기 턴·웨이브 전환까지 들고 있었다.
실행: python -X utf8 -I tests/skip_tick_clear_test.py"""
import os
import sys
from types import SimpleNamespace as NS

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from battlesim.mc import Battle, Eff                             # noqa: E402


def _unit(side, skip):
    e = Eff('공격력 증가', {'atkp': 0.2}, 1, 2, None, False)
    e.skip_tick = skip
    return NS(side=side, dead=False, acting=False, extra_turn=False, eff={e.name: e})


def test_finish_action_clears_all_skip():
    actor, ally, foe = _unit(0, True), _unit(0, True), _unit(1, True)
    actor.acting = True
    units = {0: [actor, ally], 1: [foe]}
    b = NS(mc={'any_turn_clock': False}, alive=lambda side: units[side], _expire_checks=lambda actor=None: None,
           _forced_coop_candidates=set())
    Battle._finish_action(b, actor)
    for u in (actor, ally, foe):
        assert u.eff['공격력 증가'].skip_tick is False
        assert u.eff['공격력 증가'].dur == 2          # 지우기만 하고 지속은 안 깎음
    assert actor.acting is False


if __name__ == '__main__':
    test_finish_action_clears_all_skip()
    print('ok 1')
