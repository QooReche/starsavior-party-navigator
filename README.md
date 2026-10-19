# 스타세이비어 파티 편성 네비게이터 (시험판)

콘텐츠(작전·성간 회랑·플래시 포인트·코스모 게이트 등)와 스테이지를 고르면, 그 적의 속성 분포에 맞는 4인 파티(전열 2/후열 2)와 브레이크 스킬, 대체 구원자를 보여 주는 개인용 도구입니다. 점수는 **자동 계산한 참고용**이며 검증된 공략이 아닙니다.

## 계산 방식
- DB 티어(가이드 DB의 PVE 티어) + 속성 상성 + 주 사용 콘텐츠 여부 + 팀 기능 태그(힐·보호막·딜 버프 등)
- 규칙값(가중치, 상성, 콘텐츠, 브레이크 스킬, 뉴비 편성 유형)은 `party_contents.json` 에서 고친다. 가중치는 임의값이다.
- 구원자 기능 태그는 스킬 텍스트에서 키워드로 뽑은 것이라 오판이 있다(`docs/synergy_tags_review.md`).

## 사용
```
python -X utf8 -I party_reco.py 작전 --stage "SECTOR 1-1"          # 콘솔
python -X utf8 -I party_reco.py "코스모 게이트" --stage 길레 --owned wedding-carmen,fei,...
python -X utf8 -I build_party_html.py                              # ..\release\party_preview\index.html 생성(단일 HTML)
```
`-I` 는 스크립트 폴더를 import 경로에서 빼므로 `build_party_html.py` 는 스스로 경로를 추가한다.

## 폴더
- `data/` 입력 데이터: `db_tier.json`(티어·주 사용 콘텐츠), `synergy_tags.json`(기능 태그), `foe_stages.json`(스테이지별 적 정보 4.6MB), `kinds.json`(어나더/코즈믹), `savior_reco.json`·`saviors_index.json`(구원자 목록·이미지 경로)
- `assets/` 직업·속성 아이콘, 브레이크 스킬 원형 이미지
- `tools/build_foe.py` 데이터북 `foe.js` -> `data/foe_stages.json` 재생성
- `docs/` 조사 자료(전투 규칙·콘텐츠 정리, 브레이크 스킬, 뉴비 편성 공략 요약, 태그 검수표)

## 출처와 주의
- 구원자·적·티어·편성 정보: 가이드 DB(starsavior-guide.github.io), 팬 데이터북(starsavior-databook.pages.dev), 나무위키, 아카라이브 글, 제3자 DB(브레이크 스킬 효과). 데이터북 재사용은 사용자가 허락받은 것으로 확인되었다(2026-10-19).
- 직업·속성 아이콘과 브레이크 스킬 이미지는 게임 리소스다. 사용 허락은 사용자가 확인했다고 함(2026-10-19).
- 구원자 초상화·일러스트는 가이드 DB 사이트에서 내려받아 줄여서 `assets/savior/` 에 담았다(`tools/fetch_images.py`, 사용자가 이미지 저장을 허락). 웹 페이지(`index.html`)는 이 상대 경로를 쓴다.
- 게임 화면·실전 편성 효과는 검증하지 못했다.

## 재생성 메모(저장소에 없는 입력)
- `synergy_tags.py <databook main.json>`: 데이터북 `data/main.js` 를 JSON 으로 푼 파일이 필요하다.
- `crop_break_icons.py`: 인게임 브레이크 스킬 스크린샷을 `break_ref/7~11.png` 로 둔다(특이점 관측, 스타피어서, 큐브 과부하, 행성 정화, 차원 강습 순).
- `tools/build_foe.py`: 데이터북 `data/foe.js` 를 `tools/raw/` 에 내려받아 둔다.

## 공개/테스트
- GitHub Pages: https://QooReche.github.io/starsavior-party-navigator/ (시험 공개, 점수는 오토 전투 기준을 염두에 둔 참고용이며 가중치 검증 중)
