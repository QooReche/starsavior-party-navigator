# 다른 PC에서 이어서 작업하기

> 빠른 계산·브라우저 시뮬·시험은 맨 아래 7절. (옛 사전 계산 `data/sim/` 은 2026-10-20 퇴역)

저장소 하나로 작업을 이어갈 수 있게 원본 입력 자료(`rawdata/`)와 도구를 모두 포함했다. 순서대로 하면 같은 결과가 재현된다(2026-10-20 기준 검증: `tools/update.py` 를 처음부터 돌려 시너지 1,120쌍·기믹 44유형·스테이지 3,596개가 그대로 재생성됨).

## 1. 준비
```
git clone https://github.com/QooReche/starsavior-party-navigator.git
cd starsavior-party-navigator
```
- Python 3.11 (표준 라이브러리만으로 대부분 동작). 이미지 도구(`tools/fetch_images.py`, `crop_break_icons.py`)만 `pip install -r requirements.txt` (opencv-python, numpy)가 필요하고, 가상환경은 저장소 밖에 둘 것.
- Node.js (가이드 추출기·JS 시험·Python↔JS 동일성 시험에 사용함).
- 스크립트는 `python -X utf8 -I <스크립트>` 로 실행한다(`-I` 는 스크립트 폴더를 import 경로에서 빼므로 일부 스크립트는 스스로 경로를 추가한다). 한글·백슬래시가 든 코드는 셸 heredoc 으로 넘기지 말고 파일로 만들어 실행할 것(`\n` 이 풀리는 문제가 반복됨).

## 2. 확인
```
python -X utf8 -I party_reco.py 작전 --stage "SECTOR 1-1"      # 콘솔 추천
python -X utf8 -I build_party_html.py index.html                  # 웹 페이지 생성
python -m http.server 8000 --bind 127.0.0.1                       # http://127.0.0.1:8000/index.html (file:// 로는 일부 도구가 못 연다)
```

## 3. 저장소 구성(어디에 뭐가 있나)
| 위치 | 내용 | 비고 |
|---|---|---|
| `rawdata/` | 원본 입력: `databook_main.json`(데이터북 main.js 를 푼 것), `foe.js`(적 정보), `guide_app-core.js`(가이드 DB), `break_ref/`(브레이크 스킬 인게임 스크린샷 7~11) | 출처 사이트가 바뀌면 `tools/fetch_sources.py` 로 갱신 |
| `data/` | 엔진·웹이 쓰는 생성 데이터 | `tools/update.py` 가 재생성. 수동 보정은 `synergy_overrides.json` |
| `party_contents.json` | 모든 가중치·콘텐츠 규칙(임의값 포함) | 보정은 여기 |
| `party_reco.py`, `party_template.html`, `build_party_html.py` | 엔진(콘솔), 웹 템플릿(JS 엔진 포트 포함), 웹 생성기 | **엔진은 py 와 JS 두 곳에 있으므로 점수식을 고치면 둘 다 고칠 것** |
| `battlesim/` | 전투 시뮬레이터 패키지(화력 지표·파티 시뮬, 규칙 수치 `battlesim/rules/default.json`) | `tools/sim_damage.py` 는 호환 껍데기. 회귀 시험 `tests/golden_check.py`, 설명 `battlesim/README.md` |
| `tools/` | 데이터 생성 도구 | `update.py` 가 진입점 |
| `assets/` | 아이콘·초상화·일러스트·브레이크 스킬 이미지 | 이미지 사용은 사용자가 허락 |
| `docs/` | 조사 자료·검수 문서(`research.md`, `gimmick_review.md`, `weight_check.md`, `corridor_rules.md` 등) | 근거 확인용 |
| `HANDOFF.md` | 현재 상태, 미검증, 다음 후보 | 먼저 읽을 것 |

## 4. 게임 업데이트가 있을 때

