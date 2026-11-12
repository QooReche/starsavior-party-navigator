# 2026-11-12 재점화 증감 합산

## 결론

클라 빌드 **26610546**은 재점화를 **일반 피해 증가·감소 스탯에 더함**. 별도 `×(1+x)`·`×(1−x)`가 아님. `rekindle_apply=sum`을 기본으로 넣었고 `legacy=multiply`로 종전 동작을 보존했음.

두 설명이 동시에 맞음: 최종 스탯 계산에서는 **버프의 3단 가산값**이고, 그 결과를 피해식이 읽을 때는 **주는 증감 − 받는 감소의 순합**에 들어감. 공격력 등에 쓰는 3단 **비율 곱**과 혼동하면 안 됨. 외부 장비 도구의 추가 스탯 배열은 결론의 근거로 쓰지 않았음.

## 근거 경로

아래 경로는 비공개 `starsavior-static-data/` 기준임. 표 원문은 복사하지 않았음. 디컴파일 판은 `decompiled/BUILD.md:44` 이하의 26610546 기록으로 확인했음.

| 단계 | 근거 파일:줄 | 확인한 내용 |
|---|---|---|
| 재점화 단계 → 전투 효과 | `tables/OPERATION_BUFF_TEMPLET.json:7-43` | 5단계가 `BATTLE_EFFECT_OPERATION_HANDICAP_70001~70005`에 연결됨 |
| 전투 효과 → SE | `tables/BATTLE_EFFECT_TEMPLET.json:2044-2078` | `AteamEffectTarget=ALL`, 해당 효과가 `COND_BATTLE_EFFECT_OPERATION_HANDICAP_700011~700051`을 사용함 |
| 효과 대상 판정 | `decompiled/NKM/NKM.decompiled.cs:415-427`; `decompiled/NKM.Templets/NKM.Templets.decompiled.cs:37223-37224,37242-37263` | 효과 목록을 받아 조건을 검사함. AteamEffectTarget은 A팀에, BteamEffectTarget은 B팀에 적용되며 ALL은 모든 해당 팀 유닛을 통과시킴 |
| SE → 스탯 효과 | `tables/SE_TEMPLET_BATTLE_EFFECT.json:11559-11633` | 전투 시작, 발동률 10000, SELF에 `BI_OPERATION_HANDICAP_01~05`를 부여함. 표의 SELF를 곧바로 ALL_ALLY라고 해석하지 않았음 |
| 스탯 키·수치 | `tables/BUFF_TEMPLET.json:55578-55937` | `NST_RATE_DAMAGE_UP`, `NST_RATE_DAMAGE_REDUCE`에 각각 300·700·1200·1800·2500. TurnInfinite·DeadNotDispel·ForceApplyEffect=true, IsBuff=false |
| enum·수치 단위 | `decompiled/NKM.Templets/NKM.Templets.decompiled.cs:32494-32566,33017-33031` | REDUCE=71, UP=72. `OBF_4001`은 ×0.0001. NV 비율 스탯의 대응표에는 HP·속도·공격·방어만 있음 |
| 효과 스탯 수집 | `decompiled/NKM/NKM.decompiled.cs:3885-3892,2371,18947-18950` | 효과의 스탯들을 합쳐 `OBF_6433`으로 전달함 |
| 3단 가산 | 같은 파일 `18864-18897` | 효과 스탯 `num10`이 `num22`에 더해지고 최종식 `floor(num17 + num22 + num17 × 3단 비율)`에 들어감. 재점화의 두 RATE 스탯에는 NV 대응이 없어 재점화 자체가 비율 곱을 만들지 않음 |
| 일반 증가·감소 소비 | 같은 파일 `18482-18490,18611-18620,18299-18334` | 공격자의 일반 DAMAGE_UP, 피격자의 일반 DAMAGE_REDUCE를 각 증감 합에 포함함. 지속 피해도 같은 일반 항을 사용함 |
| 최종 피해 | 같은 파일 `18185-18193` | 방어를 먼저 적용한 뒤, 증가−감소 순합에 하한을 적용하고 `피해 + 피해 × 순합`을 계산함. 현재 `dmg_cap_scope=net` 경로와 연결됨 |
| 연쇄 예외 | 같은 파일 `6212-6236,17774-17818` | 공격자의 일반 DAMAGE_UP은 연쇄 계산에도 합산함. 받는 쪽은 REDUCE_ADD_DAMAGE만 읽으므로 재점화의 일반 DAMAGE_REDUCE는 연쇄를 줄이지 않음. ADT_STAT_TRUE는 별도 조기 반환임 |

