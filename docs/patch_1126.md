# 11/26 패치 대조 — PC 빌드 26935738

정본은 비공개 `starsavior-static-data`의 지정 커밋 `a9e2377`임. 설치본 buildid와 디컴파일 DLL 10개가 일치했음(`check_build.py` 종료 0). 아래 파일:줄은 해당 저장소 기준임. 원문 표·계정 수치는 이 문서에 싣지 않음.

## 반영과 공개 여부

| 항목 | 판정·클라 근거 | 변경 범위 |
|---|---|---|
| 길드 30112 | 반영함. `GUILD_DUNGEON_SEASON_TEMPLET.json:502`의 MAIN_OPEN·시즌 P5 기간 연결, `BATTLE_TEMPLET_GUILD_DUNGEON.json:2010` 이하 7전투와 CARBONPUNK_LORD 01~07 원배치. 50턴·BM_BOSS_KILL·난이도 그룹 2001 | 현재 보스 BFB → 카본펑크 칸. 7단계·시즌 지원·점수·직접 편성·공유·저장 키·콘텐츠 표시 |
| 길드 지원 4011202 | 반영함. `SE_TEMPLET_BATTLE_EFFECT.json:1587` 발동률 10000. 시전 시작에 한 번 굴리는 기존 공통 지원 실행기를 사용 | 해당 지원이 연결된 길드 시즌. BFB의 보관 모델·시뮬은 그대로 |
| 장비 21·22 | 반영함. 세 탭의 MAIN_OPEN 전투·해금·원배치 연결. `BATTLE_TEMPLET_NORMAL.json:173544,173642,175695,175793,177846,177944` | 장비 신규 6스테이지·적 8종·스킬 22개·목록/필터/직접 편성·빠른 계산 입력 |
| 소환 1021/1022 | 기존 실행기로 지원됨. `SKILL_TEMPLET_2.json:17592,17605`, `SE_TEMPLET_SKILL_2.json:36601`, `Plain/SUMMON_TEMPLET.json:464,487`. `NKM.decompiled.cs:5713,1224,15779`의 슬롯·생성 초기화·스킬 종료 처리 대조 | 페르세스 신규 두 단계. 스킬 종료, 슬롯 0/4, 시작 쿨, 강인도·공격 보정, 점유 슬롯 중복 소환 방지를 시험함 |
| ImmuneInfoId | **클라 미사용**. `UNIT_TEMPLET_BASE2.json:143`부터 기존 적 1,270행에 추가됐지만 디컴파일 10개 전체에서 문자열/필드 참조 0건. 실제 유닛 로더는 `Star.Templets.decompiled.cs:34050`에서 ImmuneGroupId를 읽음 | 엔진 변경 없음. 기존 면역 그룹과 임의 매핑하지 않음 |

신규 전투 행은 공개 태그만 보고 선택하지 않고 기간·탭·전투·배치까지 연결했음. 실제 공개 연결이 없는 행을 신규 적/스테이지로 추가하지 않았음. 신규 장비 등급·세트는 없음(EquipTier 1·2만 존재). 클라 전투 코드의 의미 있는 변경은 없으며 이번 엔진 수정은 모듈 분리임. 규칙 기본값·피해식·난수 흐름을 바꾸지 않았음.

## 이전 기준이 어긋났던 17개 표

`62bb6b6`의 표와 실제 26752678 추출본(`rebuild_26752678/T`)을 다시 비교해 17개를 확인했음. 이 차이를 11/26 신규 변경으로 세지 않음.