비공개 표 갱신 뒤 `python -X utf8 -I tools/build_chain_damage.py --static <static-data 경로>`로 연쇄 피해 유형도 다시 생성함. `data/chain_damage.json`은 구원자·스킬별 유형만 담고, 한 스킬 안에 유형이 섞이면 줄별 매핑을 추가하도록 빌더가 실패함. 대상 문구가 바뀌면 `tools/build_auto_skill.py`도 재생성함.
```
python -X utf8 -I tools/fetch_sources.py                 # 데이터북·가이드 DB 원본 갱신(rawdata/)
node tools/extract_guide_tier.js                          # 가이드 DB 티어·주 사용 콘텐츠 -> data/db_tier.json
python -X utf8 -I tools/update.py                         # 태그·연계·분류·전투력 표·적 정보·기믹 재생성 + 변경 요약 + index.html
```
- **패치 때마다 먼저 확인(2026-10-29 누락 사고)**: 신규 구원자가 나왔으면 가이드 사이트(`rawdata/guide_app-core.js` 의 `SAVIORS`)에 이미 있는지 본다. 있으면 아래 `savior_reco.json`·`saviors_index.json`·그림 갱신이 **필수**(`update.py` 는 이 파일들을 자동 갱신하지 않음). 안 하면 신규 구원자가 «가이드에 없음»으로 보이고 쌍 빌더가 키 None 으로 죽는다. 그림은 가이드 `data/savior-detail-assets/<id>-portrait|illustration.webp` 를 `fetch_images.py` 규격(얼굴 160px·일러스트 420px)으로 줄여 `assets/savior/<키>_face|art.webp` 로. 클라 표 기반 빌더(`--static` 15개)는 `static-data` 재추출이 «중복 번들 최신 우선»으로 끝난 뒤(`static-data/INDEX.md` 2b) 돌릴 것.
- 가이드 DB 가 구원자를 추가했으면 `data/savior_reco.json`(구원자 목록·추천 세팅)은 여정 내비게이터 저장소(`QooReche/starsavior-journey-lite`)의 `assets/savior_reco.json` 에서 갱신하고, `data/saviors_index.json`(이미지 경로)은 가이드 DB 의 `saviors_index.json` 을 받아 갱신한 뒤 `python -X utf8 -I tools/fetch_images.py`(opencv 필요)로 초상화·일러스트를 받는다.
- `fetch_sources.py` 는 사이트 구조가 바뀌면 정규식이 실패할 수 있다(`--dry` 로 주소만 확인 가능). 실패하면 브라우저로 직접 받아 `rawdata/` 에 넣고 `tools/unwrap_ssd.py <main.js>` 를 쓴다.
- 이어서 `docs/gimmick_review.md`·`docs/synergy_pairs_review.md` 의 변경 요약을 확인해 새 구원자/기믹을 검수한다.

장비 던전 단계 확장 때는 `check_build.py` 확인 → `DECOMPILE.md`·`INDEX.md`에 따라 표/문자열/배치 재추출 → `$env:STARSAVIOR_STATIC='<static-data 경로>'` 지정 → `python -X utf8 -I tools/build_foe_equip.py` → `python -X utf8 -I tools/update.py` → `python -X utf8 -I tools/unsupported_allowlist.py --diff` → `python -X utf8 -I tools/run_tests.py --rebuild` 순서로 실행함. 생성기는 클라 `BattleName`을 쓰고 데이터북에 없는 탭·단계만 `data/foe_equip.json`에 담으며, 기존 1~20단계는 그대로 둠. 현재 표에 실제 21·22단계가 없으면 빈 조각이 정상임. 패치 뒤 세 탭의 신규 6단계·스킬·소환·화면 목록을 확인하고, 새 효과 때문에 생성이 실패하면 원인을 클라에서 확인한 뒤 변환기를 확장함. 기존 단계 대조는 `python -X utf8 -I tools/compare_foe_equip.py --out local/equip-compare.json`이며 범위·차이 판정은 [장비 단계 검증](equip_client_stages.md)에 정리함. 새 장비 등급(예: `EquipTier=3`)이 생기면 체크: □ `tools/build_growth.py`의 표준 장비 등급 선택(기존 84줄) □ 같은 파일의 아이템·세트 매핑(기존 254줄) □ `battlesim/starsavior/build.py`의 표준 육성 등급 인덱스(기존 24줄) □ 내정보 아이템 ID·세트 매핑 및 `myinfo_stats.py`/JS 계산 일치. 등급 번호만 보고 수치를 추정하지 않음.

