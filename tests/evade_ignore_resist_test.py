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
from battlesim.starsavior.parser import Line                     # noqa: E402


def _apply(mode, name, evaded=True, phase=None, ally=False, ignore_resist=True, **extra):
    b = battle([unit('a'), unit('a2')], [unit('f')], mc={'evade_ignore_resist': mode})
    a, f = b.allies[0], b.foes[0]
    owner = b.allies[1] if ally else f
    ctx = Ctx(owner, owner, owner.d.skills['기본기'])
    ctx.target, ctx.targets = a, [a]
    if evaded:
        ctx.evaded.add(a)
    eff = dict(dict(kind='buff', target='', name=name, chance=1.0, dur=2, props={}, max=None, times=1, judge=False,
                    ignore_resist=ignore_resist), **extra)
    if phase is not None:
        b._cur_line = Line('[%s] 스킬 대상에게 〈%s〉 (2턴)' % (phase, name), '기본기', 'active')
    b.add_effect(owner, a, eff, ctx)
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



def test_skill_end_line_blocked():
    b, a = _apply('client', '출혈', phase='스킬 사용 후', dot=('atk', 0.1))   # NSEAT_SKILL_END
    assert '출혈' not in a.eff and b.rule_hits['evade_ignore_resist'] == 1


def test_skill_start_line_not_blocked():
    # NKM:4546 — HIT·SKILL_END 가 아닌 시점(SKILL_START)의 효과는 회피 거부 대상이 아님(저항 대상 약화도)
    _, a = _apply('client', '출혈', phase='스킬 사용 시작 시', dot=('atk', 0.1))
    assert '출혈' in a.eff
    _, a = _apply('client', '공격력 감소', phase='스킬 사용 시작 시', ignore_resist=False,
                  props={'공격력%': -30})
    assert '공격력 감소' in a.eff
    _, a = _apply('client', '출혈', phase='턴 시작 시', dot=('atk', 0.1))
    assert '출혈' in a.eff
    _, a = _apply('off', '공격력 감소', phase='스킬 사용 시작 시', ignore_resist=False, props={'공격력%': -30})
    assert '공격력 감소' not in a.eff                              # legacy: 시점 구분 없이 저항 대상 약화 거부


def test_ally_target_not_blocked():
    # NKM:4542 — 같은 편 대상은 회피 거부 없음(대상 종류도 아군 계열)
    _, a = _apply('client', '공격력 증가', ally=True, phase='스킬 사용 후', props={'공격력%': 30})
    assert '공격력 증가' in a.eff


def test_marker_on_enemy_blocked():
    # 클라 회피 거부는 강화/약화를 가리지 않음 — 적에게 거는 체크용 표식도 회피하면 안 붙음
    b, a = _apply('client', '피격 체크용 버프', phase='스킬 사용 후')
    assert '피격 체크용 버프' not in a.eff and b.rule_hits['evade_ignore_resist'] == 1
    _, a = _apply('off', '피격 체크용 버프', phase='스킬 사용 후')
    assert '피격 체크용 버프' in a.eff


def test_forced_marker_passes():
    _, a = _apply('client', '잔멸의 가시', phase='스킬 사용 후', ignore_resist=False, dot=('atk', 0.1))
    assert '잔멸의 가시' in a.eff


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
