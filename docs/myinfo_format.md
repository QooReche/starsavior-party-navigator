# 내정보.json 형식 (`ss-myinfo-v1`)

설치형 추출 도구(비공개 저장소 `QooReche/starsavior-packet-ref` 의 `myinfo/`)가 만드는 파일. 페이지의 「내 정보 불러오기」가 이 파일을 읽는다.
**닉네임·UID·로그인 정보·세션 키는 담기지 않는다.** 전부 게임 내부 ID 와 수치뿐이다. 페이지는 서버로 보내지 않고 브라우저 `localStorage` 에만 저장한다.

```jsonc
{
  "format": "ss-myinfo-v1",
  "game_build": "25951618",              // 추출 당시 게임 빌드(스키마 기준)
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
      "gauntlet": { "journey": [1250, 435, 497, 148, 66], "level": 77 }   // 스텔라 아카이브(여정 스탯 5개, UI 순서) — 없을 수 있음
    }
  ]
}
```

스탯 이름: `NST_ATK, NST_HP, NST_DEF, NST_TURN_SPEED, NST_RATE_CRITICAL(0.01%), NST_RATE_CRITICAL_DAMAGE, NST_RATE_EFFECT_HIT, NST_RATE_EFFECT_EVADE, NST_NV_RATE_ATK/HP/DEF`(0.01% 단위 비율).
검증: 장비 합계는 5명 모두 게임 화면의 장비 탭 값과 일치(2026-10-21). 최종 능력치 계산 규칙은 `starsavior-packet-ref/tools/STATS.md`.
