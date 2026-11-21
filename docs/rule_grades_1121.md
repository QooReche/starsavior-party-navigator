# 남은 가정·커뮤니티·사용자·영상 등급 규칙 재기입 — 2026-11-21

`battlesim/rules/default.json`에서 grade가 code/data가 아닌 규칙 29건(formula 1·opts 14·mc 14)을 다시 판정했음.
목록은 스크립트로 다시 뽑았음(assumed 25·user 1·community 1·video 2, mc.break_skills는 전부 code라 대상 아님).
**기본값은 하나도 바꾸지 않았음.** 바꾼 것은 등급·근거 문구, 결과의 가정 보고 범위, 허용 목록 D 4행임.

## 근거 범위

static-data `check_build.py`: 설치본·디컴파일 buildid 26752678, DLL 10개 불일치 0.
`NKM`·`NKM.Templets`는 static-data `decompiled/` 아래의 각 `*.decompiled.cs`, `T`는 `E:/AI_mk2/rebuild_26752678/T`임.
3월판 디컴파일, 커뮤니티 수치, 계정 입력은 근거로 쓰지 않았음.

## 등급 체계 정리

등급 두 개를 새로 넣었음. 정의는 `default.json` 맨 위 `_note`, 어휘는 `battlesim/api.py`의 `RULE_GRADES`에 있음.

- `approx`: 빠른 계산·지표용 기대값 엔진(`engine.Sim`·`metrics`·`data/quick.json` 재료)에서만 쓰는 근사. MC 엔진(`mc.Battle`·`api.simulate`)에서는 읽지 않고 클라 경로를 씀.
- `tool`: 클라 규칙이 아닌 시뮬 도구 장치(안전 상한·모델 시간·파서 정책·민감도 스위치).

`ASSUMPTION_GRADES`(결과의 `assumptions_used`에 싣는 등급)는 그대로 두었으므로 `approx`·`tool`은 실리지 않음.
`tool` 항목이 실제로 걸리는 경우는 이미 따로 보고됨: 깊이 초과와 미해석 조건은 unsupported runtime의 `depth:`·`cond:`, `max_turns` 도달은 `timeout_p`, 이벤트 초과는 `EventLimitError`로 나옴.
그래서 정보는 사라지지 않음. `tests/rules_test.py`의 note 키 검사는 `ASSUMPTION_GRADES` 기준으로 맞췄음.

## 항목별 판정

|항목|전→후 등급|판정|근거·찾아본 위치|
|---|---|---|---|
|mc.enemy_init_cd|video→**code**|승격, 값 1.0 유지|AllSkillAvailable이 아니면 OBF_7817→OBF_25503이 모든 칸에 표 쿨을 넣음(NKM:1940–1949,2389–2396). Special·Hyper 플래그 칸만 0(NKM:1950–1957). «플래그 없는 칸 = 가득 1.0»과 같음. enemy_spawn=legacy 전용이고 영상 근거는 source에 보존|
|mc.enemy_init_cd_special|video 유지|근거 보강, 승격 안 함|클라는 배치별 SpecialSkillAvailable로만 특수기를 0으로 함(NKM:1950–1953). 모든 적에 상수 하나를 쓰는 이 값은 클라 구조와 다름(S 플래그와만 같음). legacy 전용이며 기본 경로 0회|
|mc.target_row_weight|community 유지|legacy 전용, 기본 0회|기본 table 경로는 클라 1001 필터와 같음. OBF_19762가 RollDice 뒤 전열/디펜더만 남기고(NKM:7766–7809) 최종은 균등 추첨(NKM:7168–7173). T AUTO_SKILL_TARGET_TEMPLET Id1001 Front/Defender 8000. 클라는 가중 추첨이 아니라 확률 필터라 대응 값 없음. 폴백은 legacy 재현용으로 보존|
|mc.target_defender_mult|assumed 유지|위와 같음|위와 같음|
|mc.target_mode|assumed 유지|위와 같음|위와 같음|
|mc.manual_burst|assumed 유지|근거 보강|버스트는 플레이어가 차례 유닛에 켬(NKM:14405–14487: 노바 비용·CC 불가·레벨1 상한). 효과는 그 행동의 슬롯 1~3(기본기·특수기·궁극기)에 붙음(NKM:2598–2608, NKM.Templets:33137–33143). ult_only는 클라보다 좁고, 어느 턴에 켤지는 사람 선택이라 클라 확정이 아님. 기본 auto에서는 0회|
|mc.ally_init_cd|user 유지|근거 못 찾음|NKM:3457·1940–1958(로컬 덱 쿨0), NKC:26583–26602(서버 쿨 배열 복사). 서버 초기값은 클라에 없음. note에 사용자 확인(10/21) 근거를 남김|
|mc.clash_no_turn_limit|assumed→user|재분류|근거가 11/12 사용자 판단임. 서버 제한 주입은 여전히 미확인(allowlist_round2 조사 유지)|
|mc.heal_target|assumed 유지|근거 못 찾음|round2 조사(NKM:7132–7181,7572–7594, Id2)에서 새 클라 대응 없음. 표준 67형태 폴백 0회|
|mc.cosmo_raid_boss|assumed 유지|변경 없음|서버 산출 묶음(allowlist_rules·round2 판정 유지)|
|mc.turn_ticks·max_events·max_depth·unknown_cond|assumed→**tool**|재분류|allowlist_rules_1121 조사 그대로(NKM:13872–13900,15345–15470, NT:42260–42279). 클라 상수 대응 없음. 허용 목록 D에서 해소|
|formula.TICK_PER_TURN|assumed→tool|재분류|기대값 엔진 시간 단위. MC 턴 제한은 전역 행동 수(NKM:13880–13883)|
|opts.unknown_cond_p·nova·coop|assumed→tool|재분류|파서 가중치, 민감도 스위치(true = 클라처럼 켬)|
|opts.enemy_resist·enemy_def·enemy_spd·ref_enemy_count·inf_hp_frac·kill_p_inf·no_debuff_p|assumed→**approx**|값 유지|기준 적(HP 무한 가상 적)은 클라 개념이 아니라 대응 상수가 없음. 스테이지·MC 전투는 적마다 표 값을 씀|
|opts.debuff_success|assumed→approx|값 유지|debuff_model=hit_resist(기본)에서는 쓰지 않음. 클라 효과 적중은 상수가 아니라 적중−저항 판정임|
|opts.break_p|assumed→approx|값 유지|클라 브레이크는 강인도가 0이 된 상태이고 빈도 상수가 없음. MC는 강인도 모델로 직접 계산|
|opts.init_cd_frac|assumed→approx|값 유지|MC는 ally_init_cd(0)를 씀. 근거가 ally_init_cd와 같은 미확정이고, 바꾸면 골든·quick.json 재료가 바뀌어 유지|
|opts.debuff_state|assumed→approx|값 유지|기대값 모델의 상태 처리. MC는 판마다 성공/실패를 굴림|

