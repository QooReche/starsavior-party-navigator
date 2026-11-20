# 구원자 미지원·근사 8건 정리 (PC 26752678)

## 근거 범위

지정된 PC 설치본 buildid=26752678과 `E:/AI_mk2/decomp_26752678/dll/`의
NKM·NKM.Templets·Star.Templets SHA256이 일치함을 직접 확인했음.
비공개 static-data는 pull 후 최신이지만 기본 `decompiled/`는 26610546이므로 사용하지 않았음.
아래 NKM·Star.Templets 줄은 `E:/AI_mk2/decomp_26752678/set10/clean/` 아래
각 어셈블리의 `*.decompiled.cs`, 표 줄은 `E:/AI_mk2/rebuild_26752678/T/` 기준임.
공개 저장소에는 원문 표·계정 입력·계정 결과를 넣지 않았음.

## 항목별 확정

|항목|PC 근거|확정·변경|
|---|---|---|
|선샤인 캣 스마일 기본기 물폭탄 해제|CLIENT_SE_TEMPLET_SKILL_1.json:31048(SE10464017), plain/AUTO_SKILL_TARGET_TEMPLET.json:727(10463), NKM:7132–7178|U5 원형 실행기가 제거 표지의 현재 보유자를 고름. 보유자 0명도 정상임. 해제 전 공통 검사에서 설명문 폴백을 하지 않도록 연결했음.|
|선샤인 캣 스마일 궁극기 물폭탄 해제|동일 SE 표:31112(SE10464021), NKM:16492–16559|기본기와 같은 규칙임. 원형의 조건 판정·수신자·AfterActiveSkillSe 순서는 유지함.|
|구원자 길레 표지 해제 2종 기록|동일 SE 표:12541(SE10201012),12823(SE10202015), plain/AUTO_SKILL_TARGET_TEMPLET.json:677(10205), NKM:7152–7178,7535–7545|기본기·특수기 모두 현재 마지막 타격 표지 보유 적 전원이 대상임. 기존 auto_skill의 두 행은 이미 맞았음. 빈 집합을 규칙 없음으로 바꾸던 공통 폴백 때문에 발생한 두 종류 실행 기록을 해소했음.|
|클레어 개화 선제 방어 무시|동일 SE 표:50653(SE16093014), CLIENT_BUFF_TEMPLET.json:31359–31417(BI_MAID_SPEAR_SSR_2), Star.Templets:4773, NKM:9019–9028|스탯 감소가 아니라 NoPreemptiveDefend=true임. IsBuff=false·표시 없음·수명 0인 숨은 표지로 부여·종료 정리함. 기존 no_preemptive의 버프/궁극기 우회와 연결하고 정적 의미 미해석 오탐을 제거함.|
|스칼렛 핀볼 타임!|CLIENT_BUFF_RANDOM_TEMPLET.json:78–87(RBI_BUNNY_SCISSORS_1), Star.Templets:4375–4383, NKM:16444–16482|후보 2개에 각각 가중치 10000, BuffCount=1임. 독립 SE 3회는 매번 새 추첨이므로 같은 볼 중복 가능함. 기존 choice 동작을 유지하고 code 근거로 분류함.|
|베라 특급 배송|CLIENT_SE_TEMPLET_SKILL_1.json:44226(SE15073011), CLIENT_BUFF_RANDOM_TEMPLET.json:88–95(RBI_LPU_POST_1), NKM:16468–16477|후보 4개가 같은 가중치이며 1개 추첨임. 기존 choice 유지함.|
|베라 개화 특급 배송|동일 SE 표:49292(SE16073012), 같은 RBI_LPU_POST_1·NKM 경로|개화도 BuffCount=1임. 표에 별도 존재하는 RBI_LPU_POST_2(BuffCount=2)를 사용하는 것으로 오인하지 않았음.|

여기서 감사의 «8건»은 구원자 6형태의 미지원 1·실행 진단 4·균등 가정 3을 뜻함.
구원자 길레의 진단 2종은 각각 기본기·특수기 SE에서 발생할 수 있음.

무작위 버프 클라 공통 경로는 선택한 후보를 지우고 다음 후보를 추첨함(NKM:16476–16477).
이번 3형태의 실제 연결은 모두 BuffCount=1이므로 기존 단일 균등 choice와 같음.
이 확정을 임의의 무작위 적 대상·미연결 효과·BuffCount>1 경로 전부의 동등성으로 확대하지 않음.

클레어 표지는 IsBuff=false·IsPositive=true여서 강화 불가·약화 면역에 막히지 않음
(NKM:4389–4398). 현재 CLIENT_BUFF_IMMUNE_TEMPLET에 해당 버프가 없으며,
Star.Templets:4167–4178은 양성 버프를 면역 목록에 넣는 것도 거부함.
새 경로의 직접 부여가 현재 클레어 표의 면역 동작을 바꾸지 않음을 확인했음.

