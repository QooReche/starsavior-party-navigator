# 11/26 길드 표시 문구·자료 버전

설치 클라와 static-data 디컴파일은 buildid 26935738, DLL 10개 해시가 일치함.
아래 표·디컴파일 경로는 비공개 starsavior-static-data 기준임.

## 생명력 감소 문구

- 공통 기본값의 hpDrain을 «보스가 맞으면 때린 쪽의 최대 생명력 -{v}%씩 쌓임(최대 10회)»로 고쳤음. 사용자 제공 게임 화면 원문은 적 보스 피격 후 타격자의 최대 생명력 감소임.
- 선택 세트 «쇠락»도 현재 표에서는 보스를 때린 쪽이 대상임. `tables/DIFFICULTY_ADD_POINT_TEMPLET.json:218`의 200103은 92051~92053을 참조함. `tables/BATTLE_EFFECT_TEMPLET.json:2405`부터 보스(`BteamEffectTarget=MONSTER_BOSS`)에게 적용함. `tables/SE_TEMPLET_BATTLE_EFFECT.json:6330`부터 각 SE는 `NSEAT_DAMAGE_END`, `NSETT_AUTO_ENEMY_ONE`, AutoTargetId 17임. `tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json:156`의 17은 `IsLastDamageTarget=true`(자신을 마지막으로 공격한 유닛)임. 자동 대상 처리는 `decompiled/NKM/NKM.decompiled.cs:16583`임. 따라서 «보스가 맞으면 때린 쪽의 최대 생명력 -3/4/5%»로 고쳤음. 계산에 쓰이는 숫자는 불변임.
- 생성기가 공통 기본값을 보관 시즌·BFB 최상위/내장 client 정의에 반영함. 시즌 사본을 수동 치환하지 않음.

## 선택 효과 연결 조사

- `tables/DIFFICULTY_ADD_POINT_GROUP.json:80`부터 길드 그룹 2001, 선택 세트 제목 1~4, MAIN_OPEN이 정의됨. `tables/DIFFICULTY_ADD_POINT_TEMPLET.json:176`부터 효과와 추가 점수 5/10/15%가 정의됨.
- 92041~92043은 선택 세트뿐 아니라 별의 도전 10~12단계 고정 효과로도 재사용됨(`tables/DIFFICULTY_LEVEL_GROUP.json:6228,6257,6286`). 사용자 제공 길드 «별의 도전 EX» 화면에는 단계 목록·도전 효과·보스 능력치·추가 점수만 있고 선택 세트 UI가 없음. 표 정의와 화면 노출은 구분함.
- 확정 판정: `decompiled/NKM.Templets/NKM.Templets.decompiled.cs:19323,19332` 길드 전투 시작 요청에 `List<int> OBF_4093`과 직렬화가 존재함. 실제 길드 요청 생성부 `decompiled/NKC/NKC.decompiled.cs:151692`는 그 필드를 대입하지 않아 항상 기본 빈 목록임. 같은 식별자 필드를 선택 목록으로 채우는 곳은 BossRush뿐임(`:75459`에서 난이도 선택 조회 `OBF_10106()` → `:320390,320400`의 목록 대입, 조회 구현 `:332467`). 따라서 클라는 길드에서 선택 효과를 보내지 않음.
- 길드 전투 템플릿은 단계 난이도 인터페이스를 사용함(`decompiled/Star.Templets/Star.Templets.decompiled.cs:6661,6687`). 길드 준비 화면도 `starChallenge.UpdateView`에 단계 그룹을 전달함(`decompiled/NKC/NKC.decompiled.cs:73381`). 요청의 빈 목록과 실제 EX 화면의 선택 UI 부재를 근거로 선택 효과 화면을 숨겼음.
- 공통 기본값 `data/guild_defaults.json`의 `sets.ui=false`를 현재·보관 시즌과 BFB 내장 client에 반영했음. 시즌의 `sets.ui=true`로 다시 켤 수 있음. 숨김 때는 직접 편성·자동 추천·공유의 선택값을 `GuildView.normSel`에서 0으로 정규화하며 드롭다운·효과 라벨·sets.note를 표시하지 않음. 옛 공유 링크와 저장값도 같은 경로를 사용함. 효과 데이터·엔진·최고 조합의 기존 0 기본값은 유지했음.

