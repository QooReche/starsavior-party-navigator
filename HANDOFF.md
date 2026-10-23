# 인수인계

갱신: 2026-10-24 대상 선택 해소(se_of 수정으로 적 601종·효과 줄 359, BI_ENFORCE 강제 추가 행동, NOT_SELF·IsHighDef 필터). 이전: 10/23 밤(장비 탐색 시작 쿨 연결, 서든데스 반영). 새 세션은 이 파일 → `README.md` 순으로 읽을 것. 과거 세션 기록은 [docs/HISTORY.md](docs/HISTORY.md)(원문 그대로 이동했음). / 2026-10-24(효과 미지원 잔여 해소 — 오르트로스 지속 턴 연장·타 대상 보정, 티리아 게이지 조건부 설정, 올베로스 등장 후·영웅의 혼 마커, 잊혀진 맹세 vs 속성, 맹약결속 마커, 큐브 확률 보정, 선제 방어). 이전: 10/23 밤(장비 탐색 시작 쿨 연결, 서든데스 반영). 새 세션은 이 파일 → `README.md` 순으로 읽을 것. 과거 세션 기록은 [docs/HISTORY.md](docs/HISTORY.md)(원문 그대로 이동했음).

## ▶ 게임 설치 PC 작업 결과 (2026-10-23 밤, 이 PC)

