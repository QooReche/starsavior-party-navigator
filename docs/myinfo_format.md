# 내정보.json 형식 (`ss-myinfo-v1`)

별도의 추출 도구가 만드는 파일. 페이지의 「내 정보 불러오기」가 이 파일(또는 주소 해시 `#myinfo=<base64url(gzip(JSON))>`)을 읽는다.
**닉네임·UID·로그인 정보·세션 키는 담기지 않는다.** 전부 게임 내부 ID 와 수치뿐이다. 페이지는 서버로 보내지 않고 브라우저 `localStorage` 에만 저장한다.

```jsonc
{
  "format": "ss-myinfo-v1",
  "game_build": "25951618",              // 추출 당시 게임 빌드
  "exported_at": "2026-10-22T00:20:00+09:00",
  "star_link_level": 343,                // 스타 링크 레벨(계정 공통, 구원자 레벨 역할)
  "tactics": {
    "facility_level": 5,                 // 전술 분석 시설 레벨(공격·방어·생명 비율 보너스: 레벨5 = +5%)
    "common_level": 111,                 // 공통 전술 레벨
    "groups": { "TG_STAR": {"level": 64, "attack": 65, "defense": 64, "hp": 65}, "...": {} }
                                         // TG_SUN/MOON/STAR/ORDER/CHAOS(속성), TG_DEFENDER/STRIKER/RANGER/CASTER/ASSASSIN/SUPPORTER(클래스), TG_ARCANA, TG_SAVIOR
  },
  "break_skills": [                      // 보유 브레이크 스킬(없는 파일도 있음 → 화면에서 직접 선택)
    {"id": 101, "level": 1}              // id = 정적 표 ORBITAL_ARRAY_TEMPLET.m_SkillID(101 특이점 관측·102 스타피어서·103 큐브 과부하·104 행성 정화·105 차원 강습), 레벨 1~10
  ],
  "units": [                             // 보유 구원자만(id 오름차순)
    {
      "id": 1040,                        // 정적 표 UNIT_TEMPLET_BASE1.m_UnitID
      "star": 3,                         // ★ 수(0~3)
      "sigil": 2,                        // 수호성 각인(별의 인장) 단계(0~6)
      "resonance": 10,                   // 공명 단계(0~10)
      "skills": {"basic": 7, "special": 7, "ultimate": 7, "passive": 4},
      "favor": 30,                       // 호감도 레벨
      "equip": [                         // 장착 장비(기본 탭 6칸)
        { "item_id": 511020301,          // 정적 표 EQUIP_ITEM_TEMPLET.EquipItemId
          "enhance": 15,
          "main": {"stat": "NST_ATK", "value": 375},
          "subs": [{"stat": "NST_HP", "value": 630}, ...] }
      ],
      "gauntlet": { "journey": [1250, 435, 497, 148, 66], "level": 77,   // 스텔라 아카이브(여정 스탯 5개, UI 순서) — 없을 수 있음
                    "potentials": [[20001, 0, 3, 0]], "blessings": [10301, 10302] }   // [ID,레벨,비용할인 인덱스,계승 축복 레벨]; blessings = 관문 이력, 전투 무관 (근거 NKC 231872)
    }
  ]
}
```

스탯 이름: `NST_ATK, NST_HP, NST_DEF, NST_TURN_SPEED, NST_RATE_CRITICAL(0.01%), NST_RATE_CRITICAL_DAMAGE, NST_RATE_EFFECT_HIT, NST_RATE_EFFECT_EVADE, NST_NV_RATE_ATK/HP/DEF`(0.01% 단위 비율).
구원자 ID(`id`)·장비 아이템 ID 는 게임 내부 ID 이며, 페이지는 로스터의 `uid` 로 보유 구원자를 연결한다.

