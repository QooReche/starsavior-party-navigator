# 인수인계

갱신 2026-11-10. 읽는 순서: 이 파일 → README.md → docs/DEVELOPMENT.md. AI 작업 규칙은 [AGENTS.md](AGENTS.md). 옛 기록은 [docs/HISTORY.md](docs/HISTORY.md).

## 현재 상태

- 11/10 밤 늦게: 육성 가이드 리뷰 반영 `cf7d316`과 코스모 탐색 R&D `412da89`를 `0c70ab4`에서 병합했음. Astra 2건·Opus 1~5 권고를 반영해 누락 팀 재평가·벤치 시간 보존·ETA 저장값 갱신·작은 풀 전수 경로를 보완했음. 기본 옵션 결과는 유지했음. 코스모 «빠른 탐색(실험)»은 기본 꺼짐, 단계 사이 워커 재사용은 기본 켜짐(`workerReuse.value=true`, legacy=false)임. 네이티브 전체 탐색은 작은 풀 1.24배·큰 풀 1.11배로 **2배 목표 미달**이며, 기본 변경만의 브라우저 전체 탐색 가속률은 미확인임. 상세 `docs/cosmo_speed_rd_1110.md`와 아래 밤 늦게 절.
- 11/10 심야 리뷰 3종 후속: 소스/고레벨 가상 슬롯 차단, 미지원 구원자 개별 제외, 옛 형식 항목별 육성 비교를 고쳤음. 현재 조건과 호환되는 기록만 우선순위에 쓰고 모바일은 결론·넣기/빼기·상위 5명 중심으로 바꿨음. 추출 도구 두 저장소의 null 슬롯도 처리했음. 다크 전용 유지, light 신설 지적은 기각했음. 아래 심야 절에 판정·검증 기록을 남김. `cf7d316`까지 푸시 완료했음.
- 11/10 심야: `9f33827`의 구원자별 실효 레벨과 육성 가이드 1단계를 `ca1e271`에서 병합했음. manifest 충돌은 빌더로 재생성했음. 목표 육성을 레벨·장비·스킬·공명·잠재력 묶음으로 통합하고 단일 항목 비교·임시 보정 표시·현재 슬롯 수 내 교환 추천을 추가했음. 비공개 자료는 읽기만 했으며 이후 `cf7d316`까지 푸시 완료했음. 상세는 아래 심야 절과 `docs/assumed_build_design.md`.
- 11/10 밤 리뷰 후속: R1 정화 legacy 시간선·R2 웨이브 게이지 독립성을 고쳤음. R3~R5 미확인 경계를 note에 구체화하고 R6 실제 standard 길방 시험을 추가했음. «guild_sim 미재계산» 지적은 a732566에서 이미 재계산했으므로 기각했음. 93d300f 대비 legacy 14사례 일치, a732566 대비 기본값 72판 결과 불변. 상세 `docs/review_followup_1110.md`.
- 11/10 밤 병합: `guild_bridal_kill_reset=client`, `wave_extra_turn=clear`, `turn_start_order=client`, `guard_skip_immune=client`, `buff_fresh_scope=client`, `break_gauge_actor=client`, `purify_nova_scope=all_casts`, `preemptive_reduce=client`, `omega_dispel=client`로 기본 전환했음. 근거가 불완전한 D 5개·E 2개는 옛 기본을 유지했음. 정본은 `battlesim/rules/default.json`, 상세는 아래 «11/10 밤» 절. 코스모 가속은 규칙·시드·후보·판 수를 바꾸지 않음. (→ 이후 11/10 밤 늦게 워커 재사용 기본 채택·대리 선별은 기본 꺼짐인 실험 옵션으로 추가)
- 11/10 오후 병합 기본값: `cosmo_hyper_true_target=self`, `damage_vampirism=client`, `cosmo_drain_category=marker`, `cosmo_speed_floor=true`, `variant_self_state=client`, `turn_unit_debuff_cond=client`, `auto_marker_lines=keep`, `shield_tick=turn_end`, `break_domain_revive=client`. `wave_carry`는 새 `client` 선택지를 넣고 기본/legacy `keep` 유지했음. 오전 `cond_count_bind=holding`, `cosmo_boss_barrier=client`, `stage_fx_target=allies`도 반영됨. 정본·근거는 `battlesim/rules/default.json`, 상세는 아래 «11/10 오후» 절.
- 근거 코드는 비공개 static-data `decompiled/`(디컴파일 빌드 26314877)임. 11/10 설치본이 **26429597**(11/05 갱신)인 것을 확인했고 DLL 5개 해시가 바뀌었으나 내용 비교 결과 **전투 로직 변화 없음**(식별자 재난독화만, 근거 줄 163건 이동 0, `decompiled/BUILD.md` 11/10 절). 표(`tables/`)는 11/10 에 26429597 로 다시 뽑아 덮어썼음(절 «2026-11-10»).
- 협공 기본값: `formula.COOP_CAP=1.0`, `opts.coop_trigger=basic_only`, `coop_single=true`, `coop_order=random_success`, `forced_coop_target=random`, `forced_coop_slot=shared`, `coop_dead_target=cancel`. 강제 효과 대상을 먼저 정하고 유효 강제 후보 중 균등 1명을 고름. 강제 후보가 없으면 일반 후보 전원 판정 후 성공자 중 균등 1명임. 단일 본대상 사망 시 협공을 취소함.
- 11/08 기본 전환: `enemy_leader=none`(적 리더 속도 +10 제거, legacy=boss, 절 «11/08 밤 틱 제외 조건» 안 «적 리더» 항목), `any_turn_source=table`(전체 턴 시계 버프를 표 `GlobalTurnCounting` 으로 판정, legacy=text, 절 «전체 턴 시계를 표 기준으로»).
- 11/05 기본 전환: `dot_formula=client`, `react_hist_unit=unit`, `immune_force_apply=client`(절 «2026-11-05»). 11/04 전환 4개는 `preemptive_defense=client_main`, `toughness_elem=client`, `break_point_hits=window`, `break_auto_blocked_cc=on`. 11/05 오전에 `guild_boss_nv_sum=client`(길방 보스 속도·공격력 합산)도 기본으로 넣었고 9·10단계 낙관의 주원인이었음(절 «11/05 오전»). 길방 표는 이 기본으로 재생성함. 11/10 AddStatData 전달 경로 확인으로 같은 합 가정의 근거를 재검토하기로 했으며 이번에는 기본값을 유지했음(남은 일 4).
- 그 밖의 새 기본값: `mc.enemy_cd_end_order=after_effects`, `revenge_rate=hit`, `nova_force_cap=12`, `ally_auto_lines=client`. 기존 병합분 `foe_skill_order=data`, `empty_attack=process`, `ally_variant_mapping=data`도 반영했음. 선제 방어 실험용 `client`는 차단 조건을 보강했음. 선제 방어 기본값은 11/04 전환한 `preemptive_defense=client_main`임(legacy=recognize).
- 기존 기본값은 `enforce_timing=queue`, `enforce_target=exec`, `wave_ally_gauge=reset`, `buff_ban=refuse`, `buff_ban_force=client`, `guild_count=all`, `instant_damage=damage`, `reaction_timing=queue`, `skill_order=data`, `dispel_on_attack=on`, `turn_limit_unit=actions`, `break_skill_domain_clock=global`, `break_skill_domain_turns=5`, `enemy_hit_buff_cmp=le`임(`toughness_elem`은 11/04부터 `client`, legacy=db). 정본은 `battlesim/rules/default.json`임.
- 길드방어전 시즌4(BFB·별 속성)는 11/05 04:00 KST 종료, 결산은 11/12 04:00까지임(`data/guild_defense.json`). BFB 상태 기계·지원 5종·선택 효과 4종·부분 점수식·내 정보 편성 탐색을 구현했음. `guild_boss=off`가 기본이고 길방 진입에서만 켬.
- `data/guild_sim.json`은 11/10 밤 병합 기본값으로 **234,000판** 재계산했음. off/max·육성 ×1·×1.5·×2·×2.5·×3, 팀 5개·지원 6종·단계 0~12·칸당 60판이며 공개 표준 육성만 썼음. 최고 단계는 직전과 같음: off 0/6/8/8/9, max 없음/3/4/6/7(없음은 클리어율 50% 이상 단계 없음). 각 1,950칸 중 클리어율은 off 221칸·max 275칸, 평균 진행도는 off 733칸·max 1,025칸 바뀜. 실제 플레이 대조는 남았음.
- 빠른 계산 표본 2,323건×40판을 11/10 밤 병합 기본값으로 다시 생성·재보정했음. 전체 일치 **0.910**(직전 **0.909**, +0.001, `data/quick.json calib.acc`). 그룹별 최종 일치는 base 0.886·cosmo 0.963·rush 0.948임.
- 11/09 새 기본값: `foe_react_buff_count=client`, `buff_step_group=client`(단계 그룹 버프), `break_skill_reduce=client`(오비탈은 피해 감소 항 0), `chain_pen=client`(연쇄 피해는 공격자 관통 미적용). 모두 legacy 로 되돌릴 수 있음(절 «2026-11-09»). `guild_sim.json` 은 60칸 비교로 불변 확인해 도장만 인정, `quick.json` 은 재생성·재보정(전체 일치 **0.919**). (→ 이후 11/10 병합 규칙으로 두 생성물 재계산)
- 생성물 규칙 도장: `tools/rules_stamp.py`·`tools/gen_rules_stamp.json`. 규칙 기본값을 바꾸면 `tests/gen_rules_stamp_test.py` 가 `guild_sim`·`quick` 이 낡았다고 실패하므로 다시 만들거나 `--ack 이름 --reason "…"` 로 이유를 적어 인정함. 건너뜀 표시는 `run_tests.py --strict`.
- 11/09 코스모 실제 플레이에서는 벨그라스가 특히 비관적이었음. 11/10 보호막·자기 피해·흡혈을 수정했으며 같은 시점 자료로 재대조하기로 함(남은 일 16, 계정 수치는 비공개 보고서).
- 저장소: `origin/main=cf7d316`, 육성 가이드 리뷰 반영까지 푸시되어 있음. main의 R&D 병합 `0c70ab4`와 이번 재빌드·문서 갱신은 로컬 작업이며 푸시하지 않았음. 주소: https://QooReche.github.io/starsavior-party-navigator/
- 최근 검증: 11/10 밤 늦게 리뷰 반영 전 기준선은 **112 통과/0 실패**였음. 반영 후 static-data와 Playwright 가상환경을 지정한 `tools/run_tests.py --rebuild --e2e <Playwright Python> --timeout 1800`은 **일반 113개·브라우저 44개 통과/0 실패**였음(실행기 집계 114 통과). 기존 환경 건너뜀 2건(COSMO_TABLES·옆 journeyhelper 없음)은 같음. 탐색 결함 10종·벤치 시간 덮어쓰기 결함을 모두 검출했음. 로그는 `local/cosmo-review-final.log`, 골든/결과 해시 `--write`는 쓰지 않았음.

