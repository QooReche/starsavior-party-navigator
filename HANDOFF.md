# 인수인계

갱신 2026-11-08. 읽는 순서: 이 파일 → README.md → docs/DEVELOPMENT.md. AI 작업 규칙은 [AGENTS.md](AGENTS.md). 옛 기록은 [docs/HISTORY.md](docs/HISTORY.md).

## 현재 상태

- 근거 코드는 비공개 static-data `decompiled/`의 Steam 빌드 **26314877**임(`decompiled/BUILD.md`). 외부 3월판 근거 규칙을 A/B/C/D 묶음으로 재확인했음. 표 기록 빌드 26291832와 DLL의 내용 동일성은 게임 PC 확인 대상으로 남겼음.
- 협공 기본값: `formula.COOP_CAP=1.0`, `opts.coop_trigger=basic_only`, `coop_single=true`, `coop_order=random_success`, `forced_coop_target=random`, `forced_coop_slot=shared`, `coop_dead_target=cancel`. 강제 효과 대상을 먼저 정하고 유효 강제 후보 중 균등 1명을 고름. 강제 후보가 없으면 일반 후보 전원 판정 후 성공자 중 균등 1명임. 단일 본대상 사망 시 협공을 취소함.
- 11/08 기본 전환: `enemy_leader=none`(적 리더 속도 +10 제거, legacy=boss, 절 «11/08 밤 틱 제외 조건» 안 «적 리더» 항목), `any_turn_source=table`(전체 턴 시계 버프를 표 `GlobalTurnCounting` 으로 판정, legacy=text, 절 «전체 턴 시계를 표 기준으로»).
- 11/05 기본 전환: `dot_formula=client`, `react_hist_unit=unit`, `immune_force_apply=client`(절 «2026-11-05»). 11/04 전환 4개는 `preemptive_defense=client_main`, `toughness_elem=client`, `break_point_hits=window`, `break_auto_blocked_cc=on`. 11/05 오전에 `guild_boss_nv_sum=client`(길방 보스 속도·공격력 합산)도 기본으로 넣었고 9·10단계 낙관의 주원인이었음(절 «11/05 오전»). 길방 표는 이 기본으로 재생성함.
- 그 밖의 새 기본값: `mc.enemy_cd_end_order=after_effects`, `revenge_rate=hit`, `nova_force_cap=12`, `ally_auto_lines=client`. 기존 병합분 `foe_skill_order=data`, `empty_attack=process`, `ally_variant_mapping=data`도 반영했음. 선제 방어 실험용 `client`는 차단 조건을 보강했음. 선제 방어 기본값은 11/04 전환한 `preemptive_defense=client_main`임(legacy=recognize).
- 기존 기본값은 `enforce_timing=queue`, `enforce_target=exec`, `wave_ally_gauge=reset`, `buff_ban=refuse`, `buff_ban_force=client`, `guild_count=all`, `instant_damage=damage`, `reaction_timing=queue`, `skill_order=data`, `dispel_on_attack=on`, `turn_limit_unit=actions`, `break_skill_domain_clock=global`, `break_skill_domain_turns=5`, `enemy_hit_buff_cmp=le`임(`toughness_elem`은 11/04부터 `client`, legacy=db). 정본은 `battlesim/rules/default.json`임.
- 길드방어전 시즌4(BFB·별 속성)는 11/05 04:00 KST 종료, 결산은 11/12 04:00까지임(`data/guild_defense.json`). BFB 상태 기계·지원 5종·선택 효과 4종·부분 점수식·내 정보 편성 탐색을 구현했음. `guild_boss=off`가 기본이고 길방 진입에서만 켬.
- `data/guild_sim.json`은 11/08 `810dc37`에서 `enemy_leader=none` 기본으로 다시 계산했음(off/max·육성 ×1·×1.5·×2·×2.5·×3, **234,000판**). off 최고 단계 ×1.5 5→6, ×2 7→8, ×2.5·×3 유지, max 쪽은 오르내림이 섞임. 그 뒤 `any_turn_source=table` 은 길방 결과 해시가 같아 재생성하지 않았음. 기존 필드·최고 클리어 단계는 off, `bySets`·`summaryBySets`는 max를 보존함. 공개 표준 육성만 썼으며 실제 플레이 대조는 남았음.
- 빠른 계산 표본 2,323건×40판을 11/08 `810dc37`에서 다시 생성하고 재보정했음. 전체 일치 **0.920**(이전 0.916, `data/quick.json calib.acc`).
- 저장소: 11/08 `21e1c8e`까지 커밋·푸시 완료(`git status -sb` ahead 0). 주소: https://QooReche.github.io/starsavior-party-navigator/
- 최근 검증: 11/08 `run_tests.py --rebuild --e2e` **86 통과/0 실패**(e2e 포함). 계정 자료·8899 포트·골든/해시 `--write`는 쓰지 않았음.

## 남은 일

1. 게임 PC에서 표 26291832와 DLL 26314877의 추출 시점·내용 동일성을 확인하기로 함. 11/01 클라 표 수정본 보존·동기화 여부도 함께 확인하기로 함.
2. 최신 내 정보와 영상으로 실제 플레이를 대조하기로 함: 선택 효과·질투의 시선·정실 어필·보호막·웨이브 게이지·스칼렛 행동 수·하이 스코어 버프 해제·부케 딜 분배. 이번 작업은 계정 자료를 쓰지 않았음.
3. 추가 규칙 후보는 [누락 점검](docs/client_recheck_extra.md)의 목록에서 이어가기로 함. 피해·명중(`AOE_DIV`, `BREAK_DEC`, `ELEM_HIT`, DoT, 카운터 지속 피해), 대상·시계, 노바 정책·브레이크 경계가 남았음. 모델 가정 자체와 실제 클라 규칙을 구분하기로 함.
4. 광역 협공의 저장 대상 대응, 서든데스 사망·부활, 신규 연쇄 피해 유형, 반응 중복 이력 단위, 아군 공격 선제 방어, BFB 능력치 배율 순서·전체 피해식을 추가 확인하기로 함. 기대값의 확률 상태 상관·동률 대상·아군 HP/브레이크 미모델 근사도 남았음.
5. 길방 추천에 보유 브레이크 스킬 입력을 연결하고, 편성·지원·단계를 직접 고르는 시뮬 UI와 수동 비교 범위를 정하기로 함.
6. 길방 미확정 규칙을 확인하기로 함: 허무와 10단계 면역 동시 선택, 하루 도전·점수 합산·1~6단계 요일, 보스 속도/공격 AddStat·지원 배치 순서·시즌 길드 버프, 졸개전 패배 부분 점수 근사.
7. 11/05 종료 뒤 다음 시즌 자료·보스 명세·search 설정을 갱신하고 빌더 검증을 확인하기로 함(`docs/PORTING.md`, `tools/build_guild_bfb.py`).
8. 저사양 PC의 길방 탐색 시간·예상 시간·탐색 축소·부분 결과·진단 표시를 검토하기로 함. 협공 제외 수·불리한 구원자·예선/본선 부분 결과의 합성 e2e는 완료했고 실제 플레이 탐색 성능은 남았음.
9. 게임 PC에서 37-3 비관·37-2 에핀델 편성·37-36 샤를 첫 행동·38-36 생존/행동 수·트리쉬 피해·세레스/루그 동작을 같은 시점 자료로 재대조하기로 함. 달 회랑 360층 낙인·기본기 대상 분산, 성간 회랑 카르멘 리더 corr-c 샘플도 남았음.
10. 브레이크 자동 발동·쿨 단위·발동자 게이지·영역 지속·재발동·행성 정화 조건, 보스 브레이크 지속·미측정 궁극기 강인도·불리 상성 강인도·`enemy_hit_buff_cmp`를 영상으로 확인하기로 함.
11. 서부 탈환대 세레스 스킬·기본 베라 자동 지정 근사, 기믹 추정 대처·무적 웨이브 실제 배치·길방 밖 협공/추가타·ReactiveBarrier 활성 표를 추가 확인하기로 함. 기본/개화 매핑과 적 SkillOrderList·빈 공격 처리는 완료했음.
12. 게임 PC의 10/29 아카라이브 원고 «게임 파일에 새 수치가 없어» 문단과 myinfo.ps1 배포 필요 여부를 확인하기로 함. 작전 보스 근사 보정·rankAll/quickRank 캐시·legacy 정리는 낮은 우선순위로 남겼음.
13. 장비 탐사 외 «N턴 이내 승리» 미션 확장은 낮은 우선순위: 큐브 팰리스 일부(65·60턴)·이벤트(65·60 / 50·45)·일일(50·45)도 같은 미션이 표에 있으므로 필요하면 `STAR_TURNS` 확장함. 65턴(2별 추정)은 표시 안 함.
14. 점검(11/08)에서 보류한 것(비공개 표 경로 통일·건너뜀 표시·생성물 규칙 도장은 11/09 완료, 절 «2026-11-09»): 단계 그룹 버프(`BUFF_STEP_TEMPLET`)의 엔진 미구현(영향 작음).
15. 중복 코드 점검 결과(11/08, Opus, 읽기 전용, 상세 `AI\temp\partynavigator\work\audit_1108\dup\duplication_audit.md`): 공통화 우선순위 ① (11/09 완료) 비공개 표 경로 통일 ② (11/09 완료) 구원자 키↔게임 id 매핑 7곳 ③ (11/09 일부 완료: jsonc·rows 만, 아래 절) B2 적 반응 강화/약화 판정(11/09 완료, 위 절) ④ (11/09 완료) `tests/simkit.py`. 이미 어긋난 곳: 길방 `score()` Python(짝수 반올림·가설 B)↔JS(사사오입·B 무시), 길방·코스모 `_put`, 적 반응 조건(mc.py:2697-2709)만 강화/약화를 따로 세어 표식이 «강화 있음»으로 잡힘, 분위수 정의 3가지, `savior_reco.json` 수동 복사. 아직 코드는 안 고침. 독립 리뷰(`bd3ffda..9f8b101`) 지적 7건 중 6건은 이 커밋에서 반영(HANDOFF 절 정정, 제어문자 시험에 탭 금지, 깨진 참조·낡은 문서 표시, enemy_leader 등급 `code`·출처 접두). 반영 안 한 것: enemy_leader 근거가 로컬 전투 호스트 경로뿐이라 서버 동작은 미확인(AGENTS 의 «근거 불완전하면 옛 동작» 과 긴장, note 에 미확인 명시), `guild_sim.json` 234,000판은 이 변경 뒤 재계산 안 함.
## 환경·주의

- 회사 PC는 공개 저장소와 `E:\AI_mk2\starsavior-static-data`를 함께 pull하기로 함. 추출 도구 작업이면 `starsavior-packet-ref`도 확인.
- 회사 PC codex 실행은 `-Sandbox danger-full-access`, e2e는 `E:\AI_mk2\venv-pw\Scripts\python -X utf8 tests\e2e\test_page.py` 기준임. 옛 PC 경로·시험 개수는 당시 기록임.
- 게임 PC의 내 정보·영상 판독·work 메모·임시물은 `AI\temp\partynavigator\` 기준이며 `INDEX.md`로 찾기로 함. 계정 자료 사본은 비공개 static-data/samples에만 둠.
- 공개 저장소·Pages에 계정 수치·내 정보 원본·클라 원본 표를 추가하지 않기로 함. 공개 화면은 가공한 일반 자료만 사용함. 계정 기준 시뮬 수치는 11/08 정리에서 일부 걷어내 비공개 폴더(`AI\temp\partynavigator\private_results\`·`work\`) 안내로 바꿨고, 남은 옛 수치는 당시 기록임(git 기록에는 남음).
- Git 신원은 `QooReche <87477643+QooReche@users.noreply.github.com>`만 사용하기로 함.
- codex 는 구현·조사·리뷰 모두 맡길 수 있음(쓰기 제한 없음). 커밋·푸시는 시험 전부 확인 뒤. 시험은 `python -X utf8 -I tools/run_tests.py`(`--rebuild`·`--e2e <python>`). 골든을 통과시키려고 `--write` 하지 않기로 함.
- 엔진 변경 뒤에는 `tools/build_simpack.py` → 계수 재맞춤(`tools/gen_quick_calib.py --per-content 400 --opboss`, `tools/calibrate_quick.py --write`) → HTML 생성 → 관련 시험·검토 순으로 진행하기로 함.
- 패치 때는 `docs/PORTING.md`대로 구원자 목록·색인과 --static 빌더를 갱신하고, 최신 번들 채택(`dupes.json used`)을 확인하기로 함. static-data 경로는 --static → STARSAVIOR_STATIC 순임.
- 영상은 촬영 시점 내 정보·실제 장착 브레이크·왕관의 리더·부제/직업/키를 맞춰 판독하기로 함. 촬영은 사용자, 판독은 AI 몫임. 10/22 밸런스 변경 스테이지·토벌의 패치 전 영상은 대조 근거로 쓰지 않기로 함.
- PowerShell 한글 읽기는 `Get-Content -Encoding utf8`, git dubious ownership은 설정 변경 없이 `git -c safe.directory=<저장소 경로> ...` 조회로 처리하기로 함.
- 문체는 존칭 없이 「했음·하기로 함」으로, 짧은 문장·줄바꿈·소제목으로 구분하기로 함.

## ▶ 2026-11-09 (Claude) — 적 반응 강화/약화 판정 정렬·건너뜀 표시·생성물 규칙 도장 (푸시 완료)

- 적 반응 조건 4개(`target_neg_buff`·`target_pos_buff`·`self_pos_buff`·`self_neg_buff`)를 `e.harmful` 직접 셈에서 `n_harmful()`/`n_good()` 로 바꿈. 스위치 `foe_react_buff_count`(새 기본 `client`, legacy=`harmful`). 근거: 클라 조건이 «IsBuff && IsPositive / IsBuff && !IsPositive» 개수(NKM.Templets:40116-40137, 42099-42270)를 쓰고 `buff_count_source` 와 같은 기준임. 현재 `data/foe_react.json` 에 이 4개 조건을 쓰는 줄이 없어 **결과는 안 바뀜**(잠재 결함 정리). 클라가 세는 효과 목록의 세부(표시 효과 등)는 미확인. 시험 `foe_react_test.TestBuffPresence`(기본을 harmful 로 돌리면 실패 확인), `rules_test` 키 목록.
- 건너뜀 표시: 환경 때문에 못 돌린 검사(node 없음·`COSMO_TABLES`/비공개 표 없음)를 `tools/runtime.skip_note()` 로 표식(`[건너뜀]`)을 남기고, `run_tests.py` 가 표식과 unittest `skipped=N` 을 모아 끝에 «건너뜀 N건» 으로 보임. `--strict` 이면 실패로 침. 이 PC 는 node 있음, `COSMO_TABLES` 없어 1건 건너뜀.
- 생성물 규칙 도장: `tools/rules_stamp.py`·`tools/gen_rules_stamp.json`(지문 = formula·opts·mc 기본값 해시). `guild_sim`·`quick` 이 만들어진 규칙과 지금 규칙이 다르면 `tests/gen_rules_stamp_test.py` 가 실패. 다시 만들거나(빌더 `build_guild_sim.py`·`calibrate_quick.py --write` 가 도장을 새로 찍음) `rules_stamp.py --ack <이름> --reason "…"` 로 이유를 적어 인정함. 지금 도장은 11/09 기준선(두 파일 다시 만들지 않음, 이유는 json 에 기록). 전체 89/0 + e2e 통과(`--rebuild`).
- 안 한 것: 규칙을 조건별로 나눠 «어느 키가 이 생성물에 영향 주는지» 판정하지 않음(키 하나만 바꿔도 낡았다고 뜨므로 인정 절차를 거침).

## ▶ 2026-11-09 (Claude) — 비공개 표 경로 통일 (푸시 전)

- `tools/runtime.static_path_or_none(root)` 추가: `STARSAVIOR_STATIC` → `<저장소>/../static-data`(`tables/` 가 있어야 인정) → None. 시험 6개(`myinfo_stats`·`myinfo_combat`·`savior_mapping`·`guild_bfb`·`client_gaps_1104`·`eff_remaining`)가 이 규칙을 씀. `C:\build\static-data` 고정 경로·다른 PC 경로(`E:\AI_mk2\...`)·`CERES_AUDIT_STATIC` 별칭은 없앰. `cosmo_raid_test` 의 `COSMO_TABLES`(추출본 형식이 달라) 는 그대로.
- 이 PC 에서 그동안 건너뛰던 `myinfo_stats` 비공개 정답 대조·`myinfo_combat` 재현·`savior_mapping` 원본 대조가 실제로 돌았고 **모두 통과**(새로 깨진 시험 없음). 사본은 `AI\partynavigator\static-data`(0e16db1, 11/02)를 씀.
- 시험 `cleanup_test.test_static_path_or_none`(함수를 깨면 실패 확인). 전체 `run_tests.py` 86/0(e2e 안 돌림).
- 남음: node 없을 때 print 후 통과하는 시험 3개(항목 14), 건너뜀 방식 통일(guild_bfb 는 print 유지). 다음 공통화 후보는 항목 15의 ③ 나머지(BUFF 이름표·STRING_COMMON·`names_of`).

## ▶ 2026-11-09 (Claude) — 구원자 키↔게임 id 매핑 공통화 (푸시 전)

- `battlesim/starsavior/savior_ids.py` 추가: `keys_by_id(index, db=None, only_db=False)`(id→키), `ids_by_key(index, db=None)`(키→id, DB 키는 setdefault), `uid_resolver(index)`(키 우선, 이름은 유일할 때만). 규칙은 «색인 key → 시뮬 DB id → 유일한 이름».
- 쓰는 곳으로 바꿈: `build_auto_skill`(3곳)·`savior_mapping_test`·`build_myinfo_combat`·`ingame_check`·`build_growth.roster_ids`·`build_party_html` uid. 지금 시뮬 DB 에는 색인에 없는 구원자가 0명이라 `auto_skill.json` 은 바뀌지 않음(아모라는 색인에 있음). 앞으로 색인에 없는 구원자가 생기면 `build_auto_skill` 은 키를 채우지 않고 `build_myinfo_combat` 은 채움(`only_db` 때문에 규칙은 그대로 두었음, 통일 여부 미정).
- 확인: `--static` 으로 build_auto_skill·build_growth·build_myinfo_combat·build_party_html 재실행 -> `git diff data index.html` 0. 시험 `savior_ids_test`(DB 변형 제외를 지우면 실패 확인). `sim/manifest.json` 에 새 파일이 목록에 들어감(브라우저 시뮬 묶음). 전체 87/0(e2e 제외).

## ▶ 2026-11-09 (Claude) — 빌더 표 읽기 `tools/tables.py` (푸시 전)

- `tools/tables.py`: `jsonc(path)`(문자열 안 `//` 보존, BOM 허용 — build_auto_skill 구현을 옮김), `rows(path)`(Data 벗김). 정규식으로 `//` 를 지우던 `build_foe_spawn.jsonc`·`build_foe_summon` 인라인·`build_cosmo_raid.strip_jsonc` 를 이것으로 교체(`errors='replace'` 도 없어짐 — 표에 잘못된 바이트가 있으면 이제 오류). 다른 빌더가 `build_auto_skill`/`build_foe_spawn` 에서 가져다 쓰던 `jsonc` 이름은 재노출로 유지.
- 확인: `--static` 으로 build_auto_skill·foe_spawn·foe_summon·foe_auto·foe_react·buff_force·guild_bfb·battle_end 재실행 -> `git diff data` 0. 코스모는 `C:\build
ew-extract`·시즌 1022·빌드 26429597 로 임시 출력과 `data/cosmo_raid.json` 키별 비교 같음. 시험 `tables_test`(문자열 안 `//` 처리 되돌리면 실패 확인), 전체 88/0(e2e 제외).
- 안 한 것: `m_BuffStrID → 이름` 7곳·`STRING_COMMON` 10곳·`names_of` 중복·`SKILL_TEMPLET_{1,2}` 읽는 20여 줄(`json.loads(...)['Data']` 를 `rows` 로 바꾸는 일). 효과가 작고 diff 확인 비용이 커서 보류.