### 4-1. 길드 방어전 패치 후 새 시즌 추가
정본은 `data/guild_seasons/<seasonId>.json`, 현재 선택은 `data/guild_current.json`의 명시적 ID임. `data/guild_defense.json`은 모듈을 펼친 현재 화면용 생성 사본임. 날짜는 상태 표시에만 쓰고 시즌을 자동 선택하지 않음. 30111은 BFB 전용 실행기와 당시 공개 `guild_bfb`·`guild_sim` 자료를 함께 보관했음. 보관 시즌은 현재 빌드에서 다시 추출한 정의이며 당시 빌드 재현본이 아님.

1. static-data의 `check_build.py`로 설치본·DLL 일치를 확인하고, 패치됐다면 `DECOMPILE.md`에 따라 표·디컴파일을 다시 추출함. `STARSAVIOR_STATIC`을 해당 폴더로 지정함. 일반 적·버프 등 공용 자료 생성과 현재 번역 이름 연결 검사를 먼저 마친 뒤 시즌을 추출함. 공용 자료를 뒤늦게 갱신하면 시즌 정의의 의존 자료 해시와 시뮬 표도 다시 생성해야 함.
2. `python -X utf8 -I tools/build_guild_seasons.py --season 30112 --extract-only`로 새 시즌을 생성함. 시즌 행 → 전투 행 → 원래 배치 스크립트·유닛 레벨/스탯·스킬 → 난이도 그룹·지원 SE를 연결함. 없는 시즌·해석하지 못하는 지원 효과는 중단하며, 없는 배치 스크립트는 해당 단계에 실행 불가 사유를 남김. 다른 시즌 배치에 새 유닛을 끼워 만들지 않음.
3. 생성된 시즌 파일의 `season.start/end/settleEnd`, `asOf`, 표시 문구·출처를 확인한 값으로 채움. 실제 전투 값과 보스 실행기(`client`/`bfb`)를 확인함. 선택 효과 `sets`는 계속 가정 계산용임. 보스별 실제 처치·체력 감소가 기본 점수이고, 추가 점수 배율의 서버 반올림은 미확인임.
4. `python -X utf8 -I tools/build_guild_seasons.py --current 30112 --select-only`로 현재 시즌을 전환함. 정본의 `dataVersion` 재계산, 현재 사본, `party_contents.json`의 보스 항목을 함께 생성함. 현재 기본은 `data/guild_current.json`이 정본임. 11/26 공개 행 확인 뒤 30112로 전환했음.
5. `python -X utf8 -I tools/build_guild_sim.py --season 30112 --workers 1`로 현재 시즌 시뮬 표를 생성함. 지원·도전 범위·기준 전투력은 시즌 정의에서 읽음. 새 표의 시즌·자료 버전이 다르면 화면에 싣지 않음. 30111 보관 자산을 새 시즌 표로 덮어쓰지 않음.
6. `python -X utf8 -I tools/unsupported_allowlist.py --diff` → `python -X utf8 -I tools/run_tests.py --rebuild` → Playwright의 `tests/e2e/test_page.py`·길드 관련 시험을 실행함. 관문은 보관된 client 시즌도 검사함. 새 미지원은 클라로 확정하거나 근거와 사유를 등록함. BFB 78조건 골든·108조건 훅/타임라인 회귀도 확인함.

