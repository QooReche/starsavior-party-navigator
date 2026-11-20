# 개발·검증 메모

작업 안내: `../HANDOFF.md` → `PORTING.md`.

과거 용량·실측 수치는 기록 시점 기준입니다.

초기 화면 요청은 비압축 기준 HTML 약 1.68MB + quick 약 0.80MB + 화면 JS임(약 2.53MB, 이미지 제외). Cytoscape(약 0.37MB)는 「추천 근거 보기」 켤 때 지연 로드, 근거 문장(약 0.26MB)은 선 탭 시 data/syn_detail.json으로 요청함. 시뮬 최초 다운로드와 구분함. 성장표·스킬은 필요할 때 요청함. 실제 전송량은 압축·캐시에 따라 달라짐.

## 화면 구성

### 추천 파티
- 1안 + 차선 2안. 빠른 계산으로 전체 후보의 순위를 바로 매김.
- 파티 헤드라인: 선택한 전투 방식의 클리어 가능성·클리어 %·턴·위험 구원자. 통계는 title.
- 「시뮬로 확인」: 상위 3팀을 브라우저 안 전투 시뮬레이터로 다시 돌림(시뮬 최초 실행 때 엔진·자료 약 4.79MB와 Pyodide 약 13.78MB를 별도로 내려받음; 합계 비압축 약 18.57MB). 클리어 %·턴·먼저 쓰러지는 구원자 표시.
- 모의 전투는 오토 기준 하나(2026-11-14 수동 모드 제거 — 전환 UI·수동 스킬 순서 없음, 옛 수동 링크·저장값은 무시하고 오토로 열림).
- 기본 100판. 300판 요청·캐시 코드는 호환용으로 남아 있으며 화면 버튼은 제거됨.
- 「링크 복사」: 콘텐츠·스테이지·육성 가정·재점화·브레이크를 주소로 공유. 내 구원자 수치는 기본 포함. 사용자가 체크를 끄면 조건만 공유.
- 브레이크 스킬: 파티 카드에서 선택, 「스킬별 비교」로 보유 스킬을 한 번에 비교.
- 기믹은 기본 접기. 담당 없는 항목만 카드 위에 표시.

### 직접 편성

- 코스모 자동 검색은 정밀 후보에서 비중복 삼중을 못 찾으면 `search.retry.keepMultipliers` 순서로 확대함(null은 전체 후보, 상한 적용). `maxCandidatesPerBoss`와 `maxRerankGames`는 기존 정밀 계산을 포함한 누계이며, `maxTripleChecks`는 모든 재시도의 삼중 검사 누계임. 학습 겹침 회피는 별도 `learned.maxOverlapChecks`를 씀. 예선에서 탈락한 후보는 첫 판 결과를 재사용하고, 빠른 선별 미계산 후보도 복귀 대상으로 두어 새 정밀 job만 요청함. ETA는 같은 정밀 단계의 완료 수·전체 판 수를 누적함. 보스별 상위 20팀 과반에서 쓰이고 둘 이상 보스에 반복되는 구원자 최대 2명을 실패 안내에 표시함. `tests/cosmo_retry_test.js`, `tools/check_cosmo_retry_mutations.py`, 종합 페이지의 `test_cosmo_retry`가 회귀 기준임.

- 삼중 탐색은 a와 호환되는 Ba·Ca를 점수 순서 그대로 만들고 그 최고점으로 가지치기함. a별 경계는 다음 a에서 증가할 수 있으므로 해당 a만 건너뜀. `bestTriples`와 화면의 `bestTriplesAsync`는 같은 생성기를 사용하며, 화면은 검사 4,096회 또는 a 전환마다 시간을 확인해 16ms 이상이면 다음 작업으로 양보함. 시간으로 결과를 자르지 않고 횟수 예산과 동점 ID 순서를 보존함. 소진은 `visit()`의 실패로만 판정하고, 남은 상한은 현재 c 꼬리·다음 b·다음 a의 최댓값임. 요청한 상위 개수를 모두 확보했고 남은 상한이 마지막 점수보다 **엄격히 작을 때만** 제한 경고를 생략함. 확정 범위는 2단계 후보 점수이며 이후 난이도·브레이크 재평가 순위를 보장하지 않음. `tests/cosmo_triples_test.js`와 `tools/check_cosmo_triples_mutations.py`가 기존 구현·전수 대조와 경계 변이를 검사함.

