# 시간·횟수·주기 필드 전수 대조 (2026-11-21)

## 결론

- 배경: 작전 42-12에서 프로페서M 잠재력 〈날렵한 자세〉(SeCoolTurn 1)의 재발동 제한을 엔진이 행동 시작 횟수로 세서 과다 발동했음(`mc.se_cool_clock`, `docs/op4212_triggers_1121.md`). 같은 종류의 어긋남이 다른 효과에 없는지, SE·BUFF·SKILL 표의 시간·횟수 필드를 PC 26752678 클라(`starsavior-static-data/decompiled/`, `rebuild_26752678/T`)와 전부 대조했음.
- 표의 SeCoolTurn>0 SE 96건을 하나씩 엔진 줄과 연결했음. 엔진이 다루는 구원자·잠재력·현행 적 SE는 전부 설명문에 {발동 후 N턴 재발동 불가}가 있고 N도 표와 같음(빠진 것 0). 나머지는 엔진이 지원하지 않는 참(장신구)·큐브 팰리스 스킬·길드 레이드 아이템이거나 엔진 콘텐츠 밖(메인 스토리·이벤트·여정) 적임. 전투당 1회(m_bNoReuse)도 같은 방식으로 확인했고 빠진 것 0.
- **클라와 달라서 고친 것 2건**(규칙 스위치, 기본 client·legacy 보존):
  1. `mc.revive_se_reset` — 부활하면 그 유닛의 재발동 제한·전투당 1회 기록을 비움(클라 부활 경로가 등장 초기화를 다시 불러 기록 사전을 Clear). 엔진은 부활 뒤에도 기록을 유지했음.
  2. `mc.skill_cool_change` — 스킬 쿨 감소·증가 효과. 클라는 효과 대상(적 전체 등)마다 적용하고, 칸 지정 없는 «스킬 쿨타임»은 모든 칸을 줄이며, 증가는 그 칸 최대 쿨을 넘지 않음. 엔진은 감소를 줄 주인 한 칸에만 적용(대상 무시)하고 증가에 상한이 없었음.
- 영향: 괴리의 표상(코스모) 〈심상 균열〉 «적 전체에게 스킬 쿨타임 1턴 감소»가 엔진에서는 보스 자신의 쿨을 줄이고 있었음 → 코스모 시즌 괴리의 표상 3단계 Lv0 표준 육성(프레이·왈츠 아세라·프로페서M·그웬) 500판 클리어 6→54. 코스모 힐데(지크프리트) 3단계는 진행도 47.1%→43.8%. 작전 42-12(내 정보, 1000판)는 해당 효과가 없어 변화 없음(원값 비공개 `role-private/op4212/timing/`).
- 행동 불가 턴: 클라는 행동 불가(또는 사망) 턴 유닛도 행동 끝 처리(TURN_END·재발동 제한 차감)를 거침(NKM:13935-13936 → 13957-13966, 사망이면 제외). 엔진도 같은 자리에서 셈. 일치.

## 필드별 판정

클라 시점 = «저장 → 감소 → 판정». 엔진 시점 = 엔진이 쓰는 시계. 근거 줄은 `decompiled/NKM/NKM.decompiled.cs`(NKM), `Star.Templets.decompiled.cs`(ST).