## 남은 일

2. 최신 내 정보와 영상으로 실제 플레이를 대조하기로 함: 선택 효과·질투의 시선·정실 어필·보호막·웨이브 게이지·스칼렛 행동 수·하이 스코어 버프 해제·부케 딜 분배. 이번 작업은 계정 자료를 쓰지 않았음.
3. 추가 규칙 후보 중 미확인: heal_target 동률·부활 대상, AOE_DIV 레벨 가산 위치, 피해 감소의 클라 전용 항(비치명·역할·상성·유닛 종류), 절대 적중/저항 항(현 데이터 0), ForceNonCritical SE 1건, 구원자 격파 게이지·AdjustSuperArmorBreakScale 사용처. 11/10 구현·직접 확인분은 `docs/followup_d_1110.md`·`docs/rules_e_1110.md`에 정리했음.
4. 서든데스 컨트롤러가 단계 선택식에 이전/새 턴 중 무엇을 넘기는지, ADT_FIXED_TRUE 전체 식, 엔진 trigger_skills와 표 NST_REACT 28건의 전수 대응, counter_inc의 시전 시작/끝 마지막 칸 기록 시점이 미확인임. BFB 배치 AddStatData는 1단 NV, 버프는 3단으로 들어가는 경로를 확인했으므로 현 `guild_boss_nv_sum=client`의 같은 합 가정을 재검토해야 함. 별의 도전 단계 배율 주입·지원/선택 효과 전체 피해식은 미확인임. 기대값 엔진의 확률 상태 상관·동률 대상·아군 HP/브레이크 근사도 남았음.
5. 길방 추천에 보유 브레이크 스킬 입력을 연결하고, 편성·지원·단계를 직접 고르는 시뮬 UI와 수동 비교 범위를 정하기로 함.
6. 길방 미확정 규칙을 확인하기로 함: 허무와 10단계 면역 동시 선택, 하루 도전·점수 합산·1~6단계 요일, 보스 속도/공격 AddStat·지원 배치 순서·시즌 길드 버프, 졸개전 패배 부분 점수 근사. BFB 52204 처치 초기화는 구현 완료했고, 중간 신부 경쟁 해제·부활·다단 타격 사건 순서는 미검증임.
7. 11/05 종료 뒤 다음 시즌 자료·보스 명세·search 설정을 갱신하고 빌더 검증을 확인하기로 함(`docs/PORTING.md`, `tools/build_guild_bfb.py`).
8. 저사양 PC의 길방 탐색 시간·예상 시간·탐색 축소·부분 결과·진단 표시를 검토하기로 함. 협공 제외 수·불리한 구원자·예선/본선 부분 결과의 합성 e2e는 완료했고 실제 플레이 탐색 성능은 남았음.
9. 게임 PC에서 37-3 비관·37-2 에핀델 편성·37-36 샤를 첫 행동·38-36 생존/행동 수·트리쉬 피해·세레스/루그 동작을 같은 시점 자료로 재대조하기로 함. 달 회랑 360층 낙인·기본기 대상 분산, 성간 회랑 카르멘 리더 corr-c 샘플도 남았음.
10. 브레이크 자동 발동·쿨 단위·발동자 게이지·영역 지속·재발동·행성 정화 조건, 보스 브레이크 지속·미측정 궁극기 강인도·불리 상성 강인도·`enemy_hit_buff_cmp`를 영상으로 확인하기로 함.
11. 서부 탈환대 세레스 스킬·기본 베라 자동 지정 근사, 기믹 추정 대처·무적 웨이브 실제 배치·길방 밖 협공/추가타·ReactiveBarrier 활성 표를 추가 확인하기로 함. 기본/개화 매핑과 적 SkillOrderList·빈 공격 처리는 완료했음.
12. 게임 PC의 10/29 아카라이브 원고 «게임 파일에 새 수치가 없어» 문단과 myinfo.ps1 배포 필요 여부를 확인하기로 함. 작전 보스 근사 보정·rankAll/quickRank 캐시·legacy 정리는 낮은 우선순위로 남겼음.
13. 장비 탐사 외 «N턴 이내 승리» 미션 확장은 낮은 우선순위: 큐브 팰리스 일부(65·60턴)·이벤트(65·60 / 50·45)·일일(50·45)도 같은 미션이 표에 있으므로 필요하면 `STAR_TURNS` 확장함. 65턴(2별 추정)은 표시 안 함.
15. 중복 코드 점검(11/08) 뒤 남은 공통화 후보: `m_BuffStrID→이름` 나머지 복사본(`build_buff_count`·`build_break_levels` 등은 용도가 달라 보류), `SKILL_TEMPLET_{1,2}` 읽기, mc.py 효과 직접 생성 4곳(의미가 달라 보류). 상세는 절 «11/09 중복 코드 점검 나머지 정리». 독립 리뷰에서 `enemy_leader`의 로컬 전투 호스트 근거만 확인돼 서버 동작은 미확인으로 남겼음(note에 명시).
16. **코스모 벨그라스 남은 대조**: 침식 체크 수명 0의 초기 대입·ROOT와 BOSS_5 대응, 영상의 브레이크 피해량이 미확인임. 시전 시작 판정·SKILL_END 정리는 확인했으나 다단 타격을 분리하면 시전 시작 스냅숏이 필요함. 쇠락 사망 보존은 `dead_keep_dnp=client` 선택지로 구현했으며 동명 충돌·전체 부여 경로 미확인으로 기본 off 유지했음. 같은 시점 내 정보·영상 재대조는 남았음(계정 수치는 비공개 폴더).
17. **코스모 탐색 시간 단축 후속**: 다음 후보는 핵심 함수 Cython/WASM 이전이며 효과 미확인·비용 큼. 워커 재사용 기본 변경의 브라우저 전체 탐색 전후 시간, 16워커·다른 기기, 장시간 메모리·인터넷 지연을 측정하기로 함. «빠른 탐색(실험)» 기본 전환은 별도 시드에서 작은 풀을 포함한 보스별 gold 상위50 회수율이 기준선보다 낮아지지 않고, 후회값 비열등·최선 삼중 구원자 보존·전체 시간 감소를 함께 만족할 때 검토하기로 함. 현재 작은 풀 카넬리아 회수율은 89.2%→88.8%로 조건 미달임. 자동 난이도·mean·브레이크 스킬·계정별 육성으로의 일반화, Pyodide 버전 비교도 남았음. 리뷰 권고의 복구·계측·표시 보완은 완료했으며 성능 추가 측정이 남았음. 완료한 CRN·턴 제한·후반 예산·1/2/4/8워커 측정과 채택/기각은 `docs/cosmo_speed_rd_1110.md`.
18. **코스모 난이도 자동**: 선택 로직에 상한은 없음(0~18 비교). 난이도 9 부터 «폭주: 시공»(보스 속도 +30%)이 붙어 엔진 점수가 꺾이고 이후는 기본 점수×배율이 지배(8과 18이 비슷). 실제 9 이상 데이터가 없어 엔진 9+ 구간은 미검증 -> 사용자가 9~12단계 결과(턴·생존·깎음)를 주면 보정. 후보 선정이 대표 난이도 6 기준이라 고난이도 전용 팀을 놓칠 수 있음 -> 고난이도(12 등) 추가 스크리닝·probeRuns 증가는 계산 시간과 맞바꿈.
19. 추가 규칙 후보의 남은 경계: 엔진 `dur=None`과 클라 0턴 전수 대응(`check_buff_expiry=action`, `check_buff_scope=name` 유지), 행성 정화의 대상은 있지만 실제 이력이 없는 시전·사망 시전자 SKILL_END, 영역 해제·강화 개수 집계는 미확인임. 11/10 리뷰 R3~R5: 아군·적 턴 시작 SE와 틱 뒤 반응 예약 전수 대응, `skill` 만료의 중첩 시전 외부 효과 제거, 부활 등장 HP 0에서의 회복·조건·자해 경계는 기본 전환 전에 검증하기로 함.
23. **구원자 스킬 효과 남은 확인**: DoT/HoT 사이 순서·수명 차감 시점·아군 쿨 차감, 능력치 최종 정수화/반올림, 린 실제 서버 덱의 초기 쿨은 미확인임. `stat_select_int=float`, `ally_init_cd=0.0`·grade=user 유지. 실제 플레이 대조는 남았음.
20. 코스모 영상 대조는 난이도 8 한 판씩뿐이라 전역 가정을 바꾸지 않음. 카넬리아·티리아 판은 11/09 데이터가 남아 있음(비공개 `video_1109`).
21. **외부 문서 규칙 남은 확인**: NKM:826 두 필드 초기화 의미, 서버의 스테이지 효과 주입기 구성, AFTER_SPAWN 문구↔SE 전수 대응·HP 조건부 등장 효과, DeadNotDispel 동명 충돌·전체 생성 경로가 미확인임. `wave_carry=keep`, `wave_foe_battle_start=all`, `revive_after_spawn=off`, `dead_keep_dnp=off` 기본 유지. 전투력 산출식·적용 콘텐츠·재점화 결합·전투력 공식 일치, `wave_carry=client` 영상 대조·외부 문서와 같은 입력 결과 대조는 남았음(`power_penalty=off` 유지).
22. **육성 가이드 2·3단계**: 길방의 상위 20% 점수 비교·코스모의 3팀 재결합 가이드는 차후 구현하기로 함. 작전·회랑 1단계와 슬롯 교환 추천은 구현했음.
24. **가진 +15 장비를 구원자끼리 재분배하는 최적화 — 차후 구현(사용자 11/10 결정)**.
25. **내 정보 레벨 경계**: 코스모/플래시 포인트 레벨 200 고정의 서버 동작 미확인, 소스 구원자 정확히 200일 때 미확인. 새 형식 내 정보 재추출은 게임 PC에서 하기로 함. 이번 검증은 합성 계정만 사용했음. 서버의 null 슬롯·레벨 0 전송 여부와 잠긴 슬롯 포함 여부는 미확인임. 방어 처리는 추가했으며 실제 사용 가능한 슬롯 수는 재추출 뒤 대조하기로 함.