## 불러오기·저장·갱신 (페이지 동작)
- **불러오는 경로 두 가지**: ① 주소 해시 `#myinfo=<base64url(gzip(JSON))>` 로 열면 자동으로 읽는다(읽은 뒤 주소창에서 해시를 지운다. 해시는 서버로 전송되지 않는다). ② 서랍 「내 구원자 → 내 정보 불러오기 → 파일 선택」으로 `내정보.json` 을 고른다. 구현 `myinfo_import.js`, 연결 코드 `party_template.html`(`miApply`).
- **저장**: 브라우저 `localStorage` 키 `pn.myinfo` 에 JSON 전체(약 50KB)를 저장한다. 같은 브라우저·같은 PC 에서 다시 열면 상태("불러옴: 보유 구원자 N명")와 체크가 그대로 복원된다(시험 확인). 쿠키는 4KB 제한과 서버 전송 때문에 쓰지 않는다. 서버·외부로는 아무것도 보내지 않는다.
- **적용 범위**: 보유 구원자 체크(`pn.owned`)와 육성 「내 정보」에 반영한다. 저장된 정보가 있으면 처음 열 때 기본 선택한다. `growth.json`은 이 모드를 선택할 때만 요청한다. 최종 능력치·전투력은 `MyInfoStats.final_stats`로 계산한다. 수동 입력은 육성 「내 전투력」에서만 적용하며, 수치를 편집하면 그 모드로 전환한다.
- **갱신**: 게임에서 육성이 바뀌면 파일을 다시 만들어 다시 불러온다(덮어쓴다). 자동 동기화는 없다. 「지우기」 버튼이나 브라우저 사이트 데이터 삭제로 지운다.
- **한계**: 다른 브라우저·다른 PC·시크릿 창에는 저장되지 않는다. 성장표와 `game_build`가 다르면 「빌드 다름」을 표시하고 계산은 계속한다.

## 맞춤 추천 화면 (2단계)

- 「추천 파티 / 내 정보」 화면 전환. 서랍의 「내 정보 보기」도 같은 탭을 연다.
- 내 정보: 스타링크·전술 공통·추출 날짜·보유 수·저장 날짜, 구원자별 전투력·★/각인·공명·스킬 4종·호감도·장비 칸/세트 효과·공/생/방/속도. 기본 전투력순, 이름순 전환. 모바일 카드형.
- 빠른 계산은 개별 `powers`에 계산 전투력을 넣고, 시뮬은 `build:none`, `stats_final:true`, 8종 최종 능력치를 전달한다. 기존 수동 전투력이나 육성 배수를 중복 적용하지 않는다.
- 내 정보가 없는 구원자/성장표 누락은 평균 가정과 「일부 가정」. 미매핑 콘텐츠는 「미매핑 · 평균 가정」. 성장표 오류도 평균 가정으로 돌아가며 탭에서 재시도한다.
- 파티 맨 위 「오토 가능 / 오토 어려움」은 빠른 계산 판정. 「약 +N 전투력 필요」는 같은 팀의 기존 사다리 첫 성공 배수와 현재 합계의 차이이며 1,000 단위 반올림(양수 최소 1,000)이다. 사다리 범위에서 성공하지 못하면 「필요량 산정 불가」.
- 실제 브라우저 시뮬 결과가 있을 때만 「오토 클리어 X% / 수동 X%」 표시. 기존 버튼/자동 설정을 유지한다. 결과는 실제 게임 성공률을 보장하지 않는다.
- 불러오기/지우기는 실행 중인 작업을 취소하고 캐시를 비운다. 서명에도 내 정보 해시를 넣는다. 추가 저장 키 없이 `pn.myinfo`를 쓰며 지우기는 그 키를 제거한다. 보유 체크와 기존 수동 입력은 보존한다.
- 공개 시험 자료 `tests/fixtures/myinfo_synthetic.json`은 가짜 수치로 작성한 합성 계정이며 실제 계정 자료를 복사하지 않았다.

## 능력치 계산 모듈 (1단계, 2단계 화면 연결)

### 전체 보기와 선택적 분해

구원자 행의 「상세」는 첫 펼침에만 분해를 계산한다. 「스킬」과 독립적으로 열며,
정렬·접기에서는 계산과 내부 펼침 상태를 재사용한다. 계정·성장표·콘텐츠 규칙 또는
시뮬 반영 모드가 바뀌면 캐시를 무효화한다. 계정 공통 내실은 탭 상단에서 따로 펼친다.

`final_stats(unit, info, growth, rule, breakdown=True)`(JS는 마지막 인자 `true`)는
기존 반환에만 `breakdown: {sources, stats}`를 추가한다. 기본 호출의 반환은 변하지 않는다.
`sources`는 계산에 실제 사용한 고정·비율 수치와 적용 레벨을 기록한다.
`stats[키]`는 `components`, `x1`, `r1`, `x`, `r2`, `y`, `final`을 담는다.
출처별 고정 기여에 `bundle = x1*r1 + x*r2`를 더하고, `rounding`으로 버림·0 하한 및
부동소수점 합산 잔차를 보정하면 최종 정수와 정확히 일치한다. 비율은 출처 옆에 R1/R2로
표시하며 합계 기여는 「묶음 비율 효과」 한 줄에 표시한다.