전투 효과의 대상은 표에서 **아군 전체**로 확인했음. 서버가 콘텐츠·계정의 재점화 단계에 맞춰 효과를 선택·주입하는 부분은 클라만으로 확정할 수 없어 **미확인**으로 남겼음. 기존 `op·oph` 적용 범위와 사용자 확인은 유지했음. IsBuff=false이므로 일반 강화 개수·정화 대상처럼 모델링하지 않았음. 예전 HANDOFF의 «해제 불가» 표현은 표의 CanNotDispel=true라는 뜻이 아님(현재 표는 false).

## 구현

- 종전 `api.py`는 재점화 수치를 전투력 보정 `pen`에 곱했고, `mc.py`는 일반·지속·연쇄 피해 끝에서 이 배율을 곱했음. 감소 상한을 통과한 뒤에도 재점화 감소가 다시 적용되고, 치명·다른 증가까지 재점화로 증폭되는 차이가 있었음.
- 새 API 경로는 아군 상시 효과 `ally_fx`에 피해 증가·감소 %p를 넣음. `mc.Unit.mods()` → 일반 `final_dmg()` / 지속 `_tick_dot_hot()` / 연쇄 `chain()`의 기존 스탯 경로를 재사용했음. `mc.py` 피해식을 중복 수정할 필요가 없었음.
- 전투력 보정은 독립적으로 보존함. `stage_fx_target=off`여도 재점화는 적용하며, 아군 전체에만 넣음. 옵션에 잘못된 적용 방식이 오면 오류로 거부함.
- 일반 강화로 등록하지 않아 강화 개수·강화 불가·해제와 독립이며, 아군 객체에 남으므로 웨이브 전환에도 유지됨. 고정 고유 피해는 변경하지 않았음.
- `tests/rules_test.py` 키 목록과 `mc_cache_test.py`의 `_KEEP`를 갱신했음. 결과 해시 기대값은 다시 쓰지 않았음.
- 화면의 빠른 계산은 집계 화력 계수에 재점화 배율을 적용하는 **근사**를 유지함. 개별 타격의 치명·증감·감소 상한을 표현하지 못하므로 상세 시뮬과 같은 식이라는 주석을 고쳤음. 아래 재보정만으로 재점화가 켜진 빠른 계산의 정확도까지 검증했다고 보지 않음.

## 결과 영향

시작 main·작업 브랜치 모두 `d0b4f64180d8595f1285e7eaf6203a000f18bbfc`였음. main을 작업 폴더 안 `local/rk_main_source/`에 `git archive`로 고정해 비교했음. 지정 폴더 밖은 읽기만 했고 커밋·푸시·HANDOFF 수정은 하지 않았음.

- 지정 `accel-golden/golden.py`를 main 스냅샷과 작업 폴더에 각각 실행했음. **78/78 동일, 오류 0**. 출력은 `local/rk_main.json`, `local/rk.json`. 원본 도구는 재점화를 켜지 않으므로 이것만으로 수정 검증을 끝내지 않았음.
- 추가 비교 `local/rk_compare.py`: 원본의 공개 standard 3팀, 작전 36-36·40-1 및 어려움 13-10, 재점화 0·1·5, 전투력 보정 off·model, seed=3·20판, 기본/전체 legacy/재점화만 legacy. **162건**을 양쪽에서 같은 조건으로 실행했음.
- 기본 54건 중 **36건 변경**(재점화 1·5의 모든 케이스), 재점화 0의 18건은 동일. 전체 legacy **54/54**, 재점화만 multiply **54/54**가 main과 동일했음.
- 어려움 13-10은 재점화가 있는 기본 12건 모두 해시가 달라졌음. 공개 standard에서 클리어율은 모두 0으로 같았고, 적어도 실제 피해가 나간 양의 진행도를 확인했음. 예: 전투력 보정 off·5단계의 진행도는 팀0 0.0108→0.0072, 팀1 0.0055→0.0054, 팀2 0.0774→0.0689. 큰 교전의 승률 영향까지 대표하는 표본은 아님.

## 검증 기록

변경 전 기준선: `STARSAVIOR_STATIC=E:\AI_mk2\starsavior-static-data`를 지정한 전체 시험 **130 통과 / 0 실패**. 환경 건너뜀 2건(COSMO_TABLES·옆 journeyhelper 부재)이 있었음.

