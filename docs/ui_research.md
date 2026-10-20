# 파티 편성 네비게이터 P4 — UI/UX 참고 조사

작성 2026-10-20. 대상: `E:\AI_mk2\starsavior-party-navigator\party_template.html`(→ `index.html`, GitHub Pages). 설계 근거: `docs/battlesim_design.md` §4·§4-1.
읽기 전용 조사이며 저장소는 손대지 않았다.

## 0. 전제

- **P4 가 화면에 더할 것**: 추천 파티마다 ① 클리어 확률(몬테카를로, 범위 포함) ② 처치 턴 중앙값(p10–p90) ③ 전멸 확률 ④ 누가 몇 턴에 먼저 쓰러지나 ⑤ 피해 기여 % ⑥ 「이 추천은 ○○ 가정에 기댐」 한 줄. 생존은 **관문**(클리어 확률 먼저, 비슷하면 처치 턴). 「오토 / 수동」 선택(기본 오토), 수동이면 **서순(스킬 순서 가이드)** + 오토 대비 개선치(「수동 시 처치 턴 −1.3」).
- **제약**: 브라우저에 Python 없음 → 사전 계산 JSON. 단일 정적 HTML, 한국어, 다크 테마, PC·모바일 공용, 새 무거운 라이브러리 없이 HTML/CSS/바닐라 JS.
- **조사 방법**: 웹 검색 + 페이지 열람(Chrome 확장으로 실제 렌더 확인: gcsim.app, prydwen.gg HSR/Endfield, fribbels.github.io, calc.pokemonshowdown.com, thebalanceffxiv.com, 현재 라이브 페이지). GitHub README 는 WebFetch. 열리지 않은 것(schaledb, prydwen NIKKE 는 403, gcsim 공유 결과 뷰어는 DB 페이지 미준비)은 README·기억에 의존했고 아래에 그렇게 표시했다.
- **못 한 것**: 모바일 폭 실측(창 크기 변경이 적용되지 않아 CSS 로만 판단), game8·gamewith 팀 빌더(검색에 안 잡힘), HSR 행동 순서 시각화 웹 도구(존재 확인 못 함 — 엑셀 기반 `StarRail-Action-Sequence-speed-tool` 뿐).

---

## 1. 참고 사례 (14건)

형식: URL / 무엇을 보여주나 / 레이아웃·패턴 / 가져올 것 / 피할 것

### 1-1. gcsim — 원신 몬테카를로 전투 시뮬레이터
- URL: https://gcsim.app/ (한국어 UI 제공), https://github.com/genshinsim/gcsim, https://docs.gcsim.app/
- 보여주는 것: README 「mean DPS and the DPS distribution across iterations」, 「sample of 1 iteration … lists every action, damage instance」. 문서는 통계 목록(캐릭터별 피해 분포, 스킬별 분포, 원소 에너지, 반응 횟수, 필드 피해)만 적고 뷰어 레이아웃 설명은 없음.
- 레이아웃(실제 뷰어는 열지 못해 **기억 기반**): 맨 위 「요약 카드」= 4인 초상화 + 반복 횟수·시뮬 길이·**DPS 평균 ± 표준편차·최소·최대**. 아래 탭: 결과(DPS 히스토그램, 캐릭터별 DPS 파이·막대, 원소/대상별, 시간축 피해 그래프), 설정, **샘플(1판 재생: 프레임 축 × 캐릭터 행에 행동 블록이 늘어선 표)**. 홈 화면은 다크 네이비 배경 + 카드 + 파란 주 버튼.
- 가져올 것: ① **요약 카드 한 장에 평균·범위·표본 수를 같이** 두는 것(우리 KPI 스트립의 원형). ② **「1판 샘플」을 턴×캐릭터 행렬로 재생**하는 것 — 서순 표의 원형. ③ 「분포」를 통계 용어 없이 「반복해서 돌린 결과의 퍼짐」으로 읽게 하는 배치(평균 옆 ± 작게).
- 피할 것: 히스토그램·파이·시간축 그래프를 전부 펼치는 것(시뮬 사용자용). 우리는 **플레이어용**이라 히스토그램 대신 범위 바 하나.

