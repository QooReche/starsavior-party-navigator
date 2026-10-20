# battlesim — 전투 시뮬레이터 패키지

설계는 `docs/battlesim_design.md`, 모델·가정 설명은 `docs/sim_report.md`. 지금(P1)은 예전 `tools/sim_damage.py` 를 구조만 나눈 것이라 결과가 완전히 같다.

## 구성
| 파일 | 내용 |
|---|---|
| `rules.py` | 피해식 상수·가정(ASSUMPTIONS)·속성 상성·DoT 표·`DEFAULT_OPTS`. 값은 `rules/default.json` 에서 읽음 |
| `rules/default.json` | 불확실하거나 바뀌기 쉬운 수치. 항목마다 `value`·`grade`(data/official/community/assumed)·`note` |
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
```
구조만 바꾸는 작업은 정확 일치해야 한다. 규칙을 고치는 단계(P2~)는 `--write` 로 골든을 바꾸기 전에 변경 사유를 남긴다(설계 5절).

## 규칙 수치 바꾸기
- 수치는 `rules/default.json` 에서 고친다. 실수는 `1400.0` 처럼 소수점을 지켜 적는다(정수로 바꾸면 출력 JSON 표기가 달라진다).
- 실행 중 실험: 엔진은 `from .rules import BASE_MULT` 로 값을 복사해 쓰므로 `battlesim.engine.BASE_MULT` 를 바꿔야 반영된다. `DEFAULT_OPTS` 는 dict 를 공유하므로 제자리 수정이 반영되고, 보통은 `Sim(..., opts={...})` 로 넘기면 된다.
