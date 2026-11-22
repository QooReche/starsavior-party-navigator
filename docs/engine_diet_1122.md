# 엔진 다이어트 0~1·4단계 (2026-11-22)

설계: 페이블 상담 «엔진 다이어트»(1안: 묶음 경량화 먼저, legacy 스위치 삭제는 wt-batch 병합 뒤 기준선 위에서 20~30개씩). 이 문서는 5절 단계 계획의 0단계(실측·기준선·태그)·1단계(묶음 1차 경량화)·4단계(legacy 스위치 삭제) 결과.

- 태그 `engine-legacy-final` = `ed64b93`(브랜치 `diet` 시작 = 당시 main). 로컬에만 찍었고 push 는 메인이 판단.
- 엔진 코드(`mc.py`·`api.py`·`web.py`)는 건드리지 않았음. `battlesim/rules.py` 는 규칙 파일 경로 대체(아래 1단계)만.

## 0단계 — 실측

도구: `tools/diet_profile.py`(결과 JSON 은 `local/diet_profile.json`, 저장소 밖). Python 3.13.12, 이 PC(16코어) 단일 프로세스.
입력: 파티 `fei·professor-m·emily·wedding-carmen`(리더 0), 화면 옵션(`build: standard`, `rules_override: {power_penalty: model}`, `raw_runs`), 시드 1, `web.run_auto`.

### run_auto 시간(프로파일러 없이, 데우기 뒤 최솟값)

| 케이스 | 1판 ms | 8판 ms | 100판 ms | 판당 ms(100판) |
|---|---:|---:|---:|---:|
| 작전 NOA 1-3 | 2.2 | 10.1 | 137 | 1.37 |
| 달 회랑 FLOOR 100 | 11.3 | 84.0 | 1003 | 10.03 |
| 태양 회랑 FLOOR 250 | 30.2 | 344.9 | 5013 | 50.13 |
| 코스모 길레 1단계(스테이지) | 4.5 | 31.0 | 513 | 5.13 |
| 코스모 시즌 바스커빌 3단계 | 27.0 | 421.4 | 4894 | 48.94 |
| 길드 방어전 Lv1(fire) | 11.8 | 110.6 | 1858 | 18.58 |

1판·8판·100판이 판 수에 거의 비례 — 호출당 고정 비용(파티·적 정의 만들기, `support_report`, `assumptions_used`)은 데운 뒤엔 판 1개 시간보다 작음. 같은 조건 반복 사이 흔들림이 ±5~15%(1판 기준 태양 250 이 30↔50ms)라 1~2% 차이는 이 PC 의 wall 로는 가려지지 않음.

### 진단·기록 비용 비율

cProfile(함수 호출이 잦은 코드를 부풀리므로 상한 쪽 근사), 총시간 대비 cumtime:

| 케이스 | n | support_report | assumptions_used | Battle.log (호출 수) | lines_of | Battle.__init__ |
|---|---:|---:|---:|---:|---:|---:|
| 작전 1-3 | 8 | 1.79% | 0.39% | 0.02% (24) | 4.65% | 8.03% |
| 작전 1-3 | 100 | 0.13% | 0.03% | 0.01% (300) | 4.88% | 7.07% |
| 달 회랑 100 | 8 | 0.45% | 0.05% | 0.00% (61) | 3.67% | 1.46% |
| 태양 회랑 250 | 8 | 0.07% | 0.02% | 0.01% (314) | 3.35% | 1.47% |
| 코스모 길레 1 | 8 | 0.49% | 0.12% | 0.00% (8) | 3.43% | 1.64% |
| 코스모 시즌 바스커빌 3 | 8 | 0.01% | 0.01% | 0.00% (188) | 3.05% | 1.15% |
| 길드 Lv1 | 8 | 0.03% | 0.03% | 0.01% (131) | 3.92% | 1.38% |

횟수 × 단가(timeit) 추정, 판당 wall 대비:

