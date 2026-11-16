# 그웬 추가 그림·움직임

아래는 최초 제작 당시 기록임. 현재 confident·thoughtful·notes 원화와 화풍은 후속 [art6.md](art6.md)에서 교체했음.

내장 `image_gen`으로 SD 걷기 4프레임과 등신대 상반신 반응 3종(엄지척·고민·메모, 각 2개 원화 프레임)을 만들었음. 공식 22.png·23.webp·24.webp·25.png의 얼굴·남색 단발·금색 눈·핀·견장·청록 리본·채색을 참고했음. 28_sd_emote.webp는 가운데 SD 배지만 참고·비교했음. 원본 영상 배경은 사용하지 않았음. 새 걷기는 기존 승인된 investigate의 비율·선 굵기·의상을 따랐음.

기존 SD 5종과 정지 PNG·512px 원본은 바꾸지 않았음. report는 종이 든 팔, welcome은 손 흔들기, surprised는 짧은 움찔을 기존 그림의 부분 회전·위치 변화로 만들었음. 새 걷기와 등신대 반응은 생성된 프레임을 분리·정렬했음. 걷기 첫 생성본의 흐린 반투명 배경은 도구로 한 차례 제거했음. 그림 제외 없음.

생성 프롬프트는 `prompts2.json`, 배경 제거 프롬프트는 `walk_cleanup.txt`. 공식 참고는 커밋하지 않음. 내장 도구 기본 출력물을 작업 폴더 `_tmp/art2/`로 복사한 뒤 후처리했음. 코드로 캐릭터를 새로 그리지 않았음. 저작권은 기존 README의 원 캐릭터 권리 안내를 따름.

## 파일·재현

`masters2/*.webp`는 정규화한 320px 원화 프레임 시트이며 사이트에서 불러오지 않음. 사이트용 파일은 `assets/ui_icons/gwen/`의 이름별 PNG·WebP임. 512px 기존 원본·도구용 시트를 제외한 9종의 모든 화면용 PNG·WebP 합계는 **590,088바이트**, 개별 최대 53,170바이트임. 정지 PNG는 RGB 팔레트를 줄이되 원본 알파를 그대로 복원했음.

```powershell
# 커밋된 시트·기존 SD 원본으로 생성 API 없이 재현
python -X utf8 tools/gwen_art/build2.py
# 공식 참고를 포함한 로컬 비교 시트도 재생성
python -X utf8 tools/gwen_art/build2.py --reference-dir <gwen_src>
```

| 파일 | WebP / PNG 바이트 | 움직임 | 위치 |
|---|---:|---|---|
| walk | 28,118 / 19,225 | 4프레임, 1.2초 연속 | 검증·길드/코스모 탐색·육성·슬롯 진행의 long 상태 |
| confident | 53,170 / 50,484 | 3프레임, 1초, 1회 | 첫 파티 클리어율 70% 이상 |
| thoughtful | 46,788 / 46,723 | 3프레임, 1초, 1회 | 첫 파티 클리어율 5% 이상·70% 미만 |
| notes | 47,518 / 48,320 | 3프레임, 1초, 1회 | 첫 파티 클리어율 5% 미만 |
| report | 12,888 / 기존 27,471 | 4프레임, 1초, 1회 | 결과 발표 |
| surprised | 32,140 / 기존 26,603 | 4프레임, 1초, 1회 | 오류·빈 결과 |
| welcome | 13,044 / 기존 26,591 | 4프레임, 1초, 1회 | 첫 안내·불러오기 창 |

investigate(준비·조사)와 files(후보 거르기·내 구원자 빈 명단)는 그대로 사용함. 기존 조사·서류 넘기기 파일은 유지하되 화면에서는 1초 동작 뒤 정지 PNG로 쉬게 했음. 클리어 판정 문구·계산·엔진은 바꾸지 않았음. 5~70%의 고민 그림은 기존 ‘아슬아슬’ 판정도 포괄함.

## 화면 재생

`GWEN_SCENES`가 파일·대체 그림·깜빡임 연결의 정본임. `Ux.gwenImage`는 width/height·데이터 경로를 만들고 CSS aspect-ratio로 자리를 잡음. 그림·테두리는 decode 전 투명이며 완료 뒤 160ms 동안 나타남. 헤더·메모·구원자 얼굴도 같은 표시 규칙을 쓰되 헤더에는 상주 연출을 넣지 않았음. 교체할 PNG·WebP·blink를 미리 decode하고 src를 바꾸므로 기존 그림을 빈 프레임으로 바꾸지 않음.

`mountGwen`의 장면별 컨트롤러는 다음 이벤트 timeout 하나만 예약함. 전환·중단 때 토큰 무효화 → 예약 취소 → object URL 해제 → 경로 갱신 → 가시성 재평가 순으로 정리함. IntersectionObserver와 실제 교차·부모 잘림 검사로 숨긴 탭·닫힌 서랍·화면 밖·document.hidden에서 시계와 CSS를 멈춤. 제거·교체 중 끝난 fetch/decode는 이전 토큰으로 화면에 쓰지 못함. WebP 바이트와 정지 decode는 경로별로 공유하고, 단발 재생은 매번 새 object URL을 만든 뒤 종료·중단 때 해제함.

