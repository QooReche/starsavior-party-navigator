# 전체 리뷰 반영 기록

기준: main 8342226 / 작업: chore/cleanup, 2026-10-22.
리뷰 원문 3개를 먼저 읽고 실제 구현·호출부를 확인했음. 비공개 자료를 복사하지 않았고 커밋·푸시하지 않았음.

## 반영했음

- 엔진 1: 아군 최초 전투·후속 웨이브 시작 모두 `lines_of()`를 사용함. 물폭탄 면역 적에게도 설명문 기준 표식이 적용되는 회귀를 추가했음.
- 엔진 2·웹 2: manifest를 생성기로 갱신함. 파일 목록·전체 바이트·경로+내용 SHA-256을 독립 재계산하는 시험을 추가했음.
- 엔진 3: `unit_def`는 DB 객체를 키에 포함함. `gloss`는 원본별로 분리하고 원본 참조도 보유하여 id 재사용을 막음.
- 엔진 4: `n_runs`는 bool·문자열·실수·0·음수를 거부함. 구원자 검색은 `ValueError`, 종료 처리는 CLI에서만 수행함.
- 웹 1·3: 중첩 장비·전술·스킬·건틀렛 필드를 검증함. 일반·고정 레벨 계산을 먼저 확인하고 렌더링 뒤 저장함. 실패는 기존 저장값을 보존함. 저장 실패면 메모리 적용과 「저장 안 됨」을 구분함. 잘못된 기존 JSON도 오류 안내·지우기·다시 불러오기로 복구함.
- 도구 1: 원본 전체 수신·구조 검사 후 파일별 원자적 교체함. SSD가 비거나 형식이 틀리면 실패하고 기존 파일을 보존함.
- 도구 2: 공개 스킬·내 정보 설명 생성기를 업데이트에 연결함. `--no-html`도 두 자료를 갱신함. HTML 빌더는 다른 출력 경로를 만들 때 저장소의 설명 JSON을 수정하지 않음. 비공개 성장표·슬롯·전투 어댑터는 명시 입력으로 별도 생성하는 단계임.
- 도구 3·5: 추출 끝 표식이 없으면 오류로 종료함. E2E 필터 0건은 브라우저 실행 전에 실패함.
- 엔진 5·도구 4: 표본을 안정 정렬한 뒤 분할함. 빈 표본·단일 판정 그룹·빈 검증 집합·생성 실패는 성공 점수를 내지 않고 실패함.
- 엔진 6: 최종 더미 구현을 클래스에 둠. 재수출되는 `dummy_dmg_hook`, `_patch_dummy` 호환 이름은 유지함.
- 세 리뷰 Top 10: 미사용 함수·선언·해시·인자를 제거하고 모든 호출부를 정리했음. `EL/ELKO`, `POWK/_POWK`를 정리했음. 빌더 읽기 재사용·UTF-8 바이트 로그·주석을 수정했음.
- 웹 10: 동일한 NST 표와 두 뷰의 esc를 `ui_shared.js`로 공용화함. 능력치 합산 순서는 유지했음.
- 엔진 12·웹 7·도구 8: Python 텍스트 산출물은 `battlesim/fileio.py`의 UTF-8·LF·동일 디렉터리 임시파일→교체로 통일함. Node 추출기는 `tools/fileio.js`를 사용함. 비공개 경로는 인자→`STARSAVIOR_STATIC`이며 하드코딩을 제거함. 감사 출력은 명시 인자로 받음.
- 도구 6·7·9: 작업자별 quick 로드 캐시, Python `DEF_K` 공용 참조, 검증하는 IDLE 도우미를 적용함. 독립 진단 도구에 보관 목적·입력·근거를 명시했음.
- 웹 6: manifest HTTP 상태 검사, 최대 5개 동시 다운로드, 모든 파일 기록 후 Python import를 수행함.
- 웹 5 일부: 숨은 그래프는 첫 표시 때 만들고 변경 때 갱신함. 초기 이중 그리기를 제거했음.
- 엔진 13·웹 12·도구 10: 낡은 명령·입력 위치·다운로드 크기·Windows 시험 안내를 수정함. 기존 HANDOFF 전체를 docs/HISTORY.md로 내용 삭제 없이 이동했음.

