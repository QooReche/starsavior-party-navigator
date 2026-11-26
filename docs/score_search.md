# 점수형 탐색 부품 (P2, 2026-11-26)

정책·결과 불변 추출임. 설정·후보·작업 순서·시드·판 수·동점 처리·완주 결과·공유 서명을 바꾸지 않았음. 일반 추천의 흐름은 옮기지 않았음. 모든 탐색 실행은 기존 `GS.runPhase`를 거침. 진행·부분 결과 계약은 [search_progress.md](search_progress.md)를 그대로 따름.

## 부품과 조립

번호는 11/26 중복 조사 §3 기준임.

| 번호 | 공통 부품 | 길드 조립 | 코스모 조립 |
|---|---|---|---|
| 10 | `PlacementSearch.joint` | 최종 후보 **한 팀씩** 호출, 마지막 정밀 단계는 전 팀을 모아 실행 | 모든 팀을 묶어 호출, 최종 브레이크 전수 재확인은 호출부에 유지 |
| 11 | `ScoreSearch.placementAudit` | 경계 먼저·학습 감사 표본 뒤, 복구·확대는 planner | reservoir 먼저·경계 뒤, 보스별 복구·확대는 search |
| 12 | `fitScreen`, `evaluateMissing`, `expandedSettings` | 표본 평가→학습, 후보·감사 재사용, 확대 | 보스별 표본 평가→학습, 겹침 회피 후 감사, 확대 또는 512팀 전수 복귀 |
| 1 | `compareBy`, `descending`, `guildRank/cosmoRank/recoRank` | top→cap→mean, 각 호출부의 keys/order/key 동점 그대로 | 기준→반대→clear, 호출부의 idOf 또는 배치 level→key 동점 그대로 |
| 2 | `ScoreSearch.goal` → `PartyPlacement.goalOf` | 일반 추천 `goalVal`·배치 비교가 같은 순수 함수를 사용 | t60가 0이어도 보존, 없으면 clear, 결과가 없으면 null |
| 3·4 | `random`, `reservoir` | 기존 학습 표본 시드 유지 | 섞기·학습 표본·배치 감사의 시드와 난수 소비 횟수 유지 |
| 5 | 기존 `SearchExecutor.chunkSize` | 실행 설정 유지 | 기존 유효 작업자 수(1 이상)의 묶음 식으로 위임 |
| 8 | `PartyPlacement.jobKey` | 시즌 접두사·지원·tiers·브레이크 형식은 길드에서 구성 | 보스 접두사·브레이크 형식은 코스모에서 구성 |
| 9 | `ScoreSearch.topRows` | 경계 동점 자름, 새 방식의 중복은 마지막 값·첫 삽입 순서 | 경계 동점 포함 옵션, 중복은 첫 값, 구원자별 대안은 코스모에 유지 |
| 비중복 조합 | `ScoreCombinations.steps/bestSets` | P3에서 N팀·지원·장비 제약을 주입할 경계만 준비 | 기존 3팀 순회·분기 한정·예산·양보 위치 유지 |
| 21 | 페이지 `seasonTeam` | compact 브레이크·`rowcards` | 상세 브레이크·`rowcards cs-cards` |

`compareBy`는 키별 비교 함수를 순서대로 합성함. 숫자 내림차순은 `descending(value)`를 씀. 마지막 문자열 비교는 기존의 `< ? -1 : 1` 또는 `localeCompare`를 호출부에서 유지함. 일반 추천 순위는 t60/clear→clear→prog이며 기존 교체 여유폭 판정은 그대로임.

## 결합 비교 주입점

`joint({teams, probeJobs, rank, group, jointJobs, revisitJobs, movedJobs, runStage, keep, beforeScreen, validateProbe})`:

- 공통 순서 = 예비 평가 → 결합 짧게 → 그룹별 상위 후보 → 정밀 → 전체 난이도 재확인 → 바뀐 그룹만 재비교.
- `rank(jobs,res)`가 적격성·점수·동점을 소유함. 길드는 점수 필드를 붙인 행, 코스모는 `P.best`의 result 필드 행을 그대로 사용함.
- `jointJobs(teams,probeJobs,probe)`가 `P.levels`에 난이도 경계와 점수를 전달하고 자리×난이도×추가 선택지×브레이크를 기존 순서로 만듦. 길드의 추가 선택지는 지원이며 `finalSupports` 필터를 유지함.
- `revisitJobs(best)`와 `movedJobs(changed)`가 재확인 범위·지원 고정 여부·자리 후보를 소유함. P3의 지원 전체 재확인 정책은 아직 연결하지 않았음.
- `runStage(stage,jobs)`가 시드·판 수·문구를 주입함. 길드는 4~8, 코스모는 5~9를 유지하고 마지막 정밀 9/10은 각 호출부에 남겼음.
- 첫 선별은 그룹별 묶음 순서, 변경 난이도 재선별은 **전역 순위 순서**를 유지함. `perGroup(...,false)`가 후자를 맡음.
- 반환 `selected/extra/probe/conditions/moved/changed`에서 moved는 생성 작업 수, changed는 난이도가 바뀐 그룹 수임. 기존 코스모/길드 결과에 각각 원래 단위로 반영함.
- `incumbentWithMargin(incumbent,candidate,value,margin)`은 차이가 여유폭을 **초과**할 때만 후보를 고르는 순수 함수임. P3 준비용이며 기본 탐색에 연결하지 않았음. 실제 연결할 때 기존 자리도 같은 시드·판 수로 재평가해야 함.