장비 6부위와 주·부옵, 완성 세트, 적용 내실 그룹, 여정 상한 1500, 습득 잠재력·전투 효과,
미해석 축복을 표시한다. 치확·치피·적중·저항과 능력치 비율은 모두 0.01% 단위로 표시한다.
시뮬 입력 칩은 같은 최종 8종·전투력·스킬 레벨을 사용하며, 평균 모드나 미매핑 콘텐츠는
「현재 시뮬 미적용」으로 구분한다. 누락 자료는 상세 하단의 진단으로 남는다.

`myinfo_view.js`는 첫 구원자 상세를 열 때만 다음 자료를 읽는다.

- `data/myinfo_view.json`: `tools/build_myinfo_view.py`가 공개 `rawdata/databook_main.json`의
  잠재력 이름·레벨별 효과 문구, 세트 이름, 부위명을 추출한다.
- `data/myinfo_slots.json`: `tools/build_myinfo_slots.py`가 아이템 ID → 0~5 슬롯 번호만
  가공한다. 원본 행·이름 문자열은 포함하지 않는다. 슬롯 순서는 공개 데이터북의
  무기·장갑·갑옷·신발·목걸이·반지 순서다. 미지 장비는 부위를 추측하지 않는다.
- `data/myinfo_combat.json`: 엔진이 적용하는 잠재력 효과 행만 선택하여 보여 준다.

검증: `tests/myinfo_breakdown_test.py`는 합성 계정·96개 변형의 Python/JS 결과와
분해 합을 대조한다. `tests/myinfo_view_test.js`는 단위·부위·세트·공개 이름·전투 효과를
검사하며, `tests/e2e/test_page.py myinfo_full`은 지연 계산·캐시·키보드·390px을 검사한다.

Python `battlesim.starsavior.myinfo_stats.final_stats(unit, info, growth, rule="normal")`와
브라우저 `MyInfoStats.final_stats` / Node `require('./myinfo_stats.js').final_stats`는 같은 결과를 낸다.
`unit`은 `info.units`의 한 항목이며 `id`는 로스터 `uid`와 연결한다.
`growth`는 `tools/build_growth.py --static <비공개 경로>`로 만드는 `data/growth.json`이다.
빌더는 샘플·정답을 읽지 않고 성장 수치만 추출한다. 경로를 생략하면 `STARSAVIOR_STATIC`,
그 환경변수도 없거나 경로가 없으면 안내 후 실패함.

결과는 `{stats: {atk,hp,def,spd,cr,cd,eh,er}, missing: [...], power}`이다.
치확·치피·적중·저항은 1/10000 단위(12.34% → 1234)이다. 서로 다른 `game_build`이면
`build_mismatch: true`가 추가되고 계산은 계속한다. 누락된 입력은 중립 기본값을 쓰고 `missing`에 기록한다.
성장표 범위를 넘으면 마지막 누적값과 `growth:...:level` 진단을 반환한다.

`rule_for_content(content)`는 작전(`op`)·회랑(`clo`)에 `normal`, 코스모 게이트(`cosmo`)와
플래시 포인트(`rush`)에 `fixed200`을 반환한다. `fixed200`은 레벨 200·공명 10 고정이며
스타링크 추가 성장은 반영하지 않는다. **플래시 포인트 = BossRush 연결은 추정**이다.
미매핑 콘텐츠 또는 지원하지 않는 rule은 `None`/`null`이므로 호출 쪽에서 기존 가정으로 돌아간다.

시뮬 입력은 `{key, build: "none", stats_override: result.stats, stats_final: true, power: result.power, myinfo_combat: result.combat}`이다.
유닛의 `build`가 전역 옵션보다 우선하여 표준 장비·잠재력·그 조건부 효과를 추가하지 않으며,
`stats_final`은 입력된 능력치의 상시 패시브 재적용을 막는다.
`myinfo_combat`은 실제 스킬 레벨과 습득 잠재력의 전투 효과·추가 강인도를 전달한다.
규칙 `mc.myinfo_combat=false`로 종전 동작을 재현할 수 있다. 감사·중복 제외 기준은 `docs/myinfo_combat_audit.md`에 기록했다.
`power`는 내정보 스킬 4종 레벨 합(고유 패시브 포함)과 습득 잠재력의 전투력 PP로 계산한다.
PP는 `potential_pp[ID][a]`의 합이다. 해당 잠재력의 1~a 레벨 중 `PotenBattlePowerCheck`가
참인 행의 `PotenLevelUpReqPP`를 누적한 값이며 할인 b·축복 레벨 c는 적용하지 않는다.
각인·장비는 최종 능력치에 반영되며 별도 PP를 더하지 않는다. 이 값을 API에 전달하면 파티 전투력에
반영한다. 생략한 기존 입력은 스킬 레벨 합 34를 가정하므로 계산 결과가 다를 수 있다.