|필드(표)|클라 시점|엔진 시점|판정|해당 수(구원자/잠재력/적, 엔진 범위)|
|---|---|---|---|---|
|SeCoolTurn(SE)|저장: SE 판정에서 쿨 확인(OBF_8201) → 발동 확률(m_fActiveRate) → HP·조건 통과 뒤 OBF_31057이 SE ID별로 N 저장(NKM:16491-16538, 3532-3546). 대상별 확률(m_fBuffActiveRate)은 그 뒤라 실패해도 저장됨. 감소: 주인(턴 유닛, 생존)의 TURN_END 처리 끝 OBF_15627(2013-2021·3604-3617), 행동 불가 턴 포함(13935-13936). 판정: 0이면 다시 걸림(3549-3560). 부활 시 초기화(아래)|설명문 {발동 후 N턴 재발동 불가}, 주인의 자기 턴 종료 횟수 `turn_ends`(mc.py 턴 종료 블록 끝). 확률 줄은 실제 발동 때 기록(`_fired`)|일치(`se_cool_clock`, 앞 조사에서 고침)·부활 초기화만 **고침**|96행: 구원자 SKILL_1 15(카넬리아 1·샤를 1·페트라 4·베스타 개화 3·나루 개화 2·클레어 개화 2·스칼렛 개화 2, 전부 문구·N 일치), 잠재력 POTEN 6(13002·25001·30005·32003·40301·40401, 전부 일치), 적 SKILL_2 18(현행 배치 12 일치, 6 콘텐츠 밖), 참·큐브·길드 아이템 BATTLE_EFFECT 39·ITEM_1 18(엔진 미지원)|
|m_bNoReuse(SE)|SeCoolTurn과 같은 저장(OBF_29319), 감소 없음, 판정 영구 거짓(3549-3556). 부활 시 초기화|설명문 {전투당 1회}, 조건 통과 때 `once`에 기록|일치·부활 초기화만 **고침**|구원자 SKILL_1 4(로자리아 3·카넬리아 1), 잠재력 1(33003 〈증표〉), 적 SKILL_2 53(현행 배치 연결 32행 전부 문구 있음, 22행 콘텐츠 밖), 참·대미지 브레이크 BATTLE_EFFECT·ITEM_1(참은 미지원, 대미지 브레이크는 엔진 `_limit_damage` 별도 경로)|
|부활 시 SE 기록|Resurrection(NKM:5436-5461) → OBF_20318(1207-1221) → OBF_0597(1927-1930) → OBF_35004(3493-3499) `OBF_16992.Clear()`|기록 유지|**고침**(`revive_se_reset`)|엔진 부활 = 엘리사 궁극기뿐. 부활 대상이 위 두 줄을 가진 구원자(로자리아·샤를·페트라·카넬리아·개화 4명·잠재력 6종 보유자)일 때|
|m_CoolTurn·SkillLevelCoolTurnReduce(SKILL)|저장: DoSkill 시작에 본행동·반응 스킬만(NormalAttack·ReactAttack, NKM:15622-15628 → OBF_25503 2405-2408 → 최대 쿨 OBF_14012 2467-2470). 추가 발동·협공·반격은 저장 안 함. 감소: TURN_END OBF_15627(3604-3611), 방금 쓴 스킬 포함·행동 불가 턴 포함|본행동 cast(`not extra`)·반응 `trigger_cast`에서 저장, 턴 종료 효과·지속 차감 뒤 차감(`ally_cd_tick=turn_end`, `enemy_cd_native`, `enemy_cd_end_order=after_effects`)|일치(앞 조사 규칙, 이번에 저장 경로 재확인)|구원자·적 전체|
|SkillCoolturnDownValue·SkillCoolturnType(SE+BUFF)|SE 대상 유닛마다 BattleBuff(NKM:5008-5011) → OBF_19444(2063-2078): 칸 지정이면 그 칸, NSI_INVALID면 1~4칸 전부 → OBF_34909(3120-3133) max(현재−N,0), N=0이면 0|legacy: 줄 주인 한 칸만(시전 칸→줄 칸→궁극기→가장 긴 칸), 대상 무시. «초기화»(N=0)는 이름 경로 `CD_RESET_NAMES`|**고침**(`skill_cool_change`)|칸 지정 없는 «스킬 쿨타임» 감소: 코스모 힐데(지크프리트) 〈인내〉 2줄(자신), 괴리의 표상 〈심상 균열〉 1줄(적 전체). 칸 지정 감소(구원자 로베르타·루나·린·스칼렛·아모라·에밀리·트리쉬·힐데 등, 적 다수)는 전후 같음|
|SkillCoolturnUpValue(SE+BUFF)|OBF_18296(2043-2058) → OBF_32846(3100-3117) min(현재+N, 최대 쿨), N=0이면 최대|legacy: 현재+N 상한 없음|**고침**(`skill_cool_change`)|루그 궁극기(스킬 대상 궁극기 +1), 괴리의 표상 특수기(스킬 대상 스킬 쿨 +1). 바스커빌의 괴수 자기 쿨 증가는 별도 클라 모델|
|m_BuffLifeTurn(SE)·TurnInfinite(BUFF)|주인 TURN_END에서 TURN_END SE 뒤 OBF_1812.OBF_2567(2013-2020)|own_te 뒤 지속 차감, 부여 턴 면제(`buff_fresh_scope`), 보호막(`shield_tick`), 지속 피해(`dot_hot_lifetime`)|일치(앞 조사 규칙)|전체|
|GlobalTurnCounting(BUFF)|턴 유닛 외 전원은 행동 끝 OBF_11783(13966-13968), 턴 유닛은 자기 차감에 포함|`any_turn_clock`·`any_turn_source=table`|일치(앞 조사)|BUFF 22행|
|NSEAT_TURN_START·TURN_END 트리거|턴 시작 SE는 행동 불가여도 생존이면 실행(13930-13932), 턴 종료는 생존 턴 유닛만(13963-13965)|own_ts는 생존이면 행동 불가 판정 전, own_te는 생존일 때|일치|전체|
|RepeatBuffCount·m_fActiveRate·m_fBuffActiveRate|SE마다·대상마다 굴림(NKM:16374-16432)|«N회 부여»·«(대상마다 N% 판정)»|일치(`op4212_triggers_1121.md` 공통 동작)|—|
|대상별 확률 + SeCoolTurn 겹침|확률 실패해도 저장(위)|—|해당 없음|겹치는 SE 3행 모두 참(BuffActiveRate 10000), 엔진 미지원|
|BuffTurnChangeValue(BI_BUFF/DEBUFF_TURN_INCREASE/DECREASE)|—|`effect_dur_extend`|근거 재확인 안 함(앞 조사 규칙 유지)|SE 16행|
|CheckCriticalCount·CheckCriticalCountMax(SE)|—|`per_crit`|근거 재확인 안 함|잠재력 2행·SKILL_1 1행|
|CountMax·UniqueIdStackMax·BuffLevelMax(BUFF)|CountMax는 효과 개수 비례 능력치의 개수 상한(NKM:5674-5697), 시간·발동 횟수 아님|`level_max_source`·`unique_id_stack`|시간 필드 아님(앞 조사)|—|
|브레이크 스킬 쿨·영역, 시작 쿨, 턴 제한, 서든데스|—|`break_skill_*`·`ally_init_cd`·`enemy_spawn`·`turn_limit_unit`·`sudden_death`|앞 조사 규칙 유지(이번 범위 밖)|—|