- 진행 문구는 호출자가 주는 `bossName`을 사용함. 학습 선별 선택은 `pn.cosmo.learned`의 boolean만 복원하며 저장값이 없거나 잘못됐으면 시즌 기본값을 사용함. CLI `--lists-output <외부 JSON>`은 각 정밀 단계 직후 목록을 기록함. 계정 후보 목록과 결과는 입력과 다른 작업 트리 밖 파일에만 저장하고 공개 시험 자료로 쓰지 않음. 로컬 조합 측정은 `node tools/measure_cosmo_triples.js --lists <외부 JSON> [--rows <외부 결과 JSON> --target <합계>]`로 함.

- 코스모 게이트는 `cosmo_direct.js`(순수 상태)·`cosmo_direct_ui.js`(보스 카드·편집 패널)·`cosmo_direct_page.js`(페이지/작업자 연결)를 사용함. 컨테이너 `#cosmo-direct-panel`, LS `direct.cosmo.v1`, 공유 `cd`, 소유자 `cdirect`를 기존 1팀과 분리했음. 슬롯은 엔진 순서이며 팀별 리더는 `party.leader`, 육성은 최종 능력치로 직렬화함. 자동 브레이크는 기존 `pickBreak`를 사용함. 팀별 서명에는 시즌·보스·난이도·브레이크·최종 파티·계정·버전·seed·판수를 포함하며 현재 서명의 3팀 결과가 모두 있을 때만 합계를 표시함. 탭 전환은 실행을 유지하고 편집·계정 변경은 코스모 소유 작업만 취소함. 팀별 되돌리기는 다른 팀으로 옮겨 간 구원자를 빼앗지 않음. 공유 초안은 편집 후에도 로컬 저장을 덮어쓰지 않음. 자동 결과는 `CosmoDirectUI.summaryHtml`을 공유하고 실제 선택 행을 `fromSearch`로 가져옴. 공사모 자산·`GWEN_SCENES.construction`은 유지함. 진입 검사는 기존 construction 이름의 시험, 통합 검사는 `tests/cosmo_direct_page_test.js`·`tests/e2e/test_cosmo_direct.py`임.

