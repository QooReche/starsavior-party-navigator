# 직접 편성 그웬 길 (2026-11-16)

## 조사 배너 (2026-11-17)

- 기존 배경과 같은 buildid 26610546 설치본을 `check_build.py`로 대조했음(DLL 8개 불일치 0). 지정 기준 커밋과 작업 폴더 범위를 유지하기 위해 pull하지 않았음.
- 설치 루트 기준 `Data/eb/711cfc1a586b268916f81a4a23cd3e8125906431.bundle`에서 `UI_JOURNEY_POPUP_SD_AUTO_JOURNEY`·`FINISH`와 Sprite `UI_JOURNEY_POPUP_AUTO_FINISH_TITLE`을 직접 확인했음. 이전 실행에서 남긴 900×353 추출 미리보기를 확인했으며, 파랑 그라데이션·흰 외곽선·짙은 그림자·강한 제목 글자의 영문 `JOURNEY COMPLETE` 그림임. 이 스프라이트는 스타일 참고에만 사용하고 배포하지 않음.
- 비공개 `tables/Strings/STRING_COMMON_ko_en.json`에서 `SI_AUTO_JOURNEY` = **자율 여정** / Auto Journey, `SI_JOURNEY_COMPLETE_TITLE` = **여정 완료** / Journey Complete, `SI_AUTO_JOURNEY_DESC` = 자율 여정 진행 옵션 안내를 확인했음. 완료 문자열에는 느낌표가 없음. 한국어 문자열과 영문 스프라이트는 구별하며, 해당 스프라이트가 한국어 완료 문자열을 직접 쓰는 것으로 단정하지 않음.
- 배포 글자는 아래 PM 확정 문구를 새로 렌더했음. `tools/build_case_banner.py <NotoSansKR-VF.ttf>`로 Noto Sans KR weight 900(Pillow 가변 글꼴), 흰색→금색 결과·회청색 오류, 흰/남색 외곽선과 작은 기울기를 적용했음. 글꼴은 Noto Sans KR(SIL OFL 1.1), 글꼴 파일은 배포하지 않으며 실행 중 외부 요청 없음. 원본 글꼴 프로젝트: https://github.com/notofonts/noto-cjk .
- `assets/ui_icons/case_banner_*.webp` 4장, 각 640×160 RGBA, 총 **61,148B**, 최대 **17,548B**, 파일당 80,000B 이하. 실측은 `budget.json`의 `case_banner`에 기록했음. 기존 그웬 그림 예산과 별도로 명시한 제목 그림 합계임. 이전 `journey_complete.webp`·빌더는 제거하고 무관한 `gwen/wake.webp` 수정은 되돌렸음.

| 상태 | 문구 | 파일 접미사 | 선택·연출 |
|---|---|---|---|
| 결과 | 조사 완료! | investigation | 세 후보 중 직전 새 결과와 다르게 무작위 |
| 결과 | 수사 완료! | inquiry | 같은 규칙 |
| 결과 | 계산 완료! | calculation | 같은 규칙 |
| 오류 | 수사 난항… | error | 회청색 정지 표시 |

- 결과 문구는 승리를 단정하지 않고 계산·조사의 완료만 뜻함. 따라서 낮은 클리어 결과의 울음/육성 권유, 중간 결과의 비교 권유, 높은 결과의 자신만만한 대사와 모순되지 않음. 기존 결과 말풍선 대사는 유지함. 점수별 추가 문구는 쓰지 않았음.
- 계산 중에는 그웬이 철창 길에 남으므로 배너가 없음. 출발 달리기와 왼쪽 진행 길을 제거했음. 같이 돌리기의 내 편성 첫 발표·자동 추천·육성 추천도 같은 규칙이며, 전체 종료 때 그웬이 왼쪽 결과 자리로 이동하고 빈 철창 길에 결과 문구를 표시함. 오류도 왼쪽 이동 뒤 표시함. 1~3명 대기·stale·복귀·다른 탭에서는 숨김. 같은 결과의 문구는 resize·반응 줄이기·탭 왕복으로 재선택하지 않음(최근 128개 결과 보관).
- absolute 배치·고정 비율·aria-hidden이며 이미지 decode 전/실패 때도 같은 문구의 CSS 글자가 보임. 결과·오류 배너는 정지 그림임. 독립 리뷰에서 결과 그웬과 배너 등장 동작의 동시 재생·화면 밖 배너 재생을 지적해 등장 애니메이션을 제거했음. 움직이는 요소는 그웬 하나이며 reduced-motion·반응 줄이기·탭 숨김·화면 밖 정지를 유지함.
- `tests/case_banner_test.js`: 상태·직전 중복 제한·기존 결과 복원·문구·실측 예산. `tests/e2e/test_case_banner.py`: 실제 진행 이벤트 10→55→100%에 따른 철창 길 이동·수사 동작·skip·결과/오류/복귀·묶음 진행, 1280/1600/360 경계·겹침, 이미지 지연 CLS 0·실패 대체, reduced-motion/반응 줄이기/숨김/화면 밖 정지. 계산을 왼쪽 길로 보내기·진행 이동 끄기 2종은 응답 route에서 결함을 주입해 실패를 확인하고 정상 소스로 재검증함. 추천 결과 불변은 전체 시험의 실제 Pyodide·추천 회귀 검사로 확인함.
- 캡처: `_tmp/banner2/work-{1280,1600,360}.png`, `result-{1280,1600,360}.png`, `error-1280.png`. 모두 합성 시험 계정임. 추출 임시 파일은 확인 후 삭제했음.
- 최종 전체 검증: 단위 197 + E2E 14 = 211모듈 통과·실패 0. 기존 `COSMO_TABLES` 부재 1건만 건너뜀. 진행 중/이미지 지연 CLS 0이며 전체 로그는 `_tmp/banner2/full-tests.log`임.

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
- 입력·편성 변경·부르기·계산·결과가 놀이를 취소함. 계산은 철창 길에서 진행률에 따라 왼쪽→오른쪽으로 걷고, 도착 뒤 investigate·magnify·think·board·coffee·stakeout·stamp·files 활동을 함. 9초마다 수사 동작을 바꾸며 reduced-motion은 20초 간격임. 단계별 진행은 왼쪽부터 시작하고 진행을 모르는 준비 단계는 수사 동작만 함. 왼쪽 진행 막대·판 수는 유지함. 결과 발표는 기존 왼쪽 자리를 유지하며 60초 방치 doze·wake·빈 칸 안내·반응 우선순위를 보존했음.
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
