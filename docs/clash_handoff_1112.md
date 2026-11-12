# 격전 의뢰(Onslaught Quest) 반영 인수인계 — 2026-11-12 게임 PC → 작업 PC

데이터북에 아직 없는 신규 콘텐츠 «격전 의뢰»(11/12 04:00 ~ 12/03 04:00, 보스 3종 × 6단계 = 18스테이지)를 **PC 클라 표(정답지)에서 직접** 만들어 엔진·화면에 붙였음. 사용자 방침: 정확한 정보는 PC 클라 디컴파일·표 기준, 확인 못 한 것은 추측하지 않고 클라에서 찾을 것.

## 한눈에

| 항목 | 상태 |
|---|---|
| 스테이지·스탯·배치·해금·소환 데이터 | 완료(클라 표 → `data/foe_clash.json`) |
| 스킬 효과 줄 변환 | 완료 — 미반영 SE 0건, 옛 판(데이터북에 있는 같은 계열 보스) 재현 스킬 63/63·줄 134/134·상태설명 78/78 일치 |
| 엔진 연결(로더 병합·battle_end·소환·스폰) | 완료 — 18스테이지 시뮬 실행 확인(`simulate({'units':[…]}, {'stage':'clash/<탭>/<이름>'})`) |
| 화면 연결(콘텐츠 목록·기간 게이트·장비 탐사와 같은 «정상 레벨») | 완료 — 실제 Pyodide 결과 카드·종료 게이트 확인, `local/shots/clash.png` |
| 퍼세스 «판별» 강제 협공 | 완료 — AutoTargetId 52 변환·적 forced_coop 실행, 기본 on / legacy off |
| 실제 플레이·영상 대조 | **없음** |

## 데이터 흐름

```
비공개 static-data/tables (클라 표, 빌드 26610546)
  └ tools/build_foe_clash.py --static <static-data>   → data/foe_clash.json (조각: u·s·x·g + aux·boss_kill·period·unmodeled·check)
      └ battlesim/starsavior/foe.py  load_extra()/merge_extra()  (foe.js 뒤에 덧붙임, 조각 안 인덱스는 «조각 내부 0 기준» + 오프셋)
          ├ load_foe()  → FoeDef·stage_waves 가 그대로 읽음(콘텐츠 키 'clash')
          ├ spawn_flags()/foe_summon()/battle_end()  → aux·boss_kill 병합(extra_aux/extra_boss_kill)
          └ tools/build_foe.py → data/foe_stages.json 에 'clash' 콘텐츠 포함 → build_party_html.py (CONTENT_META['clash'])
```
- 데이터북 `foe.js` 가 같은 콘텐츠 키(`clash`)를 반영하면 `merge_extra` 가 조각을 **자동으로 쓰지 않음**(데이터북 우선). 그때는 조각 값과 데이터북 값을 대조(레벨·전투력·스킬 수치)한 뒤 `data/foe_clash.json`·`tools/build_foe_clash.py` 를 정리할 것.
- 재생성: `python -X utf8 -I tools/build_foe_clash.py --static <static-data>` → 이어서 `build_foe.py`, `build_foe_spawn.py`·`build_foe_summon.py`·`build_foe_auto.py`·`build_foe_react.py`·`build_battle_end.py`(각 `--static`) → `build_quick_data.py` → `tools/run_tests.py --rebuild`.
- 시험: `tests/foe_clash_test.py`(스키마·옛 판 재현율·스탯 독립 계산·18스테이지), `tests/clash_runtime_test.py`(실제 로더·소환·강제 협공·보스 처치·행동 루프), `tests/clash_ui_test.js`(생성 목록·브라우저 자료·정상 레벨·기간 경계), `tests/e2e/test_page.py test_clash`(실제 Pyodide).

## 게임 PC에서 건드린 파일(공개 저장소)

