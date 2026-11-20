# 그웬 공통 무대

설계 2를 채택했음. GwenStage.mount가 진행 레인·배너·결과 자리를 소유하고 화면은 상태만 전달함.
기존 레인 컨트롤러의 단일 배우·보고 이력·이미지 decode 무효화를 재사용하며 탐색 실행기는 바꾸지 않음.
화면별 registerStage 호출은 없앴고 기존 CSS 식별자와 자리 크기를 유지했음.

## 부품 계약

`gwen_lane.js`의 `GwenStage.mount(container,{mode})`가 `data-gwen-slot="모드-board/result"` 자리에 진행 레인·완료 배너·결과 자리를 생성함. 자리 표시자는 배치만 정하며 레인 DOM 등록은 부품 내부 전용임.

- `progress(p,msg,extra)`는 0~1 진행률과 짧은 상태를 받음. `extra.step`이 바뀌면 이전 이동·이미지 요청을 취소하고 처음부터 걸음.
- `done(result,extra)`는 기존 결과 정책에 따른 등신대 반응을 한 번 실행함. 레인에는 «수사 완료!» 배너만 남기고 같은 배우 노드를 결과 요약 위로 옮김. 결과 객체 식별자를 유지해야 재표시 때 반응을 반복하지 않음.
- `reset()`은 해당 모드의 대기 상태, `destroy()`는 등록·DOM·진행 중 연출을 정리함. 파괴된 핸들의 늦은 갱신은 무시함.
- `update()`는 기존 직접 편성의 편집·오류·묶음 상태를 전달하는 호환 경로임. `activate(mode)`가 화면 소유권을 전환하므로 비활성 화면 갱신이 현재 그웬을 가져가지 않음.

reco·direct·cdirect·cosmoSearch·guildSearch가 같은 부품을 사용함. home도 같은 생성 경로로 옮겼음. reco의 기존 말풍선과 반신 크기·자리, 직접 편성·코스모 직접 편성의 CSS 식별자를 유지했음.

검색은 요청 id와 onPhase마다 증가하는 phaseSerial을 전달함. 동일 문구를 반복하는 보스별 단계도 구분함. 추천 묶음은 작업 객체 식별자와 request, 기존 추천은 편성 번호·예선 여부·라운드로 단계를 구분함.

## 정적 관문 범위

`gwen_stage_contract_test.js`는 루트 JS와 party_template의 progress 태그·progressbar 역할·보간된 N/M 표시를 자동 수집함. 파일·정확한 문자열·출현 수 인벤토리와 비교해 새 표시도 실패시키며, 다섯 화면의 실제 갱신 함수가 공통 부품으로 이어지는지 검사함. 생성물 index는 별도 중복 수집하지 않음.

단순 편성 인원·장비 부품·결과 준비 개수는 사유를 적고 제외했음. 별도 육성 결과 탭은 이번 다섯 화면 범위 밖임. 육성 평가 공용 producer는 env.paint 소비와 기본 육성 탭 소비를 구분했음. 직접·코스모 직접 편성·추천의 보조 «배치 비교 N/24» 세 곳은 **레인 미연결(범위 밖)**임. 이 보조 작업 자체의 레인 진도 연결은 이번 변경에 포함하지 않았음.

## 검증 범위

변경 전 home·reco·direct·cdirect 1280/390 캡처는 `local/gwen_before/`에 있음.
재현 명령은 `tests/e2e/capture_gwen_stages.py local/gwen_before`임. 합성 상태·정지 모션이며 실제 계정이나 시뮬 워커를 쓰지 않음.
변경 후 같은 명령의 출력 폴더를 `local/gwen_after/`로 지정해 비교함.
전체 비브라우저 시험과 지정된 브라우저 시험만 순차 실행함. HANDOFF·엔진은 변경하지 않음.

독립 리뷰는 `1892ce2..c0a497b`, `c0a497b..40da38e`, `40da38e..7657df4` 고정 범위로 진행했음. 단계 토큰·신규 진행 표시 발견·추천 묶음 토큰 지적을 반영했으며 마지막 범위에서 추가 확정 결함 없음으로 끝났음.

기존 네 화면의 진행/대기 8장과 결과 6장, 합계 14장은 1280·390 폭에서 픽셀까지 같았음. PIL ImageChops로 크기와 모든 RGB 픽셀을 비교했으며 차이 영역은 모두 없음임. 비교 기록은 `local/gwen_after/comparison.json`임. 첫 비교에서 드러난 reco 말풍선·자리 크기·모바일 그림자는 기존 배치에 맞췄음. 최종 CSS·시험 계약 수정 `7657df4..03adf41`도 독립 리뷰에서 추가 확정 결함 없음으로 끝났음.

집중 검증 결과:

| 명령 | 결과 |
| --- | --- |
| `node tests/gwen_stage_contract_test.js` | 다섯 화면 연결·변이 10개 통과 |
| `node tests/gwen_stage_dom_test.js` | DOM 7시나리오·변이 15개 통과 |
| `test_gwen_search_stage.py` | 코스모·길드 × 1280·390, 4흐름 통과 |
| `test_gwen_ux.py --mutations` | 22검사·변이 14개 통과 |
| `test_direct_party.py --mutations` | 10그룹·변이 1개 통과 |
| `test_cosmo_direct.py` | 3그룹 통과, 실제 워커로 3보스 × 2판 확인 |

브라우저 명령은 `E:\AI_mk2\venv-pw\Scripts\python.exe -X utf8 tests/e2e/파일명`으로 실행했음. `PLAYWRIGHT_BROWSERS_PATH=E:\AI_mk2\pw-browsers`, `PN_E2E_WORKERS=1`이며 모두 한 파일씩 실행했음. 신규 탐색 시험은 실제 planner와 제어된 가짜 워커를 사용하며 `progs`·`via`도 반환함. 진행률이 실제로 증가하고 배우 위치가 0보다 큰지, 같은 문구의 다음 단계 초기화·취소·늦은 응답·재실행·결과 위치·그웬 1명·재반응 없음까지 확인했음. 실제 탐색 결과 품질이나 전역 클라 일치율 검증은 아님.

UX 시험에서 `pause_at(Date.now())`가 명령 도착 전에 과거가 되는 경합이 한 번 발생해 목표를 1초 뒤로 지정했음. 해당 식은 기준 커밋 `0f7b89f`와 같음을 확인했으며 기준 커밋의 원본 화면·원본 idle 검사 1회는 통과했음. 기존부터 항상 실패했다고 판정하지 않았음.

최종 `python -X utf8 -I tools/run_tests.py --rebuild`는 234개 파일 통과·실패 0이었음. 로그는 `local/gwen_full_test.log`임. 기준선도 통과했지만 COSMO_TABLES가 없어 시즌 1022·1023의 클라 원표 재생성 대조 2건은 양쪽 모두 건너뛰었음. 첫 전체 실행에서 새 GwenStage 스텁이 빠진 기존 코스모 페이지 시험이 실패해 스텁과 제거 변이를 새 계약으로 고쳤고, 위 최종 실행으로 실패 0을 확인했음. 이미지 재생성 시험 이후 자산 변경 없음도 확인했음.
