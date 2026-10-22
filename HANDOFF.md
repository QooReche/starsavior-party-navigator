# 인수인계

갱신: 2026-10-22 밤. 새 세션은 이 파일 → `README.md` 순으로 읽을 것. 과거 세션 기록은 [docs/HISTORY.md](docs/HISTORY.md)(원문 그대로 이동했음).

## 위치

- 저장소: https://github.com/QooReche/starsavior-party-navigator (공개, Pages: https://QooReche.github.io/starsavior-party-navigator/)
- 로컬: `E:\AI_mk2\starsavior-party-navigator`. 페이지 `index.html` 은 `python -X utf8 -I build_party_html.py index.html` 로 만들어 커밋함.
- 비공개 게임 표: `QooReche/starsavior-static-data`(로컬 `E:\AI_mk2\starsavior-static-data`). 원본 표·계정 자료는 공개 저장소에 복사하지 않음(가공 수치만). 경로는 `--static` → 환경변수 `STARSAVIOR_STATIC` 순으로 받음.
- 내 정보 추출 도구: 공개 `QooReche/starsavior-myinfo`, 소스는 비공개 `QooReche/starsavior-packet-ref`.
- 커밋은 QooReche noreply 로만.

## 현재 상태

- 화면: 추천 파티(빠른 계산 + 브라우저 Pyodide 시뮬), 내 정보 탭(능력치·전투력·내실·장비·건틀렛·출처 분해·스킬 카드), 추천 카드 얼굴 → 스킬 카드, 공유 링크.
- 내 정보 → 최종 능력치는 게임 화면과 일치함(`myinfo_stats.py` = `myinfo_stats.js`). 시뮬은 같은 값 + 잠재력 전투 효과 + 실제 스킬 레벨을 씀.
- 결과 화면 TURN = 적 포함 전체 행동 수(전역 턴). 영상 판독과 해독 코드로 확인했음.
- 빠른 계산 계수 재맞춤(10/22 밤): 판정 일치 91.9%(base 89.8%, 코스모 95.5%, 플래시 95.5%, 스테이지 보정 후).
- 10/22 리뷰 반영 내역: [docs/cleanup_review.md](docs/cleanup_review.md).

## 미해결

- 큰 보스전 비관: 36-36 준÷받은 1.09(실측 1.88), 37-3 1.13(실측 1.82), 시뮬 클리어 0%. 적 피해 속도는 맞고 아군 피해가 부족함. 필요한 증거 = 같은 편성 큰 보스전 녹화(행동 순서·구원자별 시전). 근거 `docs/ally_damage_audit.md`.
- 37-5 낙관: 예언자 배치 데이터 `HyperSkillAvailable` 필요(게임 설치 PC 추출).
- 10/22 패치 미반영: 작전 최종 보스 공격력 하향·공허체 패시브 조정·토벌 하향·플래시 포인트 공허매장자·임무 턴 완화. 수치는 공지에 없음 → 비공개 저장소 `SIM_HANDOFF.md` 맨 위 절차로 표 재추출 후 「10/22 패치 반영해 줘」.
- 건틀렛 축복 미해석.

## 남은 것 (근거는 docs/cleanup_review.md)

- MC 의미 해석 캐시: 난수 순서 보존 시험부터.
- 추천 후보 평가 재사용(`buildCands`·`quickRank` 중복): 동점 순서·Python 동일성 고정 뒤.
- Cytoscape 지연 로드·설명 데이터 분리.
- `rules/default.json` 의 실행 분기 없는 설명값·legacy 스위치 정리(호환 시험에 쓰여 보존 중).

## 작업 방식

- 구현은 별도 worktree(`git worktree add -b <브랜치> E:/AI_mk2/pn-<이름> main`)에서 codex(`gpt-6-astra`, high)로, 검토는 래퍼 `codex-review.ps1`(읽기 전용).
- 시험: `tests/*_test.py`, `tests/golden_check.py`(골든 `--write` 금지), web/quick/shim_compat 는 `tests/run_workspace_test.py tests/<이름>.py` 경유, `node tests/*.js`, 브라우저 `E:\AI_mk2\venv-pw\Scripts\python -X utf8 tests\e2e\test_page.py`(27개).
- 엔진을 바꾸면 `tools/build_simpack.py` → 계수 재맞춤(`tools/gen_quick_calib.py --per-content 400` → `tools/calibrate_quick.py --write`, 약 15분) → e2e.
- 문서 문체: 존칭 없이 「했음·하기로 함」, 담백, 참고는 주소만.
