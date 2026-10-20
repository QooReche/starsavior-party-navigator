# 파티 편성 네비게이터 인수인계 (다음 세션용)

최종 갱신: 2026-10-20. 새 세션은 `AI\CLAUDE.md` → 이 파일 → `README.md` 순으로 읽을 것. 메모리 `party-navigator` 에도 요약 있음.

## 상태
- 저장소: https://github.com/QooReche/starsavior-party-navigator (**공개**, GitHub Pages: https://QooReche.github.io/starsavior-party-navigator/). 최신 커밋은 `git log` 로 확인.
- 로컬: `E:\AI_mk2\starsavior-party-navigator` (2026-10-20 새 PC. 옛 PC 는 `AI\partynavigator\src`). C: 용량 부족이라 작업 폴더는 `E:\AI_mk2\` 아래. 웹 페이지 `index.html` 은 `python -X utf8 -I build_party_html.py index.html` 로 생성해 커밋한다(Pages 가 루트 index.html 서비스).
- 사용자 허락: databook 재사용, 이미지(아이콘·초상화·브레이크 스킬) 저장·공개 허락 확인됨(2026-10-19).

## 진행 중: 전투 시뮬레이터 분리·고도화 (2026-10-20 시작)
- 확정 설계 = `docs/battlesim_design.md`(Claude 초안 → codex·Fable 독립 검토 → 합의안). 공식·수치 근거 = `docs/formulas_local.md`(데이터북 계산기 코드·로컬 데이터), `docs/formulas_web.md`(공식 공지 114건·아카·패치 연표).
- **P0 완료**: `fetch_sources.py` foe.js 버전 키 버그 수정(main.js `__SSV`), 회귀 기준 `tests/golden_check.py`(`--write` 저장 / 인자 없이 대조, 일부러 상수를 바꿔 실패하는 것 확인), 실측 기록 양식 `calibration/`.
- **P1 완료**: 엔진을 `battlesim/` 패키지로 분리(구성 `battlesim/README.md`), 불확실 수치는 `battlesim/rules/default.json`(값·근거 등급), `tools/sim_damage.py` 는 호환 껍데기(값 교체도 실제 모듈로 전달 — `tests/shim_compat_test.py`). 골든 정확 일치, `tools/update.py` 전체 재생성 시 `data/`·`index.html` 바이트 동일, 브라우저 화면·콘솔 오류 0 확인. codex 검토의 차단 1건(껍데기 상태 전달) 수정 완료. `lines` 명령으로 파싱 결과 덤프(노바 줄 314 중 엔진 반영 76).
- **P2 완료**(미커밋 상태로 검토 대기일 수 있음 — `git status` 확인): 확인된 규칙으로 교정, 교정마다 `battlesim/rules/default.json` 스위치(`legacy` = 교정 전 값). 협공 = 아군 기본기 뒤·1명, 노바 = 오토 기본(버스트 안 씀)·수동이면 팀 공용 풀, 효과 적중 = 적중 - 저항 +-상성(적 저항은 `foe_stages.json` 에 새로 넣음, 기준 적 60%), 강제 협공 대상 = 현재 공격력, DoT 매 틱 재계산, 장비 순서, 감소 합(상한 50%), codex 2차 검토 수정(강제 협공도 협공 1명 자리 공유·추가 시전에서 미발동, 실패한 약화는 상태 불변·지속 피해 시전자별, 적 게이지 감소 기대값). 영향 표·해석 = `docs/sim_changes.md`(구원자 순위 Spearman 0.996, 150팀 0.992, 상위 20팀 19 유지; 왈츠 아세라 -16%, 유미나 -20%). 측정 `tests/rank_check.py`, 스위치 시험 `tests/rules_test.py`(일부러 깨뜨려 실패 확인), P1 골든 보관본 `tests/golden/sim_golden_p1.json`.
- **다음 = P3** 적 행동(스킬·쿨·광역·대상 선택)·아군 HP·생존, 난수 굴림·seed/n_runs. P2 에서 미룬 것: 카운터 +10%(적이 쓴 칸 필요), 리더 속도 +10(리더 입력 필요), 적 자신의 피해 감소 기믹·스테이지 fx·면역(감소 합 구조만 있음), 브레이크 빈도(P5). 남은 비차단: 이벤트 순서·시드·추적 로그는 P3 확률 엔진과 함께, `Sim.COND_KEYS` 는 `cond_weight` 와 중복 관리(같이 고칠 것).
- 알려진 잡음: `tools/update.py` 가 `docs/synergy_tags_review.md` 줄 순서(집합 순회)와 일부 파일 줄바꿈(CRLF)을 바꿔 쓴다 — 내용 변경 아님, 커밋 전 `git checkout --` 로 되돌릴 것.
- 데이터: 로컬 = 10/15 패치(2.50), 라이브와 동일(10/20 확인). **10/22 작전 26~37 최종보스 공격력 하향 예정 → 이후 `fetch_sources.py` 로 재수집.**
- 사용자 결정(10/20): **오토 기준이 기본**, 화면에 오토/수동 선택, 수동이면 스킬 순서 가이드(서순) 표시 → 설계 4-1절.

## 구현된 것(요약, 상세는 README)
콘텐츠/스테이지별 4인 파티(전열2/후열2, 인게임 편성 UI 배치) + 브레이크 스킬 + 리더(속도 +10) 추천 + 대체 후보(이 구원자만 빠졌을 때 팀 점수순), 속성 상성, DB 티어, 스킬 연계 시너지 1,120쌍과 구조도(Cytoscape), 전투력 보정(패널티) 입력, 성간 회랑 속성 제한(태양/달/별 회랑은 해당 속성만, 사용자 확인), 스테이지 적 기믹 44유형 반영(개인 점수 + 필요 슬롯 보너스), 보유 구원자/브레이크 스킬 선택(왼쪽 서랍, localStorage 저장), 추천 근거는 기본 숨김("추천 근거 보기" 체크).

## 다른 PC 에서 이어서
`docs/PORTING.md` 에 clone 부터 업데이트 절차까지 정리했다. 원본 입력 자료는 `rawdata/` 에 포함.

## 게임 업데이트 대응
`python -X utf8 -I tools/update.py <databook main.json>` (태그·연계·분류·전투력 표·기믹 재생성 + 변경 요약). 입력은 저장소에 없음: 데이터북 `data/main.js` 를 JSON 으로 푼 파일, `tools/raw/foe.js`. 가이드 DB 변경(티어·구원자 목록·이미지)은 `data/db_tier.json`·`savior_reco.json`·`saviors_index.json`·`tools/fetch_images.py` 로 따로 갱신. 수동 보정: `data/synergy_overrides.json`(연계), `party_contents.json`(가중치·규칙).

## 미검증/알려진 한계
- 가중치(티어·상성·시너지·기믹·전투력 반응)는 모두 임의값, 실전 편성과 비교 검증 못 함. 사용자가 오토 전투 기준으로 직접 써 보고 이상한 편성을 알려 주는 것이 가장 정확한 보정 경로.
- 기믹의 영향 방향은 대부분 추정(피격이 타수 단위인지 스킬 단위인지 원문 없음). 태그가 많은 구원자(에핀델 등)가 유리해지는 편향.
- 스킬 연계 724/1,120쌍은 키워드 추정. 리더 추천·브레이크 스킬 추천·전투력 부족 시 반응은 추정.
- 성간 회랑 속성 제한은 사용자 확인뿐(데이터북·가이드 DB·제3자 DB에 문구 없음). 다른 콘텐츠의 편성 제한은 미조사.
- 구원자별 리더 효과는 데이터 없음(속도 +10 이 리더의 유일한 효과라고 사용자가 확인).
- 브라우저 화면 확인은 로컬 서버(127.0.0.1) + Chrome 확장으로 함(file:// 불가). 모바일/라이트 모드 미확인.

## 화력 지표(2026-10-20 추가)
`tools/sim_damage.py` 시뮬레이터 → `data/damage_index.json` → 팀 점수에 화력 항(`party_contents.json` damage 가중치 0.6 보스/0.35 일반) + 딜러 최소 2명 안전망(-3). 한계는 README·`docs/sim_report.md` 참고(장비 제외 상대 비교, 협공 규칙 추정).

## 다음 후보
0. 화력 지표 검증: 인게임 결과와 비교, 장비·아르카나·브레이크·반응형 스킬 반영, 서포터/디펜더 생존(버티기)을 시뮬레이터에 넣기.
1. 기믹이 바꾼 조합을 구조도에 반영(해당 스테이지에서 중요한 슬롯끼리의 연계 강조) — 사용자 요청, 미구현.
2. 플래시 포인트·코스모 게이트 보스 지정 입력(현재 스테이지 단위 기믹은 반영, 보스별 속성 입력 UI 없음).
3. 가중치 보정: 사용자의 이상한 편성 사례 수집 → `party_contents.json`·`synergy_overrides.json` 조정.
4. 구조도 글자 크기/전체 지도 가독성, 모바일 확인.
5. 다른 콘텐츠 편성 제한 조사(코스모 게이트 파티 간 중복 제한 등), 가이드 DB 운영자에게 통합 제안용 설명 정리.

## 작업 습관(이 프로젝트에서 반복된 함정)
- 한글·백슬래시가 든 코드는 bash heredoc 으로 넘기지 말고 Write 도구로 파일을 만든 뒤 실행한다(`\n` 이 실제 개행으로 풀려 문법 오류가 두 번 났다). 일회성 패치 스크립트는 적용 후 삭제했다.
- 서브에이전트 산출물은 `AI\temp\journeyhelper\work\party\` 에 있고(원본·검수 문서), 저장소에는 압축 데이터와 문서만 넣었다. 임시 폴더는 삭제 가능(INDEX.md 참고).
