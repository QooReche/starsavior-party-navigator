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
```
python -X utf8 -I tools/fetch_sources.py                 # 데이터북·가이드 DB 원본 갱신(rawdata/)
node tools/extract_guide_tier.js                          # 가이드 DB 티어·주 사용 콘텐츠 -> data/db_tier.json
python -X utf8 -I tools/update.py                         # 태그·연계·분류·전투력 표·적 정보·기믹 재생성 + 변경 요약 + index.html
```
- **패치 때마다 먼저 확인(2026-10-29 누락 사고)**: 신규 구원자가 나왔으면 가이드 사이트(`rawdata/guide_app-core.js` 의 `SAVIORS`)에 이미 있는지 본다. 있으면 아래 `savior_reco.json`·`saviors_index.json`·그림 갱신이 **필수**(`update.py` 는 이 파일들을 자동 갱신하지 않음). 안 하면 신규 구원자가 «가이드에 없음»으로 보이고 쌍 빌더가 키 None 으로 죽는다. 그림은 가이드 `data/savior-detail-assets/<id>-portrait|illustration.webp` 를 `fetch_images.py` 규격(얼굴 160px·일러스트 420px)으로 줄여 `assets/savior/<키>_face|art.webp` 로. 클라 표 기반 빌더(`--static` 15개)는 `static-data` 재추출이 «중복 번들 최신 우선»으로 끝난 뒤(`static-data/INDEX.md` 2b) 돌릴 것.
- 가이드 DB 가 구원자를 추가했으면 `data/savior_reco.json`(구원자 목록·추천 세팅)은 여정 내비게이터 저장소(`QooReche/starsavior-journey-lite`)의 `assets/savior_reco.json` 에서 갱신하고, `data/saviors_index.json`(이미지 경로)은 가이드 DB 의 `saviors_index.json` 을 받아 갱신한 뒤 `python -X utf8 -I tools/fetch_images.py`(opencv 필요)로 초상화·일러스트를 받는다.
- `fetch_sources.py` 는 사이트 구조가 바뀌면 정규식이 실패할 수 있다(`--dry` 로 주소만 확인 가능). 실패하면 브라우저로 직접 받아 `rawdata/` 에 넣고 `tools/unwrap_ssd.py <main.js>` 를 쓴다.
- 이어서 `docs/gimmick_review.md`·`docs/synergy_pairs_review.md` 의 변경 요약을 확인해 새 구원자/기믹을 검수한다.

### 4-1. 길드 방어전 시즌 갱신(시즌제 콘텐츠)
길드 방어전은 시즌이 바뀌면 보스·단계 점수·별의 도전이 달라질 수 있어, 시즌 정의를 `data/guild_defense.json` **한 곳**에만 둔다(시즌 id·기간·결산·단계 표·별의 도전·선택 효과·점수 가설·출처/신뢰도). 콘텐츠 이름의 «(시즌4 10/29~11/05)» 는 이 파일의 시작·끝 날짜에서 자동으로 만든다.
- 화면은 열 때의 시각을 시즌 끝(`season.end`)과 비교해 «진행 중 / 결산 중 / 종료», 끝난 뒤에는 «갱신 대기» 경고를 띄운다(`guild_view.js`, 파이썬 쪽 `guild_defense.season_state`). «이 시즌 정보는 ○/○ 기준» 은 `asOf`.
- 갱신 절차: `data/guild_defense.json` 의 `howToUpdate` 참고(시즌·날짜, 단계 표, 별의 도전, 보스, 점수 가설) → `python -X utf8 -I tests/guild_defense_test.py`(일관성·화면 계산 일치·만든 index.html 최신 여부) → `python -X utf8 -I build_party_html.py index.html`.
- 단계 표 값은 클라 표 `GUILD_DUNGEON` 전투 표의 새 시즌 행(`static-data/tables`)에서, 날짜·별의 도전 문구는 공식 공지에서 확인한다. 점수 계산식이 확인되면 `score.hypotheses` 를 하나로 줄이고 `conf` 를 «확인» 으로.
- 추천 연결: 콘텐츠는 `party_contents.json` 의 «길드방어전»(`seasonal`, 보스 BFB 별(배치 ChangeAdjustType)), 스테이지·기믹은 시즌 파일에서 만든다(`guild_defense.foe_content`, `stage_gimmicks`). `data/foe_stages.json`·`stage_gimmicks.json` 은 건드리지 않는다.

### 4-2. 코스모 게이트 시즌 갱신(시즌제 콘텐츠)
시즌 값(보스 3종·Step 스탯·난이도 레벨 표·챌린지 효과·시즌 전투 버프·점수 상수·벨그라스 수치)은 `data/cosmo_raid.json` **한 곳**에 있고 코드(`battlesim/starsavior/cosmo_raid.py`, `cosmo_raid.js`)는 시즌 공통이다. 자세한 근사 목록은 `docs/cosmo_raid.md`.
- 새 시즌 표를 추출한 폴더(파일명 `CLIENT_` 접두, 문자열 `hard/STRING_COMMON.json`, 배치 스크립트 `plain/`)를 만든다. 비공개 static-data 에 새 표를 반영하는 일과는 별개이며 빌더는 폴더를 인자로 받는다.
- `python -X utf8 -I tools/build_cosmo_raid.py --tables <폴더> --season <RankingRaidSeasonId> --build <빌드>` → `data/cosmo_raid.json`. 기대한 표 구조(벨그라스 스킬·버프·SE)와 다르면 `Changed` 로 멈춘다 — 그때는 상태 기계(`Controller`)를 사람이 다시 확인한다. 새 챌린지 효과 번호(`SET_NN`)는 `EFFECT_KIND` 에 추가하고 엔진 처리(`on_wave`/`after_cast`/`post_hit`)를 넣는다(없으면 `kind=null` → 시뮬 결과 `unsupported.runtime` 에 «미지원 챌린지 효과» 로 남음).
- 보스가 바뀌면(벨그라스가 아닌 새 보스) `build()` 의 보스 key 매핑과 엔진의 보스 정의(`build_waves`)를 추가한다. 티리아·카넬리아처럼 databook 에 스킬 줄이 있는 보스는 기존 `cosmo` 콘텐츠 N단계를 재사용한다(`tools/update.py` 로 foe 자료를 먼저 갱신).
- `python -X utf8 -I tools/build_simpack.py`(`data/cosmo_raid.json` 은 시뮬 파일 목록에 포함) → `python -X utf8 -I tests/cosmo_raid_test.py`(`COSMO_TABLES=<폴더>` 를 주면 표에서 다시 뽑은 값과 대조) → `tools/run_tests.py --rebuild`.

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
- 확인 항목(27개): 콘솔 오류 0·옛 결과 안 부름, 빠른 계산 추천·보유 필터·육성 가정·구원자별 전투력, 브라우저 시뮬(인터넷 필요 — 결과·입력이 파이썬과 같음), 내려받기 차단 시 실패 표시, 자동 확인·시뮬 기준 판정, 수동 서순, 코스모 두 파티 겹침 없음(시뮬 뒤에도), 모바일 390×844, 파이썬/JS 근사 상위 10 일치. 스크린샷은 `--shots` 폴더.
- 경로가 다르면 `PLAYWRIGHT_BROWSERS_PATH` 만 맞추면 된다(시험은 기존 로컬 브라우저 경로가 있으면 호환 기본값으로 사용함).

CMD에서는 환경변수를 `set PLAYWRIGHT_BROWSERS_PATH=<경로>`로 지정함. 위 예시는 PowerShell 문법임.
