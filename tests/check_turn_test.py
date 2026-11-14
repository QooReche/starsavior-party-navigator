# -*- coding: utf-8 -*-
"""수명 0 효과 정리의 «같은 전역 턴 생성분만» 조건(check_buff_expiry=skill).
클라 build 26610546 NKM.decompiled.cs:4047-4053 OBF_10623: buff.OBF_10523(생성 전역 턴) == 지금 전역 턴 && 수명 <= 0 인 버프만 지움.
스킬 끝(OBF_4932 16017-16024)·행동 끝(OBF_14573 13990-13994) 둘 다 이 함수. 다른 턴에 생긴 수명 0 버프(전투·웨이브 시작처럼 턴
사이에 부여)는 행동 끝 차감(OBF_29028 3999-4014, 생성 턴이 다르면 차감)에서 사라짐 — 턴 유닛은 전부(OBF_2849), 나머지 유닛은
전체 턴 시계 버프만(OBF_16373 → OBF_8763). 옛 엔진은 생성 턴을 안 보고 check_pending 을 전부 지웠다.
실행: python -X utf8 -I tests/check_turn_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit                                  # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402


def _give(mc, turn, text='자신에게 〈귀족의 품격〉'):
    b = battle([unit('a'), unit('a2')], [unit('f')], mc=mc)
    a = b.allies[0]
    b.global_turns = turn
    ctx = Ctx(a, a, a.d.skills['기본기'])
    ctx.target, ctx.targets = b.foes[0], [b.foes[0]]
    b.run_line(a, Line('[스킬 사용 후] ' + text, '기본기', 'active'), ctx)
    return b, a


def test_same_turn_cleared():
    b, a = _give({}, 3)
    assert a.eff['귀족의 품격'].check and a.eff['귀족의 품격'].check_turn == 3
    b._expire_checks(skill=True)
    assert '귀족의 품격' not in a.eff and b.rule_hits['check_turn_keep'] == 0


def test_other_turn_kept_at_skill_end():
    b, a = _give({}, 3)
    b.global_turns = 4
    b._expire_checks(skill=True)                                  # 다른 턴 생성분 — 스킬 끝 정리 대상 아님
    assert '귀족의 품격' in a.eff and b.rule_hits['check_turn_keep'] == 1
    b._expire_checks(actor=b.allies[1])                           # 남의 행동 끝: 주인 시계 버프는 차감 안 됨
    assert '귀족의 품격' in a.eff
    b._expire_checks(actor=a)                                     # 자기 행동 끝 차감(OBF_2849)으로 사라짐
    assert '귀족의 품격' not in a.eff and not b.check_pending


def test_other_turn_global_clock_cleared_any_action_end():
    b, a = _give({}, 3)
    a.eff['귀족의 품격'].clock = 'global'                         # 전체 턴 시계(OBF_10355) 버프는 남의 행동 끝에도 차감
    b.global_turns = 4
    b._expire_checks(actor=b.allies[1])
    assert '귀족의 품격' not in a.eff


def test_reapply_renews_turn():
    b, a = _give({}, 3)
    b.global_turns = 5
    ctx = Ctx(a, a, a.d.skills['기본기'])
    b.run_line(a, Line('[스킬 사용 후] 자신에게 〈귀족의 품격〉', '기본기', 'active'), ctx)
    assert a.eff['귀족의 품격'].check_turn == 5                    # 재부여 = 새 버프 객체(NKM:4419)
    b._expire_checks(skill=True)
    assert '귀족의 품격' not in a.eff


def test_legacy_action_ignores_turn():
    b, a = _give({'check_buff_expiry': 'action'}, 3)
    b.global_turns = 4
    b._expire_checks()
    assert '귀족의 품격' not in a.eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
