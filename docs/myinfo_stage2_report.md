# 내 정보 기반 맞춤 추천 — 2단계 결과

2026-10-22, `feat/myinfo-stats`, 기준 커밋 `364e8ce`.
구현·생성·JS/Python 시험·실제 브라우저 확인은 완료했다. **전체 Playwright e2e 통과는 확인하지 못했다.** Windows 제한 환경에서 드라이버 파이프 생성이 `PermissionError: [WinError 5]`로 실패하여 21개 시험의 본문에 진입하지 못했다.

변경 파일:

| 파일 | 변경 |
|---|---|
| `party_template.html` | 내 정보 탭·육성 선택·카드 칩·판정·저장/삭제·지연 로딩·시뮬 연결 |
| `myinfo_reco.js` | 프로필/혼합 파티 어댑터·내 정보 해시·판정/부족분 계산 |
| `index.html` | 지정 빌더로 재생성 |
| `tests/fixtures/myinfo_synthetic.json` | 가짜 수치의 8명 합성 자료. 실제 계정 원본/샘플 복사 없음 |
| `tests/myinfo_reco_test.js` | JS 시험 6개와 메모리 실패 주입/원복 6개 |
| `tests/e2e/test_page.py` | 불러오기/삭제, 콘텐츠/모바일, 실제 시뮬 시험 3개 추가. 초기 성장표 요청 금지 검증 추가 |
| `tests/break_ui_test.js` | 기존 VM 환경에 내 정보 비활성 상태 추가 |
| `tests/run_workspace_test.py` | 임시 폴더를 작업 폴더 안에 생성하는 실행 보조 도구 |
| `docs/myinfo_format.md` | 적용 범위·화면·캐시·기존 정답 시험 설명 갱신 |
| `docs/myinfo_stage2_report.md` | 이 보고 |

화면 문구와 구성:

- 화면 전환: 「추천 파티」「내 정보」. 서랍 연결: 「내 정보 보기」.
- 육성: 「내 정보」「평균 (권장 100%)」「덜 키움 (권장의 80%)」「넉넉히 (권장의 125%)」「내 전투력」. 불러온 정보가 있으면 초기값은 「내 정보」.
- 내 정보 상단: 「스타링크 Lv120 · 전술 공통 Lv20 · 2026-10-01 · 보유 8명」, 「저장됨: 2026-10-01T12:34:56+09:00」(합성 예시).
- 조작: 「불러오기」「지우기」「정렬」「전투력순」「이름순」.
- 구원자: 초상화·이름·부제·「전투력」「★N · 각인 N」「공명」「호감도」「스킬」4칸·「장비 N/6 · 세트」·「공」「생」「방」「속도」.
- 파티: 「팀 전투력」 합계, 구성원별 전투력과 ★/각인 칩.
- 판정: 「오토 가능」「오토 어려움」「약 +N 전투력 필요」. 사다리에 성공 구간이 없으면 「필요량 산정 불가」. 실행된 결과만 「오토 클리어 X%」「수동 X%」.
- 상태: 「근사」「빌드 다름」「일부 가정」「미매핑 · 평균 가정」「Lv200 · 공명 10」「성장표 오류 · 평균 가정」. 미매핑 콘텐츠의 내 정보 탭에는 「일반 능력치」.
- 설명: 「근거·가정」 접기. 다크 고정, 390px 카드형.

시험 명령과 결과:

아래 Python 파일은 `python -X utf8 -I tests/<파일>`로 실행했다. `web_test.py`, `quick_test.py`는 Windows Python 3.13의 임시 폴더 ACL 문제로 직접 실행이 실패하여 `python -X utf8 -I tests/run_workspace_test.py tests/<파일>`로 실행했고 통과했다. 보조 도구는 새 폴더가 작업 폴더의 권한을 상속하게 하며 기존 경로의 권한을 바꾸지 않는다.

| Python 파일 | 결과 |
|---|---|
| `savior_fix_test.py` | 50/50 |
| `p5_test.py` | 21/21 |
| `p3_test.py` | 33/33 |
| `break_skill_test.py` | 19/19 |
| `enemy_target_test.py` | 10/10 |
| `web_test.py` | 10/10 |
| `rules_test.py` | 15/15 |
| `quick_test.py` | 7개 검사 통과, Python/JS 300건 일치 |
| `shim_compat_test.py` | 9개 검사 통과 |
| `golden_check.py` | 구원자 64 / 파티 150 / 스테이지 팀 10 일치 |
| `heal_burst_test.py` | 8/8 |
| `toughness_video_test.py` | 11/11 |
| `myinfo_stats_test.py` | 16/16, 비공개 경로의 기존 시험 3개 포함. 원본/샘플은 읽기만 하고 복사하지 않음 |

