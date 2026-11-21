# 공략 사례집 탐색 검사의 의심·미확인 항목 클라 대조 (2026-11-21)

## 결론

- `docs/casebook_search_check.md` «개별로 확인한 것» 1~4와 그 문서의 «미확인» 표시를 PC 26752678 클라 코드·표로 확정했음. **엔진이 클라와 다른 항목은 없었음.** 엔진 코드·규칙 기본값은 바꾸지 않았음. 그래서 전후 측정도 없음.
- 사례 14 «차원 강습은 역속성 강인도 피해 0»은 **맞음.** 다만 차원 강습만의 규칙이 아님. 클라는 공격자가 상성 불리이면 그 타격의 스킬 강인도 값과 〈강인도 피해〉 스탯을 모두 0으로 만듦. 차원 강습 영역의 강인도 피해 +1도 이 스탯이라 불리 대상에게는 0이 됨. 오비탈 자기 타격은 어느 속성 대상에게도 강인도를 깎지 않음.
- 사례 01 «누가 막타를 쳤느냐»도 클라와 엔진이 같음. 편애의 마녀의 추가 턴은 **자기 턴의 자기 시전 중에** 대상이 격파되어야 붙음. 연쇄 피해는 누가 깼든 대상이 격파 상태면 붙음(자기 턴일 때만).
- 길드 «신부 경쟁»은 클라 표 3%이고 엔진도 3%임(① M12 그대로).
- 이 내용을 고정하는 시험 `tests/casebook_suspects_test.py`를 새로 넣었음. 엔진을 일부러 깨뜨리면 두 시험 모두 실패하는 것을 확인했음.

## 자료

- 클라: `STARSAVIOR_STATIC=E:/AI_mk2/starsavior-static-data`의 `decompiled/`(빌드 26752678). NKM = `NKM/NKM.decompiled.cs`, ST = `Star.Templets/Star.Templets.decompiled.cs`, NT = `NKM.Templets/NKM.Templets.decompiled.cs`. 3월판은 쓰지 않았음.
- 표: `E:/AI_mk2/rebuild_26752678/T/CLIENT_*.json`, 조건 표는 `static-data/tables/Plain/SKILL_CONDITION_TEMPLET.json`(SC).
- 엔진: 이 작업 트리 `battlesim/mc.py`(커밋 45cb764 기준 줄 번호).

## 1. 사례 14: 브레이크 스킬과 강인도 상성

### 클라의 강인도 피해식(모든 타격 공통)

NKM:17194–17226 `SuperArmorController`. 대상 강인도가 이미 0 이하이거나, 일반·치명 타격이 아니거나, 〈강인도 피해 무효〉(SuperArmorDamageBan) 버프가 있으면 깎지 않음. 그 밖에는 다음과 같음.

|공격자 → 대상 상성|깎는 양|
|---|---|
|유리(NKM:17982–17993)|스킬 SuperArmorBreakValue + 1 + 공격자 `NST_SUPER_ARMOR_DAMAGE`|
|불리(NKM:17995–18004)|**0**(스킬 값·`NST_SUPER_ARMOR_DAMAGE` 모두 버림, NKM:17214)|
|그 밖(동일·중립·속성 없음)|스킬 값 + 공격자 `NST_SUPER_ARMOR_DAMAGE`|

여기에 공격자 `NST_SUPER_ARMOR_TRUE_DAMAGE`(강인도 고정 피해)를 더하고 대상 `NST_SUPER_ARMOR_DAMAGE_REDUCE`를 뺌(NKM:17221–17222). 합이 0보다 클 때만 깎음. 고정 피해는 불리여도 남음. 불리는 태양→달·달→별·별→태양뿐임. 질서·혼돈은 서로 유리만 있고 불리는 없음.

### 오비탈(브레이크 스킬) 자기 타격

- 스킬 값: ORBITAL_ARRAY 로더가 `SuperArmorBreakValue`를 읽지만 기본값 0임(ST:24200). 표의 브레이크 스킬 7행(11·21·101~105) 모두 이 열이 없음 → 0.
- 속성: 오비탈 유닛의 속성 속성(NKM:3187)은 값을 넣는 곳이 없어 enum 기본값 `NUAT_INVALID`(NT:32606–32614)임 → 유리도 불리도 아님.
- 스탯: 오비탈의 스탯 조회는 항상 0(NKM:3328–3331) → 영역의 `NST_SUPER_ARMOR_DAMAGE`도 오비탈 타격에는 안 붙음.
- 결과: **모든 대상 속성에서 0**. 앞 조사(`docs/break_skill_1121.md` 1절)와 같음.

