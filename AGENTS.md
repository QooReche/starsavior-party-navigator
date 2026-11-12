# AI 작업 가이드 (Claude Code·codex 공통)

이 저장소에서 AI 가 작업할 때 지킬 것. 2026-11-02 리뷰(게임 PC 커밋 52개)에서 실제로 나온 결함을 바탕으로 정리했음.
상태·남은 일은 `HANDOFF.md` 가 정본. 이 파일엔 «어떻게 일하는가»만 둠.

## 시작할 때

1. `git pull` — 이 저장소와 비공개 `starsavior-static-data` **둘 다**. static-data 가 옛 빌드면 시험이 틀린 이유로 깨지고, 리뷰·조사가 옛 표로 오판함.
2. `HANDOFF.md` 맨 위(«현재 상태»·«남은 일») → `README.md` → `docs/DEVELOPMENT.md`.
3. 시험 기준선: `python -X utf8 -I tools/run_tests.py` — 고치기 전에 이미 깨진 시험이 있는지 먼저 앎.

## 엔진 규칙을 바꿀 때

- **근거는 클라 코드·표의 파일:줄.** 디컴파일본(비공개 static-data `decompiled/NKM/NKM.decompiled.cs` 등, 빌드는 `decompiled/BUILD.md`)이나 static-data 표에서 확인한 것만 «클라와 같음»으로 씀. 확인 못 한 부분은 «미확인»으로 남기고 추측으로 확정하지 않음.
  - ⚠ 외부 `star-savior-decompiled` 는 2026-03-28판이라 근거로 쓰지 않음(11/02 현재 빌드 디컴파일로 대체). 패치 때 static-data `DECOMPILE.md` 로 다시 뽑고, 근거 줄은 빌드가 바뀌면 다시 찾음(`OBF_` 번호도 바뀜).
- **스위치로 넣음**: `battlesim/rules/default.json` 에 `value`(새 기본)·`legacy`(옛 동작)·`alt`·`grade`·`note`·`source`. 새 키는 `tests/rules_test.py` 의 `_EXPECTED_MC_OPTS_KEYS` 에도 추가. 근거가 불완전하면 기본값은 옛 동작으로 둠.
- 결과 해시를 고정하는 시험(`mc_cache_test` 등)은 새 규칙의 옛 값으로 고정(`_KEEP`). 해시를 새 값으로 다시 박아 시험을 «맞추지» 말 것.
- 패치 노트·게임 내 수치가 표와 다르면 날짜를 확인(예: 격돌의 돌풍 게이지 11/01 패치로 2000→3000). 옛 표로 «틀렸다» 판단하지 않음.
- 엔진(`battlesim/*.py`)을 고치면 `tools/build_simpack.py`, 화면(`party_template.html`·`*.js`·data)을 고치면 `build_party_html.py index.html` — `tools/run_tests.py --rebuild` 가 둘 다 함.

## 시험 — 가장 많이 틀린 곳

- **시험이 실제로 뭔가를 검사하는지 확인.** 2026-11-02 에 새 기본값 시험 2개가 standard 육성으로 **진행도 0** 인 스테이지(작전 43-36)를 써서, 기능을 통째로 꺼도 통과했음.
  - 시뮬 시험은 결과 진행도가 0 보다 큰지(`assert progress > 0`), 보려는 경로가 실제로 몇 번 탔는지 확인.
  - standard 육성으로 쓸 만한 스테이지: `clo/달 회랑/FLOOR 100`(클리어, 추가 발동 나감), `clo/태양 회랑/FLOOR 200`(클리어 40~85%), `FLOOR 250`(진행도 0.6 안팎, 웨이브 전환 일어남).