## 규칙과 API 계약

`supported_marker_targets`는 스마일 물폭탄 원형 표지·구원자 길레의 마지막 타격 해제에만
빈 집합을 정상으로 인정함. 다른 미지원 표지의 legacy 설명문 폴백은 유지함.
`claire_preemptive_marker`는 클레어 개화의 숨은 표지 분류·수명을 선택함.
기본/legacy·근거 등급 정본은 `battlesim/rules/default.json`임.
`random_buff_draw`는 실행 옵션이 아닌 code 근거 설명 항목임.

`assumptions_used`는 assumed·community·video·user·inference·game 등급만 담음.
mc·break_skills·opts에 같은 필터를 적용하며 code/data는 제외함.
실제 분기 실행 추적 목록은 아니므로 선택 규칙이 해당 전투에서 발동했다는 뜻은 아님.
이미 지원하는 선제 방어·반응 트리거의 포괄적 미지원 문구와 균등 추첨 가정은 제거함.

`unsupported.gate_ok`는 정적 critical 또는 실행 중 기록이 있으면 false임.
`runtime_approx`는 실행 기록 존재 여부, `runtime`은 키별 횟수,
`runs_affected`는 해당 판 수를 그대로 제공함. 허용 목록·자동 중단은 도입하지 않았음.
`web.run_auto`의 기존 `gate`는 이 값을 전달함. 화면에는 assumptions_used를 소비하는 코드가 없으며,
현재 화면의 잠재력 경고와 계산 정책은 유지함. 분할 실행의 gate는 해당 호출 진단임(원시 판별 배열에는 진단이 없음).

## 재현

```
python -X utf8 -I tests/unsupported_26752678_test.py
python -X utf8 -I tests/unsupported_26752678_test.py --mutations
python -X utf8 -I tools/measure_unsupported_26752678.py before
python -X utf8 -I tools/measure_unsupported_26752678.py after
```

## 감사·표준 육성 영향

수정 전 3697359 기준선은 219개 파일 통과·실패 0이었음. 원문 표 대조 2건은
COSMO_TABLES 미설정으로 건너뜀. 지정 감사의 audit.py를 `local/unsup/`에 복사하고
하드코딩된 저장소 경로만 이 작업 트리로 바꾸어 실행했음. 원본 감사 자료는 보존했음.
67형태×standard/none 정적 검사 모두 0건, 67형태×5전투×3판(1,005판)의
실행 기록 모두 0건이었음. 표본에서 안 탄 분기의 전역 지원을 보증하는 결과는 아님.

`measure_unsupported_26752678.py`는 대상 구원자+그웬+아모라+프레이, 표준 육성,
seed=20261120, 조합당 8판임. 코스모 시즌 1023의 3보스 1단계·챌린지 0과
태양 회랑 FLOOR 250을 비교했음. 24조합 모두 진행도>0, 23조합의 outcome·per_unit·점수가
동일했음. 아래는 평균 점수와 클리어 판 수의 표본임. 계정 결과가 아님.

|대상 구원자|스테이지|평균 점수 전→후|클리어 전→후|
|---|---|---:|---:|
|선샤인 캣 스마일|괴리의 표상 1단계|153875→153875|8/8→8/8|
|구원자 길레|모굴루스 1단계|154000→154000|8/8→8/8|
|클레어 개화|바스커빌 1단계|154375→154375|8/8→8/8|
|스칼렛|괴리의 표상 1단계|153250→153250|8/8→8/8|
|베라|괴리의 표상 1단계|153000→153000|8/8→8/8|
|베라 개화|괴리의 표상 1단계|153000→153000|8/8→8/8|
|클레어 개화|태양 회랑 FLOOR 250|점수 없음, 진행도 0.5104→0.5361|0/8→0/8|

클레어의 숨은 버프가 일반 강화로 집계되던 차이를 없애면서 후속 전투 집계가 달라졌음.
8판 차이를 승률 개선 추정치로 일반화하지 않음. 쉬운 보스 표본에서는 해당 스킬까지
도달하지 않을 수 있으므로, 표지 경로 검증은 위 감사의 3단계·길드 방어전과 경계 시험이 맡음.
quick 재보정은 이전 공개 표보다 표본 수가 많으며 누적된 엔진 교정도 함께 반영함.
따라서 quick 계수·추천 결과 변화 전체를 위 8건의 독립 효과로 해석하지 않음.

## 검증·남는 범위

- 집중 시험 8개 메서드: 물폭탄 기본기/궁극기 빈 집합·현재 표지 이동, 구원자 길레
  두 SE의 빈 집합·복수 보유자 해제, 클레어 플래그·강화 개수 제외·0턴 만료·캐시 전환,
  무작위 3형태의 후보·독립 추첨, 모든 규칙 절의 등급 필터, 실제 진행도>0 전투에 진단을
  주입해 API gate·판 수·웹 gate 전달을 검사함.
