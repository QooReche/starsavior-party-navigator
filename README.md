# 스타세이비어 파티 편성 네비게이터 (시험판)

콘텐츠·스테이지를 고르면 4인 파티(전열 2/후열 2)·리더·브레이크 스킬을 추천하는 개인용 도구.
추천은 계산 모델 기준 참고값이고, 검증된 공략이 아님.

- 사이트: https://QooReche.github.io/starsavior-party-navigator/
- 이어서 작업할 때: `HANDOFF.md` → `docs/PORTING.md`

초기 화면 요청은 비압축 기준 HTML 약 1.68MB + quick 약 0.80MB + 화면 JS임(약 2.53MB, 이미지 제외). Cytoscape(약 0.37MB)는 「추천 근거 보기」 켤 때 지연 로드, 근거 문장(약 0.26MB)은 선 탭 시 data/syn_detail.json으로 요청함. 시뮬 최초 다운로드와 구분함. 성장표·스킬은 필요할 때 요청함. 실제 전송량은 압축·캐시에 따라 달라짐.

## 화면 구성

### 추천 파티
- 1안 + 차선 2안. 빠른 계산으로 전체 후보의 순위를 바로 매김.
- 파티 맨 위 판정 줄: 오토 가능 / 오토 어려움, 못 깨면 약 +N 전투력 필요.
- 「시뮬로 확인」: 상위 3팀을 브라우저 안 전투 시뮬레이터로 다시 돌림(시뮬 최초 실행 때 엔진·자료 약 4.79MB와 Pyodide 약 13.78MB를 별도로 내려받음; 합계 비압축 약 18.57MB). 클리어 %·턴·먼저 쓰러지는 구원자 표시.
- 오토 / 수동: 기본 오토. 수동을 고르면 스킬 순서 예시(서순) 표시.
- 판 수: 100(기본) / 300. 클리어 35~65% 팀만 「더 돌리기」.
- 「링크 복사」: 콘텐츠·스테이지·육성 가정·오토/수동·재점화·브레이크를 주소로 공유. 내 정보·보유 목록은 넣지 않음.
- 브레이크 스킬: 파티 카드에서 선택, 「스킬별 비교」로 보유 스킬을 한 번에 비교.
- 기믹 칸: 스테이지 특이사항 → 대처 → 담당 구원자. 대부분 추정이라 (추정) 표시.

### 육성 가정
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
- 미지원: 반격·선제 방어, 행성 정화 브레이크 스킬 등. 목록은 `docs/BACKLOG.md`.
- 설계·검증 기록: `docs/battlesim_design.md`, `docs/redesign_v1.md`, `docs/ingame_samples.md`(인게임 실측 대조).
- 게임 코드로 확인한 규칙은 `battlesim/rules/default.json` 의 스위치(근거 등급 `code`)로 둠. 실측 대조: `tools/ingame_check.py --myinfo <내정보>`.
- 알려진 한계: 큰 보스전(36-36·37-3)은 실측보다 비관적. 기록 `docs/received_damage_audit.md`.

### 추천 점수
- DB 티어 + 속성 상성 + 기능 태그 + 스킬 연계(1,120쌍) + 스테이지 기믹(44유형).
- 가중치는 `party_contents.json`. 대부분 임의값.

## 시험
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
