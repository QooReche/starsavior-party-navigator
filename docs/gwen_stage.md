# 그웬 공통 무대

설계 2를 채택했음. GwenStage.mount가 진행 레인·배너·결과 자리를 소유하고 화면은 상태만 전달함.
기존 레인 컨트롤러의 단일 배우·보고 이력·이미지 decode 무효화를 재사용하며 탐색 실행기는 바꾸지 않음.
화면별 registerStage 호출은 없애고 기존 CSS 식별자와 자리 크기를 유지하기로 함.

## 검증 범위

변경 전 home·reco·direct·cdirect 1280/390 캡처는 `local/gwen_before/`에 있음.
재현 명령은 `tests/e2e/capture_gwen_stages.py local/gwen_before`임. 합성 상태·정지 모션이며 실제 계정이나 시뮬 워커를 쓰지 않음.
변경 후 같은 명령의 출력 폴더를 `local/gwen_after/`로 지정해 비교함.
전체 비브라우저 시험과 지정된 브라우저 시험만 순차 실행함. HANDOFF·엔진은 변경하지 않음.
