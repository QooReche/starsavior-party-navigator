# 그웬 SD 팬 그림

2026-11-15 `ready`를 추가했음. 내장 `image_gen`에 기존 welcome·investigate·report를 참조로 넣고 «기존 SD와 같은 머리·몸 비율, 굵은 윤곽선·단순 명암·남색/청록/금색을 유지하며 한 손은 허리, 다른 흰 장갑 손은 아래의 가상 단추를 가리키고 자신만만하게 미소 짓는 전신 그웬, 투명 배경, 전연령, 문자·로고 없음»으로 요청했음(전체 프롬프트: [ready_prompt.json](ready_prompt.json)). 생성 1회, 재생성 0회이며 기존 5종·walk와 공식 21.webp·22.png를 먼저 확인했음. [build_ready.py](build_ready.py)는 기존 `build.master`·`build2.move_part`·`build2.encode`를 재사용함. 생성 알파의 미세한 배경 잡음을 정리하고 가장자리 투명도를 보존해 본체 높이 약 450px로 맞췄으며, 원본은 내부색 192개·알파 가장자리 64개 팔레트의 512px PNG로 저장했음. `ready.png`는 표시 120~140px용 160px 정지본, `ready.webp`는 손·소매 끝만 0/−4/+3/0도로 움직이는 4프레임(500/220/220/460ms), `loop=1` 한 번 재생임. 세 파일 모두 80,000바이트 이하·투명도·프레임 수를 검사했음. 재현은 `python -B -X utf8 tools/gwen_art/build_ready.py`, 최초 가져오기는 `--import-file <생성 PNG>`를 붙임. 밝은 배경·어두운 UI·140px 표시·동작 프레임을 나란히 둔 `_tmp/_art_ready_compare.png`에서 기존 5종과 화풍을 대조해 채택했음.

후속 그림·현재 재생 방식은 [추가 그림·움직임](art2.md)에 정리했음. 기존 SD 5종은 유지했으며 아래는 최초 제작 기록임.

공식 4컷 만화의 SD 얼굴을 참고해 내장 `image_gen`으로 새로 만든 팬 그림 5종.
공식 원화 자체가 아니며 원 캐릭터·디자인의 권리는 원 권리자에게 있음.
공식 참고 파일은 이 폴더에 복사하거나 커밋하지 않음.

## 생성

- 공식 `21.webp`(4컷), `22.png`(카드), `23.webp`·`24.webp`·`25.png`(게임 화면), 저장소 `assets/ui_icons/gwen_sd.png`를 `view_image`로 먼저 확인했음.
- 정확한 생성 프롬프트는 `prompts.json`. `transparent_background=true`로 각 그림을 한 번씩 생성했음. `investigate`는 SD 얼굴·공식 만화를 참조했고, 나머지는 그 두 참고와 생성된 investigate를 함께 참조했음.
- 생성 결과 1254×1254 RGBA를 `_tmp/gwen_art/{이름}.png`에 복사했음. 도구가 자동 보관하는 생성 캐시 외 프로젝트 파일은 이 worktree 안에만 작성했음.
- 같은 프롬프트도 생성 결과는 달라질 수 있음. 확정한 `*_512.png`를 보존하므로 사이트용 이미지와 움직임은 생성 API 없이 재현할 수 있음.
- 비교 시트에서 공식 얼굴의 남색 단발·금색 눈·금색 머리핀과 군복·청록 리본·흰 프릴·장갑·견장을 대조했음. 전연령 포즈이며 문자·로고 없음. 5종 채택, 재생성·제외 없음.

## 후처리 재현

Python + Pillow 필요. 저장소 루트에서 실행함.

```powershell
# 처음: 내장 생성 도구의 결과 파일 5개가 있는 폴더를 지정
python -X utf8 tools/gwen_art/build.py --import-dir _tmp/gwen_art --compare
# 이후: 커밋된 512px 원본에서 완전히 같은 축소본·프레임을 만듦
python -X utf8 tools/gwen_art/build.py --compare
```

`assets/ui_icons/gwen/`에 512px RGBA PNG 5개와 160px PNG 5개, 160px 무손실 animated WebP 2개를 만듦. 알파를 보존하고 사각 캔버스에 여백을 둠.
investigate는 원본의 돋보기·장갑·소매 바깥쪽만 0/-2/-4/-2px 이동함. files는 원본에서 잘라낸 종이 한 장만 높이를 바꿔 넘기는 동작을 만듦. 얼굴·몸은 다시 생성하지 않음.
각각 4프레임, 320/220/320/220ms, 무한 루프. 파일당 80,000바이트를 넘으면 스크립트가 실패함.
비교 시트 `_art_compare.png`는 밝은 배경·실제 어두운 UI·프레임 비교를 함께 보여 주며 커밋하지 않음.

## 화면 연결과 검증

`Ux.gwenWork`: inspect/long → investigate, screen → files, error → surprised. 기존 상태명·문구·단추·id는 유지함.
결과는 `Ux.gwenReport`가 같은 객체마다 한 번 표시하고 실제로 보인 시점부터 1.8초 뒤 제거함. 숨긴 탭·닫힌 details·버린 HTML은 표시 횟수를 소비하지 않으며, 시간 안의 재렌더는 최초 만료 시각을 유지함. 모의 전투·시즌 탐색·육성·스타링크 결과에 연결했음.
첫 안내와 내 정보 불러오기 창은 welcome. 그림은 PC 140px, 휴대폰 120px로 표시함.
`picture`의 `no-preference` 소스만 WebP이며 기본 PNG가 reduced-motion 정지 프레임임. 발표 CSS 동작도 reduced-motion에서는 끔.

```powershell
python -X utf8 build_party_html.py index.html
node tests/ux_ui_test.js
node tests/public_ui_test.js
E:/AI_mk2/venv-pw/Scripts/python.exe -X utf8 tests/e2e/test_gwen_loading.py --shots
python -X utf8 tools/run_tests.py
python -X utf8 tests/golden_check.py
```

브라우저 시험은 실제 `currentSrc`, 진행률·취소 단추 보존, 성공 1회·시간 후 제거·중간 재렌더·숨긴 패널의 첫 표시, 오류·빈 결과, 360px 가로 넘침, 동작 줄이기 전환을 검사함. 옛 얼굴로 소스를 되돌리거나 정지 CSS를 무효화하면 실패하는지도 검사함.
캡처 `_shot_art_*.png`와 임시 폴더 `_tmp`는 커밋에서 제외함.