### 강인도에 관계되는 브레이크 스킬

|브레이크 스킬|영역|강인도 관련 효과(BATTLE_EFFECT)|불리 대상|
|---|---|---|---|
|차원 강습(105, GLEIPNIRE)|CRF 증폭(DOMAIN 105, CharmList 7205001·7205002)|7205002 `NST_SUPER_ARMOR_DAMAGE` +1(아군 전원), 7205001은 공격력 +15%|+1이 0이 됨|
|행성 정화(104, ALICIA)|마녀의 은총(7203001·7203002)|7203001 `NST_SUPER_ARMOR_DAMAGE` +1|+1이 0이 됨|
|특이점 관측·스타피어서·큐브 과부하|—|강인도 효과 없음|해당 없음|

두 스킬 모두 고정 피해(`NST_SUPER_ARMOR_TRUE_DAMAGE`)가 아니라 일반 강인도 피해 스탯이라 불리 대상에게 0이 됨. 글의 «차원 강습은 역속성에 강인도 피해 0»은 이 규칙을 차원 강습에 대해 본 것으로, 클라와 맞음. 행성 정화도 같음.

### 엔진 대조

|항목|엔진|판정|
|---|---|---|
|불리 0·유리 +1·고정 피해 유지·감소 차감|`tough_hit` 3290–3363, 기본 `toughness_elem=client`(3339–3349). 불리면 `normal = 0`(3343)|일치|
|질서·혼돈 불리 없음|`rules.py:54` ELEM_LOSES에 질서·혼돈 없음|일치|
|영역 +1의 경로|`break_skills.차원 강습.props.강인도 피해 1`, `행성 정화` 같음 → `m['tough']` → `normal`에 더함(불리면 함께 0)|일치|
|오비탈 자기 타격|`apply_damage(None, v, hit, 'bskill')`(1784). `tough_hit`의 호출처는 일반 타격 경로 한 곳(3282)뿐이라 강인도·포인트 없음|일치|

새 시험 `DimensionalStrikeToughnessTest`: 태양 아군이 차원 강습을 발동한 뒤 기본기(스킬 강인도 0)로 치면 달(불리) 0·태양(동일) 1·별(유리) 2를 깎고, 발동 자체로는 대상 강인도가 그대로임.

사례 14 전투에서는 표준 육성이 티리아를 브레이크하지 못해 브레이크 스킬이 발동하지 않았으므로, 측정 결과(`casebook_search_check.md` 3번)는 바뀌지 않음.

## 2. 사례 01: 누가 브레이크했느냐와 편애의 마녀

### 클라

- 편애의 마녀 고유 패시브(SE_TEMPLET_SKILL_1, SKILL_END 시점):
  - 추가 턴 10614021(`BI_EXTRA_TURN`)·대기 표지 10614022(`BI_DARK_UNKNOWN_4`): 조건 52205(SC:9325–9331) = 내가 공격 후 · **MyTurn** · **TargetSuperArmorBreak** · 자신에게 `BI_DARK_UNKNOWN_4` 없음.
  - 연쇄 피해 10614013·014·017·018(4·3레벨 행 포함): 조건 2171·2172·52200(SC:1775–1790, 9272–9279) = 내가 공격 후 · MyTurn · **IsNotTargetSuperArmor** · 단일/광역·보스 표지.
  - 10614011·012·015·016: 조건 2169(SC:1760–1765) = MyTurn · IsNotTargetSuperArmor.
- TargetSuperArmorBreak는 «대상 강인도가 정확히 −1»(NKM:10251, 10390, 10492, 10638 → NKM:17253–17259)임. −1은 이번 타격으로 0 이하가 되면 설정되고(NKM:17289–17300), **모든 시전 끝에 0으로 풀림**(NKM:15826–15827 → 16017–16026). 시전 끝 처리 순서는 SKILL_END 조건 판정(NKM:15789) → 반응 예약 → … → −1 해제(15827)임. 협공·반응은 예약만 되고 해제 뒤 별도 시전으로 돎(NKM:15797–15800).
  - 그래서 −1은 **그 시전 안에서 격파된 대상**만 가짐. 편애의 마녀의 시전 끝에 −1인 대상은 그 시전의 편애의 마녀 타격으로 격파된 대상임. 다른 아군이 먼저 깼으면 그 시전 끝에 0으로 풀린 뒤라 −1이 아님.
  - 이미 0 이하인 대상은 강인도 피해를 받지 않으므로(NKM:17196–17200) 다시 격파되지도 않음.
