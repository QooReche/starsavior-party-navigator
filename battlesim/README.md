# battlesim — 전투 시뮬레이터 패키지

설계는 `docs/battlesim_design.md`, 모델·가정 설명은 `docs/sim_report.md`, 규칙 교정 기록은 `docs/sim_changes.md`. P1 에서 예전 `tools/sim_damage.py` 를 구조만 나눴고(결과 동일), P2 에서 확인된 게임 규칙으로 교정했다(교정마다 스위치, 아래).

## 구성
| 파일 | 내용 |
|---|---|
| `rules.py` | 피해식 상수·가정(ASSUMPTIONS)·속성 상성·DoT 표·`DEFAULT_OPTS`. 값은 `rules/default.json` 에서 읽음 |
| `rules/default.json` | 불확실하거나 바뀌기 쉬운 수치·규칙 스위치. 항목마다 `value`·`grade`(data/official/community/assumed)·`note`, P2 교정 항목은 `legacy`(교정 전 값)·`source` |
| `starsavior/data.py` | 저장소 루트(`SRC`, 환경변수 `PN_SRC` 로 바꿀 수 있음), `DB`·`get_db`, 이름으로 구원자 key 찾기(`_find_key`) |
| `starsavior/stats.py` | 스탯 계산(데이터북 `sCalc` 재현) |
| `starsavior/parser.py` | 스킬 문장(`ef` 줄) 파서 → `Line`, `Skill`, 구원자 정의 `UnitDef` |
| `engine.py` | 행동 게이지 이벤트 시뮬레이터 `Sim`(기대값), 런타임 개체, 더미 딜러 `DummyDef` |
| `metrics.py` | 개인 지표·파티 시뮬·대표 스테이지·`build_index`(damage_index) |
| `cli.py` | 명령줄(index/stats/party/stage/unit/lines/simulate) |
| `mc.py` | **P3 확률(몬테카를로) 엔진** `Battle`: 양 진영 대칭(적 스킬·쿨·광역·대상 선택, 아군 HP·사망·회복·보호막·도발·수호·피해 감소·피격 반응, 카운터, 리더 속도, 회피), 치명·효과 적중·확률 효과·협공·대상·피해 난수를 실제로 굴림. `support_report`(실행 전 미지원 줄 검사) |
| `api.py` | 재사용 계약 `simulate(party_spec, encounter_spec, options)`(설계 2절) — `battlesim.simulate` 로도 부름 |
| `starsavior/build.py` | **P5 육성 프리셋**: 가이드 DB(`rawdata/guide_app-core.js`)의 구원자별 목걸이·반지·세트·잠재력 코드 + databook 장비 수치 + `rules/builds.json` 가정(부옵·여정·번호 없는 잠재력·클래스 기본값) -> 장비·여정·특수 잠재력(`UnitDef(..., build='none'|'light'|'standard')`), databook 전투력 공식 `unit_power` |
| `rules/builds.json` | 육성 프리셋 가정·예외(사람이 고침). 세팅 없는 신규 구원자는 `use_class_default` 목록만 클래스 기본값, 그 밖은 `BuildError` |
| `starsavior/foe.py` | 적 로더: `rawdata/foe.js` 에서 스테이지 웨이브의 적 `FoeDef`(스탯 10종·스킬·효과 줄·면역), 스테이지 fx 해석, 상태 효과 사전(무작위 효과용) |

`tools/sim_damage.py` 는 호환용 껍데기다. 예전 import 이름(`sd.get_db`, `sd.build_index` …)과 명령이 그대로 동작한다.

## 실행 (저장소 루트에서)
```
python -X utf8 -I tools/sim_damage.py unit 그웬              # 개인 지표 상세
python -X utf8 -I tools/sim_damage.py party professor-m,gwen,fei,amora --stages
python -X utf8 -I tools/sim_damage.py index                  # tools/raw/damage_index.json (tools/update.py 가 호출)
python -X utf8 -I tools/sim_damage.py lines                  # tools/raw/lines.json: 구원자별 파싱된 Line + unparsed 목록
python -X utf8 -m battlesim unit 그웬                         # 패키지로 직접 실행(-I 를 빼야 현재 폴더에서 찾음)
```
### 확률 엔진(P3) — 생존·클리어 확률
```
python -X utf8 -I tools/sim_damage.py simulate --party gwen,fei,professor-m,amora --leader 0 --stage "cosmo/길레/길레 2단계" --runs 200 --out 결과.json
python -X utf8 -I tools/sim_damage.py simulate --spec 입력.json        # {"party": ..., "encounter": ..., "options": ...}
python -X utf8 -I tools/sim_damage.py simulate ... --rules "{\"target_defender_mult\": 4.0}"   # 규칙 민감도
```
파이썬: `from battlesim import simulate; simulate({"units": ["gwen", "fei", "professor-m", "amora"], "leader": 0}, {"stage": "rush/매니저 그레고리/매니저 그레고리 Ⅰ"}, {"seed": 1, "n_runs": 200})`.
입력·출력 형식은 `api.py` 머리말, 규칙·근거는 `rules/default.json` 의 `mc` 절, 설계는 `docs/battlesim_design.md` 9절, 검증은 `docs/sim_p3_report.md`.
- 편성 칸 0·1 = 전열, 2·3 = 후열. 레벨·공명 기본 Lv200·공명10(fixed 모드, 장비·잠재력·여정 없음).
- 결과의 턴은 「모델 기준 턴」(100틱)이고 처치 턴은 클리어한 판만 센다. `unsupported` 의 `gate_ok=false` 면 적 생존 기믹이 빠진 결과라 추천 관문에 쓰지 말 것.
- 이벤트 한도를 넘으면 `EventLimitError` 가 나고 결과를 돌려주지 않는다.
- 기대값 엔진(`engine.Sim`, 웹 화력 지표)은 P3 에서 동결 — 새 규칙은 `mc.py` 에만 넣는다(퇴역 조건은 설계 9절).

