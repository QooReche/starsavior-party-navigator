# -*- coding: utf-8 -*-
"""지속 표기 없는 효과(클라 수명 0)를 매 스킬 끝에 정리하는 기본값 mc.check_buff_scope=all·check_buff_expiry=skill.
클라: 스킬 끝마다(OBF_4932, build 26610546 NKM.decompiled.cs 16017-16024) 같은 전역 턴에 생긴 수명<=0 버프를 전원에게서
지운다(OBF_10623 4047-4053). 수명은 SE m_BuffLifeTurn(0 = 지속 표기 없음), 버프가 TurnInfinite 면 무한.
11/14 전수 대조: 엔진 dur=None 이름 32 = 클라 수명 0 일치 22 + TurnInfinite 2(나태·헥사 너트, «타격 후 해제») + 즉시 처리 5
+ 미실행 2 + 능력치 보정 1. TurnInfinite 는 data/buff_flags.json turn_infinite 로 정리 대상에서 뺀다.
옛 기본(name/action)은 이름에 확인용·체크용이 든 효과만 행동 끝에 정리하고 나머지(예: 〈귀족의 품격〉)는 영구히 남겼다.
실행: python -X utf8 -I tests/life0_cleanup_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit                                  # noqa: E402
from battlesim import mc as M                                    # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS, MC_RULES                    # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def _give(mc, text):
    b = battle([unit('a')], [unit('f')], mc=mc)
    a = b.allies[0]
    ctx = Ctx(a, a, a.d.skills['기본기'])
    ctx.target, ctx.targets = b.foes[0], [b.foes[0]]
    b.run_line(a, Line('[스킬 사용 후] ' + text, '기본기', 'active'), ctx)
    return b, a


def test_defaults_client():
    assert (MC_OPTS['check_buff_scope'], MC_OPTS['check_buff_expiry']) == ('all', 'skill')
    assert (MC_RULES['check_buff_scope']['legacy'], MC_RULES['check_buff_expiry']['legacy']) == ('name', 'action')


def test_life0_effect_cleared_at_skill_end_default():
    b, a = _give({}, '자신에게 〈귀족의 품격〉')
    assert '귀족의 품격' in a.eff and a.eff['귀족의 품격'].check
    b._expire_checks(skill=True)
    assert '귀족의 품격' not in a.eff


def test_life0_effect_kept_legacy():
    b, a = _give({'check_buff_scope': 'name', 'check_buff_expiry': 'action'}, '자신에게 〈귀족의 품격〉')
    assert not a.eff['귀족의 품격'].check
    b._expire_checks(skill=True)
    assert '귀족의 품격' in a.eff


def test_turn_infinite_not_cleared():
    assert {'나태', '헥사 너트'} <= set(M.buff_flags()['turn_infinite'])
    b, a = _give({}, '자신에게 〈나태〉 (타격 후 해제 / 피해 증가 -30%, 피해 감소 -30%)')
    assert not a.eff['나태'].check
    b._expire_checks(skill=True)
    assert '나태' in a.eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