- **일부러 깨뜨려 보기**: 새 시험을 쓰면 고친 코드를 잠깐 되돌리거나(예: `Battle._exec_pick = lambda self: False`) 그 경로를 꺼서 **시험이 실패하는지** 본 뒤 원복. 실패하지 않으면 그 시험은 아무것도 지키지 않음.
- 가짜 작업자·가짜 결과를 쓰는 JS 시험은 실제 결과에 실리는 필드(`via`·`progs` 등)까지 돌려주고, 그 값이 다음 단계(협공 배제·점수)까지 이어지는지 확인.
- Python·JS 로 같은 계산을 두 번 구현한 곳(점수 `score_at`/`scoreAt` 등)은 경계값(반올림 .5, 0, 1)까지 같은지 비교. Python `round` 는 짝수 반올림이라 JS `Math.round` 와 다름.
- 전체: `python -X utf8 -I tools/run_tests.py`(+ `--e2e <Playwright python>`). 실패가 있으면 «원래부터 실패였나»를 고치기 전 커밋으로 확인한 뒤 보고.

## 계산 실수 주의

- **평균을 비선형 식에 넣지 말 것.** 기대 점수는 판마다 점수식에 넣고 평균(평균 진행도 → 점수는 «졸개전 패배 + 클리어» 섞인 팀을 크게 낮춰 봄). 시뮬 결과의 판별 값은 `prog_runs`(api)·`progs`(web).
- 확률 효과는 «언제 굴리나»까지 확인: 클라 `m_fActiveRate` 는 확률(5000 = 50%), 스킬 시작 때 굴리는 것은 **시전마다 한 번**. 유닛 단위로 저장하면 다른 시전이 결과를 물려받음.
- 연쇄 피해 등 공용 식은 «같은 편이면 0» 같은 예외를 넣기 전에 클라 식에 그 분기가 있는지 확인.

## 공개 저장소 — 넣으면 안 되는 것

- 계정 수치: 내 정보 파일, 그걸로 돌린 시뮬 결과(클리어율·응징 횟수 등)를 **데이터·화면 문구·커밋 메시지**에 넣지 않음. 결과는 게임 PC 의 비공개 작업 폴더에만.
- 비공개 static-data 원문 표. 공개 data 는 `tools/build_*.py` 가 뽑은 필요한 값만.
- 커밋 신원은 `QooReche` / noreply. 커밋 전 `git log -1 --format=%ae` 와 `git diff --cached` 에 회사 메일 0건.
- 새 파일을 추가하면 `git status --short` 에 의도한 것만 보이는지. 내 정보 파일은 `.gitignore`(`/내정보*.json`·`/myinfo*.json`·`/samples/`·`/static-data/`)로 막혀 있음 — 다른 이름으로 복사하지 말 것.

## 리뷰

- 엔진·화면 로직을 고쳤으면 커밋 전에 독립 리뷰 한 번(codex 래퍼 또는 다른 모델). 리뷰 지적은 그대로 믿지 말고 클라 코드·패치 날짜로 확인 후 반영/기각, 기각 이유는 HANDOFF 에.
- 리뷰를 맡길 땐 커밋 범위(`git diff A..B`)로 읽게 함 — 작업 트리는 다른 작업이 동시에 바꿀 수 있음.

## HANDOFF·문서

- 문체: 존칭 없이 「했음·하기로 함」, 담백하게, 줄바꿈·소제목. «허락/동의 받음» 같은 말 넣지 않음.
- HANDOFF «현재 상태»는 **지금 사실 스냅숏**: 날짜별 경과를 쌓지 않고, 사실이 바뀌면 그 줄을 고쳐 씀. 규칙 기본값·일치율·시험 수 같은 값은 정본 파일(`battlesim/rules/default.json`·`data/quick.json`)을 가리키고 목록을 옮겨 적지 않음(옮겨 적은 값이 낡아 AI 가 잘못 보고한 사고 11/13).
- «남은 일»은 끝나거나 하지 않기로 한 항목을 바로 지움(번호는 고정, 빈 번호 허용). «예정»·«다음에»라고 적은 일을 했으면 같은 커밋에서 그 문구도 지움.
- 작업 경과(무엇을 왜 바꿨나)는 커밋 메시지와 `docs/HISTORY.md` 맨 위 새 절에. 남은 일 보고 전엔 문서 문구 말고 코드·설정 현재값으로 확인.
- 영상·스크린샷 판독 결과는 `docs/ingame_samples.md`, 대조는 `tools/ingame_check.py`. 판 하나로 전역 가정을 바꾸지 않음.