공유 링크는 `c=guild&gs=<seasonId>`임. `gs` 없는 옛 링크는 30111로 해석하고, 현재 선택과 다르면 안내 후 실행을 막음. 검색·저장·결과 캐시는 시즌과 자료 버전을 포함함. 일반 적 정의 등 의존 자료가 달라지면 보관 정의를 조용히 다른 데이터로 실행하지 않고 오류로 알림.

11/26처럼 일반 적 조각이 추가되면 보관 시즌도 현재 클라에서 다시 추출해 의존 자료·근거 줄을 갱신함. 30111의 BFB 설정·`data/guild_seasons/30111/` 보관 자산은 생성기가 유지하며 과거 빌드 재현본으로 부르지 않음. 마지막에 현재 시즌의 날짜·공식 출처를 확인하고 `--select-only` → `build_guild_sim.py` 순서로 자료 버전을 맞춤. 시즌 전용 시험은 해당 보관 ID를 명시하고 현재 시즌 시험과 구분함.
칸 대조 근거·잔여 제한은 [칸 검증 문서](guild_khan_1125.md), 미지원 관문 운영은 [관문 문서](unsupported_gate.md)에 정리했음.

#### 보스·몬스터 모듈의 등록과 재등장

- `data/boss_modules/`는 보스 표시·실행기, 몬스터의 스킬/패시브/자동 대상/디버프 정의와 기믹을 내용 해시로 보관함. 동일 정의는 같은 파일을 재사용하고, 변경된 정의는 새 파일이므로 과거 시즌의 모듈을 덮어쓰지 않음. 기존 일반 적은 공용 foe 정의와 서명 참조를 재사용하며 원문 표를 복사하지 않음. 시즌에는 `$module` 참조와 배치·단계 능력치·점수·난이도·지원 연결을 남김.
- 읽는 곳은 `battlesim/starsavior/boss_registry.py`의 `expand`임. 길드 `load`와 화면 빌더가 같은 펼친 자료를 사용함. BFB 전용 `guild_bfb`·공통 `guild_common`·코스모 컨트롤러 선택도 이 등록 경로에 모았음. 전투 규칙·빠른 계산의 공통 정본(`rules/default.json`·`foe`·`quick.json`)을 모듈마다 복제하지 않음.
- 이름과 동작의 연결은 `data/boss_catalog.json`이 정본임. `monsters`/`clientModels`의 `profiles`가 `behaviorProfiles`의 기능·스위치를 고르고, `FoeDef.boss_behaviors`를 통해 엔진에 전달함. 칸의 순차 SE·과열 기절·확정 단일 SE·면역 전 적중·legacy 추가 발동 경계, 일반 벨그라스 SE, 바스커빌의 클라 효과 실행은 표시 이름을 비교하지 않음. 같은 기믹의 다른 이름은 기존 profile을 등록하면 됨. `monsters.extract`의 클라 유닛 패턴·개수·스킬 목록·확정 SE 검증과 `skillPrefix`/`clientRules`도 추출기가 읽음. 클라 연결과 확률이 달라지면 기존 검증에서 중단함.
- 코스모는 등록의 `adapter`로 웨이브 생성기(`stage`/`erosion`)를 선택하고 `modelData`로 보관 모델, `mechanics`로 상태 기계 기능을 연결함. 침식 모델의 표시 이름·key는 시즌 보스 정의에서 받음. 새로운 이름으로 기존 모델을 재사용할 때 엔진 분기를 추가하지 않음. 새로운 종류의 동작은 클라 근거를 확인한 어댑터 구현과 등록을 함께 추가해야 함. 모델 내부의 SE ID/스킬 구조 검증과 효과 종류 분기는 유지함.
- 모듈·보관 시즌·현재 사본은 `tools/boss_modules.py:write` 하나로 UTF-8/LF 직렬화함. 길드 의존 입력은 `boss_registry.GUILD_DEPENDENCIES`로 관리하며 현재 코스모/길드 사본은 포함하지 않음. JSON 의존성은 정규화한 내용 해시(`json:`), 원본 JS는 LF 바이트 해시로 검사함. 보스 등록표 변경도 길드 의존성 변경이므로 보관 시즌을 확인·재추출하고 시뮬 표의 자료 버전을 맞춰야 함. 기존 보관 시즌 선택만으로 다른 콘텐츠의 의존 해시가 바뀌지 않음.
- 새 보스: 공개 연결 확인 → 기존 추출기로 수치·효과 생성 → `tools/boss_modules.py`의 등록/재사용 → 시즌 파일 참조 → 현재 시즌 선택 → simpack·시뮬 표·화면 생성 → 진행도/미지원·기존 보스 불변 시험 순서임. 기존 효과로 표현되지 않는 새 동작만 클라 근거를 조사해 어댑터/스위치를 추가함.
- 재등장 보스: 이전 `$module`과 전용 자산 참조를 그대로 고르고 새 시즌의 배치·단계·점수·지원 값을 추출함. BFB의 `bfb` 실행기와 자산도 보관돼 있음. 지원 방식·배치가 달라졌다면 옛 수치를 그대로 적용하지 않고 새 추출본으로 대조함.
- 코스모 배치 식별자는 `data/boss_catalog.json`의 `cosmo` 등록만 사용함. `build_cosmo_raid.py`는 보스 모듈과 `data/cosmo_seasons/<id>.json`을 저장하고 화면용 `cosmo_raid.json`을 생성함. 기존 보관 시즌 선택은 `--season <id> --select-only`로 함. 벨그라스의 모델·기록자·처단자는 1022 모듈에 보관돼 있으며 현재 보스 목록에서 빠졌어도 삭제하지 않음.
- 확인: `tests/boss_modules_test.py`는 30109(심해의 폭군)를 현재 시즌으로 임시 지정해 실행·화면 자료를 만들고 실제 현재값 30112 복원을 검사함. 1022 벨그라스도 모듈 시즌 파일만 선택해 보관 fixture와 결과를 비교함. 모듈 해석 비활성화·해시 훼손은 실패해야 함. e2e의 과거 시즌 화면도 30109를 사용함. 같은 보스/효과의 다음 로테이션은 추출 도구 → 모듈/시즌 데이터 → 시험으로 처리하며 시즌 번호별 코드를 추가하지 않음.
- 선택기 회귀는 `tests/season_selector_test.py`임. worktree 안 임시 복사에서 실제 CLI로 코스모 1022→1023→1023·길드 30109→30112→30112를 선택하고 웨이브·시뮬·결과 불변·직렬화 일치를 검사함. `tests/boss_behavior_test.py`는 다른 이름/모델 등록으로 칸·일반 침식·코스모 침식·클라 효과 profile을 재사용하며, 기능 등록 제거 변이를 검사함.

