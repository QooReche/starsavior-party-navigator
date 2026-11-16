# 직접 편성 그웬 길 (2026-11-16)

## 배경 출처·가공

- 게임 클라이언트 배경 이미지(© STUDIOBSIDE). 사이트 하단 «출처·면책»에도 같은 출처를 표기했음. 기존 그웬 팬 그림과 출처가 다름.
- Steam buildid 26610546. 비공개 static-data의 `DECOMPILE.md`·`INDEX.md`·`decompiled/BUILD.md`를 확인하고 `check_build.py`로 설치본 빌드·DLL 해시 일치를 확인했음.
- 설치 루트 기준 `Data/eb/711cfc1a586b268916f81a4a23cd3e8125906431.bundle`에서 추출했음. 자동 여정 프리팹 `UI_JOURNEY_POPUP_SD_AUTO_JOURNEY`, 배경 오브젝트 `UI_AUTO_JOURNEY_BG_DOWNTOWN_00`과 같은 번들임.
- UnityPy 1.25.4, fallback Unity version `6000.0.61f1`. 비공개 추출기의 번들 해독을 사용해 Texture2D만 이미지로 저장했음. 다른 캐릭터·UI 그림·프리팹 원문은 배포하지 않음.
- 사용 텍스처: `AUTO_JOURNEY_00_BG`, `AUTO_JOURNEY_00_CLOUD`, `AUTO_JOURNEY_00_BACK02`, `AUTO_JOURNEY_00_BACK01`, `AUTO_JOURNEY_00_BOTTOM_02`, `AUTO_JOURNEY_00_BOTTOM`, `AUTO_JOURNEY_00_FRONT` (각 2048×948).
- `tools/build_journey_lane.py <추출 PNG 폴더>`로 합성함. 웹 길에 맞춰 보도 레이어를 아래로 280px 옮기고 `(0, 500, 2048, 935)`를 잘라 1600×340 WebP quality 75로 축소했음. 클라 화면 전체를 그대로 재현하는 합성은 아님.
- 배포 파일: `assets/ui_icons/journey_lane.webp`, **72,260B** (한도 80,000B). SHA-256 `df722c82342628775daf9105c40ac61b610606ac106463578089c801d69d2438`.
- CSS `cover`·하단 정렬과 남색 그라데이션을 적용했음. 고정 높이를 먼저 확보하므로 배경 요청이 늦어도 레이아웃을 밀지 않음. 배경 자체는 움직이지 않음.
- 사용한 WebP 외 임시 추출 PNG·미리보기는 모두 삭제했음.

## 동작

- 1200px 이상에서 편성판 길의 그웬 80→120px, 길 122→162px (+40px). 진행 막대·결과 칸과 1200px 미만 규칙은 유지했음.
- 직접 편성 대기 상태에서 3~7초 뒤 길 양끝을 오가며 걷고, 25% 확률로 달림. 도착 후 2~3초 동안 magnify·think·coffee·stamp 중 직전 두 대기 동작을 제외해 고름. 15% 확률로 jump를 선택함. 다음 이동까지 3~7초 기다림.
- 입력·편성 변경·부르기·계산·결과가 놀이를 취소함. 계산은 진행 길을 사용하고 결과 발표는 기존 자리를 유지함. 60초 방치 doze·wake·빈 칸 안내·반응 우선순위를 보존했음.
- 한 actor만 transform으로 움직임. reduced-motion·반응 줄이기는 정지 그림을 남김. 탭 숨김·그웬 자체가 화면 밖이면 가시 시간·이동을 멈추고 PNG로 복귀함. 길 윗부분만 보이는 경계도 포함함.
- 공용 `.art` 이미지가 있는 직접 편성·추천 카드의 `.fallback`을 완전히 숨김(로드 대기 중에도 글자가 비치지 않음). 로드 실패로 img가 제거되거나 이미지 주소가 없으면 대체 글자가 보임.

## 검증·재현

- `node tests/gwen_lane_test.js`: 대기 후보 반복 제한·시간 범위·확률 분기·양끝 목표 및 기존 우선순위/이동 제한 검사.
- `tests/e2e/test_direct_lane.py`: 1280·1600·1100의 크기, 경계·단추/글 겹침, 방향 반전·walk/run/jump·조작/계산 우선순위, 숨김/화면 밖 clock 및 정지 PNG, reduced-motion·반응 줄이기, 직접/추천 fallback 성공·실패, 배경 지연 CLS 0, 두 되돌림 검출.
- 이동 되돌림은 transform을 길 밖으로 강제함. fallback 되돌림은 visibility를 되살림. 두 경우 실제 브라우저 검사가 실패해야 통과함.
- E2E는 놀이 RNG만 고정해 걷기/동작과 달리기/jump 분기를 각각 확실히 밟음. 실제 이동·그림·입력을 검사하며, 후보 이력·확률 경계는 JS 시험에서 모든 `pose()` 호출을 검사함. 부분 편성 상태에서 그웬을 눌러도 포인터 아래 자리에서 멈추는지 확인함.
- 독립 리뷰에서 길만 일부 보일 때 그웬이 화면 밖에서도 움직이던 기존 경계를 지적해 actor 사각형 기준으로 고쳤음. animated WebP→정지 PNG 검사도 보강했음. resize와 단계 전환 때 남은 놀이 이동을 취소하는 경계를 함께 보완했음.
- `tests/e2e/test_direct_lane.py --capture`: `_tmp/lane/lane-1280.png`, `lane-1600.png`, `lane-idle.webm`. 제출용 12초 영상은 `lane-idle-12s.webm`임.
- 전체 시험 로그: `_tmp/lane/full-tests.log`. 합성 계정만 사용했음.