## ▶ 2026-11-09 (Claude) — 시험 공용 도우미 `tests/simkit.py` (푸시 전)

- `FIXED`·`unit`(p3 판)·`battle`·`give` 를 `tests/simkit.py` 로 옮기고 `p3_test`·`p5_test` 는 거기서 가져옴(p5 의 `unit` 은 element·sa 를 항상 넣는 얇은 래퍼로 남김). 기존 `from p3_test import ...`(29곳)·`from p5_test import ...`(11곳)은 그대로 동작함. 새 시험은 simkit 에서 가져오기로 함.
- 사고와 정정: 앞 절을 쓸 때 heredoc 안 파이썬 문자열의 백슬래시+b 가 백스페이스 문자가 되어 HANDOFF 의 코스모 표 경로가 깨진 채 푸시됐음(`md_control_chars_test` 가 잡음). 이번 커밋에서 복원함. 교훈: HANDOFF 수정은 Edit 도구로 하기.
- 남음: 지역 `battle()` 7개(용도별이라 그대로), 항목 15의 ③ 나머지.

## ▶ 2026-11-09 (Claude) — 길방 `score()` 반올림 정렬 (푸시 완료)

- `guild_defense.score()` 가 Python `round`(짝수 반올림)와 가설 B 분기를 쓰던 것을 `score_at(g, pct, 1.0)`(정수 사사오입)으로 바꿔 `guild_view.js score()` 와 같게 함. 현재 가설은 A 하나라 값은 바뀌지 않음. 시험: `guild_defense_test` 에 합산 10.5 -> 11 단정 추가(옛 코드로 되돌리면 실패 확인). 전체 88/0(e2e 제외).
- 항목 15의 B3 중 이 부분만 완료. `node_json`/node 없을 때 통과로 보이는 문제, 칸 순서 변환 공통화는 남음.

## ▶ 2026-11-08 밤 (Claude) — 문서 유지보수 정리 (코드 변경 없음, 푸시 완료)

