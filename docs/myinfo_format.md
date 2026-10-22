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
                    "potentials": [[20001, 0, 3, 0]], "blessings": [10301, 10302] }   // [ID,레벨,비용할인 인덱스,계승 축복 레벨]; blessings 목록 의미 미확정
    }
  ]
}
```

스탯 이름: `NST_ATK, NST_HP, NST_DEF, NST_TURN_SPEED, NST_RATE_CRITICAL(0.01%), NST_RATE_CRITICAL_DAMAGE, NST_RATE_EFFECT_HIT, NST_RATE_EFFECT_EVADE, NST_NV_RATE_ATK/HP/DEF`(0.01% 단위 비율).
구원자 ID(`id`)·장비 아이템 ID 는 게임 내부 ID 이며, 페이지는 로스터의 `uid` 로 보유 구원자를 연결한다.

## 불러오기·저장·갱신 (페이지 동작)
- **불러오는 경로 두 가지**: ① 주소 해시 `#myinfo=<base64url(gzip(JSON))>` 로 열면 자동으로 읽는다(읽은 뒤 주소창에서 해시를 지운다. 해시는 서버로 전송되지 않는다). ② 서랍 「내 구원자 → 내 정보 불러오기 → 파일 선택」으로 `내정보.json` 을 고른다. 구현 `myinfo_import.js`, 연결 코드 `party_template.html`(`miApply`).
- **저장**: 브라우저 `localStorage` 키 `pn.myinfo` 에 JSON 전체(약 50KB)를 저장한다. 같은 브라우저·같은 PC 에서 다시 열면 상태("불러옴: 보유 구원자 N명")와 체크가 그대로 복원된다(시험 확인). 쿠키는 4KB 제한과 서버 전송 때문에 쓰지 않는다. 서버·외부로는 아무것도 보내지 않는다.
- **적용 범위(현재)**: 보유 구원자 체크(`pn.owned`)에만 반영한다. 저장된 별·각인·공명·스킬·호감도·장비·전술 레벨은 아직 시뮬 입력에 쓰지 않는다(다음 작업).
- **갱신**: 게임에서 육성이 바뀌면 파일을 다시 만들어 다시 불러온다(덮어쓴다). 자동 동기화는 없다. 「지우기」 버튼이나 브라우저 사이트 데이터 삭제로 지운다.
- **한계**: 다른 브라우저·다른 PC·시크릿 창에는 저장되지 않는다. 게임 업데이트로 파일 형식(`game_build`)이 바뀌면 불러오기 전에 알림이 필요하다(미구현).

## 능력치 계산 모듈 (1단계, 화면 연결 전)

Python `battlesim.starsavior.myinfo_stats.final_stats(unit, info, growth, rule="normal")`와
브라우저 `MyInfoStats.final_stats` / Node `require('./myinfo_stats.js').final_stats`는 같은 결과를 낸다.
`unit`은 `info.units`의 한 항목이며 `id`는 로스터 `uid`와 연결한다.
`growth`는 `tools/build_growth.py --static <비공개 경로>`로 만드는 `data/growth.json`이다.
빌더는 샘플·정답을 읽지 않고 성장 수치만 추출한다. 경로를 생략하면 `STARSAVIOR_STATIC`,
그 환경변수도 없으면 `E:\AI_mk2\starsavior-static-data`를 사용하며, 경로가 없으면 skip한다.

결과는 `{stats: {atk,hp,def,spd,cr,cd,eh,er}, missing: [...], power}`이다.
치확·치피·적중·저항은 1/10000 단위(12.34% → 1234)이다. 서로 다른 `game_build`이면
`build_mismatch: true`가 추가되고 계산은 계속한다. 누락된 입력은 중립 기본값을 쓰고 `missing`에 기록한다.
성장표 범위를 넘으면 마지막 누적값과 `growth:...:level` 진단을 반환한다.

`rule_for_content(content)`는 작전(`op`)·회랑(`clo`)에 `normal`, 코스모 게이트(`cosmo`)와
플래시 포인트(`rush`)에 `fixed200`을 반환한다. `fixed200`은 레벨 200·공명 10 고정이며
스타링크 추가 성장은 반영하지 않는다. **플래시 포인트 = BossRush 연결은 추정**이다.
미매핑 콘텐츠 또는 지원하지 않는 rule은 `None`/`null`이므로 호출 쪽에서 기존 가정으로 돌아간다.