## N팀 비중복 조합 인터페이스

```js
const budget = {remaining: 100000};
const rows = ScoreCombinations.bestSets(lists, 5, budget, {
  id: e => e.key,
  resources: e => ({units: e.keys, support: e.sup ? [e.sup] : [], equipment: e.equipUids})
});
```

- `lists`는 출전 슬롯별 후보 배열 N개, 각 배열은 **score 내림차순**이어야 함. 각 후보의 `score`는 합산할 유한 점수임. 적격성·인장 수·EX 우선·지원 필수 여부는 호출자가 정함.
- 반환은 `{sum, teams}` 배열임. 슬롯마다 후보 하나, 모든 슬롯의 같은 자원 종류 안에서 중복이 없어야 함. `resources`를 생략하면 `{units:e.keys}`만 검사함. 덮어쓸 때도 units를 명시해야 함.
- 자원 종류를 분리하므로 구원자와 지원에 같은 문자열을 써도 충돌하지 않음. 지원 없음은 빈 배열로 표현함. 장비는 슬롯 이름이 아니라 장비 UID를 넘겨야 함.
- `id`는 동점용 식별자임. 기본은 정렬한 구원자 키를 `+`로 연결함. 길드는 지원·난이도가 다른 후보를 구별할 실행 키를 전달해야 함. 합산 점수 동점은 팀 id를 슬롯 순서대로 `/`로 연결한 문자열 순임.
- 3팀은 기존 코스모 최적화 경로임. 다른 팀 수는 같은 비트 마스크·순위 삽입을 쓰는 깊이 우선 분기 한정임. 팀 수별 예산 소모 단위를 서로 비교하지 않음.
- `budget.exhausted`이면 미완료 가능성이 있음. `upperBound`가 반환 경계 점수보다 작다는 증명 없이 전역 최적이라고 표시하지 않음. N≠3의 upperBound는 전체 슬롯 최고점 합을 사용한 보수적 상한임.
- UI에서는 동기 `bestSets` 대신 `steps` 생성기를 조금씩 진행하고 기존 코스모처럼 시간 양보·stale 검사를 붙일 수 있음. 코스모 재순위·후보 확대·삼중 재구성 루프는 그대로 유지했음.

## 남긴 중복

- #6·7·16: 작업자 수·실행 래퍼·ETA의 정책과 진행 메타가 다름. 기존 실행기·P1 계약까지만 공유함.
- #1 일부: 일반 예선 `scrCmp`의 prog null 처리·마지막 ttk 비교와 빠른 계산 순위는 기존 호출부에 남겼음. 일반 배치 순위와 목표 지표만 순수 부품으로 연결했음.
- #11·12 일부: 표본 순서·대표 조건·학습 겹침 회피·전수 복귀·후보 복구는 콘텐츠 정책이라 호출부에 남겼음.
- #13~15: 일반 추천·육성 흐름은 이번 범위 밖임.
- #17~20·22: 코스모 갱신·시작/취소·idle/run/err/done·서명은 부분 결과·육성 재실행·ETA·캐시 조건이 달라 그대로 뒀음. 공통 팀 카드의 HTML·순서·리더 표시는 바이트 대조했음.
- #23~25: 점수 집계 위치·난이도 경계 자료·growthOwned 의미가 달라 그대로 뒀음. 난이도 경계는 결합 부품의 주입점으로만 공유함.

## 검증

동결 `guild_defaults_test`, `search_freeze_test`, `search_screen_freeze_test`, `search_cosmo_trace_test`, 실행기·그웬·길드 배차 계약의 기대값과 정규화는 수정하지 않았음. 새 `score_placement_test`는 f4afb12 코스모 배치 경로와 8조건의 작업·시드·판 수·문구·결과를 비교함. `score_guild_trace_test`는 같은 기준의 길드 배치 끔/켬·감사 복구·확대·난이도 변경을 실제로 실행해 비교함.

`score_search_test`의 부품·브라우저 모듈 로딩 검사와 변이 10건, `score_combinations_test`의 N=1~4 전수 대조 160건과 변이 4건, 결합 비교 변이 3건, 팀 카드 변이 2건을 추가했음. 기존 코스모 삼중 600건·예산 441건·상한 증명·취소 검사도 유지함.

`growth_all_test`는 goalVal 의존성 주입과 변이 위치만, `growth_stage23_test`는 겹침 검사의 변이 대상 파일만 옮겼음. 기대값·정규화는 불변임. 독립 리뷰에서 발견한 재비교 후보의 그룹별 재정렬은 전역 순서 보존으로 수정하고 회귀 검사를 추가했음.

관련 Node 시험 31파일을 직렬로 실행해 31/31 통과했음. 전체 시험·실제 시뮬·Pyodide·e2e는 P0 측정과 겹치지 않도록 실행하지 않았음. 마지막 전체 검증은 메인 작업에서 한 번 실행하기로 함.
