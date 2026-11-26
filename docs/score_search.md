# 점수형 탐색 부품 (P2, 2026-11-26)

## 길드 daily 조립 (P3)

`GuildPlanner.search({...cx,S:{...S,preset:'daily'},previous?,session?,nowMs?,secondsPerGame?,cosmoSpeed?,growthResults?})`로 선택함. 기본 프리셋은 `legacy`이며 전환은 별도임. daily는 EX 1팀(닫힌 날 일반 1팀)을 찾고, 결과를 `previous`로 전달하면 앞 팀을 고정한 채 일반 1팀을 추가함. 총 인장은 3장 이하(EX 포함 2팀, 일반만 3팀). 인장 입력·나눔 자동 비교·관련 설정은 제거했음.

`secondsPerGame`은 선택한 작업자 수에서 측정한 벽시계 초/판임. 없으면 호출자가 전달한 `cosmoSpeed`(`cosmo.speed.v2` 저장 객체)를 `CosmoSearch.priorFrom`으로 작업자 수에 맞춰 환산함. 둘 다 없으면 [기존 브라우저 744판·워커 재사용 실측](cosmo_speed_rd_1110.md)의 1/2/4/8작업자 처리량을 근사 초기값으로 사용함(1작업자 약 0.025초/판). 다른 기기·길드 전체 탐색 시간의 검증값은 아니며 실제 시간 상한은 별도로 유지함.

| 명세 | daily 조립·재사용 |
|---|---|
| §2 1~3 | `GS.pool/combos` → 전수 훑기 → `CosmoSearch.pickPass`(동점·구원자별 대안) → 정밀. 학습 선별 없음 |
| §2 4~6·§3 | 앞 팀의 구원자·지원 제외 → 남은 지원마다 최선 조건 → 이번 1팀 후보 결선·브레이크. 동점은 평균→키 |
| §3 재시도 | `CosmoSearch.retryPlan`으로 후보 확대, 이미 받은 판 재사용. 끝내 없으면 앞 팀 보존·인장 추가 사용 없음 |
| §4 | 1위 묶음만 `PartyPlacement.all`+기존 자리, 20→상위 3+기존 자리 100→경계면 200판. `PlacementSearch.incumbentWithMargin`으로 판정. 바뀐 팀만 자기+미사용 지원 재확인·40판 확인·브레이크, 자리로 되돌아가지 않음 |
| §2·§6 실행 | `GS.runPhase`·공통 풀·`chunkSize`·코스모 `workerCount`. 육성 포함도 풀 하나·기한 하나. 통일 시드·`run_offset/merge_raw`로 판을 이어 돌림. 상위 20%는 원시값에서 재집계함(`mergeSummary`의 다판 근사 평균은 사용하지 않음) |
| §6 날짜·설정 | `GuildView.gameDay`가 KST 04:00과 `rules.entryDaysEx`를 참조함. 정본 `guild_defaults.json`, `build_guild_seasons.py --select-only`와 페이지 payload로 반영함. `preset/daily`는 전투 입력이 아니므로 자료 버전 해시에서 제외함 |

`GuildDaily.plan(cx)`는 예상 판 수·시간·축소 목록·팀 부족 안내를 반환함. 시간 상한은 자리 대상→조건 비교 팀 수→정밀 수→풀 순으로 줄임. 풀은 `GS.pool`의 직업 보충과 최대 팀 수에 필요한 `minFront/minDealer` 인원을 보존하고 나머지만 전투력순으로 채움. 하한은 원래 풀과 `max(20, 최대 팀 수 × 4 + 4, 보존 인원)` 중 작은 값임. 예상 조합 수에도 역할 조건을 적용하고 `pickPass`의 전원 동점까지 상한에 포함함. 최소 풀도 예상 상한을 넘으면 실행 전에 사유를 반환함. 실제 실행의 절대 기한과 시간·품질 채택 판정(P4)은 유지함.

결선에서 협공 제외된 묶음은 버리고 남은 조건을 다시 묶으며, 후보 확대 후에도 없으면 새 팀 없이 반환함. 자리 고판수 평가에서도 제외된 후보만큼 나머지 자리를 승격함. 기존 자리가 제외됐으면 다음 유효 자리를 기준으로 비교하고, 모든 자리가 제외되면 팀 부족 결과를 반환함.

진행은 P1의 `planStages`·`etaNew`를 씀. `onPlan`은 시작·조건부 단계·완료 때 갱신되며 `eta`도 전달함. `onPhase.meta.stage`는 실행 순서대로 증가하고 `policyStage`는 명세의 1~7임. 현재 단계의 남은 고판수·브레이크·다른 팀·육성 작업도 ETA에 남김. `onProgress(done,total,estimate)`의 세 번째 인자는 선택적 ETA임. 완료 때 계획의 `complete`, 중단 때 `stopped`를 표시함.