- IsNotTargetSuperArmor는 «현재 강인도 ≤ 0인 대상이 있음»(NT:42461–42501, NKM:9321–9348)이라 누가 깼든 격파 상태면 참임.
- MyTurn은 시전자가 턴 유닛일 때만 참(NKM:9483–9489, 9615). 협공·반응처럼 남의 턴에 친 시전은 둘 다 안 붙음.

### 판정표

|상황|추가 턴|연쇄 피해|
|---|---|---|
|자기 턴, 자기 타격으로 이번 시전 중 격파|붙음|붙음|
|자기 턴, 다른 아군이 앞 시전에서 이미 격파|**안 붙음**|붙음|
|남의 턴(협공 등)에 편애의 마녀가 격파|안 붙음|안 붙음|
|같은 시전의 여러 타 중 어느 타로 격파|붙음(시전 끝까지 −1 유지)|붙음|

### 엔진 대조

|항목|엔진|판정|
|---|---|---|
|TargetSuperArmorBreak|`대상 브레이크`, 기본 `target_break_condition=event`: 이번 시전의 `ctx.break_targets`에 든 대상만 참(4520–4528). 시전마다 새 문맥|일치|
|IsNotTargetSuperArmor|`대상 강인도 없음`, 기본 `target_toughness_condition=any`: 현재 강인도 ≤0 대상이 있으면 참(4508–4519)|일치|
|MyTurn|`내 턴` = 시전자가 지금 행동 중인 유닛(4569–4574). 협공 시전은 `acting=False`|일치|
|이미 격파된 대상 재격파 없음|`tough_hit`에서 `v.broken`이면 깎지 않음(3308)|일치|

새 시험 `AsherahBreakerIdentityTest`: 위 표의 앞 세 줄을 그대로 확인함(자기 격파 = 추가 턴·연쇄, 남이 먼저 격파 = 연쇄만, 자기 턴 아님 = 둘 다 없음).

`casebook_search_check.md` 1번의 해석(편마가 빨라지면 세레스가 막타를 쳐서 편마의 추가 턴이 빠지고 피해가 124k → 65k로 줆)은 이 클라 규칙대로 나온 결과임. 엔진 의심 아님.

## 3. 사례 10·12: 길드 신부 경쟁

- 클라 표 BUFF_TEMPLET:46546–46608 `BI_AUTOMATON_MINIGUN_BOSS_1`: 최대 10중첩, `NST_NV_RATE_ATK` 300(= 중첩당 3%).
- 엔진 `data/guild_bfb.json` `bridal.atkPerStack 300·max 10·trigger 5` → `guild_bfb.py:398–409`가 공격력 +3%/중첩으로 씀. 정실 어필(1:1 대결)은 경쟁 카운트 5 이상에서 예약됨(`guild_bfb.py:388`). ① M12와 같음. **일치.** 글의 5%는 클라 표와 다름.

## 4. 그 밖의 «미확인» 표시

`casebook_search_check.md`에서 «미확인»은 위 사례 14와 «한계» 절의 한 줄뿐이었음.

- «강한 육성 구간에서 탐색이 사례를 놓치는지 미확인»: 엔진 규칙이 아니라 측정 범위(육성 체급) 문제임. 클라 코드로 정할 항목이 아니며, 강한 공개 가정 육성이나 비공개 계정으로 같은 도구를 다시 돌려야 확인됨. 이번에도 돌리지 않았음(미확인 유지).
- 같은 문서의 별명 대응 «추정»(수마일=`sunshine-cat-smile` 등)은 커뮤니티 별명 해석이라 클라 근거 대상이 아님. 이름·속성·직업은 `data/saviors_index.json`과 모순 없음.

## 시험

```
export STARSAVIOR_STATIC=<static-data>
python -X utf8 -I tests/casebook_suspects_test.py
```

- 새 시험 2개 통과. `tough_hit`의 불리 `normal = 0`을 지우고 `대상 브레이크`를 «지속 격파 상태»로 바꾸면 두 시험 모두 실패(1 != 0, (True, True) != (False, True))하고, 원복 뒤 다시 통과함.
- 관련 기존 시험: `break_skill_test`(36)·`client_gaps_1104_test`·`casebook_mechanics_test`(19)·`asherah_toughness_test`(6)·`guild_bfb_test`(20) 모두 통과.
- 규칙·엔진을 바꾸지 않았으므로 `rules_stamp`·`build_simpack`·`unsupported_allowlist`는 돌리지 않았음.