- `direct_party.js`: 순수 초안·검증·배치 변환·사용자 배치 직렬화·전투력·서명·저장/공유 허용 목록. `direct_ui.js`는 편집, `direct_run.js`는 실행 스냅샷·행별 캐시·비교 표시를 맡음. 둘 다 물리 작업자를 만들지 않음.
- 초안 `{v:1, slots:[{key,grown}|null × 4], leader:key|null, brk:'auto'|null|{name,level}}`. 저장/엔진 순서는 전열1·전열2·후열1·후열2, `toScreen` 결과는 후열1·전열1·전열2·후열2. 리더·육성 선택은 구원자를 따라감.
- `powers`는 선택하지 않은 구원자를 excluded로 넘겨 추천의 overwrite를 호출함. 장비 부위와 journeyPriority를 같이 전달함. 개방 판정 true이고 레벨 자료가 유효하면 체크한 구원자를 사본의 스타링크 slots에 추가해 profile을 재계산함. false면 현재 돌파·실제 개화 기준 최대 레벨을 자기 레벨에 적용하고 4명 조건은 안내만 함. unknown은 현재 수치 계산을 유지하되 레벨 가정·가상 등록 없이 재불러오기를 안내함. 개방 계정의 칸 수·원천·격차 제한을 두지 않는 기존 직접 편성 정책과 원계정 보존은 유지함. fixed200은 기존 능력치 규칙을 쓰며 미개방 안내를 숨김. 옛 저장값·공유의 starLink 필드는 무시함.
- `serialize`는 arrangeOf를 호출하지 않음. B단계 실행 직전 `validate`로 계정·속성·콘텐츠를 검사하고 `serialize(draft, profile.results)`로 직렬화함. `signature`에는 최종 party, stage, break 이름/레벨, seed, runs, options, engine/data/policy/preset versions를 모두 전달해야 함.
- 로컬 저장은 `LS.set('direct.v1', DirectParty.storage(DIRECT))`의 허용 목록만 사용. 공유받은 세션의 storage는 null이고 편집 후에도 로컬을 덮어쓰지 않음. 공유 `dp`는 초안+entry만, `pm`은 화면 모드이며 기존 `m/mode`·`#shared=`와 구분함. 명시적 pm은 공유 초안과 독립적으로 복원함.
- 실행/비교는 B단계에서 연결했음. `SIMPOOL` 관리자가 코어·메모리·모바일 상한 안에서 작업자를 독점 대여함. `scrPool`은 예약 배열이며 `simDispatch` 배정 전에는 비어 있음. 직접 작업은 진행 중인 추천 팀을 끊지 않고 다음 배정부터 우선함. 무진행 타이머는 예약별이며 대기 중에는 멈춤. `simPoolDrop(owner, requestId?, group?)`의 기본 owner는 추천 묶음(`reco`)임.
- 직접 현재/가정은 같은 seed·판수·전체 옵션으로 실행하며 직렬화된 요청이 같으면 계산 한 번을 공유함. 결과의 표시 줄과 스냅샷은 별도로 유지함. 추천 1안은 완료된 `LASTQ[1].rows[0]`과 실행 당시 metadata가 조건·계정·버전까지 일치할 때만 비교함. 추천의 rng_streams 정책은 바꾸지 않았으며 직접 본선도 기존 추천 본선과 같음. 3별 비교는 t60, 구간은 각 Wilson 구간 끝점 차이인 보수적 비교 범위임.
- 직접 진행률은 sim_worker가 DIRECT 요청에 한해 Battle.run 완료를 관측해 전달함. 엔진 파일·판별 집계·난수 입력은 그대로이며 관측 함수는 finally에서 복원함. 새 작업자의 준비 180초·팀별 상한·숨김/절전 보정, 육성 예선 무진행/본선 deadline을 유지함.
- 기존 추천 now/growth 두 탭은 그대로임. 계약 검사는 `node tests/direct_party_test.js`, 실행 소유권은 `node tests/direct_execution_test.js`, B 화면·실제 엔진·되돌림은 `tests/e2e/test_direct_execution.py --real --mutations`임(Playwright Python 필요). B 캡처는 `_tmp/direct-b/`, C 그웬 길/이동/새 그림과 실제 육성 효과 시험은 `tests/e2e/test_direct_gwen.py`·`tools/gwen_art/direct_c.md`, 캡처는 `_tmp/direct-c/`임.

