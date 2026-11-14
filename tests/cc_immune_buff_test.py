# -*- coding: utf-8 -*-
"""〈기절 면역〉 등 상태이상 면역 버프가 해당 효과를 막는지 mc.cc_immune_buff.
클라: 부여 검사(build 26610546 NKM.decompiled.cs 4407-4411)는 Stun/Sleep/Silence/Aggro 버프를 각각
ImmuneStun/ImmuneSleep/ImmuneSilence/ImmuneAggro 보유자에게서 거부한다(강제 적용 예외). 옛 엔진(off)은 무시.
현재 엔진 데이터에 면역 버프를 거는 줄이 없어 실전 발생 0(우선순위 낮음).
실행: python -X utf8 -I tests/cc_immune_buff_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def _run(mode, guard, effect='기절'):
    b = battle([unit('a')], [unit('f')], mc={'cc_immune_buff': mode})
    a, f = b.allies[0], b.foes[0]
    b.roll_hit = lambda *args: True
    if guard:
        give(f, guard, dur=3)
    ctx = Ctx(a, a, a.d.skills['기본기'])
    ctx.target, ctx.targets = f, [f]
    b.run_line(a, Line('[스킬 사용 후] 스킬 대상에게 〈%s〉 (1턴) {효과 적중 판정}' % effect, '기본기', 'active'), ctx)
    return b, f


def test_default_client():
    assert MC_OPTS['cc_immune_buff'] == 'client'


def test_stun_immune_blocks_client():
    b, f = _run('client', '기절 면역')
    assert '기절' not in f.eff and b.rule_hits['cc_immune_buff'] == 1


def test_stun_immune_ignored_legacy():
    assert '기절' in _run('off', '기절 면역')[1].eff


def test_other_immune_does_not_block():
    assert '기절' in _run('client', '수면 면역')[1].eff
    assert '수면' not in _run('client', '수면 면역', '수면')[1].eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
