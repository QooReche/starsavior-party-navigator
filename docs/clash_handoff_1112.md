# 격전 의뢰(Onslaught Quest) 반영 인수인계 — 2026-11-12 게임 PC → 작업 PC

데이터북에 아직 없는 신규 콘텐츠 «격전 의뢰»(11/12 04:00 ~ 12/03 04:00, 보스 3종 × 6단계 = 18스테이지)를 **PC 클라 표(정답지)에서 직접** 만들어 엔진·화면에 붙였음. 사용자 방침: 정확한 정보는 PC 클라 디컴파일·표 기준, 확인 못 한 것은 추측하지 않고 클라에서 찾을 것.

## 한눈에

| 항목 | 상태 |
|---|---|
| 스테이지·스탯·배치·해금·소환 데이터 | 완료(클라 표 → `data/foe_clash.json`) |
| 스킬 효과 줄 변환 | 완료 — 새 보스 SE 75행 중 73행 변환, 옛 판(데이터북에 있는 같은 계열 보스) 재현 스킬 63/63·줄 134/134·상태설명 78/78 일치 |
| 엔진 연결(로더 병합·battle_end·소환·스폰) | 완료 — 18스테이지 시뮬 실행 확인(`simulate({'units':[…]}, {'stage':'clash/<탭>/<이름>'})`) |
| 화면 연결(콘텐츠 목록·기간 게이트·장비 탐사와 같은 «정상 레벨») | 코드 반영, **화면 확인(e2e·스크린샷) 안 함** |
| 퍼세스 «판별» 강제 협공 | **미반영**(아래 1번) — 시뮬 결과의 «지원하지 않음» 목록에 표시됨 |
| 실제 플레이·영상 대조 | **없음** |

## 데이터 흐름

```
비공개 static-data/tables (클라 표, 빌드 26610546)
  └ tools/build_foe_clash.py --static <static-data>   → data/foe_clash.json (조각: u·s·x·g + aux·boss_kill·period·unmodeled·check)
      └ battlesim/starsavior/foe.py  load_extra()/merge_extra()  (foe.js 뒤에 덧붙임, 조각 안 인덱스는 «조각 내부 0 기준» + 오프셋)
          ├ load_foe()  → FoeDef·stage_waves 가 그대로 읽음(콘텐츠 키 'clash')
          ├ spawn_flags()/foe_summon()/battle_end()  → aux·boss_kill 병합(extra_aux/extra_boss_kill)
          └ tools/build_foe.py → data/foe_stages.json 에 'clash' 콘텐츠 포함 → build_party_html.py (CONTENT_META['clash'])
```
- 데이터북 `foe.js` 가 같은 콘텐츠 키(`clash`)를 반영하면 `merge_extra` 가 조각을 **자동으로 쓰지 않음**(데이터북 우선). 그때는 조각 값과 데이터북 값을 대조(레벨·전투력·스킬 수치)한 뒤 `data/foe_clash.json`·`tools/build_foe_clash.py` 를 정리할 것.
- 재생성: `python -X utf8 -I tools/build_foe_clash.py --static <static-data>` → 이어서 `build_foe.py`, `build_foe_spawn.py`·`build_foe_summon.py`·`build_foe_auto.py`·`build_foe_react.py`·`build_battle_end.py`(각 `--static`) → `tools/run_tests.py --rebuild`.
- 시험: `tests/foe_clash_test.py`(스키마·옛 판 재현율·스탯 독립 계산·18스테이지, 변이 6종 검출 확인). 로더 병합·게이트·화면은 **전용 시험이 아직 없음**(남은 일 5).

## 이번에 건드린 파일(공개 저장소)

- 새 파일: `tools/build_foe_clash.py`, `data/foe_clash.json`, `tests/foe_clash_test.py`, 이 문서.
- 엔진: `battlesim/starsavior/foe.py`(`load_extra`·`merge_extra`·`extra_aux`·`extra_boss_kill`, `spawn_flags`·`foe_summon`·`battle_end` 병합, `FoeDef` 미반영 효과 기록), `battlesim/mc.py`(조건 키 «대상 강화효과 개수 이하» 추가 = 대상 강화 효과 수 ≤ N·0개 포함, 지원 보고에 «격전 의뢰 효과 미반영» 출력), `battlesim/starsavior/myinfo_stats.py`·`myinfo_stats.js`(`clash`→normal 레벨).
- 빌더: `tools/build_foe.py`(조각 병합), `tools/build_foe_spawn.py`(`candidates()` 에 격전 의뢰 BattleStrID 규칙).
- 화면: `build_party_html.py`(`CONTENT_META['clash']`, `boss` 플래그, `seasonPeriod`), `party_reco.py`(`FOE_KEYS`), `season_gate_ui.js`(`SEASON_KEYS` 에 clash — 기간 끝나면 «미오픈»), `star_link_ui.js`.
- 규칙 메모: `battlesim/rules/default.json` `enemy_hit_buff_cmp` 에 클라 근거 추가(기본값 `le` 가 클라와 같음, 값 변경 없음).
- 이 변경으로 `data/foe_stages.json`·`foe_spawn`·`foe_summon`·`battle_end`·`index.html`·`sim/manifest.json` 등 생성물이 바뀜.

## 클라에서 확인한 것(근거)