## ▶ 2026-11-10 밤 늦게 (Claude+codex) — 코스모 탐색 시간 R&D (푸시 전)

- **리뷰 권고 반영**: Astra 2건·Opus 1~5를 모두 반영했음(기각 없음). 누락 cosmo 결과 팀 재평가·재누락 오류, 완료 벤치 시간 보존, 최초 엔진 안내 복구, ETA 키 v2, 작은 풀 대리 선별 생략, legacy 검증 범위·시드/판 수 검사·공개 R&D 문서 경로/CPU 모델 일반화를 적용했음. 탐색 결함 10종·벤치 덮어쓰기 결함 주입은 모두 실패를 검출했으며 변경 전 대비 합성 8조건의 기본 결과·전투 요청이 같았음. 고정 범위 `452784e..86f180b` 독립 리뷰에서 추가 확정 결함은 없었음. 재빌드·전체 일반 113개·e2e 44개 통과/0 실패, 기존 환경 건너뜀 2건이며 로컬 커밋만 했음.

- **범위**: `cf7d316`의 육성 가이드 리뷰 반영과 `412da89`의 속도 R&D를 합친 `0c70ab4`에서 생성물을 재빌드했음. 두 저장소를 `git pull --ff-only`로 확인했으며 각각 origin/main `cf7d316`·static-data `64e4fad`로 최신이었음. 엔진 규칙·골든을 바꾸지 않았음. 상세 측정 조건·품질·독립 리뷰 기록은 `docs/cosmo_speed_rd_1110.md`.
- **전체 탐색**: 공개 standard·난이도 6·top·8워커 네이티브 측정임. 작은 풀 30명은 기준선 314.77초(3회 평균)→실험 253.75초(1회), **1.24배**였음. 큰 풀 54명은 1,962.52초(5회 평균)→1,771.95초(1회), **1.11배**였음. 대리 선별·감시·전수 복귀·워커 재사용을 함께 켠 값이며 **2배 목표 미달**임. 큰 풀 실험은 기준선 최단 1,776.08초와 비슷하므로 환경 변동과 분리한 성능 보장은 아님.
- **대리 선별 — 실험 유지**: r=.70, 제외 표본 2%, 놓침 문턱 .04와 전수 복귀를 넣었음. 두 풀 모두 같은 시드의 최종 1위가 5회 전부 같고 gold 최선 삼중의 구원자 놓침은 0명이었음. 다만 작은 풀 카넬리아 상위50 회수율이 89.2%→88.8%로 0.4%p 낮아 기본 채택 조건에 실패했음. «빠른 탐색(실험)»은 모든 풀에서 기본 꺼짐으로 유지했음.
- **CRN — 기본 활성화·판 수 축소 기각**: 28,800판에서 기본 60.28초·streams 62.13초였음. 상위 후보 paired 분산은 카넬리아 약 1.2% 감소에 그치고 벨그라스 약 9.9% 증가였음. 20/40판은 유지하고 옵션 전달만 남겼음.
- **턴 제한 — 제품 적용 기각**: 15/25행동은 29.81/41.70초로 짧아졌으나 상위10% 순위 상관이 벨그라스 .059/.239·카넬리아 -.026/.250으로 낮았음. 전체 순위 상관만으로 후보 보존을 주장하지 않았음.
- **후반 예산 — 세 방법 기각**: 보스별 40팀 파일럿에서 균등20판 6.71초, 반감 4.97초(1.35배), racing 4.64초(1.45배), OCBA 9.46초였음. 반감·racing은 일부 보스 상위10 회수율이 낮아졌고 OCBA는 동일 판 수에서 시간이 늘었음. 전체 탐색 가속률로 해석하지 않았음.
- **워커 재사용 — 기본 채택**: Chromium/Pyodide 744판·4단계·조건별 3회에서 1/2/4/8워커 새 생성→재사용 시간이 25.90→18.66초·17.29→10.63초·14.02→7.21초·13.63→5.97초(1.39/1.63/1.94/2.28배)였음. 24개 실행 결과 해시가 같고 생성/종료 수가 일치했음. `workerReuse.value=true`, legacy=false로 채택했음. 8워커 2.28배는 짧은 벤치의 부팅 비용 절감이며 브라우저 전체 탐색 2배라는 뜻은 아님. 16워커·다른 기기·전체 탐색은 남은 일 17에 남겼음.

- **병합·재빌드 검증**: 육성 가이드 JS 7개는 `cf7d316`, 코스모 탐색 JS·설정 3개는 `412da89`와 같음을 확인했음. 생성 HTML에 모바일 육성/슬롯 UI와 빠른 탐색 UI가 함께 있고, 내장 search 설정은 JSON과 같았음. `index.html`은 재빌드 결과가 병합본과 같음(2,088,971바이트). simpack은 46파일·6,124,004바이트·`fa9690e1a621`로 갱신했음.
- **시험**: 변경 전 병합 커밋 `0c70ab4` 기준선은 일반 111 통과/1 실패였음. 실패는 `cleanup_test.test_manifest`의 기존 `ec83b7f1a046`와 현재 파일 해시 불일치뿐이었음. 같은 static-data 환경의 `tools/run_tests.py --rebuild` 뒤 일반 **112 통과/0 실패**, 지정 Playwright Python으로 e2e 전체 **44 통과/0 실패**했음. 환경 건너뜀은 COSMO_TABLES·옆 journeyhelper 없음 2건으로 유지됐음. 골든 `--write`·시험 기대값 변경 없이 통과했음. 로그·스크린샷은 무시되는 `local/merge_verify_1110/`에 남겼음.
- **마무리**: HANDOFF 현재 상태·남은 일 17·이 절과 sim manifest만 갱신했음. 로컬 QooReche/noreply 신원으로 한국어 커밋하며 푸시하지 않음. 계정 입력·비공개 표 원문은 추가하지 않았음.

## ▶ 2026-11-10 심야 (Claude+codex) — 내 정보 실효 레벨(스타링크 슬롯)·육성 가이드 1단계·슬롯 추천 (푸시 완료)

### 리뷰 3종 후속 (11/10, 푸시 전)

- **blocking 반영**: Astra 1은 소스를 가상 슬롯에 넣지 않고 현재 실효 레벨 유지, Astra 2는 후보별 예외 격리·제외 사유 표시, Opus B1은 옛 형식에서도 장비·스킬·공명·잠재력을 기존 대체 레벨로 계산하고 레벨 항목만 자료 없음으로 처리했음. 일반 진단 누락과 달리 여정·잠재력 등의 실제 자료 누락은 계속 차단함.
- **화면 blocking 반영**: Fable B1 모바일 라벨을 짧은 종류 칩으로 이동, B2 3열/모바일 행 재구성·상위 5명/나머지 접기, B3 슬롯 넣기·빼기 카드를 가이드 위 요약에 배치, B6 맨 위 육성 결론·클리어 이전→이후 표시를 반영했음.
- **blocking 기각**: Fable B4·B5의 light 대응은 사이트가 다크 전용이며 테마 신설은 범위 밖이라 기각했음. 잘못된 `[data-theme=light]` 가정 색상 덮어쓰기는 제거했음. 현재 다크 라벨 글자 대비 7.01:1·테두리/카드 바탕 9.24:1·수치 표시/화면 바탕 9.48:1로 WCAG 글자 4.5:1·비문자 3:1을 넘음. R2의 점/대시·＋/↑·라벨 모양을 함께 써 색에만 의존하지 않음.
- **코드 권고 전부 반영**: Astra 3·Opus R4는 콘텐츠/대상만 다른 호환 서명만 저장·집계하도록 했음(MM·SCROWN도 포함). Opus R1은 빈 칸에만 단독 넣기 진단·만석은 교환 필요, R2는 빈 칸 빼기 진단 제거, R3은 하향/동일 레벨 가정 제거, R5는 추출기 null 슬롯 원소 건너뛰기, R6은 레벨 0 수입 허용·기존 대체 계산·슬롯 추천 보류, R7은 세 JS 시험의 `--mutations`를 정규 실행기에 연결했음. 옛 형식의 카드마다 반복되던 레벨 누락 미반영 안내도 상단 재추출 칩으로 모았음.
- **화면 권고 전부 반영**: Fable R1 구역 점선, R2 종류별 테두리/기호, R3 공통 긴 문구 반복 축소, R4 구간/판 수/후보 수는 상세 접기, R5 미평가 행 접기, R6 전투력 이전→이후 상시 표시·세부 능력치 접기, R7 얼굴/넣기·빼기 교환 카드, R8 개선/손해/미확인 기호·테두리, R9 가정 기준 칩·재추출 안내 강조를 반영했음. 권고 기각 없음.
- **근거 직접 대조**: private static-data `64e4fad` NKC:420258-420264 슬롯 후보에서 소스 제외, 421483-421504 소스 적용 조건, 501255-501265 슬롯이면 링크 레벨 반환을 읽었음. 추출기 `SsMyInfo.cs`의 건틀렛 조건부 출력·null 가능한 디코더와 세 출력 구현을 확인했음. main pull은 최신 상태였고 static-data는 읽기만 하라는 이번 조건에 따라 pull 없이 `ls-remote`로 로컬/원격 해시 일치를 확인했음.
- **독립 리뷰**: 고정 범위 `d675cd0..7c5e950`에서 재추출 칩 문자열과 슬롯 노드 재렌더 지적을 받아 반영했음. `7c5e950..b0a2a7f` 및 추출기 `7ef7648..f72e9b9`·`fb00393..c29168b` 재검토에서 추가 blocking/정확성 결함 없음. 스냅숏은 main에 연결하지 않았음.
- **추출 도구 완료**: `starsavior-myinfo` main `ff7b9ef`, `starsavior-packet-ref` main `d33f754`로 로컬 커밋했음. C#·두 PowerShell 배포본·Python의 일반/빈 목록/null 혼합/전부 null 합성 ACK 출력이 일치함. null 방어를 제거하면 정상 2사례 뒤 null 사례에서 실패하고 복구 후 통과함. 신원은 QooReche/noreply, push하지 않았음.
- **회귀 검증**: 코드 blocking 3종과 조건 혼합/슬롯 수 초과/레벨 0 거부를 메모리 변이로 재주입해 실패를 확인했음. 브라우저는 모바일 라벨 높이·카드 하단 정보와 비겹침·이름 한 줄·상위 5명·슬롯 위치·맨 위 결론·WCAG 대비를 검사하고 B1/B2/B3/B6 결함 주입을 각각 잡았음. 가이드 재렌더 뒤 슬롯 버튼 노드/리스너 유지도 확인함. 추가 8명 계정의 옛 형식 전환 시험은 시뮬 완료 전에 30초 칩 대기로 실패했으며 완료 대기를 추가한 뒤 실제 작업자 슬롯 시험이 통과했음. 시뮬 판 수·탐색 상한·제품 시간 제한은 그대로임.
- **최종 시험 검토**: `b0a2a7f..cbb70df`의 호환 기록 유지/제외 시험·권고 변이 검사·슬롯 화면 완료 대기를 독립 재검토했고 추가 지적 없음. 기준선은 일반 109 통과/0 실패였음. 골든 기대값·엔진 규칙은 바꾸지 않았고 `--write`는 쓰지 않았음.
- **최종 실행**: static-data 지정 `tools/run_tests.py --rebuild --e2e E:\AI_mk2\venv-pw\Scripts\python.exe --timeout 1800`에서 브라우저 44건은 모두 통과했음(`%TEMP%/pn-review-final.log`). 일반 시험 한 건이 옛 레벨 0 거부 기대값으로 실패해 `myinfo_level_test.js`를 0 수입 허용·대체 레벨·누락 진단 검증으로 고쳤음. 두 0 거부 결함을 다시 주입하면 각각 실패함을 확인했으며, 같은 제품 코드로 `--rebuild` 일반 전체를 재실행해 **110 통과/0 실패**했음(`%TEMP%/pn-review-general-final.log`). 브라우저 제품/시험 코드는 앞서 통과한 실행과 같음. 환경 건너뜀은 기존 COSMO_TABLES·journeyhelper 2건임.
- **재캡처**: 요청한 scratch `pn/shots/capture.py`를 `pn/shots2/capture.py`로 재사용해 기존 18상태와 옛 형식 육성 가이드 1장, 합계 19장을 저장했음. `capture_manifest.json`에 전체 파일명·상태·크기·대비 검사를 남김. 4조합(1366/390 × light 속성/dark 속성) 모두 가로 넘침·깨진 이미지 0, 캡처 오류 0임. 접힌 모바일 전체 높이는 10,839→3,897px, 데스크톱은 5,899→3,580px임. 05 펼침 캡처는 나머지 명단도 열어 실제 보유 구원자의 항목별 기여를 표시함. 실계정 자료는 쓰지 않았음.

