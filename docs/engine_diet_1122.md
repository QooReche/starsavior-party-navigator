# 엔진 다이어트 0~1단계 (2026-11-22)

설계: 페이블 상담 «엔진 다이어트»(1안: 묶음 경량화 먼저, legacy 스위치 삭제는 wt-batch 병합 뒤 기준선 위에서 20~30개씩). 이 문서는 5절 단계 계획의 0단계(실측·기준선·태그)와 1단계(묶음 1차 경량화) 결과.

- 태그 `engine-legacy-final` = `ed64b93`(브랜치 `diet` 시작 = 당시 main). 로컬에만 찍었고 push 는 메인이 판단.
- 엔진 코드(`mc.py`·`api.py`·`web.py`)는 건드리지 않았음. `battlesim/rules.py` 는 규칙 파일 경로 대체(아래 1단계)만.

## 0단계 — 실측

도구: `tools/diet_profile.py`(결과 JSON 은 `local/diet_profile.json`, 저장소 밖). Python 3.13.12, 이 PC(16코어) 단일 프로세스.
입력: 파티 `fei·professor-m·emily·wedding-carmen`(리더 0), 화면 옵션(`build: standard`, `rules_override: {power_penalty: model}`, `raw_runs`), 시드 1, `web.run_auto`.

### run_auto 시간(프로파일러 없이, 데우기 뒤 최솟값)

| 케이스 | 1판 ms | 8판 ms | 100판 ms | 판당 ms(100판) |
|---|---:|---:|---:|---:|
| 작전 NOA 1-3 | 2.2 | 10.1 | 137 | 1.37 |
| 달 회랑 FLOOR 100 | 11.3 | 84.0 | 1003 | 10.03 |
| 태양 회랑 FLOOR 250 | 30.2 | 344.9 | 5013 | 50.13 |
| 코스모 길레 1단계(스테이지) | 4.5 | 31.0 | 513 | 5.13 |
| 코스모 시즌 바스커빌 3단계 | 27.0 | 421.4 | 4894 | 48.94 |
| 길드 방어전 Lv1(fire) | 11.8 | 110.6 | 1858 | 18.58 |

1판·8판·100판이 판 수에 거의 비례 — 호출당 고정 비용(파티·적 정의 만들기, `support_report`, `assumptions_used`)은 데운 뒤엔 판 1개 시간보다 작음. 같은 조건 반복 사이 흔들림이 ±5~15%(1판 기준 태양 250 이 30↔50ms)라 1~2% 차이는 이 PC 의 wall 로는 가려지지 않음.

### 진단·기록 비용 비율

cProfile(함수 호출이 잦은 코드를 부풀리므로 상한 쪽 근사), 총시간 대비 cumtime:

| 케이스 | n | support_report | assumptions_used | Battle.log (호출 수) | lines_of | Battle.__init__ |
|---|---:|---:|---:|---:|---:|---:|
| 작전 1-3 | 8 | 1.79% | 0.39% | 0.02% (24) | 4.65% | 8.03% |
| 작전 1-3 | 100 | 0.13% | 0.03% | 0.01% (300) | 4.88% | 7.07% |
| 달 회랑 100 | 8 | 0.45% | 0.05% | 0.00% (61) | 3.67% | 1.46% |
| 태양 회랑 250 | 8 | 0.07% | 0.02% | 0.01% (314) | 3.35% | 1.47% |
| 코스모 길레 1 | 8 | 0.49% | 0.12% | 0.00% (8) | 3.43% | 1.64% |
| 코스모 시즌 바스커빌 3 | 8 | 0.01% | 0.01% | 0.00% (188) | 3.05% | 1.15% |
| 길드 Lv1 | 8 | 0.03% | 0.03% | 0.01% (131) | 3.92% | 1.38% |

횟수 × 단가(timeit) 추정, 판당 wall 대비:

| 케이스 | self.mc 읽기/판 | 읽기 비용 | rule_hits 증가/판 | rule_hits 비용 | log 호출/판 | log 호출 비용 | lines_of 모드 튜플 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 작전 1-3 | 1,253 | 1.2% | 37 | 0.14% | 3 | 0.04% | 1.1% |
| 달 회랑 100 | 12,996 | 1.7% | 449 | 0.23% | 8 | 0.01% | 1.2% |
| 태양 회랑 250 | 52,392 | 1.4% | 1,817 | 0.18% | 39 | 0.01% | 0.9% |
| 코스모 길레 1 | 3,715 | 1.0% | 141 | 0.14% | 1 | 0.00% | 0.8% |
| 코스모 시즌 바스커빌 3 | 40,692 | 1.1% | 1,933 | 0.20% | 24 | 0.01% | 0.8% |
| 길드 Lv1 | 16,164 | 1.1% | 561 | 0.15% | 16 | 0.02% | 1.0% |

