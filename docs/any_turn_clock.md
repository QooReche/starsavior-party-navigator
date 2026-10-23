# 「누군가 턴 종료 시 턴 수 차감」 효과 (mc.any_turn_clock)

## 문제
엔진은 모든 효과를 효과 주인이 행동을 끝낼 때만 차감했음(`Eff.clock='owner_turn'`). 37-36 보스 공허조율자 궁극기가 거는 「불협화음(해제불가)」(속도 -100%, 3턴)은 걸린 샤를이 행동하지 못해 영원히 풀리지 않았고, 시뮬에서 샤를 행동이 0회였음(실측 3회).

## 근거
- 클라 표 `BUFF_TEMPLET.GlobalTurnCounting` (942개 중 true 19개). 설명 문구가 있는 10개는 모두 「누군가 턴 종료 시 턴 수가 차감됩니다」.
- 해당 상태 이름(foe.js 용어 7종): 불협화음(해제불가), 몰락한 사념(해제불가), 타임 패러독스, 철혈의 비늘갑, 혼의 균열(해제불가), 메이드의 블로킹(해제불가), 강인도 피해 무효.
- 지속 기준 필드는 이것뿐(DurationType 류 없음). 분류표는 작업 메모 `clock_survey.md`.

## 동작
- 규칙 `mc.any_turn_clock` (기본 **true**, legacy/alt false, grade data). false 면 옛 동작(전부 owner_turn).
- 효과 설명(`foe.gloss()` / 유닛 `effect_info`)에 위 문구가 있는 이름이 걸리면 `Eff.clock='any_turn'`. 적은 자신의 스킬 용어를 우선하며 일반형도 `owner_turn`을 명시한다(집행자 길레·올베로스의 동명 「강인도 피해 무효」 구분).
- `Battle.act`의 공통 종료 경로 `_finish_action()`에서 `_tick_any_turn()`: 행동한 유닛과 무관하게 양 진영 생존 유닛의 any_turn 효과 지속 -1. NKM 3723·4240의 GlobalTurnCounting 예외대로 부여 행동도 차감하며 `fresh`로 건너뛰지 않는다. 지속 피해로 행동자가 사망해도 동일하게 처리한다.
- 브레이크 영역의 `global` 시계는 기존대로 `run()`의 `_tick_break_domain()`에서 한 번 차감한다. `any_turn` 차감 대상에 포함하지 않는다.
- 속도 감소 등 일반 약화는 GlobalTurnCounting=false 이므로 owner_turn 유지.

## 미반영
GlobalTurnCounting=true 이지만 설명 문구가 없는 9개(체크·표식·피격 카운터, 면역(영역 전개) 4102, 규제)는 엔진이 지속 턴으로 모델링하지 않아 손대지 않음.

## 시험
`tests/any_turn_clock_test.py`.