- 2차의 실행 선택은 `pn.direct.with.v1={reco:boolean}` 하나이며 초안·공유·서명에 포함하지 않음. 종속 육성 체크는 `assume-growth`의 change 이벤트를 사용하며 별도 값·저장소가 없음. 추천 탭과 같은 완료 저장소와 서명을 읽어 재계산 없이 연결함.
- `recommend_pipeline.js`는 주입된 계획·예선·본선 함수로 순차 계산함. `recommend_runtime.js`가 입력 사본과 결과 저장소를 연결하고, 기존 추천도 `recoCandidates`·`recoScreenSequence`·`simSignature`와 육성 `growthStageSearch`/`growthEvaluate`를 공유함. `direct_bundle.js`는 작업 소유자와 단계를 관리함. 실행 도중 직접 편집은 direct owner만 중단함. 조건 변경은 묶음을 중단하며, 합류한 추천 탭 작업은 묶음 취소만으로 죽이지 않음.
- 기존 육성 결과를 직접 비교로 가져올 때도 완료된 추천 rows[0]을 `baselineFirst` 기준으로 고정함. 추천 탭 본문·탭 제목도 그 기준을 사용함. 추천 자체의 후보·결과값·정렬은 변하지 않음. 기존 1팀 묶음의 길드 방어전·코스모 「이 줄만 계산」은 계속 차단함. 코스모 3팀은 별도 실행 경로를 사용함.
- 기존 추천 결과 보존을 위해 예선/육성의 rng_streams와 일반 본선 난수 정책을 그대로 사용함. 비교는 짝지은 실험이라고 표시하지 않으며 기존 보수적 구간을 사용함.
- `direct_drag.js`는 마우스 6px, 터치 350ms 이후 끌기를 시작함. 터치 대기 중 8px 이동은 일반 스크롤임. 미리보기 동안 편집·그리기를 보류하고 놓을 때 `directChange`를 한 번 호출함. ESC·바깥 놓기는 취소하며 후속 click을 삼킴. 키보드/누르기는 기존 편집 경로임. 얼굴은 추천의 art·1:1.12·그림 112% 규칙을 사용하고 전원 검토 결과 별도 예외는 없음.
- 2차 화면·실제 스타링크·되돌림·리뷰 회귀 시험은 `tests/e2e/test_direct_phase2.py`, 영상은 `--only video`로 생성함. 59명 얼굴 시트·단계·끌기·실제 전투력 전후 캡처는 `_tmp/phase2/`에 생성하며 공개 커밋에 넣지 않음.

### 이전 육성 가정 (현재 화면에서 숨김)
- 평균 / 80% / 125% / 내 전투력(파티 또는 구원자별) / 내 정보 중 하나만 적용.
- 내 정보를 불러오면 「내 정보」가 기본. 내 정보에 없는 구원자는 기존 가정으로 계산하고 칩으로 표시.

### 내 정보
- `내정보.json`(게임 로그인 때 받는 내 구원자 정보)을 불러와 브라우저 localStorage 에만 저장. 서버 전송 없음.
- 만드는 도구: https://github.com/QooReche/starsavior-myinfo (서랍 「내 정보를 만드는 방법」에 한 줄 명령)
- 「내 정보」 탭: 구원자별 전투력, ★/각인, 공명, 스킬 레벨, 호감도, 장비, 공·생·방·속도.
- 추천 카드에 구원자별 전투력·★/각인 칩, 파티 전투력 합계.
- 형식: `docs/myinfo_format.md`

## 계산

### 최종 능력치 (내 정보 → 능력치)
- 기본·레벨·스타링크·공명·호감도·각인·전술 분석·장비(세트 포함)·건틀렛(여정·잠재력)·고유 상시 패시브를 게임 합산 순서대로 더함.
- 구현: `battlesim/starsavior/myinfo_stats.py`(기준) = `myinfo_stats.js`(화면). 두 결과가 같은지 시험으로 확인.
- 재료: `data/growth.json`. 비공개 게임 표에서 계산에 필요한 수치만 뽑음(`tools/build_growth.py`).
- 콘텐츠 규칙: 작전·회랑은 그대로, 코스모 게이트·플래시 포인트는 레벨 200·공명 10 고정·스타링크 강화 제외.
- 화면 값 5명과 8종 능력치 정확 일치(10/22). 별도 3명은 ±0.2%. 전투력은 화면 대비 +0.1~0.2%.
- 미해석: 건틀렛 축복.

### 빠른 계산
- `quick.js` = `battlesim/quick.py`. 팀 화력 vs 적 화력을 라운드 단위로 비교해 클리어 여부·필요 전투력을 구함.
- 계수는 시뮬 결과에 맞춤(`tools/gen_quick_calib.py` → `tools/calibrate_quick.py --write`).

