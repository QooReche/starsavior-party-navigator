# 브레이크 스킬 허용 목록 재조사 (2026-11-21)

## 범위와 자료

D의 `mc.break_skill_residuals`, `mc.add_damage_guard` 두 항목만 다룸.
PC Steam 26752678, `STARSAVIOR_STATIC=E:/AI_mk2/starsavior-static-data`의
`check_build.py`에서 설치본·디컴파일 DLL 10개 불일치 0을 확인했음.
이 문서의 NKM·NT·ST·NKC는 그 저장소 `decompiled/<어셈블리>/<어셈블리>.decompiled.cs`임.
NT는 NKM.Templets, ST는 Star.Templets를 줄인 이름임.
표 근거는 `E:/AI_mk2/rebuild_26752678/T/CLIENT_*.json`임.
3월판 코드는 사용하지 않았음. 계정 자료·비공개 표 원문은 넣지 않았음.

HEAL·ORBITAL_ARRAY·ORBITAL_DOMAIN·ORBITAL_LEVEL_GROUP·SE_ORBITAL_ARRAY·DAMAGE·NOVA_BURST
7개 표의 Data 행을 static-data/tables와 현재 추출본에서 비교했고 모두 같았음.
각각 26·8·8·80·5·910·69행임.

## 항목별 판정과 근거

|항목|판정|클라 근거와 처리|
|---|---|---|
|큐브 회복의 사망자 합산|고침|ORBITAL_ARRAY 103의 HtStrId → ST:24191,24250–24255 → HEAL의 HT_ORBITAL_ARRAY_OMEGA(107–108줄, AllyAllHpFactor=200) → ST:4014 → NKM:15747–15763,17934–17950. 합산 대상 OBF_19846은 NKM:1032에서 사망자를 제외함. 생존자의 현재 최대 HP 합으로 바꿈. 레벨 가산과 받는 회복량 증감·정수 절삭은 NKM:17909,17967–17979와 기존 heal 경로를 유지함.|
|브레이크 광역 피해 수호|고침|NKM:15832–15882,15983–16014는 최대 수호자를 마지막 대상으로 옮김. 7989–7990에서 수호자를 선택하고 18179–18185에서 방어 적용 전에 분리함. 8020–8033,2793–2810은 광역 수호 몫을 타격별로 모음. 7984–7990,18157–18158은 수호자 자신의 기본 피해에 그 몫을 더함. 수호자의 방어·난수·팀 계수는 한 번 적용함. 본 대상 무적/스킬 무효면 분리하지 않음.|
|개인 노바 풀 대체 모델|기본값 확인, legacy 구분|ORBITAL_ARRAY 101·104의 GetNovaForceValue=4 → ST:24197 → NKM:15811–15814에서 팀에 한 번 지급함. NKM:1040,1258–1273은 팀 풀·상한·차감, 14437–14465는 팀 풀로 버스트 가능 여부를 판단하고 소비함. 기본 opts.nova_pool=team은 맞았음. unit은 PC 규칙의 미확정 후보가 아니라 교정 전 대안으로만 보존함.|
|예약 고정 추가 피해 수호|고침|NKM:8149–8191의 예약 실행 → 17773–17818의 OBF_29161에서 수호 분리 → 8371–8387에서 수호 몫을 별도 계산함. 최대 비율 1명·동률 순서는 1286–1328. 본 대상 무적/스킬 무효면 분리하지 않으며 추가 피해는 무효 횟수를 소비하지 않음. 기존 client 분기를 기본으로 켬. 이 판정은 fixed_true_formula 전체의 별도 서버 입력 범위를 확정한다는 뜻이 아님.|

기본값·legacy·등급의 정본은 `battlesim/rules/default.json`임.
브레이크 잔여 항목은 설명 전용 note에서 실제 선택 스위치로 바꾸고,
옛 사망자 포함 회복·분담 생략을 `existing_model`로 보존함.
개인 노바 옵션을 팀 공용 풀과 같다고 주장하지 않음.

## 넓힌 조사 범위

NKM·NT·ST·NKC·Assembly-CSharp 다섯 어셈블리에서 표 문자열과 필드 접근을 검색했음.
오비탈 로더 `OBF_14671`의 `OBF_34390`(회복 표 키), `OBF_20090`(회복 템플릿),
`OBF_12693`(노바 지급), 회복 로더 `OBF_35147`의 `OBF_15795`(팀 HP 계수)를 따라갔음.
NT:40695–40713의 회복 인터페이스 `OBF_5346`, NT:41014의 스킬 노바 속성도 대조했음.
NKM의 `OBF_35437`(오비탈), `OBF_30373`(스킬 회복), `OBF_28556`(회복식),
`OBF_11886`(스킬 종료), `OBF_11233`(팀), `OBF_25942`(수호 선택),
`OBF_17803`(광역 순서), `OBF_36072`·`OBF_24387`(일반 피해),
`OBF_6680`·`OBF_7440`(수호 누적·정리), `OBF_33891`·`OBF_29161`·`OBF_13711`
(예약 추가 피해·수호 몫)을 확인했음.

