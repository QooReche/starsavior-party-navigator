# -*- coding: utf-8 -*-
"""피해식 클라 대조 3건(2026-11-14, build 26610546):
- stat_floor: 최종 공격력·방어력은 3단(버프)까지 곱한 뒤 Math.Floor 한 정수(NKM:18892-18897).
- chain_round: 일반 연쇄 피해 값은 (int)((능력치 x 계수 + 그 x 증가합) x 1.85) 로 먼저 정수화(NKM:6212-6236) 뒤 방어·난수.
- chain_guard: 연쇄 피해도 수호 분담(NKM:8150-8191·17799-17803), 대상이 스킬 무효·무적이면 분담 없음.
실행: python -X utf8 -I tests/dmg_terms_1114_test.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit, give                            # noqa: E402
from battlesim.mc import Ctx                                     # noqa: E402
from battlesim.rules import MC_OPTS                              # noqa: E402


def test_defaults_client():
    assert MC_OPTS['stat_floor'] == 'client'
    assert MC_OPTS['chain_round'] == 'client'
    assert MC_OPTS['chain_guard'] == 'client'


def _atk_def(mode):
    b = battle([unit('a', atk=1000, df=1000)], [unit('f')], mc={'stat_floor': mode})
    a = b.allies[0]
    give(a, '버프', {'공격력%': 0.05, '방어력%': 0.07})        # 1000 x 1.0005 / 1000 x 1.0007
    return b, b.atk_stat(a), b.def_stat(a)


def test_stat_floor_client():
    b, atk, df = _atk_def('client')
    assert (atk, df) == (1000.0, 1000.0), (atk, df)
    assert b.rule_hits.get('stat_floor', 0) == 0                  # 판정용 카운터 없음(값으로 확인)


def test_stat_floor_float():
    _, atk, df = _atk_def('float')
    assert abs(atk - 1000.5) < 1e-6 and abs(df - 1000.7) < 1e-6, (atk, df)


def _chain(mc, guard=False, nullify=False, coef=0.3337):
    """적 f(공격력 1000)가 아군 a(방어 1000)에게 연쇄 피해 공격력 x coef. 난수·팀 배율 1."""
    b = battle([unit('a', df=1000), unit('g', df=3000)], [unit('f', atk=1000)], mc=dict(mc))
    a, g, f = b.allies[0], b.allies[1], b.foes[0]
    if guard:
        give(g, '수호', {'피해 분담(수호)': 50})
    if nullify:
        give(a, '스킬 피해 무효', {})
    ctx = Ctx(f, a, a.d.skills['기본기'])     # 피격 반응(줄 주인 f, 공격자 a) → 대상 'attacker' = a
    ctx.target, ctx.targets = f, [f]
    eff = dict(stat='atk', coef=coef, target='attacker')
    ta, tg = a.taken, g.taken
    b.chain(f, eff, ctx)
    return b, a.taken - ta, g.taken - tg


def test_chain_round_client():
    # 1000 x 0.3337 x 1.85 = 617.345 → int 617, 방어율 0.25 → 462.75 → 462
    b, da, _ = _chain({'chain_round': 'client', 'chain_guard': 'off'})
    assert da == 462, da
    assert b.rule_hits['chain_round'] == 1


def test_chain_round_float():
    _, da, _ = _chain({'chain_round': 'float', 'chain_guard': 'off'})
    assert da == 463, da                     # 617.345 x 0.75 = 463.008


def test_chain_guard_client():
    # 617 중 50% = 308.5 를 수호자가: 대상 308.5 x 0.75 = 231, 수호자(방어 3000, 방어율 0.5) 308.5 x 0.5 = 154
    b, da, dg = _chain({'chain_round': 'client', 'chain_guard': 'client'}, guard=True)
    assert (da, dg) == (231, 154), (da, dg)
    assert b.rule_hits['chain_guard'] == 1


def test_chain_guard_off():
    _, da, dg = _chain({'chain_round': 'client', 'chain_guard': 'off'}, guard=True)
    assert (da, dg) == (462, 0), (da, dg)


def test_chain_guard_skips_nullified_target():
    b, da, dg = _chain({'chain_round': 'client', 'chain_guard': 'client'}, guard=True, nullify=True)
    assert dg == 0 and b.rule_hits.get('chain_guard', 0) == 0, (da, dg)


def test_stat_floor_client_order_no_epsilon():
    # 클라: Floor(100 + 100 x (-5600 x 0.0001)) = Floor(43.99999999999999) = 43 (오차 보정 없음, codex 재검토)
    b = battle([unit('a', atk=100, df=100)], [unit('f')], mc={'stat_floor': 'client'})
    a = b.allies[0]
    give(a, '약화', {'공격력%': -56, '방어력%': -56})
    assert (b.atk_stat(a), b.def_stat(a)) == (43.0, 43.0), (b.atk_stat(a), b.def_stat(a))


def test_stat_floor_def_coef_skill():
    # 방어 계수 스킬의 방어력 항도 정수 최종 방어력
    b = battle([unit('a', df=1000)], [unit('f')], mc={'stat_floor': 'client'})
    a = b.allies[0]
    give(a, '버프', {'방어력%': 0.07})
    assert b.def_stat(a) == 1000.0


def _tie(mode):
    """아군 4칸(엔진 칸 0·1 전열, 2·3 후열) 중 칸 1(전열)·칸 2(후열)·칸 3(후열)이 같은 분담 비율. 대상 = 칸 0."""
    b = battle([unit('t'), unit('f2'), unit('b1'), unit('b2')], [unit('foe', atk=1000)],
               mc={'guard_tie': mode, 'chain_guard': 'client', 'chain_round': 'client'})
    t, f2, b1, b2 = b.allies
    for w in (b2, b1, f2):
        give(w, '수호', {'피해 분담(수호)': 30})
    # 먼저 보는 순서를 후열 b2 가 앞에 오게 섞음
    b.allies[:] = [t, b2, b1, f2]
    return b, b._chain_guard(t, 1000.0)[0], (t, f2, b1, b2)


def test_guard_tie_client_prefers_front():
    b, g, (t, f2, b1, b2) = _tie('client')
    assert g is f2, g.name
    assert b.rule_hits['guard_tie'] >= 1


def test_guard_tie_first():
    _, g, (t, f2, b1, b2) = _tie('first')
    assert g is b2, g.name


def test_guard_tie_both_back_keeps_first():
    b = battle([unit('t'), unit('f2'), unit('b1'), unit('b2')], [unit('foe')], mc={'guard_tie': 'client', 'chain_guard': 'client'})
    t, f2, b1, b2 = b.allies
    for w in (b1, b2):
        give(w, '수호', {'피해 분담(수호)': 30})
    b.allies[:] = [t, b2, b1, f2]
    assert b._chain_guard(t, 1000.0)[0] is b2


if __name__ == '__main__':
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith('test_') and callable(fn):
            fn(); n += 1
    print('ok', n)