### 전투 시뮬레이터
- `battlesim/`(Python). 브라우저에서는 Pyodide 로 같은 코드를 실행(`sim_worker.js`, `lib/pyodide/` 에 직접 둠).
- 행동 게이지·스킬 쿨·협공·강인도/브레이크·브레이크 스킬·적 스킬·사망/회복/보호막 반영.
- 행성 정화 지원. 나머지 미지원 항목은 현재 규칙과 아래 기록을 확인. 목록은 `docs/BACKLOG.md`.
- 설계·검증 기록: `docs/battlesim_design.md`, `docs/redesign_v1.md`, `docs/ingame_samples.md`(인게임 실측 대조).
- 게임 코드로 확인한 규칙은 `battlesim/rules/default.json` 의 스위치(근거 등급 `code`)로 둠. 실측 대조: `tools/ingame_check.py --myinfo <내정보>`.
- 화면의 예선·본선은 작업자 여럿에 팀 단위로 나눠 돌림(작업자 풀·대기열·1차 판 재사용: `party_template.html` 의 «작업자 풀·작업 대기열»·예선 주석). 속도를 고칠 때는 `tools/bench_screen.py` 로 고치기 전·후의 예선 순위·팀별 결과·시간·메모리를 대조(결과가 달라지면 안 됨).
- 알려진 한계: 큰 보스전은 편성에 따라 실측보다 비관적이거나 낙관적. 작전·장비 탐사·성간 회랑 등에서 주의. 기록 `docs/received_damage_audit.md`.

### 길드 방어전 (시즌제, 1차)
- 안내 패널(`guild_view.js`): 시즌 상태·«갱신 대기»·기준일, 최고 점수 조합(별의 도전 12단계 + 선택 효과 최대), 점수 범위(가설 A/B, «추정»), 재사용 제한, 커뮤니티 정보(낮은 신뢰). 선택(단계·효과)은 브라우저에만 기억.
- 점수 가설 A = 합계 전체에 추가 점수, B = 보스 처치 점수를 뺀 나머지에만. 공식 계산식이 공개되지 않아 둘 다 보여 준다.
- 시뮬 연동(2차): `battlesim/starsavior/guild_bfb.py`(BFB 상태 기계·별의 도전, 스위치 `mc.guild_boss`), 수치 `tools/build_guild_bfb.py` → `data/guild_bfb.json`, 단계별 클리어율 `tools/build_guild_sim.py` → `data/guild_sim.json`(패널 «시뮬 추정»). 시즌 길드 버프는 미반영. 추천 순위 자체는 여전히 근사 점수.
- 자료 갱신: `PORTING.md` 4-1.

### 추천 점수
- 속성 상성 + 기능 태그 + 스킬 연계(1,120쌍) + 스테이지 기믹(44유형).
- 가중치는 `party_contents.json`. 대부분 임의값.

## 시험
전부 한 번에: `python -X utf8 -I tools/run_tests.py`(`--rebuild` = 시뮬 파일 목록·index.html 먼저, `--e2e <Playwright python>` = 브라우저 시험까지, 낱말을 주면 그 시험만). AI 작업 규칙은 `AGENTS.md`.
```
python -X utf8 -I tests/myinfo_stats_test.py      # 능력치 계산기 (비공개 정답은 STARSAVIOR_STATIC 경로 있을 때만)
python -X utf8 -I tests/run_workspace_test.py tests/quick_test.py
python -X utf8 -I tests/p3_test.py                 # 그 밖 tests/*_test.py, tests/golden_check.py
node tests/myinfo_reco_test.js                     # JS 시험 tests/*_test.js
tests/e2e/test_page.py                             # 브라우저 시험(Playwright, 준비는 docs/PORTING.md 7절)
```