## 반영 안 함과 이유

- 엔진 7·웹 4는 사용자 지정대로 보류했음. 정의 수명·난수 순서·후보 동점 순서를 보존할 후속 시험이 필요함. HANDOFF의 남은 것에 기록했음.
- 웹 5의 Cytoscape 지연 로드·데이터 분리는 이번 범위 밖임.
- 템플릿 esc는 null·작은따옴표 처리 의미가 두 뷰와 달라 합치지 않았음.
- 도구 7에서 지목한 `gen_quick_calib.py:27`은 우선순위 함수이며 방어 상수 중복은 없었음. 실제 중복인 빌더·Python quick 계산만 DEF_K를 참조하도록 했음. JS 숫자는 의도된 Python↔JS 구현 쌍의 동일 값으로 유지함.
- legacy·보존 스위치, rawdata, break_ref, 호환 재수출 API는 삭제하지 않았음. 규칙 설명값 구분은 문서의 후속 정리 후보임.
- 전체 원본 재수집·비공개 가공·실제 계수 재맞춤은 실행하지 않았음. 공개 고정 자료와 합성 입력으로 회귀를 검사했으며 기존 quick 계수는 보존했음.

## 검증

- 새 회귀: `tests/cleanup_test.py`, `tests/cleanup_test.js`. 실패 시 원본 보존, API·캐시·manifest·안정 분할·업데이트 단계·저장 순서·복구·그래프 생성·Worker 동시성/완료 장벽을 검사함.
- 구현을 의도적으로 망가뜨린 30건 모두 해당 시험이 실패함을 확인하고 원복했음. 변이 시험 후 Python 바이트코드도 지우고 다시 검증했음. 상세 결과는 local/cleanup-checks/mutations.json에 남김.
- 골든 수치: 구원자 64명·파티 150팀·스테이지 10팀 일치했음. 저장 당시 원본 입력 해시 차이 경고는 있으나 이번 원본·골든 변경은 없음. `--write`는 사용하지 않았음.
- E2E: 지정 가상환경으로 실행했으나 Playwright 파이프 생성에서 `PermissionError [WinError 5]`가 발생했음. 샌드박스 밖에서 Claude가 실행해야 함.
- 크기 실측(비압축·이미지 제외): 초기 HTML+quick+화면 JS 3,235,320바이트(약 3.24MB), 시뮬 추가 엔진·자료 약 4.79MB + Pyodide 핵심 5파일 13,780,118바이트(약 13.78MB). 기존 「시뮬 약 14MB」는 총 원본 크기로는 맞지 않아 약 18.57MB로 수정했음. 실제 전송량은 압축·캐시에 따라 달라짐.
- 최종 Python 23개 파일(골든 포함), JS 10개 파일이 종료 코드 0으로 통과했음. web·quick·shim_compat는 run_workspace_test.py를 경유했음. 실행 도우미 run_workspace_test.py 자체는 단독 시험 대상이 아님.
- `myinfo_combat_test.py`의 비공개 표 재생성 대조 1건은 STARSAVIOR_STATIC 미설정으로 건너뛰었음. 공개·합성 회귀는 통과했음.
- 추천 동일성은 `tests/reco_parity_test.py`에서 실제 페이지 함수와 Python을 3개 콘텐츠 × 3개 보유 조건으로 대조했음. 상위 10팀 조합·순서·점수가 일치했음. 기존 내 정보 능력치·quick Python↔JS 시험도 통과했음.
- index.html과 manifest를 최종 재생성했음. manifest: 25파일, 4,793,664바이트, 버전 `1072adeff857`. `tools/build_skills.py --check`, `git diff --check`도 통과했음.
- 원본 rawdata·생성 data·골든·rules/default.json은 변경하지 않았음. HISTORY 끝에 옛 HANDOFF 전체가 보존되었음을 Git 원문과 대조했음.