- `tests/rekindle_1112_test.py` **9개 통과**. 비공개 표의 단계→효과→SE→버프→스탯 연결, 0~5단계·op/oph/비대상 콘텐츠·전투력 보정 on/off·기본/legacy, 일반 피해·치명·순합 하한·지속·연쇄 양 방향·고정 피해 제외·강화 불가·기존 스테이지 효과와 합산·웨이브 유지·잘못된 옵션을 검사했음.
- 실제 standard 어려움 13-10·재점화 5·seed=3·3판에서 진행도 **0.0693**, 영향을 받는 아군 타격 **9/9회**를 확인했음. 진행도 0인 빈 시험이 아님.
- `local/rk_mutations.py`에서 메모리 안 API 함수에 재점화 전체 누락·증가 누락·감소 누락·기존 곱 강제의 결함을 넣었음. 각각 **27·26·24·28개 assertion 실패**, 실행 오류 없이 모두 검출했음. 함수는 매번 원복하며 파일은 변경하지 않았음.
- 빠른 계산 표본: `local/rk_calib_serial.py --per-content 400 --opboss`로 `tools/gen_quick_calib.py`의 Pool만 순차 map으로 바꿔 실행했음. **2,323건×40판**을 재생성했음. 동일 옵션의 생성기와 표본 선택·시드·계산은 같고 병렬 작업자는 쓰지 않았음. 현재 생성기 표본은 재점화 0이라 재점화 활성 조건의 빠른 계산 정확도를 별도로 보증하지 않음.
- `python -X utf8 -I tools/calibrate_quick.py --write` 완료. `calib.acc` **0.923→0.927**. 최신 main 표본은 **1,455건**(base 935, cosmo/rush 각 260), 이번 표본은 **2,323건**(base 1,523, cosmo/rush 각 400)이므로 **직접 비교 가능한 개선폭이 아님**. 재점화 0의 결과가 불변인 것도 별도 골든으로 확인했으므로 정확도 차이를 재점화 수정 효과라고 해석하지 않았음. 빠른 계산 규칙 도장을 갱신했음.
- 길방 표는 시즌4 종료·미오픈 사유로 `tools/rules_stamp.py --ack guild_sim --reason ...` 처리했음. 재점화는 op·oph에만 적용되어 길방에는 영향이 없으며 새 시즌 자료 반영 때 표를 재생성하기로 함.

## 실제 플레이 대조

`docs/ingame_samples.md`에는 어려움 13-10 기록이 없었지만, `tools/ingame_check.py:151-155`에 `op1310`(재점화 1)과 `op1310r0`가 있고 HANDOFF에도 판독 기록이 있었음. `op1310`을 main / sum / multiply로 각각 **100판·seed=7** 대조했음. 실행은 기존 `tools/ingame_check.py --only op1310 --runs 100 --seed 7`, multiply에는 `--ov '{"rekindle_apply":"multiply"}'`를 더했음.

**개선 여부는 판단 필요.** sum은 클리어율·전체 행동 수 중앙값이 이전과 같았고, 받은 피해 오차는 줄었지만 준 피해 및 준/받은 비율 오차는 늘었음. multiply는 main 대조 결과 전체와 동일했음. 당시 내 정보가 없어 도구의 전투력·화면값 기반 근사 편성을 사용했고, 샘플의 리더/배치·브레이크 스킬도 확정되지 않았음. 한 판으로 클라 합산 근거를 뒤집지 않았음. 계정 관련 수치·상세 출력은 공개 문서에 넣지 않았음.

## 최종 확인

- `STARSAVIOR_STATIC=E:\AI_mk2\starsavior-static-data`를 지정한 `python -X utf8 -I tools/run_tests.py --rebuild`: **131 통과 / 실패 0**. 환경 건너뜀 2건(COSMO_TABLES·옆 journeyhelper 부재)은 기준선과 같았음. 로그 `local/rk_final_tests.log`.
- 관련 e2e만 실행: `E:\AI_mk2\venv-pw\Scripts\python.exe -X utf8 tests/e2e/test_page.py rekindle_ui sim_auto_and_override --shots local/rk_shots`: **2 통과 / 실패 0**. 재점화 선택·시뮬 옵션 전달·타 콘텐츠 제외·저장, 실제 브라우저 시뮬 워커 실행을 확인했음. 로그 `local/rk_e2e.log`.
- 첫 재빌드 시험에서 편집 과정의 CRLF 때문에 JS 소스 추출 시험 2개가 실패했음. 기존 LF로 복원한 뒤 해당 시험과 전체 시험이 통과했음. 기준선에는 없던 편집 문제였고 엔진 식을 바꿔 시험을 맞추지 않았음.
- `git diff --check` 통과. 엔진 규칙·시험·설명·빠른 계산·생성물만 변경했음. HEAD는 시작 커밋 그대로이며 커밋·푸시·HANDOFF 수정 없이 마무리했음.