### 이전 구현 기록

- 병합: `wt/assumed-1110`의 manifest 충돌을 `tools/build_simpack.py`로 해결하고 `ca1e271`로 병합했음. main pull은 최신 상태였음. private static-data `64e4fad`는 읽기 전용으로 사용했음.
- 묶음: 스타링크 가상 슬롯·가이드 장비 +15·최대 스킬·공명 해금 최대·목표 여정/잠재력을 함께 적용함. 실제가 더 좋은 항목의 음수도 표시함. 원본 계정은 수정하지 않음. 레벨만/장비만/스킬만/공명·잠재력만은 하나씩 바꿔 독립 재탐색함. 항목별 값을 합산하지 않음. (→ 이후 리뷰 후속에서 소스/하향 레벨 유지·옛 형식 레벨 항목만 자료 없음)
- 표시: 육성 가이드 체크박스 하나로 정리했음. 옛 장비 옵션·ae 링크 값은 무시함. 카드 안 임시 보정/미보유 가정 라벨, 두 테마의 색 점선, 팀 머리 가정 포함, 수치 원래 값→보정 값 툴팁을 넣었음. 표의 각 줄에도 같은 라벨을 표시함. (→ 이후 리뷰 후속에서 다크 전용·짧은 칩·전투력 이전→이후 상시 표시·나머지 행 접기)
- 슬롯: 직접 실행한 콘텐츠·조건만 세션 메모리에 보관함. 소스는 후보에서 제외하고 현재 슬롯 배열 길이를 유지함. 후보 상위 8명·최대 교환 3번·24쌍·12,000판·120초 안에서 실제 교환을 검증함. 콘텐츠별 원 단위를 유지하고 개선 확인 콘텐츠 수→동일 콘텐츠 개선폭 순으로 비교함. 구간 0 포함·미평가는 확인 부족, 확인된 손해가 있는 교환은 제외함. 쿨다운 시간·준비 상태는 입력에 없어 존재만 표시함.
- 독립 리뷰: 고정 범위 `ca1e271..129cad0`의 지적 3건을 반영했음. 콘텐츠별 기믹/시즌/피해 가중치를 보존했음. 편성 발견 효과를 슬롯 효과로 오인하지 않도록 양쪽 상태의 공통 후보를 같은 판수·시드로 재평가함. 개별 진단보다 실제 교환을 먼저 계산하도록 바꿨음. 기각 없음. 수정 범위 `129cad0..17a13ee` 재검토에서 세 지적 해소와 새 차단성 결함 없음을 확인했음. `17a13ee..7ba02e6`에서는 단일 항목 비교가 누락된 여정 정보를 임의로 채우지 않도록 한 후속 수정·시험을 검토했고 추가 지적 없었음.
- 검증: 병합 직후 일반 107 통과/1 실패(`unit.level` 없는 미보유 가정)였으며 가상 슬롯 입력으로 해결했음. 최종 일반 109개·브라우저 e2e 43건 모두 통과했음(실행기 합계 110 통과/0 실패, 환경 건너뜀 2건). 묶음 누락·음수 제거·슬롯 추천 제거·점선 제거 결함 주입은 모두 실패 감지했음. 공유 링크 시험의 옛 `ae` 필수 기대값도 새 계약으로 갱신했음. 최종 결과와 합성 계정 실측은 `docs/assumed_build_validation.md`에 기록했음. 엔진 규칙·골든·내 정보 미사용 경로는 변경하지 않았음.

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

## ▶ 2026-11-10 밤 (Claude+codex) — 미확인 마무리·규칙 후보 7종·길방 BFB 새 패시브·코스모 가속 (푸시 완료)

- **리뷰 권고 반영(11/10)**: R1·R2 수정, R3~R5 미확인 경계 note 반영, R6 실제 standard 길방 시험 반영·«guild_sim 미재계산»은 a732566 재생성 기록/데이터 변경으로 기각했음. 93d300f legacy 14사례 상태·시간선·난수 일치, 기본값은 a732566와 72판 API 결과 불변, 결함 재주입 4종 assertion 실패 확인. simpack 재생성·HTML 동일, quick/guild_sim·골든 유지, e2e는 기본값 결과 불변이라 재실행하지 않았음. 상세 `docs/review_followup_1110.md`.
- 리뷰 후속 검증: 기준선 일반 103/0 → 최종 일반 104/0, 환경 건너뜀 2건 동일. 독립 리뷰는 고정 범위 `a732566..e4428ead70b71b99a4b2e4924ad483ebc87b5a8c`(브랜치에 연결하지 않은 검토 스냅숏)의 엔진·시험·note와 클라 근거를 대조했으며 수정 필요 지적 없음.
- 묶음은 `93d300f` 이후 `dad6846` 코스모 가속, `3e43e9e` BFB, `6c1e847` 후속 D, `5b4dd4d` 규칙 E임. `22a6235`에서 main의 병합 충돌 3파일을 정리했음. 비공개 static-data `64e4fad`는 읽기만 했고 시험에는 `STARSAVIOR_STATIC=E:\AI_mk2\starsavior-static-data`를 지정했음. 병합 진행 중이라 pull하지 않았음.
- 충돌: default의 양쪽 키를 전부 보존하고, 부활 영역 note는 D의 주입기 근거 보완·오메가 note는 E의 해제 분리를 합쳤음. `_KEEP`는 양쪽 legacy 고정 키 합집합이며 각 부모의 키/값 포함을 자동 검사했음. 기존 브레이크 시험은 legacy 계약이므로 `wave_extra_turn=keep`·`break_gauge_actor=exclude`를 함께 고정했음. 새 기본값에서는 브레이크 발동자 +2000을 보존한 뒤 다음 웨이브에서 게이지·예약을 초기화함. 이 경계는 별도 교차 시험으로 검사했음. 골든 값은 변경하지 않았음.
- 후속 D 8종: 기본 전환은 `wave_extra_turn=clear`, `turn_start_order=client`, `guard_skip_immune=client`임. `wave_foe_battle_start=all`, `dead_keep_dnp=off`, `revive_after_spawn=off`, `add_damage_guard=off`, `stat_select_int=float`는 미확인 경계를 남기고 기존 기본을 유지했음. 상세·클라 파일:줄은 `docs/followup_d_1110.md`.
- 규칙 E 7종: `buff_fresh_scope=client`, `break_gauge_actor=client`, `purify_nova_scope=all_casts`, `preemptive_reduce=client`, `omega_dispel=client`가 새 기본임. `check_buff_expiry=action`, `check_buff_scope=name`은 유지했음. 서든데스·반응 이력·지속 피해 counter_inc 문구를 직접 확인한 범위로 정정했음. BFB AddStatData 1단 NV와 버프 3단 경로가 확인돼 기존 `guild_boss_nv_sum` 합산 근거 재검토를 남겼음. 상세 `docs/rules_e_1110.md`.
- 길방 BFB: 52204는 같은 공격 이력 대상의 신부 경쟁 보유와 사망을 함께 검사함. 삭제 수량 0은 BOSS_7 전체 삭제이며 `guild_bridal_kill_reset=client`로 구현했음. 시전별 기록·엔포스·수호자 사망 제외·캣파이트 유지·빌더 검증을 시험했음. 상세 `docs/bfb_52204.md`.
- 코스모: HP 절단은 즉시 유지하고 전체 능력치 재계산만 지연했음. 반응 줄 분류 LRU를 추가했음. 축소 네이티브 340판 측정은 평균 21.54% 단축(1.2745배), 결과/상태/난수 동일 시험을 유지했음. 실제 단일 Pyodide 워커 새 컨텍스트 평균 2.1533초·같은 컨텍스트 두 번째 1.3632초·재사용 2.2ms였음. 전체 UI 탐색 가속률로 일반화하지 않음. 상세 `docs/cosmo_speed_1110.md`.
- 병합 상호작용: `tests/merged_rules_test.py` 4개에서 턴 시작×fresh 치명 DoT·무적 수명, 보호막×fresh×부여 시점, DNP×부활 등장×영역 복구, 브레이크 처치×게이지×웨이브 예약을 검사했음. 각 경로 실행을 단정했고 8개 스위치 강제 변이 모두 assertion 실패를 확인했음. 엔진 추가 수정은 없었음.
- 독립 리뷰: 고정 스냅숏 `93d300f..d4dae905a36629f4a5b101fd112629c0af82fe3b`에서 확정 상호작용 결함 없음. 시작 순서/fresh/shield 8조합·DNP/등장/영역 8조합을 별도로 실행했고 통과했음. 클라 NKM:5379–5407·4565–4583과 부활/차감 순서를 대조했음. HP 조건부 등장·DNP 전체 부여 경로·다단 타격·정화 이력 근사는 미확인으로 유지했음. 기각한 지적 없음.
- 교차 시험 추가 리뷰: `22a6235..0614d2f0e7e953ee2249aa5c6040f71565753188`에서 조건 누락·가짜 통과 결함 없음. 웨이브 시험은 act→spawn_wave→act 직접 호출이며 자동 스케줄러를 검사하는 시험은 아님. 부활의 fresh 축은 비행동 중 대상의 양 모드 동일 경계를 검사함.
- 재생성: `build_simpack.py` → `gen_quick_calib.py --per-content 400 --opboss` → `calibrate_quick.py --write` → `run_tests.py --rebuild`의 HTML 순으로 수행했음. 표본 2,323건×40판(92,920판), 전체 일치 **0.909→0.910**(+0.001). 최종 그룹 일치는 base 0.886·cosmo 0.963·rush 0.948임. quick은 기본 계수·보정 통계만 바뀌었고 콘텐츠별 계수·스테이지 보정값은 같았음. 골든/결과 해시 `--write`는 쓰지 않았음.
- 길방: 기존 후보·지원·육성·seed 7·칸당 60판을 그대로 써 off/max 전체 234,000판을 재계산했음(988초). 각 1,950칸 중 클리어율 변화 off 221·max 275, 평균 진행도 변화 off 733·max 1,025, 판별 보스 깎음 평균 변화 off 753·max 1,046칸임. 최고 단계는 off 0/6/8/8/9, max 없음/3/4/6/7로 직전과 같았음. `guild_sim`·`quick` 도장은 생성기가 갱신했으며 둘 다 `fc85dd2714434381`임. 무영향 인정은 쓰지 않았음.
- 기준선: 충돌 정리 직후 전체 **100 통과/2 실패**. 실패는 기존 simpack manifest·quick/guild_sim 규칙 도장이었음. 새 교차 시험 1파일은 이후 추가했음. 환경 건너뜀은 COSMO_TABLES·옆 journeyhelper 없음 2건임. 최종 일반 시험은 **103 통과/0 실패**, e2e 38개도 모두 통과했음. run_tests 합계는 **104 통과/0 실패**(e2e 파일 1건 포함). 기준선의 두 실패는 재생성으로 해소했고 환경 건너뜀 2건은 같았음.

