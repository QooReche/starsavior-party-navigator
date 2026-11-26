# 탐색 진행 계약 (P1)

## 계획

`SearchExecutor.planStages`는 실행하지 않고 단계 설명만 정규화함.
`{id, name, step, jobs, done, runs, chunk, kind, p, upper, teams, games}`를 반환함.

- `jobs`는 작업 수, `runs`는 작업당 판 수, `games=jobs*runs`임.
- `teams`는 코스모 호환 별칭, `step`은 일반 추천의 표시 단계 이름임.
- `upper=true`는 작업 수가 상한임. 조건부 단계는 `condition`과 발생 확률 `p`를 둠. 확률을 모르면 상한 기준 `p=1`로 안내하고, 발생하지 않는 것이 확정이면 `p=0`임.
- `done/chunk/kind/p`는 기존 `RecoPlan` 입력과 호환함. ETA 모형은 바꾸지 않았음. 코스모의 기존 `plan().stages`도 변환 가능하나 실제 연결·동적 난이도 계획은 P2 범위임.
- 길드 기본 탐색은 `GuildPlanner.plan`에서 시작 전 계획을 내보내고, `onPhase`의 `{stage,jobs,teams,runs,games}`에서 실제 수를 전달함. 후보·승격·시드·판 수·순서에는 관여하지 않음. 설정은 `data/guild_defaults.json`이 정본이며 `guild_defense.json`은 생성 사본임.

## 실행·표시

`runPhase`는 기존 `simWatch`와 같은 작업자별 감시를 사용함. 준비 전/후 상한은 호출자가 전달하며 가려진 탭·5초 넘게 늦은 타이머에서는 시계를 다시 잼. 응답 id가 다른 것은 버리고, 계산 응답의 id 누락·요청 밖 키·초과 응답·결과 누락 후 완료는 오류로 처리함. 요청 목록에 중복 키가 있으면 요청한 횟수만큼 받음.

길드 ETA는 `SearchExecutor.etaNew`, 막대·문구 갱신은 일반 추천의 `UiShared.planHtml/planPaint`, 표시 빈도 제한은 공통 `throttle`을 사용함. 그웬 소유자는 `guildSearch`를 유지함. 단계 수는 작업이 있는 단계만 세며 완료 전 막대는 99% 이하임.

기기 속도는 기존 LS 접두사 아래 `guild.speed.v1={sec:[단계별 초/판],workers}`에 저장함. 시즌·계정·자료 버전은 키에 넣지 않으며 작업자 수 변화만 환산함. 육성 가정 실행은 이 저장값을 덮어쓰지 않음.

## 결과·취소

기존 `rows/dropped/pool/combos/finalists/runs` 값은 완주 시 그대로임. 추가 메타는 다음과 같음.

- `partial`: 지금까지 결과로 멈췄는지 여부.
- `coverage={version:1,selectedStage,stages}`: 선택 결과의 평가 단계와 실행한 단계별 `{stage,name,jobs,done,runs,seed,complete}`. 단계 번호는 1부터, 아직 적격 결과가 없으면 선택 단계는 0임.
- 부분 결과의 각 행은 `evaluation={partial:true,stage,stageSupportComplete,breakComplete}`를 함께 가짐. 후속 직접 편성 가져오기도 이 표식을 유지해야 함. 길드 결과 가져오기 기능 자체는 P1에서 추가하지 않았음.

중단 시 가장 뒤 단계에서 받은 적격 응답을 기존 순위식으로 비교함. 그 단계에 적격 응답이 없으면 앞 단계로 돌아감. 서로 다른 단계의 점수를 섞지 않음. 3단계 전 결과에는 별의 도전 단계·지원 미평가(현재 기본은 6단계·지원 없음)를, 3단계 도중에는 일부 평가를, 이후에는 브레이크 미완료를 표시함.

취소된 실행은 새 요청 id의 상태·결과를 덮어쓰지 않음. 부분 결과는 육성 추천의 완료 기준이나 자동 육성 재탐색의 기준으로 사용하지 않음. 일반 취소·조건 변경은 기존처럼 결과를 버림.

공유 `go`·길드 선택 저장·작업 키·결과 캐시 서명에는 진행 메타를 추가하지 않았음. 공유는 계속 선택 조건만 전달하며 부분 결과를 완주 결과로 저장하거나 공유하지 않음.

## 검증

`guild_defaults_test.js`와 `search_freeze_test.js`의 기대값·정규화는 그대로 유지함. 계획·감시·부분 결과는 `search_plan_contract_test.js`, `search_phase_guard_test.js`, `guild_progress_test.js`에서 실제 구현 변이까지 검사함. 진행 표시 목록·소유자·빠른 갱신 경로는 `gwen_stage_contract_test.js`가 검사함.
