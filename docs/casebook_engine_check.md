# 공략 사례 18건의 전투 동작 점검

2026-11-21, PC Steam build **26752678**. 공략의 승패를 정답으로 삼지 않고, 글에서 식별할 수 있는 동작을 검사했음. 계정 파일·계정 능력치·계정 시뮬 결과는 사용하거나 기록하지 않았음.

**집계: 18사례·68동작 행 — 계산함 47, 근사 1, 미계산 0, 엔진 밖 20.** 발견한 속도 계산 누락 2종을 수정한 뒤의 판정임. 별도의 공통 잔여 범위 R1·R2를 전체 계산 성공으로 합치지 않았음.

## 근거와 판정 범위

- 비공개 `cases.md`·`cases.json`의 사례 번호를 유지했음. 원문과 그림은 공개 저장소에 복사하지 않았음. 그림·영상에만 있는 편성, 조작 순서, 장비는 확인 불가로 두었음.
- 최초 `STARSAVIOR_STATIC/check_build.py`는 설치 26752678과 저장소 디컴파일 26610546의 불일치를 보고했음. 작업 폴더 밖 수정 금지에 따라 설치 DLL 10개를 **이 worktree의 무시된 `static-data/decompiled/`**에 다시 디컴파일했음. 그 사본의 `check_build.py`는 buildid 일치·DLL 10개 해시 불일치 0으로 통과했음. 외부 static-data 저장소의 옛 디컴파일은 그대로임.
- 아래 `NKM`은 `static-data/decompiled/NKM/NKM.decompiled.cs`, `NT`는 같은 곳의 `NKM.Templets/NKM.Templets.decompiled.cs`, `ST`는 `Star.Templets/Star.Templets.decompiled.cs`임. 모든 코드 근거를 이 사본에서 직접 확인했음. 3월판 디컴파일 코드는 쓰지 않았음. 난독화 식별자는 이번 10개 어셈블리 일괄 변환 기준임.
- `T/`는 `static-data/tables/`임. 관련 스킬 SE 1·2 표는 현재 추출 표와 같았음. BUFF 표의 변경 1행은 이번 사례와 관계없는 `BI_NIGHT_DESPAIR_BOSS_MAINSTORY_1`이었음. 현재 추출 표의 사본은 무시된 `static-data/current-tables/`에 두었음.
- **계산함**은 아래에 적은 입력·동작·시험 범위만 뜻함. 해당 편성이 공략의 승률·점수를 재현한다는 뜻이 아님. **근사**는 식이나 적용 범위가 아직 확정되지 않은 것, **미계산**은 엔진에 없는 것, **엔진 밖**은 사람의 조작·육성·식별 불가 입력임. 수동 사이클을 오토가 선택하지 않는 것은 결함으로 세지 않았음.
- 같은 동작이 다른 사례에 다시 나오면 사례별 행으로 다시 셌음. 근거 열의 M 번호는 뒤의 구현·클라·시험 묶음에 연결됨. `CB`는 새 `tests/casebook_mechanics_test.py`임.

## 사례 × 동작

