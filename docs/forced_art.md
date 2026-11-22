# 강제 탐색 연출 그림(`assets/forced/`)

«후보 전체 훑기»에 들어갔을 때만 쓰는 그림임. 평소 화면은 이 폴더를 받지 않음(훑기에 처음 들어갈 때 한 번 받음).
폴더를 통째로 빼도 화면은 동작함: 그웬 길은 CSS 밤하늘 바탕만, 오염 그웬은 원래 그림에 색조만 입혀 보임.

화면 쪽 설명(상태·문구·시험)은 [fullscreen_measure_1121.md](fullscreen_measure_1121.md)의 «강제 탐색» 절에 있음.

## 파일

| 파일 | 쓰는 곳 | 만든 방법 |
|---|---|---|
| `scene.webp` (1800×600) | 그웬 길 배경 한 장 | 받은 배경 그림을 크기만 줄임 |
| `scene_narrow.webp` (800×555) | 폭 760px 이하의 그웬 길 배경 | 같은 그림에서 가로 17~65% 구간(의자~광장)만 잘라 줄임 |
| `gwen_back.webp` (284×520) | 배경 속에 서 있는 뒷모습 그웬 | 받은 투명 그림을 여백만 자르고 줄임 |
| `gwen/<표정>.webp` (192×192) | 진행 칸 기록 줄의 오염 그웬 | 저장소의 SD 그웬 그림을 가공(아래) |
| `gwen/<표정>_eyes.webp` | 위 그림에 겹치는 눈빛 층 | 같은 가공에서 눈빛만 따로 저장 |

표정은 `charge`·`files`·`investigate`·`verdict` 4개임(`gwen_lane.js` `FORCED.arts`, 시험이 생성 목록과 같은지 확인함).

## 다시 만들기

```
python -X utf8 tools/build_forced_art.py                    # 오염 그웬만(저장소 안 그림만 씀)
python -X utf8 tools/build_forced_art.py --gen-dir <폴더>   # 배경(lavistar_ruin_bg_1.png)·뒷모습(gwen_back_illust_1.png)까지
python -X utf8 tools/build_forced_art.py --all-gwen         # 깜빡임 그림이 있는 SD 표정 전부
```

- 같은 입력이면 같은 결과가 나옴(난수 씨앗 = 표정 이름).
- 오염 그웬 가공: 눈 위치는 같은 표정의 기본 그림과 깜빡임 그림(`*_blink.png`)이 다른 곳으로 찾음. 그 안의 홍채를 적색으로, 흰자를 어둡게 바꿈. 몸은 채도를 낮추고 보라·검붉은 톤으로, 윤곽 근처에 얼룩과 뚫린 자리, 균열 4줄, 가로 글리치 띠 3개를 넣음.
- 눈빛은 그림 2장을 번갈아 끼우지 않음. 눈빛 층 한 장의 투명도를 CSS 가 부드럽게 바꿈(키프레임 5개).

## 그림 바꿔 끼우기

- **배경**: 새 그림을 `lavistar_ruin_bg_1.png` 이름으로 두고 위 명령(`--gen-dir`)을 다시 돌리면 `scene.webp`·`scene_narrow.webp` 가 바뀜. 가로세로 비율이 3:1 이 아니면 `forced.css` 의 `--fx-ar`(넓은 화면 3, 좁은 화면 1.44)도 맞춤. 좁은 화면용 자르는 구간은 `tools/build_forced_art.py` 의 `NARROW` 임.
- **뒷모습 그웬**: 새 투명 그림을 `gwen_back_illust_1.png` 이름으로 두고 같은 명령을 돌리면 `gwen_back.webp` 한 장만 바뀜. 비율이 달라지면 `forced.css` `.fx-gwen` 의 `aspect-ratio`(지금 284/520)를 맞춤. 서는 자리는 `--fx-gx`(가로)와 `.fx-gwen` 의 `inset`(세로)임.
- 움직이는 층(안개 2겹·재·불씨·고리 빛·주기 노이즈)은 그림이 아니라 `forced.css` 의 CSS 임.

## 출처

- 배경(`scene*.webp`)·뒷모습(`gwen_back.webp`): 사이트 운영자가 그림 생성 도구로 만든 임시 그림임. 정식 그림으로 바꿀 예정임. 원본 PNG 는 저장소에 넣지 않음.
- 오염 그웬: 저장소의 팬 그림(`assets/ui_icons/gwen/`, 기록은 `tools/gwen_art/README.md`)을 가공한 것임.
- 외부 사이트에서 받은 그림은 없음.
