# -*- coding: utf-8 -*-
"""행동 게이지 공통 계산(turn_gauge=client). 몬테카를로 엔진(mc.Battle)과 기대값 엔진(engine.Sim)이 같은 식을 쓴다.

근거 = build 26610546 static-data decompiled/NKM/NKM.decompiled.cs
  12286-12370 OBF_21483(TurnSpeedCalculator): 누가 100% 이상이면 게이지를 안 올림, 정렬 키(CompareTo)
  12415-12431 정수 증가: 유닛마다 (int)(속도 x 틱)
  5113-5115 게이지는 (int) 변환 뒤 저장
  1962 유닛 우선순위 = 등장 때 RandomGenerator.Next(10000)
"""

READY = 10000


def any_ready(units):
    """누가 100% 이상이면 이번 진행에서 게이지를 올리지 않는다(NKM:12290-12317)."""
    return any(x.gauge >= READY for x in units)


def int_gain(acc):
    """쌓인 실수 증가분(속도 x 틱)을 클라처럼 정수로 절삭(NKM:12415-12431)."""
    return int(acc)


def turn_key(extra_turn, gauge, spd, prio):
    """정렬 키(NKM:12332-12364 CompareTo) — 작은 쪽이 먼저 행동. 추가 턴 먼저, 게이지 높은 순, 속도 높은 순,
    유닛 우선순위 높은 순. 확정 턴(NextTurnCatch) 항은 엔진 콘텐츠에 없어 뺀다."""
    return (not extra_turn, -gauge, -spd, -prio)