## 자료 버전

- `tools/guild_version.py:season_version`이 펼친 시즌의 계산 입력을 해시함. 추출·현재 선택 모두 같은 함수를 쓰며, 엔진 `guild.identity`·화면은 저장된 버전을 소비함. 적 스킬 서명·파일 무결성 해시는 용도가 다르므로 그대로 둠.
- 재귀 제외: `effectText`, `note`, `statNote`, `provenance`, `asOf`, `gameBuild`, `source`, `sources`, `src`, `conf`, `_note`, `minionsNote`. 생성기의 문구·출처·신뢰도·추출 메타이며 길드 전투/지원/점수 입력으로 읽지 않음.
- 경로 한정 제외: `season.label/name/start/end/settleEnd/intervals`, `sets.scope/ui`, `sets.items[].name`, `supports[].name`, `score.hypotheses[].name/desc`, `search.excludeWhy`. 날짜는 화면 상태에만 쓰며 시즌 선택은 명시 ID임. `sets.ui`는 편집 UI의 표시 정책이며 실제 계산 입력 sets는 요청·캐시 서명에 별도로 포함되므로 자료 버전에서 제외함. 최상위 `dataVersion` 자체도 제외함. BFB 내장 `client`에도 같은 투영을 적용함.
- 일반 `name/text/desc`, `sets.items[].tiers[].text`, `search.excludeText/notes`, 스탯·지원 확률·의존 자료/보관 자산 해시·미확인 키는 유지함. BFB `_set_value`는 text 숫자를 읽고, 화면 `page_payload`는 excludeText로 제외 구원자를 계산함. client 정의는 BFB 일반 단계 실행에 필요함.
- 회귀 시험은 기존 전체 해시에서 표시 변경 불변 검사가 실패함을 먼저 확인했음. 계산 변경(공격력·지원 확률·선택 효과 숫자·제외 조건·내장 client·의존 자료)과 표시 변경을 따로 검사함. 30111 보관 시뮬은 기존 공통 `sim_payload`의 파일 해시 연결로 검증하며 원본 파일과 결과를 덮어쓰지 않음.

## 검증

- 선택 효과 숨김: 관련 시험 7파일·길드 e2e 8건 통과했음. 직접 편성의 옛 공유값·최고 조합 버튼·단계/지원·공유 왕복·실제 작업자 결과와 자동 추천 요청의 sets=0을 검사했음. 1280/390px에서 UI 숨김과 플래그 재활성화를 확인했고, 정규화/드롭다운 숨김 제거 변이는 실패했음. 변경 전 30112 1~7단계·시드 3·각 3판을 저장해 실행 시간 계측값 외 결과·타임라인이 같고 진행도 > 0임을 확인했음. 전 시즌 자료 버전은 불변임. 전체 시험은 메인에서 실행하기로 함.
- 30112 1~7단계: 공개 표준 편성, 시드 3, 각 3판·타임라인을 수정 전에 저장하고 수정 뒤 비교했음. 전 단계 진행도 > 0, 결과 동일함.
- BFB 30111: 수정 전 `29bbc92` 정의와 현재 정의로 6지원×13도전 단계, 조건당 시드 3·3판·타임라인 78조건을 비교했음. 전부 진행도 > 0, 결과 동일함. 기존 108조건 훅/타임라인 골든도 변경 없이 통과했음.
- 현재 `guild_sim`은 기존 생성 조건(2편성·20판·시드 7·off/max·5육성 배수·6지원)을 유지했으며 `dataVersion` 외 모든 값이 동일함. 30111의 `guild_sim`·`guild_bfb` 보관 파일은 바이트 불변임.
- 관련 시험 7파일·e2e 2건 통과. 전체 시험은 마지막에 1회 실행해 285통과/0실패, 환경 건너뜀 6건임. simpack·페이지도 재생성했음.
- `unsupported_allowlist.py --diff`는 변화 없음·종료 0임. 4,203스테이지·350시나리오·1,050판·보관 시즌 11개에서 A/B/C/E 0, 기존 D 12건을 유지했음.