| 케이스 | self.mc 읽기/판 | 읽기 비용 | rule_hits 증가/판 | rule_hits 비용 | log 호출/판 | log 호출 비용 | lines_of 모드 튜플 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 작전 1-3 | 1,253 | 1.2% | 37 | 0.14% | 3 | 0.04% | 1.1% |
| 달 회랑 100 | 12,996 | 1.7% | 449 | 0.23% | 8 | 0.01% | 1.2% |
| 태양 회랑 250 | 52,392 | 1.4% | 1,817 | 0.18% | 39 | 0.01% | 0.9% |
| 코스모 길레 1 | 3,715 | 1.0% | 141 | 0.14% | 1 | 0.00% | 0.8% |
| 코스모 시즌 바스커빌 3 | 40,692 | 1.1% | 1,933 | 0.20% | 24 | 0.01% | 0.8% |
| 길드 Lv1 | 16,164 | 1.1% | 561 | 0.15% | 16 | 0.02% | 1.0% |

단가: `self.mc[k]` 13.2ns, `rule_hits[k] += 1` 51ns, 타임라인 꺼진 `log(...)` 호출 188ns(가드로 막으면 13ns), `lines_of` 의 10개 값 튜플 650ns.
rule_hits 증가 수는 판 끝 `sum(rule_hits.values())`(일부는 `+= len(...)` 이라 실제 문장 실행 수보다 큼 = 비용 상한).

변형 실측(`mc.py` AST 변환 사본, `local/diet_variants/`, 100판 6케이스 합, 2바퀴 번갈아 최솟값): 원본 복사 13,013ms, log 가드 26곳 13,379ms(+2.8%), rule_hits 151곳 삭제 13,016ms(0.0%), 둘 다 13,166ms(+1.2%). 케이스별로 −14%~+8% 로 흩어져 **효과가 잡음보다 작음**. 둘 다 바꾼 사본도 기준선 36건과 바이트 일치(결과 불변 확인).

**판정**
- 설계의 «판당 −3~8%»는 실측이 받쳐 주지 않음. 진단 몫 합계는 약 1.5~2.5%: self.mc 읽기 1.0~1.7%(스위치를 지워도 남는 분기는 계속 읽으므로 줄어드는 건 그 일부), lines_of 튜플 약 1%, rule_hits 0.14~0.23%, log 0.04% 이하.
- `log()` 호출부 가드(3단계)는 타임라인이 꺼진 판에서 log 가 판당 1~39번만 불려 이득이 거의 없음. 하려면 결과 불변(변형 실측에서 확인)이라 위험은 없음.
- `support_report`·`assumptions_used`(호출당)는 판 수가 적고 전투가 짧은 작전 8판에서만 약 2%, 나머지는 0.5% 이하. wt-batch 일괄 API 쪽에서 다룰 일로 넘김(이번 범위 밖).
- 가장 싼 후보는 `lines_of` 의 모드 튜플(판마다 수백 번 같은 값을 다시 만듦)을 전투 시작 때 한 번 만드는 것 — 약 1%, 결과 불변. 3단계에 log 가드 대신 넣을지 메인이 판단.
- 판당 시간 대부분은 전투 계산 자체. 속도는 다이어트보다 일괄 API·Rust 쪽이 몫이 큼.

## 0단계 — 결과 불변 기준선

- 도구 `tools/diet_baseline.py`, 고정값 `tests/golden/diet_baseline.json`, 시험 `tests/diet_baseline_test.py`.
- 케이스 36 = 콘텐츠 6(작전 NOA 1-3·달 회랑 100·태양 회랑 250·코스모 길레 1단계·코스모 시즌 바스커빌 3단계·길드 방어전 Lv1 fire) × 파티 2(A `fei·professor-m·emily·wedding-carmen`, B `wedding-carmen·ceres-sun-supporter·amora·tyria`, 표준 육성·계정 자료 없음) × 시드 1·2·3, 각 8판.
- 케이스마다 해시 4개(sha256 앞 20자, `json.dumps(sort_keys, ensure_ascii=False, 구분자 고정)`): `api.simulate` 의 `raw_runs`·`runs`(per_run)·결과 전체(`runtime_ms_per_run` 만 뺌), `web.run_auto` 문자열(화면이 받는 그대로).
- 진행도 0 인 케이스 없음, 클리어 0%·100%·중간이 모두 있음(시험이 확인). 규칙 하나(`turn_gauge`)를 바꾸면 파티 A 시드 1 의 6케이스가 모두 어긋남을 확인.
- 프로세스마다 문자열 해시 시드가 달라도 같은 값(4회 실행 바이트 일치).
- 다시 고정은 엔진 결과가 «의도적으로» 바뀐 커밋에서만(`--write`, 사유는 HISTORY). 다이어트 단계는 고치지 않고 통과해야 함.