|사례·동작|검사한 내용|수정 후 판정|근거·시험 또는 한계|
|---|---|---|---|
|01a 모굴루스|구원자 길레 궁극기의 속도 감소와 피날레 전 효과 적중 판정|계산함|M4, CB `gille_resistance_before_finale`|
|01b|세레스가 보스 행동 게이지를 줄여 브레이크 회복 차례를 늦춤|계산함|M3, CB `ceres_gauge_delays_broken_target`|
|01c|보호막이 없는 대상에게 몰락한 사념·속도 0|계산함|M1. **고정 속도 누락 수정**|
|01d|차원 강습의 피해·영역·게이지 효과|계산함|M9. 수호 등 잔여 범위는 아래 R2|
|01e|속도 감소 두 번 성공·리더·브레이크 발동 시점으로 글의 결과 재현|엔진 밖|수동 조작·육성·확률 결과. 특정 성공을 강제하지 않음|
|02a 모굴루스|세레스의 게이지 감소로 이미 깨진 강인도를 유지|계산함|M3. 별도 ‘브레이크 지속 턴 +N’ 효과가 아님|
|02b|브레이크 사건에 편애의 마녀 추가 턴·연쇄 피해|계산함|M5, CB `asherah_break_extra_turn_and_chain`|
|02c|별의 도전: 모굴루스가 공격한 뒤 대상 강화 1개 삭제|계산함|M2, CB `mogulus_challenge_strips_after_attack`|
|02d|정해진 턴 안에 연장을 두 번 넣어 추가 피해를 한 번씩 더 냄|엔진 밖|수동 조작·불완전 편성. 횟수를 엔진에 보정하지 않음|
|03a 모굴루스|평타·궁극기 시작 때 보호막을 검사하고 속도 0을 3전역턴 적용|계산함|M1. 맞아서 보호막이 깨진 뒤에 소급 판정하지 않음|
|03b|아군 중 사념 보유자가 있을 때 보스 피격 뒤 게이지 +20%p|계산함|M1. ‘아무 이유로든 속도 0인 아군이 있으면 항상 증가’는 아님|
|03c|첫 턴 노바에 필요한 포스와 에데 기본기 노바 보호막|계산함|M8, CB `first_turn_nova_requires_force`. 포스 0/4 경계|
|03d|에데의 노바 슬롯 보호막|계산함|M8, `nova_gauge_test.test_manual_slot_shield_matches_heal_policy`|
|03e|행성 정화의 피해·강인도·영역 중 노바 슬롯 효과|계산함|M9, `break_skill_test`의 planet 시험|
|03f|다른 탱커로 대체·장비 해제 상태의 생존·아르카나 보유 전제|엔진 밖|육성·편성 입력. 특정 계정의 첫 턴 포스를 임의 지급하지 않음|
|04a 회랑|파쇄의 고정 강인도 피해 +1|계산함|M5, `asherah_toughness_test`|
|04b|서곡→광시곡→피날레의 단계 상승과 강인도 보정|계산함|M4, `gille_conditions_test.GillePromotionTest`|
|04c|구원자 길레 궁극기가 파쇄 아군에게 게이지 지급|계산함|M4, CB `gille_crush_gauge_and_speed_reduction`|
|04d|편애의 마녀 특수기의 보스 7·일반 적 4 강인도 피해|계산함|M5. 파쇄·표준 스킬 단계·속성 조건의 시험값임|
|04e|웨딩 카르멘 반응형 특수기는 본인이 브레이크면 불발|계산함|M6, CB `carmen_reaction_blocked_while_broken`|
|04f|남은 강인도를 보고 기본기/특수기 선택, 노바를 카르멘에 예약|엔진 밖|수동 조작. 노바 +1 계산은 M8에 있으나 임계값을 선택 정책에 넣지 않았음|
|05a 회랑 590|파쇄 평타의 브레이크가 추가 턴·연쇄로 이어짐|계산함|M5, CB `asherah_break_extra_turn_and_chain`|
|05b|메이드 세레스의 먼지 5중첩에서 특수기 추가 발동·회복·정화|계산함|M7, CB `maid_ceres_dust_extra_heals_and_cleanses`의 4/5 경계|
|05c|아모라 통찰 5중첩의 자기 턴 시작 정화|계산함|M10, CB `amora_five_insight_cleanses_at_turn_start`의 4/5 경계|
|05d|노바·브레이크·평타를 수동으로 맞추는 순서|엔진 밖|수동 조작|
|06a 작전 42-18|은신 대상의 단일 타겟 제한·전원 은신일 때 폴백|계산함|M15. 특정 보스 전투 전체의 클리어 검증은 아님|
|06b|미기재 힐러 두 명을 포함한 풀오토 클리어|엔진 밖|그림 미확인·편성 미기재. 미계산으로 세지 않음|
|07a 보스 미상|왈츠 아세라로 해석할 경우 궁극기의 자신 제외 아군 게이지 증가|계산함|M11, CB `waltz_ultimate_gauge_and_basic_healing`. 이름 해석은 조건부|
|07b|왈츠 아세라 협공 기본기의 회복|계산함|M11. 실제 협공 시전 경로를 시험함|
|07c|그 보스가 연쇄에는 반응하지 않아 특정 서순이 성립한다는 주장|엔진 밖|보스 이름·스킬 식별 불가. 일반 연쇄와 일반 타격을 구분하는 것만으로 그 보스까지 확정하지 않음|
|07d|3221 조작과 힐·브레이크 타이밍|엔진 밖|수동 조작|
|08a 편애의 마녀·게이지 감소 조합|게이지 감소로 보스 다음 행동/브레이크 회복을 늦춤|계산함|M3. 두 미기재 구원자의 스킬을 검증한 뜻은 아님|
|08b|한 사이클 연쇄 네 번·두 게이지 감소 담당의 정확한 배치|엔진 밖|수동 조작·구원자 미기재|
|09a 작전 44장|웨딩 카르멘의 자기 제외 최고 공격력 아군 서약 지정|계산함|M6, `taunt_guard_test`·`sel_targeting_test`|
|09b|서약 대상의 단일 공격 피해 40% 수호 분담|계산함|M6. 광역·다른 대상은 분담하지 않는 경계도 검사|
|09c|반응형 회복·보호막·게이지 지급|계산함|M6. 회복/보호막 계수는 카르멘 최대 HP 기준|
|09d|메이드 세레스의 추가 회복·정화|계산함|M7, CB 먼지 4/5 경계|
|09e|앞자리 선택·44-33/36의 수동 생존 사이클|엔진 밖|수동 조작·육성. 앞자리 가중 정책을 변경하지 않음|
|10a 길드 레이드 12|아군 시전마다 경쟁 카운터 증가, 5 이상에서 대결 예약|계산함|M12. 협공·반응·추가 발동도 시전으로 셈|
|10b|신부 경쟁 버프 최대 10중첩·중첩당 공격력 증가|계산함|M12, CB `bridal_stack_cap_and_attack` 1~12회. **현재 표는 3%, 글의 5%와 다름**|
|10c|최고 공격력 대상에게 경쟁 버프 지정|계산함|M12, `guild_bfb_test.test_compete_and_appeal`|
|10d|들러리 협공·공격에 대한 처벌|계산함|M12, `test_punish_maids`, `test_bouquet_chain_not_ally_damage`|
|10e|보호막 파괴·반응 예약·대결 종료|계산함|M12, `test_shield_break_bouquet`, `test_appeal_deferred_to_reaction_queue`|
|10f|들러리 속도/방어 0·추가 턴 예외·도전 면역|계산함|M12, `test_maid_speed_def_zero`, `test_maid_extra_turn_not_blocked`, `test_challenge_effects`|
|10g|첫 사이클 추가 턴을 아끼고 다음 대결 전에 사용|엔진 밖|수동 조작. 모든 추가 턴을 같은 시기에 쓰게 하는 정책은 넣지 않았음|
|11a 길드 레이드 12|대결 전 궁극기·추가 턴을 저장|엔진 밖|수동 조작|
|11b|그림 속 두 구원자를 포함한 전체 택틱|엔진 밖|그림 미확인|
|12a 길드 레이드 9 실패|누가 어떤 공격에 맞아 실패했는지|엔진 밖|글만으로 원인 식별 불가. 결함이나 계산함으로 단정하지 않음|
|13a 카넬리아|약화 상태 공격자의 보스 타격: 기본 +15%p와 도전 역류 +10%p|계산함|M13, CB `carnelia_debuff_gauge_and_challenge_are_separate`|
|13b|저항 성공으로 약화가 없으면 위 게이지 조건 불성립|계산함|M13·M4. 약화 있음/없음과 도전 켬/끔 네 경우|
|13c|아모라 통찰을 쌓고 자기 턴 시작에 약화 해제|계산함|M10, CB 통찰 4/5 경계|
|13d|리디아 속도 감소와 미지의 주문 합산|계산함|M14. **특수기는 10%, 궁극기는 20%+10%**. 글의 ‘특수기 30%’로 고치지 않았음|
|13e|협공 발생·시전 분류(EX 육성 수치 자체는 입력 전제)|계산함|M16, `forced_coop_test`, `coop_cap_test`. 실제 횟수는 확률 결과|
|13f|별 속성·어쌔신 시즌 효과를 해당 아군에 적용|계산함|M17, `cosmo_raid_test.test_season_buffs`|
|13g|속도 순서·저항 장비·리트·브레이크 시점|엔진 밖|육성·수동 조작. 글의 성공 경로를 확률 100%로 만들지 않음|
|14a 티리아|빈 슬롯에 인형 둘 소환·이미 차 있으면 중복 소환 안 함|계산함|M18, `summon_test.TyriaTest`. 시즌 효과 중도 소환 적용은 R1|
|14b|게이지 최고 대상의 타임 패러독스 속도 -300%|계산함|M19. **속도 하한 1→0 수정**, CB 실제 보스 특수기 시전|
|14c|일반 회피 및 회피 시 강인도/약화의 별도 처리|계산함|M20, `p3_test.test_evade`, `toughness_video_test`, `evade_ignore_resist_test`|
|14d|일반 면역 유무에 따른 약화 거부|계산함|M20, `debuff_ban_flag_test.test_plain_immune_and_none_both`. 공략의 방감·만료 시점 전체는 미검증|
|14e|치명타 확률과 보호막 피해 흡수|계산함|M20, `received_damage_test`, `dispel_shield_test`|
|14f|페이 첫 공격만 회피·후열 피격 회피·그웬 전기충격기와의 정확한 연속 순서|엔진 밖|그림 15장 미판독·확률 결과·수동 조작. 개별 회피 계산을 전체 서순 검증으로 확대하지 않음|
|15a 벨그라스 부분 사례|시즌 효과의 속성·직업 대상 적용|계산함|M17. 정확한 네 명의 조합은 미기재|
|15b|해당 난이도의 최종 보스 수치·점수까지 일치|근사|R1. 서버 난이도 배율·최종 점수 일부를 클라만으로 확정할 수 없음|
|15c|프엠·메이드 세레스 외 편성·실제 전투 순서|엔진 밖|그림 미확인·부분 편성|
|16a 세 조합 예상|구체적인 스킬 조건·순서·관찰 결과 없는 조합 추천|엔진 밖|미검증 제안. 동작을 임의로 만들어 넣지 않음|
|17a 바스커빌 예상|프엠·수영복 스마일·그웬 조합의 성패|엔진 밖|미검증 제안·한 자리 미기재|
|18a 바스커빌|강인도 피해 금지·억제된 야성의 속도 0/직접 게이지 구분|계산함|M21, 기존 `baskerville_client_test`의 실제 경로|
|18b|첫 브레이크 전 딜 손해가 더 크다는 평가|엔진 밖|조합·‘편마알카’ 식별 불가·비교 전투 없음|