walk만 연속 재생·좌우 이동함. 나머지 동작은 1초 뒤 PNG로 돌아가 4~8초 쉬며, PNG 휴식 중에만 발끝 기준 3.6초 숨쉬기·가끔 ±1도 기울기를 적용함. blink 연결이 있으면 3~6초 간격으로 120~160ms 눈을 감고 가끔 두 번 깜빡임. reduced-motion은 정지 PNG만 쓰고 자동 대사·순환·방치를 멈춤.

대기 그림은 접근 가능한 버튼임. 무입력 60초 뒤 doze, 입력 시 ready로 복귀함. 2초 창 안 클릭 1·3·5회는 shy·sulk·cry이며 마지막 클릭 뒤 보이는 시간 3초 후 복귀함. Enter/Space·터치를 지원하고 키 자동반복과 pointer/click 중복을 집계하지 않음. 클릭 반응만 읽기 도구에 알림. 대사는 상황별 6개이며 전체 후보에서 방문별 시작 줄을 고른 뒤 보이는 시간 12초마다 바꿈. 최장 대사에서도 추천 조작 위치가 변하지 않도록 말풍선·모바일 열을 확보했음.

실제 `data-gwen` 단계는 그대로 두고 8~10초마다 표현만 순환함. inspect는 investigate→think→magnify, screen은 files→stamp→board, long은 walk→stakeout→zap→coffee임. 새 그림을 실제 파일로 연결했음.

결과 발표 SD는 첫 파티의 선택된 `shown.clear`를 사용함. 70% 이상은 결과별로 고정된 verdict/cheer, 5% 이상·70% 미만은 report, 5% 미만은 cry임. 확률 없음·점수형·길드/코스모 배열은 중립 report임. decode가 완료되고 실제 보이는 1.8초만 소비하며 재렌더해도 다시 시작하지 않음. 등신대 반응은 기존 첫 파티 배치를 유지함. 오류는 호출부가 calculation(cry), few/empty(sulk), other(surprised)를 넘김. 취소·미계산·이미 최선은 실패 그림을 쓰지 않음.

2026-11-16 그림 작업 병합 뒤 아래 13종의 PNG/WebP와 깜빡임 10종을 실제 파일로 연결했음. 진행 7종 WebP의 loop=0은 파일 자체의 무한 반복이며 화면의 `loop:true`와 구별함. investigate/files와 같이 화면 컨트롤러가 1초 뒤 PNG로 바꾸고 4~8초 쉬게 하며 walk만 연속 재생함. 깜빡임은 ready/welcome/investigate/files/report/think/shy/sulk/verdict/cheer의 `이름_blink.png`를 사용함.

| 이름 | 연결 상황 | 연결 이전 fallback |
|---|---|---|
| cry | 낮은 결과·계산 실패·5회 클릭 | surprised |
| verdict | 높은 결과 발표 | report |
| cheer | 높은 결과 발표 | report |
| sulk | 후보 부족·빈 결과·3회 클릭 | surprised |
| shy | 대기 1회 클릭 | ready |
| doze | 대기 60초 방치 | ready |
| think | inspect 순환 | report |
| magnify | inspect 순환 | files |
| stamp | screen 순환 | report |
| board | screen 순환 | investigate |
| coffee | long 순환 | files |
| stakeout | long 순환 | investigate |
| zap | long 순환 | surprised |

## 검증

`tests/gwen_art_test.py`: 합계/개별 용량·알파·정지 PNG·프레임 변화·지속 시간·loop 메타데이터.
`tests/e2e/test_gwen_art2.py --shots --mutations`: 360/1280/1600px 실제 결과 렌더러·빈 명단·반응 3종·lazy 요청·재다운로드 없는 재생·4초 이상 휴식·document.hidden·숨긴 패널/서랍·잘린 요소·화면 경계·reduced-motion·제거 시 URL 해제와 재생 중단. 걷기 연결/loop 플래그/간격/정지/결과 그림/서랍/잘림/URL 정리 되돌림 8종을 검출함. 기존 진행 상태·취소 DOM·발표 수명·넓은 화면 시험도 유지함.
`tests/gwen_ux_test.js`: 확률 경계·누락·점수형·배열·결과 고정·오류 원인·전체 대사 선택과 되돌림 4종.
`tests/e2e/test_gwen_ux.py --mutations --shots`: 360/1280/1600px 클릭·터치·키보드·방치 복귀·표현 순환·168개 대사의 고정 배치·선택 결과·지연 decode/fetch 중 교체/제거·발표 decode 대기·시즌 후보 부족·실제 blink·로딩 지연 전후 bounding box/opacity/layout-shift를 검사함. 순환/복귀/토큰/숨김/버튼/decode/발표 decode 대기/선택 결과/고정 자리/대사 공간과 cry/순환/blink 연결·fetch 토큰 되돌림 총 14종을 각각 의도한 assertion으로 검출함. loading 시험은 오류 원인별 실제 그림을 확인하고 cry/sulk→surprised 되돌림도 검출함. 1280/360px 연결 캡처·깜빡임 프레임은 `_tmp/gwen-wire/`에 보관함.
`_art_compare2.png`와 `_shot_art2_*.png`는 비교·상황별 화면 증거이며 커밋하지 않음. 전체·골든 실행 결과는 docs/HISTORY.md의 해당 절에 기록함.