### 4-2. 코스모 게이트 시즌 갱신(시즌제 콘텐츠)
시즌 값(보스 3종·Step 스탯·난이도 레벨 표·챌린지 효과·시즌 전투 버프·점수 상수)은 `data/cosmo_seasons/<id>.json`에, 재사용 보스 정의는 참조한 모듈에 있음. `data/cosmo_raid.json`은 이를 펼친 현재 화면/엔진용 생성 사본이며 코드(`battlesim/starsavior/cosmo_raid.py`, `cosmo_raid.js`)는 시즌 공통임. 자세한 근사 목록은 `docs/cosmo_raid.md`.
- 새 시즌 표를 추출한 폴더(파일명 `CLIENT_` 접두, 문자열 `hard/STRING_COMMON.json`, 배치 스크립트 `plain/`)를 만든다. 비공개 static-data 에 새 표를 반영하는 일과는 별개이며 빌더는 폴더를 인자로 받는다.
- `python -X utf8 -I tools/build_cosmo_raid.py --tables <폴더> --season <RankingRaidSeasonId> --build <빌드>` → `data/cosmo_raid.json`. 기대한 표 구조(벨그라스 스킬·버프·SE)와 다르면 `Changed` 로 멈춘다 — 그때는 상태 기계(`Controller`)를 사람이 다시 확인한다. 새 챌린지 효과 번호(`SET_NN`)는 `EFFECT_KIND` 에 추가하고 엔진 처리(`on_wave`/`after_cast`/`post_hit`)를 넣는다(없으면 `kind=null` → 시뮬 결과 `unsupported.runtime` 에 «미지원 챌린지 효과» 로 남음).
- 새 보스의 배치 식별자는 `data/boss_catalog.json`에 등록함. 공용 foe에 cosmo «이름 N단계» 적 정의가 있으면 재사용하고, 없으면 빌더가 `sim=false`로 사유와 함께 막음. 전용 모델도 등록된 어댑터 뒤에서 실행함. 재등장 때는 보관 모듈·시즌 데이터만 선택함(위 모듈 절).
- 시즌을 바꾸기 전에 지금 자료를 `tests/fixtures/cosmo_raid_<시즌>.json` 으로 동결할지 본다 — 그 시즌 전용 모델·효과의 회귀 시험은 fixture 로 돌린다(`tests/cosmo_fixture.py`, 1022 선례). foe 자료는 `tools/update.py` 로 먼저 갱신.
- «3보스 최고 점수 편성 찾기» 설정(풀 크기·판 수·K 등)은 `data/cosmo_raid.json` 의 `search`(빌더 `tools/build_cosmo_raid.py` 의 `SEARCH` 상수에서 옴). 시즌이 바뀌어도 값은 그대로 두되, 판 시간이 달라지면 조정(`docs/cosmo_raid.md` 2단계).
- `python -X utf8 -I tools/build_simpack.py`(`data/cosmo_raid.json` 은 시뮬 파일 목록에 포함) → `python -X utf8 -I tests/cosmo_raid_test.py`(`COSMO_TABLES=<폴더>` 를 주면 표에서 다시 뽑은 값과 대조) → `tools/run_tests.py --rebuild`.
- 미지원 관문: `python -X utf8 -I tools/unsupported_allowlist.py --diff` → 새 항목은 클라 확정 또는 사유 등록(해소된 항목은 삭제) → `python -X utf8 -I tools/run_tests.py`. 고정 편성·시즌 보스 갱신 기준은 [관문 문서](unsupported_gate.md) 참조.

