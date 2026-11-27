# 바스커빌 블랙박스 시나리오 실패 판정

2026-11-19, 기준 커밋 `a0d41d8`. 외부 블랙박스 시험을 `tests/baskerville_scenario_test.py`로 가져왔음. 세 실패 모두 시험 가정 오류였으며 엔진·규칙·게임 자료는 변경하지 않았음.

## 근거 위치

- N = `E:/AI_mk2/_builds/26752678/decomp/set10/clean/NKM/NKM.decompiled.cs`.
- T = `E:/AI_mk2/_builds/26752678/rebuild/T/`.
- 비공개 static-data를 pull했고 `check_build.py`를 실행했음. 비공개 저장소의 디컴파일은 26610546으로 설치본과 달랐음. 사용자 지정 26752678 재추출본의 `set10/dll` 10개를 이 PC 설치 DLL과 SHA-256으로 다시 비교하여 10/10 일치를 확인했음. 옛 디컴파일은 근거로 쓰지 않았음.
- 작업 브랜치 `bask-s23`는 추적 브랜치가 없어 pull이 적용되지 않았음. 메인 작업 트리는 수정하지 않았음.

## test_05b — 기절 면역을 기절로 센 판독 오류

원본 `has(u, '기절')`은 효과 이름의 부분 일치를 사용했음. 시험에서 부여한 `기절 면역`까지 기절로 세어 보유자 0명인데도 `(False, True)` 4개를 반환했음. 실제 `u.has('기절')`은 전원 false였음.

T `CLIENT_SE_TEMPLET_SKILL_2.json:33619-33631`의 HYPER_03은 NSETT_AUTO_ENEMY·AutoTargetId 1028·ForceApplyEffect이며, `plain/AUTO_SKILL_TARGET_TEMPLET.json:594-597`은 심장 마비의 IsSpecificBuff 조건임. N:7532-7544의 필터는 일치한 대상이 없으면 false, N:7152-7181은 전체 대상형에서 성공한 필터가 없으면 null, N:16591-16599는 이를 빈 배열로 반환함. 대체 대상은 없으며 강제 적용도 대상 선택을 우회하지 않음(N:4318,4407,6112).

정확한 이름으로 기절을 검사하도록 교정했음. 보유자 0명·2명·4명을 검사하며, 면역이 있어도 보유자에게만 기절이 걸려야 함. 원본은 4명 전원 보유 사례만 검사해 잘못된 부분 일치가 성공 검사를 통과시켰음.

## test_02 — 별도 회복 효과와 송곳니 조건을 빠뜨린 가정 오류

회복 호출의 시전자·대상·효과 줄·실효량을 기록했음. 23,532→24,340의 +808은 카르멘 고유 패시브의 기본기 후 아군 전체 회복(자신 HP 2.5%)이었음. 바스커빌 PASSIVE1_05 호출은 없었음.

T `CLIENT_SE_TEMPLET_SKILL_1.json:35660-35674`의 COND_WEDDING_SHIELDER_UNIQUE_PASSIVE_01_04는 BI_HEAL·자신 NST_HP·HealRate 250·NSEAT_SKILL_END임. 바스커빌의 BI_HEAL은 T `CLIENT_SE_TEMPLET_SKILL_2.json:33799-33813`의 PASSIVE1_05이며 조건 55182의 회복 표지 보유가 필요함(`plain/SKILL_CONDITION_TEMPLET.json:10033-10036`).

HP 차에서 기록된 별도 회복량만 빼고, 해제 자체의 회복은 정확히 0이어야 한다는 기대를 유지했음. 실제 회복 출처가 카르멘 기본기 패시브인지도 단언함. N:3070-3081은 전투 중 상한 감소 시 초과분만 절삭하고 상한 증가로 회복하지 않음. 버프 갱신의 능력치 재계산 연결은 N:4493-4494·2916-2918임.

원본의 «매 타격마다 송곳니 +1» 기대도 잘못됐음. PASSIVE1_02는 조건 55181임(T `CLIENT_SE_TEMPLET_SKILL_2.json:33752-33764`). 이 조건은 시전자 심장 마비가 정확히 1중첩일 때만 참임(T `plain/SKILL_CONDITION_TEMPLET.json:10024-10029`). 마지막 중첩 전에는 송곳니 0, 마지막 해제 때 1을 검사하도록 고쳤음.

## test_05 — HP 순변화와 피해량을 혼동한 측정 오류

원본 4개 잔존 사례의 실제 받은 피해는 26,069였음. 동시에 카르멘 잠재력이 4,000,576 회복하여 HP 순손실은 −3,974,507이 됐음. `maxhp0 ×1000` 설정이 최대 HP 기반 회복량도 키웠음. 출처는 T `CLIENT_SE_TEMPLET_POTEN.json:1524-1540`의 POTEN_PASSIVE_4010101(BI_HEAL·자신 NST_HP 8%·피해 처리 후 25%)이며 HYPER_04~08의 해제 회복이 아니었음.

피해는 `taken` 통계의 시전 전후 차로 측정함. 동시에 `시전 후 HP − 시전 전 HP = 실제 회복 − 피해`를 단언하여 해제에 잘못된 회복을 넣어도 검출함. 원래 실패한 조건에서 잠재력 회복이 피해보다 큰 사례도 유지했음.

원본은 12~16회 타격하면 송곳니가 모두 4중첩일 것으로 가정했지만, 실제 0/2/4개 잔존의 송곳니는 각각 4/2/0개였음. 배율만 비교하는 시험은 송곳니를 0으로 통일했음. T `CLIENT_SE_TEMPLET_SKILL_2.json:33589-33601`의 HYPER_01(+10%/카운팅 객체)과 N:5663-5678·16396-16405를 기준으로 1:1.2:1.4를 정수 절삭 오차 안에서 검사함. 한 명에게 4개와 네 명에게 1개씩을 비교하여 보유자 수가 아닌 객체 수 합인지도 검사함.

## 검증

- 시나리오 8/8 통과, 기존 01·03·04·06·07 기대 유지했음.
- 새 변이 6/6을 실행 오류가 아닌 단언 실패로 검출했음: 빈 자동 대상 전원 대체, 개별 해제 회복, 궁극기 해제 회복, 카운팅 피해 배율 제거, 객체 수 대신 보유자 수, 면역 무시 제거. 원복 뒤 8/8 통과했음.
- 기존 `baskerville_client_test.py` 10/10 및 변이 10/10 통과했음.
- 전체 시험과 빌드 결과는 `docs/HISTORY.md`의 같은 날짜 시나리오 절에 기록함.

재현:

```text
python -X utf8 -I tests/baskerville_scenario_test.py --mutations
python -X utf8 -I tests/baskerville_client_test.py --mutations
python -X utf8 -I tools/build_simpack.py
python -X utf8 -I build_party_html.py index.html
python -X utf8 -I tools/run_tests.py
```
