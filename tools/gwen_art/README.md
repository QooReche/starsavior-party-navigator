# 그웬 SD 팬 그림

## 재조사 사무실용 — 코트 벗은 SD 3종

2026-11-23 내장 image_gen으로 `recon_look`(왼쪽 돋보기 관찰), `recon_pin`(왼쪽 위 사진 고정), `recon_nod`(팔짱·자신만만한 끄덕임) 정지 자세를 만들었음. PM 검수에 따라 세 원본을 국소 편집해 치마 옆·뒤의 파란 코트 자락과 금색/검은 줄, 청록 허리띠·큰 리본, 가슴 타이·자보를 제거했음. 장식 없는 흰 스탠드 칼라·손목 커프스가 있는 긴소매·맨손·흰 프릴 치마에, 은색 사각 버클 가로 벨트 두 줄이 달린 무광 검은 언더버스트 코르셋을 맞췄음. 얼굴·머리·자세·소품·스타킹·신발은 유지했음. 전연령·문자 없음·실제 투명 RGBA임.

최초 생성은 look 2회(시선 방향 보정 1회), pin·nod 각 1회로 총 4회였음. 이번 국소 편집은 각 1회, 총 3회·재시도 0회임. 이전 원본은 저장소 밖 `recon/gwen/recon_*_v1.png`, 수정본은 같은 폴더의 `recon_*.png`에 확대 없이 보관했음. 전체 호출 프롬프트·참조·선정 결과와 수정 이력은 [prompts_recon.json](prompts_recon.json)에 있음.

`python -B -X utf8 tools/gwen_art/build_recon.py --import-dir <원본 PNG 폴더>`로 최초 가져오고, 이후에는 옵션 없이 커밋된 512px 파일에서 재현함. ready와 같은 알파 정리(10 미만 0·245 초과 255), 가장자리 중간 알파 보존, 450px 이내 축소·512px 캔버스·발끝 y482·192색 본체/64색 가장자리 팔레트를 썼음. 160px PNG는 기존 정지본 방식으로 색을 줄이고 알파를 보존했음.

출력은 `assets/ui_icons/gwen/recon_look_512.png`·`recon_look.png`, `recon_pin_512.png`·`recon_pin.png`, `recon_nod_512.png`·`recon_nod.png` 6개임. 각각 512×512와 160×160, 합계 242,826바이트(160px 3개 51,655바이트)이며 파일당 80,000바이트 안에 있음. 빌더에서 크기·투명도·가장자리·여백·기존 전체 용량 한도를 검사함. **화면 연결·애니메이션은 추가하지 않았음.**

보관 폴더의 `recon/with_gwen_office.png`는 사무실 위에 각 동작을 한 번씩 얹은 3행 정지 합성임. `recon/gwen/alpha_style_review.png`에서 기존 investigate와 같은 크기의 선·색·비율, 체커보드 알파와 어두운 배경의 실제 160px 정지본을 검수했음.

검증: `python -X utf8 -I tools/run_tests.py forced gwen` 16통과·0실패. 옵션 없는 재빌드 전후 6파일 SHA-256이 같고, 호출 수·선정본·프롬프트의 로컬 절대 경로 부재를 확인했음.

## 기존 SD 제작 기록

새 SD 13종·깜빡임·용량·재현 기록: [art3.md](art3.md).

2026-11-15 `ready`를 **화면 오른쪽의 «추천 편성 보기» 단추를 가리키는 자세**로 다시 만들었음. 기존 investigate·files·report·surprised·welcome의 512px 그림과 공식 21.webp·22.png를 `view_image`로 먼저 확인했음. 내장 `image_gen`에 welcome·investigate·report를 직접 참조로 넣고, 같은 SD 비율·굵은 윤곽선·남색/청록/금색 채색, 정면 몸, 한 손은 허리, 다른 팔과 검지는 보는 사람 기준 오른쪽으로 뻗은 자세, 자신만만한 미소를 요청했음. 전연령·문자 없음·투명 배경임. 이번 교체 생성 1회, 추가 재시도 0회임. 전체 프롬프트와 참조 목록은 [ready_prompt.json](ready_prompt.json)에 있음.

[build_ready.py](build_ready.py)는 생성 알파의 미세한 잡음을 정리하고 가장자리 투명도를 보존해 본체 높이 약 450px로 맞췄음. `ready_512.png`는 내부색 192개·알파 가장자리 64개 팔레트의 512px PNG, `ready.png`는 160px 정지본임. `ready.webp`는 160px 4프레임이며 정확히 **300/200/200/300ms, 합계 1000ms, loop=1**임. 손목·장갑 영역만 오른쪽으로 살짝 늘려 손을 내미는 동작을 만들었음(512px 기준 0/+5/+9/0px, 160px에서는 최대 약 2.8px). 얼굴·몸은 고정하고 마지막 프레임은 첫 자세로 돌아옴. 손끝 여백·실제 저장된 WebP의 프레임별 시간·투명도·각 파일 80,000바이트·정지본+동작본 35,000바이트·사이트용 전체 그림 640,000바이트 한도를 빌더에서 검사함.

재현은 `python -B -X utf8 tools/gwen_art/build_ready.py`, 최초 가져오기는 `--import-file <생성 PNG>`를 붙임. 기존 5종과 새 ready, 어두운 배경의 실제 160px 정지본 오른쪽에 단추를 놓은 배치, 저장된 WebP의 4프레임을 담은 `_tmp/_art_ready2_compare.png`를 확인해 채택했음. 검증은 `python -X utf8 -m unittest tests.gwen_art_test`임. 이번에는 ready 3개 파일과 이 폴더의 빌더·프롬프트·설명만 갱신했음.

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
