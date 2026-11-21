# 전투력 차이 보정(power penalty) 클라 재조사 (2026-11-21)

## 판정

**클라 확정 불가(서버가 배율을 정함) — 단, 클라가 가진 값·식은 전부 현재 엔진 `model`과 같음.**
엔진 식·기본값·표는 바꾸지 않았음. 바꿀 클라 근거가 없었고, 추정 보정은 넣지 않았음.

- 클라는 이 배율을 **만들지 않음**. 전투 호스트가 생성자에서 양 팀 배율을 받아 그대로 곱함.
  클라가 호스트를 직접 만드는 곳은 로컬 전투(1배 고정) 하나뿐임. 일반 전투의 배율은 서버가 정함.
- 배율 표(BATTLE_POWER_RANGE_TEMPLET 500행)는 **클라 데이터에 실려 있으나 읽는 코드가 없음**.
  엔진이 쓰는 표(`data/power_penalty.json`·databook topics.pen)와 500행 전부 같음.
- 클라가 **화면에 보이는 값**(전투력 부족 경고 21단계)과 그 계산식은 엔진과 같은 비율 정의·같은 격자를 씀.
  모순되는 값은 없었음.
- 따라서 작전 42-12의 «시뮬 29% vs 실제 약 20판 0승» 차이는 이 보정으로 설명되지 않음(엔진 값 = 클라 표 값).
  남은 원인 후보는 `docs/op4212_gap_1121.md`의 다른 항목(오토 스킬 사용 등, 다른 담당)임.

## 클라 근거 (빌드 26752678)

`NKM`·`NKC`·`NT`(NKM.Templets)·`ST`(Star.Templets)·`AC`(Assembly-CSharp)는
`starsavior-static-data/decompiled/<이름>/<이름>.decompiled.cs`. `T`는 `rebuild_26752678/T/`.
`check_build.py` = 설치본·디컴파일 26752678, DLL 10개 불일치 0.

### 배율을 받고 곱하는 곳 (적용)

|위치|내용|
|---|---|
|NKM:465–482|전투 호스트 생성자. 호스트 입력의 A팀·B팀 배율을 `OBF_28386`으로 저장|
|NKM:12500–12532|호스트 입력 구조체. 배율이 0 이하이면 10000(1배)|
|NKM:12857–12859, 12951–12953|호스트 필드 기본 10000|
|NKM:13166–13167|전투 시작 로그 «[데미지 역보정 설정] A/B팀의 최종 데미지 배율»|
|NKM:13373–13376|배율 저장|
|NKM:18195, 18369–18386|일반 피해(스킬·지속·즉발·수호 분담·폭발) 마지막에 **공격자 팀** 배율을 곱함. 같은 팀끼리는 0|
|NKM:17815, 18408–18428|고정 수치 피해 경로도 **출처 팀** 배율을 곱함|
|NKM:17836–17870|폭발(지속 피해 합산 폭발)은 지속 각각에 한 번, 합계에 또 한 번 거침(엔진에 폭발 경로 없음 → 영향 없음)|

회복·보호막 경로에는 이 배율이 없음(검색 결과 배율 필드를 읽는 곳은 위 두 함수뿐). 엔진도 회복·보호막 제외.

### 배율을 «만드는» 코드를 찾은 결과

|찾은 곳|결과|
|---|---|
|호스트 입력 생성 호출 전수(`OBF_26142` 생성자·팩토리)|NKC:556331–556342 한 곳뿐. 로컬 전투(`NKCLocalHostManager`)이며 배율 인자 `10000, 10000` 고정|
|배율 저장 호출 전수(`OBF_28386`)|NKM:481 한 곳(호스트 생성자)뿐|
|배율 필드 읽기 전수(`OBF_28208`/`OBF_17481`)|NKM:12951–12953, 18377–18378, 18418–18421뿐. NKC·AC에서 읽는 곳 0|
|전투 시작/동기화 패킷(`OBF_17888`, NT:21571–21624)|배율 필드 없음(전투 ID·맵·팀·턴 정보뿐). 동기화 생성 NKM:13052–13065도 배율을 넣지 않음|
|타격 결과 패킷|타격마다 피해 기록 `OBF_16839`(NT:24388–24618)가 실리고(NT:24726), 그 안에 실제 적용 배율 `OBF_22252`(NT:24510, 24602)가 있음. 즉 서버 배율은 **타격 단위로만** 내려옴. 클라 화면·로그 코드에서 이 필드를 읽는 곳 0|
|RANGE·LEVEL 표 로더|다섯 어셈블리 + Bs.Addressable·Bs.Core·Cs.UnityShare·K4os 디컴파일 전수에서 `BATTLE_POWER_RANGE`·`BATTLE_POWER_LEVEL`·`TeamADamageRate`·`TeamBDamageRate`·`LevelDistance`(표 열 이름) 0건. 로드 등록은 TRIBE 하나뿐(NKC:591762)|
|디컴파일 안 된 DLL|설치 폴더 `Data/Managed`의 `Bs.ServerLibrary`(네트워크·메시지 라이브러리), `Bs.ClientDb`·`Bs.Windows`·`Bs.Profiler`·`Bs.Rendering`·`FX`·`ASSET_EXTLIB`의 문자열 검색: BattlePower·DamageRate·PowerRange 0건|
|클라 로그|`LocalLow/studioBside/StarSavior/Logs` 5개(11/17–11/19): 배율·전투력 구간 로그 0건(디버그 로그는 파일에 안 남음)|

