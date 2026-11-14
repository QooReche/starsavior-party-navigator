# -*- coding: utf-8 -*-
"""적에게 거는 행동 게이지 감소·스킬 쿨타임 증가도 회피·면역에 막히는지 mc.gauge_cd_immune.
클라: 둘 다 비양성·비강제 버프(BUFF_TEMPLET 2502, 2504-2506)라 공통 부여 검사(build 26610546 NKM.decompiled.cs
4323-4327 회피 거부, 4364-4377 효과 적중, 4394-4398 CantGetMoreDebuff)를 거친다.
옛 엔진(off)은 면역 중이거나 공격을 회피해도 게이지가 깎이고 쿨타임이 늘었다.
실행: python -X utf8 -I tests/gauge_cd_immune_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402

GAUGE = '[스킬 사용 후] 스킬 대상에게 행동 게이지 20%p 감소 {효과 적중 판정}'
CD = '[스킬 사용 후] 스킬 대상에게 스킬 쿨타임 1턴 증가'


def _run(mode, text, immune=False, evaded=False):
    b = battle([unit('a', skills=[dict(slot='기본기', dm=100), dict(slot='특수기', dm=100, cd=3)])], [unit('f')],
               mc={'gauge_cd_immune': mode})
    a, f = b.allies[0], b.foes[0]
    b.roll_hit = lambda *args: True
    if immune:
        give(a, '면역', dur=3)
    a.gauge = 5000.0
    a.cd = {slot: 0 for slot in a.d.skills}
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = a, [a]
    if evaded:
        ctx.evaded.add(a)
    b.run_line(f, Line(text, '기본기', 'active'), ctx)
    return b, a


def test_default_client():
    assert MC_OPTS['gauge_cd_immune'] == 'client'


def test_gauge_blocked_client():
    for kw in (dict(immune=True), dict(evaded=True)):
        b, a = _run('client', GAUGE, **kw)
        assert a.gauge == 5000.0, kw
        assert b.rule_hits['gauge_cd_immune'] == 1


def test_gauge_applied_legacy_and_plain():
    for kw in (dict(immune=True), dict(evaded=True)):
        assert _run('off', GAUGE, **kw)[1].gauge == 3000.0
    assert _run('client', GAUGE)[1].gauge == 3000.0


def test_cd_blocked_client():
    for kw in (dict(immune=True), dict(evaded=True)):
        _, a = _run('client', CD, **kw)
        assert all(v == 0 for v in a.cd.values()), kw
        _, a = _run('off', CD, **kw)
        assert any(v > 0 for v in a.cd.values()), kw


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