tables/ 최상위에서 ORBITAL/BREAK/CUBE/NOVA/GUARD/SHARE/DAMAGE가 들어간 표는 21개였음.
GUARD·SHARE 전용 표는 없었고 수호는 버프의 NST_RATE_DAMAGE_SHARE로 표현됨.

|표|로더 등록 위치|
|---|---|
|BATTLE_TEMPLET_CUBE|ST:8079, OBF_15641|
|BATTLE_TEMPLET_EVENT_CUBE|ST:8080, OBF_4564|
|CUBE_PALACE_LEVEL_TEMPLET|NKC:591646, OBF_35163|
|CUBE_PALACE_SKILL|NKC:591695, OBF_32760|
|CUBE_PALACE_SKILL_GROUP_TEMPLET|NKC:591696, OBF_10777|
|CUBE_PALACE_WAVE_TEMPLET|NKC:591694, OBF_11961|
|DAMAGE_TEMPLET|NKC:558759,591585, OBF_29879|
|EVENT_CUBE_LEVEL_TEMPLET|NKC:591698, OBF_2731|
|EVENT_CUBE_POINT_REWARD_TEMPLET|NKC:591701, OBF_19769|
|EVENT_CUBE_SKILL_GROUP_TEMPLET|다섯 어셈블리에 이 이름의 로더 등록 없음. catalog에는 자산 존재. EventCubeSkillId·ReqSkillPoint 소비는 ST:14973–14988의 재추첨 그룹이며 브레이크 회복 표가 아님.|
|EVENT_CUBE_SKILL_REROLL_GROUP_TEMPLET|NKC:591699, OBF_15856|
|EVENT_CUBE_TAB_TEMPLET|NKC:591697, OBF_25731|
|EVENT_CUBE_TOTAL_POINT_REWARD_TEMPLET|NKC:591702, OBF_21390|
|EVENT_CUBE_WAVE_TEMPLET|NKC:591700, OBF_28846|
|LIMIT_BREAK_TEMPLET|NKC:558769,591598, OBF_12722|
|NOVA_BURST_TEMPLET|NKC:558778,591607, OBF_33417|
|ORBITAL_ARRAY_TEMPLET|NKC:558783,591732, OBF_14671|
|ORBITAL_DOMAIN_TEMPLET|NKC:558785,591734, OBF_25254|
|ORBITAL_LEVEL_GROUP_TEMPLET|NKC:558784,591733, OBF_20426|
|SE_TEMPLET_NOVA_BURST|ST:29246, OBF_8260|
|SE_TEMPLET_ORBITAL_ARRAY|ST:29246, OBF_8260|

추가로 HEAL_TEMPLET는 NKC:591586 → ST:3956–4018임.
UnitScript·BattleScript 하위 경로도 같은 이름 조건으로 전수 나열했음.
이름으로 분류한 뒤 큐브 오비탈 UnitScript의 HealEvent(25–33줄, 전체 아군)와
큐브 전투 BattleScript의 Waves·TeamBSpawnList도 읽었음. 회복 이벤트는
NKM:15747–15763에서 위 HEAL_TEMPLET 계산으로 연결되며, 배치 UnitStrId는
NT:37853의 UnitSpawnData로 읽힘. 회복 계수나 노바 풀의 다른 원천은 찾지 않았음.

설치 폴더 `F:/SteamLibrary/steamapps/common/StarSavior`는 읽기만 했음.
`Data/StreamingAssets/aa/catalog.json`을 이 작업 트리의 무시된 local/allow-brk에 복사하고
키 데이터를 해독해 CLIENT_HEAL_TEMPLET.bytes 및 위 21개 표 자산의 존재를 확인했음.
필요한 계산 데이터는 현재 추출본에 모두 있었으므로 설치 번들 수정이나 재추출은 하지 않았음.

## 시험과 결과 영향

허용 목록 담당 **2건 중 고침 2·남김 0**임. 하위 동작은 큐브 회복·브레이크 수호·예약 피해
수호를 고쳤고, 노바는 이미 맞는 기본값을 확인하고 교정 전 개인 풀 대안과 구분했음.
`tools/unsupported_allowlist.py --diff/--write`에서 담당 두 키만 빠졌음.
다른 D 항목과 E의 키·사유는 바꾸지 않았음.

새 시험 `tests/allowlist_break_test.py` 11개가 다음 경계를 검사함.
사망자 제외/legacy, 현재 최대 HP·레벨·회복 증감·버림, 수호자 마지막 순서·최대 1명·
분담 원값 누적, 대상별 난수 1회·보호막, 본 대상 무적/무효, 수호자 무효 1회 소비,
혼자 남은 수호자·사망자·legacy, 팀 노바 1회 지급·상한·공유 소비·개인 대안,
예약 피해 실제 flush 경로·무효 미소비·중복 flush를 확인했음.
사망자 다시 합산, 수호 제거, 누적 제거, 수호자 순서 복원, 무효 대상 분담,
노바 인원수 배수 지급, 타격 중 바뀐 수호자의 별도 분담 제거, 예약 피해 분담 제거의 8개 변이에서 모두 assertion 실패를 확인하고 원복했음.
옛 회복 기대값 시험은 legacy 스위치로 고정했고 결과 해시는 바꾸지 않았음.