현행 계산은 `floor(능력치 점수 × (1 + PP/10000) × (1.06 + 스킬합/100))`이며
능력치 점수는 `build.py:unit_power`의 세 방식 최댓값(속도·적중·저항 배율 포함)이다.
3월 해독 코드 `NKM.decompiled.cs:17259`는 단일 방식과 실제 돌파 등급 × 2%를 쓴다.
현재 화면과 맞는 데이터북 공식을 구버전으로 교체하지 않는다. PP 누적 근거는
`Star.Templets.decompiled.cs:21677`, 스킬 전체 합 근거는 `NKM.decompiled.cs:17240`이다.
현재 roster의 스킬 슬롯이 4개인지는 성장표 생성 시 검사한다.

2026-10-22 같은 시점의 정답 5명은 **공·생·방을 포함한 8종 모두 정수 단위까지 일치**한다.
`blessings[]`는 관문 이력(건틀렛 레벨 대응 목표 ID, 전투 무관). `gauntlet_stats`가 `hurdles`로 반환하며 `missing`에는 포함하지 않는다.
`power_pp`는 잠재력 목록·항목 또는 성장표의 PP를 해석하지 못할 때만 남긴다.
확인된 PP는 누적하며 미지 항목은 0으로 처리한다. 빈 목록·레벨 0은 알려진 PP=0이다.
상시 패시브는 성장표에 가공한 레벨별 정적 수치로 반영한다. 정상 해석한 유닛에서는 `unit_passive`를
제거하고, 표 누락·미지 레벨에만 `unit_passive` / `unit_passive:level`을 남긴다.
여정은 각 값을 1500으로 제한하고 공·생·방에 직업 배율을 곱한 뒤 각 환산값의 소수부를 버린다.
집중·보호는 각각 적중·저항에 ×4로 더한다(화면 단위로 ×0.04%p, 모든 직업 배율 1).
정답 시험의 공·생·방 회귀 한도는 각 ±0.5%(이번 최대 오차 0% + 0.5%p)로 고정했다.
`missing`을 이유로 한도를 완화하거나 실행 결과에 맞춰 한도를 다시 계산하지 않는다.
10/21 공개 화면 3명은 10/22 내정보와 시점이 다르므로 출력만 한다(현재 +0.10~+0.20%).

공·생·방의 공통 과대 원인은 돌파 `star`를 각인 `sigil`에 더한 것과 공명·각인 묶음의 오분류였다.
`STAR_GRADE_TEMPLET.StatData`는 **sigil만** 누적해 R2에 넣는다. 돌파는 이 비율에 더하지 않는다.
근거: `NKM.Templets.decompiled.cs:17837-17842`의 별도 직렬화 필드,
`NKM.decompiled.cs:1979-1982,18541-18556`의 각인·공명 전달 경로.
`IUnitResonanceTemplet`의 `UnlockLevel`도 적용한다(`NKM.Templets.decompiled.cs:25673-25690`).

일반 PvE의 핵심 합산 순서는 다음과 같다. 기존 비공개 분석 메모의 공명·별 이름은 반대로 읽혔으므로
인터페이스 연결을 기준으로 정정했다(`Star.Templets.decompiled.cs:28603,29184,29214`).

```text
x1 = 기본 + 레벨 + 스타링크 + 환산 여정
x  = x1 + 공명 고정 + x1 × 공명 비율(R1)
y  = x + 장비·잠재력·호감도·전술·패시브 고정 + x × R2
R2 = 각인 + 장비·세트 + 잠재력 + 시설·전술 + 상시 패시브 비율
최종 = floor(y)
```