## 지연 로드·근거 분리 (cleanup-cy, 2026-10-23)

기준: cleanup 커밋(chore/cleanup 마지막) / 작업: cleanup-cy 브랜치.

### 반영했음

- 웹 5(잔여): Cytoscape(373KB)를 정적 태그에서 제거하고 `loadCy()`(Promise 캐시, 실패 시 캐시 초기화·재시도 가능)로 지연 로드함. `drawGraph`는 cytoscape 미정의 시 loadCy().then(drawGraph)로 분기하며, 로드 중 중복 호출이어도 스크립트 주입 1회·cytoscape() 생성 1회를 보장함.
- 데이터 분리: D.syn의 e(근거 2줄, 270KB)를 data/syn_detail.json으로 분리함. 빌드가 내용 해시 URL(synDetailUrl)을 D에 넣고, 선 탭 시 fetch 후 표시(로딩 중 문구·실패 안내 포함)함. r(이유)는 D.syn에 유지함.
- setWhy: setTimeout 제거, drawGraph 직접 호출. cy.resize/fit는 drawGraph 완료 뒤 setTimeout(50ms)으로 이동.
- lib/cytoscape.min.js도 내용 해시 URL(cytoUrl)로 캐시 무효화 지원함.

### 크기 실측(비압축·이미지 제외)

- 이전 index.html: 2,033,497바이트, 초기 전송(HTML+Cytoscape+quick+화면 JS): 약 3.61MB.
- 이후 index.html: 1,760,300바이트(-273KB), 초기 전송: 약 2.53MB(-1.08MB 중 Cytoscape 0.37MB + e 0.27MB).
- data/syn_detail.json: 270,641바이트(선 탭 시만 요청).

### 검증

- 새 회귀: cleanup_test.js graph()를 async로 교체해 지연 로드 동작 7개 항목(첫 표시 전 미주입·첫 표시 1회 주입·중복 호출 1회 생성·재사용·dirty 재생성·실패 메시지·promise 초기화) 검사함.
- cleanup_test.py에 test_html_cleanup_checks 추가: 생성 HTML에 정적 cytoscape 태그 없음, D.syn에 e 없음, syn_detail.json 길이·순서·내용 원본 대조, URL 해시 일치 확인함.
- 새 시험 의도적 오염 1건(assertNotIn → assertIn) 후 실패 확인하고 원복했음.
- e2e: tests/e2e/test_page.py에 test_graph_evidence 추가(근거 보기 켬 → 그래프 → 선 탭 → syn_detail 로드·캐시 확인). Playwright 환경 외부에서 실행 필요.
- Python 14개(cleanup_test.py), JS 10개, reco_parity_test, run_workspace_test/web_test 전부 통과했음. 추천 점수·순서 불변.

## 추가 완료 (2026-10-23, feat-rules)

- MC 규칙 설명값 구분(커밋 a176872): `rules/default.json` mc 절 4개 항목(`enemy_skill_ai`, `caster_death`, `wave_carry`, `break_skill_model`)에 `"kind":"note"` 추가. `rules.py` 에 `MC_NOTE_KEYS` frozenset 신설, `MC_OPTS` 에서 제외하되 `MC_RULES`·`assumptions_used` 출력 유지. `api.py` `unknown_keys` 검사 호환. `toughness_elem` 의미 없는 `"legacy"` 제거. 일관성 시험 6개 추가. 골든 결과 변화 없음.
- MC 의미 해석 캐시(커밋 a9dbdb4): `Battle.__init__`에 `semantic_cache=None` 추가, `lines_of`에서 공유 캐시 우선 조회/기록(is-check 무효화). `api._simulate` 에서 런 루프 앞 `semantic_cache={}` 생성·전달. 전역·모듈 캐시 없음, 호출 간 격리 보장. 시험 8개(`mc_cache_test.py`) 신설 — 해시 고정, 결과 동일, 무효화, 오염 감지. 골든 결과 변화 없음.