- 최종 생성물: simpack 46파일·6,119,393바이트·`b9e5cecf3419`, HTML 2,083,846바이트. 신규 파일은 교차 시험뿐이며 계정 자료·비공개 원문 표를 추가하지 않았음. 로컬 QooReche/noreply 신원으로 커밋하며 푸시하지 않음.

## ▶ 2026-11-10 오후 (Claude+codex) — 먼저 할 것 3건: 벨그라스 자기 피해·흡혈, 스킬 효과 3종, 외부 문서 규칙 3종 (푸시 완료)

- **리뷰 권고 후속 반영(11/10)**: 1~4 모두 반영, 기각 없음. ① `wave_carry=client`에서 아군 차감 뒤 양 팀 WAVE_START(아군→적), keep 유지·note 정정(NKM:819-832·12618-12621). ② TurnUnitNegativeBuff는 예일 때만 검사하고 NotTurnUnitNegativeBuff도 지원했음(NKM.Templets:41814-41818·42375-42407, `tables/Plain/SKILL_CONDITION_TEMPLET.json:10849-10855` 조건 59207 존재, 공개 실행 데이터에는 아직 없음). ③ standard 보호막 시험이 실제 턴 시작 유지·턴 끝 차감과 각 경계 도달을 검사하게 고쳤음. ④ 흡혈 note에 이번 스킬 한정 보정 미연결을 명시했음(`mc.py`의 `_vampirism_hit`·`LOCAL_OK`, `data/myinfo_view.json` 잠재력 11026). 관련 시험 28개 통과, 이전 웨이브 순서·이전 조건 처리·Not 지원 제거·보호막 시작 조기 차감·종료 차감 제거 5종 변형 모두 assertion 실패 확인. 공개 standard 9개 조합·72판 결과 불변(실행 시간 제외), 기본값·quick/guild_sim·골든 유지, simpack만 재생성했음. 사용자 조건에 따라 e2e는 재실행하지 않았음.
- **후속 검증(11/10)**: 수정 전·후 전체 98 통과/0 실패(`STARSAVIOR_STATIC` 지정), 마지막 note·simpack 변경 뒤 cleanup·rules·생성물 도장 4개 재검증도 통과했음. 독립 리뷰는 고정 범위 `5fbbfa0..42463c5`로 수행했고 문구 누락 지적을 반영한 뒤 추가 지적 없음으로 완료했음. 비공개 저장소는 쓰지 않고 원격 HEAD와 로컬 `64e4fad` 일치를 확인했음.
- **병합 범위**: 외부 규칙 `967fe37`·스킬 효과 `1ef7a18`·벨그라스 `e1fdfed`를 main `ccbc0a0`에서 합쳤음. 각 작업의 고정 커밋 범위 독립 리뷰와 지적 반영을 완료했음. 생성물 재계산 작업(`5fbbfa0`)은 생성물·문서만 갱신하며 엔진·시험·골든을 고치지 않았음. 비공개 static-data `64e4fad`는 읽기만 했음. 이 절의 NKM은 `decompiled/NKM/NKM.decompiled.cs`임.
- **벨그라스 자기 피해·흡혈**: 공허 붕괴는 시전 시작의 썩은 의지 중첩을 저장해 보스 자신에게 시전당 한 번 예약 피해를 줌(`cosmo_hyper_true_target=self`, legacy `enemy_all`). 반응 처리 뒤·턴 종료 효과 전에 무적/보호막/HP 경로를 거치며 플레이어 개인 피해에 귀속하지 않음. 흡혈(`damage_vampirism=client`, legacy `off`)은 대상별 피해 동기화 합·보유 흡혈률·받는 회복량을 적용해 버림하며, 데이터에 없는 페이 기본 흡혈률을 추가하지 않았음. 쇠락은 약화가 아닌 표식(`cosmo_drain_category=marker`, legacy `debuff`), 코스모 보스 최종 속도는 버림(`cosmo_speed_floor=true`, legacy `false`)임. 근거 NKM:4666-4688·7841-7859·8123-8134·13435-13448·13537-13544·18293, `tables/SE_TEMPLET_SKILL_2.json:34711-35408`, `tables/BUFF_TEMPLET.json:18700-18759`. 해당 작업 보고: 새 시험 16개·legacy/예약 차단 변형 실패 확인. 침식 사건 경계·영상 브레이크 피해·사망 후 쇠락 보존·다단 타격 근사는 남은 일 16에 남겼음.
- **스킬 효과 3종**: `variant_self_state=client`(legacy `off`)로 루그 제압부·참 교체·설중화 감소·급급여율령 해제·노바 중첩을 연결했음. `turn_unit_debuff_cond=client`(legacy `skip`)로 세레스 할로윈의 턴 유닛 약화 보유 조건을 처리했음. `auto_marker_lines=keep`(legacy `drop`)으로 티리아 최고 방어력 체크 표지를 가시 추가 부여 전에 실행하며 동률이면 무작위 1명임. 근거 NKM:2921-2937·15891-15901·9014-9041·9161-9182·6740-6757·7039-7044·7605-7607, 조건·대상 표 상세 줄은 규칙 source에 있음. 해당 작업 보고: 새 시험 12개·legacy 핵심 시험 7개 실패 확인, 노바 표지 누락 리뷰 지적 반영·재검토 완료. 린은 source/note만 보강했고 시작 쿨 기본값은 유지했음. 남은 순서·스탯 반영 시점·덱 경로는 남은 일 23에 모았음.
- **외부 규칙 3종**: `wave_carry=client` 선택 시 생존 아군 효과 지속 차감·죽은 시전자 도발 제거·게이지 초기화 뒤 WAVE_START를 처리함(기본/legacy `keep` 유지). `shield_tick=turn_end`(legacy `turn_start`)로 보호막 보유자 턴 끝 차감·행동 중 타인 부여/재부여 면제·시작 이벤트 예외를 반영했음. `break_domain_revive=client`(legacy `none`)로 팀 영역의 남은 수명·부활자 직업별 보너스를 재부여함. `power_penalty=off` 유지, 근거 note/source만 보강. 근거 NKM:813-832·3973-3989·4565-4583·4739-4746·8263-8287·13555-13567. 해당 작업 보고: 시험 14개·7종 변형 실패 확인, 실제 웨이브 진행도/경로 검증과 미확인은 `docs/external_rules_c_1110.md`·남은 일 21에 있음.
- **길방 판정**: `git show`로 `39e03f4`·`a24d4d9`·`8537350`의 무영향 인정과 이유 이력을 확인했음. 이번에는 기존 후보 5팀이 그대로여도 영향이 있음. 저장 표 첫 팀(세레스 할로윈·웨딩 에핀델·바니 샤를·크리스텔), 표준 육성 ×1.5·6단계·지원 none·선택 off·seed 7·각 20판에서 legacy→병합 기본값 클리어 0.05→0.00, 진행도 0.7416→0.7368, 판별 보스 깎음 평균 0.4833→0.4736. 스위치 하나씩 비교해 `turn_unit_debuff_cond`만 전환해도 같은 차이를 확인했음. 따라서 도장만 인정하지 않고 기존 설정 전체 **234,000판을 재계산했음**(1,028초). 각 1,950칸 중 클리어율 변화 off 359칸·max 423칸, 평균 진행도 변화 off 1,160칸·max 1,515칸. off 최고 단계는 그대로(육성 ×1/×1.5/×2/×2.5/×3 = 0/6/8/8/9), max는 ×2 6→4·×2.5 7→6이며 나머지는 유지했음. 팀·지원·육성·seed·판 수는 이전과 같음.
- **재생성**: `build_simpack.py` → `gen_quick_calib.py --per-content 400 --opboss` → `calibrate_quick.py --write` → HTML 순으로 완료했음. quick 2,323표본×40판(92,920판), 전체 일치 **0.909**(이전 0.919, -0.010). 보정 뒤 그룹 일치 base 0.885·cosmo 0.963·rush 0.945. quick의 기본 계수·보정 통계만 바뀌었고 콘텐츠별 계수·스테이지 보정값은 동일했음. 길방 완료 뒤 `--rebuild`와 같은 simpack·HTML 빌더를 다시 실행했음. simpack 45파일·6,087,219바이트·`f24c4f44c50d`, HTML 2,083,862바이트. quick/guild_sim 규칙 도장은 모두 `ab0c0aa44391ff86`이며 생성기가 직접 갱신했음.
- **기준선**: `STARSAVIOR_STATIC=E:\AI_mk2\starsavior-static-data`, 전체 96 통과/2 실패. 실패는 simpack manifest·quick/guild_sim 도장뿐이었음. `COSMO_TABLES`·옆 journeyhelper 없음으로 2건 건너뜀. 골든 `--write`·계정 자료는 쓰지 않았음.
- **최종 검증**: 같은 `STARSAVIOR_STATIC`으로 `python -X utf8 -I tools/run_tests.py` **98 통과/0 실패**, `python -X utf8 -I tools/run_tests.py --e2e E:\AI_mk2\venv-pw\Scripts\python.exe` **99 통과/0 실패**(e2e 파일을 1건으로 센 수, 브라우저 38개 모두 통과). 기준선의 두 실패는 재생성으로 해소했으며 환경 건너뜀 2건은 같음. HTML의 데이터 밖 내용은 동일하고 데이터 변경은 `guild.sim`뿐임. 11/03·11/02의 오래된 절은 원문 그대로 `docs/HISTORY.md`로 옮겼음. 로컬 QooReche/noreply 신원을 유지해 생성물·문서를 한 커밋으로 묶으며 푸시는 하지 않음.