### P4 — 추천 연결용 사전 계산·수동 정책 (사전 계산은 2026-10-20 퇴역 → 브라우저 시뮬 `battlesim/web.py`)
- 웹 시뮬은 `sim_worker.js` → `battlesim/web.py`로 실행함. 파일 목록·내용 해시는 `tools/build_simpack.py`로 생성함. 옛 사전 계산 기록은 `docs/sim_p4_report.md`에 보관했음.
- `simulate` 옵션 추가: `run_offset`(판 번호 시작값 — 대표 판 하나만 다시 돌려 타임라인을 얻을 때), `per_run`(판별 [결과, 처치 턴]), `formula_override`(민감도용 공식 상수 임시 교체, 지금은 `COOP_CAP` 만, 끝나면 원복).
- 규칙 `mc.manual_burst`: 수동일 때 노바 버스트를 쓰는 스킬(`any_attack` = 4개 모이면 다음 공격, `ult_only` = 궁극기에만). `opts.nova_pool='unit'`(개인 풀)이 확률 엔진에서도 실제로 동작한다(민감도용).
- 확률 엔진 `nova_policy='heal'`: 오토 스킬 선택을 유지하고 회복·보호막에만 버스트. 슬롯별 노바 효과로 회복·보호막을 추가/강화하는 생존 아군의 액티브가 있으면 그 스킬을 기다리고, 없으면 `hl`/효과 줄로 판별한 일반 회복·보호막에 사용한다. 조건부 효과는 후보에 포함하되 실제 조건은 시전 때 평가한다. 강인도 회복·반응/협공/추가 시전 제외. 기존 auto/manual·동결 기대값 엔진은 불변이며 슬롯별 노바 효과 실행은 heal에만 추가했다. `result.nova_burst`에 전체 판 횟수와 시전자/슬롯별 합계를 제공한다. `tools/ingame_check.py --runs 60 --bs`는 36-36만 heal, 나머지는 auto이며 `--ov`로 덮어쓴다. 회귀 시험: `tests/heal_burst_test.py`.
- 타임라인 항목에 `pos`(편성 칸)·`via`(coop/forced_coop/trigger/reaction/extra)·`nb`(노바 버스트)·`all`·`tgt_side`·`tgt_boss` 가 붙는다(서순 표 재료).
- 시험: `python -X utf8 -I tests/run_workspace_test.py tests/web_test.py`, 브라우저 `tests/e2e/test_page.py`(`docs/PORTING.md` 7절).

### P5 — 육성 프리셋·강인도/브레이크·피해 제한·전투력 보정
- `simulate(..., options={'build': 'standard'})`: 육성 프리셋(기본 'none' = 예전과 같음, 유닛별 `{'key':..., 'build':...}` 도 됨). 브라우저 평균 육성 시뮬은 'standard'를 사용함. 결과 `party.build`·`builds`(구원자별 주옵·세트·잠재력 요약)·`power`(databook 전투력 공식 4명 합)·`power_ratio`(권장 대비 %)·`penalty`.
- 규칙(`rules/default.json` 의 `mc`): `toughness`(on/off, 강인도·브레이크), `toughness_elem`(강인도 상성), `basic_tough`(기본기 강인도 파괴량, 0), `ally_break_gauge`(구원자 브레이크 때 게이지 keep/reset), `power_penalty`(off/model).
- 「피해 제한」은 효과별 표 `mc.DAMAGE_LIMIT`(대미지 브레이크·불사의 육신·바큇살)만 지원, 그 밖은 중요 미지원. 〈불사〉 = 생명력 1 남김.
- 결과 `breaks{ally, foe}`(판당 평균 브레이크 횟수), `unsupported.depth_runs`(연쇄 깊이 한도로 시전을 건너뛴 판 수 — 사전 계산은 1판이라도 있으면 그 팀을 「계산 불가」로).
- 시험: `python -X utf8 -I tests/p5_test.py`(15개, 일부러 깨뜨려 실패 확인 — `docs/sim_p5_report.md`). 설계 = `docs/battlesim_design.md` 11절.

