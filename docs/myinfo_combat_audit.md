# 내정보 전투 효과 감사

2026-10-22, `feat/myinfo-combat`, `E:\AI_mk2\pn-omit`에서 작업했음. 커밋·푸시하지 않았음. 비공개 표·해독 코드·샘플은 제자리에서 읽었음. 원본을 공개 파일에 복사하지 않았음. 생성·계산·시험은 IDLE 우선순위로 실행했음.

내정보 경로에서 **습득 잠재력의 전투 효과와 추가 강인도가 빠졌음**. 스킬은 최대 레벨 효과를 쓰고 있어 실제 레벨로 교정했음. 장비 세트·각인·호감도·전술에서 별도의 피해 배율을 발견하지 못했음. 큰 보스전 조기 전멸은 남았음. 실측에 맞춘 임의 배율은 추가하지 않았음.

아래 표 파일명은 `E:\AI_mk2\starsavior-static-data\tables\`, 해독본 파일명은 `E:\AI_mk2\star-savior-decompiled\` 기준임. 해독본은 3월판이므로 구조 근거로 사용하고 수치는 현재 표를 사용했음. 결과에는 가공한 효과·집계만 남겼음.

1차는 웨딩 에핀델·크리스텔·화이트 펄 루나·웨딩 카르멘을 조사했음. 기존 실측 도구의 2차는 클레어·왈츠 아세라·**웨딩 카르멘**·프로페서M임. 요청의 ‘카르멘’이 일반형을 뜻할 가능성도 있어 일반 카르멘을 별도 감사했음. 실측 5판 편성은 바꾸지 않았음.

## 화면 능력치에 포함된 항목

장비 세트 12종 전부를 검사했음. SetStat 외에 전투 SE·보스 피해·조건부 발동 필드가 없었음. 치명 세트도 화면 능력치임. 기존 `final_stats`가 완성 횟수만큼 합산하므로 다시 더하지 않았음.

| 대상 | 완성 세트에서 계산한 합계 | 화면 8종 포함 | 근거 |
|---|---|---|---|
| 웨딩 에핀델 | 치확 +30%p, 공격 비율 +5%, 저항 +5%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:83,98 |
| 크리스텔 | 공격 비율 +20%, 적중 +20%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:38,68 |
| 화이트 펄 루나 | 치확 +15%p, 적중 +40%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:38,118 |
| 웨딩 카르멘 | 생명 비율 +40%, 저항 +5%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:138,168 |
| 클레어 | 치피 +40%p, 공격 비율 +5%, 저항 +5%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:98,153 |
| 왈츠 아세라 | 치확 +30%p, 생명 비율 +10%, 저항 +5%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:83,168 |
| 프로페서M | 치확 +30%p, 적중 +20%p | 포함 | EQUIP_SET_OPTION_TEMPLET.json:38,83 |
| 일반 카르멘 | 완성 세트 기여 0 | 별도 전투 효과 0 | EQUIP_SET_OPTION_TEMPLET.json:8 |

| 항목·대상 | 값과 판정 | 화면 8종 포함 | 근거 |
|---|---|---|---|
| 각인, 조사한 8종 모두 | 단계마다 공·생·방 비율 +2%. 스킬 강화 필드 없음 | 포함 | STAR_GRADE_TEMPLET.json:1296,2101,4516,5321,5482,6448,6609,6770 |
| ★, 조사한 8종 모두 | ★1 고유 패시브 해금, ★2/3 레벨 상한 180/200. 별도 스킬 배율 없음. 패시브는 실제 레벨을 선택했음 | 상시 스탯은 포함, 조건부 SE는 미포함 | LIMIT_BREAK_TEMPLET.json:184,294,624,734,756,888,910,932 |
| 호감도, 조사한 8종 모두 | 공·생·방 정수 보상뿐. 비능력치 전투 효과 0 | 포함 | FAVOR_TEMPLET.json:10919,17739,38199,45019,46383,54567,55931,57295 |
| 전술·시설, 두 편성 공통 | 전술은 공·생·방 정수, 시설은 기존 비율 버킷. 비능력치 전투 효과 0 | 포함 | CENTRAL_TACTICS_TEMPLET.json:6; CENTRAL_FACILITY_TEMPLET.json:6; NKM/NKM.decompiled.cs:18846 |

## 누락된 습득 잠재력

아래 전투 효과는 모두 화면 8종에 **포함되지 않음**. 조사 대상에서 모두 습득 Lv1 효과였음. 같은 잠재력의 상시 8종 스탯은 제외하고 전투 효과와 강인도만 추가했음. 미습득 Lv0은 할인·계승 레벨이 있어도 실행하지 않았음.

| 잠재력 | 해당 유닛 | 전투 효과·값 | 근거 |
|---|---|---|---|
| 11003 운명의 길 | 화이트 펄 루나 | 자신/아군 턴 시작 표지 +1, 최대 5. 스킬 사용 후 스택마다 무작위 적에게 공격력×32% 연쇄 피해, 이후 표지 소거 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:8; SE_TEMPLET_POTEN.json:9,44; BUFF_TEMPLET.json:20137 |
| 11055 사랑의 행진 | 웨딩 카르멘 | 강인도 +1. 특수기 또는 궁극기 사용 후 노바 +2 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:94; SE_TEMPLET_POTEN.json:612 |
| 23007 두 번째 심장 | 웨딩·일반 카르멘 | 강인도 +2. 웨딩 카르멘은 위 항목과 합쳐 기본 3→6 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:1120 |
| 25002 스택 트리거 | 프로페서M | 특수기 타격 후 특수기 피해 +5%씩, 최대 5중첩(+25%) | POTENTIAL_LEVEL_GROUP_TEMPLET.json:1964; SE_TEMPLET_POTEN.json:712; BUFF_TEMPLET.json:19373 |
| 30001 확고한 믿음 | 일반 카르멘 | 최초 전투 시작에 최대 생명력 20% 보호막, 2턴 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:1982; SE_TEMPLET_POTEN.json:784 |
| 30005 신중한 전술 | 화이트 펄 루나·일반 카르멘 | 턴 시작 노바 +2, 발동 후 2턴 제한 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2025; SE_TEMPLET_POTEN.json:862 |
| 32003 날렵한 자세 | 프로페서M | 단일 대상 특수기 타격 후 행동 게이지 +20%p, 1턴 제한 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2103; SE_TEMPLET_POTEN.json:1072 |
| 33001 표적 정렬 마법진 | 웨딩 에핀델 | 턴 시작 치피 +10%p씩, 최대 3중첩(+30%p) | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2130; SE_TEMPLET_POTEN.json:1129; BUFF_TEMPLET.json:18924 |
| 33004 진홍의 맹세 | 웨딩 에핀델 | 전체 공격 후 증표 2턴(피해 증가·감소 각 +10%). 증표 상태 타격에 별도 피해 +15% | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2157; SE_TEMPLET_POTEN.json:1182; BUFF_TEMPLET.json:2990 |
| 40005 AX5 | 크리스텔·클레어·프로페서M | 턴 시작 공격 비율 +8%씩, 최대 5중첩(+40%), 궁극기 사용 후 초기화 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2317; SE_TEMPLET_POTEN.json:1398; BUFF_TEMPLET.json:19698 |
| 40102 BX2 | 웨딩·일반 카르멘 | 피격 후 25% 확률로 최대 생명력 8% 회복 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2422; SE_TEMPLET_POTEN.json:1434 |
| 40405 EX5 | 웨딩 에핀델·화이트 펄 루나·왈츠 아세라 | 자기 턴 기본기 치명타 후 25% 확률로 무작위 아군 기본기를 무작위 적에게 추가 발동, 1턴 제한 | POTENTIAL_LEVEL_GROUP_TEMPLET.json:2974; SE_TEMPLET_POTEN.json:1510 |

AX5의 상시 공격 +8%·치확 +5%p, BX2의 생명 +12%, EX5의 치확 +15%p는 화면에 이미 포함되어 재가산하지 않았음. 강인도는 8종 밖이므로 더했음. 연쇄는 기존 방어 적용·×1.85 경로를 사용했음. EX5는 일반 협공과 분리된 추가 시전으로 처리했음. 재발동 제한은 재귀 시전 전에 예약했음.

잠재력 SE는 `[ID,a,b,c]` 중 `a`를 사용했음. 할인 `b`와 계승 레벨 `c`를 전투 레벨로 사용하지 않았음. 근거: NKM.Templets/NKM.Templets.decompiled.cs:18436; NKM/NKM.decompiled.cs:2470,2481,18628; Star.Templets/Star.Templets.decompiled.cs:21540,21651,21665.

### 표준 build와의 차이

표준 build는 추천 특수 잠재력 하나만 골라 비능력치 줄을 넣었음. 현재 기본 설정에서 에핀델·크리스텔·아세라·M은 AX5, 루나·클레어는 AX1, 카르멘 두 종류는 BX2였음. 내정보는 build=none이라 이 조건부 줄까지 빠졌음. 추천과 실제 소유가 다르므로 표준 build를 켜지 않고 실제 습득 목록 전체를 사용했음. 표준 build와 내정보가 동시에 입력되면 내정보가 표준 build를 대체하게 했음.

근거: battlesim/starsavior/build.py:147,190,230; battlesim/starsavior/parser.py:314; battlesim/api.py:88.

## 스킬 레벨

기존 엔진은 `ef`·`cdm`의 최대 레벨 효과를 사용했음. `L.e[L.ei[level-1]]`의 완성된 효과 목록과 해당 레벨 설명문을 선택하도록 했음. 이전 레벨 줄을 무조건 누적하지 않았음. 쿨타임은 표의 레벨 감소를 누적했음. 조사한 실제 레벨은 쿨 감소 해금 이후라 최대 레벨과 쿨타임은 같았음. 더 낮은 레벨도 시험했음.

샘플의 스킬 입력 필드 자체는 전재하지 않고, 선택 결과의 전투 효과 차이만 기록했음. 피해 수치 순서는 기본/특수/궁극임.

| 유닛 | 최대 레벨→실제 레벨에서 계산한 전투 효과 | 근거 |
|---|---|---|
| 웨딩 에핀델 | 스킬 피해 증가 15/15/15%→8/7/7% | SKILL_LEVEL_GROUP_TEMPLET_1.json:26872,27065,27258,27451 |
| 크리스텔 | 피해 15/15/15%→8/15/7%. 기본기 게이지 +30→18%p | SKILL_LEVEL_GROUP_TEMPLET_1.json:8426,8619,8812,9005 |
| 화이트 펄 루나 | 피해 10/25/15%→6/15/7%. 아군 치명 피격 후 점화 확률 100→60% | SKILL_LEVEL_GROUP_TEMPLET_1.json:21835,22028,22221,22414 |
| 웨딩 카르멘 | 기본기 피해 +10→6%. 궁극기 주는 회복 보정 +20→12% | SKILL_LEVEL_GROUP_TEMPLET_1.json:26245,26438,26631,26824 |
| 클레어 | 피해 15/15/15%→8/8/8% | SKILL_LEVEL_GROUP_TEMPLET_1.json:21208,21401,21594,21787 |
| 왈츠 아세라 | 이미 최대 레벨과 같았음 | SKILL_LEVEL_GROUP_TEMPLET_1.json:25611,25804,25997,26190 |
| 프로페서M | 피해 15/15/15%→8/7/7%. 아군 공격 시 냉각 확률 100→75% | SKILL_LEVEL_GROUP_TEMPLET_1.json:18059,18252,18445,18638 |
| 일반 카르멘 | 피해 10/10/10%→6/5/5%. 냉각 중첩당 피격 직전 방어 +4→3%(최대20→15%) | SKILL_LEVEL_GROUP_TEMPLET_1.json:5070,5263,5456,5649 |

위 조건부 피해·게이지·확률·회복·피격 직전 방어는 **화면 8종에 포함되지 않음**. 고유 패시브의 상시 공·생·방은 이미 실제 레벨로 화면 스탯에 계산되어 `stats_final`에서 재가산을 막았음. 여러 효과를 낮추는 교정이라 잠재력 추가와 반대 방향으로 작용했음.

`SkillLevelDamageUp`는 공격 계수가 0이 아닐 때 계수에 더하는 별도 필드임. 현재 SKILL_LEVEL_GROUP_TEMPLET_1/2에는 해당 필드가 없어 0임. 이를 누락된 큰 배율로 넣지 않았음. 현재 레벨 피해 증가는 SE의 `NST_RATE_DAMAGE_UP`이며 기존 가산 증가 경로에 실제 레벨 값으로 넣었음.

근거: NKM/NKM.decompiled.cs:17744,17757; Star.Templets/Star.Templets.decompiled.cs:25778,25782; SE_TEMPLET_SKILL_1.json:23168,33725,34084; battlesim/starsavior/parser.py:208.

## 축복 목록 해석 시도

| 항목 | 확인한 내용 | 판정 |
|---|---|---|
| potentials의 c | SE 등록·스탯 계산이 사용하는 a와 별도 필드. a=0,c>0에서 전투 SE 등록 근거 없음 | 직접 전투 효과 추가 0 |
| BLESS_SUCCESSION_TEMPLET | 20행, 계승 그룹·StarLv만 있음. 전투 SE/피해 스탯 없음 | 목록 ID→전투 효과 매핑 불가 |
| POTEN_TO_BLESS_TEMPLET | 20행, 변환 그룹·PotenLv·여정 점수 가중치만 있음 | 직접 전투 효과 아님 |
| STAT_POTENTIAL_TEMPLET | 45행, JST 여정 능력치. 조사 대상 blessings 값이 이 표와 SE_POTENTIAL의 PotenId에 매칭되지 않았음 | 여정 최종값에 재가산 금지 |
| gauntlet.blessings | 3월 클라이언트 별도 목록은 관문 이력 UI로 연결됨. 현재 내보내기 col13과의 동일성은 확정 못했음 | 미해석 표시 유지. 화면 포함 여부도 미확정 |

근거: BLESS_SUCCESSION_TEMPLET.json:6; POTEN_TO_BLESS_TEMPLET.json:6; STAT_POTENTIAL_TEMPLET.json:6; NKM/NKM.decompiled.cs:2470,18628; NKC/NKC.decompiled.cs:231872,232478,268033.

## 구현과 재현

- 표와 기존 공개 DB를 대조해 수치·공개 효과 줄 인덱스만 `data/myinfo_combat.json`에 생성했음. 원본 설명문·조건 본문·계정 파일을 복사하지 않았음. 55종 스킬과 185종 잠재력의 레벨 연결을 생성했음.
- Python/JS `final_stats`에 `combat`을 추가했음. 스킬 레벨과 유효한 습득 잠재력 ID/레벨만 엔진에 전달함. 장비·여정·blessings 이력은 전달하지 않음.
- API `myinfo_combat`을 `mc.myinfo_combat`(grade=code, 기본 true, legacy=false)로 제어했음. 입력 없는 기존 호출은 유지했음. 미지 잠재력과 미지원 상시 스탯은 `unsupported`로 기록함.
- 무작위 아군 추가 시전과 무작위 적 연쇄 대상의 엔진 분기를 추가했음. 나머지는 기존 조건·스택·회복·노바 실행 경로를 사용했음.
- template과 생성한 index에 입력을 연결했음. worker는 party 객체를 그대로 넘기므로 변경이 필요 없었음. 새 Python 모듈·가공 JSON을 manifest에 넣었음.

근거: tools/build_myinfo_combat.py:1; battlesim/starsavior/myinfo_combat.py:1; battlesim/api.py:88; myinfo_stats.js:201; party_template.html:603; sim_worker.js:15,37; tools/build_simpack.py:14.

```text
python -X utf8 tools/build_myinfo_combat.py
python -X utf8 build_party_html.py index.html
python -X utf8 tools/build_simpack.py
python -X utf8 tools/ingame_check.py --runs 60 --bs --myinfo <비공개 샘플 경로>
python -X utf8 tools/myinfo_combat_audit.py --runs 60 --myinfo <비공개 샘플 경로>
```

빌더·시험은 IDLE 부모/자식 프로세스로 실행했음. HTML 빌더 기본 목적지가 다른 release 폴더여서 처음 실행은 권한 오류로 실패했음. 목적지를 `index.html`로 명시해 이 worktree 안에 생성했음.

## 60회 × 5판 대조

seed=7, 큐브 과부하 Lv5, 36-36은 heal·재점화3·리더 없음, 나머지는 auto·재점화0·웨딩 카르멘 리더를 유지했음. before는 수정 전 실제 실행값임. 수정 후 규칙 false의 결과와 집계 필드가 전부 같음을 확인했음. after도 요청한 ingame_check 독립 실행과 감사 도구 결과가 같았음. 집계만 `docs/myinfo_combat_results.json`에 저장했음.

| 판 | 준/받은 피해 전→후 (실측) | 클리어 전→후 | 아군 행동 전→후 | 적 행동 전→후 | 전체 행동/TURN 전→후 |
|---|---|---|---|---|---|
| 36-36 | 0.96→1.09 (1.88) | 0→0% | 16.4→16.8 | 16.03→16.95 | 0.854→0.889 |
| 37-2 | 3.80→4.80 (4.13) | 98.33→98.33% | 45.5→38.5 | 20.48→17.02 | 1.269→1.067 |
| 37-3 | 0.95→1.05 (1.82) | 0→0% | 22.3→23.7 | 12.72→13.47 | 0.815→0.864 |
| 37-4 | 5.63→5.55 (6.52) | 100→100% | 15.5→14.9 | 6.10→6.12 | 1.660→1.621 |
| 37-5 | 7.03→7.09 (4.17) | 100→100% | 19.4→18.4 | 5.03→5.02 | 1.111→1.064 |

아군 행동당 준 피해는 36-36 25,709→31,439(+22.3%), 37-3 17,580→20,262(+15.3%)였음. 37-2는 23,688→27,990, 37-4는 32,643→33,807, 37-5는 35,194→37,107이었음. 추가 시전은 피해에 포함되고 전역 행동 수에는 포함되지 않음. TURN은 전역 행동임. 실측 아군 비중을 시뮬과 같다고 가정한 피해 부족 배율은 수정 후 큰 보스에서 1.67/1.61배였음. 이 비중은 관측값이 아님.

일부 부족분은 설명했지만 큰 보스전 전멸은 해결하지 못했음. 잡몹전 비율이 실측을 넘어선 경우도 있어 공통 배율을 추가하지 않았음. 37-4 보스 사망 뒤 종료/오버킬 집계와 37-5 적 시작 궁극기는 기존 별건으로 유지했음.

## 시험과 남은 것

`tests/*.py` 실행 대상 20개를 전부 통과했음(golden_check 포함, run_workspace_test 자체는 실행 보조임). web/quick/shim_compat는 지정한 run_workspace_test 경로로 실행했음. JS 7개 파일도 전부 통과했음. 합성 새 Python 시험 13개와 JS 입력 시험을 추가했음. Python/JS 능력치 일치와 비공개 화면 정답 검사는 기존 기준을 유지했음.

새 시험은 스탯 중복 방지, 강인도, 실제 레벨 SE·쿨타임, 미습득/미지 입력, 스택 상한·초기화, 루나 연쇄 계수·소비, 무작위 대상, EX5 자기 턴·1회 제한, 노바 주기, 웹 Python 진입점·manifest, DB 불변, 가공 데이터 재생성을 확인했음. 잠재력 제거·최대 레벨 강제·EX5 제거·무작위 적 선택 제거의 고장 주입 4개가 각각 assertion 실패를 내는지 확인하고 복원했음. 55종 최대 레벨 선택 결과도 기존 공개 효과·쿨타임과 일치했음.

근거: tests/myinfo_combat_test.py:1; tests/myinfo_combat_test.js:1; tests/myinfo_reco_test.js:29; tests/boss_recheck_test.py:74; tests/myinfo_stats_test.py:1; tests/run_workspace_test.py:1.

남은 것은 blessings의 현재 빌드 의미와 큰 보스전 잔여 피해/생존 격차임. 이번 두 편성에서 새로 연결한 잠재력의 미지원 줄은 없었음. 다른 유닛의 8종 밖 상시 협공·흡혈·반격·스킬별 피해/감소 등은 가공 데이터에서 감지하지만 강인도 외 항목은 이번에 적용하지 않고 `unsupported`로 남겼음. 다른 모든 잠재력의 대상·조건·타격 시점까지 새로 검증한 것으로 확대 해석하지 않았음. 재보정·커밋·푸시하지 않았음.