- 새 파일: `tools/build_foe_clash.py`, `data/foe_clash.json`, `tests/foe_clash_test.py`, 이 문서.
- 엔진: `battlesim/starsavior/foe.py`(`load_extra`·`merge_extra`·`extra_aux`·`extra_boss_kill`, `spawn_flags`·`foe_summon`·`battle_end` 병합, `FoeDef` 미반영 효과 기록), `battlesim/mc.py`(조건 키 «대상 강화효과 개수 이하» 추가 = 대상 강화 효과 수 ≤ N·0개 포함, 지원 보고에 «격전 의뢰 효과 미반영» 출력), `battlesim/starsavior/myinfo_stats.py`·`myinfo_stats.js`(`clash`→normal 레벨).
- 빌더: `tools/build_foe.py`(조각 병합), `tools/build_foe_spawn.py`(`candidates()` 에 격전 의뢰 BattleStrID 규칙).
- 화면: `build_party_html.py`(`CONTENT_META['clash']`, `boss` 플래그, `seasonPeriod`), `party_reco.py`(`FOE_KEYS`), `season_gate_ui.js`(`SEASON_KEYS` 에 clash — 기간 끝나면 «미오픈»), `star_link_ui.js`.
- 규칙 메모: `battlesim/rules/default.json` `enemy_hit_buff_cmp` 에 클라 근거 추가(기본값 `le` 가 클라와 같음, 값 변경 없음).
- 이 변경으로 `data/foe_stages.json`·`foe_spawn`·`foe_summon`·`battle_end`·`index.html`·`sim/manifest.json` 등 생성물이 바뀜.

## 클라에서 확인한 것(근거)

- 스테이지·보스·스킬 해독 전체와 근거 표 위치: 비공개 `starsavior-static-data` `analysis/clash_1112.md`·`clash_1112_se.md`(SE 조건 ID·공식 설명문)·`clash_1112_buffs.md`(버프 정의). 해독 스크립트는 비공개 저장소 `tools/decode_clash_se.py`(SE 해독표)·`tools/diff_clash_variants.py`(6변형 비교) — 공개 저장소 작업 폴더에서 `python -X utf8 -I <스크립트> <src 루트> <static-data 루트> [출력 md]` 로 실행(`tools.tables.jsonc` 사용). `SkillLevelGroup.SkillLevelSE` 목록 기준(이름 접두 매칭은 번호 없는 이름·클라 오타 `SPEICIAL` 을 놓침).
- 조건 `BuffCountLess N` = 개수 ≤ N(0개 포함): `NKM.Templets` 43328 부근, `TargetPositiveBuff` 는 대상 강화 효과 수를 세는 조건(42752). → 웬디고 기본기 빙결(조건 2161)을 «대상 강화효과 개수 이하: 1» 로 변환.
- 변형 유닛 `_02~_06` 은 `m_listSkill` 로 `_01` 스킬을 그대로 쓰고 퍼세스만 특수기가 `_0N_SPECIAL`(소환 그룹 1301~1306 만 다름).
- 레벨 고정 없음: `BATTLE_STAT_APPLY_TEMPLET` 에 격전 의뢰 장면이 없음(장비 탐사·일일과 같은 정상 레벨).
- 기간은 클라 표에 없음(서버 INTERVAL). 공지·게임 화면 기준 11/12 04:00 ~ 12/03 04:00(UTC+9)을 `data/foe_clash.json` `period` 에 직접 기록.

## 남은 일 처리 결과 — 2026-11-12 작업 PC

근거 줄은 모두 비공개 `starsavior-static-data/decompiled/` 빌드 26610546 기준. `NKM`·`NKM.Templets`·`Star.Templets`·`NKC`는 각각 `<이름>/<이름>.decompiled.cs`임.

