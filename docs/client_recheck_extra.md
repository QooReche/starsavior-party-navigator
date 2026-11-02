# 2026-11-03 — 추가 규칙 누락 점검

## 범위

- `battlesim/rules/default.json`의 assumed/data 및 커뮤니티·영상 근거 규칙을 빠르게 훑고, 협공 세 규칙과 바로 추적되는 상수·시계를 확인했음.
- 근거 빌드는 비공개 `starsavior-static-data/decompiled/BUILD.md`의 Steam **26314877**임. 표 기록 빌드 **26291832**와 내용 동일성은 미확인임.
- 아래 N/T/S/U는 각각 `decompiled/NKM/NKM.decompiled.cs`, `decompiled/NKM.Templets/NKM.Templets.decompiled.cs`, `decompiled/Star.Templets/Star.Templets.decompiled.cs`, `decompiled/Cs.UnityShare/Cs.UnityShare.decompiled.cs`임. 표 경로는 비공개 저장소 루트 기준임.
- 이 문서는 조사 결과와 근거 갱신 제안임. 조사 담당은 엔진·rules·골든·해시를 수정하지 않았음. 계정 자료를 쓰지 않았음.

## 확인한 규칙

| 규칙 | 결과·확인 범위 | 현재 빌드 근거 | 반영 제안 |
| --- | --- | --- | --- |
| `opts.coop_trigger=basic_only` | 일반 본행동 뒤 선택 스킬이 기본기인 경우에만 협공자를 선정함. 추가 시전 함수 안에서 재귀 협공을 고르는 구조가 아님 | N:14857–14867; 선정 함수 N:15482–15521 | 값 유지, grade=code, source 갱신 |
| `opts.coop_single=true` | 선정 함수는 강제/일반 후보 중 단일 객체만 반환하며 호출부도 협공 1회만 시전함 | N:15508–15521,14863–14867 | 값 유지, grade=code, source 갱신 |
| `opts.forced_coop_slot=shared` | 강제 후보가 있으면 즉시 반환하여 일반 후보 확률 판정을 생략함. 후보가 없으면 일반 판정으로 내려감 | N:15509–15518; 본행동만 호출 N:14857–14867 | 값 유지, grade=code, source 갱신 |
| `opts.forced_coop=true` | 강제 효과는 대상에게 플래그를 붙이고, 이후 선택된 대상이 기본기를 사용함 | N:5230–5232,15662–15667,14865–14867; 턴 종료 초기화 N:13569–13572 | 기본기 추가 시전 근거를 code로 올릴 수 있음. 효과 대상 선정과 협공자 추첨은 아래처럼 구분 필요 |
| `formula.BASE_MULT=1.85` | 피해 기초값에 공용 DamageScale을 곱함. 로더는 만분율을 배율로 변환함 | N:17740–17744; T:29958–29960; `tables/Plain/CLIENT_CONST_TEMPLET.json`:109 | 값 유지, grade=code, source 갱신. 전체 피해식 동등성을 뜻하지 않음 |
| `formula.DEF_K=3000` | 비PvP 방어율은 방어력/(방어력+DefenceConst), 별도 관통 보정이 뒤따름 | N:17786–17806; T:29962; `tables/Plain/CLIENT_CONST_TEMPLET.json`:110 | 값 유지, grade=code, source 갱신 |
| `formula.DEC_CAP=0.5` | 감소 합에 양수 RATE_DAMAGE_REDUCE_TOTAL_LIMIT 상한을 적용함 | N:17762–17783; T:29982–29985; `tables/Plain/CLIENT_CONST_TEMPLET.json`:133–136 | 값 유지, grade=code, source 갱신. 감소 항목 각각의 완전성은 별도임 |
| `mc.rand_range=[0.95,1.0499]` | 정수 Range(9500,10500), 상한 제외 후 만분율 변환임. 현재 MC의 0.0001 간격과 같음 | N:17880–17889; U:1864–1866; `battlesim/mc.py`의 `rand` | 값 유지, grade=code, source 갱신. RANDOM_DAMAGE 설정이 켜진 비고정 피해 경로임 |
| `mc.any_turn_clock=true` | 주인 턴은 일반 지속 차감, 다른 유닛은 GlobalTurnCounting만 차감함. 해당 속성은 부여 턴 차감 제외도 우회함 | S:4712; N:13537–13548,13234–13239,3973–3988,4565–4573 | 값 유지, grade=code, source 갱신. 개별 버프 제외·삭제 세부를 전부 검증한 것은 아님 |
| `mc.enemy_cd_tick=turn_end` | TURN_END 효과·지속 차감 뒤 쿨 차감 함수가 호출되고 양수 쿨을 1 줄임 | N:2013–2021,2038–2040,3578–3590 | 값 유지, grade=code, source 갱신. 이 키는 enemy_cd_native=false의 호환 경로이며 실제 기본 순서는 enemy_cd_end_order가 담당함 |
| `mc.counter_inc=0.1` | 상대의 마지막 스킬 칸과 시전자의 현재 선택 칸이 같으면 DamageUpRate를 증가 합에 넣음. 값은 1000/10000임 | N:3573–3575,17943–17951,17759; T:29531–29544; `tables/Plain/CLIENT_CONST_TEMPLET.json`:111–114 | 핵심 값·일반 공격 조건은 같음. 지속 피해에서 시전자 선택 칸의 수명은 이번에 추적하지 않아 기존 data 등급 유지 제안 |