## ▶ 2026-11-10 (Claude) — 새 빌드 확인·표 재추출·벨그라스 조사·외부 문서 대조 (푸시 완료)

- **빌드**: 설치본 26429597(11/05 20:03). DLL 변경 5개(NKM·NKC·Assembly-CSharp·NKM.Templets·Star.Templets)는 로직 동일(식별자 재난독화). 직접 검증: 새 NKM 을 옛 번호 체계로 맞춰 옛 파일과 비교하면 숫자 유지·CR 정규화 diff 89줄(전부 로그 문자열 속 변수명 접미사). 상세·해시는 static-data `decompiled/BUILD.md`.
- **표 재추출**(static-data `64e4fad`): 신규 구원자 0. 코스모 시즌 22(벨그라스·티리아·카넬리아) 표 + BattleScript 3개, 길드 레이드 속도 게이지 아이템 2000→3000(`SE_TEMPLET_BATTLE_EFFECT` 4015202, 11/01 이전 수정분 포함), 인코그니타 랜드그레이브 charm 발동 시점(BATTLE_START→AFTER_SPAWN), EX 효과 4개, 미니건 패시브 SE 1개(남은 일 24). 연출·이벤트 포인트 참조·목록 순서는 수치 아님. 패치 노트 대조는 미확인.
- **생성물**: `data/growth.json` 의 `game_build` 만 갱신(26291832→26429597, 나머지 동일). `data/guild_bfb.json` 은 재생성 결과가 기존과 동일. 시험 93 통과/0 실패(건너뜀 1: `COSMO_TABLES` 없음, 11/09 와 같음).
- **벨그라스 조사**(비공개 `AI\temp\partynavigator\work\belgras_1110\REPORT.md`, 계정 자료 기반이라 공개 금지): 주원인은 **보스 보호막 오류**로 확정. 처단자 패시브 표(`SE_TEMPLET_SKILL_2`)에 BI_BARRIER 가 3개 있음: `_05`·`_07`(ENEMY_ALL, 25%)·`_09`(AUTO_ALLY 보스 쪽, 1%). `tools/build_cosmo_raid.py:281` 이 첫 줄(25%)만 `barrierHpPct` 로 저장하고 `cosmo_raid.py:443` 이 보스에 적용해 과대. 에이전트 실험(아군 무적)에서 1%로 줄이면 깎음이 크게 올라감(수치는 계정 자료 기반이라 비공개 보고서에만). 고정 피해(공허 붕괴가 아군 전원에게 들어가는지)는 클라 코드 미확정, 페이 흡혈(`NST_RATE_DAMAGE_VAMPIRISM`)은 엔진에 없음. 전부 고쳐도 실제 점수에 못 미쳐 침식 방어 유지·브레이크 스킬 피해가 남은 후보. **아직 코드에는 넣지 않았음**(다음: `cosmo_boss_barrier` 스위치, 근거 `_09` 가 보스 대상인지 대상 해석 확인). (→ 이후 11/10 오전 보호막, 오후 자기 피해·흡혈 수정 완료)
- **`cond_count_bind`(새 기본 `holding`, legacy `last_key`)**: 조건 줄의 `중첩수`·`효과 개수`가 바로 앞 «자신이 미보유» 키의 효과(없는 효과라 개수 0)에 묶여 루그 설중사우 후 행동 게이지 +40/80/120%p 줄(「자신이 보유: 설중화; 자신이 미보유: 급급여율령; 중첩수: N」)이 항상 거짓이던 것을 고침. 근거 표 조건 52189~52191(`SelfBuffLevelCount` 는 `SelfBuffStrId`=설중화에만 붙음). `mc.py` `cond_ok`, 시험 `tests/cond_count_bind_test.py`(4개, 두 모드 결과가 갈림). 표준 육성 A/B(에이전트, 6칸)에서 루그 피해 +1.5~+60%. 생성물: `guild_sim` 은 루그가 팀에 없어 인정(이유 기록), `quick` 재생성·재보정 전체 일치 **0.919**(변화 없음). 시험 94 통과/0 실패. 실제 플레이 대조는 미검증(남은 일 9).
- **`cosmo_boss_barrier`(새 기본 `client`, legacy=`legacy`)**: 벨그라스 처단자가 보스에게 주는 보호막을 1%로(표 SE 210009411 `_09`, 조건 60414 «아군이 타격 후+응집된 생기», 대상 AUTO_ALLY, BarrierRate 100). 이전에는 아군용 줄(`_05`·`_07`, ENEMY_ALL, 25%)의 값을 보스에도 써서 보스가 공격마다 최대 HP 25% 보호막을 얻었음. `tools/build_cosmo_raid.py` 가 `bossBarrierHpPct` 를 따로 뽑아(`data/cosmo_raid.json` 의 `belgras.minions`, 나머지 필드 불변 확인) `mc.cosmo_boss_barrier_pct` 가 고름. 시험 `cosmo_raid_test.test_minions` 의 «보스 보호막 ≥ 25%» 단정(잘못된 가정을 굳힌 것)을 client 1%·legacy 25% 두 모드 검사로 바꿈. `quick`·`guild_sim` 은 코스모 게이트 규칙을 켜지 않아 인정(이유 기록). 시험 94 통과/0 실패(`COSMO_TABLES=C:\build\new-extract` 로 표 대조까지). 실제 플레이 대조(남은 일 16)는 미검증: 이 수정만으로는 실제 점수에 못 미치는 것으로 조사됐고 고정 피해·침식·브레이크 스킬 피해가 남은 후보. (→ 이후 11/10 오후 고정 피해는 보스 자신 대상 예약 피해로 수정, 침식·브레이크 피해 대조는 남음)
- **`stage_fx_target`(새 기본 `allies`, legacy=`enemies`, `off`도 있음)**: 플래시 포인트(BOSS_RUSH) 스테이지 효과를 적에게 걸던 가정을 아군(속성·직업 조건에 맞는 유닛)으로 바꿈. 근거: `BATTLE_EFFECT_TEMPLET` 60001~60021 전부 `AteamEffectTarget=ALL`·`BteamEffectTarget` 없음, 속성 `TargetAdjustType`·직업 `TargetRoleType`, SE 6000101~ 전부 `NSETT_SELF`+`NSEAT_BATTLE_START`, 클라 팀·직업·속성 판정 `NKM.Templets.decompiled.cs:36731-36799`, 효과 선별 `NKM.decompiled.cs:415-429`, 전투 시작 발동 `12829-12836`. 44개 스테이지 효과 순서·수치를 데이터북 fx 문장과 대조해 일치(`tools/build_stage_fx.py` -> `data/stage_fx.json`, 속성·직업 조건). fx 가 있는 스테이지는 플래시 포인트 44개뿐(다른 콘텐츠 0). 에이전트 측정(20판, 표준 육성): 같은 팀 진행도 allies 0.75 / enemies 0.62 / off 0.73, 클리어율 그레고리 Ⅰ 30% 대 5%. **미확인**: 서버가 전투 시작에 실제로 아군 유닛에 효과를 주입하는 호출(클라 코드에 없음, A팀=플레이어는 AteamWin·서든데스 A팀 효과 선례로 판단) -> 실제 플래시 포인트 영상 대조 필요. 엔진에 항이 없는 «생명력 흡수율 +15%»(공허매장자)는 양쪽 모드 모두 미반영. (→ 이후 11/10 오후 `damage_vampirism=client`로 생명력 흡수율 효과 연결) 시험 `tests/stage_fx_target_test.py`(7개, 일부러 깨뜨려 확인). `guild_sim` 은 fx 스테이지를 안 써서 인정, `quick` 은 rush 표본이 있어 재생성·재보정. 아래 «이전 판단» 문장 정정: 앞선 «기본 enemies 유지»는 quick 재보정 전의 임시 상태였음.
- **외부 «게임코드 시뮬» 문서 대조**: `docs/external_party_sim_1110.md`(11/10 푸시 완료). 남은 일 21·22.

## ▶ 2026-11-09 (Claude) — 코스모 추천 편성 실제 플레이: 벨그라스 (푸시 완료)