### 클라가 «표시»하는 값 — 현재 model과 대조

|항목|클라 근거|엔진|판정|
|---|---|---|---|
|전투력 비율 정의|ST:6514–6544 경고 구간 조회: `(long)전투력*10000/권장`(정수 내림), 부족분 = 10000 − 비율. 전투력 ≥ 권장이면 경고 없음|`power_pen`: `floor(전투력*10000/권장)`|같음|
|편성 전투력|NKC:92011–92013 → NKC:514826: 덱 4명 `OBF_29625` 합(오비탈·리더 보너스 없음)|`party_power` = 4명 합|같음|
|구원자 전투력 식|NKM:17465–17475, 17487–17504(최종 = 1차 × (1 + 한계 돌파×0.02 + 스킬 레벨 합×0.01)), 17544–17696(DEFAULT·BALANCE·CRIT_DEFAULT, MIX = 셋 중 최대). 상수 NT:30320–30389 ← `T/plain/CLIENT_CONST_TEMPLET.json` Battle 절(12, 10/55/5/5, Balance 1/1/1, CritDefault 0/1/0/2/3)|`build.unit_power`: 세 방식 최대 × (1+0.06+스킬 합×0.01), 같은 상수|같음. `T/CLIENT_UNIT_TEMPLET_BASE1.json`의 구원자 60명 전부 `BattlePowerCalculatorCategory=MIX`(ST:34130 기본 DEFAULT지만 실제 값은 MIX)|
|권장 전투력|NKC:92012 전투 표 `BattlePower`(ST:8116). 42-12 = T/CLIENT_BATTLE_TEMPLET_NORMAL.json BattleID 11042012 `BattlePower`|`st['bp']`|같음|
|경고 단계(21단계)|T/CLIENT_BATTLE_POWER_TRIBE_TEMPLET.json(ST:6548–6561 로더): 부족분 10–1000 주의, 1000–4800 경계·어려움·매우 어려움·악몽 각 5단계(200 간격), 4800 이상 악몽5|`data/power_penalty.json` tribe 21행|같음(새 시험으로 대조)|
|표 격자|RANGE의 배율 꺾임 20곳이 비율 5000·5200·…·8800, 보정 시작은 비율 9000 미만 = 경고 «경계 1»(부족분 10%) 시작과 같은 자리. 아군+적 배율 합은 500행 모두 20000|같은 표|모순 없음. 표를 «부족분»으로 읽는 해석(부족분 0–50% → 아군 ×0.1)은 영상의 준 피해(시뮬 패배 판과 비율 약 1.04)와 맞지 않아 기각|
|경고 문구|`tables/Strings/STRING_COMMON_ko_en.json` SI_BATTLE_*_DESC_CHANGE_*: «주의»엔 적 강화 언급 없음, «경계 1»부터 «적들이 강해지기 시작»|비율 90% 이상 1배, 미만부터 보정|문구의 시작점과 표의 시작점이 같음|
|보스 러시|NKC:92458: 덱 종류가 BossRush면 경고 표시 생략. 보스 러시 전투 표에는 권장 전투력이 있음(T/CLIENT_BATTLE_TEMPLET_BOSS_RUSH.json 44행)|`rush`는 보정 미적용|같은 방향(표시만이라 확정은 아님)|
|레벨 차 표|T/CLIENT_BATTLE_POWER_LEVEL_TEMPLET.json 14행(레벨 차 −5…+9). 로더 0건. 레벨 차 상수는 여정 전용(NT:29711–29712 `SafeJourneyBattleLevelDistance`·`RecommendJourneyBattleLevelDistance`)|미적용|작전 일반 전투에 쓴다는 클라 근거 없음|
|그 밖의 전투력 상수|`CombatPowerOverSpecRatio` 1.2·`CombatPowerUnderSpecRatio` 0.999(NT:30358–30359): 읽는 코드 0. `Front/BackClassBattlePowerCorrection`(NT:31737–31781): 자동 편성(AutoDeckSetting)용|해당 없음|피해 배율과 무관|