단가: `self.mc[k]` 13.2ns, `rule_hits[k] += 1` 51ns, 타임라인 꺼진 `log(...)` 호출 188ns(가드로 막으면 13ns), `lines_of` 의 10개 값 튜플 650ns.
rule_hits 증가 수는 판 끝 `sum(rule_hits.values())`(일부는 `+= len(...)` 이라 실제 문장 실행 수보다 큼 = 비용 상한).

변형 실측(`mc.py` AST 변환 사본, `local/diet_variants/`, 100판 6케이스 합, 2바퀴 번갈아 최솟값): 원본 복사 13,013ms, log 가드 26곳 13,379ms(+2.8%), rule_hits 151곳 삭제 13,016ms(0.0%), 둘 다 13,166ms(+1.2%). 케이스별로 −14%~+8% 로 흩어져 **효과가 잡음보다 작음**. 둘 다 바꾼 사본도 기준선 36건과 바이트 일치(결과 불변 확인).

**판정**
- 설계의 «판당 −3~8%»는 실측이 받쳐 주지 않음. 진단 몫 합계는 약 1.5~2.5%: self.mc 읽기 1.0~1.7%(스위치를 지워도 남는 분기는 계속 읽으므로 줄어드는 건 그 일부), lines_of 튜플 약 1%, rule_hits 0.14~0.23%, log 0.04% 이하.
- `log()` 호출부 가드(3단계)는 타임라인이 꺼진 판에서 log 가 판당 1~39번만 불려 이득이 거의 없음. 하려면 결과 불변(변형 실측에서 확인)이라 위험은 없음.
- `support_report`·`assumptions_used`(호출당)는 판 수가 적고 전투가 짧은 작전 8판에서만 약 2%, 나머지는 0.5% 이하. wt-batch 일괄 API 쪽에서 다룰 일로 넘김(이번 범위 밖).
- 가장 싼 후보는 `lines_of` 의 모드 튜플(판마다 수백 번 같은 값을 다시 만듦)을 전투 시작 때 한 번 만드는 것 — 약 1%, 결과 불변. 3단계에 log 가드 대신 넣을지 메인이 판단.
- 판당 시간 대부분은 전투 계산 자체. 속도는 다이어트보다 일괄 API·Rust 쪽이 몫이 큼.

## 0단계 — 결과 불변 기준선

- 도구 `tools/diet_baseline.py`, 고정값 `tests/golden/diet_baseline.json`, 시험 `tests/diet_baseline_test.py`.
- 케이스 36 = 콘텐츠 6(작전 NOA 1-3·달 회랑 100·태양 회랑 250·코스모 길레 1단계·코스모 시즌 바스커빌 3단계·길드 방어전 Lv1 fire) × 파티 2(A `fei·professor-m·emily·wedding-carmen`, B `wedding-carmen·ceres-sun-supporter·amora·tyria`, 표준 육성·계정 자료 없음) × 시드 1·2·3, 각 8판.
- 케이스마다 해시 4개(sha256 앞 20자, `json.dumps(sort_keys, ensure_ascii=False, 구분자 고정)`): `api.simulate` 의 `raw_runs`·`runs`(per_run)·결과 전체(`runtime_ms_per_run` 만 뺌), `web.run_auto` 문자열(화면이 받는 그대로).
- 진행도 0 인 케이스 없음, 클리어 0%·100%·중간이 모두 있음(시험이 확인). 규칙 하나(`turn_gauge`)를 바꾸면 파티 A 시드 1 의 6케이스가 모두 어긋남을 확인.
- 프로세스마다 문자열 해시 시드가 달라도 같은 값(4회 실행 바이트 일치).
- 다시 고정은 엔진 결과가 «의도적으로» 바뀐 커밋에서만(`--write`, 사유는 HISTORY). 다이어트 단계는 고치지 않고 통과해야 함.

### `mc_cache_test` 의 `_KEEP` 재고정 설계(4단계 때 실행, 이번엔 안 함)

현재 `_KEEP` 은 legacy 값 약 100개를 `rules_override` 로 넘겨 세 해시(`_H_GWEN_MULTIWAVE`·`_H_PM_GWEN_MULTIWAVE`·`_H_GWEN_RNG_STREAMS`)를 고정함. `simulate` 는 모르는 규칙 키를 `ValueError` 로 막으므로(`api.py` 의 `unknown_keys`) 스위치를 지우면 해시가 바뀌기 전에 키 오류로 깨짐.