### `mc_cache_test` 의 `_KEEP` 재고정 설계(4단계 때 실행, 이번엔 안 함)

현재 `_KEEP` 은 legacy 값 약 100개를 `rules_override` 로 넘겨 세 해시(`_H_GWEN_MULTIWAVE`·`_H_PM_GWEN_MULTIWAVE`·`_H_GWEN_RNG_STREAMS`)를 고정함. `simulate` 는 모르는 규칙 키를 `ValueError` 로 막으므로(`api.py` 의 `unknown_keys`) 스위치를 지우면 해시가 바뀌기 전에 키 오류로 깨짐.

1. 4단계 첫 묶음 전 커밋: 같은 세 시나리오를 `rules_override` 없이(기본 프로필, `_KEEP_FORMULA` 의 COOP_CAP 0.30 은 공식 상수라 유지) 돌린 해시 `_H_*_DEFAULT` 세 개를 추가. 이 커밋에서 옛 `_KEEP` 해시 셋과 새 기본 해시 셋이 둘 다 통과해야 함.
2. 각 삭제 묶음: 지운 스위치를 `_KEEP` 에서도 지우고, 옛 해시가 바뀌면 그 시험을 «legacy 비교는 태그 `engine-legacy-final` worktree 에서»로 옮겨 적고 삭제. 기본 해시 셋과 `diet_baseline` 은 바뀌면 안 됨.
3. 모든 묶음이 끝나면 `_KEEP` 에는 남긴 스위치(ENGINE_MC_KEYS·화면이 넘기는 값·user/assumed 등급 등)만 남김.

## 1단계 — 묶음 1차 경량화

- `tools/build_simpack.py`
  - 파이썬 제외 목록 `EXCLUDE_PY` 에 `battlesim/metrics.py`(11,896B)·`battlesim/quick.py`(9,412B) 추가. 진입점(작업자는 `battlesim.web.run_auto` 와 `battlesim.api.Battle` 만 가져옴, `sim_worker.js`) → `api` → `mc` 경로에서 import 안 됨: 두 파일이 없는 묶음 폴더에서 36케이스가 돌고 `sys.modules` 에도 없음(`test_pack_same`), 실제 Pyodide 페이지 시험도 통과.
  - 규칙 파일은 축약본 `battlesim/rules/default.min.json` 을 실음(빌더가 default.json 에서 다시 만듦). 항목마다 `value`·`grade`·`kind`, `note` 는 가정 등급(`api.ASSUMPTION_GRADES`) 12항목만. `source`·`alt`·`legacy`·나머지 note·`_note` 는 뺌.
- `assumptions_used`(`api.py`)는 가정 등급 항목의 note 를 결과에 실음 → 그 note 만 남겨 `api.simulate` 결과 전체가 원본 규칙 파일과 바이트 같음. `web.run_auto` 는 `assumptions_used` 를 화면에 내지 않음. 축약본에서 note 를 다 빼면 `test_pack_same` 이 실패함을 확인(일부러 깨뜨려 봄).
- `battlesim/rules.py` `load_rules`: `default.json` 이 없으면(브라우저) `default.min.json` 을 읽음. PC·도구는 그대로 원본을 읽음. 브라우저에서 `LEGACY_OPTS`·`LEGACY_FORMULA` 는 비지만 엔진 경로는 안 씀.
- 화면·작업자(`sim_worker.js`)는 바꾸지 않았음 — 작업자는 매니페스트 목록 그대로 받아 같은 경로에 씀.