- 사용자가 추천 화면(자동 난이도) 대로 벨그라스를 쳤음(영상 11/09 19.53.35, 난이도 8, 판독 `AI\temp\partynavigator\work\video_1109\belgras\REPORT.md`). 편성은 추천과 일치(프레이·에밀리 리더·로자리아·페이 + 스타피어서 Lv.4). 결과: 점수 **7,619,375**(추천 화면 상위 4,537,859·평균 3,898,913), 보스 남은 HP **43%**(예측 깎음 22% -> 실제 57%), 턴 50/50 미처치, 생존 2/4(통계 남은 HP 0% 2명으로 읽은 추정), 점수식 역산은 생존 2명·깎음 약 57.5%와 맞음(식은 11/08 와 같음). 보스 시작 HP 1,450,000 은 엔진과 같음.
- 엔진은 실제보다 **크게 비관적**: 같은 편성을 표준 육성으로 돌리면(전투력이 실제의 약 절반이라 직접 비교는 못 함) 난이도 0에서도 18턴쯤 전멸, 실제는 50턴 동안 2명 생존. 이번 값은 같은 내 정보(편성 전투력 일치)로 다시 돌려 차이를 재야 함(남은 일). 후보: 보스 피해량·«폭주: 쇠락»(최대 생명력 5%씩 감소)·브레이크 스킬 피해(영상 HUD 에서 발동 한 번에 점수가 약 358k 뛴 장면, 데미지 180,000 표기) 과소 가능성. 모두 미확인.
- **티리아**(영상 11/09 20.04.47, 난이도 8, 판독 `...\video_1109\tyria\REPORT.md`): 편성 추천과 일치(리디아·루나 리더·에핀델·프로페서M, 지원 이름 미확인). 점수 **10,903,250**(예측 상위 11,111,547·평균 9,620,094), 남은 보스 HP 약 9~10%(예측 깎음 84% -> 실제 약 90%), 4/4 생존, 50/50 미처치(부하 2기 생존). 역산 깎음 약 91%. 즉 티리아는 예측이 잘 맞고(점수 평균 +13%, 상위 -2%) **벨그라스만 크게 비관적**임 -> 원인은 전역 규칙보다 벨그라스 보스 전용 처리(보스 피해량·«폭주: 쇠락»·기믹 연출) 쪽일 가능성. 미확인.
- **카넬리아**(영상 11/09 20.10.58, 난이도 8, 판독 `...\video_1109\carnelia\REPORT.md`): 편성 일치(아모라·아세라 리더·카넬리아·린 + 지원 특이점 관측 Lv.1). 점수 **9,085,875**(예측 상위 9,908,484·평균 8,405,344), 남은 보스 HP 30%(예측 깎음 71% -> 실제 70%), 4/4 생존, 50/50 미처치, 특이점 관측 컷인 2회(약 T37·T18). 예측과 거의 일치.
- **세 보스 종합**: 티리아·카넬리아는 예측(점수 평균 +13%·+8%, 깎음 84→90%·71→70%)이 잘 맞고 벨그라스만 크게 비관적(점수 7.6M 대 평균 3.9M, 깎음 22→57%, 예측은 전멸 쪽 / 실제는 2명 생존). 따라서 전역 규칙보다 벨그라스 보스 처리(`cosmo_raid.py`의 벨그라스 기믹·«폭주: 쇠락»·피해량)를 먼저 의심. 추천 순위(편성 선택)는 세 보스 모두 실제로 높은 점수를 냈음(2번째 판 폐기분 제외). 2번째 판은 폐기.

## ▶ 2026-11-09 (Claude) — 단계 그룹 버프·오비탈 감소·연쇄 관통 (푸시 완료)

- **단계 그룹 버프** `buff_step_group`(새 기본 client, legacy=off): 같은 BuffStepGroup 에서 더 높은 단계가 있으면 새 효과는 걸리지 않고(새 지속이 같거나 길 때만) 기존 지속을 늘린 뒤 다음 차감 1회를 건너뜀(`Eff.skip_tick`), 아니면 같은 그룹의 낮은 단계를 지우고 새로 걸림. 근거 NKM:4283-4305(지속 비교 4934-4937 `새 지속 >= 기존 지속`), 4450-4458(그룹 삭제). 표 `BUFF_STEP_TEMPLET.json` -> `data/buff_step.json`(`tools/build_buff_step.py`, 22개 이름, 이름만으로 단계를 못 가르는 10001 그룹 제외), simpack 목록에 추가. 데이터상 해당 버프는 세이라(1014)의 «상급 공격력 증가» 하나뿐. 미확인: 높은 단계가 이미 있을 때 새 효과의 props 를 병합하는지(여기선 지속만 늘림). 시험 `tests/buff_step_test.py`(9개).
- **오비탈(브레이크 스킬) 피해** `break_skill_reduce`(client/legacy=all): 클라 피해 감소 합(NKM:17773)의 5항(전체·역할·상성·브레이크·유닛 종류)이 모두 «공격자가 유닛일 때만» 값을 가짐(18028-18033, 18078-18083, 18090-18095, 17563-17578)이고 오비탈은 유닛이 아니라 0. 엔진은 전체·광역 감소와 브레이크 -15%p(=브레이크된 대상이 15% 더 맞음)를 적용해 과대였음. 방어율은 그대로 적용(클라 방어 항의 오비탈 취급은 미확인). 시험 `break_skill_test.BreakReduceClientTest`, 기존 시험은 legacy(`all`)로 고정.
- **연쇄(추가 고정량) 피해** `chain_pen`(client/legacy=attacker): 클라 추가 피해 경로(OBF_0763, NKM:17335-17356)는 방어율에 대상 방어력과 대상의 관통 저항만 쓰고(17837-17855) 공격자 관통(`NST_RATE_PENETRATE_DEF`, 일반 타격 17812)을 안 씀. 시험 `tests/chain_pen_test.py`.
- 생성물: `guild_sim` 은 60칸(팀 5·육성 1.5/3·단계 0/6/12·지원 2) 새/옛 규칙 결과 동일이라 인정(이유 기록, 스크립트 `AI\temp\partynavigator\scripts\guild_sens_1109.py`). `quick` 은 표본 재생성·재보정(결과는 절 끝 «quick 재생성»).

## ▶ 2026-11-09 (Claude) — 추가 규칙 후보 조사 (읽기 전용 3건 + 직접 확인 일부, 푸시 완료)

보고서(비공개 작업 폴더) `AI\temp\partynavigator\work\extra_1109\damage.md`·`state.md`·`nova_break.md`. Sonnet 조사라 아래는 **직접 확인한 것과 못 한 것**을 나눠 적음.
- 직접 확인해 구현함: 오비탈 감소 없음, 연쇄 공격자 관통 없음(위 절).
- 조사만 됨(직접 확인 전, 다음에 코드로 확인 후 스위치로 넣기):
  - **stage_fx_target (영향 큼 가능)**: 플래시 포인트 스테이지 효과(BATTLE_EFFECT 60001-60021)가 표에서 A팀(아군)·속성/직업 한정 자기 버프인데 엔진은 전 적에게 건다고 함. 서버가 실제로 아군에 부여하는 코드는 클라에 없어 표의 대상 조건으로만 판정.
  - **wave_carry**: 클라는 웨이브 전환 때 아군 버프·보호막·DoT·HoT 지속을 1씩 줄이고 노바 버스트 레벨을 0으로, «웨이브 시작 시» 줄은 그 뒤. 엔진은 지속을 안 줄이고 순서 반대. (→ 이후 11/10 `wave_carry=client` 선택지 구현, 기본 `keep` 유지·미확인은 남은 일 21)
  - **일반 버프 부여 턴 차감 제외**: 클라는 행동 중인 유닛이 남에게서 받은 버프도 그 행동 끝 차감에서 제외, SKILL_START 시점 부여분은 같은 턴에도 차감. 엔진은 자기 부여만 제외. (→ 이후 11/10 밤 `buff_fresh_scope=client` 기본 전환)
  - **스타피어서 발동자 게이지**: 클라는 턴 선정 때 게이지를 0으로 만든 뒤(NKM:13488 근처 `OBF_3574(0)`) 브레이크가 발동해 `BI_SPEED_GAUGE_UP` +2000 이 발동자에게도 붙음. 엔진은 발동자를 제외(mc.py `_apply_break` 게이지 줄 `u is not actor`). 호출 순서는 직접 못 확인. (→ 이후 11/10 밤 `break_gauge_actor=client` 기본 전환)
  - **오메가 프로토콜 break_skill_fixed**: `BI_ORBITAL_ARRAY_OMEGA` 가 일반 버프(CanNotDispel=false)라 클라에서는 해제됨, 엔진은 해제 불가. (→ 이후 11/10 밤 `omega_dispel=client` 기본 전환)
  - **행성 정화 조건 8000**: 표에 `AfterMyAction {}`(스킬 필터 없음, SKILL_CONDITION_TEMPLET.json:2498). 엔진은 반응·협공·추가 시전을 제외하는데 클라에 그런 분기가 안 보임. (→ 이후 11/10 밤 `purify_nova_scope=all_casts` 기본 전환, 실제 이력 근사는 남음)
  - **counter_inc 지속 피해**: 클라는 공격자 현재 시전 칸이 턴 전환 때 지워져(NKM:13486) 지속 피해에 카운터 +10%가 안 붙을 수 있음. 엔진은 붙임. 틱 순서 미확인. (→ 이후 11/10 밤 지속 피해도 같은 증가 합임을 확인, 시전자 칸 초기화 가설 기각)
  - 그 밖: shield_tick(클라는 보유자 턴 끝 차감, 엔진 기본 턴 시작) (→ 이후 11/10 기본 `turn_end` 전환), check_buff_expiry(매 스킬 끝), 부활 시 DeadNotDispel 유지·AFTER_SPAWN 재발동, heal_target 동률·부활 대상, AOE_DIV 레벨 가산 위치, dmg_reduction 클라 전용 항(비치명·역할·상성·유닛 종류), debuff_model 절대 적중/저항 항(현 데이터 0), ForceNonCritical SE 1건, toughness 구원자 격파 게이지 0(표 근거 없음)·AdjustSuperArmorBreakScale 사용처, power_penalty 레벨 거리 표 미모델.