1. **완료 — 퍼세스 판별 강제 협공.** `build_foe_clash.py`에서 효과 줄 변환, `build_foe_auto.py`에서 AutoTargetId 52와 자신 제외를 연결했음. NKM:7143-7186은 자신 제외 후 순서 있는 우선 필터를 적용하며, 필터 결과가 0명이면 이전 후보를 유지하고 성공 결과가 1명이면 중단함. 따라서 세 조건의 단순 AND로 구현하지 않았음. NKM:7535-7545는 특정 버프 제외, 7572-7574는 현재 공격력 최고, 7754-7763·7901-7912는 격파·기절·수면 제외임. NKM:5294-5298의 대상 플래그와 15913-15950·16073-16100의 협공 후보·기본기 사용 검사를 기존 `forced_coop` 경로로 재사용했음. `mc.foe_forced_coop=on`(legacy off), 일반 적 협공은 확장하지 않았음. 변환 미반영 0건, 지원 보고에서도 사라졌음.
2. **미확인·판단 필요 — 패배 제한 턴 수치.** NKM:538-560·638-668·768-803에서 전역/웨이브/적 행동 제한과 패배 판정을 찾았음. 그러나 제한값 필드(`OBF_31827`·`OBF_32696`·`OBF_29861`)에 격전 의뢰 값을 넣는 경로는 배포 클라에서 찾지 못했음. Star.Templets:8115는 `LimitTurn` 미지정 시 0, 격전 전투 18행은 미지정임. 별 미션 65·60을 패배 제한으로 바꾸지 않았음. `max_turns=50` 유지했음. 이는 시뮬 시간 상한이며 클라 전역 행동 턴 50을 확인했다는 뜻은 아님. 수치 확정은 서버 입력 또는 게임 PC 대조가 필요함.
3. **완료 — AddStatData 순서, 계산 유지.** NKM.Templets:37860·42002에서 스폰/소환 AddStatData를 읽음. NKM:2350-2377·18935-18945에서 1단 입력으로 전달하고, 19150-19176에서 레벨 성장 합산, 18784-18824·18878-18903에서 `(기본+고정 가산+성장)×1단 비율 → 2단 패시브/장비 → 3단 전투 버프` 순서로 계산함. 격전 의뢰의 보스·소환병은 현재 `foe_stats`의 `(b+gw×(L-1))×(1+AddStatData%)`와 맞았음. 소환/배치 유닛은 NKM:2215·19078-19089에서 구원자 스타링크 레벨 보정을 사용하지 않음. 일반 유닛의 패시브·버프 2/3단 분리라는 기존 전역 과제는 이번 범위에서 변경하지 않았음.
4. **완료 — 버전 업그레이드 5%, WeakAdjustData 표시용.** Star.Templets:29274-29280은 Stats와 BuffDesc를 별도 필드로 읽고, NKM:4895-4905·6072는 SE Stats로 버프 스탯을 덮어씀. NKM:3885-3893·2371·18947-18951로 최종 3단 버프 입력에 연결됨. NKC:562000-562010은 BuffDesc를 설명문에만 사용함. 표 `SE_TEMPLET_SKILL_2.json:34664-34684`의 500을 따라 중첩당 5%·최대 5를 유지했음(설명문 @@3와의 불일치는 표 자체에 남아 있음). WeakAdjustData는 Star.Templets:8119-8128·8026에서 추천 속성 목록으로 읽고 NKC:65990-66006 `NKCBattleRecommendAdjustViewer`의 아이콘 표시만 소비함. 추가 피해 배율을 넣지 않았음.
5. **완료 — 전용 시험·실제 화면.** 실제 로더의 조각 유무/데이터북 우선·인덱스 오프셋·부가 자료 on/off, API의 boss_kill 연결·소환 0/4칸·최대 2명, 정상 레벨, 3탭×6단계, 시작/종료 경계와 종료 시 «미오픈»을 검사했음. e2e에서 실제 Pyodide 결과 카드 확인, 스크린샷 `local/shots/clash.png`(합성 계정) 저장했음. 발견한 연결 누락 2건을 고쳤음: `build_simpack.py`의 `foe_clash.json` 누락, `data/quick.json`의 clash 자료 누락(없으면 시뮬 버튼도 안 나옴). quick 재생성 결과는 clash 18곳만 추가됐고 기존 st·sv·계수·보정값은 동일했음.
6. **완료 — MC 이벤트/timeline 점검.** 공개 표준 육성 4명(gwen·fei·professor-m·amora), seed 3, 각 3단계에서 실제 `Battle.run()`을 실행했음. 원본 로그·효과 관찰은 `local/clash_timeline.json`, 재현 스크립트 `local/clash_trace.py`. 게임 실측 로그가 아닌 시뮬 로그임.
   - 모티베이터: 재충전→포착→포착→재충전→침입자 청소. 저항 장막 보호막 생성, 버전 업그레이드 3중첩까지 관찰했음.
   - 웬디고: 서리 지진→차가운 고통→차가운 고통→서리 지진→눈보라를 가르는 포효. 혹한의 기운 8중첩·혹한의 서리 부여를 관찰했음.
   - 퍼세스: 소집→판별→판별→판별→소집. 병졸 강제 협공 1회, 방위 10중첩·퇴적 7중첩까지 관찰했음. 해당 판은 궁극기 사용 전 종료됐으므로 궁극기까지 관찰했다고 보지 않았음.
   - 퍼세스 추가 표본: 오래 버티는 합성 표적으로 소집→판별×3→소집→제거(궁극기)→판별×2→소집→판별→제거를 확인했음. 진행도 >0·미지원 0, 강제 협공도 반복 발동했음. 표준 육성/게임 실측과 구분해서 `local/clash_perses_trace.py`·`local/clash_perses_timeline.json`에 저장했음.
   - 세 표본 모두 진행도 >0·미지원 기록 0이었음. 순서·장막·중첩·협공은 전용 시험에서도 경로 통과를 검사함.