## SeCoolTurn 96행 목록

엔진 범위 = 엔진이 전투를 만드는 콘텐츠(작전·어려움·일일·장비 탐사·큐브·플래시 포인트·회랑·코스모·길드 방어전·격전 의뢰)의 구원자·잠재력·적.

|표|SE|N|연결|엔진 문구|판정|
|---|---|---|---|---|---|
|SKILL_1|COND_MAID_LANTERN_SPECIAL_01_04|1|카넬리아 특수기|특수기 추가 발동 {발동 후 1턴 재발동 불가}|일치|
|SKILL_1|COND_BUNNY_KNIGHT_UNIQUE_PASSIVE_01_03|1|샤를 고유 패시브|기본기 추가 발동 {…1턴…}|일치|
|SKILL_1|COND_CONSTRUCT_BOMB_UNIQUE_PASSIVE_02_01·02_02·03_01·04_01|1|페트라 고유 패시브(점화·게이지 10/15/20%p)|{…1턴…}|일치|
|SKILL_1|COND_WEST_LANCER_SSR_UNIQUE_PASSIVE_01_01·03_01·04_01|1|베스타 개화(20/30/40% 특수기 추가 발동)|{…1턴…}|일치|
|SKILL_1|COND_NOA_OBSERVER_SSR_UNIQUE_PASSIVE_01_02·01_03|1|나루 개화(기본기 추가 발동·도약 해제)|{…1턴…}|일치|
|SKILL_1|COND_MAID_SPEAR_SSR_UNIQUE_PASSIVE_01_02·01_03|1|클레어 개화(게이지·냉각 해제)|{…1턴…}|일치|
|SKILL_1|COND_MAID_SCISSORS_SSR_UNIQUE_PASSIVE_01_02·01_03|1|스칼렛 개화(특수기 추가 발동·점화 해제)|{…1턴…}|일치|
|POTEN|POTEN_PASSIVE_1300201|1|잠재력 13002(치명 시 연쇄)|{…1턴…}|일치|
|POTEN|POTEN_PASSIVE_2500101|2|잠재력 25001(HP 25% 이하 회복)|{…2턴…}|일치|
|POTEN|POTEN_PASSIVE_3000501|2|잠재력 30005(턴 시작 노바 +2)|{…2턴…}|일치|
|POTEN|POTEN_PASSIVE_3200301|1|잠재력 32003 〈날렵한 자세〉|{…1턴…}|일치|
|POTEN|POTEN_PASSIVE_4030101|1|잠재력 40301(25% 게이지)|{…1턴…}|일치|
|POTEN|POTEN_PASSIVE_4040101|1|잠재력 40401 EX5(다른 아군 기본기)|{…1턴…}|일치|
|SKILL_2|COND_MON_COMMON_PASSIVE7_01|1|살육의 포식자·왜곡의 배회자|50% 기본기 추가 발동 {…1턴…}|일치|
|SKILL_2|COND_MON_CRUNNADUN_AXE_BLACK_BOSS_RUSH_PASSIVE3_01|1|약탈자 족장 크룬나둔|{…1턴…}|일치|
|SKILL_2|COND_MON_MAID_LANTERN_DARK_BOSS_COSMO_01_SPECIAL_01|1|코스모 카넬리아|{…1턴…}|일치|
|SKILL_2|COND_MON_MOGULUS_CROWN_BLACK_BOSS_COSMO_01/02/03_PASSIVE2_02|1|불사왕 모굴루스 〈그릇된 의지〉|{…1턴…}|일치|
|SKILL_2|COND_MON_RECON_AMULET_BOSS_CUBE_02_PASSIVE2_01|1|복제체 루그|{…1턴…}|일치|
|SKILL_2|COND_MON_SPOTTER_ELITERING_PASSIVE_01·02|1|잔상의 감시자|{…1턴…}|일치|
|SKILL_2|COND_MON_SPOTTER_RING_PASSIVE_01|3|감시자|{…3턴…}|일치|
|SKILL_2|COND_NKM_UNIT_MON_PUNISHER_ARMOR_RED_BOSS_PASSIVE2_02|1|공허몰살자 〈강화 반격〉|{…1턴…}|일치|
|SKILL_2|COND_NKM_UNIT_MON_TUNER_CROWN_PURPLE_BOSS_PASSIVE2_01|1|공허변주자|{…1턴…}|일치|
|SKILL_2|COND_MON_ARCHIVE_INFORMER_RED_PASSIVE_01|1|이벤트 큐브(NORMAL_BATTLE_EVENT_CUBE_*)|—|콘텐츠 밖|
|SKILL_2|COND_MON_CONSTRUCT_WRENCH_BOSS_MAINSTORY_04_PASSIVE1_01|1|메인 스토리 EP4|—|콘텐츠 밖|
|SKILL_2|COND_MON_LANIAKEA_RULER_BLACK_BOSS_MAINSTORY_00_PASSIVE1_01|2|메인 스토리 EP0|—|콘텐츠 밖|
|SKILL_2|COND_MON_TUNER_CROWN_PURPLE_BOSS_EVENT_PASSIVE3_01·02|1|오비탈 챌린지 이벤트|—|콘텐츠 밖|
|SKILL_2|COND_MON_VETERAN_BARON_BOSS_PASSIVE1_01|2|여정 레이드(JOURNEY_01_H_BATTLE_RAID_05·06)|—|콘텐츠 밖|
|BATTLE_EFFECT|COND_BATTLE_EFFECT_CHARM_* 33행|1~5|참(장신구) 전투 효과|—|엔진 미지원|
|BATTLE_EFFECT|COND_BATTLE_EFFECT_CUBE_PALACE_STAGE2_04_01·STAGE3_02_01|1·3|큐브 팰리스 선택 스킬(CLIENT_CUBE_PALACE_SKILL)|—|엔진 미지원|
|BATTLE_EFFECT|COND_BATTLE_EFFECT_GUILD_RAID_*_BUFF_ITEM_(PROMOTION_)01_02 4행|1|길드 레이드 아이템(CLIENT_GUILD_DUNGEON_SEASON_TEMPLET)|—|엔진 미지원|
|ITEM_1|CHARM_* 18행|1~5|참 아이템|—|엔진 미지원|

