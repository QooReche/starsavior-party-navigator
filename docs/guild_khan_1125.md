# 길드 보스 로테이션·카본펑크 칸 대조

정본은 설치 PC 빌드 26752678임. `check_build.py`로 디컴파일 DLL 10개 일치를 확인했음.
아래 `클라/`는 비공개 starsavior-static-data임. 과거 시즌은 이 빌드에서 추출한 정의이며 당시 빌드 재현본이 아님.

## 칸 패시브

| 항목 | 근거 | 판정·시험 |
|---|---|---|
| GUILDRAID_01~07·RUSH_01~03의 스킬 6개 | 클라/tables/UNIT_TEMPLET_BASE2.json:114471,114502,114533,114564,114595,114626,114657,117191,117222,117253 | 동일 ID 목록임 |
| 기본기·특수기·궁극기 대상과 강인도 | 클라/tables/SKILL_TEMPLET_2.json:9593,9608,9623 | 단일/1·전체/1·단일/3. 범용 FoeDef 경로 사용함 |
| 오버클럭·오버히트 상한 | 클라/tables/BUFF_TEMPLET.json:42716,42778 | 각 5중첩 |
| 탑 기어 4→5 직후 추가 궁극기·삭제 | 클라/tables/SE_TEMPLET_SKILL_2.json:17354,17394,17409,17423; 클라/tables/Plain/SKILL_CONDITION_TEMPLET.json:7982 | 종전 일괄 조건 판정 때문에 같은 사건의 부여를 못 읽었음. 순차 재평가로 고쳤음 |
| 전체 공격 피격 4→5 직후 과열·게이지 0·삭제 | 같은 SE 표:17380,17437,17452,17465,17479; 같은 조건 표:1896,9586 | 같은 순서 결함을 고쳤음 |
| 과열 상태 기절 | 클라/tables/BUFF_TEMPLET.json:42783-42803 | 이름이 ‘기절’이 아니어서 행동 차단을 놓쳤음. 칸은 buff_flags의 기절·수면 속성을 읽도록 고쳤음 |
| 순차 SE 실행 근거 | 클라/decompiled/NKM/NKM.decompiled.cs:16103-16116,16374-16387 | SE마다 조건 검사 직후 효과 실행함 |
| 파워트레인 | 클라/tables/SE_TEMPLET_SKILL_2.json:17493; 클라/decompiled/NKM/NKM.decompiled.cs:10733-10739 | 아군 행동 후 경로는 있었음. 탑 기어 삭제 뒤 조건 재평가도 고쳤음 |
| 불타는 엔진 | 클라/tables/SE_TEMPLET_SKILL_2.json:17577-17585; 클라/tables/BUFF_TEMPLET.json:5910-5912; 클라/decompiled/NKM/NKM.decompiled.cs:2063-2078,3120-3131 | 웨이브 시작 궁극기 쿨 초기화. 감소값 0은 초기화이며 기존 경로와 일치함 |
| 추가 궁극기 대상 | 클라/tables/SE_TEMPLET_SKILL_2.json:17400; 클라/tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json:80 | EnforceAutoTargetId=4, 생존 무작위 대상 |

규칙 정본은 `battlesim/rules/default.json`의 `khan_passives`임. `client`가 새 기본, `snapshot`이 종전 동작임.
`tests/guild_khan_rotation_test.py`는 실제 칸 정의로 중첩 경계·legacy 차이·과열·S1/S2/G2의 진행도와 미지원을 검사함. `tests/guild_rotation_test.py`는 원래 배치의 보스 처치 승리와 all_kill 변이, 지원·점수·작업자 병합을 검사함.

## 스킬·SE·AI 전수 정적 대조

아래 표의 `표/`는 `클라/tables/`, `코드/`는 `클라/decompiled/`임. NKM 줄은 `NKM/NKM.decompiled.cs` 기준임.