- 스테이지·보스·스킬 해독 전체와 근거 표 위치: 비공개 `starsavior-static-data` `analysis/clash_1112.md`·`clash_1112_se.md`(SE 조건 ID·공식 설명문)·`clash_1112_buffs.md`(버프 정의). 해독 스크립트는 비공개 저장소 `tools/decode_clash_se.py`(SE 해독표)·`tools/diff_clash_variants.py`(6변형 비교) — 공개 저장소 작업 폴더에서 `python -X utf8 -I <스크립트> <src 루트> <static-data 루트> [출력 md]` 로 실행(`tools.tables.jsonc` 사용). `SkillLevelGroup.SkillLevelSE` 목록 기준(이름 접두 매칭은 번호 없는 이름·클라 오타 `SPEICIAL` 을 놓침).
- 조건 `BuffCountLess N` = 개수 ≤ N(0개 포함): `NKM.Templets` 43328 부근, `TargetPositiveBuff` 는 대상 강화 효과 수를 세는 조건(42752). → 웬디고 기본기 빙결(조건 2161)을 «대상 강화효과 개수 이하: 1» 로 변환.
- 변형 유닛 `_02~_06` 은 `m_listSkill` 로 `_01` 스킬을 그대로 쓰고 퍼세스만 특수기가 `_0N_SPECIAL`(소환 그룹 1301~1306 만 다름).
- 레벨 고정 없음: `BATTLE_STAT_APPLY_TEMPLET` 에 격전 의뢰 장면이 없음(장비 탐사·일일과 같은 정상 레벨).
- 기간은 클라 표에 없음(서버 INTERVAL). 공지·게임 화면 기준 11/12 04:00 ~ 12/03 04:00(UTC+9)을 `data/foe_clash.json` `period` 에 직접 기록.

## 남은 일(우선순위 순) — 모두 PC 클라에서 먼저 찾을 것

1. **퍼세스 판별(기본기)의 강제 협공**: 효과 줄을 못 만듦. 클라 `AutoTargetId` 52 = `{IsNotUnableToAct, IsNotSpecificBuff:[BI_DISABLE_CROSS_ATTACK], IsHighAtk}`(공격력 최고·행동 가능·협공 불가 표지 없는 다른 아군). 의미 근거는 디컴파일 `NKM.decompiled.cs` 7535(`IsNotSpecificBuff`)·7572(`IsHighAtk`)·7754(`IsNotUnableToAct`), 필터 목록 `NKM.Templets` 41399~41611. 엔진은 `강제 협공` 효과(`mc.py` 4363)와 `foe_auto` 자동 대상 어휘(`tools/build_foe_auto.py`)를 이미 가짐 — 어휘에 이 3개 조건 조합을 더하고 변환기의 `변환 불가` 처리를 풀면 됨. 효과: 부하 고대 병졸이 판별 뒤 추가 기본기를 침.
2. **전투 제한 턴**: 표에는 «별 3개 조건 `BMT_LIMIT_TURN` 65·60» 만 있고 패배 턴 제한은 못 찾음. 지금 시뮬은 상한 50턴(`max_turns`). 클라 전투 종료 조건 코드에서 확인.
3. **`AddStatData` 와 레벨 적용 순서**: `foe_stats` 공식(`b + gw×(L-1)` 뒤 % 보정)을 가정. 클라 스탯 계산 코드로 확인(시험은 같은 공식으로 독립 계산해 일치만 봄).
4. **버전 업그레이드 수치**: SE `BuffDesc` 는 `@@3` 인데 `Stats` 는 500. 지금은 `Stats`(5%/중첩, 최대 5) 기준. 클라가 어느 쪽을 쓰는지 확인. `WeakAdjustData`(모티 달·웬디 별·퍼세스 태양) 의미도 미확인.
5. **시험·화면 확인**: 로더 병합(조각 on/off), `battle_end`·소환·`period` 게이트, `build_party_html` 콘텐츠 목록에 «격전 의뢰» 가 뜨는지, 기간 종료 후 «미오픈» 이 되는지에 대한 전용 시험 + e2e/스크린샷. 장비 탐사처럼 «정상 레벨»·보스 3탭·6단계 화면이 맞는지.
6. 엔진: 새 보스의 피격·사망 반응 줄은 `mc.py` `REACT_TRIG` 로 해석되고 정적 지원 검사에서 걸린 것은 없었음. 그러나 **실제 전투 로그로 보스가 스킬 순서대로 쓰고 장막·중첩이 쌓이는지 눈으로 확인하지 않았음**(`mc` 이벤트 로그 확인).
7. `foe_auto`: 격전 의뢰 보스에는 AutoSkillId/SkillOrderList 규칙이 표에 없어 엔진 기본(궁극기→특수기→기본기) 적용. 이것이 게임 기본과 같은지(규칙 없음 = 기본) 코드로 재확인.
8. 데이터북이 격전 의뢰를 반영하면 위 «데이터 흐름» 의 정리 절차.

## 주의

- 원본 클라 표·디컴파일은 공개 저장소에 넣지 않음. 이 문서의 줄 번호는 비공개 `decompiled/`(빌드 26610546, `OBF_` 번호는 빌드마다 바뀜) 기준.
- 해독 스크립트 위치는 위 «클라에서 확인한 것» 참조(비공개 저장소 `tools/`).
