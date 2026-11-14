# -*- coding: utf-8 -*-
"""공격 시 해제(DC_ATTACK) 대상이 표의 이름 전부인지 mc.dispel_attack_names.
클라: 공격 스킬(SAT_ATTACK) 끝에 시전자의 DispelCondition=DC_ATTACK 버프를 전부 지운다(OBF_20893,
build 26610546 NKM.decompiled.cs 4084-4097, 15719-15722). 옛 엔진(two)은 여유로운 응수·헥사 너트만 지워
길드 방어전 심해의 폭군 〈나태〉(피해 증가·감소 -30%, BUFF_TEMPLET 300932 DC_ATTACK)가 무한 유지됐다.
실행: python -X utf8 -I tests/dispel_attack_names_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit                            # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402
from battlesim import mc as M                                    # noqa: E402


def _attack(mode, name):
    b = battle([unit('a')], [unit('f')], mc={'dispel_attack_names': mode, 'dispel_on_attack': 'on'})
    a, f = b.allies[0], b.foes[0]
    give(a, name, {'피해 증가': -30.0}, dur=10 ** 6)
    hp = f.hp
    b.cast(a, a.d.skills['기본기'], target=f)
    assert f.hp < hp
    return b, a


def test_default_table():
    assert MC_OPTS['dispel_attack_names'] == 'table'
    assert '나태' in M.buff_flags()['dispel_attack']


def test_sloth_removed_table():
    b, a = _attack('table', '나태')
    assert '나태' not in a.eff and b.rule_hits['dispel_attack_names'] == 1


def test_sloth_kept_legacy():
    b, a = _attack('two', '나태')
    assert '나태' in a.eff


def test_confirmed_names_both():
    for mode in ('table', 'two'):
        for name in M.DISPEL_ON_ATTACK:
            _, a = _attack(mode, name)
            assert name not in a.eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
