# 인수인계

갱신: 2026-10-22. 과거 세션 기록은 [docs/HISTORY.md](docs/HISTORY.md)에 원문 그대로 이동했음.

## 현재 상태

- 작업 범위는 `chore/cleanup` worktree임. 커밋·푸시하지 않았음. Claude 검증 후 처리하기로 함.
- 화면은 빠른 계산 + 브라우저 Pyodide 시뮬을 사용함. 옛 `build_sim_results.py`, `p4_test.py`, `data/sim`은 퇴역했음. 코스모 공동 선택은 구현했음.
- 리뷰 결함·정리 내역과 검증은 [docs/cleanup_review.md](docs/cleanup_review.md)에 기록했음.
- 공개 입력 `rawdata/databook_main.json`, `foe.js`, `guide_app-core.js`는 저장소에서 추적함. 비공개 원본·계정 자료는 복사하지 않음.
- 비공개 성장표 생성기는 `--static` → `STARSAVIOR_STATIC` 순으로 경로를 받음. 둘 다 없으면 안내와 함께 실패함. 일반 공개 업데이트는 기존 가공 자료를 사용함.
- Python↔JS 빠른 계산·내 정보 능력치·추천 쌍과 합산 순서, `rules/default.json`의 legacy·보존 스위치를 유지했음.

## 미해결

- 큰 보스전 아군 피해 과소: 기존 60판 기준 36-36 준÷받은 1.09(실측 1.88), 37-3 1.13(실측 1.82), 클리어 0%임. 전체 TURN은 적 포함 행동 수임. 대상별 피해·회복과 구원자별 시전 횟수 증거가 필요함. 근거: `docs/ally_damage_audit.md`, `boss_action_audit.md`, `received_damage_audit.md`.
- 37-5 낙관: 예언자 배치의 `HyperSkillAvailable`을 확인해야 함. 시작 쿨 0 실험은 근거 확보 전 적용하지 않기로 함.
- 건틀렛 `blessings` 미해석, +N 전투력 실측 대조, 10/22 보스 공격력 하향의 데이터북 반영 여부가 남았음.
- 적 생존 기믹·구원자 반응·소수 HP 조건·보스 지정·구조도 후속 기능은 `docs/BACKLOG.md` 참조하기.

## 남은 것

- 엔진 리뷰 7: MC 의미 해석 캐시는 이번에 하지 않았음. 판마다 해석 비용이 있으나 실행 단위 재사용은 정의 수명·전투 상태 분리와 난수 순서 보존 시험이 먼저 필요함.
- 웹 리뷰 4: 후보 평가 재사용은 이번에 하지 않았음. `buildCands`·`quickRank`가 중복 평가하지만 동점 순서·코스모 공동 선택·Python 동일성을 고정한 뒤 분리하기로 함.
- Cytoscape 지연 로드·설명 데이터 분리는 범위 밖으로 남겼음. 이번에는 숨은 그래프 생성만 늦췄음.
- 실행 분기에 연결되지 않은 규칙 설명값과 legacy 스위치는 정리 후보임. 호환 시험에 쓰이므로 삭제하지 않았음.
- Playwright E2E는 샌드박스 파이프 생성 `WinError 5`로 실행하지 못했음. Claude가 제한 없는 환경에서 실행하기.

## 다음 할 일

1. `git diff`와 `docs/cleanup_review.md` 검토하기.
2. `python -X utf8 -I build_party_html.py index.html`, `python -X utf8 -I tools/build_simpack.py` 실행 후 시험하기. 골든에 `--write` 쓰지 않기.
3. `tests/*_test.py`와 `tests/golden_check.py`, `node tests/*.js`를 각각 실행하기. `web_test.py`, `quick_test.py`, `shim_compat_test.py`는 `tests/run_workspace_test.py tests/<이름>.py` 경유하기. `run_workspace_test.py` 자체는 인자가 필요한 실행 도우미임.
4. `E:\AI_mk2\venv-pw\Scripts\python -X utf8 tests\e2e\test_page.py --shots local\cleanup-e2e` 실행하기. 계산은 IDLE 우선순위 유지하기.
5. 검증 후 Claude가 커밋·푸시하기. 신규 원본 수집·계수 재맞춤·비공개 가공은 필요할 때 별도 실행하기.