시뮬 입력은 `{key, build: "none", stats_override: result.stats, stats_final: true}`이다.
유닛의 `build`가 전역 옵션보다 우선하여 표준 장비·잠재력·그 조건부 효과를 추가하지 않으며,
`stats_final`은 입력된 능력치의 상시 패시브 재적용을 막는다.
`power`는 내정보 스킬 4종 레벨 합과 PP=0으로 계산한다. 기존 API의 파티 전투력은 아직
스킬 레벨 합 34를 가정하므로 이 반환값과 다를 수 있다.

현재 계산은 **정확한 최종 능력치 재현을 완료하지 못했다**. 잠재력의 정적 수치는 해석했고,
별도 `blessings[]` 목록(`gauntlet_blessings`, 비어 있지 않을 때), PP(`power_pp`)를 남긴다.
스킬 데이터를 담지 않는 성장표만으로는 구원자 상시 패시브를 확정할 수 없어 `unit_passive`도 기록한다.
여정은 각 값을 1500으로 제한하고 공·생·방에 직업 배율을 곱한 뒤 각 환산값의 소수부를 버린다.
집중·보호는 각각 적중·저항에 ×4로 더한다(화면 단위로 ×0.04%p, 모든 직업 배율 1).
별 비율은 기준선대로 별+각인 등급의 누적을 사용하며, 레벨 의존 방식은 미확정이다.
`missing`이 있어도 정답 시험의 허용치를 완화하지 않는다. 건틀렛 탭 정답이 있는 2명은 8종 모두
정확히 일치하고, 최종 능력치의 속도·치확·치피·적중·저항은 5명 모두 일치한다.
최종 생명력은 4명에서 ±1%를 벗어나 정답 시험은 여전히 실패한다(기존 18항목 실패 → 4항목).

`gauntlet_stats(unit, growth)`는 Python/JS 공통으로 `{journey, potential, missing}`을 반환한다.
화면 탭의 고정 기여는 두 묶음의 같은 키를 더하고, 비율 기여는 `potential`의 `atkP/hpP/defP/spdP`다.
최종 계산에서는 여정 고정값을 x1에, 잠재력 고정값·비율을 각각 고정 합·R2에 넣는다.
`SE_POTENTIAL_TEMPLET.PotenLevelGroupId` → `POTENTIAL_LEVEL_GROUP_TEMPLET.PotenLevelValue`의
**a 레벨 한 행**을 쓴다(누적하지 않음). 레벨 0은 미습득이다. b/c와 건틀렛 `level`을
능력치 배수로 쓰지 않는다. 미지 ID/레벨은 `gauntlet.potential:<ID>[:level]`로 남긴다.
직렬화·합산 근거는 계산기 주석의 `NKM.Templets.cs:18436`, `NKM.cs:18628,18263,18344`와
현재 `reference/StatFactorBundle.cs`, `FinalStatCombiner.cs`다.

`STAT_POTENTIAL_TEMPLET`는 전투 스탯 NST가 아닌 여정 스탯 JST를 준다. 수입된 여정 값에
재가산하지 않는다. `blessings[]`를 무조건 이 표의 ID로 해석하는 근거도 없다.
3월 클라이언트의 대응 목록은 관문 이력 표시(`NKC.cs:231872 SetHurdleList`)에 사용된다.
현재 내보내기의 col13 매핑은 추가 확인이 필요하여 이 목록 자체는 미해석으로 남긴다.

성장표의 최상위 필드는 `_note`, `game_build`, `units`, `star_link`, `tactics`, `facility`,
`item_sets`, `sets`, `potentials`다. `potentials`는 ID → 레벨 → 8종 능력치 및 4종 비율의 수치만 담는다.
전투 전용 효과만 있는 알려진 잠재력은 빈 행으로 남겨 미지 ID와 구분한다.
유닛에는 `base`, `per_level`, `journey_mul`(3개), `resonance`,
`favor`, `star` 및 전술 수치를 연결할 최소 메타데이터 `tactics_groups`(속성·직업 2개)가 들어간다.
원본 텍스트·아이콘·스킬·피해·확률·장비 주부옵션 표는 포함하지 않는다.

시험: `python -X utf8 -I tests/myinfo_stats_test.py` (비공개 경로 없으면 정답·재생성 시험 skip).
`SyntheticTests` 인자로 합성 시험만 실행할 수 있다. `--mutations`는 각 새 시험에 잘못된 값을
메모리에서 주입해 실패를 확인하고 복원하며 파일을 바꾸지 않는다.