| 항목 | 근거 파일:줄 | 판정·시험 |
|---|---|---|
| 6스킬의 SE 연결 | 표/SKILL_LEVEL_GROUP_TEMPLET_2.json:3014,3020,3026,3032,3038,3044 | 4+2+3+10+6+1=26개 SE. raw는 연소 2개를 묶은 25줄. 빌더가 줄 짝짓기를 검증하며 변경 시 중단함 |
| 기본기 피해·연소 | 표/DAMAGE_TEMPLET.json:3016; 표/SE_TEMPLET_SKILL_2.json:17224 | 공격력 65%, 단일, 강인도 1, 연소 1턴. raw skill110 일치 |
| 기본기 조건부 피해 | 표/SE_TEMPLET_SKILL_2.json:17236,17255,17274; 표/Plain/SKILL_CONDITION_TEMPLET.json:6680,6687,6695 | 오버히트 0/1/2에서 이번 스킬 피해 +10%. 조건과 이번 시전 한정 경로 일치 |
| 특수기 | 표/DAMAGE_TEMPLET.json:3020; 표/SE_TEMPLET_SKILL_2.json:17293,17305; 표/BUFF_TEMPLET.json:3784,3789,3842,3843,273,278,331,332 | 공격력 180%, 전체, 강인도 1, 쿨 3. 공격력 −30% 2턴은 효과 적중, 자기 속도 +20% 2턴은 확정. raw skill111 일치 |
| 궁극기 | 표/DAMAGE_TEMPLET.json:3024; 표/SE_TEMPLET_SKILL_2.json:17317,17330,17342; 표/BUFF_TEMPLET.json:5125,5130,5140,7072,7077 | 공격력 95%, 단일, 강인도 3, 쿨 5. 게이지 −20%와 연소 2턴 2개에 각각 효과 적중. 독립 SE 2회 시험함 |
| 탑 기어 자기/아군 발동 | 표/SE_TEMPLET_SKILL_2.json:17354,17367; 표/Plain/SKILL_CONDITION_TEMPLET.json:1451-1455,2595; 코드/NKM:10722-10739 | 자기 공격 후는 Enforce 제외, 다른 아군 행동 후는 자기 자신 제외. 기존 사건 경로와 일치 |
| 오버히트 부여 | 표/SE_TEMPLET_SKILL_2.json:17380; 표/Plain/SKILL_CONDITION_TEMPLET.json:1896-1900 | 전체 공격 피격 후 +1. 조건에 명중 결과 제한 없음 |
| 파워트레인·Enforce | 표/SE_TEMPLET_SKILL_2.json:17493-17573; 표/Plain/SKILL_CONDITION_TEMPLET.json:7990,7997,8005,2632,2639,2647; 코드/NKM.Templets/NKM.Templets.decompiled.cs:42314-42315,42519-42529 | 자기 공격/다른 아군 행동 후 오버히트 0/1/2면 +20%. Enforce 제외 조건 없음. 추가 궁극기 후에도 발동함. 삭제 후 재평가 시험함 |
| 중첩·과열 | 표/BUFF_TEMPLET.json:42716,42778,42783-42843; 코드/NKM:4443-4452,5073-5082 | 상한 5. 과열 피해 감소 −15%로 실제 피격 피해 1.15배, 기절로 일반/추가 행동 차단 시험함 |
| 강제 적용 | 표/BUFF_TEMPLET.json:42736,42796,8116; 표/SE_TEMPLET_SKILL_2.json:17437-17442 | 오버히트·과열·게이지 초기화는 ForceApply. buff_flags에 있음. SE의 EffectHitCheck=false 덮어쓰기 포함하여 강제 적용과 효과 적중을 구별함 |
| 기본 AI 순서 | 코드/NKM.Templets/NKM.Templets.decompiled.cs:28901-28906; 코드/Star.Templets/Star.Templets.decompiled.cs:33807,34122-34124; 코드/NKM:7104-7112 | SkillOrderList 없음: 궁극기→특수기→기본기. 기존 엔진과 일치 |
| 기본 AI 대상·필터 | 코드/NKM:7303-7308,7766-7809; 표/Plain/AUTO_SKILL_TEMPLET.json:233-237; 표/Plain/AUTO_SKILL_TARGET_TEMPLET.json:411-415 | 기본 규칙 1001: 전위 80%→디펜더 80%. 실패/빈 후보는 기존 후보 유지. RULE1001과 일치 |
| 추가 궁극기 대상 | 표/SE_TEMPLET_SKILL_2.json:17394-17400; 표/Plain/AUTO_SKILL_TARGET_TEMPLET.json:80-82 | 무변형 foe:55의 메타 누락을 보완함. 실제 4명 대상에서 직전 대상과 다른 무작위 선택 경로를 시험하고, 메타를 끄면 직전 대상을 쓰는 변이를 검출함. 추가 궁극기 실행 직전에 두 중첩이 0인지 검사함 |
| 강인도 | 코드/NKM:17211-17225 | 스킬값+상성+일반/고정 보정−감소. 1/1/3이 FoeDef ab로 전달됨 |
| 유닛 면역 | 표/BUFF_IMMUNE_TEMPLET.json:8-35; 코드/NKM:4318-4327 | 도발·기절·수면·침묵·강화 불가·쿨 증가 목록 일치. 과열은 별도 버프이며 강제 적용임 |
| 확정 SE 난수 | 코드/NKM:16504,16420-16432,16606-16616; 코드/Star.Templets/Star.Templets.decompiled.cs:29262; 코드/NKM.Templets/NKM.Templets.decompiled.cs:41933 | 칸 26 SE는 ActiveRate/BuffRate 10000. SELF/TARGET의 불필요한 확률 추첨을 제거하고 ENEMY_ALL의 대상별 BuffRate 추첨 유지. 자기 중첩 0회, 특수기 4대상 8회, 궁극기 연소 2회 난수 소비를 검사함 |
| 효과 적중·면역 순서 | 코드/NKM:4318-4327,4363-4379,4394-4398,20295 | 고유 면역/회피→효과 적중→약화 면역 순서. 칸 연소·공격력 감소의 순서를 고쳤음. 면역 대상에게 독립 연소 2개의 효과 적중을 먼저 검사하고 부여는 거부하는 시험함 |

