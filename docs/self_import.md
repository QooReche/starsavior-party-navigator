# 내 정보 불러오기(자기 계정) — 조사·준비 (2026-10-21)

목표: 사용자가 **자기 계정** 정보(보유 구원자·능력치·내실 반영 최종값, 가능하면 뽑기 기록)를 손 입력 없이 페이지에 채운다.
범위 밖: 다른 유저 정보, 게임 통신 가로채기·메모리 읽기(약관 위반 위험 — 하지 않는다).

## 다른 게임 사례

| 방식 | 사례 | 조건 |
|---|---|---|
| 기록 파일에 남은 웹 주소 → PowerShell 로 찾아 붙여넣기 | 원신·스타레일·명조 뽑기 기록(paimon.moe, starrailstation, wuwatracker) | 게임 안 기록 화면이 **웹페이지**이고 그 주소(임시 인증 포함)가 로컬 기록에 남아야 함 |
| 공식 공개 프로필 UID 조회 | 원신 Enka.Network | 개발사가 공개 API 를 열어 둬야 함 |
| 화면 캡처 글자 인식 → 표준 파일 | 원신 Inventory Kamera → Genshin Optimizer(GOOD 형식), 안드로이드판 scanner | 항상 가능. 화면 배치에 맞춘 인식 영역 필요 |

스타세이비어(studioBside, Unity, Steam·모바일): 2026-10-21 웹·GitHub 검색으로 **전용 불러오기 도구·공개 프로필 API 모두 없음**. 팬 DB(kanohban.github.io/StarSaviorArcanaDB)도 직접 입력+브라우저 저장 방식.
작업 PC 엔 게임이 없어(같은 개발사 CounterSide 기록만) 로컬 확인은 **설치된 PC 에서** 한다.

## 결론(1안)

- **능력치 화면 캡처 인식이 본선.** 능력치 화면 값에 내실(전술 분석·호감도)이 이미 들어 있어(`docs/ingame_samples.md`) 내실 입력이 필요 없고, 시뮬은 이미 화면 값=최종값 경로(`stats_final`)를 갖고 있다. 인식은 브라우저 안에서(사진 외부 전송 없음), 인식 엔진은 Pyodide 처럼 저장소에 직접 둔다(외부 CDN 금지 원칙).
- **뽑기 기록 주소 방식은 설치 PC 점검 결과에 따라.** 주소가 남으면 「명령어 한 줄 → 내 기록 불러오기」 가능.

## 설치된 PC 에서 할 일(순서)

1. 저장소 받기: `git clone https://github.com/QooReche/starsavior-party-navigator` (또는 `git pull`)
2. 게임 실행 → **뽑기 기록 화면·공지·이벤트 웹 화면을 한 번씩 연다** → 게임 종료
3. 점검(읽기 전용): `powershell -ExecutionPolicy Bypass -File tools\probe_local_game.ps1`
   - 결과 = `local\probe\probe_<시각>.md`(git 에 안 올라감). 게임 폴더를 못 찾으면 `-ExtraPath "<설치 폴더>"`
   - 주소의 ?·# 뒤 값과 긴 토큰은 가려진다. ★ 줄(gacha·history·record·webview·auth 등)이 핵심
4. 캡처 모으기 → `local\captures\` (git 에 안 올라감)
   - 구원자 **능력치 화면** 서로 다른 구원자 3장 이상(해상도·기기 다르면 각각)
   - **보유 구원자 목록** 화면 1~2장
   - (가능하면) 같은 구원자의 장비·잠재력 화면 1장
5. 그 PC 의 Claude 세션에 「파티 네비게이터 이어서 — 내 정보 불러오기」 + 보고서·캡처 위치를 알려 준다

## 설치 PC 점검 결과 (2026-10-21) — 로컬에서 계정 값을 읽는 길은 없다

- 점검 스크립트: 후보 3곳(`LocalLow\StudioBside\StarSavior`, Steam 설치 폴더). 웹 주소 597종 중 ★ 24종은 전부 내장 브라우저(CEF) 라이브러리·라이선스 문서의 주소. 게임 서버·뽑기 기록 주소 없음.
- 게임 로그(`LocalLow\StudioBside\StarSavior\Logs\Log-*.txt`)는 **단일 바이트 XOR `0x63`** 인코딩 UTF-8 평문이다(앞서 암호화로 오판). 내용은 장면 전환·전투 상태머신·서버 접속(`star-kr-game.sbside.com:9340`)·CDN 주소 등 클라이언트 동작뿐. `[Send]`/`[Recv]` 는 난독화된 패킷 **이름**만 찍는다(게임 코드 `Bs.ServerLibrary.dll` `SerializableExt.DumpToInfoLog`: `NetworkSetting.PacketDumpType` 이 `Name` 이면 이름만, `All` 이면 JSON 전체. 릴리스는 `Name`). 계정 값(보유 구원자·레벨·능력치)은 로그·레지스트리(PlayerPrefs 는 옵션뿐)·캐시 어디에도 없다 = 서버에만 있다.
- 값을 얻는 남은 경로는 통신 가로채기나 게임 메모리 읽기(예: starsavior-extractor 의 Frida 기능)뿐이다. **하지 않는다**(약관·제재·안티치트 위험, 업데이트마다 깨짐, 배포 불가). `PacketDumpType` 을 `All` 로 바꾸는 것도 변조라 하지 않는다. → **능력치 화면 캡처 인식(1안)으로 간다.**
- 게임은 Unity 6 **Mono** 라 `Data\Managed\*.dll` 이 일반 .NET 어셈블리다(UI 코드 `NKC.dll` 은 이름 약 70% 가독, 전투 로직 `NKM.dll`·`*.Templets.dll` 은 이름 난독화). 읽기 전용 정적 분석만 한다(원본 폴더 밖 사본에서).
- **정적 데이터 표(능력치·스킬·버프·피해 계수 등)는 비공개 저장소 `QooReche/starsavior-static-data` 에 있다** — 캡처 인식 기준값(이름·기본 능력치)과 시뮬 강화에 쓴다.

## 다음 세션(구현) 메모

- 설계는 구현 전 codex 동반(설계 게이트): 인식 엔진 후보(Tesseract.js 한글 모델 자체 호스팅 vs 숫자 전용 경량 인식+이름은 초상화·글자 대조) — 용량·정확도 비교.
- 흐름: 캡처 여러 장 → 이름·공격·방어·생명·속도·치명·치피 등 표 → 틀린 칸만 고침 → 적용 → `localStorage` 저장 → 추천·시뮬이 그 값 사용.
- 시험: 캡처 원본은 개인 계정 화면이라 저장소에 넣지 않는다. 시험용은 숫자만 뽑은 기대값 JSON + 잘라낸 비식별 조각만.
- 점검에서 뽑기 기록 주소가 나오면: 주소 형식·만료·필요 파라미터를 보고 별도 판단(인증값은 사용자 브라우저에만, 서버·저장소 저장 금지).