사례 링크: [01](https://arca.live/b/starsavior/189640146), [02](https://arca.live/b/starsavior/189695441), [03](https://arca.live/b/starsavior/189614638), [04](https://arca.live/b/starsavior/189137698), [04 보충](https://arca.live/b/starsavior/188953589), [05](https://arca.live/b/starsavior/189264564), [06](https://arca.live/b/starsavior/188942000), [07](https://arca.live/b/starsavior/189700929), [08](https://arca.live/b/starsavior/188954677), [08 보충](https://arca.live/b/starsavior/188799406), [09](https://arca.live/b/starsavior/187617622), [10](https://arca.live/b/starsavior/187421752), [10 보충](https://arca.live/b/starsavior/187477682), [11](https://arca.live/b/starsavior/187469459), [12](https://arca.live/b/starsavior/187432986), [13](https://arca.live/b/starsavior/188314780), [14·15](https://arca.live/b/starsavior/188634988), [16](https://arca.live/b/starsavior/189530753), [17](https://arca.live/b/starsavior/187918069), [18](https://arca.live/b/starsavior/189733974).

## 구현·클라·시험 색인

공통 클라 실행 경로를 먼저 적었음. 아래 M의 표 행은 이 실행 경로에 입력되는 데이터임. 표에 값이 있다는 이유만으로 계산함 판정을 하지 않고, 오른쪽의 실제 실행 시험도 대조했음.

|코드|현재 PC 클라 클래스·메서드·줄|확인한 동작|
|---|---|---|
|G1|NKM `OBF_29345.OBF_18595`:16101, `.OBF_18609`:16492, `.OBF_28434`:16540|사건별 SE 열거·조건·수신자 선택. 각 SE 실행 때 현재 상태를 읽음|
|G2|NKM `OBF_3509.OBF_8842`:5109–5136|행동 게이지 증감. 속도와 별개로 직접 변경|
|G3|NKM `OBF_8000.OBF_0912`:4303–4400|강제 적용·회피·면역·효과 적중과 해제 처리|
|G4|NKM `OBF_14689.OBF_8487`:17194–17227, `.OBF_4400`:17289–17317, `.OBF_6640`:17230–17244|속성·고정 강인도 피해, 브레이크 버프 부여, 다음 자기 턴 회복|
|G5|NKM `OBF_12756.OBF_15561`:18896–18902, `.OBF_1825`:19001–19016, `.OBF_15134`:19019–19027|최종 고정값을 적용하고 속도 음수를 0으로 제한. NT:32808–32832의 음수 허용 스탯에 속도 없음|
|G6|NKM `OBF_29345.OBF_0709`:15955–15978, `OBF_34350.OBF_8574`:9101, `OBF_14895.OBF_34590`:2268–2288|반응 예약·실행 시 사용 가능 검사|
|G7|NKM `OBF_35527.OBF_34464`:5521–5551, `OBF_27338.OBF_20265`:8350–8369, `.OBF_13711`:8371–8388|SE 회복과 수호 분담. 분담자는 자기 방어식으로 피해를 받음|
|G8|NKM `OBF_29345.OBF_0728(OBF_23947, OBF_23958)`:14402–14484|노바 포스 확인·소모·노바 상태 적용. 획득과 소모를 별도로 처리|
|G9|NKM `OBF_27338.OBF_25539`:8266–8288, `.OBF_11338`:8290|명중/회피 뒤 치명 판정. G3의 효과 거부는 별도|

|근거|엔진 파일:줄|클라 표 키·줄 / 공통 경로|시험|
|---|---|---|---|
|M1 몰락한 사념|`battlesim/starsavior/parser.py:213`, `battlesim/mc.py:720,745,1351,5737`|T/BUFF_TEMPLET:36324 `BI_MOGULUS_CROWN_1`, FixStats:36386, GlobalTurnCounting:36341. T/SE_TEMPLET_SKILL_2:29674 `930043101`, :29739 `930043302`, :29753 `930043401`; 조건31010, T/Plain/SKILL_CONDITION_TEMPLET:9565–9569 `55117`(MyEffectiveHit·ExistEnemySpecificBuff), AutoTarget1009. G2·G3·G5. NKM `OBF_8000.OBF_30811`:3895–3905, `OBF_14895.OBF_15241`:2376–2377, ST:4803–4806|CB `mogulus_zero_speed_and_direct_gauge`, `mogulus_fixed_speed_ignores_increases_and_global_expiry`, `mogulus_shield_at_skill_start`, `mogulus_gauge_requires_marker_and_hit`|
|M2 도전 삭제|`battlesim/starsavior/cosmo_raid.py:490`, `battlesim/mc.py:5096`|T/SE_TEMPLET_BATTLE_EFFECT:7310 `9402801`, 조건2107, SKILL_END·삭제1; G1·G3|CB `mogulus_challenge_strips_after_attack`; `cosmo_raid_test.py:685`|
|M3 세레스 지연|`battlesim/mc.py:1337,1436,4534`, `battlesim/starsavior/marker_se.py:49,126,154`|T/SE_TEMPLET_SKILL_1:22692–22788 `10333013..19` 냉각별 감소·소거. G2·G4. 다음 행동 때 회복하므로 게이지 감소가 회복을 늦춤|CB `ceres_gauge_delays_broken_target`; `savior_mapping_test.py:125`|
|M4 구원자 길레|`battlesim/mc.py:2602,4454,5737`|T/SE_TEMPLET_SKILL_1:12754–12841 `10202011..16`, :13036–13113 `10203011..15`; T/BUFF_TEMPLET:24643–24978 `BI_APOSTLE_GILLE_1..6`. G1·G2·G3·G4|CB 길레 2개; `gille_conditions_test.py:66,93,108,127`|
|M5 편애의 마녀|`battlesim/mc.py:3119,5298`, `battlesim/starsavior/mc_semantics.py:63`|T/BUFF_TEMPLET:3472 `BI_CRUSH`; T/SE_TEMPLET_SKILL_1:41514–41570 `10612014..16`, :41723 `10613011`, :41917–42055 `10614011..18`. G1·G4. NKM `OBF_8000.OBF_0912`:4421–4431은 추가 턴의 현재 행동자 제한|CB `asherah_break_extra_turn_and_chain`; `asherah_toughness_test.py:46,79`; `chain_stat_true_test`; `target_conditions_test.py:27`|
|M6 웨딩 카르멘|`battlesim/mc.py:2569,2676,2573,3359`|T/SKILL_TEMPLET_1:2588 `10552` 반응 조건56008, T/SE_TEMPLET_SKILL_1:35162–35208 `10552011..13`, 최대 단계 게이지 `10552081..82`:35334–35363, 서약 `10554011..12`:35608, 피격 패시브 `10554041`:35777. G6·G7. **T/SE_TEMPLET_SUPER_ARMOR:26,40 → BUFF_TEMPLET:8925 `BI_ARMOR_BREAK_PARALYSIS`, :8953 DisableReactSkill=true → NKM:2279**. 기본 브레이크 피해 버프만 보면 이 차단을 놓침|CB 카르멘(브레이크여도 별도 패시브 게이지는 유지); `taunt_guard_test.py:119,140`; `sel_targeting_test.py:134`; `nova_gauge_test.py:91`|
|M7 메이드 세레스|`battlesim/mc.py:2602,4030,4534`|T/SE_TEMPLET_SKILL_1:38943–39025 `10592011..15`, :39434–39498 `10594013..16` 추가 발동·먼지 감소. G1·G3·G7|CB `maid_ceres_dust_extra_heals_and_cleanses`; `survey_g2_test.py:46` 지속 회복|
|M8 첫 노바|`battlesim/mc.py:2546,2602`, `battlesim/starsavior/myinfo_combat.py:41,89`|G8; T/NOVA_BURST_TEMPLET·SE_TEMPLET_NOVA_BURST의 에데1018/웨딩 카르멘1055 슬롯. 스킬 기본 포스 획득값은 SKILL_TEMPLET_1의 GetNovaForceValue|CB `first_turn_nova_requires_force`; `nova_gauge_test.py:70,82,91`; `myinfo_combat_test`|
|M9 브레이크 스킬|`battlesim/mc.py:1600,1661`|NKM `OBF_12098.OBF_24645`:18247–18296 팀 합산 피해, G4; T/ORBITAL_ARRAY_TEMPLET·ORBITAL_DOMAIN_TEMPLET·SE_TEMPLET_ORBITAL_ARRAY의 차원 강습/행성 정화|`break_client2_test.py:28,40,51` 현재 팀 합산·연속 발동·영역; `break_skill_test.py:185,550,562,583` 개별 효과. R2를 제외한 핵심 동작|
|M10 아모라|`battlesim/mc.py:1436,4534`|T/SE_TEMPLET_SKILL_1:38630–38706 `10584013..17`, 조건39025. G1·G3|CB `amora_five_insight_cleanses_at_turn_start`|
|M11 왈츠 아세라|`battlesim/mc.py:1337,2573,4030`|T/SE_TEMPLET_SKILL_1:34418–34447 `10543011..12`, 기본기 회복 `10544021` (:34622). G1·G2·G7|CB `waltz_ultimate_gauge_and_basic_healing`|
|M12 길드 레이드|`battlesim/starsavior/guild_bfb.py:340,398,411,482,514`|T/BUFF_TEMPLET:46545 `BI_AUTOMATON_MINIGUN_BOSS_1` 최대10/공격력300, `_2` 들러리, `_8` 보호막. 조건58801·52093·52094·52095·37201; G1·G3·G6. 엔진 수치는 `data/guild_defense.json`에서 읽음|CB `bridal_stack_cap_and_attack`; `guild_bfb_test.py:73,119,166,180,187,201,240,316,336`; `guild_bridal_kill_test`|
|M13 카넬리아|`battlesim/starsavior/cosmo_raid.py:705`, `battlesim/mc.py:1337,4534`|T/SE_TEMPLET_SKILL_2:34664 `930073401` 기본 +1500, T/SE_TEMPLET_BATTLE_EFFECT:7043 `9402001` 역류. G1·G2·G3|CB `carnelia_debuff_gauge_and_challenge_are_separate`; `cosmo_raid_test.py:159`|
|M14 리디아|`battlesim/mc.py:720,4534`, `battlesim/starsavior/marker_se.py:49,126,154`|T/BUFF_TEMPLET:26736 `BI_WEST_ROD_1` 속도-1000; T/SE_TEMPLET_SKILL_1:23654 `10342012`, :23882–23909 `10343012..13`. G1·G3·G5|CB `lydia_special_and_ultimate_slow_are_different`; `marker_se_test.py:108` 게이지 표지|
|M15 은신|`battlesim/mc.py:2076` 대상 선택|NKM `OBF_36005`의 스킬 대상 필터:7132–7180, `OBF_22109.OBF_17327`:5794–5802의 Hide/SpecificHide 검사; T/BUFF_TEMPLET `BI_HIDE`의 Hide 플래그. 공격 스킬의 전체/단일 유형을 구분|`p3_test.py:50`의 은신 대상 제외/전원 은신 폴백 시험. 회랑/작전 전체 승패는 미검증|
|M16 협공|`battlesim/mc.py:2793,2820`|NKM `OBF_29345` 협공 선정:15904–15952, 참가 가능:16028–16088; T/SKILL_TEMPLET_1·COOP 확률 스탯. 강인도 파괴·기절 제외|`forced_coop_test`, `coop_cap_test`, `coop_order_test`|
|M17 시즌 효과|`battlesim/starsavior/cosmo_raid.py:400`|NT `OBF_3092.OBF_5587`:33003–33014의 BCT→속성 매핑과 ST:9367–9372의 RankingRaidBuff 대상/효과 로더, RANKING_RAID_SEASON_TEMPLET 시즌1022·1023의 전투 참조. 클라 부여 경로 NKM `OBF_29345` 전투 효과 실행:680–741. 서버/중도 소환 경계는 R1|`cosmo_raid_test.py:121`; `cosmo_s23_test`|
|M18 소환|`battlesim/mc.py:3564`|NKM `OBF_19499.OBF_34464`:5711–5754 → 팀 슬롯 추가:1224–1239 → 유닛 초기화:1927–1964. `OBF_27479.OBF_35004`:3493–3499는 게이지0 초기화. T/SUMMON_TEMPLET 티리아 인형 슬롯|`summon_test.py:138,152,201`. 현재 근거로 시작 게이지0도 확인했음|
|M19 타임 패러독스|`battlesim/mc.py:745,1351`|T/BUFF_TEMPLET:47269 `BI_APOSTLE_TYRIA_BOSS_COSMO_2`, :47341 `_3` 속도-30000; T/SE_TEMPLET_SKILL_2 티리아 특수기 `930051202` (:31098); G5|CB `speed_floor_and_legacy`, `tyria_real_paradox_stops_passive_gauge`|
|M20 회피·면역·치명·보호막|`battlesim/mc.py:2993,3359,5459,5737`|G3·G9. T/BUFF_TEMPLET `BI_EVADE_INCREASE`, `BI_DEBUFF_BAN`, `BI_BARRIER`. 페이1029 회피 증가 SE는 표 대조에 한정하며 고유 패시브 전체 회귀 검증은 아님. 일반 피해와 약화 거부는 독립|`p3_test.py:250`; `toughness_video_test.py:128`; `debuff_ban_flag_test.py:49`; `immune_group_resist_test.py:30,49`; `received_damage_test.py:36`; `dispel_shield_test`|
|M21 바스커빌|`battlesim/starsavior/cosmo_raid.py:400`, `battlesim/mc.py:720,3119`|T/BUFF_TEMPLET:50962–51020 `BI_DOOMSDAY_BEAST_BOSS_3`의 SuperArmorDamageBan, :51023–51087 `_4`의 FixStats, G4·G5. 기존 조사 `docs/baskerville_26752678.md`의 표 키를 이번 사본에서 재확인했음|`baskerville_client_test`, `cosmo_gauge_immune_test`|

## 고친 것과 공략 설명의 차이

1. **고정 속도 0 누락.** 설명문 파서가 `속도 0 고정`을 효과 속성으로 전달하지 않아 모굴루스의 몰락한 사념이 걸려도 계속 속도가 있었음. 파서→효과→최종 속도에 연결하고 `fixstats_speed_zero` 기본을 `client`로 바꿨음. 옛 `off`는 legacy로 남겼음. 바스커빌은 기존부터 별도 연결되어 있었음.
2. **일반 속도 하한 1.** 타임 패러독스처럼 속도 감소가 100%를 넘을 때도 엔진은 속도 1로 움직였음. 클라 G5에 따라 `speed_min=0`, legacy=1을 넣었음. 속도 0이어도 직접 게이지가 10000에 도달하면 행동함. 기존 골든 해시는 `_KEEP`에 옛 값을 지정해 보존했음.
3. 모굴루스 패시브는 ‘속도 0 존재’를 주기적으로 검사하는 것이 아니라 **보스 피격과 적 진영 중 누군가의 사념 보유**를 검사함. 사념 보유자가 공격자일 필요도 없으며, 다른 아군이 보유한 경계도 시험했음. 에데 보호막은 시작 검사 때 존재하면 해당 공격에 깨져도 사념을 막음. 새 시험은 이 차이를 확인함.
4. 신부 경쟁은 현재 표에서 중첩당 공격력 3%임. 리디아 특수기는 속도 10%, 궁극기의 두 약화가 합쳐 30%임. 글의 수치에 맞추려고 엔진을 바꾸지 않았음.
5. 독립 리뷰에서 카르멘의 반응 검사에 직접 `broken` 분기가 없다는 의문이 나왔음. 별도 마비 버프의 `DisableReactSkill`까지 확인해 기존 차단이 맞다고 결론냈음(M6). 속도 하한 변이 시험은 기본값만 바꾸던 방식에서 실제 `Unit.spd()`를 최소1로 되돌리는 방식으로 강화했음.

## 남는 근사와 찾아본 위치

**R1 — 코스모 절대 수치와 중도 소환 효과.** `cosmo_raid._scale_stats`는 현재 능력치에 `(1 + ScaleFactor/10000)`을 곱함. 난이도·전투력 보정의 최종 서버 값, 생존 점수·합산 반올림은 클라 코드만으로 완전히 확정하지 못했음. 찾아본 곳은 NKM 최종 스탯 계산 `OBF_12756.OBF_15561`:18783–18912, NT의 RANKING_RAID·DIFFICULTY_LEVEL 템플릿, NT의 BattleConditionType, NKC `NKCUiBattleHudCosmo.UpdateRaidScore`:69006–69017, NKM `OBF_15985.OBF_15136`:17371–17375, ST:9374–9376 점수 로더임. HUD 식은 있지만 생존 점수 로더/최종 합산식은 여기에 없음. NT:40209 ScaleFactor 로더도 읽었음. 인형의 빈 슬롯/초기화는 M18로 확인했지만 시즌 버프를 중도 소환에 어디까지 붙이는지는 이 감사에서 확정하지 않았음.

기존 허용 목록 D의 키 `['rule','mc.cosmo_raid_boss']`, `['cosmo_approx','난이도 배율: 서버가 적용해 전송하고 클라는 표시만 함. 엔진 현행 능력치 x (1 + ScaleFactor/10000) 유지']`, 시즌 버프·전투력 보정·점수의 `cosmo_approx` 키를 유지함. 여기서 근사는 서버와 정확히 다르다는 확정이 아니라 현재 모델의 미확정 범위임.

**R2 — 브레이크 잔여 범위.** 핵심 팀 합산 피해·영역·게이지/노바는 시험하지만 큐브 회복의 사망자 합산, 수호 분담, 개인 노바 풀 대체 모델 전체는 확정하지 않았음. 기존 D `['rule','mc.break_skill_residuals']`, `['rule','mc.add_damage_guard']`에 대응함. NKM `OBF_12098.OBF_24645`:18247–18296, 피해 분담:8330–8387, 팀 노바 풀:1258–1264를 읽었음. 계정별 결과나 공략의 성공으로 이 경계를 덮지 않았음.

|조용한 근사 후보|이번 결론|허용 목록|
|---|---|---|
|몰락한 사념을 진단 경고 없이 처리하지만 속도 고정은 빠짐|M1 수정·회귀 고정|기존 키 없었음. 고쳐서 새 허용 항목 없음|
|속도 감소가 100%를 넘어도 최소1|M19 수정·회귀 고정|기존 키 없었음. 고쳐서 새 허용 항목 없음|
|‘세레스가 브레이크 턴을 늘린다’는 설명|게이지 감소에 따른 회복 지연임. 별도 연장 규칙 불필요|추가 없음|
|웨딩 카르멘 반응 차단이 공략에서만 온 가정인지|M6의 마비 버프로 클라 확인|추가 없음|
|소환 시작 게이지0|M18의 초기화로 확인. 소환 전체를 완전 일치로 확장하지 않음|시즌 중도 소환의 기존 D는 유지|
|카넬리아 +25%p를 단일 패시브로 취급하는지|기본15와 도전10을 분리해 시험함|추가 없음|
|R1·R2의 서버/잔여 경계|현재 모델 유지. 새 규칙을 추정해 넣지 않았음|기존 D 유지|

## 전후 비교와 검증

재현: `python -X utf8 -I tools/measure_casebook.py after`, 옛 규칙 비교는 `... legacy --legacy`. 표준 육성, 시드20261121, 각8판, 기본 자동 정책임. 기존 6개 시나리오의 실제 수정 전 기록과 legacy 재실행 결과가 일치했음. 티리아는 시즌1022 공개 시험 fixture를 사용했음. 평균 점수는 **각 판 점수의 평균**이며 평균 진행도를 점수식에 다시 넣지 않았음.

|시나리오|편성|평균 진행도 전→후|클리어율 전→후|평균 엔진 점수 전→후|
|---|---|---:|---:|---:|
|모굴루스 1단계·도전0|편애의 마녀·구원자 길레·에데·세레스|100%→100%|100%→100%|153,375→153,375|
|모굴루스 3단계·도전0|같음|70.34%→55.26%|0%→0%|2,311,250→1,934,312.5|
|모굴루스 3단계·도전18|같음|6.04%→6.04%|0%→0%|3,448,987.5→동일|
|태양 회랑200|편애의 마녀·구원자 길레·아모라·웨딩 카르멘|100%→100%|100%→100%|해당 없음|
|태양 회랑250|같음|97.66%→97.66%|50%→50%|해당 없음|
|바스커빌 3단계·도전0|같음|23.14%→23.14%|0%→0%|1,131,437.5→동일|
|티리아 3단계·도전18|그웬·페이·스마일·루나|3.88%→3.88%|0%→0%|3,184,081.25→동일|

모든 대표 시나리오는 진행도 >0을 검사했음. 모굴루스 도전18·티리아는 너무 일찍 패배해 결과 차이가 작거나 없을 수 있으므로, 수정 경로 자체는 별도의 작은 시나리오로 검사했음. 전체 전투 결과가 같다고 수정 경로가 없다고 결론내리지 않았음.

- 수정 전 전체 기준선: 243파일 통과, 실패0, 원문 표 경로 미설정으로 표 재생성 대조2건 건너뜀.
- 새 CB: 19시험 통과. 실제 효과 제거·게이지 지급 차단·추가 발동 차단·전역턴 차감 차단·실제 속도 최소1 복원 등 **19개 결함 주입에서 모두 assertion 실패**를 확인하고 원복했음. 오류로 중단된 변이는 성공으로 세지 않음.
- 허용 목록은 `tools/unsupported_allowlist.py --diff`로 대조했음. 신규/삭제0, A/B/C=0, D=32, E=77. 수정한 두 누락은 기존 진단에 없던 것이므로 삭제할 기존 키도 없었음.
- 빠른 계산 계수는 유지했음. `gen_quick_calib --per-content 400 --opboss`와 같은 2,323표본×40판(92,920판)을 계측하고, 속도1 미만 경로가 있었던 215표본을 두 규칙으로 다시 비교했음. 클리어 확률은 11표본에서 달랐지만 **보정에 쓰는 클리어/실패 경계 `clear_p >= 0.5`의 차이는 0**이었음. 같은 라벨을 사용하는 보정 계수를 바꿀 필요가 없어 이유를 적고 quick 도장을 갱신했음. 원시 공개 표준 입력 결과·계측 스크립트는 무시된 `local/casebook/calib_speed_*`·`check_calib_speed.py`·`compare_calib_speed.py`에 있음.
- 비활성 `guild_sim`은 시즌4 종료 후 새 시즌에 재생성한다는 기존 방침을 유지하고 사유를 기록했음. 이 인정은 길드 결과가 새 규칙에서도 같다는 주장이 아님. 직접 길드 시뮬은 새 엔진으로 실행됨.
- 최종 `python -X utf8 -I tools/run_tests.py --rebuild`: **244파일 통과·실패0·건너뜀0**. `COSMO_TABLES`를 현재 추출 표 사본에 지정해 표 재생성 대조도 수행했음. 리뷰 후 보강한 CB 19시험은 별도로 다시 통과했고 변이19개도 모두 검출했음. simpack을 재생성하고 생성물 도장 시험도 통과했음.
- 독립 리뷰는 작업 트리 대신 `87c8471..f8c55a6` 및 보완 스냅숏 `f8c55a6..2645ebe`의 불변 커밋 범위로 진행했음. 모굴루스 조건 설명, 일반 면역·회피의 검증 범위, 경쟁 버프 중첩 경계를 보완한 뒤 추가 차단 사항0으로 마쳤음.

공략의 증거가 없는 동작이나 서버 전용 값은 ‘미계산’으로 억지로 분류하지 않았음. 반대로 한 동작 시험의 성공을 전체 18편 공략 재현 성공으로 확대하지 않았음. 탐색 정책·화면·계정별 수치 보정은 변경하지 않았음.