## 5. 저장소에 없는 것(다른 PC에서 다시 설정)
- Claude 의 메모리·`AI\CLAUDE.md` 규약은 저장소에 없다. 이 저장소의 `HANDOFF.md` 와 이 문서가 같은 내용을 담았다.
- GitHub 로그인(`gh auth login`)과 git 사용자 설정(개인 메일 대신 noreply: `git config user.email 87477643+QooReche@users.noreply.github.com`).
- 서브에이전트 분석에 쓴 중간 산출물(`tools/raw/`, 약 수십 MB)은 재생성 가능해서 저장소에서 제외했다.
- 웹 화면 확인 도구(Chrome 확장 등)는 PC 별 설정이다. 화면 검증은 `http.server` + 브라우저로 하면 된다.

## 6. 배포
- GitHub Pages(`main` 브랜치 루트)가 `index.html` 을 서비스한다: https://QooReche.github.io/starsavior-party-navigator/
- 변경 후 `python -X utf8 -I build_party_html.py index.html` 로 `index.html` 을 다시 만들어 함께 커밋·푸시한다.
- `data/quick.json`(빠른 계산 재료·계수)과 `sim/manifest.json`(브라우저 시뮬 파일 목록)도 같이 커밋한다. 페이지는 이 파일들을 불러오므로 `file://` 로는 안 열린다(로컬 서버 필요).
- 저장소 루트 `.nojekyll` 을 지우지 말 것 — 없으면 Pages 가 `__init__.py` 를 숨겨 브라우저 시뮬이 404 로 실패한다.

