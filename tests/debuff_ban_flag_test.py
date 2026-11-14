# -*- coding: utf-8 -*-
"""새 약화 거부(CantGetMoreDebuff)를 이름이 아니라 표 플래그로 보는지 mc.debuff_ban_flag.
클라: 부여 검사(build 26610546 NKM.decompiled.cs 4394-4398)는 대상 버프의 CantGetMoreDebuff 플래그(BUFF_TEMPLET
m_bDebuffBan)로 거부한다. 옛 엔진(name)은 이름 〈면역〉만 봐서 길드 방어전 티엔 〈시엔 고유 버프(해제불가)〉
(약화효과 면역, BUFF_TEMPLET 300781)가 있어도 약화가 들어갔다.
실행: python -X utf8 -I tests/debuff_ban_flag_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim.starsavior.parser import Line                     # noqa: E402

SHIEN = '시엔 고유 버프(해제불가)'


def _apply(mode, guard):
    b = battle([unit('a')], [unit('f')], mc={'debuff_ban_flag': mode})
    a, f = b.allies[0], b.foes[0]
    if guard:
        give(f, guard, dur=10 ** 6)
    ctx = Ctx(a, a, a.d.skills['기본기'])
    ctx.target, ctx.targets = f, [f]
    b.run_line(a, Line('[스킬 사용 후] 스킬 대상에게 〈공격력 감소〉 (2턴 / 공격력% -20%)', '기본기', 'active'), ctx)
    return b, f


def test_default_table():
    assert MC_OPTS['debuff_ban_flag'] == 'table'


def test_shien_blocks_table():
    b, f = _apply('table', SHIEN)
    assert '공격력 감소' not in f.eff and b.rule_hits['debuff_ban_flag'] == 1


def test_shien_ignored_legacy():
    b, f = _apply('name', SHIEN)
    assert '공격력 감소' in f.eff


def test_plain_immune_and_none_both():
    for mode in ('table', 'name'):
        assert '공격력 감소' not in _apply(mode, '면역')[1].eff
        assert '공격력 감소' in _apply(mode, None)[1].eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