- `node tests/myinfo_reco_test.js --mutations`: 6/6, 잘못된 매핑·판정·혼합·고정 레벨·해시·시뮬 입력을 주입한 6개 모두 실패 감지 후 원복 통과.
- `node tests/break_ui_test.js`: 9개 묶음 통과. 내 정보 비활성 시 기존 시뮬 서명 바이트 유지 포함.
- `node tests/myinfo_import_test.js`: 통과, 로스터 56명/UID 56개.
- `python -X utf8 -I build_party_html.py index.html`: 정상, 약 1,596KB.
- `git diff --check`: 통과.
- Playwright: `E:/AI_mk2/venv-pw/Scripts/python.exe -X utf8 -I tests/e2e/test_page.py --shots E:/AI_mk2/pn-myinfo/local/shots ...` 및 전체 실행 `python -X utf8 -I tests/run_workspace_test.py tests/e2e/test_page.py --shots E:/AI_mk2/pn-myinfo/local/shots` 모두 드라이버 시작 전 `WinError 5`. **기존 18개 + 추가 3개 = 21개 미실행. 새 e2e의 실패 주입도 미실행.**

대신 ego-browser의 실제 로컬 Chromium 화면에서 확인한 결과(Playwright 전부 통과를 대체하지 않음):

- 저장 정보 없는 최초 요청에서 `growth.json` 요청 0, 불러온 뒤 1.
- 파일 불러오기 → 「내 정보」 기본 선택, 보유 8명, 전투력·★/각인·내실·정렬 표시, 새로고침 후 복원.
- 빠른 계산 팀 합계와 구성원 합계 일치(예: 41,435). 시뮬 요청의 8종 최종 능력치, `build:none`, `stats_final:true` 확인.
- 루나 합성 전투력: normal 10,146 → fixed200 17,379. 코스모 두 파티 중복 없음.
- SECTOR 15-3: 팀 40,970, 「오토 어려움」「약 +45,000 전투력 필요」.
- SECTOR 1-3: 기존 버튼으로 3팀 × 10판 오토, 이어 수동 모드. 「오토 클리어 100%」「수동 100%」 표시, 페이지 오류 없음. 동시에 실행하는 작업자 1개.
- 미보유 1명 혼합: 최종 능력치 3명 + 기존 가정 1명, 「일부 가정」.
- 미매핑 콘텐츠: 추천 개별 전투력 override 없음. 내 정보 탭은 normal 능력치를 계속 표시.
- 수동 전투력 모드와 내 정보 모드 배타 적용. 지우기 후 평균 가정·저장 키 삭제·캐시 0·서명 변경·추천 칩 제거.
- 내 정보/코스모 추천/부족 전투력 화면 모두 `scrollWidth=innerWidth=390`. 마지막 브라우저 검사 스크립트는 assertion으로 확인하고 통과.

화면 캡처(작업 폴더 내부, `local/`은 기존 gitignore 대상):

- `local/shots/myinfo_desktop.png`
- `local/shots/myinfo_mobile.png`
- `local/shots/myinfo_reco_mobile.png`
- `local/shots/myinfo_need_mobile.png`

설계에서 구체화한 부분:

- 수동 입력을 육성 「내 전투력」 옵션으로 명시했다. 입력 편집 시 그 옵션으로 전환하며, 다른 육성 모드에서는 입력값을 무시한다.
- 미보유/미매핑/성장표 오류의 기존 가정은 「평균」으로 고정했다.
- 양수 부족분이 반올림으로 0이 되는 경우 최소 1,000으로 표시한다. 사다리에서 실패하면 수치를 지어내지 않고 「필요량 산정 불가」를 표시한다.
- 세트 고유 명칭은 공개 성장표에 없어 효과 종류와 착용 수/필요 수로 표시한다.
- 미매핑 콘텐츠에서도 계정 탭 자체의 전투력을 볼 수 있도록 그 탭에는 normal 규칙을 사용한다.

남은 한계:

- 전체 e2e 실행은 파이프 생성이 허용되는 환경에서 다시 필요하다. 환경 제한을 우회하거나 권한을 변경하지 않았다.
- 축복·상시 패시브·PP는 기존 계산기의 미해석 항목이다. 전투력·최종 능력치와 클리어 확률은 근사이며, 계수 재맞춤은 하지 않았다.
- 기존 실제 능력치 목표 중 생명력 4명의 ±1% 미달은 남아 있다. 현재 1단계 시험은 목표 미달 보고와 별도 회귀 허용치 검사를 구분하므로 16개 통과가 정밀 재현 완료를 뜻하지 않는다.
- 빠른 계산은 전투력을 표준 능력치로 환산하며, 시뮬의 내부 전투력 공식은 스킬 레벨 합 34를 가정하는 기존 차이가 남아 있다. 플래시 포인트 fixed200 연결도 기존 추정이다.

커밋·푸시·`tools/update.py`·계수 재맞춤·전체 사전 계산은 실행하지 않았다. 소스와 산출물 쓰기는 `E:/AI_mk2/pn-myinfo` 안에서만 수행했다.