## 게임 업데이트 때
```
python -X utf8 -I tools/update.py                  # 적·태그·연계·기믹·빠른 계산 재료·시뮬 파일 목록·index.html
python -X utf8 -I tools/build_growth.py --static <비공개 표 경로>   # 내 정보 능력치 재료
```
엔진(`battlesim/*.py`)을 고치면 `tools/build_simpack.py` 도 실행.

## 참고
- https://starsavior-guide.github.io (구원자·티어·편성·이미지)
- https://starsavior-databook.pages.dev (스킬·적 데이터)
- https://github.com/p1021/journeyhelper (전투력 계산 참고)
- https://namu.wiki , https://arca.live (전투 규칙·공략 글)
- 직업·속성 아이콘, 브레이크 스킬 이미지, 스킬 아이콘: 게임 리소스

이 도구는 비공식 팬 도구이며 게임과 관련이 없음. 구원자 카드, 스킬·브레이크 스킬·UI 아이콘 등 게임 이미지의 저작권은 원 권리자에게 있음. 이 저장소의 라이선스는 게임 이미지에는 적용되지 않음.

Windows 임시 디렉터리 시험인 web·quick·shim_compat는 `tests/run_workspace_test.py`를 경유함. 데이터 갱신에는 공개 스킬·내 정보 설명 생성도 포함함. 비공개 성장표·슬롯·전투 어댑터는 `--static` 또는 `STARSAVIOR_STATIC`을 지정하여 별도 생성함.

### e2e 서버·실패 진단 (2026-11-02)

- `tests/e2e/test_page.py`는 시험 프로세스 안에서 서버를 띄우며 20000~60000 포트를 직접 바인드해 종료까지 소유함. 8899는 쓰지 않음. Windows에서 기존 `http.server`의 주소 재사용 설정으로 두 서버가 같은 포트에 바인드되는 현상을 재현했음. 새 서버는 주소 재사용을 끄고 `SO_EXCLUSIVEADDRUSE`로 중복 바인드를 거부함. 준비 요청 실패 시 바로 중단하고 브라우저·서버를 정리함.
- 각 시험의 성공·실패와 관계없이 남은 브라우저 컨텍스트와 작업자를 닫음. 실패 시 콘솔 발생 위치와 요청 URL·종류·실패 이유·미완료 요청을 출력하고 `--shots` 폴더의 `<시험 이름>_network.json`에 저장함. 작업자 다운로드도 컨텍스트 이벤트로 수집함. 의도적인 요청 차단 시험은 자체 판정을 유지함.
- 과거 첫 로드 30초 초과와 시즌 전환 연결 거부의 정확한 URL은 옛 로그에 없어 미확인임. 서버 중복 바인드 위험은 재현했지만 그 두 실패의 직접 원인이라고 단정하지 않음. 가상환경 런처와 실제 서버의 PID는 달랐으나, 런처 종료 뒤 자식 서버 잔류는 재현되지 않았음. 로드 시간 제한을 늘리거나 자동 재시도로 실패를 감추지 않았음.
- `e2e_server_test.py`는 동시 서버의 포트 격리·32개 요청·종료를 검사함. 브라우저 `test_request_diagnostics`는 실제 닫힌 서버를 요청해 연결 거부 URL 수집을 검사함. `test_guild_search_dropped`·`test_gimmick_avoid`·`test_sim_timeout_partial`은 가상 계정으로 협공 제외/해제·판별 기대 점수·불리한 구원자 표시·예선/본선 부분 결과·재시도를 검사함. 시간 초과와 협공 화면 시험의 작업자 결과는 제어된 값이며, 기존 실제 Pyodide 작업자 시험도 유지했음.

## 공개 화면 정리 (2026-10-23)

행성 정화의 근거 없는 캐스터·어쌔신 bonusRoles를 빈 배열로 변경했습니다. JS·Python 추천에서 이 배열은 브레이크 스킬 선택 가산에 쓰이므로 기본 추천 스킬이 바뀔 수 있습니다. 파티 점수·엔진 효과는 변경하지 않았습니다. 배열은 기존 소비자의 호환을 위해 유지합니다.
