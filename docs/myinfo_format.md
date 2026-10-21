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
                    "potentials": [[20001, 0, 3, 0]], "blessings": [10301, 10302] }   // 잠재력 [ID,?,?,?]·축복 ID(선택 필드, 의미 일부 미확정)
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