### 묶음 크기 전후(`sim/manifest.json`, Pyodide 런타임 `lib/pyodide` 13,781,345B 는 별도·불변)

| | 파일 수 | 바이트 | gzip(6) 합 |
|---|---:|---:|---:|
| 전(ed64b93) | 60 | 7,625,097 | 1,004,395 |
| 후 | 58 | 7,424,409 | 936,600 |
| 차 | −2 | −200,688 (−2.6%) | −67,795 (−6.7%) |

규칙 파일만: 200,339B(gzip 65,472) → 20,552B(gzip 5,994). 매니페스트 ver 가 `d4bb1b4df2a2` → 바뀌어 화면의 이전 시뮬 결과 캐시는 무효(설계 «위험: 캐시 무효»).
남은 큰 몫(2단계 후보): `rawdata/databook_main.json` 2,805,613B, `rawdata/foe.js` 1,954,851B, `rawdata/guide_app-core.js` 427,861B, `data/foe_spawn.json` 388,120B, `battlesim/mc.py` 369,408B, `battlesim/engine.py` 59,915B.

### 확인

- `tests/diet_baseline_test.py` 3건: PC 기준선 일치, 축약본이 최신, 매니페스트 파일만 복사한 폴더(Pyodide 조건)에서 기준선 36건 바이트 일치.
- 기준선 출처 대조: 태그 `engine-legacy-final`(ed64b93) 원본을 `git archive` 로 풀어 그 엔진·원본 default.json 으로 다시 계산 → 36건 전부 고정값과 같음(기준선은 수정 전 엔진 결과).
- e2e(`tests/e2e/test_page.py browser_sim`, 실제 Pyodide): `test_browser_sim`(3팀, 브라우저 결과 = PC 파이썬 결과)·`test_browser_sim_blocked` 통과. `sim_auto_and_override` 도 통과.
- 전체 `tools/run_tests.py --rebuild`(공용 잠금): 통과 264 / 실패 1, 건너뜀 6(환경). 실패 `md_control_chars_test`는 `HANDOFF.md:71` 의 제어문자(`work\allowlist\fable_…` 경로의 `\a`·`\f`)로 ed64b93(main)부터 있던 것 — 이번 변경과 무관, 고치지 않음. 재빌드 뒤 매니페스트 변화 없음.

## 4단계 — legacy 스위치 삭제(2026-11-22, 브랜치 `diet4`)

기본값(client)과 다른 `legacy` 분기를 7묶음으로 지웠음. 묶음마다 diet 기준선 36건·unify 기준선·`savior_rules_lines` 골든(기본 항목)·`golden_check`·`mc_cache_test` 기본 프로필 해시가 바이트 일치했고, 로컬 광역 대조(구원자 67명을 4명씩 묶은 34파티 × 콘텐츠 탭마다 1스테이지·회랑 3층·코스모 시즌 3보스 2레벨·길드 지원 6종 = 5,338건, 판 2개, 결과 전체 해시)도 매번 0건 불일치. `tools/unsupported_allowlist.py --diff` 도 매번 변화 없음.

- 0단계 마무리: `mc_cache_test` 에 기본 프로필 해시 3개(`_H_*_DEFAULT`)를 먼저 고정(7fb177a, 옛 `_KEEP` 해시와 함께 통과), 1묶음에서 `_KEEP`·옛 해시 삭제.
- 접기 방법: libcst 로 `self.mc['k']`·`.get('k')` 읽기를 기본값 상수로 바꾸고 비교·`and/or`·삼항·`if`·도달 불가 문장을 접은 뒤 손으로 검토(남은 상수 변수·주석·인자 정리). Battle 은 이제 모르는 MC 규칙 키를 받으면 `ValueError`(지운 스위치를 조용히 무시하지 않음).