- 적 연결은 `tools/build_foe_auto.py`의 스테이지 배치 연결(SkillLevelSE 순서 ↔ 데이터북 효과 줄, 대상 머리말 대조)을 그대로 써서 SE 행과 줄을 짝지었음. 콘텐츠 밖 판정은 그 유닛이 나오는 배치 파일 이름으로 확인.
- 구원자 줄은 데이터북 전 레벨 줄(L.ln)에서 «재발동» 문구를 모은 11종과 SE 15행을 대조(레벨별 행이 같은 문구), 잠재력은 `data/myinfo_view.json` 문구 6종.
- 엔진의 확률 줄 기록 시점: 클라는 확률이 통과하고 조건이 통과하면 저장, 엔진은 확률 줄에서 실제 발동 때(`_fired`) 기록. 위 목록의 확률 줄(베스타 개화·잠재력 40301·40401·공용 패시브7)은 모두 자기 대상이라 결과가 같음. 예외: 자기 게이지 증가가 〈억류〉 등 게이지 증가 면역에 막히면 클라는 저장하고 엔진은 저장하지 않음(엔진 범위에서 아군이 게이지 증가 면역을 받는 경우 없음, 고치지 않음).

## 고친 것

### 1. 부활 시 재발동 제한·전투당 1회 초기화 (`mc.revive_se_reset`)