| 표 | 현재 상태 판정 |
|---|---|
| POTENTIAL_LEVEL_GROUP_TEMPLET | 23038·23040·23042 설명의 치명타 피해 8→6 교정임. 실제 PotenLevelStatRate는 600이고 기존 `growth.json`도 cd=600임. 능력치 재하향 없음. 근거 `:1704,1744,1784` 및 각 행의 PotenLevelStat |
| SKILL_TEMPLET_1 / SKILL_TEMPLET_2 | IsChangeSkill 삭제 6+5행. 빌더·엔진은 이 열을 소비하지 않음. 클라 로더는 누락 시 false(`NKM.Templets.decompiled.cs:42258`); 스킬 교체의 실제 효과/자동 대상 연결은 기존 구현을 유지함 |
| ARCANA_TEMPLET | 7102001·7106101의 AST_ATK는 분류 태그임(`:272,992`). 내 정보 계산·빌더에서 이 열 사용 없음. 실제 스탯 표를 계산하므로 결과 변경 없음 |
| RANKING_RAID_SEASON_TEMPLET / BATTLE_TAB_TEMPLET / BATTLE_TEMPLET_RANKING_RAID | 1023은 MAIN_OPEN이며 기존 현재 시즌임(`RANKING_RAID_SEASON_TEMPLET.json:467`). 현재 표를 다시 읽어 보스·3단계·난이도·시즌 버프를 기존 자료와 전수 비교해 동일했음. 바스커빌 3배치 조각도 재생성 값과 동일함 |
| BATTLE_EFFECT_TEMPLET / DIFFICULTY_LEVEL_GROUP / SE_TEMPLET_BATTLE_EFFECT | 이전 코스모 효과·난이도 연결은 위 재생성 대조에서 동일함. 길드 2001의 잠금 메타 변경은 실제 단계 수·효과를 추출하는 경로에서 처리함. 이번 지원 4011202만 확률 변경으로 구분함 |
| BUFF_TEMPLET | 301157의 m_bShowBuffText 표시 메타 변화임. 추가로 현재 번역과 공용 버프 이름 표의 불일치 2개를 고쳤음. 기존 ID 301067의 «패시브 3»→«끝나지 않는 사냥», 301157의 «패시브 카운트 버프»→«인과의 반향»임. 수치/플래그 변경은 없음 |
| CRAFT_REWARD_TEMPLET / NORMAL_ITEM_TEMPLET_1 | 제작·보상/일반 아이템 연결. 구원자 능력치·장비 아이템·장비 세트 계산 변경 없음 |
| EVENT_CUBE_POINT_REWARD_TEMPLET / EVENT_CUBE_SKILL_REROLL_GROUP_TEMPLET / EVENT_CUBE_TOTAL_POINT_REWARD_TEMPLET | 큐브 보상·재추첨 연결. 네비게이터 계산 콘텐츠 밖이므로 전투 엔진에 옮기지 않았음 |
| PVP_SEASON_GROUP_TEMPLET | 맵·시즌·강화 그룹 연결. 네비게이터 계산 콘텐츠 밖임. 공개 여부를 추정해 미공개로 단정하지 않음 |

## 영향 범위와 유지보수

- 추천·직접 편성이 같은 `guildOptions`/`GuildView.battleOptions`를 사용함. 일반 단계에서는 도전/가정 효과를 0으로 정규화하고 지원 선택은 유지함. 판별 점수를 평균해 기대 점수를 표시함.
- 길드 공유는 gs(시즌)·go(도전/가정 효과/지원)를 왕복함. gs 없는 옛 링크는 기존 30111 의미를 유지하고 현재 시즌과 다르면 만료 표시·실행 차단함. 저장은 시즌 ID·자료 버전별 키이며 이전 지원 이름을 새 시즌 지원으로 조용히 바꾸지 않음.
- 장비는 공용 foe 병합·콘텐츠 필터·직접 편성 경로로 21·22단계를 노출함. 기존 1~20단계와 코스모·격전·플래시 포인트는 같은 정의를 유지함. 길드 적의 한글 속성명을 추천용 영문 키로 변환하는 누락을 고쳤음.
- 내 정보 계산에 쓰는 성장표·장비/세트·아르카나 실제 수치가 같으므로 계정 수치 마이그레이션은 없음. 합성 내 정보로 새 단계의 현재/육성 스냅샷·직접 편성 경로를 검사함.
- 보스 모듈의 내용 해시가 다르면 새 정의로 등록하고 옛 파일을 보존함. 공통 foe·규칙·빠른 계산 자료를 복제하지 않으며 길드·코스모 시즌은 모듈을 선택함. 절차와 재등장 시험은 [PORTING](PORTING.md)의 모듈 절을 따름.

버프 이름 연결의 근거는 `BUFF_TEMPLET.json:51225,54695`와 `Strings/STRING_COMMON_ko_en.json:1`의 해당 m_BuffName 키임. 301067은 바스커빌 공개 시즌 1023의 패시브 SE(`SE_TEMPLET_SKILL_2.json:33934`)와 기존 foe 조각에 이미 연결돼 있음. 301157은 기존 EP8 전투 22401007/22401008의 MAIN_OPEN 행(`BATTLE_TEMPLET_NORMAL.json:213003,213064`), 배치 `JSON_NORMAL_BATTLE_MAINSTREAM_NORMAL_EP8_007.json:14`·`008.json:13`, 유닛 스킬과 SE(`SE_TEMPLET_SKILL_2.json:17049`)에 연결됨. 새 전투를 추가한 것이 아니며 이벤트 기간을 추정해 새 콘텐츠를 노출하지 않았음. 공용 면역 통과·버프 분류/중첩·사망 보존 표만 같은 ID의 현재 이름으로 생성했음. 이를 반영한 뒤에도 위 151조건의 결과 차이 목록은 동일했음.

전후 비교·최종 시험 수치는 `HISTORY.md`의 같은 날짜 절에 기록함. 서버 최종 점수의 배율 적용 후 반올림, 실제 점검 종료 시각 등 기존 미확인 사항을 이 패치로 확인됐다고 바꾸지 않았음.