### 지운 스위치 168개 (mc 절 237 → 69키)

| 묶음 | 커밋 | 수 | 스위치 |
|---|---|---:|---|
| 1 | 494d3ea | 26 | break_skill_residuals·barrier_formula·reaction_single_target_rng·level_max_source·supported_marker_targets·gille_promotion_target·auto_cond_hp_float32·foe_client_flow·fixstats_speed_zero·speed_min·self_hp_condition·last_damager_timing·potential_11026_vampirism·revive_toughness·damage_break_boundary·shield_enemy_count·random_basic_not_self·unique_id_stack·dispel_isbuff·se_cool_clock·revive_se_reset·skill_cool_change·independent_stack_limits·bloom_passive_levels·passive_se_order·hit_ally_skill_end |
| 2 | 6bc6dba | 24 | stack_react_timing·target_break_condition·target_condition_set·source_buff_list·foe_forced_coop·myinfo_potential_coverage·ally_turn_self·break_domain_category·ally_cd_tick·dot_hot_lifetime·dot_hot_order·wave_extra_turn·turn_start_order·wave_foe_battle_start·guard_skip_immune·dead_keep_dnp·revive_after_spawn·add_damage_guard·stat_select_int·buff_ban_force·skill_order·foe_skill_order·empty_attack·dispel_on_attack |
| 3 | 981160c | 24 | buff_count_source·hit_stack_order·debuff_instance_count·myinfo_combat·enemy_cd_end_order·revenge_rate·nova_force_cap·chain_target_stat·target_hp_condition·not_self_stack·target_toughness_condition·nova_skill_gain·nova_force_effects·nova_slot_effects·taunt_skill_end_duration·any_turn_clock·any_turn_source·ally_auto_target·auto_skill·turn_limit_unit·foe_auto·revenge·reaction_timing·wave_ally_gauge |
| 4 | 3868ae3 | 28 | enforce_timing·enforce_target·self_enforce_target·variant_self_state·turn_unit_debuff_cond·auto_marker_lines·ally_auto_lines·instant_damage·break_skill_level·break_skill_scale·guard_normal_hit·enemy_leader·level_buff_decrease·buff_fresh_scope·break_gauge_actor·purify_nova_scope·preemptive_reduce·omega_dispel·check_buff_scope·check_buff_expiry·shield_tick·caster_death·stage_fx_target·evade_model·wave_carry·break_skill_domain_clock·break_domain_revive·break_skill_reduce |
| 5 | 84e5c32 | 23 | barrier_depletion·dispel_shield·dispel_instance·dispel_order·dispel_evade·sleep_wake·dispel_attack_names·debuff_ban_flag·gauge_cd_immune·gauge_up_immune·cc_immune_buff·immune_group_resist·abs_hit_terms·nullifier_count·dot_hit_result·bskill_nullify·evade_ignore_resist·se_force_apply·heal_tie·foe_react·buff_step_group·cosmo_hyper_true_target·immune_force_apply |
| 6 | 2671165 | 25 | damage_vampirism·cosmo_drain_category·cosmo_speed_floor·cosmo_boss_barrier·cond_count_bind·rekindle_apply·chain_guard·target_row_slot·living_slot_order·local_chance·guard_precision·guard_tie·foe_react_buff_count·foe_react_timing·toughness_elem·own_turn_condition·ally_break_gauge·summon·enforce·preemptive_defense·effect_dur_extend·gauge_conditional·role_damage_terms·local_vs_element·permanent_accuracy |
| 7 | fc5f435 | 18 | battle_end_mode·guild_bridal_kill_reset·guild_count·buff_ban·break_point_hits·react_hist_unit·guild_boss_nv_sum·break_auto_blocked_cc + 정규화 10개(skill_end_timing·se_independent_roll·smile_waterbomb_scope·scarlet_pinball_marker·cristelle_ignite_targets·gauge_lock_order·heal_cleanse_skill_end·marker_se_flow·claire_preemptive_marker·belgras_stage_se) |