- 클라: 버프 Resurrection(NKM:5436-5461)이 덱에 다시 넣는 OBF_20318(1207-1221)은 등장 초기화 OBF_0597(1927-1930)을 부르고, 그 첫머리 OBF_35004(3493-3499)가 SE 기록 사전 OBF_16992를 Clear함. 이 사전이 SeCoolTurn과 m_bNoReuse를 함께 담음(3532-3546).
- 엔진 전: `Battle.recast`·`Battle.once`가 (유닛, 줄) 키로 남아 부활 뒤에도 막았음. 후: 부활 처리 첫머리(등장 후 SE보다 앞)에서 그 유닛 키를 지움.
- 해당: 엔진에서 부활은 엘리사 궁극기 «스킬 대상에게 부활(생명력 50%)»뿐. 부활 대상이 로자리아(HP 40% 이하 공격력 증가 {전투당 1회}), 잠재력 33003 〈증표〉 {전투당 1회}, 위 재발동 제한 줄을 가진 구원자일 때.
- 측정(표준 육성, 500판, seed 20261121): 엘리사·로자리아·프레이·그웬 태양 회랑 200 클리어 500→500, 250 클리어 2→1·진행도 65.78→66.36%(판 안에서 초기화 766회). 결과 차이는 판 수 오차 안.

### 2. 스킬 쿨 감소·증가 (`mc.skill_cool_change`)

