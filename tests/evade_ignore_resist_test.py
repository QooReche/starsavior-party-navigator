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


def _side(mode='client', sel=None, sel_target='a', hit_evaded=True, in_ctx=False, hit=False, tg_src='적 단일'):
    """줄 주인(f2)이 지금 시전자(f)가 아닌 경우 — 다른 아군의 «아군 공격 후» 줄·피격 반응 등. 클라는 그 유닛이 마지막으로 고른
    스킬(OBF_5963)·대상(OBF_35462)과 x 의 마지막 피격 결과(OBF_20548)로 판정(NKM:4542·4559·4564)."""
    b = battle([unit('a'), unit('a2')], [unit('f'), unit('f2', skills=[dict(slot='기본기', dm=100), dict(slot='궁극기', dm=100, all=True),
                                                                         dict(slot='특수기', dm=0, tg='자신')])],
               mc={'evade_ignore_resist': mode})
    a, f, f2 = b.allies[0], b.foes[0], b.foes[1]
    sk = {'single': f2.d.skills['기본기'], 'all': f2.d.skills['궁극기'], 'self': f2.d.skills['특수기'], None: None}[sel]
    f2.sel_skill, f2.sel_target = sk, {'a': a, 'a2': b.allies[1]}[sel_target]
    a.hit_evaded = hit_evaded
    ctx = Ctx(f2, f, f.d.skills['기본기'])
    ctx.target, ctx.targets = a, [a]
    if in_ctx:
        ctx.evaded.add(a)
    if hit:
        ctx.hit_targets.append(a)
    b._cur_line = Line('[스킬 사용 후] (조건: 아군 공격 후) 스킬 대상에게 〈출혈〉 (2턴)', '기본기', 'active')
    eff = dict(kind='buff', target='', name='출혈', chance=1.0, dur=2, props={}, max=None, times=1, judge=False,
               ignore_resist=True, dot=('atk', 0.1))
    b.add_effect(f2, a, eff, ctx)
    return '출혈' not in a.eff


def test_side_owner_never_selected_no_block():
    assert not _side(sel=None, in_ctx=True)                        # OBF_5963 null → 거부 없음(4542)


def test_side_owner_single_target_rule():
    assert _side(sel='single', sel_target='a')                       # 고른 대상 = x, x 마지막 피격 회피(4559)
    assert not _side(sel='single', sel_target='a2')                  # 고른 대상이 다르면 거부 없음
    assert not _side(sel='single', sel_target='a', hit_evaded=False)


def test_side_owner_all_and_self_skill():
    assert _side(sel='all', sel_target='a2')                         # 적 전체 스킬: x 마지막 피격 회피면 거부(4564)
    assert not _side(sel='self')                                     # 자신 대상 스킬: 거부 없음
    assert not _side(sel='all', mode='off')                          # legacy 는 저항 대상 약화·ctx.evaded 만


def test_this_cast_result_overrides_stale():
    assert not _side(sel='all', hit=True, hit_evaded=True)           # 이번 시전에 맞았고 회피 안 했으면 옛 회피 기록 무시
    assert _side(sel='all', hit=True, in_ctx=True, hit_evaded=False)


def test_strike_records_last_hit_result():
    b = battle([unit('a')], [unit('f')])
    a, f = b.allies[0], b.foes[0]
    a.hit_evaded = True
    b.cast(f, f.d.skills['기본기'], target=a)                        # 회피 0 → 명중
    assert a.hit_evaded is False and f.sel_skill is f.d.skills['기본기'] and f.sel_target is a


def test_damage_end_line_not_blocked():
    """«피해 처리 후» = NSEAT_DAMAGE_END(레이시 SE 10494016 등) — 회피 거부 시점(HIT·SKILL_END, NKM:4546)이 아님.
    레이시 기본기를 회피했던 적이 레이시를 때릴 때 피격 반응 〈뒤엉킨 꿈결〉이 붙어야 함(codex 재현)."""
    b = battle([unit('a')], [unit('f')], mc={'evade_ignore_resist': 'client'})
    a, f = b.allies[0], b.foes[0]
    f.sel_skill, f.sel_target = f.d.skills['기본기'], a       # 반응 주인(f)이 전에 a 를 고름
    a.hit_evaded = True                                       # a 는 f 의 공격을 회피했었음
    ctx = Ctx(f, a, a.d.skills['기본기'])                      # a 가 f 를 공격하는 중(피격 반응)
    ctx.target, ctx.targets = f, [f]
    for phase, blocked in (('피해 처리 후', False), ('피해 처리 직전', False), ('피격 시', True)):
        b._cur_line = Line('[%s] (조건: 내가 피격될 때) 대상에게 〈뒤엉킨 꿈결〉 (2턴)' % phase, '기본기', 'active')
        a.eff.pop('뒤엉킨 꿈결', None)
        b.add_effect(f, a, dict(kind='buff', target='', name='뒤엉킨 꿈결', chance=1.0, dur=2, props={}, max=None, times=1,
                                judge=False, ignore_resist=True), ctx)
        assert ('뒤엉킨 꿈결' not in a.eff) is blocked, phase


def test_skill_start_resets_hit_result():
    """스킬 시작마다 전원 피격 결과 = Evade(NKM:15621-15623 → 2003), 대상은 판정값으로 덮음 — 대상이 아니었던 적도 «회피»."""
    b = battle([unit('a'), unit('a2')], [unit('f')])
    a, a2, f = b.allies[0], b.allies[1], b.foes[0]
    b.cast(f, f.d.skills['기본기'], target=a)
    assert a.hit_evaded is False and a2.hit_evaded is True


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
