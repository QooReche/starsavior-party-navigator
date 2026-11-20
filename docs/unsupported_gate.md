# 미지원·근사 허용 목록 관문

## 계약

`tests/unsupported_gate_test.py`는 `tools/run_tests.py`가 자동 수집함.
진단 키 문자열 **집합**을 `tests/fixtures/unsupported_allowlist.json`과 양방향 비교함.
새 항목은 클라로 확정하거나 사유와 함께 등록해야 하며, 사라진 항목은 해소 여부를 확인해 목록에서 지움.
같은 개수의 서로 다른 진단으로 바뀌어도 실패함. 허용은 구현 완료·안전 판정을 뜻하지 않음.

|영역|수집 범위와 키|
|---|---|
|A|전체 구원자 형태 × standard/none의 support_report. 구원자 키·육성·정적 줄|
|B|전체 구원자 형태 × 고정 5시나리오의 runtime 키. 구원자 키·시나리오·진단 문자열|
|C|현재 코스모 3보스·길드 방어전 waves의 정적 줄과 고정 상위 편성 표본 runtime 키|
|D|실제 API 결과의 assumptions_used.rule, cosmo_approx 문구, score_conf 값|
|E|data/foe_stages.json 전 스테이지의 정적 고유 줄. 지난 시즌 탭도 포함|

정적 줄의 키는 unit·slot·reason·raw·critical을 JSON 배열 문자열로 직렬화함.
원문 구분자와 줄바꿈을 보존하며 critical 변경도 드러남. E는 스테이지마다 support_report를 호출한 뒤
합집합을 취하므로 서로 다른 전투에 등장하는 표지 이름을 섞지 않음.
키마다 reason(남기는 사유)·client_clue(확정에 필요한 조사 단서)·owner(담당 영역)를 둠.
세 칸 모두 빈칸/공백을 거부함. client_clue의 기존 문서·규칙 source는 **재조사 단서**이며
이번 작업이 해당 규칙을 새로 클라 확정했다는 뜻이 아님.

## 시나리오

정본은 `tests/fixtures/unsupported_scenarios.json`임. seed=1, 3판, standard,
단일 프로세스로 실행함. B의 5전투는 감사와 같은 코스모 3보스 Step3 Lv0·길드 방어전 Lv0·
일반 스테이지 경로의 **코스모 길레 1단계**임. 마지막 전투는 현 시즌 코스모 게이트 경로가 아님.
기본 채움 파티는 카르멘·프레이·클레어이며 대상 구원자와 겹치면 에데·세르팡·페이로 바꿈.
C는 감사의 보스별 첫 상위 편성에서 구원자 키를 취한 코스모 3표본과 공개 길드 방어전
COMMUNITY 편성 1표본임. 전원 standard로 다시 계산하며 계정 능력치·결과를 쓰지 않음.
난이도·리더·지원 스킬은 fixture의 고정 검사 조건임. 현재 계정의 최적 편성을 뜻하지 않음.

현 시즌 bossOrder가 fixture의 3보스와 다르면 실패하며 시즌 갱신 때 편성도 다시 선정함.
시나리오 예외, 3판 미반환, 진행도 전부 0, 구원자 0명, 스테이지 0개, 빈 waves는 실패함.
시간·판 수는 시험과 도구 출력에 표시함. 시간은 환경 부하에 따라 달라져 실패 상한으로 쓰지 않음.

## 갱신

1. `python -X utf8 -I tools/unsupported_allowlist.py --diff`로 추가·삭제 키 확인함.
2. 클라 설치본/디컴파일 빌드를 확인하고 새 진단을 조사함. 확정할 수 없으면 사유·단서·담당을 등록함.
3. `--write`는 기존 메모를 유지하고 해소된 키를 지우며 새 키의 세 메모 칸은 비워 씀.
   새 키가 있으면 저장한 뒤에도 종료 코드 1임. 자동 사유 채움으로 관문을 통과시키지 않음.
4. diff와 사유를 검토하고 `--diff` → `python -X utf8 -I tools/run_tests.py`로 검증함.

## 한계

API가 기록하지 않는 조용한 근사, code 등급 note의 부분 미확정, 표본에서 실행되지 않은 조건은
이 관문만으로 검출하지 못함. assumptions_used는 선택 규칙 목록이며 해당 판의 분기 실행 추적이 아님.
남은 범위는 `unsupported_26752678.md`·`engine_fix2_26752678.md`와 규칙 정본을 함께 확인함.
구원자/적 정적 보고가 0이어도 전역 지원을 보증하지 않음.

API `unsupported.gate_ok`는 기존대로 정적 critical 또는 runtime 진단이 있으면 false임.
허용 목록을 API에 연결하지 않았음. 화면·엔진·탐색 코드는 변경하지 않았음.
