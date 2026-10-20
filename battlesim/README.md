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
| `cli.py` | 명령줄(index/stats/party/stage/unit/lines) |

`tools/sim_damage.py` 는 호환용 껍데기다. 예전 import 이름(`sd.get_db`, `sd.build_index` …)과 명령이 그대로 동작한다.

## 실행 (저장소 루트에서)
```
python -X utf8 -I tools/sim_damage.py unit 그웬              # 개인 지표 상세
python -X utf8 -I tools/sim_damage.py party professor-m,gwen,fei,amora --stages
python -X utf8 -I tools/sim_damage.py index                  # tools/raw/damage_index.json (tools/update.py 가 호출)
python -X utf8 -I tools/sim_damage.py lines                  # tools/raw/lines.json: 구원자별 파싱된 Line + unparsed 목록
python -X utf8 -m battlesim unit 그웬                         # 패키지로 직접 실행(-I 를 빼야 현재 폴더에서 찾음)
```
`lines` 의 `unparsed` 는 `reason` 으로 나뉜다: `trigger`(발동 시점 미해석), `effect`(효과 미해석), `condition`(엔진이 모르는 조건 키 — 실행 시 0.5 가중), `skill`(변형·반응 스킬 미반영).

## 회귀 시험(골든)
```
python -X utf8 -I tests/golden_check.py      # 「골든 일치」면 통과(종료코드 0), 다르면 1
python -X utf8 -I tests/rank_check.py        # 골든 대비 순위 변화(구원자·150팀 Spearman, 상위 20 겹침, 처치 턴)
python -X utf8 -I tests/rank_check.py --matrix --golden tests/golden/sim_golden_p1.json   # 교정 하나씩 영향
python -X utf8 -I tests/rules_test.py        # 규칙 스위치마다 뒤집어 기대 방향 확인 + 교정 전 값 = P1 골든 재현
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