## 강제 협공의 두 대상 선정 단계

**강제 효과를 누구에게 줄지와 강제 협공자 최종 추첨을 구분해야 함.**

1. 효과 타겟 지정 후 `ForceCrossAttack`이 그 타겟의 플래그를 true로 만듦(N:5230–5232).
2. 본행동 종료 뒤 자신을 뺀 같은 편에서 아머브레이크·기본기 사용 불가·DisableCrossAttack을 제외하고 강제 플래그가 있는 후보를 모음(N:15508–15509,15644–15667).
3. 강제 후보 중 균등 1명을 고름. 후보가 없을 때만 일반 후보 전원 확률 판정 뒤 성공 집합에서 균등 1명을 고름(N:15510–15518,15606–15641; U:1874–1876).
4. 턴 종료에 강제 플래그를 지움(N:13569–13572).

프로페서M은 다음 표 연결 때문에 평소 후보가 높은 공격력 아군 1명으로 제한됨. 따라서 최종 추첨을 random으로 바꾸더라도 모든 아군을 곧바로 랜덤 대상으로 삼으면 클라와 달라짐.

- `tables/SE_TEMPLET_SKILL_1.json`:23711–23723은 체크 버프 대상에 AutoTargetId=52를 씀.
- `tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json`:378–383은 행동 가능·협공 불가 없음·가장 높은 공격력 필터임.
- `tables/SE_TEMPLET_SKILL_1.json`:23760–23772는 강제 협공 효과에 AutoTargetId=10392를 씀.
- `tables/Plain/AUTO_SKILL_TARGET_TEMPLET.json`:659–664는 행동 가능·협공 불가 없음·앞서 체크 버프를 받은 대상 필터임.
- `data/auto_skill.json`의 교수M `lines`·`variant_lines`에 이 연결이 이미 있음. 기존 `Battle.forced_coop(owner, ctx, len(tg))`는 실제 타겟 `tg`를 버리고 공격력으로 재선정하므로 클라의 두 단계를 구별할 필요가 있음.
- `opts.forced_coop_target`의 옛 설명은 교수M 효과 대상 선정에 관한 것이었음. 새 random 값의 설명은 **효과 대상 필터를 통과한 강제 후보 중 최종 추첨**으로 고쳐야 함. 커뮤니티 관찰의 높은 공격력 후보 1명은 위 표와 모순되지 않음.

## 남긴 후보

아래는 이번 짧은 점검에서 새 빌드 전체 경로를 확인하지 못한 후보임. 이미 A/B/C/D에서 조사한 내용과 겹치는 항목도 있어 다음 점검은 해당 문서의 미확인 범위부터 이어가기로 함.

- 피해·명중: `AOE_DIV`, `BREAK_DEC`, `ELEM_HIT`, `debuff_model`, `dot_snapshot`, `gear_order`, `dmg_reduction`의 개별 감소 항목, `guard_mode`의 수호자 독립 난수·반응 제외 전체, `counter_inc`의 지속 피해 선택 칸, `enemy_same_formula`, `evade_model`, `toughness`, `toughness_elem`, `basic_tough`, `power_penalty`.
- 대상·시계·상태: `target_defender_mult`, `target_mode`, `enemy_leader`, `leader_speed`, `check_buff_expiry`, `shield_tick`, `caster_death`, `stage_fx_target`, `wave_carry`의 HP/쿨/버프 세부, `heal_target`, `sudden_death`의 사망·부활 처리. `wave_carry` 설명의 게이지 유지 문장은 현재 `wave_ally_gauge=reset` 기본과 맞지 않는 오래된 설명임.
- 노바·브레이크: `nova_policy`의 오토 미사용 근거, `break_skill_point_cap`, `break_skill_cd_unit`, `break_skill_domain_clock`의 전체 효과 지속·발동 행동 포함·사망 경계, `break_skill_fixed`, `break_skill_model`의 영역 재부여와 행성 정화 조건 8000.
- 이미 별도 규칙이 대체한 호환 설명: `enemy_skill_ai`, `enemy_init_cd`, `enemy_init_cd_special`, `init_cd_frac`. 기본 클라 경로와 legacy 민감도 경로를 혼동하지 않도록 설명 정리가 필요함.
- 지표·기대값 모델 자체의 가정: `TICK_PER_TURN`, `unknown_cond_p`, `debuff_success`, `inf_hp_frac`, `break_p`, `kill_p_inf`, `no_debuff_p`, `enemy_def`, `enemy_spd`, `ref_enemy_count`, `enemy_resist`, `debuff_state`, `gauge_expect`, `turn_ticks`, `max_events`, `max_depth`, `unknown_cond`, `manual_burst`. 이 항목은 클라 상수로 승격할 대상과 모델 정책을 먼저 구분해야 함.
- 게임 PC에서 표 26291832와 DLL 26314877의 내용·추출 시점 동일성을 확인하기로 함. 이번 근거는 현지 두 자료의 연결을 읽은 결과이며 빌드 번호 불일치를 해소하지 않았음.