- 클라: 버프 SkillCoolturnUp/Down(BattleBuff NKM:5002-5011)은 SE 대상 유닛 각각에 OBF_18296/OBF_19444(2043-2078)를 부름. SkillCoolturnType이 칸이면 그 칸, 없으면(BI_SKILL_COOL_TURN_DOWN·BI_SKILL_COOL_TURN_UP) 1~4칸 전부. 감소 OBF_34909 = max(현재−N, 0)(N=0이면 0), 증가 OBF_32846 = min(현재+N, 최대 쿨)(N=0이면 최대)(3100-3133). 최대 쿨 OBF_14012(2467-2470) = 스킬 사용 때 넣는 값과 같음.
- 엔진 전: 감소 `cdr`는 줄 주인(owner) 한 칸만 줄였음 — 대상 문구를 무시해 «적 전체에게 스킬 쿨타임 1턴 감소»가 보스 자신의 궁극기 쿨을 줄였고, 칸 지정 없는 «스킬 쿨타임»도 한 칸만 줄였음. 증가는 상한이 없었음.
- 엔진 후: 대상 문구로 유닛을 고르고(자신이면 주인), 칸 지정이 없으면 그 유닛의 모든 칸, 증가는 `sk.cd` 상한.
- 해당: 코스모 힐데(지크프리트) 〈인내〉 «내가 피격될 때(기본기/특수기) 자신에게 스킬 쿨타임 1턴 감소»(COND_MON_COUNTERSIDE_HILDE_BLACK_BOSS_COSMO_01_PASSIVE1_02·04), 괴리의 표상 〈심상 균열〉 «적 전체에게 스킬 쿨타임 1턴 감소»(COND_MON_DISPARITY_WINGS_WHITE_BOSS_COSMO_01_PASSIVE2_04, NSETT_ENEMY_ALL), 괴리의 표상 특수기 «스킬 대상에게 스킬 쿨타임 1턴 증가»(SPECIAL_03), 루그 궁극기 «스킬 대상에게 궁극기 쿨타임 1턴 증가»(COND_RECON_AMULET_HYPER_01_01).
- 측정(표준 육성 프레이·왈츠 아세라·프로페서M·그웬, 500판):

|시나리오|클리어 전→후|진행도 전→후|새 경로 실행 수|
|---|---|---|---|
|코스모 시즌 괴리의 표상 3단계 Lv0|6→54|88.69→92.98%|1008|
|코스모 힐데 3단계|0→0|47.1→43.8%|6466|
|코스모 힐데 2단계|500→500|100→100%|521|
|코스모 괴리의 표상 2단계(스테이지 경로)|500→500|100→100%|0(심상 균열 조건 미충족)|
|루그·프레이·프로페서M·그웬 태양 회랑 250|1→1|57.38→57.38%|0(증가 뒤 상한 초과 없음)|

## 작전 42-12 (내 정보 1121, 1000판, seed 7)

- `tools/ingame_check.py --only op4212 --bs-real --myinfo …/myinfo_1121.json --runs 1000`, 전 = `--ov '{"revive_se_reset":"legacy","skill_cool_change":"legacy"}'`. 원값은 `role-private/op4212/timing/`.
- 전후 출력이 한 글자도 다르지 않음(클리어·피해 비율·행동 수 모두 같음). 이 편성(프레이·왈츠 아세라·프로페서M·그웬)과 적(공허선도자·감시자)에 부활·칸 지정 없는 쿨 감소·쿨 증가 효과가 없음.

## 시험

- `tests/timing_audit_1121_test.py` 9건: 실제 `Battle.cast` → 피격 반응(hit_self) → 효과 줄 경로. 부활은 효과 줄 실행(엘리사 문구) 뒤 다시 피격.
- 변이: 부활 초기화 분기를 끄면 1건, 쿨 변경 분기를 끄면 3건 실패를 확인하고 원복.
- 앞 커밋(`se_cool_clock`)으로 깨져 있던 시험 3개(`nova_gauge_test`·`p5_test test_recast_limit`·`self_enforce_target_test test_spotter_recast_and_condition`)를 클라 시계(`turn_ends`)로 고쳤음.

## 측정 재현

- 표준 육성: `python -X utf8 -I tools/measure_timing_1121.py before|after --runs 500` → `local/timing-1121/`.
