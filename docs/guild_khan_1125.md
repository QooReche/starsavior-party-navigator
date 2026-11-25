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
| 불타는 엔진 | 클라/tables/SE_TEMPLET_SKILL_2.json의 PASSIVE3 행 | 기존 웨이브 시작 궁극기 쿨 초기화 경로를 사용함 |
| 추가 궁극기 대상 | 클라/tables/SE_TEMPLET_SKILL_2.json:17400; 클라/tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json:80 | EnforceAutoTargetId=4, 생존 무작위 대상 |

규칙 정본은 `battlesim/rules/default.json`의 `khan_passives`임. `client`가 새 기본, `snapshot`이 종전 동작임.
`tests/guild_khan_rotation_test.py`는 실제 칸 정의로 중첩 경계·legacy 차이·과열·S1/S2/G2의 진행도와 미지원을 검사함.
미지원 0을 전체 클라 일치 판정으로 사용하지 않음. 전체 AI 분기·효과 적중 난수 순서의 실행 대조는 추가 확인 대상임.

## 보관·검증

30111의 BFB 수치·기준 시뮬 표를 `data/guild_seasons/30111/`에 보관했음. 공통 훅 분리 전후 78조건 골든과 지원·도전 경계·선택 효과 108조건 훅/타임라인이 동일했음.
골든 원본의 코스모 18조건은 현재 시즌과 맞지 않아 오류였음. 별도 정상 실행 비교에서는 기존 1022 fixture를 지정해 78조건 모두 실행했음.
108조건 기준선은 `6c4d3b0`에서 얻은 합성 표준 육성 결과 해시이며 계정 수치가 아님.

현재 추출본에 `JSON_GUILD_DUNGEON_G3_04.json`이 없음(클라/tables/BATTLE_TEMPLET_GUILD_DUNGEON.json:776 참조).
해당 단계는 실행 불가 사유를 보존함. 다른 단계 배치를 복사해 채우지 않았음.