집계: code 승격 1, 재분류 20(tool 8·approx 11·user 1), 근거 보강 뒤 유지 5(legacy 전용 4·manual_burst 1), 근거 못 찾음·변경 없음 3. 값 교정 0.
(29 = 1 + 20 + 5 + 3)

## 대상 선택 폴백 계측

`tools/measure_rule_grades_1121.py`를 실행함: standard, seed 20261121, 시나리오마다 8판, 단일 프로세스, 편성 그웬·아모라·프레이·클레어.

|시나리오|1001 필터|옛 가중 추첨|legacy weighted 선택 시 가중 추첨|
|---|---:|---:|---:|
|달 회랑 100|0|0|0|
|태양 회랑 200|74|0|74|
|태양 회랑 250|108|0|106|
|코스모 길레 1단계|0|0|0|
|코스모 모굴루스3·도전0|39|0|42|
|길드 방어전 Lv0|87|0|0(길드 보스 전용 모델이 1001을 직접 씀)|

같은 계측에서 enemy_init_cd 옛 경로 0슬롯, 배치 표시 없음 0, ranked 설명 근사 0, 노바 버스트 0, depth·cond 진단 0이었음.
달 회랑 100과 길레 1단계는 적 단일 대상 선택 자체가 0회임(적이 행동 전에 쓰러지거나 광역).
폴백은 기본 경로에서 0회이므로 엔진 코드는 고치지 않았음. legacy 재현용으로 보존함.

## 결과 영향

같은 도구로 전(HEAD e6749f0)·후를 비교함. 여섯 시나리오 모두 진행도·클리어·비교 점수·계측이 같음.
태양 회랑 250은 55.1512, 모굴루스는 1,622,718.75임.
값을 바꾸지 않았으므로 바뀐 것은 `assumptions_used` 하나뿐임. 모든 시나리오에서 mc.max_depth·max_events·turn_ticks·unknown_cond 4행이 빠졌음.
규칙 지문(`tools/rules_stamp.py`)은 값만 해시하므로 e06c79830ecb9052 그대로이고 guild_sim·quick 모두 일치함. 그래서 `--ack`과 quick 재보정은 하지 않았음(탐색 정책 불변).
허용 목록 D는 16→12(위 tool 4행 해소)이고 A/B/C/E 변화 0. `--write` 뒤 `--diff`가 깨끗함.
시뮬 묶음을 재빌드해 `sim/manifest.json` ver가 d4bb1b4df2a2가 됐음(api.py·default.json 내용 변경).

## 시험

새 `tests/rule_grades_1121_test.py` 6개: 등급 어휘, 재분류 결과, 보고 계약(tool 제외·user·legacy 대안 복귀), 깊이 상한 진단, legacy 시작 쿨 = 클라 가득, 기본 대상 = 1001(가중 0)·legacy에서 가중 > 0.
일부러 깨뜨린 4개(기본 경로를 가중으로, legacy 시작 쿨 ×0.5, 깊이 검사 제거, tool을 보고 등급에 추가)가 각각 해당 시험을 실패시켰고 원복 뒤 통과했음.
관련 시험 rules·allowlist_rules_1121(enemy_init_cd 기대 갱신)·allowlist_break·followup·remain·round2·unsupported_26752678·unsupported_gate·auto_skill_1121·p3·client_rules_1111·external_rules_c·auto_target·heal_burst·mc_cache·client_gaps_1104·gen_rules_stamp가 통과했음.
전체 시험(run_tests.py --rebuild)은 돌리지 않았음(합친 뒤 1회 예정).

## 남은 것

- ally_init_cd·clash_no_turn_limit·cosmo_raid_boss: 서버 입력이라 클라로 확정할 수 없음.
- heal_target: 원형 SE가 없는 입력의 폴백이라 클라 표로 채울 대상이 아님.
- target_*·enemy_init_cd_special: 클라와 구조가 다른 옛 근사임. legacy 재현을 위해 보존함.
- manual_burst: 사람 운영 정책임.
- approx 11건: 기준 적 정의라 클라 값이 없음. 빠른 계산 계수를 다시 맞추는 것은 범위 밖임.