## 7. 빠른 계산·브라우저 시뮬·시험
### 7-1. 데이터 갱신(게임 업데이트 때)
```
python -X utf8 -I tools/update.py          # 태그·연계·적 정보 + 빠른 계산 재료(data/quick.json, 계수 보존) + 시뮬 파일 목록(sim/manifest.json) + index.html
```
- 엔진 코드(`battlesim/*.py`)를 고쳤으면 `python -X utf8 -I tools/build_simpack.py` 로 목록(내용 해시)을 다시 만든다.
- 엔진 규칙·적 데이터가 크게 바뀌면 빠른 계산 계수를 다시 맞춘다(작업자 2개·낮은 우선순위):
```
python -X utf8 -I tools/gen_quick_calib.py --runs 40 --per-content 400   # 약 15분, tools/raw/quick_calib.json
python -X utf8 -I tools/calibrate_quick.py --write                       # 콘텐츠별 계수 + 보스 스테이지 보정(sm)
```
- 설계·결과 = `docs/redesign_v1.md`, 남은 일 = `docs/BACKLOG.md`.

### 7-2. 시험
```
python -X utf8 -I tests/run_workspace_test.py tests/quick_test.py        # 빠른 계산 Python = JS(300건), 단조성, 역보정, 계수 보존
python -X utf8 -I tests/run_workspace_test.py tests/web_test.py          # 브라우저 시뮬 진입점(battlesim/web.py), 시뮬 칸 순서, 서순, 목록 파일만으로 실행
python -X utf8 -I tests/p5_test.py && python -X utf8 -I tests/p3_test.py && python -X utf8 -I tests/rules_test.py && python -X utf8 -I tests/run_workspace_test.py tests/shim_compat_test.py && python -X utf8 -I tests/golden_check.py
```
브라우저 시험(Playwright, 가상환경·브라우저는 저장소 밖에 — C: 가 좁으면 다른 드라이브로):
```
# PowerShell: 저장소 밖의 설치 경로를 지정하기
$venv = Join-Path $env:LOCALAPPDATA 'pn-venv-pw'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $env:LOCALAPPDATA 'pn-pw-browsers'
python -m venv $venv
& "$venv\Scripts\python" -m pip install playwright
& "$venv\Scripts\python" -m playwright install chromium
& "$venv\Scripts\python" -X utf8 tests\e2e\test_page.py --shots local\shots
```
- 시험이 직접 `python -m http.server` 를 127.0.0.1 빈 포트에 띄우고 끝나면 그 프로세스만 끈다. 시험 프로세스·서버·브라우저는 낮은 우선순위로 돈다.
- 확인 항목(27개): 콘솔 오류 0·옛 결과 안 부름, 빠른 계산 추천·보유 필터·육성 가정·구원자별 전투력, 브라우저 시뮬(인터넷 필요 — 결과·입력이 파이썬과 같음), 내려받기 차단 시 실패 표시, 자동 확인·시뮬 기준 판정, 수동 모드 없음(옛 수동 링크는 오토로 열림), 코스모 두 파티 겹침 없음(시뮬 뒤에도), 모바일 390×844, 파이썬/JS 근사 상위 10 일치. 스크린샷은 `--shots` 폴더.
- 경로가 다르면 `PLAYWRIGHT_BROWSERS_PATH` 만 맞추면 된다(시험은 기존 로컬 브라우저 경로가 있으면 호환 기본값으로 사용함).

CMD에서는 환경변수를 `set PLAYWRIGHT_BROWSERS_PATH=<경로>`로 지정함. 위 예시는 PowerShell 문법임.