`lines` 의 `unparsed` 는 `reason` 으로 나뉜다: `trigger`(발동 시점 미해석), `effect`(효과 미해석), `condition`(엔진이 모르는 조건 키 — 실행 시 0.5 가중), `skill`(변형·반응 스킬 미반영).

## 회귀 시험(골든)
```
python -X utf8 -I tests/golden_check.py      # 「골든 일치」면 통과(종료코드 0), 다르면 1
python -X utf8 -I tests/rank_check.py        # 골든 대비 순위 변화(구원자·150팀 Spearman, 상위 20 겹침, 처치 턴)
python -X utf8 -I tests/rank_check.py --matrix --golden tests/golden/sim_golden_p1.json   # 교정 하나씩 영향
python -X utf8 -I tests/rules_test.py        # 규칙 스위치마다 뒤집어 기대 방향 확인 + 교정 전 값 = P1 골든 재현
python -X utf8 -I tests/p5_test.py           # P5: 육성 프리셋·스탯 순서·강인도·피해 제한·전투력 보정·새 적 효과 15개
python -X utf8 -I tests/p3_test.py           # 확률 엔진: 대상 가중·도발·수호·보호막·회복·사망·카운터·리더·시드·이벤트 한도 등 31개(codex 2·3차 검토 회귀 시험 포함)
```
구조만 바꾸는 작업은 정확 일치해야 한다. 규칙을 고치는 단계(P2~)는 `rank_check.py` 결과를 `docs/sim_changes.md` 에 남긴 뒤 `--write` 로 골든을 바꾼다(설계 5절). `tests/golden/sim_golden_p1.json` 은 교정 전(P1) 보관본.

## 규칙 스위치 (P2, 상세·근거·영향 = `docs/sim_changes.md`)
| 스위치 | 기본값 | 교정 전 | 뜻 |
|---|---|---|---|
| `coop_trigger` | basic_only | any_attack | 협공은 아군 기본기 뒤에만 |
| `coop_single` | true | false | 공격 1번에 협공 1명(확률 높은 순 기대값) |
| `nova_policy` | auto | manual | 오토 = 노바 버스트 안 씀 / 수동 = 4개면 다음 공격 스킬에 버스트 |
| `nova_pool` | team | unit | 노바 포스 파티 공용(수동일 때만 차이) |
| `debuff_model` | hit_resist | constant | 효과 적중 판정 = 적중 - 저항 +-상성 30%p (constant 는 `debuff_success`) |
| `enemy_resist` | 0.6 | - | 지표용 기준 적 효과 저항(대표 스테이지 보스 중앙값, 가정) |
| `forced_coop_target` | live_atk | stat_atk | 프로페서M 강제 협공 대상 = 버프 포함 현재 공격력 1위 |
| `dot_snapshot` | live | on_apply | 지속 피해를 매 틱 현재 스탯으로 |
| `gear_order` | databook | legacy | 장비 훅 반영 순서(지금 장비 미사용이라 결과 같음) |
| `dmg_reduction` | sum_cap | none | 감소 합(상한 50%), 브레이크는 감소 합 -15%p |
| `forced_coop_slot` | shared | independent | 강제 협공도 협공 1명 자리를 먼저 차지, 추가 시전 기본기에선 강제 협공 없음 |
| `debuff_state` | per_caster | overwrite | 성공 0 이면 상태 불변, 지속 피해 시전자별, 지속 갱신은 성공 0.5 이상일 때만 |
| `gauge_expect` | exact | linear | 적 게이지 증감의 효과 적중 성공률 기대값을 0~100% 경계까지 정확히 |

실행 중 바꾸기: `Sim(..., opts={'nova_policy': 'manual'})`, 또는 `simulate_party(keys, opts={...})`. 지표 전체(`build_index`)는 `opts` 인자로 넘기거나 `battlesim.rules.DEFAULT_OPTS` 를 제자리에서 고친다(`tests/rank_check.py` 의 `apply_rules` 참고, 스탯 캐시 `metrics._CACHE` 도 비울 것). 교정 전 값 모음은 `battlesim.rules.LEGACY_OPTS`.

## 규칙 수치 바꾸기
- 수치는 `rules/default.json` 에서 고친다. 실수는 `1400.0` 처럼 소수점을 지켜 적는다(정수로 바꾸면 출력 JSON 표기가 달라진다).
- 실행 중 실험: 엔진은 `from .rules import BASE_MULT` 로 값을 복사해 쓰므로 `battlesim.engine.BASE_MULT` 를 바꿔야 반영된다. `DEFAULT_OPTS` 는 dict 를 공유하므로 제자리 수정이 반영되고, 보통은 `Sim(..., opts={...})` 로 넘기면 된다.

API의 `n_runs`는 양의 정수만 받음. 입력 오류는 `ValueError`이며 CLI에서만 종료 코드로 처리함.