공명 고정은 R1 뒤, R2 앞에 들어간다(`NKM.decompiled.cs:18260-18271,18342-18354`).
시설 +5%는 `CENTRAL_FACILITY_TEMPLET.BonusType=TACTICS_COMMON_RATE_TRINITY`의 누적 NV_RATE이며
기존 R2 처리를 유지한다(`reference/CentralFacilityTactics.cs`, `NKM.decompiled.cs:18846`).
상시 패시브는 `UNIT_TEMPLET_BASE1.m_listSkill` → `SKILL_TEMPLET_1/2.SkillLevelGroup` →
`SKILL_LEVEL_GROUP_TEMPLET_1/2.SkillLevelStat`의 실제 습득 레벨 **한 행**이다.
`SkillLevelStatType`과 `SkillLevelStatRate/Value`를 가공하며, 이전 레벨과 누적하지 않는다.
근거는 `Star.Templets.decompiled.cs:25785,26156-26170`,
`NKM.decompiled.cs:18566-18608,18269-18271` 및 현재
`reference/StatFactorBundle.cs:118-119`, `FinalStatCombiner.cs:193-195`다.
엔진 DB의 최대 레벨 패시브를 그대로 쓰면 현재 습득 레벨보다 과대해질 수 있다.

`gauntlet_stats(unit, growth)`는 Python/JS 공통으로 `{journey, potential, missing}`을 반환한다.
화면 탭의 고정 기여는 두 묶음의 같은 키를 더하고, 비율 기여는 `potential`의 `atkP/hpP/defP/spdP`다.
최종 계산에서는 여정 고정값을 x1에, 잠재력 고정값·비율을 각각 고정 합·R2에 넣는다.
`SE_POTENTIAL_TEMPLET.PotenLevelGroupId` → `POTENTIAL_LEVEL_GROUP_TEMPLET.PotenLevelValue`의
**a 레벨 한 행**을 쓴다(누적하지 않음). 레벨 0은 미습득이다. b/c와 건틀렛 `level`을
능력치 배수로 쓰지 않는다. 미지 ID/레벨은 `gauntlet.potential:<ID>[:level]`로 남긴다.
직렬화·합산 근거는 계산기 주석의 `NKM.Templets.cs:18436`, `NKM.cs:18628,18263,18344`와
현재 `reference/StatFactorBundle.cs`, `FinalStatCombiner.cs`다.

`STAT_POTENTIAL_TEMPLET`는 전투 스탯 NST가 아닌 여정 스탯 JST를 준다. 수입된 여정 값에
재가산하지 않는다. `blessings[]`(관문 이력)를 이 표의 ID로 해석하는 근거도 없다.
3월 클라이언트 `NKC.cs:231872 SetHurdleList`가 이 목록을 관문 이력 UI에만 사용함이 확인됨.
전투 스탯 기여 없음. `gauntlet_stats` 반환값 `hurdles`에만 담으며 능력치·전투력은 변동 없다.

성장표의 최상위 필드는 `_note`, `game_build`, `units`, `star_link`, `tactics`, `facility`,
`item_sets`, `sets`, `potentials`, `potential_pp`다. `potentials`는 ID → 레벨 → 8종 능력치 및 4종 비율의 수치만 담는다.
`potential_pp`는 ID → 레벨 → 누적 전투력 PP 수치만 담는다(비용 원본·할인표 제외).
전투 전용 효과만 있는 알려진 잠재력은 빈 행으로 남겨 미지 ID와 구분한다.
유닛에는 `base`, `per_level`, `journey_mul`(3개), `resonance`, `resonance_unlock`(등급 → 해금 레벨),
`favor`, `star`, `passive`(레벨 → 상시 능력치) 및 `tactics_groups`(속성·직업 2개)가 들어간다.
원본 텍스트·아이콘·스킬 효과·피해·확률·장비 주부옵션 표는 포함하지 않는다.

시험: `python -X utf8 -I tests/myinfo_stats_test.py` (비공개 경로 없으면 정답·재생성 시험 skip).
`SyntheticTests` 인자로 합성 시험만 실행할 수 있다. `--mutations`는 각 새 시험에 잘못된 값을
메모리에서 주입해 실패를 확인하고 복원하며 파일을 바꾸지 않는다.

불러오기 때 중첩 필드를 검증하고 성장표 계산에 성공한 뒤 저장함. 저장 실패면 현재 화면에 적용하고 「저장 안 됨」을 표시함. 잘못된 기존 저장값은 지우기 또는 파일 다시 불러오기로 복구함.