- **스킬 아이콘(완료, 푸시 b9d04d7)**: 스킬 표 `m_SkillIcon` 344개를 번들 `Data\eb\f771deb…bundle`(개별 Texture2D)에서 추출(스크립트 `AI\temp\partynavigator\scripts\skill_icons_*.py`, 패치로 번들 이름이 바뀌면 scan 부터), 128px 220개를 `assets/skill_icons/`, 맵 `data/skill_icons.json`(`tools/build_skill_icons.py --static`)로 화면 연결(스킬 카드·내 정보 상세). 224칸 전부 연결, 변형 스킬 4개는 일반 아이콘. README 에 비공식 팬 도구·게임 이미지 저작권 문구 추가. e2e 27개 중 26 통과, `test_load_no_errors` 1개는 이전 커밋에서도 실패(404 한 건, favicon 추정). e2e 실행은 `C:\build\partynavigator\venv-pw` + 래퍼 `AI\temp\partynavigator\scripts\run_e2e_chrome.py`(Chrome 채널).
- **잠재력 11011(완료)**: 카르멘 전용 고유 잠재력 「여유로운 응수」(획득처 아르카나 「유리창 너머의 밤 풍경」, 데이터북 `pot`). 게임 빌드 26155183(표 26105710 대비 표 148개 바이트 동일). 데이터북 4줄이 맞고 클라 표는 4번째 효과 1101104 가 레벨 행에 연결 누락(고아). 4번째 줄은 능력치 없는 표시용 마커 버프(110112)라 시뮬 영향 없음. **미해결**: 클라는 〈여유로운 응수〉를 카르멘이 공격하면 해제(`DC_ATTACK`)하는데 엔진은 지속 무한 → 반격 확률 100% 가 유지돼 반격 과다 가능(게임 확인 필요, 이 잠재력은 id 1011 카르멘만 해당).
- **큰 보스전/실측 대조(진행)**: 영상 판독·대조는 `docs/ingame_samples.md` 새 절(37-36r·37-36r2·17x-a·17x-b). 37-36(재점화 1단계, 에핀델·아세라·아모라·샤를): 실측 2판 모두 패배(TURN 25·23, 달성도 36%)로 시뮬 클리어 0% 와 일치, 합계 준 피해는 시뮬과 거의 같고(−0.5%) 받은 피해는 시뮬이 16% 적음. 구원자별 분배는 어긋남(에핀델 과다·샤를 행동 0회). 혹한의 습격 XVII(트리쉬·에데·에밀리 리더·그웬, 큐브 과부하 Lv5): 실측 1패 1승, 시뮬 클리어 100%(낙관), 합계·분배는 실측 범위 안, TURN 은 시뮬이 1.14~1.25배 김. 판독 노트 `AI\temp\partynavigator\work\video_3736\`·`video_17x\`. 그래서 **큰 보스전 경고 문구를 「시뮬이 실제와 다를 수 있음(편성에 따라 비관·거의 일치)」으로 수정**했음(푸시 8fec039). `--bs` 는 레벨 인자(`--bs 3`, 기본 5), Lv3·Lv5 결과 동일. 내 정보의 보유 브레이크 스킬은 `break_skills`(id 매핑 `myinfo_import.js` BREAK_IDS: 101 특이점 관측 Lv1·102 스타피어서 Lv3·103 큐브 과부하 Lv5·104 행성 정화 Lv3·105 차원 강습 Lv8, 사용자 최신본 10/23 08:47; 앱 목록 `pn.brk` 의 표시 순서와 id 순서가 달라 착각하지 말 것). 실제 장착: 37-36 영상 = 행성 정화 Lv3(편성 화면 배너 아이콘 대조, 사용자 확인), 혹한의 습격 영상 = 사이트 추천 큐브 과부하 Lv5. 37-36 샘플을 시뮬에 미장착으로 돌린 앞선 결과는 정정 재대조 중(`ingame_check.py` 샘플별 브레이크 스킬). 저장소 샘플(`static-data/samples/myinfo_2026-10-22.json`)에는 `break_skills` 가 없어 전투력이 영상보다 −0.3%.
- **샤를 행동 0회 원인(진행: 브랜치 `fix-any-turn-clock`, worktree `C:\build\partynavigator\wt_clock`)**: 보스 「만상의 사슬」이 거는 불협화음(속도 −100%, 「누군가 턴 종료 시 차감」)을 엔진이 효과 주인 행동 때만 차감(`mc.py:345·918-934`) → 속도 −100% 유닛이 영구 정지. 「누군가 턴 종료」 계열 전반(속도 감소 등)에 일반 문제, 공허조율자 14개 스테이지 이상 영향 가능. 수정안: 해당 효과를 `any_turn` 시계로 표시하고 `Battle.act` 끝에서 양 진영 차감. 결과는 브랜치 커밋과 이 파일 다음 갱신에서 확인(병합은 사용자 검토 후).
- 남은 것: 1) 영상 추가분은 `SAMPLES` 에 한 줄 + `docs/ingame_samples.md` 절. 2) 브레이크 스킬 종류·레벨을 사용자에게 받으면 37-36 샘플(영상에서 Lv.3, 큐브 과부하/특이점 관측 불명) 보정. 3) 최신 내 정보 파일(break_skills 포함)을 `static-data/samples/` 에 두면 대조 정확도 상승(계정 자료, 비공개 저장소만).

### 2026-10-23 밤 마감 상태 (다른 PC 에서 이어서 검증)
- **샤를 수정 브랜치 `fix-any-turn-clock`(커밋 e3f4812, 푸시했으나 main 병합 안 함)**: `BUFF_TEMPLET.GlobalTurnCounting`(942개 중 true 19개, 「누군가 턴 종료」 설명 10개 전부 true)을 근거로 해당 효과를 `any_turn` 시계로 처리(`mc.py` `_is_any_turn`·`_tick_any_turn`, 규칙 `mc.any_turn_clock` 기본 true, 문서 `docs/any_turn_clock.md`, 시험 `tests/any_turn_clock_test.py` 6개 통과, 골든 불변). 37-36 에서 샤를 행동 0 → 1.84회(실측 3회), 준 피해 합 374,896 → 388,795(실측 378,366), 받은 피해는 약 322k(실측 386k)로 여전히 낮음. 속도 감소(2턴, 표상 GlobalTurnCounting=false)가 남아 첫 행동이 TURN 19(실측 16). 간이 계수 재맞춤으로 `data/quick.json`·`sim/manifest.json`·`tests/fixtures/reuse_baseline.json` 이 바뀜(일치율 0.922 → 0.924). **미검증: e2e 27개, 실제 게임 규칙과의 일치. 병합 전에 e2e 와 사이트 추천 결과 변화를 확인할 것.** 작업 폴더(`C:\build\partynavigator\wt_clock`)는 이 PC 전용 — 다른 PC 에서는 `git fetch` 후 `git worktree add ... origin/fix-any-turn-clock`.
- **혹한의 습격(장비 탐색)에서 시뮬이 낙관적**: XVII(1승 1패)는 시뮬 100%, XVIII(2패)는 92%. 전체 행동 수가 TURN 의 1.1~1.28배, 딜러(아모라·그웬) 준 피해 과대, 받은 피해 과소. 큐브 과부하 미장착일 때가 실측에 더 가까움(XVIII 33% vs 장착 92%). 엔진 출력에 큐브 과부하 회복이 0 으로 잡히나 실측은 아군 HP +7,936(아모라 확인, 약 5턴 지속 카운트다운 5→1, 「치트 매트릭스가 개방되었습니다」). **브레이크 스킬 5종 클라 표 조사 완료(노트 비공개 저장소 `analysis/ingame_2026-10-23/notes/break_skills/notes_break.md`)**: 5종 모두 클라 표에 완전 정의(표만으로 엔진 반영 가능, 데이터북에는 없음). 경로 `ORBITAL_ARRAY_TEMPLET` → 피해 `DAMAGE_TEMPLET.AllyAllAtkFactor`·회복 `HEAL_TEMPLET.AllyAllHpFactor` → 영역 `ORBITAL_DOMAIN_TEMPLET.CharmList` → `BATTLE_EFFECT_TEMPLET`, 레벨 `ORBITAL_LEVEL_GROUP_TEMPLET`, 효과 `SE_TEMPLET_ORBITAL_ARRAY`. 공통 쿨 8·발동 포인트 3·영역 지속 5. 101 특이점 관측 ATK 70%·노바 4·영역 공·방 +20%, 102 스타피어서 ATK 50%·아군 전체 게이지 +20%·영역 치확·치피 +10, 103 큐브 과부하 HP 2% 회복·오메가 프로토콜 2턴(공격력·효과적중 +15%)·영역 속도 +10(디펜더·서포터 +10 추가), 104 행성 정화 ATK 100%·영역 강인도 피해 +1·스킬 사용 후 노바 +1, 105 차원 강습 ATK 50%·노바 4·영역 공격력 +15%·강인도 피해 +1. 큐브 과부하 회복 계수는 실측과 일치(18x-b 팀 최종 HP 합 317,390 × 2.5% = 7,934.75 vs 실측 +7,936). 「행성 정화 자료 상충」은 appmedia(강인도 피해 +1·노바 +1, 계수 비공개)와 starsavior-db(미출시, 공격력 +10%·방어력 감소)의 충돌이었고 클라 표는 appmedia 쪽이 맞음. **엔진 차이**: 영역 지속이 표는 5인데 엔진은 4(아군 유닛 턴마다 -1) — 영상의 5→1 카운트다운(T22~T26)은 표와 일치, 전역 턴 시계(`global_turns`)로 통일 권장; 행성 정화 미등록(`mc.break_skills` 에 추가 + 「영역 보유자가 스킬 사용 뒤 노바 +1」 기능 필요). **18x 낙관의 원인은 큐브 정의로는 설명되지 않음** — 시뮬은 보스 브레이크 2.0회·큐브 2.0회, 실측은 각 1회뿐이라 브레이크 빈도 쪽이 유력. 표로 확정 안 되는 것: 스타피어서 게이지 +20% 가 발동자 포함인지, 쿨 단위, 노바 +1 이 일반 스킬에도 붙는지, 영역 재발동 갱신 규칙(영상 실측 필요).
- **성간 회랑 FLOOR 355 Lv2237**: 프로페서M 리더 판 2패 판독(비공개 저장소 노트). 사용자가 카르멘 리더(사이트 추천 그대로)로 다시 찍어 올 예정 — 도착하면 `SAMPLES` 에 `corr-*` 로 추가(브레이크 스킬 스타피어서 Lv3, 엔진 지원 여부 확인). 카르멘은 탱커·힐러(준 피해 4% 안팎, 파티 회복의 82~89%). 「여유로운 응수」 라벨은 영상에 안 보임.
- **푸시된 것(2026-10-23 밤)**: 공개 저장소 main(스킬 아이콘 220개 포함 `assets/skill_icons/`, README 면책, 샘플·문서)과 브랜치 `fix-any-turn-clock`. 비공개 `starsavior-static-data`(5aea947): `samples/myinfo_2026-10-23.json`, `analysis/ingame_2026-10-23/`(영상 판독 노트·조사 노트, README 에 목록), `tools/ingame/`(아이콘 추출·원인 추적 스크립트).
- **다른 PC 에서 먼저 할 일**: ① 두 저장소 `git pull`(공개 main + `git fetch` 로 브랜치) ② `static-data/samples/myinfo_2026-10-23.json` 로 `python -X utf8 -I tools/ingame_check.py --runs 100 --only <샘플> --bs-real --myinfo <경로>` 재실행 ③ e2e: `E:\AI_mk2\venv-pw` 또는 이 PC 방식(venv + Chrome 채널, `test_load_no_errors` 는 favicon 404 로 이전부터 실패) ④ 브랜치 병합 여부 결정. 이 PC 의 임시물: `C:\build\partynavigator\venv-extract`(179MB)·`venv-pw`·`wt_clock`.
- 남은 일 요약: 큐브 과부하/행성 정화/스타피어서 모델 점검, 37-36 첫 행동 시점(속도 감소 차감), 카르멘 「여유로운 응수」 해제 조건(`DC_ATTACK` 클라 vs 엔진 무한 지속, 게임 확인 필요), 큰 보스전 원인 미해결(37-3), favicon 404.

(원래 요청 원문, 참고)

1. **큰 보스전 녹화 실측** — 시뮬이 큰 보스전에서 아군 피해를 약 1.5~2배 적게 냄(37-3 등). 원인 후보 = 구원자별 시전 횟수·반응·행동 순서.
   - 찍을 것: 작전 큰 보스 스테이지 1곳(10/22 밸런스 변경 7곳·토벌은 제외 — 예: 37-3) 같은 편성으로 오토 1판 전체 녹화 + 결과 화면(TURN·준/받은 피해·구원자별 피해) + 편성 화면 능력치.
   - 넣을 곳: `tools/ingame_check.py` SAMPLES 에 한 줄(형식은 그 위 주석: 콘텐츠, 탭|스테이지, 화면 카드 순서[후열1, 전열1, 전열2, 후열2], 리더, 파티 전투력, 재점화 단계, 준 피해, 받은 피해, TURN, 결과), 영상 판독(구원자별 시전·반응·보스 행동 순서)은 `docs/ingame_samples.md` 새 절, 대조 결과는 `docs/ally_damage_audit.md`.
   - 대조: `python -X utf8 -I tools/ingame_check.py --runs 100 --only <이름>`(내 정보 파일이 있으면 `--myinfo <경로>`).
   - 참고: 10/24 에 브레이크 스킬 피해 x1.85·레벨 가산을 넣었으므로 브레이크 스킬 장착 여부·레벨도 기록(`--bs` 옵션은 큐브 과부하 Lv5 고정 — 다른 스킬이면 알려 줄 것).
2. **스킬별 게임 아이콘** — 지금 화면은 종류(기본기·특수기·궁극기·패시브) 아이콘. 게임 클라이언트 자원에서 구원자 스킬 아이콘(SKILL_TEMPLET 의 아이콘 이름)을 뽑아 오면 화면에 연결함. 제3자 DB 경로 규칙은 미확인이라 클라 추출이 확실함. 뽑은 그림은 `assets/` 아래 새 폴더, 이름 = 스킬 아이콘 이름.
3. **잠재력 11011 레벨 1 재확인** — 데이터북 설명 4줄 vs 클라 표(빌드 26105710) 효과 3개 불일치, 이전 계수 보존 중. 새 빌드에서 표를 다시 뽑은 뒤 `python -X utf8 -I tools/build_myinfo_combat.py --static <비공개 저장소>` 가 불일치를 출력하는지 확인, 게임 화면의 그 잠재력 설명(레벨 1 효과 줄 수)을 캡처.

## ▶ 이어서 할 것 (2026-10-23 저녁 갱신 — 위·아래 「10/24」 표기는 실제로는 10/23 작업분)

- (완료) r4-tail 마무리·병합(54c8a0d, 병합 19bda2f): 레벨업 추가 행 자동 지정(힐데·웨딩 에핀델 궁극기 — 데이터북 L 전 레벨 그룹 줄을 기본 묶음 규칙으로 등록, 엔진은 원문으로 조회하므로 내 정보 스킬 레벨 줄도 잡힘), 줄 수 불일치 3스킬(SEGroupID 만 다른 같은 SE 행 합침), 웨딩 에핀델 궁극기(조건 안 괄호 파싱), 프로페서M IsNotUnableToAct(해독본 26105710: 사망·기절·수면 제외), 피해 결과 조건 시험 ctx 주입식. 자동 지정 줄 24→36, 제외 보고 0. codex 리뷰 결함 0.
- 남은 범위 밖 사안: 데이터북에 기본·개화(SSR) 두 기록이 있는 8명(1501·1502·1506~1511)은 빌더가 id 당 마지막 기록(개화)으로 짝지음 — 게임 표 유닛은 하나이고 스킬은 개화 기록과 맞음. 기본형 베라 궁극기 「특급 배송」 자동 지정 줄은 게임 표 대응 행이 없어 설명문 근사로 남음.
- 계수 재맞춤(10/23 저녁, 3차+r4 뒤): 전체 일치(가중) 91.3%(base 89.5%, 코스모 스테이지 보정 후 94.0% — 10곳, 플래시 95.5% — 17곳). 작전 큰 보스 공통 배수 검증 개선 0 이라 미적용.
- 그 밖에 남은 미지원은 전수 스캔 기준 0(스테이지 support_report·실행 중 미지원) — 확인은 `local/runtime_unsup_*.json` 과 같은 방식으로.
- 추천 재사용 기준값(`tests/fixtures/reuse_baseline.json`) 재생성 방법: 리팩터 전 코드(d6e0818 의 party_template·index·quick.js) + 새 `data/quick.json` 으로 `tools/capture_reuse.js`(buildCands 는 topParties 사용). 계수가 바뀔 때마다. d6e0818 엔 capture_reuse.js 가 없으므로 현재 것을 복사해 3곳만 옛 API 로: buildCands `rankAll(cands,defPen).slice(0,10)`→`topParties(cands,defPen,10)`, 호출 `quickRank(rankAll(cands,defPen),qi)`→`quickRank(cands,defPen,qi)`. 대조군 = 직전 quick.json 으로 뽑아 HEAD 기준값과 바이트 일치 확인(10/23 저녁 일치, 바뀐 것은 cosmo_24 qr·jp 뿐).

## ▶ 다음 세션 시작 (2026-10-23 정리)

시작 멘트 예: 「여정 네비게이터 이어서 — HANDOFF 다음 세션 남은 일 1번(큰 보스전 녹화 대조)부터」

시작 절차
1. 세 저장소 최신 받기: `E:\AI_mk2\starsavior-party-navigator`(main), `E:\AI_mk2\starsavior-static-data`, `E:\AI_mk2\starsavior-packet-ref` 에서 `git pull --ff-only`. 작업 사본 `E:\AI_mk2\pn-community`(worktree, 브랜치 community-removal)는 `git merge --ff-only origin/main`.
2. 시험 기준선: 단위 `tests/*_test.py`·`node tests/*.js`·`tests/golden_check.py`(STARSAVIOR_STATIC 지정), 브라우저 `E:\AI_mk2\venv-pw\Scripts\python -X utf8 tests\e2e\test_page.py`(27개, 약 4~5분). 10/23 기준 전부 통과.
3. ⚠ 10/22 밸런스 변경 스테이지(작전 최종 보스 26·27·28·30·35·36·37-36, 토벌)의 패치 전 실측·공략 영상은 참조 금지(사용자 지시). 유효한 실측: 37-2~37-5(10/21), 혹한의 습격 17·17e·17r(10/23).

남은 일(권하는 순서) — 모두 이 PC 에서 가능(자료는 비공개 저장소에 있음)
1. (10/23 밤 완료) 장비 탐색 시작 쿨 연결: 후보를 `tools/build_foe_spawn.py` `candidates()` 로 옮김, `foe_spawn.json` 에 60곳 연결(등급 규칙과 같은 값이라 시뮬 변화 없음), `foe_auto.json` 바이트 동일.
   (10/23 밤 완료) 서든데스: `tools/build_sudden_death.py` → `data/sudden_death.json`, 규칙 `mc.sudden_death`(data, 옛 동작 off). 원본 표 기준 작전 일반 1,267·작전 어려움 350·회랑 1,900곳(비공개 요약의 301~304 보다 넓음). 전역 턴 +1 직후 아군 전원에 최대 생명력(전투 전 최종값에 곱함)·방어력·주는 회복량·주는 보호막량 감소. 실측 7판·계수 영향 거의 없음(시뮬 전투가 대부분 전역 턴 100 전에 끝남). 상세 `docs/enemy_cond_audit.md` 끝 절. (10/24 버프 생명력%도 최대 생명력에 반영 — 아래 3번.)
2. **큰 보스전 아군 피해 부족(37-3 약 1.5배)의 원인 찾기 — 녹화 필요**: 대상·스킬 규칙·보스 수치·반격·턴 제한은 원인이 아니었음. 남은 후보 = 같은 편성 큰 보스전 녹화로 구원자별 시전 횟수·반응 대조(`docs/ally_damage_audit.md`).
2-1. (10/23 완료) 반격·턴 제한 단위·보스 수치 기준선: 규칙 `mc.revenge`(on, 반격 적 304 스테이지, 표본 클리어 평균 −23%p)·`mc.turn_limit_unit`(actions, 코스모 50 = 전체 행동 50번). 보스 1,151곳 수치는 엔진과 일치(다른 7곳은 패치 뒤 값이 엔진 쪽). 상세 `docs/enemy_cond_audit.md` 끝 절.
3. (10/23 완료) 적 스킬별 자동 규칙·효과 줄 자동 대상: `tools/build_foe_auto.py` → `data/foe_auto.json`, 규칙 `mc.foe_auto`(data). 적 414종·스킬 규칙 398·효과 줄 167. 혹한의 습격 3판 모두 실측 쪽으로(17r 클리어 98→88%). (10/24) 코스모·플래시·일일 던전 이름 연결(적 473종, 연결 없음 5스테이지), 짝짓기 실패 0, 적의 아군 대상 줄·구원자 효과 줄 15개(`mc.ally_auto_lines`)도 게임 규칙, 반응 스킬 대기열(`mc.reaction_timing`)·버프 최대 생명력(`mc.buff_maxhp`). 남은 것: `EnforceAutoTargetId`(강제 추가 행동) 미사용, 「자신 제외 1명」·`IsHighDef`·레벨업 추가 행 자동 지정은 근사. 상세 `docs/enemy_cond_audit.md` 끝 절.
4. (2번에 포함, 10/23 완료) 턴 제한 단위.
5. (10/23 완료) 반응·대상 선택 규칙: 게임 자동 전투 규칙 1(구원자)·1001(적)·구원자 스킬별 규칙(`tools/build_auto_skill.py` → `data/auto_skill.json`, 규칙 `mc.ally_auto_target`·`enemy_auto_target`·`auto_skill`)을 기본으로. 회복 스킬 8개는 75% 이하 아군이 있을 때만, 바니 샤를 궁극기는 점화 5스택일 때만. 실측 대조: 37-2·37-4 는 가까워지고 혹한의 습격 17r(실제 패배)은 클리어 72→98% 로 더 낙관적 — 코드 근거라 실측에 맞추지 않았음. 상세 `docs/ally_damage_audit.md` 끝 절.
6. 그 밖(10/24 진행분): 반격·반응 스킬 순서 게임과 맞춤, 〈특수기 쿨타임 초기화〉·〈즉시 피해〉(자폭)·브레이크 스킬 레벨·브레이크 피해 x1.85 반영(상세 `docs/enemy_cond_audit.md` 끝 절), 크로넷 자동 조건(〈태엽 가속〉 보유 시에만 폭탄)은 일일 던전 이름 연결로 들어감, 건틀렛 13열 = 관문 이력(전투 무관)으로 확정, 전투력 PP 항은 내 정보 경로에서 이미 게임 공식과 같음(내 정보 없는 standard 빌드만 PP 0 근사 — 이 앱은 내 정보 전용이라 영향 작음).
   (10/24 완료) 적 트리거(반응) 스킬 5종: `tools/build_foe_react.py` → `data/foe_react.json`, 규칙 `mc.foe_react`(data, 옛 동작 off). 맹약 회수·앙코르·소거·태엽 폭탄 기폭·월영, 적 16종 16규칙. 작전 어려움 35-10 클리어 0%←82%, 달 회랑 450 95%←100%, 괴리의 표상 1단계 98%←100%(40판, seed 7). 상세 `docs/enemy_cond_audit.md` 끝 절.
   남은 것(조사 끝, 구현 전):
   - (10/24 완료) 소환(올베로스 하수인·티리아 인형·페르세스 고대 병졸, 26곳): `tools/build_foe_summon.py` → `data/foe_summon.json`, 규칙 `mc.summon`(data, 옛 off). SUMMON_TEMPLET 칸·쿨 플래그, BattleScript SpawnPosIndex 연결 26/26곳. 티리아 1단계 82→100%(off), 2단계 진행 0.53→0.66(off). 상세 `docs/enemy_cond_audit.md` 끝 절.
   - (10/24 완료) 적 반응 스킬 시점·조건 어휘 확장: `tools/build_foe_react.py` + `mc._check_foe_react` 에 AfterAllyAttack·OnMyAttack·AllyEffectiveHit 시점, DamageResultType·IncludeSelf·TargetNegativeBuff 등 조건, NSTT_REACT_ALLY_TARGET 대상, special/hyper 스킬 인덱스 추가. 규칙 `mc.foe_react_timing`(extended, 옛 legacy). 현재 데이터북 적에 해당 시점 규칙 없어 시뮬 변화 0(WHITEDRAGON·HAPPY68 MAINSTORY·VAGABOND EVENT 는 게임 유닛이 있으나 데이터북 미연결). 상세 `docs/enemy_cond_audit.md` 끝 절.
   - (10/24 완료) 효과 미지원 잔여 해소(7항목): 오르트로스 효과 지속 턴 +1·타 대상 보정, 티리아 게이지 조건부 설정, 올베로스 등장 후·영웅의 혼 마커, 잊혀진 맹세 vs 속성, 맹약결속 마커, 큐브 확률 보정, 선제 방어 확률. 규칙 4개(`mc.effect_dur_extend`·`gauge_conditional`·`local_vs_element`·`preemptive_defense`). 마무리: 힐데 다중 상시 능력치 파싱(쉼표 분리 `perm_multi`), 맹약결속 마커 수집(foe_react 리스트형 조건 스캔), 등장 후 속도 보정 _meaning_gap 통과, 선제 방어 공격자 reduce(고립 -50%). 전수 스캔 3,690곳 effect/trigger 보고 0. 상세 `docs/enemy_cond_audit.md` 끝 절.
   - 코드 정리: 4번 규칙 설명값 구분(enemy_skill_ai·caster_death·wave_carry·break_skill_model 은 코드가 안 읽음 — 구분만, legacy 분기 삭제는 사용자 결정) → 1번 MC 의미 해석 캐시(기본값 고정 해시 먼저).
   - 적 조건 판정 `enemy_hit_buff_cmp` 재선택(실측 더 쌓이면). 게임 PC 필요: 스킬별 아이콘, 잠재력 11011/1 재확인.

엔진 규칙을 바꾸면: `tools/build_simpack.py` → `tools/gen_quick_calib.py --per-content 400 --opboss`(약 20분) → `tools/calibrate_quick.py --write` → `build_party_html.py index.html` → 시험 → codex 리뷰(래퍼 `codex-review.ps1`) → 커밋·푸시(QooReche noreply).

## 위치

- 저장소: https://github.com/QooReche/starsavior-party-navigator (공개, Pages: https://QooReche.github.io/starsavior-party-navigator/)
- 로컬: `E:\AI_mk2\starsavior-party-navigator`. 페이지 `index.html` 은 `python -X utf8 -I build_party_html.py index.html` 로 만들어 커밋함.
- 비공개 게임 표: `QooReche/starsavior-static-data`(로컬 `E:\AI_mk2\starsavior-static-data`). 원본 표·계정 자료는 공개 저장소에 복사하지 않음(가공 수치만). 경로는 `--static` → 환경변수 `STARSAVIOR_STATIC` 순으로 받음.
- 내 정보 추출 도구: 공개 `QooReche/starsavior-myinfo`, 소스는 비공개 `QooReche/starsavior-packet-ref`.
- 커밋은 QooReche noreply 로만.

## 현재 상태

- 화면: 추천 파티(내 정보 기준, 예선·본선 시뮬이 끝난 뒤 결과), 내 정보 탭(캐릭터 격자 + 상세 팝업), 추천 카드 얼굴 → 스킬 카드, 공유 링크(내 정보 포함 가능).
- 내 정보 → 최종 능력치는 게임 화면과 일치함(`myinfo_stats.py` = `myinfo_stats.js`). 시뮬은 같은 값 + 잠재력 전투 효과 + 실제 스킬 레벨을 씀.
- 결과 화면 TURN = 적 포함 전체 행동 수(전역 턴). 영상 판독과 해독 코드로 확인했음.
- 빠른 계산 계수 재맞춤(10/23 저녁 3차: 91.3%, 위 「이어서 할 것」) (10/24 2차, 위 반영 + 적 트리거 스킬·소환·해석 캐시 뒤): 판정 일치 91.6%(base 89.5%, 코스모 95.8%, 플래시 95.5%, 스테이지 보정 후 — 코스모 보정 12곳), 코스모 공통 계수 A 1.0→1.3. (1차 91.5%) (10/23 저녁: 91.8%) 작전 큰 보스 공통 배수는 검증 개선 0(0.842→0.842)이라 미적용(`calibrate_quick.py` OPBOSS_GAIN 1%p 문턱).
- 10/22 리뷰 반영 내역: [docs/cleanup_review.md](docs/cleanup_review.md).

## 10/22 밤 개편 (브랜치 `community-removal`, worktree `E:/AI_mk2/pn-community`)
- **커뮤니티 자료 제거**: 커뮤니티 편성 표시·CLI 「뉴비 편성 유형」, 추천 점수의 커뮤니티 티어·딜러 최소 2명 감점·웨르멘+왈세라 짝 예외 삭제(티어 배지는 표시만). 사용자 판단: 「티어도 사람 체감, 시뮬레이터니까 어떤 조합이 깨는지가 유효」.
- **후보 풀**: 개인 점수 상위 14 → 역할별 선발 최대 24명(단일·광역 화력·아군 피해 증가·개인 점수 상위 + 연계 강한 쌍 둘 다). JS `partyPool` = Python `party_pool`. 전원(56명) 풀이면 재계산 4.5~10초라 상한.
- **시뮬이 끝난 뒤 결과 표시**: 「추천 편성 보기」 → 진행 화면(단계·진행률·취소)만 → 예선(빠른 계산 상위 80 + 근사 점수 상위 40 = 120팀 8판 → 상위 20팀 32판, 상한 60초) → 본선(상위 3~9팀 100판) → 결과. 근사 판정은 화면에 안 보임(「시뮬 전」). 1파티 콘텐츠만 예선(2파티는 함께 고르기 JOINT 유지). 조사 근거: SimulationCraft/Raidbots 단계식(Smart Sim), successive halving.
- **적 진척도**(`outcome.progress`, `Battle.progress()`): 끝낸 웨이브 + 현재 웨이브 깎은 체력 비율. 0% 팀끼리 순위·「적 체력 N% 깎음」 표시.
- **큰 보스전 경고(B)**: 작전에서 보스 생명력 ≥ 권장 전투력 1.2배(비관 3곳 1.49~1.54배, 맞은 곳 0.75배). 작전 1,268 중 302 스테이지.
- **적 패시브 조건 점검(2026-10-23)**: 「강화/약화 효과 개수」 조건이 개수 대상 없이 0 으로 읽히던 오류 4종을 때린 상대 한 명 기준으로 고침(`mc.py` `cond_ok`), 규칙 `enemy_hit_buff_cmp`(기본 `le`, 실측 4판 근거로 임시 선택 — 프레이 팀 3승·추천 팀 1패를 동시에 맞추는 판정은 없었음). 전체 점검 결과·남은 미지원 목록(반격 확률·적 자동 지정·소환 등)은 `docs/enemy_cond_audit.md`. 실측 샘플 `17`·`17e`·`17r` 는 `tools/ingame_check.py`, 시험 `tests/enemy_cond_test.py`. 새 실측이 생기면 판정을 다시 고를 것.
- **턴 표시(2026-10-23)**: 결과는 「게임 TURN 약 N (ttk M턴)」 — N 은 게임 결과 화면 TURN(전체 행동 수=아군+적, 클리어 판 중앙값 `outcome.ttk_actions_median`)으로 바꿈. 모델 턴 `ttk`(100틱)는 순위·비교용으로 그대로. 실측 대조(`tools/ingame_check.py`, 샘플 `17` 추가): 시뮬 행동 수 ÷ 실제 TURN = 1.10(장비 탐색 혹한의 습격 XVII)·1.5(37-4) 등 0.8~1.7배. 턴 제한(`turn_limit`)은 아직 모델 턴 기준 — 제한 초과가 실패인 콘텐츠는 단위 불일치 점검 필요. 이 콘텐츠(`equip`)는 내 정보 규칙이 없어 평균 육성 가정으로 계산됨.
- **보유 브레이크 스킬(2026-10-23)**: 내 정보 `break_skills:[{id,level}]`(`ud[31]`)을 읽어 보유 칸 자동 체크·Lv 표시(`MyInfoImport.mapBreak`), 파일에 없으면 직접 선택. 레벨은 시뮬 요청에 넘기지만 엔진은 반영 안 함(효과 +1~5%, 해석 불명). 게임 화면 레벨과 일치 확인됨.
- **내 정보 전용**: 내 정보 없으면 계산 안 함(안내 카드). 평균 육성·내 전투력·구원자별 전투력·「내 구원자」 서랍 삭제 → 불러오기·만드는 방법 팝업. 보유 = 내 정보 − 「추천」 끈 구원자(LS `excl`). 브레이크 보유 선택은 내 정보 탭. 링크 복사 「내 정보 포함」 = `#shared=`(gzip+base64url, 받는 쪽 저장 안 함).
- **내 정보 탭**: 캐릭터 선택창 격자 + 상세 팝업(능력치 8칸·스킬 레벨·장비 6칸·여정 5칸·잠재력, 아이콘 = Lucide ISC 인라인 `ui_shared.js`). 게임 톤(차콜 + 금선).
- 측정(이 PC, 브라우저): 시뮬 1판 ≈ 30ms(실전 후보 팀). 37-3 평균 육성: 예선 55초 + 본선 12초, 1~3안 88/83/76%.

## 남은 일
- 스킬별 실제 게임 아이콘: 지금은 종류(기본기·특수기·궁극기·패시브) 아이콘. 게임 설치 PC 에서 스킬 아이콘 추출 필요(제3자 DB 경로 규칙 미확인).
- (10/23 완료) 예선 병렬화: 작업자 최대 3개(코어−1·메모리 상한), 37-3 예선 9.5→5.2초. 공통 난수(`rng_streams`, 아군·적 난수 흐름 분리)는 예선에만 — 100판 정답과 순위 일치 0.821→0.838. 본선은 기본(꺼짐)이라 파이썬·골든과 같음.
- 엔진 대조: `SKILL_CONDITION_TEMPLET`·`AUTO_SKILL_*` 로 반응·대상 선택 규칙(큰 보스전 아군 피해 과소·적 자동 지정 미지원 후보), 반격 확률 미지원(약 390 스테이지), 보스 수치 기준선(`static-data/analysis/baseline`) 대조, 턴 제한 단위(모델 턴 vs 게임 TURN). 시작 쿨 플래그는 10/23 반영(아래).
- (10/23 완료) 기존 실패 시험 3개 정리. 잠재력 11011 레벨 1: 데이터북 설명 4줄 vs 클라 표(빌드 26105710) 효과 3개 — 이전 계수 보존 중. 다음 표 재추출 때 다시 확인(`tools/build_myinfo_combat.py` 가 불일치를 출력).

## 화면 동작 변경 (2026-10-22, 사용자 제보: 37-36 추천대로 했는데 패배)
- 원인: 시뮬 전에는 빠른 근사의 「깰만함」이 크게 보였음(37-36 실제 편성은 시뮬 클리어 0%). 근사는 콘텐츠 공통 계수라 작전 최종 보스급(스테이지 보정 `sm` 이 코스모·플래시에만 있음)에서 낙관적임. 실측은 `docs/ingame_samples.md` 2026-10-22 37-36 항목.
- 변경(`party_template.html`): 계산은 「추천 편성 보기」 버튼을 눌렀을 때만(조건·내 구원자를 바꿔도 계산·시뮬 안 돎, 바꾸면 안내로 복귀), 버튼은 서랍을 닫고 현재 조건으로 계산+시뮬 자동 실행. 시뮬 전 행은 점선 「근사」 배지·경고, 시뮬 후에는 시뮬 기준 배지. 탭(추천 파티/내 정보)과 링크 복사는 필터 위 한 줄. 300판 옵션 삭제(100판만). 내 정보 탭에서는 필터 숨김.
- 자동 시험·공유 링크: 주소에 `?auto=1` 이 있거나 공유 링크(`c=`)로 열면 예전처럼 바로 계산. E2E(`tests/e2e/test_page.py`)는 `?auto=1` 로 열고 `test_press_to_compute` 를 추가했으나 **이 PC 에 Playwright 가 없어 미실행**(브라우저 수동 확인으로 대신함). 제한 없는 환경에서 실행 필요.
- 시뮬이 보인 팀이 모두 클리어 50% 미만이면 클리어하는 팀이 나오거나 9팀이 될 때까지 다음 3팀을 자동 시뮬한다(`simAutoKick`). 전 구원자 보유·권장 100% 육성에서도 37-36 은 9팀 모두 0%(27초).
- **시뮬은 큰 보스전에서 비관적**: 준÷받은 실측/시뮬 = 36-36 1.88/0.90(2.1배), 37-3 1.82/0.91(2.0배), 37-36 0.50/0.28(1.8배) — 세 판 모두 약 2배로 일정. 그래서 「시뮬 0%」도 「불가능」이 아님(권장 100% 팀이 전부 0%로 나옴). 클라 `DamageScale 18500`(=BASE_MULT 1.85)·`DefenceConst 3000` 은 엔진 값과 일치하므로 원인은 그 밖(아군 행동 수·반응/연쇄·대상 선택 등, `docs/ally_damage_audit.md`). 아군 피해 배율을 실측에 맞추는 보정은 감사 원칙상 아직 안 했음(사용자 결정 필요).
- 남은 개선 후보: 작전 보스 스테이지의 근사 보정(`sm`)을 시뮬에 맞춰 추가(`calibrate_quick.py` 가 보스 콘텐츠 그룹만 처리함).

## 미해결

- 큰 보스전 비관: 36-36 준÷받은 1.09(실측 1.88), 37-3 1.13(실측 1.82), 시뮬 클리어 0%. 적 피해 속도는 맞고 아군 피해가 부족함. 필요한 증거 = 같은 편성 큰 보스전 녹화(행동 순서·구원자별 시전). 근거 `docs/ally_damage_audit.md`.
- (10/23 해결) 37-5 낙관: 적 시작 쿨을 배치 데이터로(`data/foe_spawn.json` ← `tools/build_foe_spawn.py --static`, 규칙 `mc.enemy_spawn`=data). 게임 코드: AllSkillAvailable 이면 전부 0, 아니면 전부 가득, Special/Hyper 는 그 스킬만 0. 배치 2만여 기 중 일반 적 A·보스 S 가 95%, 37-5 정예 2기는 A(궁극기도 0). 연결 3,553/3,690(권장 전투력·레벨·웨이브 일치, 작전은 데이터북 번호가 밀린 섹터가 있어 같은 섹터에서 찾음), 나머지는 등급 규칙. 실측 37-5 준÷받은 4.17: 옛 6.97 → 3.54. 실제로 쿨이 달라지는 스테이지 83곳. ⚠ 10/22 밸런스 변경 스테이지(작전 최종 보스 7곳·토벌)의 패치 전 실측·영상은 참조 금지 — `tools/ingame_check.py` PRE_PATCH(36-36).
- (10/23 반영) 10/22 패치: 데이터북 적 데이터 재수집(작전 최종 보스 7곳 공격력 하향·26-36 생명력 하향·27-36 패시브 1줄 변경 확인), 성장표 빌드 26105710(새 장비 세트 2·새 잠재력 11014, 삭제된 1060·11060 은 이전 값 보존), 파생 데이터·계수 재생성. 토벌·플래시 포인트·임무 턴 완화는 데이터북 반영분 그대로.
- 건틀렛 축복 미해석.

## 남은 것 (근거는 docs/cleanup_review.md)

- 추천 후보 평가 재사용(`buildCands`·`quickRank` 중복): 동점 순서·Python 동일성 고정 뒤.
- Cytoscape 지연 로드·설명 데이터 분리.

## 완료된 것 (2026-10-23, feat-rules)

- MC 규칙 설명값 구분: `rules/default.json` mc 4개 항목 `"kind":"note"`, `MC_NOTE_KEYS` 신설, 일관성 시험 6개. (커밋 a176872)
- MC 의미 해석 캐시: `Battle.semantic_cache` 런 간 공유, 결과 바이트 동일, 시험 8개. (커밋 a9dbdb4)

## 작업 방식

- 구현은 별도 worktree(`git worktree add -b <브랜치> E:/AI_mk2/pn-<이름> main`)에서 codex(`gpt-6-astra`, high)로, 검토는 래퍼 `codex-review.ps1`(읽기 전용).
- 시험: `tests/*_test.py`, `tests/golden_check.py`(골든 `--write` 금지), web/quick/shim_compat 는 `tests/run_workspace_test.py tests/<이름>.py` 경유, `node tests/*.js`, 브라우저 `E:\AI_mk2\venv-pw\Scripts\python -X utf8 tests\e2e\test_page.py`(27개).
- 엔진을 바꾸면 `tools/build_simpack.py` → 계수 재맞춤(`tools/gen_quick_calib.py --per-content 400` → `tools/calibrate_quick.py --write`, 약 15분) → e2e.
- 문서 문체: 존칭 없이 「했음·하기로 함」, 담백, 참고는 주소만.