1. 4단계 첫 묶음 전 커밋: 같은 세 시나리오를 `rules_override` 없이(기본 프로필, `_KEEP_FORMULA` 의 COOP_CAP 0.30 은 공식 상수라 유지) 돌린 해시 `_H_*_DEFAULT` 세 개를 추가. 이 커밋에서 옛 `_KEEP` 해시 셋과 새 기본 해시 셋이 둘 다 통과해야 함.
2. 각 삭제 묶음: 지운 스위치를 `_KEEP` 에서도 지우고, 옛 해시가 바뀌면 그 시험을 «legacy 비교는 태그 `engine-legacy-final` worktree 에서»로 옮겨 적고 삭제. 기본 해시 셋과 `diet_baseline` 은 바뀌면 안 됨.
3. 모든 묶음이 끝나면 `_KEEP` 에는 남긴 스위치(ENGINE_MC_KEYS·화면이 넘기는 값·user/assumed 등급 등)만 남김.

## 1단계 — 묶음 1차 경량화

- `tools/build_simpack.py`
  - 파이썬 제외 목록 `EXCLUDE_PY` 에 `battlesim/metrics.py`(11,896B)·`battlesim/quick.py`(9,412B) 추가. 진입점(작업자는 `battlesim.web.run_auto` 와 `battlesim.api.Battle` 만 가져옴, `sim_worker.js`) → `api` → `mc` 경로에서 import 안 됨: 두 파일이 없는 묶음 폴더에서 36케이스가 돌고 `sys.modules` 에도 없음(`test_pack_same`), 실제 Pyodide 페이지 시험도 통과.
  - 규칙 파일은 축약본 `battlesim/rules/default.min.json` 을 실음(빌더가 default.json 에서 다시 만듦). 항목마다 `value`·`grade`·`kind`, `note` 는 가정 등급(`api.ASSUMPTION_GRADES`) 12항목만. `source`·`alt`·`legacy`·나머지 note·`_note` 는 뺌.
- `assumptions_used`(`api.py`)는 가정 등급 항목의 note 를 결과에 실음 → 그 note 만 남겨 `api.simulate` 결과 전체가 원본 규칙 파일과 바이트 같음. `web.run_auto` 는 `assumptions_used` 를 화면에 내지 않음. 축약본에서 note 를 다 빼면 `test_pack_same` 이 실패함을 확인(일부러 깨뜨려 봄).
- `battlesim/rules.py` `load_rules`: `default.json` 이 없으면(브라우저) `default.min.json` 을 읽음. PC·도구는 그대로 원본을 읽음. 브라우저에서 `LEGACY_OPTS`·`LEGACY_FORMULA` 는 비지만 엔진 경로는 안 씀.
- 화면·작업자(`sim_worker.js`)는 바꾸지 않았음 — 작업자는 매니페스트 목록 그대로 받아 같은 경로에 씀.

### 묶음 크기 전후(`sim/manifest.json`, Pyodide 런타임 `lib/pyodide` 13,781,345B 는 별도·불변)

| | 파일 수 | 바이트 | gzip(6) 합 |
|---|---:|---:|---:|
| 전(ed64b93) | 60 | 7,625,097 | 1,004,395 |
| 후 | 58 | 7,424,409 | 936,600 |
| 차 | −2 | −200,688 (−2.6%) | −67,795 (−6.7%) |

규칙 파일만: 200,339B(gzip 65,472) → 20,552B(gzip 5,994). 매니페스트 ver 가 `d4bb1b4df2a2` → 바뀌어 화면의 이전 시뮬 결과 캐시는 무효(설계 «위험: 캐시 무효»).
남은 큰 몫(2단계 후보): `rawdata/databook_main.json` 2,805,613B, `rawdata/foe.js` 1,954,851B, `rawdata/guide_app-core.js` 427,861B, `data/foe_spawn.json` 388,120B, `battlesim/mc.py` 369,408B, `battlesim/engine.py` 59,915B.

### 확인

- `tests/diet_baseline_test.py` 3건: PC 기준선 일치, 축약본이 최신, 매니페스트 파일만 복사한 폴더(Pyodide 조건)에서 기준선 36건 바이트 일치.
- 기준선 출처 대조: 태그 `engine-legacy-final`(ed64b93) 원본을 `git archive` 로 풀어 그 엔진·원본 default.json 으로 다시 계산 → 36건 전부 고정값과 같음(기준선은 수정 전 엔진 결과).
- e2e(`tests/e2e/test_page.py browser_sim`, 실제 Pyodide): `test_browser_sim`(3팀, 브라우저 결과 = PC 파이썬 결과)·`test_browser_sim_blocked` 통과. `sim_auto_and_override` 도 통과.
- 전체 `tools/run_tests.py --rebuild`(공용 잠금): 통과 264 / 실패 1, 건너뜀 6(환경). 실패 `md_control_chars_test`는 `HANDOFF.md:71` 의 제어문자(`work\allowlist\fable_…` 경로의 `\a`·`\f`)로 ed64b93(main)부터 있던 것 — 이번 변경과 무관, 고치지 않음. 재빌드 뒤 매니페스트 변화 없음.