- **같음 확인**: ELEM_HIT, dot_snapshot(live), enemy_same_formula, toughness_elem(client), basic_tough, evade_model 확률식, power_penalty 범위표 500행, nova_policy(오토에 버스트 호출 없음), break_skill_point_cap(grade code 로 올릴 수 있음), break_skill_cd_unit, break_skill_domain_clock, 광역 협공 저장 대상.

## ▶ 2026-11-09 (Claude) — 중복 코드 점검 나머지 정리 (푸시 완료)

- **`Battle.put_eff`**(mc.py): 길방 BFB `_put`·`_sup_put`, 코스모 `_put` 의 효과 직접 생성을 한 함수로 모음. 옛 차이는 인자로 그대로 살림(코스모만 `refresh_props=True`, src 기본값, 길방은 수치 갱신 안 함, `_sup_put` 은 marker·src=대상). 중첩 하한 `max(0, …)` 은 길방에도 적용되나 길방은 음수 add 를 쓰지 않아 동작 같음. mc.py 안 직접 생성 4곳(브레이크 영역:1279 · 불사·잔향:2502,2509 · 보호막:3566)은 11/09 에 읽어 보고 옮기지 않기로 함: 덮어쓰기·시계(clock)·합산(shield)·거부 검사 유무가 모두 달라 put_eff 에 넣으면 인자만 늘어남. 시험 `tests/put_eff_test.py`(코스모/길방 래퍼의 갱신 여부를 뒤집으면 실패 확인; 기존 시험은 이 차이를 못 잡았음).
- 분위수: `boss_hit_diagnostic` 의 `pct` 를 `api._pct` 로 교체(같은 식). `ingame_check._q`(최근접 순위)는 docs/ingame_samples.md 의 옛 수치와 맞추려고 그대로 두고 정의 차이를 docstring 에 적음.
- `build_gimmicks`: `savior_reco` 에 (이름, 부제) 중복이 생기면 조용히 덮어쓰지 않고 중단.
- `tests/savior_reco_sync_test.py`: 옆 `journeyhelper/src/assets/savior_reco.json` 이 있으면 `data/savior_reco.json` 과 같은지(줄바꿈 무시) 확인, 없으면 건너뜀 표식. 지금은 같음.
- `tests/nodejs.py`(`node_json`·`node_available`): cosmo·guild_defense 시험의 중복 제거. `tools/tables.py` 에 `buff_names`·`names_of`·`UnknownName` 추가, build_auto_skill·foe_auto·foe_react 의 복사본 제거(`--static ../static-data` 로 세 빌더 재실행 -> `git status data` 변화 없음). 시험은 `tables_test`.
- 점검 문서(11/08)가 이미 낡았던 항목: 직접 `json.dump` 는 모두 `atomic_open` 안에서 쓰고 있었고(C2 할 일 없음), 칸 순서 변환은 `gen_quick_calib.party_spec` 하나로 모여 있었음(`ingame_check`·`toughness_check` 도 그것을 씀).
- 안 한 것: `m_BuffStrID→이름` 의 나머지 복사본(`build_buff_count`·`build_break_levels` 등은 용도가 달라 보류), `SKILL_TEMPLET_{1,2}` 읽기 20여 줄, 길방·코스모 `_put` 과 mc.py 직접 생성 4곳 통일, 위 C1·C3 의 함수화. 전체 91/0(건너뜀 1건) + e2e 통과.

## ▶ 2026-11-09 (Claude) — 적 반응 강화/약화 판정 정렬·건너뜀 표시·생성물 규칙 도장 (푸시 완료)

- 적 반응 조건 4개(`target_neg_buff`·`target_pos_buff`·`self_pos_buff`·`self_neg_buff`)를 `e.harmful` 직접 셈에서 `n_harmful()`/`n_good()` 로 바꿈. 스위치 `foe_react_buff_count`(새 기본 `client`, legacy=`harmful`). 근거: 클라 조건이 «IsBuff && IsPositive / IsBuff && !IsPositive» 개수(NKM.Templets:40116-40137, 42099-42270)를 쓰고 `buff_count_source` 와 같은 기준임. 현재 `data/foe_react.json` 에 이 4개 조건을 쓰는 줄이 없어 **결과는 안 바뀜**(잠재 결함 정리). 클라가 세는 효과 목록의 세부(표시 효과 등)는 미확인. 시험 `foe_react_test.TestBuffPresence`(기본을 harmful 로 돌리면 실패 확인), `rules_test` 키 목록.
- 건너뜀 표시: 환경 때문에 못 돌린 검사(node 없음·`COSMO_TABLES`/비공개 표 없음)를 `tools/runtime.skip_note()` 로 표식(`[건너뜀]`)을 남기고, `run_tests.py` 가 표식과 unittest `skipped=N` 을 모아 끝에 «건너뜀 N건» 으로 보임. `--strict` 이면 실패로 침. 이 PC 는 node 있음, `COSMO_TABLES` 없어 1건 건너뜀.
- 생성물 규칙 도장: `tools/rules_stamp.py`·`tools/gen_rules_stamp.json`(지문 = formula·opts·mc 기본값 해시). `guild_sim`·`quick` 이 만들어진 규칙과 지금 규칙이 다르면 `tests/gen_rules_stamp_test.py` 가 실패. 다시 만들거나(빌더 `build_guild_sim.py`·`calibrate_quick.py --write` 가 도장을 새로 찍음) `rules_stamp.py --ack <이름> --reason "…"` 로 이유를 적어 인정함. 지금 도장은 11/09 기준선(두 파일 다시 만들지 않음, 이유는 json 에 기록). 전체 89/0 + e2e 통과(`--rebuild`).
- 안 한 것: 규칙을 조건별로 나눠 «어느 키가 이 생성물에 영향 주는지» 판정하지 않음(키 하나만 바꿔도 낡았다고 뜨므로 인정 절차를 거침).

## ▶ 2026-11-09 (Claude) — 비공개 표 경로 통일 (푸시 완료)

- `tools/runtime.static_path_or_none(root)` 추가: `STARSAVIOR_STATIC` → `<저장소>/../static-data`(`tables/` 가 있어야 인정) → None. 시험 6개(`myinfo_stats`·`myinfo_combat`·`savior_mapping`·`guild_bfb`·`client_gaps_1104`·`eff_remaining`)가 이 규칙을 씀. `C:\build\static-data` 고정 경로·다른 PC 경로(`E:\AI_mk2\...`)·`CERES_AUDIT_STATIC` 별칭은 없앰. `cosmo_raid_test` 의 `COSMO_TABLES`(추출본 형식이 달라) 는 그대로.
- 이 PC 에서 그동안 건너뛰던 `myinfo_stats` 비공개 정답 대조·`myinfo_combat` 재현·`savior_mapping` 원본 대조가 실제로 돌았고 **모두 통과**(새로 깨진 시험 없음). 사본은 `AI\partynavigator\static-data`(0e16db1, 11/02)를 씀.
- 시험 `cleanup_test.test_static_path_or_none`(함수를 깨면 실패 확인). 전체 `run_tests.py` 86/0(e2e 안 돌림).
- 남음: node 없을 때 print 후 통과하는 시험 3개(항목 14), 건너뜀 방식 통일(guild_bfb 는 print 유지). 다음 공통화 후보는 항목 15의 ③ 나머지(BUFF 이름표·STRING_COMMON·`names_of`).

## ▶ 2026-11-09 (Claude) — 구원자 키↔게임 id 매핑 공통화 (푸시 완료)

- `battlesim/starsavior/savior_ids.py` 추가: `keys_by_id(index, db=None, only_db=False)`(id→키), `ids_by_key(index, db=None)`(키→id, DB 키는 setdefault), `uid_resolver(index)`(키 우선, 이름은 유일할 때만). 규칙은 «색인 key → 시뮬 DB id → 유일한 이름».
- 쓰는 곳으로 바꿈: `build_auto_skill`(3곳)·`savior_mapping_test`·`build_myinfo_combat`·`ingame_check`·`build_growth.roster_ids`·`build_party_html` uid. 지금 시뮬 DB 에는 색인에 없는 구원자가 0명이라 `auto_skill.json` 은 바뀌지 않음(아모라는 색인에 있음). 앞으로 색인에 없는 구원자가 생기면 `build_auto_skill` 은 키를 채우지 않고 `build_myinfo_combat` 은 채움(`only_db` 때문에 규칙은 그대로 두었음, 통일 여부 미정).
- 확인: `--static` 으로 build_auto_skill·build_growth·build_myinfo_combat·build_party_html 재실행 -> `git diff data index.html` 0. 시험 `savior_ids_test`(DB 변형 제외를 지우면 실패 확인). `sim/manifest.json` 에 새 파일이 목록에 들어감(브라우저 시뮬 묶음). 전체 87/0(e2e 제외).

## ▶ 2026-11-09 (Claude) — 빌더 표 읽기 `tools/tables.py` (푸시 완료)

- `tools/tables.py`: `jsonc(path)`(문자열 안 `//` 보존, BOM 허용 — build_auto_skill 구현을 옮김), `rows(path)`(Data 벗김). 정규식으로 `//` 를 지우던 `build_foe_spawn.jsonc`·`build_foe_summon` 인라인·`build_cosmo_raid.strip_jsonc` 를 이것으로 교체(`errors='replace'` 도 없어짐 — 표에 잘못된 바이트가 있으면 이제 오류). 다른 빌더가 `build_auto_skill`/`build_foe_spawn` 에서 가져다 쓰던 `jsonc` 이름은 재노출로 유지.
- 확인: `--static` 으로 build_auto_skill·foe_spawn·foe_summon·foe_auto·foe_react·buff_force·guild_bfb·battle_end 재실행 -> `git diff data` 0. 코스모는 `C:\build
ew-extract`·시즌 1022·빌드 26429597 로 임시 출력과 `data/cosmo_raid.json` 키별 비교 같음. 시험 `tables_test`(문자열 안 `//` 처리 되돌리면 실패 확인), 전체 88/0(e2e 제외).
- 안 한 것: `m_BuffStrID → 이름` 7곳·`STRING_COMMON` 10곳·`names_of` 중복·`SKILL_TEMPLET_{1,2}` 읽는 20여 줄(`json.loads(...)['Data']` 를 `rows` 로 바꾸는 일). 효과가 작고 diff 확인 비용이 커서 보류.

## ▶ 2026-11-09 (Claude) — 시험 공용 도우미 `tests/simkit.py` (푸시 완료)

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