결과는 `teams/rows`, `sum/mean`, `split`, `seals`, `reason`, `warnings`, `flags`, `coverage`, 팀별 `evaluation`과 입력 `signature`를 가짐. 직업 불일치는 배정 지원 `sup`를 유지하며 `effectiveSupport:'none'` 계산을 공유함. 중단은 4단계부터 가능한 부분 묶음을 반환하고, 자리 비교 중에는 6단계 묶음을 반환함. 이어서 찾기 중 중단해도 앞 팀을 유지하고 팀별 evaluation을 보존함. 육성 결과는 `growth`이며 미완료면 전체에도 `partial`을 표시함.

클라 근거(설치 빌드 **26935738**, `check_build.py` DLL 10개 일치 확인): 비공개 `decompiled/NKC/NKC.decompiled.cs:408935`의 `SelectDungeonBuffSlot.SetBuffSlot`, `:408991`의 선택 잠금은 `OBF_6480`만 검사함. `:151518`→`:405948`은 지원 재사용 여부, 출전 `:71370`→`:71397`→`:151528`→`:405957`은 남은 지원이 있을 때 선택 ID가 양수인지 검사함. 팀 직업 인자를 받거나 비교하지 않아 **직업 불일치 지원 선택을 클라가 허용함**. 서버 실행 확인은 별도임.

사이드 이펙트: 자동 추천 길드 줄·직접 편성·공유 `go`·기존 저장 키·옛 결과 서명은 그대로임. daily v3 결과 서명은 날짜·설정·계정 능력치·육성·브레이크·실제 축소 계획과 앞 팀 서명을 구분함. `inputSignature`는 이어서 찾기의 조건 변경을 막음. `createSession(makeWorker)`의 같은 풀·패스별 캐시를 이어 쓰며 `close()`는 다시 찾기·조건 변경·인장 소진·초기 오류 때 호출함. 세션은 영구 저장하지 않음. 지시 밖 처리: 별도 기능 추가 없음. 독립 리뷰로 발견한 시간 예상·판 수 혼합·중단 checkpoint·단계 내부 ETA를 수정하고 회귀·변이 검사에 넣었음.

새 시험은 가짜 작업자 24개 시나리오·daily 변이 14건, 날짜 경계 4건·변이 1건을 검사함. 옛 동결 기대값은 수정하지 않았음. 관련 Node 22파일·자료 버전 Python 7개를 직렬로 통과했음. 전체 run_tests·실제 시뮬·Pyodide·e2e는 실행하지 않았음.

## P5 화면 연결

- `guild_daily_page.js`가 날짜·계정·설정을 세션 서명으로 묶고 `GuildDaily.plan/search`에 전달함. `guild_daily_ui.js`는 결과의 합산·지원 배정·선택 이유·미평가 표식을 그대로 표시함. `guild_daily.css`는 스테이지/별의 도전 칩·모바일 4장 카드만 추가함. 찾는 동안 P1 막대·그웬 소유자를 재사용하며 진행 글자·목록 노드만 갱신함.
- 직접 편성은 `GuildDailyUI.draft`로 엔진 순서·후열 리더·브레이크·육성 가정을 옮기고 기존 `GS.sel`·스테이지·`directNavigate`를 사용함. 결과와 출처 표식은 세션에 남으며 공유 `go`·기존 `guild.v3.*`·`direct.v1` 허용 목록은 유지함. 날짜가 바뀌면 결과를 지우지 않고 출정 날짜를 표시함. 숨긴 `sets.ui`·`sim.ui`는 그대로임.
- 육성 포함은 daily API의 `growthResults`로 한 번에 실행해 같은 작업자 풀·시간 상한을 적용함. 옛 `growthStart`가 daily 결과를 단일 팀으로 오해해 다시 실행하지 않도록 막았음. 현재/육성 묶음은 각각의 합산·가져오기를 사용함. 일반 자동 추천과 legacy 육성 흐름은 그대로임.
- 관련 Node 10파일(`guild_daily_ui`, `guild_daily`, `guild_daily_config`, `guild_progress`, `guild_view`, `guild_search`, `guild_defaults`, `search_freeze`, `gwen_stage_contract`, `direct_party`)과 e2e 4흐름(`test_guild_daily_ui`, `test_gwen_guild_owner`의 각 1280/390)을 순차 통과했음. 합성 작업자만 사용했고 8899·전체 시험·실제 Pyodide 측정은 사용하지 않았음. daily 시험은 결과→가져오기→복귀·부분 표식·중단 전/후·날짜 경계·육성 포함·저장 키·공유·390px 가로 넘침을 검사함.
- 지시 밖 처리: 기존 그웬 e2e 합성 작업자에 누락된 `guild.base_scores`를 보완했음. 수정 전 b958a91에서도 «길드 판별 점수 자료가 누락됨»으로 실패함을 확인했음. 제품 동작·시험 기대값은 바꾸지 않았음. 페이지 업데이트 내역은 추가하지 않았음.
- 독립 커밋 범위 리뷰에서 데스크톱 `.cs-cards` 배치, 검색 필터 밖 스테이지 가져오기, 첫 날짜 검사 오표시를 확인해 수정했음. 각각 왼쪽 카드 열·필터 해제 후 EX 가져오기·첫 tick 경고 없음 회귀 검사를 추가했음. 기각한 지적은 없음.

## P2 추출 범위

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