- 11개 변이에서 총 17개 assertion 실패를 확인했음. 설명문 폴백 복원 2개, 실제 대상 필터 제거 2개,
  클레어 표지 분류·플래그·수명 제거 3개, 균등 choice를 첫 후보 고정으로 변경,
  code 등급을 가정에 혼입, 실행 기록을 gate에서 제외, 다른 native 구원자로 적용 범위 확대임.
  스마일·구원자 길레의 두 스킬과 무작위 3형태는 subTest로 나눠 각각 실패함을 확인함. 예외 실패는 검출로 세지 않음.
- 가정 목록은 현재 기본값에서 31개임. 사용한 분기만 남기는 실행 추적·legacy 선택의
  개별 근거 재분류는 이번 범위 밖임. 일부 기본값에서 비활성인 legacy 가정도 남음.
- 구원자 6형태의 요청된 8건은 해소했음. 코스모 점수식·배율 순서·시즌 버프·전투력 보정,
  길드 방어전 지원 대상·배율 순서·졸개전 점수, 기대값 엔진의 확률 상태 상관은 남음.
  이번 작업에서 이 항목들을 새로 확정하지 않았음.
- 기존 적 감사의 지난 시즌 벨그라스·길드 스테이지 미지원, 현행 공허결집자의 복합 피해,
  공허투영자 억류 보고 오탐 가능성은 범위 밖임. 전체 적 감사의 새 판정으로 주장하지 않음.
- 정적 중요도와 실행 진단을 합친 허용 목록 관문·실행 중단·화면 경고 확장은 다음 단계임.
  기존 code 등급 note 속의 부분 근사와 서버/실게임 검증 미완료까지 지운 것은 아님.

최종 전체 시험·생성물·독립 리뷰 결과는 HISTORY의 같은 날짜 작업 절에 기록함.

## 남은 가정 목록 (감사 시점)

현재 기본 API의 31개 항목을 규칙 키로 분류했음. 아래 `mc.` 접두사는 생략했으며
값·등급·주석의 정본은 `battlesim/rules/default.json`임. 선택 규칙 목록이므로
이번 판에서 실제 실행됐다는 뜻은 아니며, code 등급 안의 부분 근사까지 망라한 목록도 아님.

|범위|규칙 키|
|---|---|
|전투 시작·웨이브·수명·턴|clash_no_turn_limit, wave_foe_battle_start, revive_after_spawn, caster_death, turn_ticks|
|AI·시작 쿨·대상|enemy_skill_ai, ally_init_cd, enemy_init_cd, enemy_init_cd_special, target_row_weight, target_defender_mult, target_mode, heal_target|
|피해·회피·강화 집계|add_damage_guard, enemy_same_formula, evade_model, enemy_hit_buff_cmp|
|안전 상한·모르는 조건|max_events, max_depth, unknown_cond|
|노바·기대값 엔진|manual_burst, opts.nova_policy, opts.init_cd_frac|
|지원 스킬|break_skill_normal_points, break_skill_boss_points, break_skill_domain_clock, break_skill_fixed, break_skill_model|
|소환·코스모|summon, cosmo_raid_boss|
|포괄 미지원 안내|model.not_modeled — 표에 없는 피해 제한, 일부 노바 슬롯·일반 잠재력·전술 분석·호감도·시즌 보너스·Lv200 초과 성장·연쇄 피해 턴 끝 시점|

## 전체 시험에서 발견한 범위 오류

최초 전체 실행에서 `autotarget_12_test`와 `engine_cache_test` 두 파일이 실패했음.
전자는 새 native 표지 조기 반환이 다른 구원자의 `line_spec` 계약까지 바꾼 결함이었음.
스마일 물폭탄·구원자 길레로 제한하고 기존 린 보호 시험은 그대로 유지했음.
후자는 마지막 실제 구원자 미지원이 해소돼 보고가 모두 빈 목록이 된 결과였음.
합성 미지원 효과를 캐시 입력에 추가하고 기존 «비어 있지 않은 보고» assertion을 유지했음.
항상 빈 보고를 반환하는 변이를 넣어 이 보강 시험의 실패도 확인했음.

범위 축소 전후 비대상 6명×2스테이지×8판의 outcome·per_unit·battle_stat이 같았음.
native `line_spec`이 실제 호출된 세레스·할로윈 리디아는 버전당 합계 175회였고,
다른 4명의 이 표본에서는 해당 호출이 없었음. 호출이 없는 경로는 직접 경계 시험과
고정 소스 리뷰로 확인했으며 표본 수치 동일성만으로 전수 동등성을 주장하지 않음.
원형 대상은 `resolve`에서 우선 처리되고, 나머지 native 해제는 적 대상이어서
아군 해제 폴백으로 확대되지 않음을 확인해 기존 quick 보정 표본을 유지했음.