7. **완료 — 규칙 없는 보스의 오토 기본 순서 확인.** NKM.Templets:28901-28906의 공통 기본 배열은 궁극기→특수기→기본기, Star.Templets:33807·34120-34125는 기본 배열을 사용하다 SkillOrderList가 있으면 덮어씀. NKM:7090-7114에서 이 배열을 순회해 사용 가능한 액티브를 선택함. 별도 규칙 없는 격전 보스의 엔진 기본과 같음. 시작 궁극기 쿨이 가득하므로 실제 첫 행동은 특수기임(`tables/BattleScript/JSON_NORMAL_BATTLE_EVENT_CLASH_MOTIVATOR_001.json:13-14` 등).
8. **작업 없음.** 데이터북 반영 시 위 «데이터 흐름» 정리 절차를 따름.

## 검증 기록 — 2026-11-12 작업 PC

- 작업 PC 변경: `battlesim/mc.py`·`rules/default.json`, `tools/build_foe_clash.py`·`build_foe_auto.py`·`build_simpack.py`·`gen_rules_stamp.json`, 생성물 `data/foe_clash.json`·`foe_auto.json`·`quick.json`·`sim/manifest.json`, 시험 `clash_runtime_test.py`·`clash_ui_test.js`·`foe_clash_test.py`·`rules_test.py`·`mc_cache_test.py`·`e2e/test_page.py`, 이 문서. `index.html`은 재빌드 후 기존 값과 동일했음.
- 기준선 `STARSAVIOR_STATIC` 지정 전체: 127 통과/0 실패. COSMO_TABLES 없음·옆 journeyhelper 없음으로 기존 2건 건너뜀.
- 전용 결함 주입: 강제 협공 제거·격파 필터 무시·조각 병합 제거·boss_kill 제거·소환/스폰 부가 자료 제거·버전 업그레이드 제거·스킬 순서 강제 기본기·브라우저 조각 누락·BuffDesc 3%를 스탯으로 사용·legacy 대상 추첨 실행 10종 모두 assertion 실패를 확인하고 원복했음(`local/clash_mutations.py`). JS의 clash 기간 게이트 제거 1종도 검출했음.
- 첫 전체 검사에서 새 코드로 생긴 `coop_order_test`·`savior_mapping_test` 실패를 고쳤음. 강제 협공 후보가 없는 적은 협공 호출을 생략하고, 아군 빌더와 공유하는 필터 함수의 새 동작을 적 강제 협공 줄로 한정했음. 기존 시험의 기대값을 바꾸지 않았음. 관련 5개 시험 재실행 통과했음.
- `accel-golden/golden.py`를 main `82c612f`와 wt-clash 각각 실행: 기본/전체 legacy 78/78 동일, 실행 오류 0. 출력 `local/clash_main.json`·`local/clash.json`. 기존 콘텐츠 계산·quick 값을 그대로 유지했음. 해시 고정 시험은 새 규칙을 legacy off로 고정했음.
- 최종 `STARSAVIOR_STATIC=E:\AI_mk2\starsavior-static-data`, `PN_E2E_LOW_MEMORY=1` 지정 후 `python -X utf8 -I tools/run_tests.py --rebuild --e2e E:\AI_mk2\venv-pw\Scripts\python.exe`: **130 통과/실패 0**, 위 환경 자료 없는 2건만 건너뛰었음. 실행 로그 `local/clash_final.log`. 격전 의뢰 실제 결과 카드·기간 종료 게이트 통과, 최종 스크린샷 `local/shots/clash.png` 육안 확인했음.
- **판단 필요는 2번 패배 제한 수치만 남았음.** 독립 리뷰는 커밋 전 단계에서 별도로 진행할 것. 이 작업에서는 병렬 작업자·커밋·푸시·HANDOFF.md 수정하지 않았음.

## 주의

- 원본 클라 표·디컴파일은 공개 저장소에 넣지 않음. 이 문서의 줄 번호는 비공개 `decompiled/`(빌드 26610546, `OBF_` 번호는 빌드마다 바뀜) 기준.
- 해독 스크립트 위치는 위 «클라에서 확인한 것» 참조(비공개 저장소 `tools/`).