### 표 전수

이름에 POWER·COMBAT·PENALTY·GAP·SUPPRESS·RATIO·CP·CORRECT·HANDICAP·REVERSE·ADJUST가 들어간 표
(`rebuild_26752678/T`·`tmpl`·`plain`·`hardall`, `starsavior-static-data/tables`, 개별 전투·여정 유닛 파일 제외):
`BATTLE_POWER_RANGE_TEMPLET`·`BATTLE_POWER_LEVEL_TEMPLET`·`BATTLE_POWER_TRIBE_TEMPLET`·`OPERATION_BUFF_TEMPLET`(재점화, 엔진 연결됨)·
`ASYNC_TOURNAMENT_ENEMY_POWER_GROUP_TEMPLET`(PvP 상대 구간)·`TUTORIAL_OPERATION`. 피해 배율을 담은 것은 RANGE·LEVEL 둘뿐.
설치 폴더 에셋 번들(`Data/eb`)은 `rebuild_26752678`이 이미 푼 표와 같은 원본이라 다시 풀지 않았음.

## 바꾼 것

- `tests/power_penalty_client_test.py`(새 시험, 계정 자료 없음): ① 클라 비율 정의(정수 내림)와 엔진 `power_pen`의 행 선택이
  경계 양쪽 합성 값 11쌍에서 같음 ② 엔진 표 = 클라 RANGE 500행 ③ tribe = 클라 TRIBE 21행 ④ RANGE 꺾임 = TRIBE 격자·시작 90%.
  일부러 깨뜨림: `--mutate`(표를 부족분으로 읽기) → 1건 실패, `data/power_penalty.json` 한 행·tribe 한 칸 변조 → 3건 실패, 원복 후 통과.
  `STARSAVIOR_STATIC` 없으면 표 대조 2건만 건너뜀.
- `battlesim/rules/default.json` `power_penalty`: 값·legacy·grade 그대로, note·source에 위 조사 결과와 26752678 줄 번호 추가.
- `tests/fixtures/unsupported_allowlist.json`: 코스모 «전투력 보정» 항목의 키는 그대로 두고 사유·단서만 새 근거로 갱신
  (예전 사유의 NKC:83210–83224는 경고 아이콘 표시 부분 — 비율 계산 NKC:92443–92465·ST:6514–6544와 배율 전달 경로를 더함).
  `unsupported_allowlist.py --diff`: 추가·해소 키 0. 다른 담당 키는 손대지 않음.

## 결과 영향

엔진 코드 변경 없음(규칙 값·표 불변, 설명 문자열과 시험만 추가). 계정 자료 없이 같은 씨앗으로 돌린 결과가 전후 같음.

|대조|전|후|
|---|---|---|
|작전 42-12(내 정보, 200판, seed 7)|클리어 29%|클리어 29%. 요약 50항목 차이 0(원값은 비공개 폴더)|
|eq1113(60판)|—|변경 없음(엔진 코드 불변)|
|clo450(60판)|—|변경 없음|
|op4136-b(내 정보, 60판)|—|변경 없음|

42-12의 적용 행은 클라 표의 같은 행(아군 ×0.755·적 ×1.245)이며 엔진이 계산한 편성 전투력은 편성 화면 값과 같음.
즉 «보정이 실제보다 약하게 들어가서 승률이 높다»는 가설은 클라 자료로는 지지되지 않음.

## 남은 것 (클라로 확정 불가)

- 서버가 실제로 RANGE 표의 어느 행을 고르는지(비율 정의·경계 포함 여부·콘텐츠별 예외). 클라에는 고르는 코드가 없음.
  확정하려면 타격 결과 패킷의 `OBF_16839.OBF_22252`(실제 적용 배율)를 받아 봐야 함 — 클라 화면·로그엔 안 나옴.
- 비율 경계 한 칸 차이: TRIBE는 부족분 기준 반열린 구간이라 비율 정확히 9000·8800… 에서 RANGE와 한 단계 어긋날 수 있음
  (만분율 1칸, 실전 영향 무시할 수준). 서버 식이 없어 그대로 둠.
- LEVEL 표(레벨 차 배율)를 서버가 어떤 콘텐츠에 쓰는지.
