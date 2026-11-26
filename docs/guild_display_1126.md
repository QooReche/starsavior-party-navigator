# 11/26 길드 표시 문구·자료 버전

설치 클라와 static-data 디컴파일은 buildid 26935738, DLL 10개 해시가 일치함.
아래 표·디컴파일 경로는 비공개 starsavior-static-data 기준임.

## 생명력 감소 문구

- 공통 기본값의 hpDrain을 «보스가 맞으면 때린 쪽의 최대 생명력 -{v}%씩 쌓임(최대 10회)»로 고쳤음. 사용자 제공 게임 화면 원문은 적 보스 피격 후 타격자의 최대 생명력 감소임.
- 선택 세트 «쇠락»도 현재 표에서는 보스를 때린 쪽이 대상임. `tables/DIFFICULTY_ADD_POINT_TEMPLET.json:218`의 200103은 92051~92053을 참조함. `tables/SE_TEMPLET_BATTLE_EFFECT.json:6330`부터 각 SE는 `NSEAT_DAMAGE_END`, `NSETT_AUTO_ENEMY_ONE`, AutoTargetId 17임. `tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json:156`의 17은 `IsLastDamageTarget=true`(자신을 마지막으로 공격한 유닛)임. 자동 대상 처리는 `decompiled/NKM/NKM.decompiled.cs:16583`임. 따라서 «보스가 맞으면 때린 쪽의 최대 생명력 -3/4/5%»로 고쳤음. 계산에 쓰이는 숫자는 불변임.
- 생성기가 공통 기본값을 보관 시즌·BFB 최상위/내장 client 정의에 반영함. 시즌 사본을 수동 치환하지 않음.

## 선택 효과 연결 조사

- `tables/DIFFICULTY_ADD_POINT_GROUP.json:80`부터 길드 그룹 2001, 선택 세트 제목 1~4, MAIN_OPEN이 정의됨. `tables/DIFFICULTY_ADD_POINT_TEMPLET.json:176`부터 효과와 추가 점수 5/10/15%가 정의됨.
- 92041~92043은 선택 세트뿐 아니라 별의 도전 10~12단계 고정 효과로도 재사용됨(`tables/DIFFICULTY_LEVEL_GROUP.json:6228,6257,6286`). 사용자 제공 길드 «별의 도전 EX» 화면에는 단계 목록·도전 효과·보스 능력치·추가 점수만 있고 선택 세트 UI가 없음. 표 정의와 화면 노출은 구분함.
- 새 확인 사항: `decompiled/NKM.Templets/NKM.Templets.decompiled.cs:19323,19332` 길드 전투 시작 요청에 `List<int> OBF_4093`과 직렬화가 존재함. 실제 길드 요청 생성부 `decompiled/NKC/NKC.decompiled.cs:151692`는 그 필드를 대입하지 않아 기본 빈 목록임. 같은 식별자 필드는 BossRush 요청에서 선택 목록으로 채워짐(`:320400`). 이 사실만으로 길드에서 선택값을 전송·적용한다고 확정하지 않음.
- 길드 전투 템플릿은 단계 난이도 인터페이스를 사용함(`decompiled/Star.Templets/Star.Templets.decompiled.cs:6661,6687`). 길드 준비 화면도 `starChallenge.UpdateView`에 단계 그룹을 전달함(`decompiled/NKC/NKC.decompiled.cs:73385`). 새 패킷 필드에 관한 재판정 전에는 숨김 변경을 보류함.

## 자료 버전

- `tools/guild_version.py:season_version`이 펼친 시즌의 계산 입력을 해시함. 추출·현재 선택 모두 같은 함수를 쓰며, 엔진 `guild.identity`·화면은 저장된 버전을 소비함. 적 스킬 서명·파일 무결성 해시는 용도가 다르므로 그대로 둠.
- 재귀 제외: `effectText`, `note`, `statNote`, `provenance`, `asOf`, `gameBuild`, `source`, `sources`, `src`, `conf`, `_note`, `minionsNote`. 생성기의 문구·출처·신뢰도·추출 메타이며 길드 전투/지원/점수 입력으로 읽지 않음.
- 경로 한정 제외: `season.label/name/start/end/settleEnd/intervals`, `sets.scope`, `sets.items[].name`, `supports[].name`, `score.hypotheses[].name/desc`, `search.excludeWhy`. 날짜는 화면 상태에만 쓰며 시즌 선택은 명시 ID임. 최상위 `dataVersion` 자체도 제외함. BFB 내장 `client`에도 같은 투영을 적용함.
- 일반 `name/text/desc`, `sets.items[].tiers[].text`, `search.excludeText/notes`, 스탯·지원 확률·의존 자료/보관 자산 해시·미확인 키는 유지함. BFB `_set_value`는 text 숫자를 읽고, 화면 `page_payload`는 excludeText로 제외 구원자를 계산함. client 정의는 BFB 일반 단계 실행에 필요함.
- 회귀 시험은 기존 전체 해시에서 표시 변경 불변 검사가 실패함을 먼저 확인했음. 계산 변경(공격력·지원 확률·선택 효과 숫자·제외 조건·내장 client·의존 자료)과 표시 변경을 따로 검사함. 30111 보관 시뮬은 기존 공통 `sim_payload`의 파일 해시 연결로 검증하며 원본 파일과 결과를 덮어쓰지 않음.
