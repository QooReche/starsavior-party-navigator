# -*- coding: utf-8 -*-
"""행동 게이지 증가 면역(억류) 보유자에게 게이지 증가가 막히는지 mc.gauge_up_immune.
클라: SpeedGaugeUp 버프는 대상이 ImmuneSpeedGaugeUp(BUFF_TEMPLET 〈억류(해제불가)〉 301144·〈들러리(해제불가)〉 300872)면
거부된다(build 26610546 NKM.decompiled.cs 4412-4416, 강제 적용 예외). 옛 엔진(off)은 들러리(zero_stats)만 막아
회랑 FLOOR 500/600 공허투영자가 건 억류를 받은 아군에게도 게이지 증가가 들어갔다.
실행: python -X utf8 -I tests/gauge_up_immune_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def _run(mode, held):
    b = battle([unit('a')], [unit('f')], mc={'gauge_up_immune': mode})
    a = b.allies[0]
    if held:
        give(a, '억류(해제불가)', harmful=True, dur=10 ** 6)
    a.gauge = 1000.0
    ctx = Ctx(a, a, a.d.skills['기본기'])
    ctx.target, ctx.targets = b.foes[0], [b.foes[0]]
    b.run_line(a, Line('[스킬 사용 후] 자신에게 행동 게이지 30%p 증가', '기본기', 'active'), ctx)
    return b, a


def test_default_client():
    assert MC_OPTS['gauge_up_immune'] == 'client'


def test_detained_blocked_client():
    b, a = _run('client', True)
    assert a.gauge == 1000.0 and b.rule_hits['gauge_up_immune'] == 1


def test_detained_applied_legacy():
    assert _run('off', True)[1].gauge == 4000.0


def test_free_unit_gains_both():
    for mode in ('client', 'off'):
        assert _run(mode, False)[1].gauge == 4000.0


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