수정은 `khan_passives=client`에 한정함. `snapshot`은 기존 동작을 보존하며 원래 존재하던 RUSH 변형 키의 대상 규칙도 유지함. 표의 지원 여부 0과 정적 대조를 클라 전체 전투의 시드별 결과 일치로 부르지 않음. 실제 클라 실행 로그와 동일 시드로 전투 전체를 비교하는 것은 아직 하지 못했음.

## 보관·검증

30111의 BFB 수치·기준 시뮬 표를 `data/guild_seasons/30111/`에 보관했음. 공통 훅 분리 전후 78조건 골든과 지원·도전 경계·선택 효과 108조건 훅/타임라인이 동일했음.
골든 원본의 코스모 18조건은 현재 시즌과 맞지 않아 오류였음. 별도 정상 실행 비교에서는 기존 1022 fixture를 지정해 78조건 모두 실행했음.
108조건 기준선은 `6c4d3b0`에서 얻은 합성 표준 육성 결과 해시이며 계정 수치가 아님.

칸 회귀 8항목은 중첩 경계·행동 차단·실제 과거 배치·추가 궁극기 대상과 중첩 초기화·확정 효과 난수·효과 적중 순서·과열 피해 감소·legacy 대상 규칙을 검사함. 스킬 또는 대상 메타를 끄는 변이에서 실패함. 길드 통합 11항목에는 10개 과거 시즌×6개 지원의 60조건, 시작 지원 생명력·다중 대상 조건·피격 지원·실제 판별 점수의 작업자 전달을 포함함.

최종 골든 78조건은 변경 전과 동일하고 실행 오류 0이었음. 미지원 측정은 349시나리오×3판(보관 시즌 10개 포함)이며 A/B/C/E 0, 기존 사유 등록 D 12로 증감 없음.

현재 추출본에 `JSON_GUILD_DUNGEON_G3_04.json`이 없음(클라/tables/BATTLE_TEMPLET_GUILD_DUNGEON.json:776 참조).
해당 단계는 실행 불가 사유를 보존함. 다른 단계 배치를 복사해 채우지 않았음.