옛 동작 비교는 태그 `engine-legacy-final`(ed64b93) worktree 에서(설계 4절). 옛 값으로 돌리던 측정 도구(`tools/measure_*`·`check_followup_quick`·`web_leads_audit` before 모드 등)의 legacy 모드도 그 태그에서만 동작함(이 브랜치에서는 `simulate` 가 모르는 규칙 키로 거부). `tools/boss_hit_diagnostic.py` no_fx 모드는 명시적으로 막았고, `tools/boss_action_diagnostic.py` 는 지운 키 읽기를 뺌.

### 남긴 code+legacy 스위치 21개

- 기대값 엔진 골든이 legacy 로 고정: `engine.ENGINE_MC_KEYS` 10개(dmg_cap_scope·turn_gauge·stat_stage·stat_floor·buff_maxhp·chain_round·chain_pen·chain_skill_damage_up·chain_stat_true·dot_formula).
- 설계서 목록: power_penalty(화면 `rules_override`)·fixed_true_formula(값 legacy)·superarmor_damage_ban(off)·counter_slot_timing(end).
- 측정 도구가 legacy 를 읽음: auto_unable_break·auto_remove_filter·auto_se_reselect·auto_hp_float32·auto_empty_marker(`tools/measure_autotarget_12.py`·`tests/autotarget_12_test.py`). 설계 초안 묶음엔 `auto_*` 가 있었으나 «남길 것» 목록과 겹쳐 남김(판단 필요).
- unify 기준선이 옛 값 경로를 고정: chain_timing(`raidex_*_imm`·`guild_mountain_L1_imm` 케이스가 `immediate` 로 코스모·길드 즉시 연쇄 경로를 지킴).
- 옛 경로만 가정·커뮤니티 등급 키를 읽음: enemy_auto_target(weighted 경로가 target_row_weight·target_defender_mult·target_mode 를 씀 — 이 셋은 «남길 것»(assumed·community)).
- opts·formula 의 legacy(17개 안팎, `rank_check`·P1 골든)는 손대지 않음.

### 구조 변화

- `normalized_lines(d, rules)` → `normalized_lines(d, native)`. 전투(`lines_of`)는 native=True, 정적 지원 진단(`support_report`)은 native=False(옛처럼 숨은 표지 줄을 설명문 그대로 검사). 정규화 스위치 9개는 구원자 67명·적 4,478종 대조에서 진단 결과가 불변이라 완전히 접었고, marker_se_flow 만 엘리사·린 진단이 달라져 이 인자로 보존.
- `lines_of`·`kind_lines` 의 판마다 만들던 10개 값 모드 튜플 삭제(0단계 실측 약 1%).
- 지운 인자·속성: `Battle(mc_overrides=)`, `api._unit_key(use_combat)`, `myinfo_combat.select_skills(bloom)`·`apply_potentials(coverage)`, `savior_rules.KEEP_NATIVE_SELECTOR` 의 스위치 열, `Battle._dispel_shield_ok`, `Battle.guild_count`.
- 남긴 내부 장치: `Unit.ban_refuse`(항상 True — 캐시 시험 `accel_test`·`cosmo_speed_test` 가 옛 «걸린 강화도 끔» 경로를 직접 켬). `rule_hits` 는 그대로(지운 스위치 이름의 카운터도 유지 — 시험이 경로 확인에 씀).
- toughness_elem 의 대안 모델(video·db·on), ally_break_gauge 의 skip·reset, guild_boss_nv_sum 의 stage·bake 도 함께 없어짐.

### 줄 수·크기 전후(7fb177a → fc5f435)

| | 전 | 후 | 차 |
|---|---:|---:|---:|
| `battlesim/mc.py` 줄 | 6,412 | 6,081 | −331 |
| `mc.py` 안 `self.mc[...]` 읽기 | 321 | 83 | −238 |
| `battlesim/**` 변경 | | | +631 / −1,181 |
| `tests/**` 변경(120파일) | | | +599 / −2,439 |
| `default.json` | 306줄 · 200,339 B | 138줄 · 73,263 B | −63% |
| `default.min.json`(묶음에 실림) | 20,552 B | 11,727 B | −43% |
| 묶음(`sim/manifest.json` 62파일) | 7,433,219 B (gzip 943,116) | 7,393,931 B (gzip 935,131) | −39,288 B (gzip −7,985) |