- 내 정보 기반 결과 JSON 8개(`docs/ally_damage·taunt_guard·boss_action·received_damage·boss_recheck·myinfo_combat·nova_gauge·web_leads_results.json`)를 비공개 `AI\temp\partynavigator\private_results\` 로 옮기고 `.gitignore` 에 `docs/*_results.json`(예외 `toughness_results.json`) 추가. 과거 커밋 기록에는 남아 있음(기록 재작성은 하지 않음).
- HANDOFF·HISTORY·audit 문서의 계정 기준 시뮬 수치 일부를 «수치는 비공개 폴더» 로 바꿈. 제어문자로 깨진 경로(`AI<탭>emp`, `work<VT>ideo` 등)를 복원하고 시험 `tests/md_control_chars_test.py` 추가(옛 HANDOFF 로 되돌리면 실패 확인). HANDOFF BOM 제거, 11/01 절은 HISTORY 로 옮김, `docs/README.md` 색인 추가.

## ▶ 2026-11-08 밤 (Claude) — 틱 제외 조건·카넬리아 기믹 클라 대조 (코드 변경 없음, 푸시 완료)

- 전체 턴 시계 틱 제외 조건(NKM:3973-3989, 빌드 26314877; Sonnet 조사, 직접 재확인은 안 함): `OBF_19516`=TurnInfinite(무한 지속 제외), `OBF_22670`·`OBF_12025`=지속 피해·회복 템플릿(별도 경로 `OBF_32280` 차감, 표에서 GlobalTurnCounting 과 같이 쓰면 템플릿 에러). 엔진 `_tick_any_turn` 과 같음. 다른 점: `OBF_31000`(NKM:3843, 4435) = 같은 BuffStepGroup 에서 기존 단계가 더 높아 신규가 못 이긴 기존 버프 목록(NKM:4296-4305), 그 버프는 이번 틱에서 제외. 엔진엔 없음 -> BuffStepGroup 충돌 버프만 1틱 빨리 줄 수 있음, 영향 미측정. `OBF_9765` 카운터 의미 미확인.
- 카넬리아 패시브(표 26291832 `SE_TEMPLET_SKILL_2` 930081501~508, 조건 5039~5042)는 효과값·판정 순서가 엔진과 같음. 차이: 「약화 효과 상태인 적에게 피격」을 클라는 때린 아군 한 명으로(NKM:10019), 엔진은 살아 있는 아군 전원 중 하나(`mc.py` 적 약화효과 보유). 고치는 스위치를 임시로 넣어 보았으나 Step 3 레벨 6·12판에서 396/396 모두 참(카넬리아가 아군 전원에 약화를 걸어 두어 차이가 안 남) -> 지켜 줄 시험을 못 만들어 되돌림. 끝없는 저주 최대 중첩(표에 값 없음)·운명 부정 +200% 합산 방식(`mc.py` 단순 합산)은 미확인. 표 26429597 은 이 PC 에서 못 찾음.
- 공허 계열 샘플 재대조(11/08, 수치는 비공개 `AI\temp\partynavigator\work\void_recheck_1108\`): 시계 수정(any_turn_source table/text) 전후 결과가 37-3·36-36·37-36r·op3836 a/b/c 에서는 모든 항목 동일(해당 버프가 발동하지 않은 것으로 추정, 보스 스킬 줄 미확인), 13-10(op1310)만 달라지고 새 기본이 실제 승리·TURN 쪽에 더 가까움. 승리한 37-3·36-36 은 여전히 시뮬이 비관적, op3836 은 시뮬이 실제보다 일찍 끝남(원인 미확인). 100판 1시드·11/02판 내 정보(`build_mismatch`)라 오차 큼.
- **적 리더 속도 +10 제거(`enemy_leader=none` 새 기본, legacy=boss; 푸시 완료)**: 클라 근거 추적(Opus, 11/08) 결과 일반 전투에서 웨이브 몬스터는 리더 플래그 false 로 생성(NKM:505-506,1801,1816; 소환물 NKM:5665,1887,1902), 스폰 표(`UnitSpawnData`/`UnitSpawnScript`, NKM.Templets:37372-37385,37445-37451)에 적 리더 필드 없음(`LeaderUnitIdList` 는 아군 리더에 따른 조건 스폰 키), 리더 효과 9000001 은 리더 플래그만 보고 보스 플래그와 별개(NKM:8296, NKM.Templets:36775-36778, 효과 표 BATTLE_EFFECT_TEMPLET.json:1281-1282). 엔진의 «적 리더 = 첫 보스» 는 설계 가정이었음. 서버 실전투 코드는 클라에 없어 미확인(NKM:14404 는 개발용 치트 호스트였음 — 앞 절의 «서버가 리더 여부를 줌» 추정은 이걸로 정정). 시험: `p3_test.test_enemy_leader_default_none`(기본 값을 boss 로 되돌리면 실패 확인), `test_leader_speed`·해시 시험(`mc_cache_test`·`heal_burst_test` `_KEEP`)·`buff_clock_test` 는 `enemy_leader: boss` 로 고정. 재생성: 빠른 계산 표본·보정(전체 일치 0.920, 이전 0.916), 길방 시뮬표(234,000판), `index.html`. 길방 off 최고 단계 ×1.5 5→6, ×2 7→8, ×2.5·×3 유지(max 쪽은 ×1.5 2→3 로 오히려 내려가는 등 혼재). 전체 `run_tests.py --rebuild --e2e` 86/0. 남은 일: 영상으로 보스 행동 턴 재대조(38-36 등), 서버 쪽 확정은 불가.
- `enemy_leader=none` 뒤 영상 샘플 11개 재대조(11/08, 100판 1시드·11/02판 내 정보, 수치는 비공개 `AI\temp\partynavigator\work\leader_1108\after\`): 규칙 변경 자체의 영향은 작음(클리어율 +0.01~0.09p, 준÷받은 +0.02~0.09). 승리한 판(37-3·op3933·eq3119·eq3019)은 여전히 시뮬이 비관적이고, 어긋난 방향은 딜 부족(아군 행동당 준 피해가 낮음 — 37-3) 또는 받은 피해 과다(op3933 턴당) 쪽, 보스 행동 과다는 샘플 전반에서 뚜렷하지 않음. eq3019 는 클리어율은 맞으나 행동 수가 1.3배 많고 비율이 낮음. 원인은 미확인(지표 방향만 읽음). 다음 후보: 개별 타격 피해(능력치·크리티컬·방어)의 소폭 과소 가능성(11/05 절), 전투 길이·딜 분배를 영상 타격 단위로 대조.
- `OBF_31000`·코스모 3보스 표 대조(11/08, 푸시 완료; 비공개 `AI\temp\partynavigator\work\obf31000_1108\`·`cosmo_tables_1108\`): ① `OBF_31000` 은 같은 BuffStepGroup 에서 기존 단계가 더 높아 신규가 거부될 때 기존 버프를 담아 다음 차감 한 번을 건너뜀(NKM:4289-4305, 4435, 3978, 3988). 그러나 표에서 GlobalTurnCounting=true 21개 중 단계 그룹 소속은 0개라 전체 턴 시계에는 구현 불필요. 단 이 차감 함수는 자기 턴 종료(NKM:2020)·웨이브 전환(NKM:823)에서도 불려 일반 단계 버프(BI_ATTACK_INCREASE/AMPLIFICATION 등 12그룹 25개)도 1회 차감이 빠지고, 엔진엔 단계 그룹 처리가 전혀 없음 — 영향 미확인(새 후보). ② 코스모 시즌 1022 표(빌드 26429597, 이 PC `C:\build\new-extract`)의 벨그라스·티리아·카넬리아 스킬 줄·계수·쿨·조건 ID·소환 그룹을 엔진 줄과 대조해 불일치 없음(티리아 기믹 5종 구현 확인, Step 3 1판 실행). 미확인: 카넬리아 운명 부정 실제 동작(1판에서 미발동), 인형 행동 게이지 규칙 실행 검증. 앞 절의 «26429597 표를 못 찾음» 은 `C:\build\static-data` 만 본 결과였음.
- 단계 그룹 버프 조사(11/08, Opus, 비공개 `AI\temp\partynavigator\work\stepgroup_1108\`): 표 `CLIENT_BUFF_STEP_TEMPLET.json:5-78` 12그룹 25개(11그룹은 «X 증가»±30%와 «상급 X 증가/감소»±50% 2단계, 회복 감소는 1·2단계 모두 -50%, 10001그룹 «잔재된 괴리»는 이름이 같은 3단계). 엔진은 이름으로만 저장해(`mc.py:3925,3947`) 다른 단계 이름이 동시에 유지되고 능력치가 합산됨(`mc.py:519-522`, 강화 개수 `584`). 실제 사례는 «상급» 이름이 플레이어 세이라(1014) 특수기 〈상급 공격력 증가〉 하나뿐(몬스터·길방·코스모 0건): 〈공격력 증가〉도 가진 아군에게 걸리면 엔진 80% vs 클라 50%. 측정(standard 육성 300판, FLOOR 200·250): 해당 시전은 아군 시전의 5~9%, 행동당 피해 -0.4~1.2%·클리어율 -1.0/-3.7%p로 신뢰구간 안 -> **구현 보류(영향 작음)**. 구현한다면: `buff_step.json`(이름→그룹·단계) 생성, `add_effect`(mc.py:3925) 앞에서 같은 그룹 처리(새 단계 ≥ 기존이면 기존 삭제, 기존이 높고 새 지속이 짧으면 거부, 아니면 기존 지속만 늘리고 다음 차감 1회 건너뜀), 스위치 `buff_step_group`(새 기본 client). 미확인: 10001그룹 단계별 동작.
- 38-36(op3836) 시뮬이 실제보다 일찍 끝나는 원인 조사(11/08, Opus, 기록 비공개 `AI\temp\partynavigator\work\op3836_1108\`): 아군 피해 과대가 아니라 보스 행동이 잦음(보스 기술 순서는 실제와 같고 타이밍만 2번째 턴부터 전역 턴 2~3칸 일찍 행동). 후보는 `enemy_leader=boss`(적 보스 리더 속도 +10; 표 `BATTLE_EFFECT_TEMPLET` 9000001·`CLIENT_CONST_TEMPLET` 129-131, 몬스터 생성 코드는 리더=false(NKM:504-506, 1887-1902)이나 그 경로는 로컬 개발 전투용(NKC:550731), 작전은 리더 여부를 서버에서 받음(NKM:14404) -> 확정 불가). 규칙 근거는 영상이 아니라 설계 가정(`default.json` source 비어 있음, grade assumed). 전 샘플 민감도(100판 1시드): 끄면 준÷받은·클리어율이 5/6 샘플에서 실제에 가깝지만(eq3219만 반대) 차이 작고 보스 턴 판독 샘플은 3개뿐이라 우열 불분명 -> 기본값은 바꾸지 않음(`enemy_leader=boss` 유지). (→ 이후 none, 위 «적 리더 속도 +10 제거» 항목) 남은 일: 서버가 작전 보스를 리더로 표시하는지(영상에 적 리더 표시가 있는지) 확인.
- 아카라이브 코게 공략 모음(https://arca.live/b/starsavior/170255501, 보스별 글 링크, 대조용·근거 아님): 카넬리아 15단 편성은 아모라(리더)·왈츠 아세라·루나·웨핀델(또는 로로카), 12단 달세라 택틱. 코게는 같은 보스가 3보스 조합으로 로테이션된다는 사용자 말(11/08)이라 다음 시즌 준비에 씀. 엔진 규칙은 추론이 아니라 PC 클라 디컴파일로 정한다는 사용자 지시(11/08).

## ▶ 2026-11-08 밤 (Claude) — 전체 턴 시계를 표 기준으로 (푸시 완료)

- 원인 확정(클라 코드·표): 13-10 보스 공허감응자의 `2회·3회 피격 카운팅` 버프·`규제`(표 `BI_PILGRIM_ALIEN_RED_3~5`)는 `GlobalTurnCounting=true`. 클라는 이런 버프를 모든 행동 끝에 전원 차감하고 걸린 행동도 차감(`NKM` 3973-3983 틱, 13546 호출(턴 유닛 제외 전원, 턴 유닛은 별도), 4571 예외 `OBF_18128`). 엔진은 시계를 설명문 문구로만 판정해 9개 이름(2회 피격 카운팅 금지용/용·3회 피격 카운팅용·규제·기본기/특수기 타겟팅용 디버프·아군 턴 카운팅·영양 과잉·제행무상 체크용)을 보스 자기 턴 기준으로 처리했음 -> 연쇄 판당 5.5회로 부풀고 규제 50% 감소가 보스 턴까지 이어졌음. 보스 줄 해석(조건)은 표와 같았음(`SKILL_CONDITION_TEMPLET` 55143~46·55515·17·18).
- 구현(커밋 `d088076`): 규칙 `any_turn_source`(table 새 기본/text 옛 동작), `data/buff_global_turn.json`(15개 이름, `tools/build_buff_force.py --static <표>` 가 생성, 표에서 일부만 true 인 3개 제외), `mc.global_turn_buff`, `_is_any_turn` 이 표도 확인. simpack 목록에 추가. 시험 `tests/buff_clock_test.py` 5개(판정·옛 동작·자기 턴 버프 유지·표⊇문구·13-10 보스 피격당 연쇄 비율, 판정을 끄면 3개 실패 확인), `rules_test` 키 목록. 전체 85/0(e2e 제외).
- 13-10 내정보 기준 재측정(11/08, 수치는 비공개 `AI\temp\partynavigator\work\bigboss_1108\clock_test.py` 출력): 연쇄 발동이 판당 절반 이하로 줄고 턴당 받은 피해·전체 행동 수·준 피해·클리어율이 모두 실제(승리, TURN 43) 쪽으로 이동. 남은 차이(준 피해 과소·행동 수)는 다른 요인. 공개 저장소에는 표준 육성 시험(`tests/buff_clock_test.py`: 보스 피격당 연쇄 비율이 옛 동작의 70% 미만)만 둠.
- 정정: 11/08 서브에이전트가 «카운팅·금제 버프는 전부 GlobalTurnCounting=true» 라고 했으나 표에서 `금제·계/갑`(RED_1·2)은 false, 카운팅·규제(RED_3~5)만 true.
- 마무리(11/08): 빠른 계산 표본 재생성(`gen_quick_calib --runs 40 --per-content 400 --opboss`)·`calibrate_quick --write` -> `data/quick.json`·`index.html` 은 재생성 결과가 이전과 같았음(전체 일치 0.916 그대로, 계수 변화 없음). 길방(레벨 0·6·10)·코스모·플래시 포인트 전투는 새 규칙/옛 규칙 결과 해시가 같아 `guild_sim.json` 은 재생성하지 않음(자료에 9개 이름 없음). 새 시험 7개 포함 전체 통과(e2e 포함).
- 독립 리뷰(Opus, `d088076~1..d088076`): 클라 틱 의미(행동마다 전원 1회 차감, 턴 유닛 별도 경로, 걸린 행동도 차감)와 엔진 일치 확인. 반영 4건: ① `(해제불가)` 꼬리표 이름이 표 경로에서 안 맞던 결함 -> 집합도 같은 규칙으로 정규화 ② 시계 차감 자체를 지키는 시험 부족 -> `add_effect` 부여 경로로 «아군 행동 뒤 사라짐(table)/남음(text)» 시험 추가(틱을 끄면 실패 확인) ③ 해시 시험 `_KEEP` 에 `any_turn_source: text` 추가 ④ 규칙 설명·HANDOFF 에 계정 기준 시뮬 수치가 들어간 것을 걷어냄(비공개 폴더 안내만 남김; 이미 푸시된 11/08 HANDOFF 절에 일부 수치가 있었음 — git 기록에는 남음). 못 읽은 것: 클라 틱의 제외 조건 3개(`OBF_19516`·`OBF_22670`·`OBF_12025`), 표에서 일부만 true 인 `강인도 피해 무효` 를 쓰는 적.
- 남은 일: 같은 방식으로 공허 계열 다른 영상(37-3·36-36·38-36) 재대조(전체 턴 시계 수정 뒤 값으로), 13-10 실제 영상에서 보스 «전체 연쇄» 장면 수 세기. (틱 제외 조건 3개는 11/08 확인 완료, 위 절)

## ▶ 2026-11-08 밤 (Claude) — 큰 보스전 «받는 피해 과대» 클라 대조·재점화 수치 대조 (푸시 완료)

- 재점화 수치: 표 `BATTLE_EFFECT_OPERATION_HANDICAP_70001~5` -> 버프 `BI_OPERATION_HANDICAP_01~05`(전투 시작 아군 전체 100%, 턴 무제한·해제 불가)가 `NST_RATE_DAMAGE_UP`·`NST_RATE_DAMAGE_REDUCE` 각각 3·7·12·18·25%. 엔진 `REKINDLE` 과 값이 같음. 차이: 클라는 능력치로 걸어 다른 증감과 같은 항에서 합산(감소는 합 상한 50%), 엔진은 전투력 패널티 배율로 곱함. 합산 규칙에 따라 1단계는 무시 수준이나 5단계는 영향이 있을 수 있음(영향 크기는 미측정, 구현은 그대로).
- 13-10 받는 피해 클라 대조(Sonnet 조사, 근거 `AI\temp\partynavigator\work\bigboss_1108\FINDINGS.md`): 단일 대상 선택(규칙 1001)·방어율(def/(def+3000))·증감 합산 상한·연쇄 피해식·회복식·결과 화면 받은 피해 집계 기준·AOE 분배 계수는 클라와 같음. 게이지 정수화는 영향 무시 수준. 상시 «받는 피해 감소» 소스 누락은 못 찾았으나 전수 증명은 아님. 카르멘 회복 258k 가 시뮬 대비 크게 많은 이유는 미확인(식은 같음).
- 이 판 보스(공허감응자)는 «맞으면 적 전체에 연쇄 피해(공격력 x40%)»를 되갚음(2회 피격 카운팅·금제 상태 피격 조건). 연쇄가 시뮬 받은 피해의 상당 부분을 차지하고 연쇄 발동 횟수를 줄이면 실제에 가까워짐 -> 아래 «전체 턴 시계» 절에서 원인 확정(클라 코드·표 근거). 계정 기준 측정 수치는 비공개 `AI\temp\partynavigator\work\bigboss_1108\`.

## ▶ 2026-11-08 밤 (Claude) — 작전(어려움) 재점화 적용·영상 13-10 대조 (푸시 완료)

- 영상 11/08 11:22(작전 어려움 SECTOR 13-10 Lv2214, 사이트 1안 4인): **승리 TURN 43**, 사이트 예측 클리어 0%. 준/받은 피해 페이 439,328/137,461·에밀리 55,813/134,408·에핀델 196,411/139,239·카르멘 76,188/251,155(회복 258,714). 승리 시점 페이만 생존으로 추정. 편성 화면·브레이크 스킬은 영상에 없음. 판독 `AI\temp\partynavigator\work\video_1108\OP1310_1108.md`, 샘플 `ingame_check.py` `op1310`(재점화 1)·`op1310r0`.
- 사용자 지적: 이 판에 재점화 1단계가 붙어 있었음. 엔진·화면이 재점화를 `op`(작전 일반)에만 적용해 작전(어려움) `oph` 에서는 옵션이 무시되고 있었음 -> `oph` 도 적용(`api.py` 두 곳, 화면 `rkOf`), 시험 `web_test.test_rekindle` 에 oph 추가(되돌리면 실패 확인). 어려움에도 일반과 같이 재점화가 적용된다는 것은 사용자가 확인했고(11/08), 클라 근거도 확인함(빌드 26314877 디컴파일·표 26291832): 표 `OPERATION_BUFF_TEMPLET` 5단계 = 활성 일수 1·3·5·9·14일(`ActiveDate`), 버프 레벨은 계정 전체 값 하나(`NKC` 675970·675994: 콘텐츠·난이도와 무관한 한 카운터)이고 스테이지 정보의 표시기는 스테이지 종류가 `OPERATION` 일 때 켜짐(`NKC` 95534). 작전 일반 탭(`BattleTabID` 11xxx, `BattleTabType` NORMAL)과 어려움 탭(12xxx, HARD)이 모두 `BattleContentsId` 1 = `OPERATION` 이라 같은 버프를 받음(`BATTLE_TAB_TEMPLET`, `BATTLE_CONTENTS_TEMPLET`). 전투에 실제로 효과를 거는 부분은 클라 코드에 없고 서버가 보내는 것으로 보여 서버 쪽은 미확인. 단계별 수치(±3·7·12·18·25%)의 표 근거는 `BattleEffectStrId` `BATTLE_EFFECT_OPERATION_HANDICAP_70001~70005` 로 이어지나 값 대조는 안 함.
- 측정(내정보 기준, 수치는 비공개 `AI\temp\partynavigator\work\op1310_sim\`): 재점화 1단계(±3%)는 클리어율·준 피해를 거의 바꾸지 않아 원인이 아님. 실제 대비 시뮬은 받는 피해가 턴당 더 크고 더 일찍 전멸(큰 보스전 시뮬 비관과 같은 방향). 준 피해 분배는 비슷. 한 판이라 가정은 바꾸지 않음.

## ▶ 2026-11-08 밤 (Claude) — 코스모 보스별 난이도·브레이크 스킬·카드 양식 (푸시 완료)

- 사용자 요청: ① 난이도를 보스마다 따로 골라 각자 최고 점수를 노림 ② 기존 추천 양식(카드·전열/후열·리더·브레이크 스킬) 표시. 구현: 자동이면 삼중의 모든 팀을 난이도 0~최대에서 짧게(probeRuns) 돌려 팀마다 최고 점수 난이도를 정하고(`levelOf`), (삼중 재정렬은 결과에 영향이 없어 뺐음). 마지막 확인에서 팀마다 «장착 안 함 + 보유·시뮬 지원 브레이크 스킬(`cx.breaks`)» 각각을 돌려 점수가 큰 것을 고름(`finalRankBrk`). 결과 팀에 `level`·`brk`·`brkLv`. 화면은 `csTeam`(기존 `card`·브레이크 줄 재사용), 대표 난이도 6에서 추린 후보만 쓰는 한계는 그대로.
- 한계: 1·2단계는 브레이크 스킬 없이 돌림(후보 선정에 미반영, 마지막에서만 비교). 브레이크 스킬은 보스끼리 같은 스킬을 써도 됨(사용자 확인 11/08: 구원자만 겹치면 안 됨). 난이도 비교 구간·브레이크 비교 구간 실제 시간 미측정.
- 시험: JS `auto_level_picks_best_level`(보스별 정점 6·12·15, 브레이크 선택, levelMax 없음 거부), e2e `test_cosmo_auto_level`(카드 4장·전열2·후열2·왕관1·브레이크 줄), 전체 85/0.
- 독립 리뷰(Opus, 커밋 범위 `7005713..cbc671c`): 화면 호출 경로의 결함은 없음. 반영 3건: 동점 규칙(난이도 낮은 쪽·장착 안 함)이 시험에 안 지켜져 동점 시험 추가(두 규칙을 뒤집으면 실패 확인), 효과 없던 삼중 재정렬 삭제, 시작 전 시간 안내가 브레이크 비교 판 수를 빼서 `plan(S, rows, nBrk)` 로 반영. 남김: e2e 가 브레이크 스킬 선택 자체는 검사 안 함(`.bbar` 는 장착 안 함이어도 그려짐), 팀별 최댓값 선택이라 점수가 실제보다 높게 보일 수 있음(문구는 «참고용»).
- 영상 3판(11/08, 8단계, 벨그라스·티리아·카넬리아) 판독 `AI\temp\partynavigator\work\video_1108\VIDEOS_1108.md`: 세 판 모두 처치 못 함(턴 제한), 총점 4,944,625·9,778,875·8,315,000(합 23,038,500, 게임 화면 일치). 시뮬 추천 합계 22.63M과 약 1.8% 차이. 점수식 역산: (기본 553,000 + 최대 피해 2.5M×깎은 비율 + 생존 구원자×50,000)×3.5 (+달성 점수 피해 300,000은 배율 없음)로 벨그라스·카넬리아는 깎은 비율 28%·61%와 맞고 티리아는 역산 78% vs 판독 76%(2%p 불일치, 원인 미확인). 남은 턴 점수는 패배라 0. 편성 판독: 벨그라스 앞 카르멘(리더)·프레이 / 뒤 세레스·페이, 티리아 앞 루나(리더)·카넬리아 / 뒤 프로페서M·스마일, 카넬리아는 아모라·아세라·로자리아·린(칸 미확인). 브레이크 스킬 이름은 영상에서 못 읽음.

## ▶ 2026-11-08 밤 (Claude) — 난이도 자동 사고 수정 (푸시 완료)

- 사고: 푸시한 난이도 자동이 실제 화면에서 약 35분 계산 뒤 «Cannot read properties of undefined (reading 'level')» 로 실패했음. 원인: 화면이 `search`에 `levelMax` 를 안 넘겨 난이도 비교 목록이 비었음(JS 시험은 `levelMax` 를 직접 넣어 통과, 화면 호출 경로는 시험이 없었음). 수정: 화면이 `levelMax` 전달, 자동인데 `levelMax` 가 없으면 계산 전에 오류(`search` 첫머리).
- 시험: JS `auto_level_picks_best_level` 에 `levelMax` 없음 거부 추가, e2e `test_cosmo_auto_level`(기본 선택 자동 -> 끝까지 완주 -> «점수가 가장 높은 난이도» 표시). 수정을 되돌리면 e2e 가 실패하는 것 확인. 전체 85/0.
- 교훈: 화면이 부르는 경로를 거치는 시험 없이 «시험 통과»만으로 푸시를 권하지 말 것. 긴 계산 기능은 끝 단계 오류가 늦게 드러나므로 필요한 입력은 시작 전에 검사.

## ▶ 2026-11-08 밤 (Claude) — 코스모 난이도 «자동 (최고 점수)» (푸시 완료)

- 난이도 선택 -1 = 자동(기본). 1·2단계는 대표 난이도 `search.auto.screenLevel`(6)에서 하고, 뽑은 삼중을 난이도 0~최대에서 `probeRuns`(10)판씩 비교해 합이 가장 큰 난이도를 고른 뒤 그 난이도로 2단계·3단계를 다시 함(`cosmo_search.js search`). 결과에 `level`(고른 값)·`reqLevel`(-1)·`probe`. 비교·마무리 단계는 ETA 단계 밖(`stage:null`, 화면은 안내를 끔).
- 한계: 대표 난이도에서 추린 후보만 비교하므로 고난이도 전용 팀은 놓칠 수 있음. `screenLevel` 6은 임의값, 비교 구간 실제 소요 시간 미측정. 시험 `auto_level_picks_best_level`(비교 방향을 뒤집으면 실패 확인), 전체 85/0(e2e 포함).

## ▶ 2026-11-08 (Claude) — 코스모 게이트 시즌 화면 (푸시 완료)

- 사용자 요청: 코스모도 길방처럼 시즌 단위로. 목록 이름 «코스모 게이트(시즌 22)»(`content.title`, 설정 키인 `name`은 그대로), 섹터·검색·스테이지 선택과 보스별 개별 추천을 숨기고 3보스 합산 편성 찾기 패널만 보임(`content.raid`, 템플릿 `raidUi`). 시즌 날짜는 서버 자료라 표시 못 함.
- 옛 스테이지 화면은 시험 전용 `window.__legacyRaid` 로 남김(`open_page(raid_ui=False)` 기본). `test_cosmo_search` 는 시즌 화면에서 선택 칸·추천 목록이 비는지 단정 추가(단정을 일부러 깨뜨려 보지는 않음).
- 시험: `run_tests.py --rebuild --e2e` 85 통과/0 실패. 다음 시즌 갱신 때 `title` 의 시즌 번호는 `season.id % 1000`.

## ▶ 2026-11-06 밤 (Claude) — 코스모 전수 탐색 안전 가속 3종 (푸시 완료)

- 사용자 결정: 풀 축소 «빠른 모드»는 만들지 않음(최적 조합을 놓치면 안 됨), 정확도 손실 0 이어야 함, 효과가 PC마다 다르니 고정값 금지·자동 적응.
- ① 엔진 캐시(`battlesim/api.py`·`mc.py`): 구원자 정의 LRU(256)·시즌 인카운터 LRU(64)·정의 객체에 붙인 의미 해석/지원 보고 메모·줄 종류 색인(`Battle.kind_lines`). 스위치 `mc.ENGINE_CACHE`. 시험 `tests/engine_cache_test.py`(캐시 끔/켬 84전투+run_auto 결과 동일, LRU 상한, 틀린 키·낡은 색인 주입 시 실패 확인).
- ② 작업자 수 자동(`cosmo_search.js workerCount`, 설정 `data/cosmo_raid.json search.workers` = 빌더 SEARCH 상수): min(논리 코어×0.75, 메모리×0.5÷250MB, 24), 모바일 2. 길방 워커 수는 건드리지 않음.
- ③ 1단계 순차 반감(`pickPass`·`mergeSummary`·`passCount`): 전 조합 1판 → 보스별 상위 10%(경계 동점 포함, 구원자별 상위 대안 포함, 최소 3×keep 팀)만 1판 더 → 2판 평균으로 기존 2단계. ETA 단계 4개로 확장(옛 저장 속도는 버림).
- 측정·예상 시간·남은 일은 `docs/cosmo_raid.md` 「전수 탐색 가속」 절. 미검증: 실제 브라우저(Pyodide) 워커 메모리, 24코어 이상에서의 실측 확장, 사용자 PC 시간.
- 클라 코드 추적 결론(근거는 코스모 절): 최종 점수·3보스 합산·순위·도전 횟수·시즌 날짜는 서버. 클라 HUD 식은 `Base+MaxDamage×(깎은비율 1/10000 내림)`을 정수 내림. 고정 레벨 200·공명 10과 스타링크 가산 없음은 시뮬이 이미 반영(`fixed200`), 서버 동작은 미확인. 시즌 버프(BCT_*)의 전투 적용 코드는 클라에서 못 찾음.
- 11/08 확인: `run_tests.py --rebuild --e2e C:\build\venv-pw\Scripts\python.exe` **85 통과/0 실패**(e2e 포함, 11/06에 실패하던 `mergeSummary` 시험도 통과). e2e `test_cosmo_search`는 작업자 수 자동·ETA 4단계 저장을 검사하도록 고쳐져 있음. 40명 전수 실측과 ETA 오차는 아직 안 쟀음.
- 다음: 사용자가 추천 편성으로 직접 뛰고 영상(편성 화면·결과 화면의 점수·남은 턴·생존 수·레벨)으로 점수식 대조. 한국 커뮤니티 조사는 사용자가 보류함(Chrome 확장 연결 안 됨).

## ▶ 2026-11-06 (Claude) — 코스모 게이트 2단계: 3보스 겹침 금지 편성 찾기+최소 화면 (푸시 완료)

- `cosmo_search.js`(보스별 작업·점수 순위·겹침 금지 삼중 분기한정·화면 조각·전체 흐름 `search`), `battlesim/web.py`(`options.cosmo_raid` 분기·`cosmo_summary` 요약), 화면 패널(`party_template.html`, 코스모 콘텐츠에서만), `build_party_html.py` 가 `cosmoRaid` 주입. 설정은 `data/cosmo_raid.json` 의 `search`(빌더 `SEARCH`). 상세·판 수 근거는 `docs/cosmo_raid.md` 2단계 절.
- 시험 `tests/cosmo_search_test.js`·`tests/cosmo_web_test.py`(겹침 판정을 끄거나 web 분기를 되돌리면 실패하는 것 확인). 미검증: 브라우저 화면·Pyodide 실제 시간·실제 내 정보 결과.
- 남은 일: 실제 브라우저 확인(e2e 추가 후보), 시간이 길면 `search` 설정 조정, 점수식 추정 항목.
- 11/06 보강: 후보 풀 전수(`maxPool null`), 시작 전 앞열·딜러 인원 검사, 조합이 `keep` 근처면 `keep` 확대, 내 정보·제외 목록 변경 시 검색 취소+«낡은 결과» 표시, 순위 기본 «상위 점수»(재도전 제한 없음), `rerank.runs` 10→20(상위 점수 표준편차 실측 0.8~1.6%→0.4~1.2%, 전체 +2%), HUD 점수 매번 내림(NKM:16914)을 문서·주석에 확인 표기.
- 남은 시간: 판 수를 시작 전에 계산, 속도는 이동 구간+단계 가중치, 워밍업 10초·저장 속도 블렌드 30초, 판 배분을 작업 큐(`runPhase chunk`)로 바꿈. 40명 전수(43만 판, 8 워커 682초) 기록을 재생하면 최대 오차 148→63%, 평균 26→25%. 중간 오차 약 25%는 실제 처리 속도가 도중에 500→1000 판/초로 바뀐 데서 오며 식으로 못 막음. 큐 배분의 꼬리 단축 효과는 40명 규모로 재측정하지 않음(16명 4 워커에서는 차이 없음).

## ▶ 2026-11-06 (Claude) — 코스모 게이트 시즌 1022 시뮬 1단계: 데이터+엔진+점수 (푸시 완료)

- `tools/build_cosmo_raid.py`(새 표 폴더를 인자로 받음, static-data 는 건드리지 않음) → `data/cosmo_raid.json`(빌드 26429597). 엔진 `battlesim/starsavior/cosmo_raid.py`, 스위치 `mc.cosmo_raid_boss`(기본 off, 새 키는 rules_test 목록에 추가), 점수 `cosmo_score`/`cosmo_raid.js` `cosmoScore`.
- api: `encounter.cosmo_raid = {boss, step, level}` → 결과 최상위 `cosmo_raid`(판별 깎은 비율·남은 턴·생존 수·점수·경로 횟수). 기존 해시 시험 영향 없음.
- 점수 합산식·난이도 배율·시즌 버프 대상·벨그라스 일부 규칙은 «추정/근사». 목록은 `docs/cosmo_raid.md`. 갱신 절차 `docs/PORTING.md` 4-2.
- 남은 일: (2단계는 위 절에서 완료) 영상 대조, 근사 항목 확인, 티리아·카넬리아 스킬 줄과 새 표의 대조.

## ▶ 2026-11-05 오후 (게임 PC, Claude) — 장비 탐사 «60턴 이내 승리» 반영 (푸시 완료)

- 근거: 표 `BATTLE_TEMPLET_NORMAL`의 `BattleMissionData`에 `BMT_LIMIT_TURN` 65·60이 탐사(EXPLORE) 60개 스테이지에 걸려 있음(큐브·이벤트·일일은 각각 65/60·50/45). 클라 `NKC` 미션 판정은 `턴 > 한도`면 실패(NKC:590576-590598), 영상 샘플 결과 화면 «TURN 52 (52/60)»과 같은 단위 → 엔진 `turn_limit_unit=actions`(전역 행동 수, `ttk_actions`)와 일치. 클라 카운터가 전역 턴과 같은지는 코드로 끝까지 추적하지 않았고 영상 샘플로만 확인.
- 구현: `api.simulate`에 옵션 `star_turns`(N) → 결과 `star_turn{limit,p}`(outcome 밖, 해시 시험 영향 없음). `web.run_auto`가 `t60`으로 전달. 화면은 `STAR_TURNS={equip:60}`일 때 옵션을 넣고, 순위(`scrCmp`·표시 순서·브레이크 비교)를 «60턴 내 비율 → 클리어율 → 진행도 → 턴» 순으로 가르며 칩에 «60턴 내 N%»를 붙임. 시험 `tests/star_turn_test.py`(한도 1·무한·중앙값·outcome 불변, 비교 방향을 뒤집으면 실패하는 것 확인).
- 옵션 «장비 탐사 목표»(60턴 안에 클리어 / 클리어만, 기본 60턴, 장비 탐사에서만 표시·`pn.goal` 저장): 60턴 기준이면 카드에 «3별(소탕) 조건 60턴 이내 승리 가능성 기준, 턴 수는 시뮬 추정» 안내를 붙이고, «클리어만»이면 옵션을 시뮬에 안 넘겨 기존 순위로 돌아감. e2e `test_equip_goal_option` 추가.
- 시험: `run_tests.py --rebuild --e2e C:\build\venv-pw\Scripts\python.exe` **81 통과(e2e 36개 포함)/0 실패**. 중간에 `breakMetric`에 `t60: null`이 항상 붙어 JS 단위 시험이 깨졌고 값이 있을 때만 붙도록 고침.
- 미검증: 순위 변화가 사용자 체감과 맞는지. (실제 장비 탐사 영상 1판으로 60턴 판정 대조는 완료 — 아래 항목)
- 아카라이브 글 원고(11/05, 간략판): `AI\partynavigator\release\arca_post\arca_post_20261105.txt`(저장소 밖, 제목·올리는 방법·본문 HTML). 상단 공지 배너는 아직 «11/03 업데이트» 문구(필요하면 11/05로 갱신 후 재배포).
- 같은 날 영상 한 판 기록: 작전 39-33 승리 TURN 71, 작전 40-3 패배(달성도 81%). 시뮬과의 비교 수치는 내 정보 기준이라 비공개 `AI\temp\partynavigator\work\video_1105\COMPARE.md`([docs/ingame_samples.md](docs/ingame_samples.md) 맨 아래).
- 장비 탐사 60턴 검증(영상 1판): 뒤틀린 감정 XIX 승리, 결과 TURN 35 = 미션 «60턴 이내 승리 (35/60)»의 카운터 → 단위 가정 확인됨. 사이트 예측과 방향 일치. 시뮬은 받는 피해가 실제보다 큰 경향(39-33은 힐데 쓰러짐 우세). 이 판 영상 판독(보스 행동 5회: T1 재충전·T7 포착·T14 포착·T26 재충전·T34 침입자 청소, 보스 브레이크 T10·T21)과 시뮬 보스 행동 턴은 T21 근처 1회 외에 일치 → **행동 빈도·타이밍은 원인이 아님**, 받은 피해 차이의 큰 부분은 시뮬 전투가 실제(35턴)보다 길어서 보스 행동이 더 늘어난 것. 11/05 영상 6판 종합(`docs/ingame_samples.md` 맨 아래): 승패 방향·진행도·피해 분배는 대체로 맞고, 시뮬이 «받는 피해가 크다»는 인상은 전투 길이(시뮬이 길게 끎)와 우연 변동으로 설명됨 — 근본 오류 증거 없음. 클라 확인: 웬디고 스킬엔 고유 AutoSkillId 없음(규칙 1001), 대상 분포 이론값과 일치. 전투 길이: 클리어한 판만 보면 실제 TURN(71·35·61)이 시뮬 중앙값보다 짧고 시뮬 분포 아래쪽임. 클라 확인: 추가 턴도 전역 턴을 올림(`SelectTurnUnit`이 호출마다 +1, NKM:13452-13470; `if(!OBF_34810()) 웨이브턴++`의 조건은 추가 턴이 아니라 웨이브 전환) → 시뮬의 턴 세기는 맞음. `WeakAdjustData`(장비 탐사 표)는 클라 코드에 계산 흔적 없음(권장 속성 표시용 추정). 장비 탐사 두 판은 실제 아군이 행동당 주는 피해가 시뮬보다 크고(작전 39-33은 일치) 보스 브레이크 지속이 길어 보스 행동이 적었음 — 다음 후보: 장비 탐사 보스의 브레이크 지속·브레이크 대상 피해 증가·강인도 계산. 점검 추가(11/05, 정정 포함): 보스 브레이크 처리(다음 자기 턴에 회복·정상 행동)는 영상(T10 브레이크→T14 «포착»)과 모순 없음. **앞서 «행동당 준 피해가 z≈3 높다»고 한 것은 독립 증거가 아니었음**: 클리어한 판은 총 피해가 보스 체력과 거의 같아 «행동당 피해»는 «전투가 짧다»의 환언이고, 실제 TURN이 시뮬 분포 아래쪽인 것과 같은 말. 장비 탐사 뒤틀린 감정 영상 판독(아군 행동 65행: 협공 14·추가 스킬 6·프로페서M 트리거 약 10)과 시뮬을 턴당으로 환산하면 보조 행동 빈도는 일치 → 보조 타격 부족은 원인 아님. 개별 타격 숫자는 시뮬 분포 안이지만 영상 값이 시뮬 중앙값보다 높은 쪽(17개 표본, 판독이 «행동 내 최댓값»이라 편향 가능) — 전투 길이 차이와 같은 크기라 능력치·크리티컬·방어 계산의 소폭 과소 가능성이 남음. 클라 확인: 상성 유리 보너스 = 0.05 + NST_RATE_DAMAGE_UP_ADJUST(NKM:17543-17557), 이 가산을 주는 효과는 표에서 보스 스킬(아키온·페르세스)뿐이라 사용자 구원자엔 해당 없음. 미지원 효과(세레스 TurnUnitNegativeBuff = 별 속성 피해 +1%×5)도 영향 없음. 크리티컬 점검: 시뮬 타격별 크리티컬 비율은 이미 높고 영상 표기(라벨 누락 많음)와 비교해 과소 아님 → 크리티컬은 원인 아님. 남은 후보: 보스 방어력(장비 탐사 스테이지 보정)·화면 능력치 직접 대조(영상 능력치 화면 필요). 전투 길이 차이는 전체 영향이 작아 우선순위 낮음. 회복: 게임 «회복» 통계는 초과 회복 포함 원래 회복량(NKM:5472-5483)이라 시뮬 `heal`(채워진 양)과 정의가 다름 → `heal_raw` 추가(결과 최상위, per_unit 밖) 후 차이가 좁혀짐, 세레스 회복 부족은 원인 미확인(수치는 비공개 폴더)(혹한의 습격 XIX 판 `eq3119`도 같은 경향). 남은 것: 단일기 «포착»의 대상 선택(실제 T7은 후열 프로페서M이 맞음, 규칙 1001은 단일의 80%를 전열로), 판 하나로 결론 못 냄. 샘플 `eq3019`. 상세 `docs/ingame_samples.md` 맨 아래.
- `tools/ingame_check.py`에 샘플 `op3933`(39-33)·`op403`(40-3, 준/받은 피해 미판독이라 비율 무의미)를 추가해 내 정보로 대조함(수치는 비공개 COMPARE.md). 결론(재점화 없음으로 대조, 11/05 정정): 시뮬은 두 판 모두 비관적 — 39-33은 승리했는데 시뮬 클리어는 낮고 힐데 쓰러짐(시뮬 우세 vs 실제 0)이 실제보다 많음. 보스 행동 턴은 시뮬(T1·9·13·19·26·30)과 실제(T1·9·약 13·약 19·26·31)가 거의 같아 보스 빈도는 원인이 아님(처음 «실제 11회»는 T1 누락 집계 — 정정), 40-3은 패배는 맞지만 진행도(시뮬 약 0.56 vs 실제 0.81)가 낮음. 준 피해 분배는 비슷. 원인 후보: 아군(특히 힐데) 받는 피해·회복·보호막 모델(시뮬 힐데 받은 피해 비중이 실제보다 낮은데도 먼저 쓰러짐), 40-3은 에밀리 생존. 처음에 «경계 Ⅳ·Ⅴ»를 재점화 단계로 단정해 «재점화 불일치가 원인»이라 적었으나 틀렸고(영상에 재점화 없음) 철회함. 편성 화면 «경계» 표시의 의미는 미확인.

## ▶ 2026-11-05 오전 (게임 PC, Claude) — 길방 보스 속도·공격력 NV 합산 `guild_boss_nv_sum=client` (푸시 완료)

- 9·10단계 낙관의 원인을 클라 코드로 좁혔음: 클라는 보스 AddStat 속도(-25%)·공격력(-17.5%)을 버프의 NV 비율(별의 도전 속도 +10/20/30%, 정실 어필 속도 -20%·공격력 -70%, 독점 선언 공격력 +30%)과 **한 합**에 더해 최종 floor(기본×(1+합))로 계산함(NKM:18200-18280, 합산 경로 2874-2904·3855-3866·2472-2483). 엔진은 AddStat 을 먼저 곱해 굳히고 버프를 또 곱했음(bake). 9~12단계 보스 속도 client ×1.05(230→241) vs bake ×0.975(223.6)로 bake 가 보스를 약 7.7% 느리게 봄(7단계 .85/.825, 8단계 .95/.90). 어필 중 보스 공격은 반대로 bake 가 약 16% 세게 봄. 생명력은 단계 배율이 곱이라 같음.
- `guild_boss_nv_sum`(기본 client, legacy bake) 추가. client 는 보스 기본 능력치(굳히기 전)를 쓰고 AddStat 비율을 고정 효과(`보스 능력치 비율(AddStat)`)로 넣어 합산하며, 보스 속도는 평탄 가산까지 포함해 내림. 시험 `guild_bfb_test.py test_boss_nv_sum`(두 방식 값 차이를 직접 확인), `rules_test` 키 목록.
- 영상 편성으로 비교(내 정보, 60판): client 가 영상의 승패(8단계 승, 9·10단계 패)와 방향이 맞고 bake 는 9·10단계를 훨씬 낙관했음. 수치는 비공개 `AI\temp\partynavigator\work\client_match_1105\nvsum\INDEX.md`. **원인 확정에 가까움**(11/04 «toughness_elem 으로 더 낙관적이 됨»의 실제 원인 후보 해소). 단 영상의 보스 첫 행동 «3번째»는 시뮬 첫 행동(전역 턴 5)과 여전히 달라 속도 정수화·시작 상태 쪽이 남았음.
- 길방 시뮬 표를 이 기본으로 재생성(234,000판, 1,020초). off 최고 단계: ×1.5 4→5, ×2.5 8 유지, ×3 9 유지(클리어율 .72→.60). max 쪽은 ×1.5 1→2, ×2 4→6, ×2.5 6→7, ×3 6→7(어필 중 보스 공격이 클라에서 약해지는 효과). 전체 시험 80/0(e2e 포함).
- 독립 리뷰(Sonnet, 커밋 범위 `a3e6619..22d69e7`): 지적 1건 반영 — 합산용 고정 효과가 보스의 강화 효과 개수(`n_good`)를 +1 하던 회귀를 `cat='marker'` 로 고치고 시험에 `n_good` 동일 단정 추가(marker 를 빼면 실패함을 확인). bake 모드는 구 커밋과 난수열까지 동일, 단계 0 값 불변, 공격력 이중 적용 없음 확인. 남은 사소한 차이: client 는 공격력을 내림하지 않음(약 0.003%). 평탄 속도 가산이 클라 식의 같은 floor 안인지는 원본 확인 못 함. 수정 뒤 길방 표를 다시 만들었으나 파일이 동일했음.
- e2e: 이 PC에 Playwright(1.64.1)를 `C:\build\venv-pw` 에 새로 설치(브라우저 chromium-1248 은 전날 설치돼 있었음). `test_request_diagnostics` 가 새 Chromium 에서 `/README.md` 이동을 «다운로드»로 처리해 실패해 `/index.html` 로 바꿨음. 실행: `python -X utf8 -I tools/run_tests.py --rebuild --e2e C:\build\venv-pw\Scripts\python.exe`.
- 남은 클라 차이 점검(2026-11-05, 읽기 전용 조사, 기록 `AI\temp\partynavigator\work\client_match_1105\*_spec.md`): 서든데스 사망자 재적용(부활 경로에 호출 없음 — 추정, 기본 유지), 수호자 동률(클라: 전열 우선→낮은 칸)·틱당 1회 고정, 반응 이력 불발 삭제(사실상 일치), 아군 공격 선제 방어(일치·적 PD 부여원 없음), 카운터와 지속 피해(일치), 노바 정책(일치, 클라 자동 호출 없음), 격파 피해 감소 -15%p 지속(클라는 자기 턴 끝까지, 엔진은 턴 시작에 해제 — 영향 작음), 보스 2종은 격파 시 게이지 0 버프가 없음(엔진은 몬스터 전부 0), `ally_break_gauge=skip` 은 클라 코드 근거 없음(사용자 관찰만), 속도 정수화·틱 절삭 미반영(`gauge_int` 후보).

## ▶ 2026-11-05 (게임 PC, Claude) — 남은 클라 맞추기 3개 기본 전환 (푸시 완료 28293f8·a3e6619)

- `dot_formula=client`, `react_hist_unit=unit`, `immune_force_apply=client`를 기본으로 전환했음(legacy=옛 값). 근거 빌드 26314877, 이 PC의 `C:\build\decompile-20261102\clean`(줄 번호가 기록과 일치)과 `C:\build\static-data`(비공개 저장소 clone, 표 153개).
- DoT 수호 분담: 대상 제외 같은 편 `DAMAGE_SHARE` 최대 1명, 분담 몫을 방어 전 기본 피해에서 떼고 수호자 몫은 수호자 방어·증감·상성·별도 난수로 계산, 보호막 무시, 무적·스킬 무효 대상은 분담 없음, 몫 1 이상일 때만(NKM:1286-1308,7925-7928,8153-8171,17315-17319,17368-17409). 관통 저항(`PENETRATE_DEF_RESIST`)은 표에 부여원 0건, 상성 가산(`DAMAGE_UP_ADJUST`)은 장비 패시브뿐이라 구현하지 않았음. 수호자 동률 규칙(`OBF_9827`)·수호자 사망 처리는 미확인.
- 반응 이력: 클라는 `HashSet<유닛ID>` 하나(NKM:8374,15534)이고 엔진 트리거 스킬은 `build_foe_react.py`가 클라 `NST_REACT`에 연결하므로 `unit`이 맞음. 코드 변경 없음. 불발 삭제 범위(엔진은 ctx 없으면 항상 삭제, 클라는 ReactAttack 실패 때만)는 차이가 남았음.
- 면역: 통과 이름 `data/buff_immune_pass.json`(`tools/build_buff_force.py`가 생성, IsPositive|DeleteBuff|ForceApplyEffect, 같은 이름 행이 모두 통과인 811개). 혼재 13개·표에 없는 효과·SE 행 강제 중 연소/기절(보스 HYPER)/착란 체크용은 거부로 둠(엔진이 SE 행 ID를 모름). 물폭탄은 전투·웨이브 시작 부여(`unique_enemy`+`ignore_resist`)를 통과로 봄 — 이름 목록만으로는 `test_fix3_waterbomb_move`가 깨져 보강했음.
- 재생성: simpack → update → 빠른 계산 표본(400/콘텐츠, opboss) → 보정 → 길방 시뮬(234,000판, 1,244초) → html. 빠른 계산 일치율 0.916 그대로, 길방 최고 단계·요약은 이전과 같고 진행도만 소수 넷째 자리에서 움직였음.
- 시험: 최종 `run_tests.py --rebuild` **79 통과/0 실패**, `git diff --check` 통과. 새 시험 `DotGuardTest`·면역 통과 목록 시험을 일부러 깨뜨려 실패하는 것을 확인했음. e2e는 이 PC에 Playwright가 없어 미실행.
- 독립 리뷰(커밋 범위 `7b9be61..28293f8`, Sonnet): legacy·수호자 없음 경로가 변경 전과 난수열까지 같음을 구 커밋 대조로 확인. 지적 1건 반영 — 자기 지속 피해(시전자=대상)에서 수호자가 피해를 받던 오류(클라는 시전자가 수호자와 같은 편이면 수호자 몫 0, NKM:17376-17379)를 고치고 시험 3개 추가(자기 지속 피해·스킬 무효·몫 1 미만·통과 목록과 표 일치). 수정을 되돌리면 새 시험이 실패함을 확인. 이 수정은 자기 지속 피해+수호자 조합에만 닿아 빠른 계산·길방 표는 재생성하지 않았음. 기각한 지적 없음. 남은 차이: 클라는 수호자를 틱당 한 번, 엔진은 지속 피해 인스턴스마다 정함(수호자가 틱 도중 죽을 때만 다름, 영향 낮음).
- 남은 일(위 목록에 반영): 서든데스 사망자, 길방 보스 속도 합산, 9·10단계 낙관 원인(ATK 배율 적용 위치·보스 대상 선택), 영상 대조.

## ▶ 2026-11-04 (게임 PC, Claude) — 길방 선택 효과 끔·점수식·순위 기준, 엔진 후보 스위치 7개 (푸시 완료)

- 길방에는 선택 효과가 클라에 연결돼 있지 않음(표 `DIFFICULTY_ADD_POINT_*`는 BossRush/Cube만 참조, 길방 HUD·점수 표시는 단계 값만 씀). 서버 처리는 미확인. 편성 찾기·시뮬 기본값·최고 조합에서 선택 효과를 껐음(옛 off/max 프리셋 데이터는 호환용으로 남김). 11/03 추천 점수가 높았던 이유 중 하나임.
- 점수식에 처치 졸개 수 k와 클라식 보스 비율 내림(1/10000)을 반영했음. 시뮬 결과에 k가 없어 진행도에서 근사하고, `guild_sim.json` 평균 표 기반 «시뮬 추정» 패널은 졸개 2기 처치로 계산함(정확히 하려면 `build_guild_sim.py`에 평균 k 저장 후 재생성). 단계 보너스 곱셈 뒤 반올림은 서버 계산이라 미확인.
- 편성 찾기 순위를 상위 20% 점수 → 상한 도달률 → 평균으로 바꿈. 시험 78→79 통과(e2e는 이 PC에 Playwright가 없어 미실행, `tests/e2e/test_page.py` 3곳 수정만 함).
- 클라(26314877) 근거 후보 스위치 7개를 MC 엔진에 추가했음. 모두 기본은 현재 동작이며 영상 대조 전임: `preemptive_defense=client_main`, `break_point_hits=window`, `toughness_elem=client`, `dot_formula=client`, `react_hist_unit=unit`, `immune_force_apply=client`, `break_auto_blocked_cc=on`. 시험 `tests/client_gaps_1104_test.py`. window·CC 차단은 엔진에 다타수 모델이 없어 실전 영향이 거의 없음. DoT 수호 분담은 미구현.
- 같은 날 사용자 판단(시뮬은 클라 기준이 우선, 영상 대조는 확인용)으로 4개를 기본 전환했음(legacy=옛 값): `preemptive_defense=client_main`, `toughness_elem=client`, `break_point_hits=window`, `break_auto_blocked_cc=on`. `immune_force_apply`는 `buff_force.json`이 IsBuff 행만 담아 IsBuff=false 강제 적용 효과 90행을 거꾸로 거부할 수 있어 보류(데이터 보강 필요). `dot_formula`(수호 분담·관통 저항 미구현)·`react_hist_unit`(부작용 클라 일치 미확인)도 옛 값 유지. (→ 위 "스위치 7개 … 기본은 현재 동작" 문장은 이 4개에 한해 바뀜)
- 전환 후 재생성: 화력 지표 변경 구원자 0명, 빠른 계산 일치율 91.8→91.6%, 길방 off 최고 단계 ×1.5/×2/×2.5/×3 = 2→4 / 6→7 / 7→8 / 8→9, max ×3은 6단계 클리어율 81.7→100%. 원인은 `toughness_elem` 하나(불리 상성 공격의 강인도 몫 0 → 적이 아군을 덜 깨뜨림)이고 `preemptive_defense`는 힐데 편성에서만 발동(7단계 .85→.73). **11/03 영상(8단계 3승·9단계 0승 2패)과는 더 낙관적이 됨** — 클라 식 해석이 틀렸거나 9·10단계 원인이 다른 곳(ATK 배율 적용 위치·보스 대상 선택)일 가능성. 되돌리려면 `toughness_elem=db`. 측정 `AI\temp\partynavigator\work\switch_1104\switch_hits.json`. 시험 79/0, e2e 미실행.
- 남은 클라 맞추기: `dot_formula` 수호 분담·관통 저항 구현 후 전환, `react_hist_unit` 확인, `immune_force_apply` 데이터 보강, 길방 보스 속도 합산 추적, 서든데스 사망자, 회복 턴 건너뛰기 코드 근거 재탐색. (→ 11/05 앞의 3개 기본 전환 완료)
- (11/04 밤 중간 저장) Opus 조사·구현 에이전트 2개가 진행 중이었음: toughness 클라 식 재검증+9단계 원인(`AI\temp\partynavigator\work\decomp_1104\toughness_recheck.md`), dot 분담·반응 이력·면역 데이터 구현. 작업 트리에 미커밋 변경이 있으면 시험 통과 확인 후 커밋.
- 보류: 길방 보스 속도 합산(`기본×(1+합)` 추정, 합산 경로 미추적 — 클라 식이면 7~12단계 보스가 약 8% 빠름), 서든데스 사망자 처리(근거 부족). 보호막(22.5%)·흡수 방식은 클라와 일치 확인 → 9·10단계 낙관의 원인은 미확정(남은 후보: ATK 배율 적용 위치, 보스 대상 선택). 시작 게이지 근거는 표·코드에 없음.
- 표 26291832 vs 설치본 26314877: 10/29 이후 바뀐 번들 5개(11/01 00:30)의 CLIENT_* 표 14개는 `tables/`와 MD5 일치, 나머지는 연출 스크립트라 재추출 불필요. 기록 `AI\temp\partynavigator\work\decomp_1104\check5_tables_vs_dll.md`.
- 그 밖에 확인한 클라 규칙(미반영): 길방 하루 도전권 기본 2+구매 1, 1~6스테이지 1개·EX 2개, EX만 화·목·토, 점수는 확정 포인트 합(최고만 쓰는지 미확인). 졸개전 패배 점수는 죽인 졸개만 1250씩.

## ▶ 2026-11-03 밤 (집 PC) — 길방 EX 영상 7판 기록 (푸시 완료)

- 길방 시즌4 EX 실제 플레이 영상 7판(6·8·9·10단계) 판독을 [docs/ingame_samples.md](docs/ingame_samples.md) 맨 아래 절에 기록했음. 코드·데이터는 바꾸지 않았음.
- 점수식 확인: 결과 포인트 = (2,500 + 1,250×졸개 2기 + 25,000×보스 깎은 비율) × (1+단계 보너스). 6단계 상한 48,000·8단계 54,000이 실제 승리 판과 정확히 일치. 단계는 12단계까지 있고(보너스 +120%까지) 상한은 9단계 57,000·10단계 60,000·11단계 63,000·12단계 66,000.
- 같은 편성(카르멘 리더·스칼렛·아모라·선샤인 캣 스마일, 격돌의 돌풍)으로 8단계 3승, 9단계 0승 2패, 10단계 0승 1패. 시뮬 기본값은 9·10단계를 훨씬 낙관적으로 봄. 원인은 정실 어필 보호막(최대 체력 22.5%) 구간의 아군 피해 과대와 보스 첫 행동 시점(영상 3번째, 시뮬 5번째)으로 좁혔으나 단일 보정으로 8·9·10단계를 동시에 맞추지 못했음. 보정 후보(보스 시작 게이지 +40%p·속도 ×1.15)는 과적합이라 엔진에 넣지 않았음(근거 불충분, 기본값은 옛 동작).
- 편성 찾기는 단계별 점수 상한이 있어 6단계 동점이 많음. 순위 기준을 평균이 아니라 상위 점수·상한 도달률로 보는 방향이 맞다는 사용자 의견(확정 전 재도전 가능)을 받았으나 화면·검색 코드에는 반영 전.
- 계정 기반 시뮬 수치(편성 찾기 결과·보정 격자)는 공개 저장소에 넣지 않고 비공개 `AI\temp\partynavigator\work\guild_ex_1103\`에 있음(INDEX.md).
- 남은 일: 보호막 구간·보스 시작 게이지를 클라 코드 근거로 확인해 규칙 스위치로 넣기, 9단계 이상 영상 추가(편성 다양화), 편성 찾기 순위를 상위 점수 기준으로 바꿀지 결정, 10단계 이상 면역(약화만 막는 구현) 영상 검증.

## ▶ 2026-11-03 (회사 PC, codex 병렬) — 현재 빌드 디컴파일본으로 규칙 재확인·대형 재생성 (푸시 완료)

### A — 협공·강제 적용·효과 순서

- 이전 5묶음(협공 후보 순서·적 스킬/빈 공격·기본/개화 매핑·기믹 재조사·e2e 서버 격리)과 A/B/C/D 재확인 4묶음을 함께 통합 검증했음. e2e는 전용 임의 포트·Windows 배타 바인딩을 쓰며 8899를 쓰지 않음.
- 13개 규칙을 현재 빌드로 대조했음. 일반 협공은 전원 확률 판정 후 성공자 중 균등 1명인 `random_success`로 바꿨음. COOP_CAP·팀 노바·강제 적용·강화 불가·스킬 순서·빈 공격·DC_ATTACK·중첩 시점·버프 개수·능력치 경로를 재확인했음. [대응표](docs/client_recheck_rea.md).

### B — 노바·쿨·반격

- 적 종료 효과 뒤 쿨 차감, 피격 시점 반격 확률, 노바 상한 12를 반영했음. 서든데스 상세 미확인은 남겼음. 독립 리뷰에서 브레이크 스킬 공용 노바 증가의 상한 우회를 찾아 `nova_add`로 통일했음. 팀/개인×상한12/legacy0 실제 발동 시험과 고장 주입 실패 2건을 확인했음. [대응표](docs/client_recheck_reb.md).

### C — 자동 대상·형태·선제 방어

- 19개 규칙을 대조했음. 자동 대상 필터 전 자신 제외를 반영하고 `ally_auto_lines=client`를 기본으로 했음. 형태별 매핑을 유지하고 선제 방어 client의 NoPreemptiveDefend를 연결했음. recognize 기본·기존 근사는 유지했음. [대응표](docs/client_recheck_rec.md).

### D — 감소 시점·길방 카운트

- LevelBuffDecrease 런타임과 그웬 감소 뒤 예약 특수기 실행을 확인했음. 카넬리아 잔향 비소모·강인한 타격 시전별 50%, 부케 피해 증가, 소환체 포함 길방 카운트를 재확인했음. 규칙 값은 유지했음. [대응표](docs/client_recheck_red.md).

### 강제 협공

- `forced_coop_target=random`을 기본으로 했음. 효과 대상의 공격력·체크 버프 필터와 최종 강제 후보 추첨을 나눴음. 유효 후보만 균등 선정하고, 없으면 일반 협공으로 내려감. 플래그는 턴 끝 초기화함. `live_atk`·`stat_atk`는 보존했음.
- 독립 리뷰에서 단일 본대상 사망 뒤 다른 적으로 재지정하는 경계를 찾아 `coop_dead_target=cancel`을 추가했음(`legacy/alt=retarget`). MC·기대값에 같은 취소 조건을 적용했음. 광역 저장 대상 대응은 미확인으로 남겼음. [근거·시험](docs/client_recheck_forced_coop.md).
- 강제 협공 시험 파일 11개·기대값 전용 12개를 통과했음. 고장 주입 MC 4종·기대값 6종·단일 대상 사망 취소 2종을 모두 탐지했음. 실제 전투 강제 경로 4회·진행도 1.0, 일반 협공 새 분기 22회·진행도 1.0을 확인했음.

### 누락 점검

- `coop_trigger`, `coop_single`, `forced_coop_slot`, `forced_coop`, `BASE_MULT`, `DEF_K`, `DEC_CAP`, `rand_range`, `any_turn_clock`, `enemy_cd_tick` 10개는 값 유지·grade=code·source 갱신했음. 카운터 일반 공격 조건은 확인했으나 지속 피해 경계 때문에 data를 유지했음. [확인 표·후보](docs/client_recheck_extra.md).
- 독립 리뷰는 불변 작업트리에서 `git diff eb522be..HEAD`로 병합된 9개 작업과 이번 수정의 상호작용을 읽었음. 노바 상한 우회·단일 대상 사망 재지정·한글 설명 손상 3건을 확인해 반영했음. 수정 스냅샷 재확인에서 추가 지적 없었음. 기각한 지적은 없음.

### 재생성·시험·공지

- `build_simpack.py → update.py → gen_quick_calib.py --per-content 400 --opboss → calibrate_quick.py --write → build_guild_sim.py(기본 인자·4작업자) → build_party_html.py index.html` 순서로 완료했음. update의 태그 문서는 줄 집합 동일·순서만 달라 원복했음.
- 단일 대상 사망 수정 전 빠른 계산 표본 작업은 354.8초에 중지하고 처음부터 다시 만들었음. 최종 단계별 소요는 아래와 같음. 최초 simpack/update와 수정 후 재실행 기록을 함께 남겼음.

```text
simpack 0.1524314 exit=0
update 22.5871662 exit=0
gen_quick 354.7641603 exit=-1
simpack_update_final 22.7772289 exit=0
gen_quick_final 428.0621252 exit=0
calibrate 87.5656995 exit=0
guild 946.1591381 exit=0
html 1.2448868 exit=0
```

- 공개 화력 지표 변경 구원자는 **0명**임. 빠른 계산 검증은 2323건, 시뮬 표본과의 가중 일치율 **91.5→91.8%**임. 계수·보정값은 이전과 같았음. 스테이지 반반 검증은 코스모 93.2→94.7%, 플래시 포인트 87.8→90.5%였음. 작전 큰 보스 m=0.85 후보는 보류 검증 개선이 작아 새 적용 0곳임. 자세한 그룹·보류 검증은 `data/quick.json calib`에 기록했음.
- 길방 기본 인자 5편성×5육성×2프리셋×6지원×13단계×60판 = **234,000판**을 완료했음. 이전 공개 JSON과 모든 필드가 정확히 같아 파일 diff는 없음. 공개 표준 육성이고 계정 수치는 없음. 최고 단계는 클리어율 50% 이상인 후보 기준임.

| 육성 | off 최고 단계(클리어율) | max 최고 단계(클리어율) |
| --- | --- | --- |
| ×1 | 없음 | 없음 |
| ×1.5 | 2 (70%) | 없음 |
| ×2 | 6 (85%) | 3 (91.67%) |
| ×2.5 | 7 (83.33%) | 5 (56.67%) |
| ×3 | 8 (88.33%) | 6 (81.67%) |

- 시험 처리: P1 골든은 당시 `stat_atk` 입력, P2/MC 해시는 `live_atk`·`retarget`로 고정했음. 일반 협공 끔이 강제 협공까지 막던 새 경로 결함을 두 엔진에서 고쳤음. 일반 협공 순서 감시는 본대상 사망으로 취소되는 행동을 제외하고 실제 분기 횟수를 계속 검사함. 골든·해시 기대값은 바꾸지 않았음. 최종 자료 재생성 뒤 추가 시험 실패는 없었음.
- 수정 전 기준선은 76/0, 최종 rebuild는 78/0, e2e 포함 79/0(브라우저35개)임. 독립 리뷰 재확인·`git diff --check` 통과했음. 이번 작업 전 HANDOFF의 약 1주 지난 절은 이미 HISTORY로 옮겨져 있어 새로 옮길 절은 없었음.
- 공지: «📢 11/03 업데이트 · 최신 클라 코드로 전투 규칙 재확인 · 협공·노바 상한·적 쿨·반격 반영 · 길방 시뮬 표 재계산 · 실제 플레이 대조 전이라 결과가 다를 수 있음». README도 갱신했음. 푸시 전 상태이므로 절 제목과 저장소 상태는 푸시 대기로 적었음.

## ▶ 2026-11-02 (회사 PC, codex) — 길방 시뮬 표 선택 효과·육성 배수 (푸시 완료)

- 기본 프리셋은 설계대로 `off=[0,0,0,0]`, `max=[3,3,3,3]`로 했음. 육성 기본값은 `1,1.5,2,2.5,3`임. 기존 `rates`·`bySupport`·`progBySupport`·`fracBySupport`·`summary`는 off로 유지하고 `sets`·팀별 `bySets`·`summaryBySets`를 추가했음. `guild_defense.py sim_payload`도 새 필드를 전달하며 옛 자료는 off만 표시함.
- `simExpect`는 프리셋별 실제 `fracBySupport`와 `extraPct`를 함께 써 최대 기대 점수를 고름. 결과에 «선택 효과 끔/모두 최대» 칩을 붙였음. 기존의 frac만 있고 progress가 없으면 frac를 무시하던 경계도 고쳤음. 최고 클리어 단계·상세 클리어율 표는 off 기준, 지원별 비교 표는 기존 ×2 기준을 유지했음. Python/JS 점수식은 0·1·.5 반올림 경계까지 대조했음.
- 순차 재생성 초반 속도로 40분 초과가 예상돼 편성·육성·프리셋별 독립 작업을 최대 4개 프로세스로 나눴음(`--workers 1`은 순차). 시드·판수·결과 병합 순서는 같으며, 실제 엔진 순차/병렬 결과 일치 시험을 추가했음. 순차 시도를 중단한 뒤 `python -X utf8 -I tools/build_guild_sim.py` 기본 인자로 다시 시작해 끝까지 완료했음.
- 재생성: 5편성×5육성×2프리셋×6지원×13단계×60판 = 234,000판. 최종 실행 약 778초(12분 58초), 빌더 계산 로그 777초였음. 이전 ×1·×1.5·×2의 off 클리어율·진행도·판별 frac·summary는 HEAD 자료와 모두 정확히 일치했음. `index.html`도 새 자료로 다시 만들었음.

| 육성 | off 최고 단계(클리어율) | max 최고 단계(클리어율) | 최대 기대 점수·선택 |
| --- | --- | --- | --- |
| ×1 | 없음 | 없음 | 20,568 · off 0단계 |
| ×1.5 | 2 (70%) | 없음 | 46,376 · max 1단계 |
| ×2 | 6 (85%) | 3 (91.67%) | 56,368 · max 3단계 |
| ×2.5 | 7 (83.33%) | 5 (56.67%) | 57,000 · max 3단계 |
| ×3 | 8 (88.33%) | 6 (81.67%) | 63,459 · max 6단계 |

- 최고 단계는 클리어율 50% 이상인 후보 기준임. 표는 공개 표준 육성으로만 만들었음. 엔진 소규모 시험(커뮤니티 편성·×2·6단계·불의 고동·seed=7·12판)은 off/max 진행도 0.6696/0.5710, 클리어율 8.33%/0%였고 양쪽 진행도>0을 확인했음.
- 추가 프리셋은 `--sets off,max,no_void=3330` 형태로 받음(순서: 소멸·불멸·쇠락·허무, 각 0~3). 커뮤니티 편성·12판·불의 고동/격돌의 돌풍·0~12단계 소규모 비교에서 최고 기대 점수는 ×2 off/max/no_void 32,962/38,772/37,341, ×3 46,472/52,011/50,636이었음. 이 표본에서는 no_void가 max를 넘지 않았음. 전체 256조합 최적을 보장하지 않으며 기본 표에는 off/max만 넣었음.
- 시험을 일부러 깨뜨린 경우 7건을 모두 잡았음: 엔진 선택 효과 끄기, 빌더의 sets 전달 끄기, 병렬 결과 순서 뒤집기, payload의 bySets 제거, 화면의 프리셋 비교 끄기·off 결과 재사용·점수 가산 제거. 메모리에서만 바꿨고 실제 소스는 정상 상태로 유지했음. 새 시험은 기본 인자→파일→화면 자료 전달, 프리셋 승자 전환, 추가 프리셋·옛 자료 호환을 확인함.
- 수정 전 기준선은 69 통과/실패 0, 최종 `python -X utf8 -I tools/run_tests.py --rebuild`는 시험 파일 70 통과/실패 0이었음. `python -X utf8 -I tools/run_tests.py --e2e E:\AI_mk2\venv-pw\Scripts\python.exe`는 전체 71 통과/실패 0이었음(e2e 내부 31개 모두 통과, `test_guild_defense`·`test_guild_season_rollover`·`test_guild_search` 포함). `git diff --check`도 통과했음.
- 독립 리뷰는 커밋 없이 HEAD `9c8808a` 기준 diff와 소스·시험의 불변 사본으로 두 번 했음(병렬화 추가분 포함). 수정 필요 지적은 없었음. 엔진 규칙·골든·해시를 바꾸지 않았고 계정 자료를 사용하지 않았음. 실제 영상 재대조는 하지 않았음. Claude 가 `run_tests.py`(70 통과)·길방 e2e 3개를 다시 돌려 확인한 뒤 커밋·푸시했음.
- e2e 흔들림: 작업 전 `--rebuild --e2e` 에서 `test_guild_season_rollover` 가 콘솔 `ERR_CONNECTION_REFUSED` 1줄로 실패(기능 판정은 전 0/후 1 정상)했고, 단독 3회 재실행은 모두 통과했음. 앞서 `test_load_no_errors` 도 로드 시간 초과로 한 번 실패했음. 매번 다른 시험이라 부하·시험 서버 흔들림으로 보고, 반복되면 해당 요청 주소를 기록해 원인을 보기로 함.

## ▶ 2026-11-02 밤 (회사 PC, codex) — 협공 확률 상한 해제 `COOP_CAP` (중간 저장, 푸시 완료)

- `formula.COOP_CAP` 기본값을 1.0으로 바꿨음(`legacy=0.30`, `alt=[0.30]`, `grade=data`). `rules.py` 주석과 규칙 근거를 맞췄음.
- 근거: `star-savior-decompiled/NKM/NKM.decompiled.cs:15835-15951`은 최종 협공 능력치 내림차순으로 `RollDice(value, 10000)` 판정함. `:2171-2201`·`:3611-3618`에서 버프 능력치 합을 넣어 `:18244` 이후 최종 능력치를 다시 계산하며, `:18462-18476`은 `StatDataCap`의 양수 상한만 적용함. (→ 11/03 최신 빌드에서 random_success로 재확인·반영)
- `NKM.Templets/NKM.Templets.decompiled.cs:27064`가 읽는 표는 `starsavior-static-data/tables/Plain/CLIENT_CONST_TEMPLET.json:125-142`임. `:138-142`의 치명·치명 피해 상한은 활성이고 협공 3000은 주석 처리돼 있음. `JSON_STAT_DATA_CAP`·`m_StatDataCap`은 현 디컴파일본 검색 0건임. 상한이 있었다면 버프에도 걸리는 구조지만, 현 표에는 협공 상한 자체가 없음.
- `LEGACY_FORMULA`를 모으고 `rank_check.apply_rules(base='legacy')`가 기대값 엔진 상수에도 적용하도록 했음. `--base legacy --golden tests/golden/sim_golden_p1.json`에서 구원자 65명·파티 150팀·스테이지 50칸 정확히 일치했음.
- 고정 결과 시험은 0.30을 명시했음: `mc_cache_test`·`heal_burst_test`는 `formula_override`, `golden_check`는 기대값 엔진 상수, `guild_defense_test`의 추천 출력 해시는 옛 상한으로 만든 화력 입력을 씀. 저장된 골든·해시는 바꾸지 않았음. `web_test`의 임시 교체값도 0.30으로 바꿔 새 기본값 1.0 복원을 검사함.
- `coop_cap_test.py`를 추가했음. 공개 표의 에밀리·왈츠 아세라·힐데·메이드 세레스, standard 육성, 태양 회랑 250층, seed=17, 20판에서 협공 버프 30% 초과 경로와 양쪽 진행도>0·협공>0을 확인했음. 판당 협공은 0.30에서 2.45회, 새 기본값에서 6.10회였음. 기본값을 메모리에서 0.30으로 되돌리자 `2.45 not greater than 2.45`로 실패했으며 1.0으로 원복했음. 계정 자료는 쓰지 않았음.
- `tools/update.py`로 화력 지표(`sim_damage.py index` → `pack_damage.py`)와 빠른 계산 재료를 재생성했음. 화력 지표의 변경 구원자는 왈츠 아세라 1명임. `gen_quick_calib.py --per-content 400 --opboss`로 표준 육성 표본 2,323건×40판을 새 엔진으로 생성한 뒤 `calibrate_quick.py --write`로 `data/quick.json`의 계수·콘텐츠/스테이지 보정·검증 요약을 다시 맞췄음. `update.py`가 만든 태그 문서의 순서만 바뀐 차이는 원복했음.
- `tools/build_guild_sim.py` 기본 인자로 `data/guild_sim.json`을 재생성했음(5편성×3육성×6지원×13단계×60판=70,200판, 805초). 선택 효과 끔·브레이크 미장착·표준 육성 가정을 유지했음. `rates`·`bySupport`·`progBySupport`·`fracBySupport`·`summary`가 새 엔진 결과임. 재생성을 생략한 요청 자료는 없음. (→ 이후 11/02 길방 시뮬 표 선택 효과·육성 배수 절에서 off/max·5육성으로 재생성)
- 새 자료로 첫 전체 재빌드 시험은 67 통과 / 2 실패였음(`reco_parity_test.py`, `reco_reuse_test.js`). 수정 전 기준선은 68 통과 / 실패 0이므로 새 자료가 드러낸 차이임. 고정 추천 결과는 새 화력표·재보정 계수에 영향을 받았음. `tests/fixtures/reuse_legacy_inputs.json`에 `684ed40`의 이전 공개 입력(0.30 화력·빠른 계산 계수)만 고정했고 `reuse_baseline.json`의 기대값은 유지했음.
- 순서 대조 실패는 Python 3.13의 `sum()` 보상 합산과 JS 순차 합산의 끝자리 차이(25.310000000000002와 25.31)가 원인이었음. `party_reco.py team_value`의 점수·시너지 합산과 태그 가산 순서를 JS와 맞췄음. 기존 상위 200 조합·동점 순서 시험이 변경 전 실패하고 변경 후 통과했음. 길방 빌더의 후보 4편성·리더가 생성 때와 그대로임도 확인해 앞서 만든 시뮬 표를 유지했음.
- 최종 `python -X utf8 -I tools/run_tests.py --rebuild`: 시험 파일 69 통과 / 실패 0. `build_simpack.py`·`build_party_html.py index.html`을 다시 실행했고 `git diff --check`도 통과했음. 골든·해시 기대값 변경 없음. e2e·실제 영상 재대조는 하지 않았음. 작업 트리만 수정했으며 커밋·푸시하지 않았음.
- 독립 리뷰는 커밋 없이 HEAD `684ed40` 기준 diff와 수정 파일의 불변 사본으로 했음. 추가 추천 합산·fixture 수정까지 리뷰했고 수정 필요 지적은 없었음. fixture 값이 이전 공개 입력과 일치함도 확인했음. 기존 근사로 `mc.py:1943`이 상한 적용 뒤 확률로 정렬하므로, 서로 다른 100% 초과 후보가 여러 명이면 클라의 원래 능력치 순서와 달라질 수 있음. 이번에는 상한 기본값과 재현 경로만 바꾸고 이 경계는 남은 일 18번에 기록했음. (→ 11/03 최신 빌드에서 random_success로 재확인·반영)

## ▶ 2026-11-02 저녁 (집 PC) — 세레스 먼지 포착 `level_buff_decrease` (푸시 완료)

- 영상 2개(작전 38-36 오토 `op3836-c` 재점화 3, 성간 회랑 450 오토 `corr450-c` 재점화 5·세레스 첫 실측)를 `docs/ingame_samples.md` 에 정리했음.
- 450 대조 중 구원자 키를 잘못 넣어(`ceres` 스트라이커 대신 `ceres-sun-supporter` 서포터) 「세레스 회복 미구현」으로 오판했다가 정정했음. 동명 구원자는 이름·부제·직업으로 키를 확인할 것.
- 올바른 키에서 시뮬이 실제보다 오래 버팀(행동 수가 실제 TURN 97 보다 큼). 원인 조사(Opus, 읽기 전용): ① 먼지 포착 «5회 부여»는 표상 `LevelBuffDecrease` 5 감소(`SE_TEMPLET_SKILL_1.json:38328-38343`)인데 엔진이 5를 더했음, ② 협공 상한 0.30(후보).
- ① 을 `level_buff_decrease`(기본 on, off=옛 동작)로 반영: 영상에서 추가 발동 전후 중첩 5건 중 4건이 정확히 -5(1건 7→4 원인 불명, 4건은 후 값 미판독). 450 대조 수치는 내 정보 기반이라 비공개 작업 폴더에만 둠(행동 수·회복·받은 피해가 실제에 가까워짐). 그웬·카넬리아 `LevelBuffDecrease` 는 감소 시점 미확인이라 제외. 시험 `tests/level_buff_decrease_test.py`. (→ 11/03 현재 빌드에서 그웬 감소 뒤 예약 특수기 실행·카넬리아 비소모 확인)
- ② 는 보류: 아세라 뤼니송 문구는 「통찰 스택당 협공 확률 20%, 최대 5개」(최대 100%)인데 `COOP_CAP` 0.30(클라 `NST_RATE_CROSS_ATTACK` 3000)이 막음. 영상: 38-36 에서 프로페서M 기본기 뒤는 강제 협공(아모라)이 협공 자리를 차지해 아세라 협공이 안 붙고, 힐데 기본기 뒤 2/2 발생, 450 에서 70% 이상. 클라 상한이 스킬 증가분에도 걸리는지 확인 필요. (→ 11/02 밤 회사 PC: 클라에 상한 없음 확인, 기본 1.0)
- 남은 차이: 450 웨이브 2 길이(시뮬이 실제보다 김)·첫 사망 시점. 후보는 출혈 겹침·보호막. 조사물 `AI\temp\partynavigator\work\video_1102_corr450\investigate\`.

## ▶ 2026-11-02 (회사 PC, codex) — 강제 적용·스택 시점·소환체

- Claude 가 검토·시험 후 커밋·푸시함. 같은 때 Claude 는 시즌 경계 화면 갱신(`party_template.html gsWatch`, e2e)과 길방 시뮬 표 재생성(`fracBySupport`)을 함.

### 강제 적용·피해 제한

- `buff_ban_force=client`를 새 기본값으로 넣었음(`legacy/alt=off`). `add_effect`·보호막 부여·`_limit_damage`의 신규 불사/후속 강화가 공통 `refuse_buff` 판정을 씀. 기존 강화는 유지하며 기존 바큇살의 생명력 회복·쿨 초기화도 그대로임. `off`는 강제 강화까지 거부하고 피해 제한은 직접 삽입하던 옛 동작임.
- 근거: `NKM/NKM.decompiled.cs:4053`의 CantGetMoreBuff + IsBuff + !ForceApplyEffect. `BUFF_TEMPLET.json:2224`의 BI_IMMORTAL과 `:22339`의 BI_MAID_LANTERN_1은 IsBuff=true, ForceApplyEffect=false임. 조율은 `:37175`의 BI_TUNER_CROWN_2(IsBuff/ForceApplyEffect=true)임.
- `tools/build_buff_force.py --static E:/AI_mk2/starsavior-static-data`로 BUFF_TEMPLET의 m_BuffName을 `Strings/STRING_COMMON_ko_en.json:1`의 ko와 연결했음. 공개 `data/buff_force.json`에는 동명 충돌 없는 강제 강화 이름 77개만 저장했음. IsBuff/ForceApplyEffect가 다른 동명 효과 17종은 경고 후 제외했음(지속 회복·참극의 가시·용의 역린·타임 패러독스 등). BuffStrID·원문 표는 복사하지 않았음. 브라우저 manifest에 새 자료를 추가했음.
- standard, seed=17, 편성·스테이지·규칙별 100판 비교했음. A=카넬리아·그웬·화이트 펄 루나·웨딩 카르멘, B=카넬리아·아모라·힐데·웨딩 카르멘. 어려움 34-6: A 클리어 0→0%, 진행도 0.0269→0.0269, B 0→0%, 0.0343→0.0343. 어려움 39-3: A 0→0%, 0.0182→0.0182, B 0→0%, 0.0278→0.0278. 모두 `off→client` 순서임. 강화 불가 중 부여 판정이 0회였으므로 이 비교는 규칙 영향 없음의 근거로 쓰지 않기로 함. 직접 효과 부여·치명 피해 경계 시험으로 변경 경로를 검증했음.

### 강인한 타격·소환체

- 강인한 타격: `guild_support_test.test_strike_cast_probability` 추가했음. 고정 시드 731, 400시전×3타에서 192시전 발동(48%), 한 시전의 모든 타격 판정 일치 확인했음. 기존 50% 기본 동작은 유지했음. 근거: `SE_TEMPLET_BATTLE_EFFECT.json:901`의 SE 4011102(m_fActiveRate=5000), `NKM/NKM.decompiled.cs:16284`의 시점 확인 뒤 확률 판정.
- 질투의 시선: `Plain/SKILL_CONDITION_TEMPLET.json:10427`(58801)은 AfterEnemyAction·보스 비변신 조건뿐임. 소환은 `NKM/NKM.decompiled.cs:5198`에서 OBF_26401을 생성하며, `:15662` SKILL_END → `:15705` → `:16040` 유닛 클래스 검사 → `:16079` 적 행동 후 SE 발행 경로에 포함됨. 기본 `guild_count=all`과 같아서 동작 수정 없이 근거 주석과 `test_summoned_cast_count`를 추가했음. 실제 소환 표지 Unit의 cast·피해·카운트/신부 경쟁 증가 및 같은 편·변신 중 제외를 확인했음. 아군 소환 자동 생성 기능을 새로 넣은 것은 아님.

### 스택·예약 경로 조사

- 그웬: 현 표 기준 `SE_TEMPLET_SKILL_1.json:24523`(10404015)는 SKILL_END 엔포스 예약, `:24541`(10404016)은 AfterActiveSkillSe=true·RepeatBuffCount=5·LevelBuffDecrease=true임(이전 기록 23868은 현 파일 줄과 다름). `NKM:2635`는 액티브 SE 뒤 AfterActiveSkillSe를 배치하고 `:15662`·`:15955`·`:16158`에서 종료 SE를 실행함. 엔진은 `run_batch`가 consume 줄을 extra_cast보다 먼저 실행하며 `apply_buff`가 5개 감소시킴. 다만 현 `Star.Templets.decompiled.cs:25257` 로더는 AfterActiveSkillSe·RepeatBuffCount를 읽지만 `LevelBuffDecrease`는 전체 디컴파일본에 없음. 감소 런타임을 확인하지 못했으므로 시점 변경·새 규칙 도입 없이 미확인으로 남겼음. (→ 11/03 build 26314877의 LevelBuffDecrease 런타임·감소 후 예약 실행으로 재확인 완료)
- 카넬리아: `SE_TEMPLET_SKILL_1.json:2815`(10052014), `Plain/SKILL_CONDITION_TEMPLET.json:8560`(52123)으로 칠흑의 잔향 보유·내 턴·SKILL_END 특수기 추가 발동 및 SeCoolTurn=1 확인했음. 잔향은 IsLevel=false(`BUFF_TEMPLET.json:22339`)이고 이 SE에 삭제·감소 설정이 없음. `NKM:15662`·`:15955`·`:16280`에서 종료/쿨 검사, `:16319`에서 쿨 등록(`:3277`의 SeCoolTurn 저장) 후 예약함. 엔진도 extra_cast의 줄 쿨로 재발동을 막으며 잔향·격동을 소모하지 않음. 격동은 own_pre에서 공격력 보정에 읽고 사용 후 부여함. count_damage 경로는 카넬리아 정규화 줄에 없음. 소모 시점 수정 없음.
- 크리스텔·프로페서M: `SKILL_TEMPLET_1.json:816`(10172)·`:860`(10175 변형)·`:1746`(10392)은 모두 NST_REACT, ReactConditionID=10413/10418/10419임. `NKM:15672` 이후 반응 예약, `:15306` 이후 ReactAttack 불발 때만 예약 이력 초기화 경로와 맞음. fire_trigger의 key(중복 제한·불발 재예약)를 유지했음. 이전 기록의 크리스텔 엔포스 표현은 이 두 반응 스킬에는 적용하지 않음.

### 검증

- 새 시험 6개(강제 강화 4·타격 확률 1·소환체 1)를 추가했음. 메모리에서 구현을 바꾸어 동명 충돌 경고 제거·강제 예외 제거·보호막 예외 제거·불사 우회·후속 강화 우회·타격 확률 100%·타격마다 재추첨·유닛별 확률 고정·소환체 제외의 9가지 오류가 모두 시험을 실패시키는 것을 확인한 뒤 원복했음.
- 기준선은 65 통과/1 실패(index.html 최신성)였음. 수정 전 HEAD bbdc21e를 별도 폴더에 git archive하여 `guild_defense_test.py` 12개 통과를 확인했음. 기존 커밋 결함이 아니라 동시 화면 작업 중 생성본 불일치였으며 재생성 후 해소됐음.
- 최종 `python -X utf8 -I tools/run_tests.py --rebuild`: 통과 67 / 실패 0. 골든·캐시 해시 변경 없음, `--write` 쓰지 않았음. mc_cache·heal_burst의 고정 해시 시험에는 새 규칙을 off로 명시했음. `git diff --check` 통과했음. e2e는 이번 작업에서 실행하지 않았음.

## ▶ 2026-11-02 (회사 PC) — 엔포스 대상 선택 시점·게임 PC 커밋 52개 리뷰 반영

- **엔포스 대상 `enforce_target`(기본 `exec`=클라, `book`=옛 동작)**: 클라는 예약에 시전자·스킬·자동 대상 규칙만 저장하고 적은 실행 검사에서 고름(NKM.decompiled.cs 7973·6390~6397·13181~13189). 엔진은 예약 때 골랐음 → `exec` 면 엔포스(`RX_ENFORCE`)·추가 시전 줄(`extra_cast`, 그웬 등)·공용 잠재력(`random_ally_basic`)·확률 추가 발동(`RX_EXTRA_P`, 개화 베스타 등)의 적을 실행 직전에 다시 고름(표지·최근 타격 대상·무작위). 시전자(아군)는 둘 다 예약 때. `enforce_timing=queue` 이고 행동 안 예약일 때만 차이. `mc_cache_test` 해시는 `book` 고정.
- 측정(standard 육성, 200판, 태양 회랑 200·250층, 그웬·선샤인 캣·크리스텔·힐데 / 프로페서M·클레어·아셰라·카르멘): exec·book 결과 동일(84.5%·42.0%, 진행도 0.616·0.629). 예약 뒤 실행 전에 대상이 죽는 경우가 드물어 영향 거의 없음. exec 경로가 실제로 타는 것은 확인(20판에 78회).
- **클라 확인 결과 중 반영 안 한 것**: ① 엔포스는 예약 중복 검사 없음·불발 시 재예약 없음(NKM 13174, 불발 이력 초기화는 ReactAttack 만 15306~15314) — 엔진의 엔포스·추가 시전 줄은 이미 key 없이 예약해 같음. key 를 쓰는 건 트리거 경로(크리스텔·프로페서M `fire_trigger`)뿐이고 이 경로가 클라에서 엔포스인지 반응인지 구원자별 미확인이라 그대로 둠. ③ 스택 소모 시점(SE_TEMPLET_SKILL_1): 스마일 도약 SKILL_START(1811)·클레어 냉각 SKILL_START(27623)·선샤인 캣 스파클라 SKILL_END 예약 후 삭제(28903~28965)·그웬 SKILL_END 5회 감소 설정만 확인(23868, 런타임 경로 미확인)·카넬리아 SKILL_END 추가 발동·쿨 1턴(2815, 스택 소모 미확인). 엔진 반영은 그웬·카넬리아 확인 뒤. (→ 이후 11/02 codex: 카넬리아는 소모 없음·크리스텔/프로페서M은 반응으로 확인, 그웬 감소 런타임은 미확인)
- **시험 보강**: `enforce_timing_test` 의 `test_both_modes_run` 이 standard 육성으로 진행도 0 인 스테이지(43-36)를 써서 아무것도 검증 못 했음 → 달 회랑 100층으로, 진행도 0 이면 실패하게 함. 새 시험 4개(기본값·두 값 실행·실행 때 대상 있음·예약 함수가 대상을 묶지 않음 — `_exec_pick` 을 끄면 실패하는 것 확인).
- **게임 PC 커밋 52개(c85c8d1..70dd48d) 리뷰(codex 영역별 2명 + Claude) 반영**:
  - 공개 화면 «제외·주의 구원자» 문구에 내 계정 시뮬 수치(클리어 96%→28% 등)가 있었음 → 수치 뺌(`data/guild_defense.json search.notes`).
  - 편성 찾기 기대 점수가 평균 진행도를 점수식에 넣어, 졸개전 패배와 클리어가 섞인 팀을 크게 낮춰 봤음(반반이면 5,000 vs 실제 평균 16,250) → 판별 진행도(`prog_runs`, api 결과 outcome 밖·`run_auto` 의 `progs`)로 판마다 점수 후 평균. 졸개전에서 진 판도 졸개 점수는 다 받은 것으로 두는 근사는 남음. 패널의 `simExpect`(시뮬 표 기반)는 표에 판별 값이 없어 그대로 — 표 재생성 때 같이 고칠 것.
  - 내 정보에서 «추천» 끈 구원자가 편성 찾기 풀에 다시 들어갔음 → `EXCL` 적용.
  - 내 정보를 바꾸거나 추천 제외를 바꿔도 이전 편성 찾기 결과·진행이 남았음 → `gsReset()`.
  - `.gitignore` 가 루트·`samples/` 의 내 정보 파일을 못 막았음 → `/내정보*.json`·`/myinfo*.json`·`/samples/`·`/static-data/` 추가(`git check-ignore -q` 로 확인, `tests/fixtures/` 는 안 막음).
  - 편성 찾기 시험의 가짜 작업자가 `via` 를 안 돌려 협공 배제 연결이 끊겨도 통과했음 → via·progs 전달과 `coopHit` 까지 확인.
  - 부분 점수 반올림 Python(짝수 반올림)·JS 불일치 → Python 도 0.5 올림.
  - 미반영: 시즌 종료 시각(11/05 04:00)을 넘겨 열어 둔 화면은 새로고침 전까지 «진행 중» 표시(영향 작음).
  - 엔진(길방): 강인한 타격(4011102)은 클라가 `m_fActiveRate` 5000 을 50% 로 굴림(NKM 16466) → 시전마다 50% 로 발동(지금 시전 `_cast_ctx` 가 바뀌면 다시 굴림 — 겹친 추가 발동도 따로, 옛 가정 100%). 부케 보스 자해 연쇄에 보스 피해 증가가 빠졌음(같은 편이면 inc 0) → 클라 연쇄 피해 계산은 대상 진영과 무관하게 시전자 피해 증가 반영(NKM 5605). `guild_sim.json` 시뮬 표는 이 두 수정 전 값 — 다음 표 재생성 때 반영.
  - `wave_gauge_test` 도 진행도 0 스테이지라 웨이브 전환이 한 번도 안 일어났음 → 태양 회랑 250층 + 전환 직후 아군 게이지(reset 0 / keep 이월)를 직접 확인하는 시험 추가.
  - **다음에 할 것(리뷰로 확인된 결함, 데이터 작업 필요)**: ① 〈강화 불가〉 중에도 `ForceApplyEffect` 강화는 걸림(NKM 4053, BUFF_TEMPLET 351개가 True) — 엔진은 전부 거부해서 공허조율자 «조율»(어려움 34-6·39-3) 같은 강제 적용 중첩을 막음. 효과 한글 이름 ↔ BuffStrID ↔ ForceApplyEffect 표를 `tools/` 로 뽑아 `add_effect` 거부 조건에 넣어야 함. ② `_limit_damage`(mc.py ~2305)가 치명 피해 때 새 〈불사〉·후속 강화(카넬리아 칠흑의 잔향 등)를 `add_effect` 없이 직접 넣어 〈강화 불가〉를 우회함 — ①의 표로 같이 처리. ③ 강인한 타격 50% 시험(발생 비율 확인)이 아직 없음.
  - 반영 안 한 리뷰 지적: 격돌의 돌풍 게이지 3,000 이 2,000 이어야 한다는 지적은 틀림 — 11/01 패치로 2000→3000(docs/HISTORY.md 11/01 절). 이 PC 의 static-data 에 11/01 표가 없어 생긴 오판.
- 수정분은 codex 로 한 번 더 검토(지적 3건: 확률 추가 발동 경로 누락·강인한 타격 판정 재사용·시험이 기능 제거를 못 잡음 → 모두 반영). 전체 Python·JS 시험·골든·e2e(Playwright, `E:\AI_mk2\venv-pw`) 통과. (→ 경로는 새 «환경·주의»의 E:\AI_mk2\venv-pw 기준)
- 이 PC 의 `starsavior-static-data` 가 10/22 빌드라 `myinfo_stats_test` 가 실패했음 → pull 후 통과. 새 PC·오랜만의 PC 에서는 두 저장소 다 pull 부터.

## ▶ 2026-11-02 밤 — `enforce_timing` 기본을 `queue` 로 전환 (푸시 완료)

- 근거(조사 `AI\temp\partynavigator\work\common_rules\enforce_client_check.md`·`enforce_order_check.md`·`enforce_tl.md`): 스마일(선샤인 캣)·클레어·그웬·카넬리아의 추가 발동은 전부 `BI_ENFORCE`(SE_TEMPLET_SKILL_1, NSEAT_SKILL_END), 반응형 아님, 확률 줄 없음(m_fActiveRate 10000 = 조건 맞으면 100%; 엔진 RX_EXTRA_P 는 베스타·공용 잠재력용). 클라는 시전 함수(DoSkill:3025) 안에서 SKILL_END SE 처리(스킬 후 해제 — 예: AX 스택 SEID 4000102, 조건 8003 궁극기 종료 — 와 엔포스 예약 등록)를 끝낸 뒤 반환하고 예약 루프(2827~2926)가 돈다 → 해제가 먼저, 추가 발동은 그 뒤. 엔진 queue 가 이 순서와 같음(nested 는 해제 전에 시전해 힐데 3 에서 과대평가).
- 영향(1000판, wave_ally_gauge=reset): 태양 회랑 450 클리어 nested 58.8% → queue 88.6%, 코스모 힐데 3(그웬·스마일·크리스텔·힐데) 95.0% → 82.0%. 원인은 11개 상한·반격 순서가 아니라 지연 시전 때의 버프·표지 상태 차이.
- **편성 찾기 재실행(reset+queue 기본, 내 정보 11/02, 선택 효과 최대, 6단계·불의 고동)**: 순위·기대 점수·클리어율은 비공개 로그 `...\work\guild_defense\gs_full_out_1102_queue.txt`(수치는 비공개 폴더). 11/03 촬영은 이 탐색의 1위 편성으로 함.
- 시험: `enforce_timing_test` 기본 queue 로 갱신, `mc_cache_test` 해시는 `wave_ally_gauge=keep`·`enforce_timing=nested` 로 고정(캐시 동일성 시험). 골든 불변, 전체 시험 통과.
- **미반영 클라 차이(엔진 수정 후보, 미확인 부분 있음)**: ① 엔포스는 예약 중복 제한 없음·불발 시 재예약 없음(엔진은 행동당 1개 제한, `_defer_extra` key) ② 대상은 실행 직전에 자동 대상 규칙(4/6/47)으로 선택(엔진은 예약 때 선택, 죽으면 무작위) ③ 스택 소모 시점 구원자별: 스마일·클레어 = 실행(SKILL_START), 선샤인 캣 = 예약(SKILL_END), 그웬 = 예약 추정. 영상 대조 전이라 아직 안 고침. (→ 11/02 회사 PC: ① 엔포스·추가 시전은 이미 key 없음, 트리거만 미확인; ② exec 반영 완료; ③ 스택 소모는 미완료)

## ▶ 2026-11-02 웨이브 전환 아군 게이지 규칙 `wave_ally_gauge` (푸시 완료)

- 클라 `BattleHostSingle.cs` 391~421: 웨이브 전환 때 OnWaveStart 트리거 실행 **뒤** 생존 아군 전원 게이지 `Set(0)`(적 신규 웨이브도 0, 보스 웨이브 전용 속도 보정·행동 대기 못 찾음). 엔진은 이월. 규칙 `wave_ally_gauge`(기본 `keep`=옛, `reset`=클라; `mc.spawn_wave`). 기본값은 영상 검증 전이라 keep. 시험 `tests/wave_gauge_test.py`, 근거 `AI\temp\partynavigator\work\guild_defense\wave_gauge.md`, 비교 `scripts\gd_wavegauge_cmp.py`. (→ 이후 기본값을 reset 으로 전환)
- 길방 상위 3팀(내 정보 11/02, 6단계·불의 고동, 100판) keep→reset: 클리어율이 대체로 내려가고 어필 횟수·보호막 시간 초과가 늘었음. 차이 원인 확인: 화면 편성 찾기는 선택 효과 4종 최대(3,3,3,3)로 돌리는데 스크립트가 끈 상태였음(선택 효과 단계가 오를수록 클리어율이 크게 떨어짐). 선택 효과 최대로 다시 비교(100판) keep→reset — reset 이면 순위가 크게 흔들림, 시간 초과(보호막 못 깸) 증가. 표본 100판이라 변동 포함. 수치는 비공개 폴더.
- 내 정보 11/02 08:43 반영(세레스 육성), 편성 찾기 재실행: 1위 동일, 풀 32·조합 28,435(편성·수치는 비공개 폴더).
- **기본값을 `reset`으로 전환(11/02)**: 호출부 추적(`wave_gauge.md`)로 확인 — 핸들러는 첫 웨이브 제외 **모든** 웨이브 전환에서 1회(`BattleHostSingle.cs:266`, 조건: 웨이브 데이터·마지막 아님·적 전멸, 일반/보스 구분 없음), 게이지 세터는 실제 행동 게이지(`TurnSpeedCalculator`), 전환 직후 속도 랜덤 없음. 추가 턴은 클라에서 게이지가 아닌 예약이라 엔진은 `extra_turn` 유닛 게이지를 유지(`break_skill_test` 근거). `mc_cache_test` 해시 3개는 `keep` 으로 고정(캐시 동일성 시험이라 규칙과 무관). 골든·전체 시험 통과(골든 불변). 옛 동작 `wave_ally_gauge=keep`. **영상 대조는 미검증**(보스 등장 직후 아군 게이지·스칼렛 행동 횟수).
- **reset 기본으로 편성 찾기 재실행(내 정보 11/02, 선택 효과 최대, 6단계·불의 고동)**: 1위가 바뀜. 상위 팀끼리 기대 점수 차가 작아 순위가 불안정(판수 40). 편성·수치는 비공개 폴더. 로그 `AI\temp\partynavigator\work\guild_defense\gs_full_out_1102_reset.txt`. (→ 이후 reset+queue 재탐색 결과는 11/02 밤 절)
- 다음: `enforce_timing=queue` 확인 4가지, 영상 촬영 대조(편성 찾기 1위로 1판). (→ queue 기본 전환·코드 확인은 완료, 스택 소모·영상 대조는 남음)

## ▶ 2026-11-02 길방 «내 정보로 최고 점수 편성 찾기» + 질투의 시선 카운트 정정 (푸시 완료)

- **편성 찾기(`guild_search.js`, 패널 아래 `#guild-search`)**: 내 정보를 불러온 뒤 버튼 → 브라우저 작업자(`sim_worker.js`, 최대 8개)로 3단계 탐색. ① 풀 전 조합 2판(예선 단계 6, 서포터 있으면 격돌의 돌풍·없으면 불의 고동) ② 상위 400팀 10판 ③ 상위 12팀 × 별의 도전 단계 [2,4,6,8,10,12] × 지원 × 40판 → 기대 점수 상위 5. 기대 점수는 확인된 점수식(진행도 → 보스 깎은 비율). 선택 효과 단계는 위 패널에서 고른 값. 실측(24코어 PC, 내 계정): 풀 33명·조합 31,855개, **5분 20초**, 1위 루나(화이트 펄 트랩)·트리쉬·아모라·스마일(선샤인 캣), 6단계·불의 고동, 기대 63,514(클리어 약 13%·보스 평균 95% 깎음). 저사양 PC 소요 시간은 미측정(조합 수가 시간을 정함). (→ 이후 reset+queue 재탐색으로 1위 변경, 11/02 밤 절 참고)
- **풀 선정이 핵심이었음**: 전투력 상위 N명만 쓰면 어제 상위 팀(아모라 18위·루나 24위·카르멘 28위, 세레스(샤프 앤 스위트)는 전투력 최고의 37%)이 빠짐. 지금은 `minPowerRatio` 0.8 이상 + 역할 보충(`minRole` 서포터 6·디펜더 3). 전투력은 100k~115k로 거의 평평해 단독 기준으로 못 씀. 2판 예선에서도 어제 상위 팀이 15~184위(풀 안에서)에 들어 400팀 유지로 충분.
- **시즌별 규칙은 `data/guild_defense.json` 의 `search`**(풀·판수·단계·지원·`excludeText`·`excludeKeys`). 보스가 매 시즌 바뀌니 새 시즌에는 이 값과 `guild_bfb.py` 를 같이 검토(화면에도 경고). 기억 `guild-defense-per-season`.
- **협공 제외(체크박스, 기본 켬)**: 스킬 문구에 «협공» 있는 구원자(프로페서M·왈츠 아세라) + 직접 지정 `excludeKeys`(그웬). 커뮤니티 근거(아카라이브 187421752 등, 중간 신뢰: 길방 EX는 협공 금지, 아모라 후열, 불의 고동). 세레스(샤프 앤 스위트 `ceres-sun-supporter`)는 그웬과 같은 «추가 발동» 문구 형태이나 커뮤니티가 필수로 써서 뺀 것이 아님. 이름이 같은 별개 구원자가 있음(세레스 샤프 앤 스위트=서포터 / 서부 탈환대=스트라이커 `ceres`, 스마일 보이저 `smile` / 선샤인 캣 `sunshine-cat-smile`, 웨딩 카르멘 등) → 항상 키·부제로 구분. (→ 이후 그웬은 제외에서 주의로 이동, 협공은 시뮬 via 로 자동 배제; HISTORY 11/01 협공 절)
- **엔진 정정(클라 코드 근거, `work/guild_defense/coop_analysis.md`)**: 질투의 시선(조건 58801 AfterEnemyAction)은 시전이 끝날 때마다 발행(DoSkill.cs:3025·3695)되고 협공·반격·반응·엔포스(추가 발동)도 같은 경로, 58801 에 IsNotEnforceSkill 없음 → **신부 경쟁 카운트에 모든 시전이 포함**. 규칙 `guild_count`(all 기본 / main = 옛 가정). 내 계정 6팀 비교에서 진행도 변화 ≤ +0.013(클리어율은 1위 팀 17% → 45% 등 표본 60판 변동 포함). 그웬 포함 팀(진행도 0.70)·프로페서M 포함 팀(0.79)은 규칙과 무관하게 1위 팀(0.98)보다 낮음. 미검증: 영상 대조, 그웬 추가 발동의 실제 attackType, 소환체 취급. (→ 그웬 추가 발동은 11/02 밤 BI_ENFORCE 로 확인, 영상·소환체 카운트는 남음)
- 시뮬 표(`guild_sim.json`) 재생성 755초. 시험: `tests/guild_search_test.js`(9), `guild_bfb_test.py`(`test_count_all_casts`), `guild_defense_test.py`(`test_search_excluded`), e2e `test_guild_search`(탐색 크기만 줄여 실제 작업자로 끝까지).
- **배포 완료(2026-11-02)**: `main` 39052c9 푸시, Pages 빌드 성공. (→ 현재 main 5cd0b75 원격 일치, Pages HTML도 로컬 index.html과 일치 확인)
- **남은 일(우선순위 순)**:
  1. **협공 자동 배제를 시뮬레이터가 조합을 보고 하도록**(사용자 지적): 지금은 스킬 문구 «협공» + 직접 지정 `excludeKeys`(그웬)뿐이라 장비로 붙는 협공·조합에 따른 발생 여부를 못 봄 → 시뮬 결과에 협공·강제 협공·추가 발동·잠재력(`via=coop/forced_coop/trigger/potential`) 시전 횟수를 싣고 예선에서 발생한 팀을 거름. (→ f18de32에서 구현 완료, 5cd0b75에서 전달 경로 시험 보강)
  2. **특수 잠재력으로 기본기가 같이 나가는 경우**(사용자 지적): 엔진 `random_ally_basic`(`mc.py` 2931, `via='potential'`), 클라 잠재력 40401~40408 이 25% 확률로 무작위 아군 기본기 추가 시전. 어느 구원자 것인지 미확인(`SE_TEMPLET_POTEN`·`BUFF_TEMPLET` BI_POTEN_PASSIVE_40401x 추적). 위 1번에 포함 + 질투의 시선 카운트에 들어가는지 코드 확인. (→ HISTORY 11/01 협공 절에서 공용 잠재력·조건·쿨·EnforceAttack·카운트 확인 완료)
  3. 영상으로 선택 효과·점수식·질투의 시선 카운트(협공·추가 발동 포함) 검증, 정실 어필 시점 대조 → 엔진 보정(편성 찾기 1위 편성으로 1판 촬영 권장). (→ 점수식은 11/01 영상 1판으로 확인, 다른 규칙 영상 대조는 남음)
  4. 저사양 PC 소요 시간 측정/`minPowerRatio` 상향 선택지/예상 시간 표시(24코어 5분 20초).
  5. 아모라·스칼렛 딜 분배 차이 원인(실측 42만·13만 vs 시뮬 55만·7만). (→ 부케 귀속 수정·스칼렛 하이 스코어 구현 일치 확인 완료, 남은 분배 차이는 영상 대조 필요)
  6. 그웬 추가 발동의 실제 attackType(엔포스 예약인지), 소환체 카운트 취급. (→ 그웬은 11/02 밤 BI_ENFORCE 로 확인, 소환체 취급은 남음)
  7. 브레이크 스킬·서포터 직업을 추천 입력에 더 반영. (→ 서포터 직업별 지원 선별은 guild_search.js에 반영, 브레이크 스킬 입력은 남음)
  8. 시즌 갱신 준비: 다음 시즌 보스가 다르면 `guild_bfb.py` 새 보스 명세 교체, `search` 설정 재검토.
  9. 서부 탈환대 세레스(`ceres`, 스트라이커) 스킬 확인. 동명 구원자는 항상 키·부제로 구분.
  10. 선택 효과 차원을 시뮬 표(`guild_sim.json`)에 추가.

