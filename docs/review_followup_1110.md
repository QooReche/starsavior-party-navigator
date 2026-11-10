# 2026-11-10 밤 독립 리뷰 권고 반영

대상은 `93d300f..a732566` 리뷰 R1~R6임. 공개 standard와 합성 입력만 썼음.
근거는 비공개 static-data `64e4fad`, `decompiled/BUILD.md`의 26314877→26429597 로직 불변 기록을 확인했음.
아래 NKM은 `decompiled/NKM/NKM.decompiled.cs`임. 비공개 원문을 공개 저장소로 복사하지 않았음.

| 권고 | 처리 | 직접 확인·반영 내용 |
| --- | --- | --- |
| R1 | 반영 | `mc.py:cast`의 정화 로그가 legacy에서도 실행됐음. `all_casts`에서만 새 로그를 남기도록 고쳤음. 노바 지급 식은 유지했음. |
| R2 | 반영 | NKM:822의 일반 게이지 초기화와 826의 추가 턴 예약 초기화는 별도임. `clear`는 예약 보유자의 게이지 표시만 제거하고 일반 게이지는 `_reset_wave_gauge`에 맡겼음. 기본 `clear/reset`의 WAVE_START 전 초기화 순서는 유지해 기본값 결과 변화도 막았음. |
| R3 | 반영 | NKM:13493·15831–15855의 아군/적 턴 시작 SE는 틱 전, 13495·13421–13424의 지속 틱 뒤 13496–13503에서 NSEAT_TURN_START 반응 스킬을 예약함. `ally_ts/enemy_ts`와 두 경로의 전수 대응이 미확인임을 note에 명시했음. 순서를 추정으로 바꾸지 않았음. |
| R4 | 반영 | `mc.py:_expire_checks`는 전역 `check_pending` 전체를 정리함. 안쪽 시전 종료 때 바깥 확인용 효과도 제거되는 경계를 note에 명시했음. 클라도 NKM:4021–4028·15394–15396·15586–15593에서 전역 턴 기준으로 전원을 정리하지만 엔진 nested 시전과의 대응은 미확인임. `action` 기본 유지, `skill` 기본 전환 전 검증 대상으로 남겼음. |
| R5 | 반영 | `mc.py:run_special`의 부활은 HP 0에서 등장 후 줄을 실행한 뒤 HP를 대입함. 회복 덮어쓰기·HP 0% 조건·자해 사망 경계를 note에 명시했음. NKM:5395→1207–1221의 주입기 뒤 5400–5407에서 HP를 설정하는 순서는 확인됐으나 HP 조건부 SE 대응은 미확인임. 기본 `off` 유지했음. |
| R6 | 부분 반영·부분 기각 | 실제 길방 1단계, standard, seed 1에서 자연 전투로 보스 진입·진행도 > 0.5·보스 행동·초기화 `rule_hits > 0`을 검사하는 시험을 추가했음. «guild_sim 미재계산»은 a732566의 HANDOFF 11/10 밤에 전체 234,000판 재계산이 기록돼 있어 기각했음. 해당 커밋의 `data/guild_sim.json` 변경과 `tools/gen_rules_stamp.json`의 `fc85dd2714434381` 재생성 기록도 확인했음. 이번 수정의 기본값 결과는 불변이라 다시 계산하지 않았음. |

## 시험

- 기준선: `STARSAVIOR_STATIC=E:\AI_mk2\starsavior-static-data`, 전체 103 통과/0 실패. COSMO_TABLES·옆 journeyhelper 저장소 없음 2건은 환경 건너뜀임.
- `tests/review_legacy_test.py` 3개: 정화 legacy 로그·3000개 상한, 예약 유무×예약 정책×게이지 정책×웨이브 이월의 16조합, 기본 초기화의 WAVE_START 전 순서·새 예약 유지.
- `python -X utf8 -I tests/review_legacy_test.py --history`: git의 `93d300f:battlesim/mc.py`를 직접 불러 비교했음. 당시 기본값과 신규 키 legacy를 적용한 정화 2건(일반/상한 경계), 웨이브 12건에서 결과·진행도·HP·게이지·피해·회복·쿨·시전 횟수·시간선·난수가 같았음. 예약 없는 아군은 `wave_extra_turn=clear`를 켠 상태도 옛 게이지 이월과 비교함. 실행에는 해당 git 이력이 필요함.
- `--mutations`: 정화 legacy 로그 재주입·예약 없는 아군 게이지 강제 0·기본 초기화의 이벤트 전 호출 제거 3종에서 assertion 실패를 확인했음. R6의 실제 전투 시험도 초기화 규칙을 `off`로 강제하면 assertion 실패했음.
- a732566 엔진과 기본값 쌍 비교: 회랑 3곳·코스모 3보스·길방 0/1/9단계 × seed 1~8 = 72판씩. 모두 공개 standard, 행성 정화 장착, 진행도 > 0을 확인했음. 실행 시간 외 API 결과 전체(시간선·판별 진행도·유닛별 결과 포함)가 같았음.
- 규칙 기본값·골든·quick·guild_sim은 유지했음. simpack을 재생성했고 HTML 생성 결과는 기존과 같았음. 기본값 결과 불변이므로 계수 재보정·길방 재계산·e2e 재실행은 하지 않았음.
- 최종 전체: 같은 `STARSAVIOR_STATIC`으로 `python -X utf8 -I tools/run_tests.py` 일반 **104 통과/0 실패**. 환경 건너뜀 2건은 기준선과 같았음.
- 독립 리뷰: 고정 범위 `a732566..e4428ead70b71b99a4b2e4924ad483ebc87b5a8c`의 엔진·시험·note와 위 클라 근거를 대조해 수정 필요 지적 없음. 스냅숏은 브랜치에 연결하지 않았고 최종 변경은 한 커밋으로 묶음.