재현:

```text
python -X utf8 -I tests/allowlist_break_test.py
python -X utf8 -I tests/allowlist_break_test.py --mutations
python -X utf8 -I tools/measure_allowlist_break.py legacy --legacy
python -X utf8 -I tools/measure_allowlist_break.py break-only --break-only
python -X utf8 -I tools/measure_allowlist_break.py after
```

표준 육성 편애의 마녀·구원자 길레·아모라·웨딩 카르멘, seed=20261121, 조건당 8판임.
모굴루스·벨그라스는 3단계·도전0, 브레이크 레벨1임. 벨그라스는 공개 시즌1022 fixture를 씀.
실제 수정 전 기록과 legacy 재실행의 진행도·승패·턴·점수가 모두 같았음.
모든 표본에서 진행도 >0을 검사했음. 점수는 각 판의 점수를 구한 뒤 평균했음.

|시나리오|평균 점수 전→후|클리어 전→후|평균 진행도 전→후|
|---|---:|---:|---:|
|태양 회랑250·큐브 과부하|게임 점수 없음|7/8→7/8|99.69%→99.69%|
|모굴루스·큐브 과부하|2,654,781.25→동일|0/8→0/8|84.08%→84.08%|
|벨그라스·특이점 관측|3,144,468.75→동일|5/8→5/8|97.61%→97.61%|
|수호 통제 입력·브레이크 잔여만 전환|2,339,718.75→2,311,468.75|0/8→0/8|70.07%→68.96%|
|같은 통제 입력·추가 피해 분담도 전환|2,311,468.75→1,808,343.75|0/8→0/8|68.96%→49.23%|

태양 회랑의 사망자 동반 큐브 발동은 6→5회, 총 발동19→18회였고 클리어 판의
모델 턴 중앙값은 3.27→3.01임. 모굴루스도 사망자 동반 큐브2회가 실제 실행됐음.
점수·승률이 같은 표본에서도 수정 경로를 탔음을 확인했음.

**수호 통제 입력은 실제 게임 스테이지 조건이 아님.** 표준 육성 파티와 벨그라스 공개 표는
그대로 두고 마지막 적에게 수호50%를 부여해 두 분기가 실행되는 조건을 만들었음.
브레이크 분담24회·예약 피해 분담16회가 실제 실행됐음. 일반 벨그라스 표본은 예약 피해16회지만
수호 대상이 없어 분담0회임. 통제 입력의 점수 감소를 실제 벨그라스 성능 변화로 해석하지 않음.

수정 전 전체 기준선은 242파일 통과·2실패였음. 두 실패는 COSMO_TABLES를
`rebuild_26752678`로 잘못 지정해 `hard/STRING_COMMON.json`을 못 읽은 것임.
`rebuild_26752678/T`로 바로잡아 cosmo_raid_test·cosmo_s23_test를 재실행하니 둘 다 통과했음.
기준선 때 엔진 파일은 변경 전이었음. 브레이크·규칙·캐시 관련 시험도 통과했음.

첫 수정 후 전체 재빌드는 244파일 통과·1실패였음. 기존 client_rules_1111_test의
고정 피해식 시험이 새 수호 기본값까지 물려받아 옛 식 기대값과 달라진 것이었음.
그 시험은 add_damage_guard=off를 명시해 식 비교 범위를 유지했고 16개 모두 통과했음.
새 기본값의 실제 예약 피해·수호 경로는 allowlist_break_test에서 별도로 검사했음.

quick 보정 입력은 `tools/gen_quick_calib.py:69–78`의 브레이크 미장착 일반 stage임.
브레이크 변경 분기는 미장착이면 반환하고, 예약 추가 피해는 cosmo 속성이 있는 시즌 컨트롤러에만
연결됨(`battlesim/mc.py`의 컨트롤러 생성·브레이크 활성 검사). 따라서 이 두 변경은 기존 quick
보정 입력에 영향이 없어 계수는 유지하고 도장에 사유를 적었음. 시즌4 종료 상태의 guild_sim은
기존 방침대로 새 시즌 자료 반영 때 다시 만들며, 현재 결과 불변을 주장하지 않음.

독립 리뷰는 작업 트리가 아니라 `d56506e..2c19e9f` 불변 범위로 수행했고 확정 결함0이었음.
리뷰에서 직접 시험이 없다고 지적한 타격 중 수호자 변경 경로는 회귀·변이1개씩을 추가해 확인했음.
최종 `python -X utf8 -I tools/run_tests.py --rebuild`는 공용 잠금을 잡고 실행해
245파일 통과·실패0·건너뜀0으로 끝났음. 워커·브라우저 e2e는 실행하지 않았음.
