# -*- coding: utf-8 -*-
"""회피한 적에게는 효과 저항 무시 약화도 안 걸리는지 mc.evade_ignore_resist.
클라 build 26610546 NKM:4323-4327·4540-4566: 회피 거부(OBF_13659)는 저항 판정과 별개 — 상대 진영·HIT/SKILL_END·적 대상·비강제면 거부.
엔진은 저항 대상 약화만 막아, 코스모 카넬리아 기본기를 회피해도 〈출혈〉(SE 9401001, BI_BLEEDING 비강제)이 붙었다.
실행: python -X utf8 -I tests/evade_ignore_resist_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit                                  # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402


def _apply(mode, name, evaded=True, **extra):
    b = battle([unit('a')], [unit('f')], mc={'evade_ignore_resist': mode})
    a, f = b.allies[0], b.foes[0]
    ctx = Ctx(f, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = a, [a]
    if evaded:
        ctx.evaded.add(a)
    eff = dict(kind='buff', target='', name=name, chance=1.0, dur=2, props={}, max=None, times=1, judge=False,
               ignore_resist=True, **extra)
    b.add_effect(f, a, eff, ctx)
    return b, a


def test_default_client():
    assert MC_OPTS['evade_ignore_resist'] == 'client'


def test_evaded_blocks_ignore_resist_client():
    b, a = _apply('client', '출혈', dot=('atk', 0.1))
    assert '출혈' not in a.eff and b.rule_hits['evade_ignore_resist'] == 1
    _, a = _apply('client', '출혈', evaded=False, dot=('atk', 0.1))
    assert '출혈' in a.eff                                       # 회피 안 했으면 그대로 걸림


def test_evaded_passes_legacy():
    _, a = _apply('off', '출혈', dot=('atk', 0.1))
    assert '출혈' in a.eff


def test_forced_buff_still_passes():
    _, a = _apply('client', '잔멸의 가시', dot=('atk', 0.1))     # BUFF 301131 ForceApplyEffect(se_force_apply)
    assert '잔멸의 가시' in a.eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
