# 다른 PC에서 이어서 작업하기

> 전투 시뮬 사전 계산(`data/sim/`)과 브라우저 시험은 맨 아래 7절.

저장소 하나로 작업을 이어갈 수 있게 원본 입력 자료(`rawdata/`)와 도구를 모두 포함했다. 순서대로 하면 같은 결과가 재현된다(2026-10-20 기준 검증: `tools/update.py` 를 처음부터 돌려 시너지 1,120쌍·기믹 44유형·스테이지 3,596개가 그대로 재생성됨).

## 1. 준비
```
git clone https://github.com/QooReche/starsavior-party-navigator.git
cd starsavior-party-navigator
```
- Python 3.11 (표준 라이브러리만으로 대부분 동작). 이미지 도구(`tools/fetch_images.py`, `crop_break_icons.py`)만 `pip install -r requirements.txt` (opencv-python, numpy)가 필요하고, 가상환경은 저장소 밖에 둘 것.
- Node.js (선택, `tools/extract_guide_tier.js` 만 사용).
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
- 가이드 DB 가 구원자를 추가했으면 `data/savior_reco.json`(구원자 목록·추천 세팅)은 여정 내비게이터 저장소(`QooReche/starsavior-journey-lite`)의 `assets/savior_reco.json` 에서 갱신하고, `data/saviors_index.json`(이미지 경로)은 가이드 DB 의 `saviors_index.json` 을 받아 갱신한 뒤 `python -X utf8 -I tools/fetch_images.py`(opencv 필요)로 초상화·일러스트를 받는다.
- `fetch_sources.py` 는 사이트 구조가 바뀌면 정규식이 실패할 수 있다(`--dry` 로 주소만 확인 가능). 실패하면 브라우저로 직접 받아 `rawdata/` 에 넣고 `tools/unwrap_ssd.py <main.js>` 를 쓴다.
- 이어서 `docs/gimmick_review.md`·`docs/synergy_pairs_review.md` 의 변경 요약을 확인해 새 구원자/기믹을 검수한다.

## 5. 저장소에 없는 것(다른 PC에서 다시 설정)
- Claude 의 메모리·`AI\CLAUDE.md` 규약은 저장소에 없다. 이 저장소의 `HANDOFF.md` 와 이 문서가 같은 내용을 담았다.
- GitHub 로그인(`gh auth login`)과 git 사용자 설정(개인 메일 대신 noreply: `git config user.email 87477643+QooReche@users.noreply.github.com`).
- 서브에이전트 분석에 쓴 중간 산출물(`tools/raw/`, 약 수십 MB)은 재생성 가능해서 저장소에서 제외했다.
- 웹 화면 확인 도구(Chrome 확장 등)는 PC 별 설정이다. 화면 검증은 `http.server` + 브라우저로 하면 된다.

## 6. 배포
- GitHub Pages(`main` 브랜치 루트)가 `index.html` 을 서비스한다: https://QooReche.github.io/starsavior-party-navigator/
- 변경 후 `python -X utf8 -I build_party_html.py index.html` 로 `index.html` 을 다시 만들어 함께 커밋·푸시한다.
- 전투 전망 결과(`data/sim/*.json`)도 같이 커밋한다. 페이지는 이 파일을 필요할 때 불러온다(`file://` 로 열면 못 불러옴 — 로컬 서버 필요).

## 7. 전투 시뮬 사전 계산과 브라우저 시험(P4)
### 7-1. 사전 계산(느림)
```
python -X utf8 -I tools/build_sim_results.py                        # 대표 스테이지 240개 전부(프로세스 1개, 낮은 우선순위 — 약 2시간)
python -X utf8 -I tools/build_sim_results.py --workers 2             # 2개(이 PC 규칙상 최대 2) — 2026-10-20 실측 65분
python -X utf8 -I tools/build_sim_results.py --contents cosmo,rush   # 일부 콘텐츠만(그 콘텐츠 파일만 다시 씀)
python -X utf8 -I tools/build_sim_results.py --stage "cosmo/길레/길레 2단계" --quick   # 한 스테이지만 빠르게(기존 파일에 그 스테이지만 덮어씀 — 다른 스테이지는 각자 실행 정보 meta 유지, 개발용)
python -X utf8 -I tools/update.py --sim                              # 데이터 재생성 + 사전 계산 + index.html
```
- 도구는 스스로 우선순위를 Idle 로 낮춘다(`--normal-priority` 로 끔). 판 수는 `RUNS`(선별 32 → 확정 200, 수동 탐색 16, 민감도 64), 시드 `--seed`(기본 20261020).
- **데이터가 바뀌면(게임 업데이트, `party_contents.json` 가중치 수정 등) 반드시 다시 돌린다.** 결과의 스테이지마다 추천 입력 데이터의 해시(`meta.sel`)가 들어 있어, 페이지에 내장된 값과 다르면 페이지가 결과를 숨기고 「시뮬 결과 없음」을 보인다(옛 숫자를 보여 주지 않음).
- 데이터를 다시 받았으면 `tools/build_sim_results.py` 맨 위 `DATA_PATCH` 라벨(화면 메타 줄에 나옴)도 고친다.
- 결과 해석·범위·가정 = `docs/sim_p4_report.md`, 설계 = `docs/battlesim_design.md` 10절.

### 7-2. 시험
```
python -X utf8 -I tests/p4_test.py           # 사전 계산 스키마·관문 순위·수동 델타·시드 결정성 등(임시 폴더에만 씀, 1~2분)
python -X utf8 -I tests/golden_check.py && python -X utf8 -I tests/rules_test.py && python -X utf8 -I tests/shim_compat_test.py && python -X utf8 -I tests/p3_test.py
```
브라우저 시험(Playwright, 가상환경·브라우저는 저장소 밖에 — C: 가 좁으면 다른 드라이브로):
```
python -m venv E:\AI_mk2\venv-pw
E:\AI_mk2\venv-pw\Scripts\python -m pip install playwright
set PLAYWRIGHT_BROWSERS_PATH=E:\AI_mk2\pw-browsers
E:\AI_mk2\venv-pw\Scripts\python -m playwright install chromium
E:\AI_mk2\venv-pw\Scripts\python -X utf8 tests\e2e\test_page.py --shots E:\AI_mk2\work\p4\shots
```
- 시험이 직접 `python -m http.server` 를 127.0.0.1 빈 포트에 띄우고 끝나면 그 프로세스만 끈다. 시험 프로세스·서버·브라우저는 낮은 우선순위로 돈다.
- 확인 항목: 콘솔 오류 0, 스테이지 전환 시 전망 변경·화면 팀 = 사전 계산 1위, 오토/수동 토글(숫자·서순 표·localStorage·`?mode=manual`), 보유 서랍으로 결과 없는 팀이 되면 「시뮬 없음」 칩(숫자 없음)·서랍 배경 클릭으로 닫힘, 플래시 포인트, 모바일 390×844 가로 스크롤 없음·카드 4열 인게임 순서, 파이썬/JS 근사 상위 10 일치(3 스테이지 × 3 보유 필터). 스크린샷은 `--shots` 폴더.
- 경로가 다르면 `PLAYWRIGHT_BROWSERS_PATH` 만 맞추면 된다(시험은 `E:\AI_mk2\pw-browsers` 가 있으면 그걸 기본으로 씀).