### 1-2. Prydwen HSR 캐릭터 페이지 — 「Calculations」 탭
- URL: https://www.prydwen.gg/star-rail/characters/acheron (탭: KIT / REVIEW / BUILD AND TEAMS / MOC·PF·AS STATISTICS / CALCULATIONS)
- 보여주는 것: 「DAMAGE OUTPUT」— 1타겟 / 3타겟 두 패널, 각 패널에 돌파(E0~E6)별 **가로 막대**(막대 안에 「1,191,414 dmg (-7.4 SP)」, 오른쪽 끝에 기준 대비 **%**: 100.00% → 169.81%), 막대 색이 초록→노랑→주황→빨강으로 값에 따라 변함.
- 레이아웃·패턴: 맨 위 **빨간 경고 배너**(「Don't use the damage output calculations as an indication on who is worth pulling … treat them as the 'floor'」) → 「Simulation rules」 **접힘 패널** → 「Important! The calculation assume you're pairing Acheron with 2x Nihility teammates …」(가정 한 줄, 빨강 강조) → 막대 → 아래에 계산에 쓴 장비(접힘). 「UPDATE TRACKER」 표(리뷰 갱신 패치 / 계산 갱신 패치 / 프로필 갱신일).
- 가져올 것: ① **가정을 결과 바로 위에 한 줄로**(「Important!」) — 우리 ⑥ 「가정 의존」의 위치와 어투. ② **규칙 전문은 접힘**, 요약만 노출. ③ 막대 안에 절대값, 끝에 상대값(%) — 피해 기여 % 막대에 그대로 적용 가능. ④ 「언제 계산했나」 표시(우리: 데이터 패치·규칙 버전·시드·표본 수).
- 피할 것: 7단계 색 그라데이션(색각 이상에 약하고 다크에서 노랑·연두가 번짐) — 우리는 3단(좋음/보통/나쁨)+아이콘. 광고·배너가 결과 사이에 끼는 구조.

### 1-3. Prydwen HSR — 「TEAMS」 (Memory of Chaos 등 콘텐츠 탭)
- URL: 위 페이지 BUILD AND TEAMS 탭 하단
- 보여주는 것: 콘텐츠 4개를 **배너형 탭**(Memory of Chaos / Pure Fiction / Apocalyptic Shadow / Anomaly Arbitration)으로 바꾸고, 각 팀은 **한 줄 = [Rank 48 / App. rate 0.76% / Avg. cycles 9.33 / Avg. cycles(E1+) 7.49] + 초상화 4장**. 2열 그리드.
- 가져올 것: ① 「Avg. cycles」= 우리 「처치 턴」의 직접 대응. **팀 한 줄에 숫자 3개 + 얼굴 4개**면 비교가 끝난다 — 「상위 후보 파티」 목록(관문 통과한 10팀) 보기에 적합. ② 콘텐츠별 탭 = 우리 콘텐츠 select 와 같은 역할이므로 모바일에서 select 유지가 맞음(배너 탭은 폭을 먹음).
- 피할 것: 「Rank」 「App. rate」처럼 커뮤니티 통계 용어 — 우리 데이터엔 없고, 있어도 설명 없이 쓰지 말 것.

### 1-4. Fribbels HSR Optimizer — Benchmarks·Showcase·Combo rotation
- URL: https://fribbels.github.io/hsr-optimizer/ (Benchmarks, Optimizer 화면 열람)
- 보여주는 것: Benchmark Generator — 입력 패널(캐릭터·돌파 E0~E6 세그먼트·광추·팀원 3명 얼굴·설정) 아래에 **빨간 테두리 경고 카드** 「Do NOT use Combo DMG or DPS Score to compare teams, light cones, or eidolons!」 + 4개 불릿 설명 + 파란 버튼 「Understood, hide warning」. 결과는 「100% / 200% Benchmark Builds」 탭의 표(Combo DMG, Delta, 부위별 메인스탯, 세트). Optimizer 화면: 「Combo DMG ability rotation」 패널에 **Simple / Advanced** 토글 + 행동 목록(Basic…) 편집기. Showcase: 캐릭터 카드에 「DPS Score 151.1% AEON」 처럼 **점수 + 등급 글자**.
- 가져올 것: ① **「이 숫자로 비교하면 안 되는 것」을 한 번 보여주고 숨길 수 있는 경고**(localStorage 기억) — 우리 「시험판·가정한 모델의 확률」 면책에 적용. ② 로테이션 편집의 **Simple/Advanced** 2단 — 서순 표도 「기본 3턴 / 전체」 2단으로. ③ 점수에 **등급 글자**(우리: 클리어 확률 → 「안정/보통/불안/위험」).
- 피할 것: 입력 패널이 결과보다 큰 구조(우리는 입력이 이미 끝난 상태에서 결과만 보여줌). 조밀한 수치 표(Optimizer 그리드)는 모바일 불가.

### 1-5. Fribbels Epic Seven Gear Optimizer (README)
- URL: https://github.com/fribbels/Fribbels-Epic-7-Optimizer
- 보여주는 것: 결과 표의 **첫 줄 = 현재 장착 상태**(비교 기준), 「Each column is color coded based on the min/max ranges of the stat on each page」, Stats 패널 「hero's current stats on the left vs the new stats on the right」.
- 가져올 것: **기준선을 첫 줄에 고정**하고 나머지를 상대 비교 — 우리 오토/수동: 오토 결과를 기준으로 두고 수동은 **델타(−1.3턴, +4%p)** 로 표시. 「왼쪽 현재 / 오른쪽 새 값」 2열 비교는 모바일에서도 성립.
- 피할 것: 열마다 min/max 로 색칠하면 색이 너무 많아진다.

### 1-6. Pokémon Showdown Damage Calculator / pkmn/dmg
- URL: https://calc.pokemonshowdown.com/ , https://github.com/pkmn/dmg
- 보여주는 것: 결과 한 줄 — 「252 SpA Abomasnow Blizzard vs. 0 HP / 0 SpD Abomasnow: 162-192 (50.4 - 59.8%) — **guaranteed 2HKO**」, 그 아래 「Possible damage amounts: (162, 165, …)」. 확률이 끼면 「**98.7% chance to 3HKO** after Leftovers recovery」(pkmn/dmg README). 레이아웃은 좌(공격) / 중앙(필드 조건) / 우(방어) 3열, 기술 4개 버튼에 각각 「29.9 - 35.5%」 범위가 붙어 있음.
- 가져올 것: ① **확률을 문장으로**: 「10판 중 9판 클리어 · 보통 5턴(4~7턴)」처럼 **범위 + 보장/확률 어휘**. 「guaranteed」= 우리 「거의 확실(≥97%)」, 「xx% chance」= 그 아래. ② 상세 수치(「Possible damage amounts」)는 **한 줄 아래 작은 글씨**로 — 우리 p10/p90·표본 수·신뢰구간 자리.
- 피할 것: 2000년대식 조밀한 폼. 범위 수치만 있고 등급 색이 없어 훑어보기 어렵다.

### 1-7. The Balance (FFXIV) — 오프너(스킬 순서) 이미지
- URL: https://www.thebalanceffxiv.com/jobs/casters/black-mage/openers/ (「Standard "5+7" Opener」 이미지)
- 보여주는 것: **가로 타임라인 1줄**(회색 선) 위에 GCD 스킬 아이콘이 1,2,3… 번호와 이름을 달고 등간격으로 서고, GCD 사이에 끼우는 oGCD 는 **선 위쪽에 작은 아이콘 쌍**으로 올라가 있음. 버프 이름(Ley Lines, Manafont…)은 더 위에 가는 선으로 묶음. 24개를 넘으면 **2줄로 줄바꿈**. 이미지 아래 산문 설명 + 「Additional notes」 불릿 + 「Patch Applicable: 7.4」·갱신일. 다크 배경에 아이콘만 색.
- 가져올 것: ① 아이콘 + **번호** + 짧은 이름 세트(이름 없이 아이콘만 두지 않음 — 우리 유저는 스킬 아이콘을 못 외운다). ② 「끼워 넣는 행동」(우리: 협공·추가 발동)은 **주 행동 선 위에 작게**. ③ 「이 순서는 ○○ 전제」(prepull, countdown) 같은 전제를 순서표 바로 위에 한 줄.
- 피할 것: 이미지로 굽는 것(검색·복사·모바일 확대 불가). 우리는 DOM 으로.

### 1-8. Prydwen Arknights: Endfield — Rotation Builder
- URL: https://www.prydwen.gg/arknights-endfield/tools/rotation-builder
- 보여주는 것: **행 = 캐릭터 4슬롯(왼쪽 「+ Select」 칸), 열 = 시간(0s, 1s, … 18s) 그리드**. 아래 「AVAILABLE ACTIONS」 = 색 블록 5종(Final Strike 빨강 / Finisher 노랑 / Combo Skill 보라 / Battle Skill 하늘 / Ultimate 초록)을 드래그해 타임라인에 놓음. 「Export & Share」(URL 쿼리에 상태) / 「Clear Rotation」.
- 가져올 것: ① **행동 종류를 색 블록으로 고정**(기본기/특수기/궁극기/노바 버스트 4색) — 서순 셀의 배지 색. ② 상태를 **URL 쿼리**로 공유(우리도 `?c=작전&s=1-1&mode=manual` 정도는 쉽게 가능). ③ 가로 스크롤 타임라인은 PC 전용이라는 반면교사.
- 피할 것: 빈 그리드로 시작하는 편집기(우리는 결과 표시용), 가로 스크롤(모바일에서 턴이 보이지 않음).

### 1-9. EndSync / Arknights Companion (Overwolf) — 로테이션 타임라인 + 데미지 계산기
- URL: https://www.overwolf.com/app/hins-endsync , https://arknightscompanion.overwolf.com/ (검색 요약만 확인, 설치형이라 화면은 못 봄)
- 보여주는 것: 「My Teams」 저장 + 「rotation timeline and damage calculator」, 「step-by-step ability rotations for your squad」. 로스터·팀을 **로컬 저장(계정·클라우드 없음)**.
- 가져올 것: 「팀 저장 + 서순 + 피해 계산」 셋을 한 화면에 묶는 흐름, 로컬 저장(우리 localStorage 와 같은 방향).
- 피할 것: 데스크톱 앱 전제의 밀도.

### 1-10. West Games — HSR Speed Breakpoint Calculator
- URL: https://west-games.com/honkai-star-rail-speed-breakpoint-calculator/
- 보여주는 것: 행동값(AV=10000/SPD), 사이클(0사이클 150AV, 이후 100AV), 버프·디버프·행동 당김을 입력하면 **몇 사이클에 몇 번 행동하는지** 숫자로 답하는 계산기. 타임라인 그림 없음.
- 가져올 것: 「사이클/턴」 기준을 **결과 옆에 정의**(우리 `ttk_basis: 모델 기준 턴(100틱), 클리어한 판만` 을 그대로 작은 글씨로).
- 피할 것: 입력 폼 + 숫자만 있는 형태 — 플레이어는 「몇 턴에 누가 움직이나」 그림을 원한다.

### 1-11. 불확실성 전달 연구 (비전문가 대상)
- URL: Padilla·Kay·Hullman 2020 「Uncertainty Visualization」 https://moodle2.units.it/pluginfile.php/466375/mod_resource/content/0/Uncertainty_Visualization_Padilla_Kay_Hullman_2020.pdf · data.europa.eu 시각화 가이드(frequencies·icon arrays) https://data.europa.eu/apps/data-visualisation-guide/frequencies · 유전 위험 범위 표시 RCT(1,300명) https://pmc.ncbi.nlm.nih.gov/articles/PMC9731905 · 아이콘 배열 언어화 연구 https://arxiv.org/pdf/2207.09608
- 요지: ① **빈도 프레이밍**(「100명 중 10명」)이 저수리력 독자에게 %보다 정확히 전달. ② 아이콘 배열은 위험 추정 정확도를 올리고 분모 무시를 줄임. ③ **범위**를 그리는 방법(음영·그라데이션·화살표)은 서로 유의차 없음 → 범위는 **간단한 음영 띠**면 충분. ④ 미리 정해진 **순서형 범주(등급)** 가 인지 부담을 줄임(저수리력엔 저정밀 표현이 오히려 적절). ⑤ 분위수 점 플롯(quantile dot plot)은 분포 전달에 좋지만 공간을 먹음.
- 가져올 것: 클리어 확률은 **「% + 10판 중 n판」 병기** + 4단계 등급 라벨; p10–p90 는 **단순 음영 띠**; 아이콘 배열(10칸)은 선택 사항(모바일에선 띠 하나가 낫다).
- 피할 것: 신뢰구간·표준편차 용어를 전면에. 「분포」 그래프.

### 1-12. 승률 바 패턴 — 체스 평가 바·스포츠 승률 (일반 패턴, 기억 기반)
- 예: chess.com 분석 화면의 세로 평가 바(백/흑 2톤, 수치 한 개), FiveThirtyEight 경기 예측의 「승률 72%」 큰 숫자 + 2색 가로 바. 특정 페이지를 열어 확인하진 않았다.
- 패턴: **큰 숫자 하나 + 2톤 바 + 즉시 읽히는 색**. 구간이 아니라 단일 값이 먼저, 범위는 보조.
- 가져올 것: KPI 타일의 기본형. 우리 「클리어 확률」= 큰 숫자 + 가로 2톤 바(클리어 / 나머지), 바 위에 p10–p90 음영 띠를 얹음(1-11 ③).
- 피할 것: 바 하나에 3가지 결과(클리어·타임아웃·전멸)를 다 쪼개 넣기 — 전멸 확률은 **조건부로만**(≥10% 일 때 경고 칩).

### 1-13. FFLogs 「Damage Done」 표 (기억 기반)
- URL: https://www.fflogs.com/ (리포트 화면)
- 패턴: 플레이어 행마다 **가로 막대(길이=기여 %) 안에 이름, 오른쪽에 절대값과 %**, 직업 색. 정렬은 기여순.
- 가져올 것: 피해 기여 % 를 **카드 아래 얇은 막대 + %** 로. 4명이 100% 가 되도록(힐·보호막은 별도 작은 글씨 「회복 n」).
- 피할 것: 파이 차트(4조각이라도 읽기 어렵고 라벨이 겹침).

### 1-14. 게임 안 「행동 순서 바」 (플레이어의 기존 멘탈 모델)
- HSR 왼쪽 세로 행동 순서 바, 스타세이비어의 행동 게이지(속도 기반) — 플레이어는 이미 「위에서 아래로 행동이 내려오는」 그림에 익숙하다.
- 가져올 것: 서순 표의 **세로 = 시간 흐름**(위에서 아래). 1-7·1-8 의 가로 타임라인보다 모바일에 맞고, 플레이어 직관과 같다.

---

## 2. P4 추천 레이아웃

### 2-1. 정보 위계와 배치(데스크톱 ≥761px)

파티 블록(`.party`) 안 순서를 다음처럼 바꾼다. 기존 요소는 그대로 두고 **두 덩어리를 끼운다**.

```
.party
 ├ .phead         파티 1 · [오토|수동] 모드 칩 · (근거 보기 시) 점수
 ├ .forecast  ★신규  「전투 전망」 스트립 — KPI 타일 4개 + 가정 한 줄
 ├ pairNotes / leadNote / gimNote / synSummary (근거 보기 시)
 ├ .rowcards      카드 4장 (BACK FRONT FRONT BACK)
 │   └ .under   ★추가  카드마다: 피해 기여 막대 · 사망 확률 점 · (수동) 역할 한 줄
 ├ .seq       ★신규  서순 표 — 수동일 때만, 기본 3턴 펼침
 └ .bbar          브레이크 스킬
```

**`.forecast` 스트립** (카드 위, 전폭, `display:grid; grid-template-columns:repeat(4,1fr); gap:10px`):

| 타일 | 큰 값 | 보조 | 시각 |
|---|---|---|---|
| **클리어 확률** (관문·1순위) | `91%` | `10판 중 9판` · 등급 칩 「안정」 | 2톤 가로 바(채움=클리어), 바 위에 윌슨 95% 구간 음영 띠 |
| **처치 턴** | `5턴` | `보통 4~7턴` (p10–p90) · 「모델 기준 턴, 클리어한 판만」 | 1~턴제한 축의 범위 띠, 중앙값 점. 턴 제한선(세로 점선) |
| **먼저 쓰러지는 구원자** | 얼굴 46px + 이름 | `3턴쯤 · 사망 확률 35%` 또는 `아무도 안 쓰러짐(≥90%)` | 얼굴 테두리 = 등급색 |
| **전멸 확률** | `4%` | `타임아웃 5%` | 작게. **≥10% 면 빨간 칩 「전멸 위험」** 로 승격해 1번 타일 옆에 붙임 |

타일 아래 **가정 한 줄**(`.assume`, 기존 `.leadnote` 모양 재사용, 왼쪽 테두리 색만 `#ffb454`):
「⚠ 이 추천은 **적 공격 ×1.85 가정**에 기댑니다 — 가정을 바꾸면 순위가 뒤집힙니다 · 규칙 보기 ▸」 → 클릭 시 `<details>` 로 민감도 표(가정 / 기본값 / 대안 / 뒤집히는 순위) 펼침. 뒤집히는 변수가 없으면 「✔ 주요 가정을 바꿔도 순위 유지」로 초록.

타일 맨 끝 작은 글씨: `표본 400판 · 시드 7 · 데이터 2.50(10/15) · 규칙 v3` — 1-2 의 UPDATE TRACKER 축약.

**카드 아래(`.under`) 추가 줄** — 기존 `.ico` 줄 바로 밑:
```
[■■■■■■■□□□] 피해 41%        ← 얇은 막대(높이 6px) + %
● 쓰러질 확률 35% · 3턴쯤        ← 점 색 = 등급, 0~5% 면 「생존 안정」 회색
```
수동 모드면 셋째 줄에 `역할: 1턴 특수기로 협공 유도` 처럼 서순에서 뽑은 한 줄.

**후보 파티 목록**(관문 통과 상위 10팀 중 2~5위)은 `.party` 아래에 1-3 패턴으로 `<details>` 「다른 후보 4팀 보기」: 한 줄 = 얼굴 4개 + 클리어 % + 처치 턴 + 차이(「−3%p · +1턴」). 누르면 그 팀으로 위 블록 교체(JSON 에 10팀 결과를 모두 담는다).

### 2-2. 모바일(≤760px)

- `.forecast` → `grid-template-columns:1fr 1fr` 2×2. 순서: 클리어 확률 / 처치 턴 / 먼저 쓰러짐 / 전멸. 큰 값 22px, 보조 12px.
- 가정 한 줄은 **한 줄 말줄임 + 「더보기」**(`-webkit-line-clamp:1`).
- `.rowcards` 는 지금 2열(`repeat(2,1fr)`)인데 **BACK/FRONT/FRONT/BACK 순서가 2행으로 꺾이면 「인게임 왼쪽부터」 의미가 깨진다**. 두 안 중 택1:
  - (권장) 4열 유지 + 카드 폭 ≈ 80px: `.card` 안 글자를 11px→ 이름만, 티어 칩은 카드 밖 `.under` 로 내림. 세로 비율 3/5.6 이라 높이 150px 정도로 수용 가능.
  - 또는 2열로 두되 열 머리글을 「후열 / 전열」 로 바꿔 배치 의미를 다시 부여(앞줄에 FRONT 2장, 뒷줄에 BACK 2장) — 데이터 순서 변경이 필요해 PC 와 어긋남.
- 피해 기여 막대·사망 점은 그대로(카드 폭에 맞춰 줄어듦).
- 서순 표는 4열 고정(구원자 열)이라 폭 360px 에서 열당 ≈ 80px — 배지는 아이콘 + 2~3글자(「특수」「궁극」「기본」)로 줄이고 대상·협공 표시는 아이콘만.

### 2-3. 불확실성·가정 의존을 플레이어 말로

| 숫자 | 화면 표현 | 피할 표현 |
|---|---|---|
| clear_p + ci95 | `91%` 크게 + `10판 중 9판` + 등급 칩 + 바 위 음영 띠(구간) | 「95% 신뢰구간 [0.87, 0.94]」 |
| ttk_median, p10–p90 | `5턴` + `보통 4~7턴` | 「p10/p90」, 「중앙값」 용어 자체 |
| wipe_p, timeout_p | 작게, 임계 넘으면 칩 승격 | 바 하나에 3분할 |
| first_death_p, death_turn_median | 얼굴 + 「3턴쯤 쓰러질 수 있음(35%)」 | 표 |
| dmg_share | 막대 + % | 파이 |
| assumptions_used + 민감도 | 「이 추천은 ○○ 가정에 기댐」 한 줄 + 펼침 | 가정 목록 전부 노출 |
| n_runs, seed, ttk_basis, 데이터 버전 | 10~11px 회색 한 줄 | 생략(재현성 때문에 꼭 남김) |

**등급 4단계**(색 + 아이콘 + 글자 — 셋 다 둔다):

| 등급 | 조건(초안) | 색 토큰 | 아이콘 |
|---|---|---|---|
| 안정 | clear_p ≥ 0.9 이고 wipe_p < 0.05 | `--good` | ✔ |
| 보통 | 0.7 ≤ clear_p < 0.9 | `--acc` | ● |
| 불안 | 0.4 ≤ clear_p < 0.7 또는 wipe_p ≥ 0.1 | `#ffb454`(기존 warn) | ▲ |
| 위험 | clear_p < 0.4 또는 wipe_p ≥ 0.25 | `--bad` | ✖ |

관문에서 떨어진 팀(`gate_ok=false`, 미지원 생존 기믹)은 등급 대신 회색 칩 「계산 불가: ○○ 효과 미지원」 — 「0%」로 보이지 않게 한다.

「난수 때문의 퍼짐」(구간 띠)과 「규칙을 몰라서 생기는 불확실성」(가정 한 줄)은 설계대로 **섞지 않는다**: 전자는 바 위 띠, 후자는 노란 테두리 문장.

### 2-4. 「오토 / 수동」 토글

- 위치: 상단 `.panel .row` 의 **「추천」 버튼 오른쪽**, 세그먼트 컨트롤 `[오토] [수동]` (라디오 2개를 `label` 로 감싼 pill, 기본 오토). 「추천 근거 보기」 체크박스는 그 다음으로 밀림.
- 상태 저장: `LS.set("mode", …)`, URL 쿼리 `?mode=manual` 도 반영(공유용).
- 동작: 수동 선택 시 ① 같은 파티의 `manual` 결과로 `.forecast` 숫자 교체, 각 타일에 **델타 배지**(「−1.3턴」「+4%p」; 좋아지면 `--good`, 나빠지면 `--bad`, ±0 은 숨김) ② `.seq` 서순 표가 열림 ③ 파티 헤더 칩이 「수동 · 서순 기준」으로 바뀜.
- 오토일 때도 **「수동이면 −1.3턴」** 을 처치 턴 타일 보조줄에 회색으로 미리 보여 주면 토글을 눌러볼 이유가 생긴다(JSON 에 두 모드가 다 있으므로 비용 0).
- 수동 결과가 오토와 같거나 나쁘면 서순 표 위에 「오토와 차이 없음 — 그대로 오토 권장」 한 줄.
- 헬퍼 문구(툴팁/`title`): 「오토 = 게임 자동 전투 규칙(쿨 찬 궁 > 특수 > 기본, 노바 버스트 안 씀). 수동 = 아래 서순대로 직접 조작했을 때.」

### 2-5. 서순(스킬 순서) 표 디자인

**구조**: 세로 = 턴(위→아래, 1-14), 가로 = 구원자 4열(카드 `.rowcards` 와 **같은 열 순서·같은 grid-template-columns** 로 정렬해 카드 바로 아래 붙임).

```
턴 │ 프로페서M(BACK) │ 카르멘(FRONT) 👑 │ 에밀리(FRONT) │ 페이(BACK)
───┼────────────────┼─────────────────┼───────────────┼──────────
 1 │ [특수] 광역     │ [기본] →보스 ⚡협공 │ [특수] 보호막  │ [궁극] →보스
   │                │  ↳ 협공: 프로페서M │               │
───┼──── ✦ 노바 4 모임 → 페이 궁극기에 버스트 ──────────────────────  ← 행 전체 폭 띠
 2 │ [기본]         │ [특수]           │ [기본]         │ [궁극✦버스트]
 3 │ …
   └ 「4턴 이후 보기」 (details)
```

- **셀 = 배지 1개**: 색은 1-8 처럼 종류별 고정 — 기본기 회색 `#4a5568`, 특수기 파랑 `#3b6cb4`, 궁극기 보라 `#6a4fb0`(기존 `.e-moon` 계열과 구분되게 조금 붉은 보라), 노바 버스트 금색 테두리 `#ffd24a`. 배지 안: 아이콘 글자(기본 ●, 특수 ◆, 궁극 ★) + 2~3글자 라벨 + 짧은 스킬명(PC 만).
- **대상**: 셀 아래 작은 글씨 「→ 보스」「→ 아군 에밀리」. 광역이면 생략.
- **협공·추가 발동**: 1-7 의 oGCD 처럼 주 배지 아래 들여쓴 작은 줄 「↳ 협공 프로페서M」(회색). 셀 안에서만 처리해 행 높이가 조금 늘어도 그리드가 깨지지 않게.
- **노바 버스트 마커**: 해당 행 위에 `grid-column:1/-1` 전폭 띠(금색 점선 테두리) 「✦ 노바 4 → ○○ 궁극기에 버스트」. 버스트가 터지는 셀 배지에도 금색 테두리.
- **턴 머리(1열)**: 턴 번호 + (선택) 그 턴 끝 적 HP 추정 `보스 62%` 작은 글씨 — 「왜 이 순서인가」를 설명 없이 느끼게 함.
- **접힘 기본값**: 처음 3턴 + 노바 버스트 행까지 펼침(버스트가 4턴이면 4턴까지). 나머지는 `<details>` 「전체 서순 보기(총 7턴)」. 각 턴이 같은 패턴 반복이면 「4~7턴: 2턴 패턴 반복」 한 줄로 접는다(데이터가 패턴 반복을 표시해 주면).
- **개선 요약 줄**(표 위): 「수동 시 처치 턴 5.8 → 4.5(−1.3) · 클리어 91% → 95%」 + 「이 순서는 1판 샘플이 아니라 400판 평균이 가장 좋은 순서」 작은 글씨.
- **불확실한 순서**: 탐색에서 차이가 미미한 턴(예: 2턴 특수기 vs 기본기 차이 <0.1턴)은 배지 테두리를 점선으로 + `title="이 턴은 순서를 바꿔도 거의 같음"` — 1-7 「flexibility notes」의 축약.
- **PC**: 턴 열 1 + 4열 = `grid-template-columns:44px repeat(4,1fr)`. **모바일**: 같은 구조, 배지 라벨만 2글자, 대상 줄은 아이콘(→)만, 스킬명 숨김(`@media (max-width:760px) .seq .sk{display:none}`).

**JSON 형태(사전 계산, 파티당)** — 설계 §2 `result` 에 서순을 덧붙이는 최소형:
```json
{"auto":{"clear_p":0.91,"ci95":[0.87,0.94],"wipe_p":0.04,"timeout_p":0.05,
         "ttk_median":5,"ttk_p10_p90":[4,7],"n":400,"seed":7,"gate_ok":true,
         "first_death":{"key":"emily","p":0.35,"turn":3},
         "per_unit":{"profm":{"share":0.41,"death_p":0.02}, "...":{}},
         "depends_on":[{"rule":"enemy_atk_x1.85","label":"적 공격 ×1.85","flips":true}]},
 "manual":{"...":"같은 키","delta":{"ttk":-1.3,"clear_p":0.04},
           "seq":[{"t":1,"acts":[{"u":"profm","k":"S","tg":"boss"},{"u":"carmen","k":"B","tg":"boss","assist":"profm"},
                                  {"u":"emily","k":"S","tg":"ally:carmen"},{"u":"fei","k":"U","tg":"boss"}]},
                  {"t":2,"nova":{"u":"fei","k":"U"},"acts":["..."]}],
           "seq_repeat_from":4}}
```
`k`: B/S/U(기본/특수/궁극), `nova` 가 있는 턴에 전폭 띠. 10팀 × 2모드여도 수 KB — 기존 `/*DATA*/` 삽입 방식에 그대로 얹을 수 있다.

### 2-6. 색·접근성(기존 다크 테마와 맞추기)

- 토큰 재사용: `--good #5fd39a`, `--bad #ff8b7e`, `--acc #4cc2c2`, 경고 `#ffb454`(이미 `.powinfo .warn`), 리더 금색 `#ffd24a`, 파랑 `#5a7bd6`. 새 색은 **궁극기 보라 1개**만 추가.
- **색만으로 뜻을 주지 않는다**: 등급 = 색 + 아이콘 + 글자, 배지 = 색 + 아이콘 글자. 초록/빨강 혼동 대비 ✔/✖ 모양을 반드시 함께.
- 대비: 다크 카드 `#1d2330` 위 본문 `#e6e9ef`(≈12:1), 보조 `#9aa4b5`(≈6:1) — 통과. 바 안의 글자는 바 색과 겹치지 않게 **바 밖(오른쪽)** 에 둔다(1-2 는 안에 두지만 우리 폭이 좁다). 노란 경고 테두리 위 글자는 기본 `--fg` 유지.
- 글자 크기 최소 12px(현재 11px 인 `.csb`·`.tile .ts`·`.crown span` 은 P4 에서 12px 로). 큰 값 22~24px, 등급 칩 12px bold.
- 막대는 `role="meter" aria-valuenow aria-valuemin="0" aria-valuemax="100" aria-label="클리어 확률 91%"`. 서순 표는 `<table>` 로 짜면 스크린리더·복사가 쉬우나 subgrid 정렬이 어려움 → `div` grid + `role="table"/"row"/"cell"`.
- `prefers-reduced-motion` 에서 바 채우기 애니메이션 끔. 애니메이션은 어차피 넣지 않는 쪽을 권장(정적 JSON 렌더).
- 라이트 모드: 현재는 `prefers-color-scheme` 으로 라이트가 기본이고 카드만 하드코딩 다크다. P4 색을 다크 기준으로 맞추므로 **`<html data-theme="dark">` 로 다크 고정** + 라이트는 토큰만 남겨 두는 편이 검증 범위가 작다(요구사항도 다크).

### 2-7. 구현 메모

- 렌더 함수 위치: `card()` 호출 전 `forecast(party, res)` → `card(x,pos,alt,unitRes)` 에 per_unit 인자 추가 → `seqTable(res.manual.seq)` 를 `breakCard` 앞에. `run()` 은 지금 1,001 조합을 JS 로 재탐색하므로 **시뮬 결과는 조합 키(정렬한 4 key 문자열)로 조회**: `D.sim[contentKey|stage][combo]`. 보유 체크로 바뀐 파티가 상위 10팀 밖이면 「이 조합은 시뮬 안 됨 — 근사 점수만」 회색 칩(관문 없음 표시).
- 신규 CSS 는 60~80줄, JS 는 100줄 안팎. 라이브러리 불필요.
- 결과가 없는 콘텐츠(시뮬 미지원 적)는 `.forecast` 자체를 숨기고 「시뮬 미지원 스테이지」 한 줄.

---

## 3. 현재 페이지에서 눈에 띈 소수정(UX)

라이브 페이지(2026-10-20, 작전 SECTOR 1-1)와 `party_template.html` 을 같이 보고 적음.

1. **리더 왕관이 일러스트 머리 위를 가린다** (`.crown{top:8px;left:50%}`, 34×26 svg + 「LEADER」). 카르멘 카드에서 머리 장식과 겹침 확인. → 카드 **왼쪽 위 모서리 리본**(`top:6px;left:6px`, 반투명 배경 `rgba(8,10,16,.7)`, 둥근 모서리, 왕관 18px + 「리더」 11→12px)으로 옮기거나, `.slotlbl` 줄(BACK/FRONT)에 「👑 리더」 를 덧붙여 카드 밖으로 뺀다. 리더 효과(속도 +10)는 근거 보기에만 있으니 `title` 로도 달아 둘 것.
2. **모바일 2열에서 편성 순서 의미 소실** — §2-2 참고(4열 유지 권장).
3. **`.arch`(다른 전략) 그리드 `minmax(320px,1fr)`**: 폭 360px 폰에서 main 안쪽 폭(≈304px)보다 커 **가로 스크롤**이 생길 수 있음 → `minmax(min(320px,100%),1fr)`.
4. **`#cy` 구조도 높이 560px 고정 + 라벨 11px** (HANDOFF 4번): `height:min(560px,70vh)`, 노드 라벨 12~13px·배경 반투명 박스(`text-background-color`), 「전체 지도」는 기본 최소 강도 3 으로, 파티 모드에서는 노드가 4~8개뿐이니 **구조도 옆/아래에 텍스트 목록을 항상 병기**(이미 `synSummary` 가 있으므로 구조도 기본 접힘 `<details>` 로 두고 목록을 앞세우는 게 모바일에 낫다).
5. **iOS 입력 확대**: `select,input` 이 14px 이라 포커스 시 화면이 확대됨 → `@media (max-width:760px){select,input{font-size:16px}}`.
6. **「추천」 버튼이 사실상 불필요**(모든 변경이 `rerun()`). 남기려면 「다시 계산」 으로 이름을 바꾸고 보조 스타일로; 자리는 오토/수동 토글에 주는 편이 낫다.
7. **드로어 배경 `#dback{display:none!important}`** → 바깥 클릭으로 닫히지 않고, 열린 동안 본문이 스크롤·클릭됨. 모바일에선 반투명 배경(`rgba(0,0,0,.5)`) + `body{overflow:hidden}` 권장. 열기 버튼 `#dbtn`(세로 글자 3줄, 11px)은 모바일에서 작고 카드와 겹침 → 하단 고정 바(「내 구원자 42/60 ▸」) 또는 상단 패널 안 버튼으로.
8. **11px 글자 다수**(`.csb`, `.tile .ts`, `.crown span`, `.btag`, `.archf`): 다크 배경 작은 회색 글자는 12px 이상으로.
9. **`.why2`(「인게임 편성 순서(왼쪽부터)」)가 근거 보기 켤 때만 보임** — 카드 배치 의미는 항상 보여야 하므로 `.phead` 보조 문구로 분리.
10. **죽은 CSS**: `.slot .pic .sinfo .brk .bicon .bcard .bcard2 .lead .alts .chips` 는 JS 가 만들지 않는 클래스, `.cls` 는 44px 뒤 50px 로 두 번 정의. 정리하면 P4 추가분이 섞여도 읽기 쉬움.
11. **푸터 문구 「초상화는 온라인일 때만 보입니다」** 는 로컬 `assets/savior/` 로 바뀐 뒤 사실이 아님 → 삭제.
12. **라이트/다크**: 시스템 설정 따라 바뀌는데 카드·브레이크 바는 다크 고정 색이라 라이트에서 섬처럼 보임 → §2-6 대로 다크 고정(또는 토글).
13. **스테이지 정보 한 줄(`#stinfo`)** 이 길어 모바일에서 3~4줄 — 「적 3체 · 태양 4」 등 핵심만 남기고 나머지는 「상세 ▸」.
14. **티어 칩 색만으로 티어 구분**(`.t-0` 주황 … `.t-4` 회색) — 글자가 있어 치명적이진 않으나 「0.5티어」처럼 글자 크기 13px 유지.
15. **대체 후보 2명이 네 카드 모두에서 같은 인물(아모라·사를)** 로 반복 노출 — 데이터 문제라기보다 표시 문제: 같은 후보가 3칸 이상 반복되면 「대체 후보: 아모라·사를(공통)」 로 파티 단위로 한 번만 보여주고 카드 아래엔 칸별 고유 후보만.

---

## 부록 — 조사에서 연 URL

- https://github.com/genshinsim/gcsim · https://gcsim.app/ · https://gcsim.app/db(미준비) · https://gcsim.app/simulator · https://docs.gcsim.app/ (+ guides/understanding_results, reading_results, getting_started 는 404 또는 동일 소개문)
- https://www.prydwen.gg/star-rail/characters/acheron (Calculations·Build and teams 탭)
- https://www.prydwen.gg/arknights-endfield/tools/rotation-builder
- https://fribbels.github.io/hsr-optimizer/ (Home·Benchmarks·Optimizer) · https://github.com/fribbels/hsr-optimizer · https://github.com/fribbels/Fribbels-Epic-7-Optimizer
- https://calc.pokemonshowdown.com/ · https://github.com/pkmn/dmg
- https://www.thebalanceffxiv.com/jobs/casters/black-mage/openers/
- https://github.com/frzyc/genshin-optimizer (README 만, 팀 기능 설명 없음)
- https://qooreche.github.io/starsavior-party-navigator/ (현재 라이브)
- 검색만: west-games.com 속도 계산기, overwolf EndSync/Arknights Companion, Padilla·Kay·Hullman 2020, data.europa.eu 시각화 가이드, PMC9731905, arXiv 2207.09608, smogon 계산기 튜토리얼
- 열리지 않음: prydwen NIKKE 티어(403), schaledb.com(본문 없음), simpact.app(제목만)