설계 추정(`mc.py` −600~1,000줄)에는 못 미침: 지운 분기 상당수가 1~3줄 조건이었고, 옛 분기만 있던 함수는 드묾.

### 판당 시간 전후

`tools/diet_profile.py --worker` 로 7fb177a 엔진(`git archive`)과 이 브랜치 엔진을 같은 프로세스 조건에서 번갈아 2바퀴, 100판 최솟값(데이터·규칙 파일은 각 엔진 것, 화면 옵션 + raw_runs, 이 PC 단일 프로세스).

| 케이스 | 전 100판 ms | 후 100판 ms | 판당 ms 전→후 | 차 |
|---|---:|---:|---:|---:|
| 작전 NOA 1-3 | 115 | 100 | 1.15 → 1.00 | −13.7% |
| 달 회랑 FLOOR 100 | 960 | 824 | 9.60 → 8.24 | −14.1% |
| 태양 회랑 FLOOR 250 | 3,881 | 3,287 | 38.81 → 32.87 | −15.3% |
| 코스모 길레 1단계 | 338 | 298 | 3.38 → 2.98 | −11.8% |
| 코스모 시즌 바스커빌 3단계 | 3,547 | 3,115 | 35.47 → 31.15 | −12.2% |
| 길드 방어전 Lv1(fire) | 1,340 | 1,166 | 13.40 → 11.66 | −13.0% |
| 합 | 10,181 | 8,790 | | −13.7% |

두 바퀴 모두 같은 방향·비슷한 크기(바퀴 사이 흔들림 1~2%). 0단계 추정(진단 몫 1.5~2.5%)보다 큼: 스위치 읽기 238곳·판마다 만들던 정규화 모드 튜플(`lines_of`·`kind_lines`)·옛 경로 조건 검사가 함께 빠진 몫으로 봄(원인별 분해는 안 함 — 미확인). 로컬 광역 대조(5,338건)도 92초 → 80초.

### 시험

- 지운 시험 함수 153개(이름만 바꾼 8개 별도) — 목록은 `docs/HISTORY.md` 2026-11-22 «엔진 다이어트 4단계» 절.
- 기본값으로 바꾼 시험: 옛 값으로 장면을 고정하던 시험은 판 번호·편성을 다시 고름(target_conditions·guild_bridal_kill·followup_d·rules_e), `living_slot_order=legacy` 로 후보 순서를 고정하던 시험은 게임 칸 순 배치로(clash_runtime·dmg_terms_1114·stat_turn_1115·forced_coop), 옛 계수 기대값은 기본 계수로(break_skill_test 옛 모델 클래스 → `BreakSkillBasicTest`, ×1.85·레벨 가산·감소 무시), `allowlist_break_test` 는 분담 산수만 보려고 `BASE_MULT` 1 로 패치.
- 변이 시험(`--mutations`·`--mutate`)의 기준 문자열을 접힌 코드로 갱신했고, 옛 값 `patch.dict(MC_OPTS, k='legacy')` 변이 항목은 삭제.

### 확인

- 전체 단위 시험 `tools/run_tests.py --rebuild`(공용 잠금): 통과 269 / 실패 2. 실패 2건(`break_skill_1121_test` 가 지운 `legacy_setup` 이름을, `engine_cache_test` 가 지운 `_unit_key(use_combat)` 인자를 흉내 냄)은 시험 쪽 이름만 고쳐 단독 재실행 통과. 재빌드 뒤 `index.html`·매니페스트 변화 없음.
- e2e 전체(`--e2e venv-pw __e2e_only__`, 실제 Pyodide 포함): 통과 24 / 실패 0.
