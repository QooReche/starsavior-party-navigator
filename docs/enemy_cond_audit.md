# 적 조건·미처리 효과 점검 (2026-10-23)

계기: 장비 탐색 혹한의 습격 XVII 를 실제로 3판 돌린 결과(전부 승리)와 시뮬(전멸 100%)이 크게 달랐다. 영상 판독으로 **보스 행동 비율**이 실제 24~28% 인데 시뮬은 44% 였고, 원인을 보스 패시브 조건 평가에서 찾았다.

## 방법
- `AI\temp\partynavigator\scripts\audit_all.py`(일회성): 작전·작전 하드·일일·장비 탐색·큐브·플래시·회랑·코스모 3,690 스테이지를 1판씩 돌리며 `Battle.cond_ok` 호출을 기록(조건 키 조합·횟수·표본 줄)하고 시뮬의 `unsupported` 보고를 집계. 평가 약 91만 건, 키 조합 73종, 오류 0.
- 조건 키 중 `COND_KEYS`(해석 목록)에 없는 것: 0개.

## 조용히 틀리던 것 (고침)
`cond_ok` 에서 「효과 개수/중첩수」 수정자는 직전 앵커 키가 정한 `last` 대상의 개수를 읽는다. 아래 앵커는 `last` 를 안 정해 개수가 0 으로 읽혔다.

| 조건 | 평가 수 | 예전 동작 | 해당 패시브(콘텐츠) |
|---|---|---|---|
| `적 강화효과 보유: 예; 효과 개수 미만: N` | 746 | 상대 전원 중 하나라도 강화 효과가 있으면 참(개수 무시) → 보스가 아군 아무에게나 맞아도 행동 게이지 +30%p·공격력 +6% | 웬디고 「끝 없는 냉기 분노」「혹한의 기운」(장비 탐색 혹한의 습격 등) |
| `시전자가 보유: X; 효과 개수: N` | 192 | 개수 0 → 한 번도 참 안 됨 | 「제행무상」 반격 연쇄 피해(회랑 410층 3종, 작전 하드 31-10) |
| `시전자가 보유: X; 효과 개수 이상: N` | 96 | 위와 같음 | 위와 같음(3중첩) |
| `적 약화효과 보유: 예; 효과 개수 이상: N` | 446 | 개수 0 → 한 번도 참 안 됨 | 「과업의 시간」 피해 감소 +20%(작전 `x-36` 계열, 작전 하드 2-10 등) |

수정(`battlesim/mc.py` `cond_ok`·`_count`): 때린 상대(`ctx.src`) 한 명 기준. 강화 효과 건은 규칙 `enemy_hit_buff_cmp` 로 판정 방식을 고른다: `le`(기본) = 때린 아군의 강화 효과 수 ≤ N(게임 설명문 「1개 이하」), `lt` = < N(데이터 줄 글자 그대로), `lt_disp`/`le_disp` = 해제 불가 강화는 세지 않음, `legacy` = 옛 방식.

### 실측 대조 (장비 탐색 혹한의 습격 XVII, 내 정보 능력치, 큐브 과부하 Lv5 장착, 200판)
실제 4판: 프레이 팀(에밀리·프레이·에데·그웬) 3/3 승리(TURN 66·69·68, 준÷받은 피해 0.81~0.87), 추천 팀(프로페서M·에데·에밀리·아모라) 1/1 패배(TURN 37, 적 77% 깎음, 준÷받은 피해 0.90).

| 판정 | 프레이 팀 클리어 | 추천 팀 클리어(적 체력 깎음) | 관측이 나올 가능성 |
|---|---|---|---|
| legacy | 0% | 0%(0.62) | 0 |
| lt | 98% | 99%(1.00) | 약 1% |
| **le(기본)** | 76% | 74%(0.97) | **약 11%** |
| lt_disp | 31% | 36%(0.92) | 약 2% |
| le_disp | 0% | 3%(0.76) | 0 |

어느 판정도 두 팀을 동시에 맞추지는 못한다(프레이 팀은 `lt`·`le` 가, 추천 팀은 `legacy`·`le_disp` 가 맞음). 시뮬의 아군 강화 효과 수에는 `해제불가` 표식·`현장 대기`·`별빛의 궤적-AX` 같은 내부 표지가 섞여 있어, 게임이 실제로 세는 방식과 다를 가능성이 크다(프로페서M 은 때릴 때 강화 0~1개 59%, 그웬은 2개 이상 100%). `le` 는 관측과 가장 덜 어긋나고 설명문과 같아 임시로 택했다. **4판뿐이라 새 실측이 쌓이면 다시 고를 것**(`tools/ingame_check.py` 샘플 `17`·`17e`·`17r`, `--ov '{"enemy_hit_buff_cmp":"lt"}'`).

한계: 시뮬의 전체 행동 수(TURN 환산)는 프레이 팀 80~93 으로 실제 66~69 보다 길다(준 피해가 모자람). 다른 스테이지의 개선은 측정하지 못했다.

## 알면서 못 하는 것 (미지원 보고, 안 고침)
`unsupported_*` 집계(스테이지 수 기준). 페이지에서는 「미지원 기믹 있음」으로 표시된다.
- (10/23 반영, 아래 절) 반격 확률(`반격 증가`·`경계 모드`·`강화 반격`).
- (10/23 일부 반영, 아래 절) 「적 자동 지정」 규칙 미확인: 작전 13-x 「영혼 구속」 930건, 17-x 「공허 방패」 229, 18-x 연쇄 피해 142, 출혈 129, 혹한의 습격 연쇄 피해 46 등. 게임 효과 줄 번호와 짝지은 167줄은 게임 규칙으로, 나머지는 옛 근사.
- 소환: 잊혀진 맹세(고대 병졸), 코스모 티리아(시계태엽 인형)·올베로스(하수인).
- 즉시 피해, 아군 사망 시 쿨타임 초기화(33), 트리거 스킬(`맹약 회수`·`앙코르` 등), 「이번 스킬 한정 vs 속성 피해 증가」.
- 결과를 얼마나 바꾸는지는 미측정. 다음 후보: 반격 확률(스테이지 수 최다), 자동 지정 규칙(영상으로 대상 확인 필요).

## 추가: 반격·턴 제한·보스 수치 (2026-10-23 오후)

반격(규칙 `mc.revenge`, 기본 on)
- 게임 코드(`NKM.decompiled.cs` 11990~12075 판정, 15227~15360 처리, 7765~7800 중복 제외, 7203~7215 타격 기록): 본 행동·협공·반응 스킬 뒤, 피해가 0보다 큰 타격을 받은 유닛마다 한 턴에 한 번 반격 확률(`NST_RATE_REVENGE_ATTACK`, 기본 0)로 공격자에게 기본기. 조건 = 공격 스킬, 피격자 생존, 브레이크 아님, 공격자 생존·적, 기본기 사용 가능(쿨·행동 불가). 반격에는 반격·협공이 없고, 공격자가 쓰러지면 그 공격의 남은 반격만 끝. 시전 하나의 후보는 추첨을 먼저 끝낸 뒤 반격함.
- 엔진 근사: 반응 스킬이 시전 안에 겹쳐 있어 행동 끝에 시전 순서대로 모아 처리. 회피해도 피해가 남으면 반격 대상(게임은 회피 여부가 아니라 피해량으로 기록).
- 반격 확률 효과는 적 스킬 6줄(공허몰살자·공허융합자·공허조율자·공허찬탈자·번뇌의 숙고자·복제체 나루·스패로우), 나오는 스테이지 304곳(회랑 199·작전 77·작전 하드 20·큐브 8). 구원자 쪽 반격 효과는 없음.
- 표본 팀 12곳 40판: 클리어 평균 −23%p(예: 태양 회랑 300층 75→5%, 작전 34-36 95→45%, 작전 하드 30-10 58→0%). 공허조율자는 생명력 50% 이하에서 3턴간 〈강화 반격〉(+100%)이라 한 판에 2~6번 반격함. 유효 실측 표본 7곳(37-2~5·17 계열)에는 반격 적이 없어 변화 없음.

턴 제한 단위(규칙 `mc.turn_limit_unit`, 기본 actions)
- 게임 전역 턴 = 유닛 턴 선택마다 +1(아군·적 모두, `NKM` 13796~13798), 전역 턴 > 제한이면 전투 종료(599~623·755~762). 턴 제한이 있는 콘텐츠는 코스모 게이트 33곳(비공개 `BATTLE_TEMPLET_RANKING_RAID` LimitTurn 50, CountEnemyTurnOnly false)뿐.
- 엔진은 그동안 50 을 모델 턴(100틱)으로 비교해 전체 행동 수로 약 9배 관대했음(코스모 클리어 판은 모델 1턴에 전체 약 9번 행동). 이제 전체 행동 50번에서 시간 초과. 빠른 계산(`quick.py`·`quick.js`)은 라운드마다 (아군 속도 합 + 살아 있는 적 속도 합)/100 번 행동으로 셈.
- 표본: 대부분 코스모 클리어는 9~21번 행동으로 끝나 영향이 없고, 「괴리의 표상 3단계」처럼 212번 걸리던 판은 이제 실패.

보스 수치 기준선
- 비공개 `analysis/baseline`(빌드 26105710) 보스 1,151곳의 생명력·공격력·방어력·속도(레벨 성장·스테이지 보정 포함)를 엔진 `FoeDef` 와 대조: 1,143곳 정확히 일치. 다른 7곳은 10/22 패치로 하향된 x-36 보스(26·27·28·30·35·36·37-36)이고 엔진(데이터북) 쪽이 패치 뒤 값. 큰 보스전 아군 피해 부족의 원인은 보스 수치가 아님.
- 서든데스(99~149 TURN 이후 아군 약화)는 유효 실측 표본의 TURN(13~69)보다 늦어 영향 없음 — (10/23 밤 구현, 아래 절).

## 추가: 적 스킬별 자동 규칙·효과 줄 자동 대상 (2026-10-23 저녁, 규칙 `mc.foe_auto`)

- 게임 코드(`NKM.decompiled.cs` 6390~6450 효과 줄 자동 대상, 6454~6620 스킬 규칙 행, 6786~7130 필터). 효과 줄 대상은 단일형(`NSETT_AUTO_ENEMY_ONE`)이면 필터 뒤 1명(1명이 되면 멈춤, 여럿이면 무작위 — 맞는 필터가 없어도 1명), 전체형(`NSETT_AUTO_ENEMY`)이면 맞는 필터가 하나라도 있을 때만 그 목록이고 아니면 대상 없음.
- `tools/build_foe_auto.py --static` → `data/foe_auto.json`(가공 어휘·한글 효과 이름만). 데이터북 적 ↔ 게임 유닛은 스테이지 배치로 연결하되, 조건에 맞는 배치가 하나뿐인 스테이지, 칸 역할·속성(배치의 속성 변경 포함)이 같은 칸만 씀. 한 적(유닛·변형)에 게임 유닛이 여럿이면 가공 규칙이 모두 같을 때만. 효과 줄은 게임 SE 행과 줄 수가 같고 모든 줄의 대상 종류(자신·적 전체·스킬 대상·자동 지정 …)가 맞을 때만 짝지음. 장비 탐색(혹한의 습격 등)은 `NORMAL_BATTLE_EXPLORE_EQUIP<탭>_<단계>` 로 연결(10/23 밤 `build_foe_spawn.candidates()` 로 옮겨 `foe_spawn.json` 에도 60곳 연결 — 값은 등급 규칙과 같아 시뮬 변화 없음).
- 결과: 적 414종, 스킬 규칙 398개(망각의 예언자 행동 게이지 최고 243, 공허목도자류 〈낙인〉 보유 적 → 80% 전열 → 80% 디펜더 104, 조율자 전열 100%·디펜더 80% 21 …), 효과 줄 167개(웬디고 궁극기 연쇄 피해 = 강화 효과 2개 이상 / 1개 이하인 적 전원, 침묵의 은둔자 등 「스킬 대상 따라감」, 공허목도자 특수기 〈낙인〉 = 후열 100%, 복제체 다나 = 마지막으로 나를 친 적 …). 짝짓기 실패 10스킬·연결 없음 105스테이지는 옛 근사.
- 「마지막으로 나를 친 상대」는 스킬 타격 때 피해 계산 전에 기록(피해 무효여도, 지속·연쇄 피해는 제외 — NKM 15563~15579).
- 실측 대조(60판): 혹한의 습격 17 준÷받은 0.98→0.93(실측 0.87), 17e 0.96→0.90(0.81), 17r 1.83→1.67(0.90)·클리어 98→88%(실제 패배). 37-x 는 변화 없음. 실측에 맞춘 것이 아니라 게임 규칙을 넣은 결과임.

## 추가: 서든데스 (2026-10-23 밤, 규칙 `mc.sudden_death`)

- 게임: `BATTLE_TEMPLET.SuddenDeathId` → `SUDDEN_DEATH_TEMPLET`(PVE·상시) → 그룹 단계 행(`EndLevelTurn` = 그 단계가 끝나는 전역 턴, 마지막 단계는 끝까지) → `BATTLE_EFFECT_TEMPLET`(아군 전체, 최대 생명력%·방어력%·주는 회복량%·주는 보호막량%). 컨트롤러는 전역 턴이 바뀔 때마다 처리(`NKM` 16989~17013, 본체는 해독본에 없음).
- 범위는 비공개 요약(`analysis/baseline`, 작전 일반 301~304)보다 넓음: 작전 일반 1,267곳(301~304)·작전 어려움 350곳(350~352)·회랑 1,900곳(401~404). 시작 턴 99~219, 마지막 단계 −50~−90%(방어력 −30~−50%). 권장 전투력·레벨이 같은 후보 전투끼리 그룹이 다른 1곳(작전 11-29)은 뺌.
- `tools/build_sudden_death.py --static` → `data/sudden_death.json`(단계표·스테이지 키만). 엔진: 전역 턴 +1 직후·그 행동 전에 단계 계산(끝 턴 포함 — 추정), 아군 전원(쓰러진 아군 포함)에 전투 효과 층(`Unit.sd`, 버프 아님 → 정화·효과 개수에 안 잡힘).
- 최대 생명력 = floor(전투 전 최종 최대 생명력 × (1 + 생명력%)), −99% 하한. 피해 공식의 생명력 비례 항도 같은 식(전투 전 값 × (1 + 생명력%)). 게임 합산(`NKM` 18272~18358)에서 전투 효과·버프는 전투 전 최종값에 곱하는 세 번째 묶음이라 최종 능력치 입력(내 정보)과 기본+패시브 입력이 같은 값이 됨(codex 리뷰 반영). 줄면 현재 생명력을 자르기만 하고 피해로 치지 않음(2828~2839). 방어력%·주는 회복량%는 버프와 같은 합산, 보호막은 생성량 × (1 + 주는 보호막량%) 후 내림, 지속 회복에는 시전자의 서든데스 회복 감소만 적용(근사).
- 남은 한계: 버프·약화의 생명력%(예: 〈영혼 구속〉 −15%)는 서든데스 전부터 최대 생명력에 반영 안 됨(피해 공식의 생명력 비례 항에만 씀).
- 영향: 유효 실측 7판은 모두 전역 턴 100 전에 끝나 변화 없음. 계수 표본 중 서든데스 스테이지 1,368건(40판)을 켜고/끄고 같은 코드로 대조하면 바뀐 표본 3건(각 −2.5%p) — 시뮬 전투는 대부분 그 전에 클리어·전멸. 빠른 계산 계수는 그대로(판정 일치 91.8%).

## 추가: 연결 확대·반응 스킬 순서·버프 최대 생명력·효과 줄 자동 대상 (2026-10-24)

연결 확대(`tools/build_foe_spawn.py`)
- 코스모 게이트(`RANKING_RAID`)·플래시 포인트(`BOSS_RUSH`)는 권장 전투력이 같은 전투가 콘텐츠마다 여럿이라, 칸마다 게임 유닛 한국어 이름(`m_UnitNameString` → STRING_COMMON)이 데이터북 적 이름과 같은 것만 연결(코스모는 데이터북 레벨이 없어 레벨은 안 봄). 일일 재화 던전도 탭이 골드·크리스탈·재료 중 무엇인지 몰라 이름 확인. `build_foe_auto` 도 같은 판정(`same_battle`).
- 결과: 코스모 33/33·플래시 40/44(게임 표에 없는 보스 1종 4단계)·일일 27 연결. 적 자동 규칙이 붙은 적 414 → 473종, 연결 없는 스테이지 105 → 5(작전 11-29 후보끼리 배치 다름 포함). 시작 쿨이 실제로 달라진 곳은 코스모 올베로스 3곳(졸개 쿨 가득).

반응 스킬 시점(규칙 `mc.reaction_timing`, 기본 queue)
- 게임(`NKM` 15180~15372): 본 행동 → 협공 → 본 행동 타격의 반격 → 협공 타격의 반격 → 예약된 반응 스킬을 하나씩(각각 직후 그 타격의 반격), 실행까지 간 예약 11개에서 멈춤, 반응 불발이면 그 유닛 예약 이력 초기화.
- 엔진은 그동안 반응 스킬을 맞는 순간 그 시전 안에서 바로(협공보다 먼저) 실행했음. 이제 행동 안에서는 예약(발동 조건은 그때 판정, 생존·행동 불가·쿨은 실행 직전), 반격은 행동 전체에서 유닛당 1번. 추가 발동·강제 협공·연쇄 피해는 여전히 시전 안에서 바로(게임 분류 미대조). 옛 동작 = nested.

버프 생명력%의 최대 생명력 반영(규칙 `mc.buff_maxhp`, 기본 on)
- 게임 합산(`NKM` 18272~18358)에서 버프·전투 효과는 전투 전 최종값에 곱하는 세 번째 묶음, 버프 제거 때 최종 능력치와 HP 를 다시 계산(2700~2715). 최대 생명력이 줄면 현재 생명력을 자르고, 늘어도 전투 상태가 Init·Start 일 때만 채움(2828~2839).
- 엔진: 최대 생명력 = floor(전투 전 최종값 × (1 + 버프 생명력% + 서든데스 생명력%)), −99% 하한. 효과가 바뀌어 다시 셀 때 현재 생명력을 자름, 전투 시작 줄의 효과만 채움, 피해 공식의 생명력 비례 항도 이 값. 예) 〈영혼 구속〉 −15% 가 이제 최대 생명력을 줄임. 옛 동작 = off.

효과 줄 자동 대상 확대
- 적: 아군 대상 자동 지정 줄(`NSETT_AUTO_ALLY`·`_ONE`)도 기록, 소환 줄(SE 대상 비어 있음)·「{N회 부여}」(SE 행 N개) 짝짓기 → 효과 줄 짝짓기 실패 15 → 0, 효과 줄 190 → 218(아군 대상 14).
- 구원자(규칙 `mc.ally_auto_lines`, 기본 data): `tools/build_auto_skill.py` 가 SE `COND_<스킬>_<묶음>_<줄>`(묶음 01 = 기본 효과, 그 뒤 = 레벨업 추가 행)에서 자동 지정 행을 찾아 데이터북 「(자동 지정)」 줄과 순서대로 짝지음(개수·아군/적·1명/전체가 맞을 때만) → `auto_skill.json` lines 15줄(구원자 13명: 세르팡·다나·왈츠 아세라·프레이·린·엘리사·리디아 …). 「자신 제외 1명」(NOT_SELF)은 게임 자동 대상 함수(6407~6450)가 다루지 않아 제외, `IsHighDef`(티리아)는 해독본에 없어 제외, 레벨업 추가 행에 자동 지정이 있는 힐데·웨딩 에핀델 궁극기와 줄 수가 안 맞는 3스킬도 제외(설명문 근사 유지).
- 체크용·판별용 표지를 찾는 필터인데 그 표지를 가진 유닛이 없으면(표지를 거는 줄이 근사로 처리될 때) 데이터 규칙 대신 설명문 근사로 되돌림 — 무작위로 새지 않게.
- 필터 `IsPositiveBuffUnit`(강화 효과 보유, `NKM` 6938) 추가.

적 전용 효과·브레이크 스킬(같은 날)
- 〈특수기 쿨타임 초기화〉(「어둠의 맹세」 — 맹목의 전파자·잔상의 감시자, 작전 4·회랑 33곳): 게임은 아군(자기 제외) 사망 시 특수기 쿨을 감소값 0 = 초기화(`NKM` 2874~2886, SE 100000301·조건 9800). 엔진이 이름을 몰라 이름뿐인 강화 효과로 붙이던 것을 쿨 초기화로.
- 〈즉시 피해〉(크로넷 「시계태엽 폭탄」 뒤·올베로스의 하수인 〈약화〉 보유 공격 뒤, 일일 거점 조사 4·코스모 올베로스 3곳): 게임 = 공격력 100% + 생명력 1000% 자기 피해(`NKM` 4794~4822·7311~7342, DAMAGE_TEMPLET) = 사실상 자폭. 엔진은 이름뿐인 강화 효과로 남아 크로넷이 폭탄을 판마다 4~5번 반복했음. 규칙 `mc.instant_damage`(self_kill, 옛 off). 수호 분담으로 넘어가는 몫은 근사에서 뺌.
- 브레이크 스킬 레벨(규칙 `mc.break_skill_level`, `tools/build_break_levels.py` → `data/break_skill_levels.json`): 레벨 L 이하 행의 피해·회복 가산을 계수에 더함(곱 아님). 특이점 관측 Lv10 70%→80%, 스타피어서·차원 강습 50%→60%, 큐브 과부하 회복 2%→4%.
- 브레이크 스킬 피해 x DamageScale(규칙 `mc.break_skill_scale`=game): 오비탈 시전자도 일반 피해식 끝에서 x 1.85(`NKM` 17742~17817, 브레이크 시전 15373~ = OBF_26964). 옛 가정(1.85 제외)은 근거 없던 assumed. 브레이크 피해가 1.85배로 늘어남 — 큰 보스전 아군 피해 부족의 일부일 수 있음(측정은 계수 재맞춤 결과로).
- 남은 미지원: 없음 — 적 트리거 스킬·소환은 아래 두 절(같은 날 구현).

## 추가: 적 트리거(반응) 스킬 5종 (2026-10-24, 규칙 `mc.foe_react`)

- 게임 코드(`NKM.decompiled.cs` 8097~8160 ReactSkillBooking): 적이 공격 뒤(`AfterMyAttack`) 또는 유효 타격 시(`MyEffectiveHit`) 조건을 판정해 반응 스킬을 예약. 시전자 사망·쿨·행동 불가면 실행 직전에 취소.
- `tools/build_foe_react.py --static` → `data/foe_react.json`(가공 어휘·한글 효과 이름만). 데이터북 적 ↔ 게임 유닛 연결은 `build_foe_auto.py` 와 같은 방식(스테이지 배치, 역할·속성 일치). SKILL_TEMPLET(`NST_REACT`) + `ReactConditionID` → SKILL_CONDITION_TEMPLET(tables/Plain).
- 결과: 적 16종, 규칙 16개.
  - **맹약 회수**(공허맹약자, 궁극기): `AfterMyAttack` + 맹약결속 ==3 + 대상 피의 맹약 보유 + 대상 미처치 → 그 대상에게. 작전 어려움 35-10·회랑 FLOOR 450×3·성간 550.
  - **앙코르**(공허변주자, 특수기): `AfterMyAttack` + 기본기 + 악상 ≥2 → 적 전체, cd 1. 회랑 FLOOR 420×3·성간 520.
  - **소거**(괴리의 표상, 특수기): `AfterMyAttack` + 잔재된 괴리 보유 + 체크용 버프 미보유 → 그 대상에게. 코스모 1~3단계.
  - **태엽 폭탄 기폭**(레디메이드 해피 68호, 특수기): `AfterMyAttack` + 기본기 → 적 전체, cd 4. 플래시 Ⅰ~Ⅳ.
  - **월영**(복제체 페이, 특수기): `MyEffectiveHit` + 풍호 보유 + 단일 대상 스킬 → 그 대상에게. 큐브 레지스터.
- 엔진: `FoeDef.react`(foe_react.json)에 칸별 발동 조건. 적 행동의 `cast()` 뒤 `_check_foe_react()`가 조건을 판정하고, 반응 대기열(`_react`)로 예약(기존 `mc.reaction_timing=queue` 경로와 같은 실행 순서). 조건 판정은 예약 시점, 사망·쿨·행동 불가는 `trigger_cast`가 실행 직전에 확인. `foe_react=off`(옛 동작)이면 미반영 표시만.
- 영향(40판, emily·frey·haydee·gwen 파티, seed 7): 작전 어려움 35-10 클리어 0%←82%(−82%p), 달 회랑 450 95%←100%(−5%p), 별 회랑 420 0%←2%(−2%p), 괴리의 표상 1단계 98%←100%(−3%p), 괴리의 표상 3단계 진척도 0.04←0.08. 맹약 회수가 있는 스테이지의 영향이 큼(보스가 추가 공격을 함). 폭탄 기폭·월영은 시험 파티가 해당 스테이지를 못 깨서 변화 0.

## 추가: 적 소환 (2026-10-24, 규칙 `mc.summon`)

- 게임 코드(`NKM.decompiled.cs` 5174~5212 소환 실행, 1156~1171 빈 칸만 배치, 1714~1748 소환 유닛 생성, 1793~1812 시작 쿨): SE SummonGroupId → `SUMMON_TEMPLET`(43그룹), SummonData 마다 SpawnPosIndex 칸에 유닛 생성. 칸이 범위 밖이거나 차 있으면 건너뜀. 사망 시 칸 비움. 시작 쿨 = 배치와 같은 로직(AllSkillAvailable/SpecialSkillAvailable/HyperSkillAvailable).
- 대상 3종 26곳: 올베로스 「대군세」(패시브, 하수인 ×4, 코스모 3곳), 티리아 「티리아의 장난감」(패시브, 시계태엽 인형 ×2, 코스모 3곳), 페르세스 「소집」(특수기 cd 4, 고대 병졸 ×2, 잊혀진 맹세 20곳).
- `tools/build_foe_summon.py --static` → `data/foe_summon.json`(가공값만: 그룹별 칸·쿨 플래그·속성, 스테이지별 웨이브 칸 번호). BattleScript 의 SpawnPosIndex 로 게임 칸을 연결(26/26곳).
- 엔진(`battlesim/mc.py`): `Unit.slot`(게임 팀 칸 0~4), `Battle._foe_slots = [None]*5`(소환 스테이지만), `spawn_wave` 에서 칸 배정, `kill` 에서 칸 비움, `_do_summon` 에서 빈 칸만 채움. 파서(`parser.py`)에서 `자신에게 소환: X ×N` 을 `kind='summon'` 으로 읽어 `_exec_line` 이 처리.
- 올베로스: 초기 배치에 하수인 4기가 이미 있음(칸 0·1·3·4, 올베로스 칸 2). 패시브가 스킬 사용 후 소환을 시도하지만 칸이 차 있으면 안 됨. 하수인 사망 시 칸 비움 → 다음 스킬에서 그 칸만 리필. 각 칸의 속성 변경(질서·태양·별·혼돈)은 SUMMON_TEMPLET ChangeAdjustType 으로 결정.
- 티리아: 초기 배치에 티리아(칸 2)만. 패시브가 첫 스킬 사용 후 인형 2기(칸 1·3) 소환. 인형 사망 시 다음 스킬에서 리필.
- 페르세스: 초기 배치에 페르세스(칸 2)만. 특수기 「소집」(cd 4) 사용 후 병졸 2기(칸 0·4, SpecialSkillAvailable) 소환.
- 진행(`progress`): 소환 유닛은 분모에 넣지 않음(반복 소환으로 진척이 줄어들지 않게). 웨이브 종료에는 소환 유닛 처치 필요(assumed — 게임 슬롯 기반 판정에서 빈 칸이 아니면 생존).
- 미확인(assumed): 소환 유닛 시작 행동 게이지 = 0, 웨이브 클리어에 소환 유닛 처치 필요.
- 영향(40판 표본, 내 정보 없는 프리셋 4명): 올베로스 1~3단계 변화 없음(하수인이 이미 배치에 있어 리필만). 티리아 1단계 82→100%(off), 2단계 0→5%·진행 0.53→0.66(off), 3단계 진행 0.022→0.034(off). 잊혀진 맹세 Ⅰ~Ⅱ 변화 없음(쉬운 스테이지). 소환은 적을 늘려 전투를 어렵게 함.
- 시험: `tests/summon_test.py`(13건). `off` 스위치 = 옛 동작(unsupported 집계만).

## 추가: 적 반응 스킬 시점·조건 어휘 확장 (2026-10-24, 규칙 `mc.foe_react_timing`)

- 게임 SKILL_CONDITION_TEMPLET 의 시점 중 `build_foe_react.py` 가 모르던 3종(AfterAllyAttack·OnMyAttack·AllyEffectiveHit)과 조건 DamageResultType·IncludeSelf·TargetNegativeBuff/TargetPositiveBuff·SelfPositiveBuff/SelfNegativeBuff·EliminateEnemy, 대상 NSTT_REACT_ALLY_TARGET, 스킬 인덱스 special/hyper 를 추가했음.
- 해독 코드 근거: OnMyAttack(`NKM.decompiled.cs` 10029~10088) = 자기 공격 시작 시(스트라이크 전) 판정. reactor == caster, SAT_ATTACK 필수. AfterAllyAttack(`NKM` 11253~11289) = 같은 편 유닛이 공격한 뒤 판정. IncludeSelf=false 면 자기 행동 제외, 같은 팀·SAT_ATTACK 필수. DamageResultType(`NKM.Templets` 38421) = per-strike 피격 결과(NormalHit/CriticalHit/Evade). 엔진은 per-target 근사(다단 히트 개별 결과를 유지하지 않으므로).
- 현황: NST_REACT 스킬 중 해당 시점을 쓰는 적(MON_) 게임 유닛은 WHITEDRAGON_WINDFAN(AfterAllyAttack 궁극기, 코스모·플래시·성간 보스), WHITEDRAGON_METEORWHIP(AfterAllyAttack 기본기/특수기, 같은 곳), HAPPY68_MAINSTORY(OnMyAttack 기본기+대상 약화, 작전 스토리), INDEPENDENT_VAGABOND_EVENT(MyEffectiveHit+DamageResultType=Evade, 이벤트). 그러나 이들은 현재 데이터북 적과 연결되지 않아 `foe_react.json` 에는 새 규칙 0건. 연결이 생기면 자동 반영됨.
- 구원자 쪽에도 같은 시점을 쓰는 NST_REACT 스킬이 있음: S_INCOGNITA_LANDGRAVE(AfterAllyAttack), S_DETECTIVE_PROFESSOR(AfterAllyAttack), S_SUMMER_SMILE(AfterAllyAttack), S_SUMMER_ORACLE(AllyEffectiveHit+DamageResultType=CriticalHit), S_WEDDING_SHIELDER(AllyEffectiveHit, NSTT_REACT_ALLY_TARGET). 구원자 반응 스킬은 `supported_trigger` 경로(텍스트 기반)로 처리되며 이번 변경 범위 밖.
- 엔진: `_check_foe_react(u, ctx, timing_filter, caster)` — timing_filter 로 호출 시점(None=기존 after_attack/hit, 'on_my_attack'=스트라이크 전, 'ally'=같은 편 순회)을 구분. on_my_attack 은 `cast()` 안 `deal()` 직전에 호출(대상 체력·버프가 피해 전 상태). after_ally_attack/ally_hit 은 `act()` 뒤 같은 편 생존 유닛 전체를 순회.
- 레거시 스위치 `mc.foe_react_timing`: extended(기본, 새 시점 포함) / legacy(after_attack+hit 만). `foe_react=off` 이면 시점 무관 전부 꺼짐.
- 미확인: on_my_attack 이 게임에서 정확히 어느 시점에 react 를 예약하는지(스트라이크 전으로 추정 — TargetHpRate 조건이 피해 전이어야 의미가 있으므로). DamageResultType 이 per-strike 인지 per-target 인지(per-target 근사). IncludeSelf=true 인 적은 0종(false 만 사용).
- 영향: 현재 데이터북 적에 해당 시점의 반응 규칙이 없어 시뮬 결과 변화 0. `build_foe_react.py` 실행 결과 16 units 16 rules(변화 없음, 어휘 건너뛰기 0건). `support_report` 적 트리거 스킬 미반영 0건(변화 없음).
- 시험: `tests/foe_react_test.py` 30건(on_my_attack 발동/미발동/off/legacy 5건, after_ally_attack 발동/미발동/wrong_skill/legacy 4건, damage_result 2건(placeholder), 기존 19건). 고의 파괴로 실패 확인 후 원복.

## 추가: 대상 선택 미지원·근사 해소 (2026-10-24, 규칙 `mc.enforce`)

적 피격 반응 패시브 자동 대상 (104곳 해소)
- 원인: `build_foe_auto.py` 의 `se_of` 가 게임 SE 이름의 두 가지 변형을 찾지 못했음. (1) `NKM_UNIT_MON_` 접두사 전체를 쓰는 SE(공허선도자·공허절멸자 등): COND_NKM_UNIT_MON_BELLWETHER_MANE_BOSS_PASSIVE2_01 → se_of 가 `NKM_UNIT_MON_` 을 벗기지 않아 못 찾음. (2) 게임 유닛 변형 접미사(_01 등)가 스킬 이름에 있지만 SE 이름에는 없음(해피 68호 _RUSH_01_PASSIVE2 → SE _RUSH_PASSIVE2).
- 수정: `se_of` 에 전체 sid 대조와 변형 접미사 제거 폴백을 추가. 적 473→601종, 효과 줄 218→359개.
- 게임 규칙 확인: 공허선도자(BELLWETHER_MANE) PASSIVE2 AutoTargetId=17(NSETT_AUTO_ENEMY) = `last_damager`, 공허절멸자(FALLEN_SHIELD) PASSIVE1 AutoTargetId=17(NSETT_AUTO_ENEMY_ONE) = `last_damager`, 해피 68호(HAPPY68) PASSIVE2 AutoTargetId=17 = `last_damager`. 모두 마지막으로 나를 친 적.
- 근거: SE_TEMPLET_SKILL COND_NKM_UNIT_MON_BELLWETHER_MANE_BOSS_PASSIVE2_01, COND_NKM_UNIT_MON_FALLEN_SHIELD_BOSS_PASSIVE1_01, COND_MON_HAPPY68_PEACE_BLACK_BOSS_RUSH_PASSIVE2_02. AUTO_SKILL_TARGET_TEMPLET 17 = `{IsLastDamageTarget: true}`.

올베로스 코스모 BI_ENFORCE 강제 추가 행동 (3곳 해소, 규칙 `mc.enforce`=data)
- 게임 SE: COND_MON_OLBERS_JOUST_BLACK_BOSS_COSMO_01_PASSIVE2_02 = BI_ENFORCE, AutoTargetId=1026(초즌 보유 아군), EnforceAutoTargetId=4(무작위 적), EnforceSkillIndex=NSI_SKILL_1_ATTACK(기본기).
- PASSIVE2_05 = AutoTargetId=5(not_self), 초즌 부여 → 턴 종료 시 자신 제외 아군 1명에게 부여.
- 엔진: `_run_special_rest` 에서 RX_ENFORCE 패턴으로 「아군 1명(자동 지정)에게 기본기 추가 발동」을 잡고, line_spec 의 enforce 규칙(actor 필터 → enemy 필터 → cast)으로 처리. 시전자 사망·행동 불가면 취소.
- 근거: NKM.decompiled.cs 4555~4572(BI_ENFORCE SE → 예약), 7955~7992(EnforceSkillBooking: 시전자 사망·스킬 불가→취소).

구원자 효과 줄 근사 해소
- NOT_SELF(NSETT_AUTO_ALLY_ONE_NOT_SELF): `build_auto_skill.py` 에서 제외 조건 제거. 웨딩 카르멘 고유 패시브(not_self + high_atk), 웨딩 에핀델 특수기(high_atk) 추가. 15→18줄.
- IsHighDef: 26105710 빌드 해독본에 함수 존재 확인(NKM ആഌഈആ...cs case IsHighDef → 방어력 최고). `build_foe_auto.py`·`build_auto_skill.py`·`mc.py _filter` 에 high_def/low_def 추가. 티리아 궁극기의 체크용 버프 줄이 이제 high_def 필터로 올바르게 연결됨.
- 남은 근사: 레벨업 추가 행(힐데·웨딩 에핀델 궁극기) — 기본 묶음(01)만 처리, 레벨별 SE 집합 계산은 다음 작업. 줄 수 불일치 3스킬(ceres 고유 패시브·harley 특수기·sunshine-cat-smile 고유 패시브) — 데이터북과 SE 행 수가 달라 짝짓기 실패, 원인 미확인. professor-m 고유 패시브의 IsNotUnableToAct 필터도 미지원(해독 코드 확인 필요).
- 시험: `tests/sel_targeting_test.py`(10건). 옛 동작 = `enforce=off`, `foe_auto=off`, `ally_auto_lines=off`.

## 추가: 효과 미지원 잔여 해소 (2026-10-24, 규칙 4개)

전수 스캔(3,690 스테이지 support_report)에서 `effect:`·`trigger:` 보고를 전부 없앰. 남은 것은 `selector:` 18건(자동 지정 대상 규칙, 올베로스 초즌 등 — 효과가 아니라 대상 선택 문제).

### 항목별

1. **오르트로스 코스모 1~3단계** (3곳)
   - 「효과 지속 턴 +1」: 파서가 `효과 지속 턴` 을 해제/교체/무작위로 잡던 것을 `kind='extend'` 로 파싱(parser.py:163~166). 엔진 `_exec_line` 의 기존 extend 핸들러(mc.py:2678)가 처리. 규칙 `mc.effect_dur_extend`(on, 옛 off).
   - 「타 대상 능력치 보정」: `적 전체에게 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}` — 파서가 `{이번 스킬에만 적용}` 플래그가 있을 때만 `kind='local'`(target 필드 포함), 없으면 종전 ignored(parser.py:109~116). 엔진은 ctx.src 가 owner 이면 자신과 같은 local 경로를 탐.
   - 근거: 데이터북 오르트로스 패시브 ef(parser:163), mc.py:2678(extend 핸들러)

2. **티리아 코스모 3단계** (1곳, 런타임)
   - 「행동 게이지가 0%보다 높으면 0%로 낮춤 {효과 적중 판정}」: 시계태엽 인형(소환) 스킬. 파서에 `kind='gauge_set_if'` 추가(parser.py:167~171). 엔진에 게이지 조건부 설정 핸들러 추가(mc.py, gauge_set_if). 규칙 `mc.gauge_conditional`(on, 옛 off).
   - 근거: 데이터북 시계태엽 인형 ef

3. **올베로스 코스모 1~3단계** (3곳)
   - 「trigger: 등장 후」: 하수인 `[등장 후] 자신에게 능력치 보정 속도% -1000% {해제 불가}`. 파서 `trig_kind` 에 `'등장 후'` → `'battle_start'` 추가(parser.py:184). 소환 시 battle_start 줄이 실행됨. `{해제 불가}` 능력치 보정은 영구 버프로 변환(parser.py:104~107 — 해제 불가이고 이번 스킬 아니면 buff).
   - 「영웅의 혼(해제불가)」 의미 미해석: 하수인이 올베로스에게 부여하는 표지. 올베로스 패시브가 `[자신이 보유: 영웅의 혼(해제불가); 중첩수: 4]` 로 조건 확인해 〈혼의 균열〉을 건다. 마커 수집을 전투의 모든 유닛에서 교차 수집하도록 변경(mc.py:support_report — per-def → all-def 마커 합집합). 하수인이 주고 올베로스가 확인하는 교차 참조도 잡힘.
   - 근거: 데이터북 올베로스의 하수인 ef, NKM.decompiled.cs 5174~5212(소환), parser.py:184(등장 후)

4. **잊혀진 맹세 장비 탐색 20곳**
   - 「이번 스킬 한정 보정 미지원 vs 달 속성 피해 증가」: `LOCAL_OK` 에 없던 stat. `_meaning_gap` 에서 `_m_vs` 정규식으로 인식(mc.py:3251~3253), `_exec_line` local 분기에서 대상 속성이 맞을 때 `ctx.local_by[target]['inc']` 에 반영(mc.py:2757~2762). 규칙 `mc.local_vs_element`(on, 옛 off).
   - 근거: 데이터북 페르세스 패시브 ef, parser.py `_map_prop` 360~361(vs 속성 → inc_vs)

5. **작전 어려움 35-10 맹약결속(해제불가)** (5곳)
   - 「의미 미해석 효과(속성 없음)」: foe_react 조건에서 맹약결속 중첩수를 확인하는데 마커 수집이 foe_react 조건을 포함하지 않았음. 마커 수집에 `d.react` 조건을 리스트 형식으로 스캔 추가(`self_stack_eq`·`self_has`·`target_has` 등에서 버프 이름 추출, mc.py:support_report 3335~3344).
   - 근거: data/foe_react.json(맹약 회수 조건: `["self_stack_eq", "맹약결속(해제불가)", 3]`)

6. **큐브 펌웨어 4곳**
   - 「effect: 미해석」: `자신에게 75% 확률로 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}` — 파서 self-target 정규식에 `(?:(\d+)% 확률로 )?` 추가(parser.py:100). 확률은 기대값으로 곱함(val × chance). `kind='local'` 유지.
   - 근거: 데이터북 복제체 리디아 ef

7. **선제 방어 확률(세레스 〈고립〉·힐데 고유 패시브)**
   - 「속성 미지원 선제 방어 확률 〈고립〉」: `_map_prop` 에 `선제 방어 확률` → `('preempt', None)` 추가(parser.py:388). `_prop_known` 이 인식. `_perm_apply` 에도 추가(parser.py:295~296). 힐데 고유 패시브가 다중 상시 능력치(「생명력% +15%, 선제 방어 확률 +30%」)라 파서 perm 파싱을 쉼표 분리로 변경(parser.py:219~231, `perm_multi` 타입).
   - 선제 방어 메카닉: 규칙 `mc.preemptive_defense`(on, 옛 off). 적 단일 공격 전 아군 중 선제 방어 확률이 있으면 `max(0, 방어자 확률 - 공격자 reduce)` 확률로 대상 전환(mc.py `_preemptive_check`). 필중이면 무시, 브레이크 상태이면 방어 불가. 공격자의 reduce 는 고립 등 약화 효과의 선제 방어 확률 감소분(`-attacker.mods()['preempt']`). 힐데 +30% 기준, 고립(-50%) 적에게는 방어 불가(30-50=0).
   - 근거: NKM.decompiled.cs PreemptiveDefenseController.cs:6~65(rate - reduce, roll 1~10000), NKM.Templets NST_RATE_PREEMPTIVE_DEFEND(라인 357)·_REDUCE(라인 358)

### 규칙 스위치
| 규칙 | 기본값 | 옛 동작 | 근거 |
|---|---|---|---|
| `mc.effect_dur_extend` | on | off | 오르트로스 효과 지속 턴 +1 |
| `mc.gauge_conditional` | on | off | 티리아 시계태엽 인형 게이지 조건 설정 |
| `mc.local_vs_element` | on | off | 잊혀진 맹세 페르세스 vs 달 속성 |
| `mc.preemptive_defense` | on | off | 힐데·고립·침묵의 방패 선제 방어 |

### 전수 스캔 결과
스캔 3,690 스테이지 support_report: `effect:` 0·`trigger:` 0·`selector:` 18(자동 지정 대상 규칙). 런타임(api.simulate n_runs 2, 표본 5곳): 오르트로스·티리아·35-10·잊혀진 맹세·펌웨어 모두 클린.

### 시험
`tests/eff_remaining_test.py`(16건): 파서 12 + 마커 2 + 엔진 2. 깨뜨리기(intentional break) 확인 후 원복함.

## 재현
`python -X utf8 -I AI\temp\partynavigator\scripts\audit_all.py <src> <내정보.json> out.json` → `audit_report.py <src> out.json`. 스크립트는 일회성(temp)이라 저장소에는 없음. 회귀 시험은 `tests/enemy_cond_test.py`.

## 추가: 강화 효과 개수·피격 중첩 판정 순서 (2026-10-23)

- 강화 효과 개수의 코드 연결을 확인했음. 해독본 루트는 `E:/AI_mk2/star-savior-decompiled`임. `NKM/NKM.decompiled.cs:9387-9389`의 Count가 `8295-8297`의 `OBF_27420`을 사용했음. `NKM.Templets/NKM.Templets.decompiled.cs:36344-36353`에서 `OBF_3108 && OBF_14228`, `Star.Templets/Star.Templets.decompiled.cs:4083-4084`에서 각각 `IsBuff`, `IsPositive`로 읽음을 확인했음. 음성은 `NKM.Templets:36356-36365`의 `IsBuff && !IsPositive`였음. 이번 구현은 강화 효과 개수에 적용했음.
- 현행 비공개 표 `tables/BUFF_TEMPLET.json:19137-19138`(탄력 가속), `19791-19792`(별빛의 궤적-AX), `20592-20593`(전투의 열기)는 `IsBuff=false, IsPositive=true`였음. 해제 불가 여부를 일괄 제외하는 근거는 없었음.
- `tools/build_buff_count.py --static E:/AI_mk2/starsavior-static-data`로 이름 843개의 `[IsBuff, IsPositive]` 후보 표를 `data/buff_count.json`에 생성했음. 원본 ID·설명·내정보는 포함하지 않았음. `mc.buff_count_source=table`을 기본, `legacy`를 이전 분류로 추가했음. `Unit.n_good()`에 통합해 적 `cond_ok`, 대상 선택, 자기/대상 강화 효과 개수별 피해 보정 등에 동일 적용했음. 기존 `*_disp` 비교 옵션은 이 분류에 해제 가능 필터를 추가하도록 했음.
- 피격 중첩 근거는 `NKM/NKM.decompiled.cs:15955-15968`의 효과별 순회, `16158-16171`의 각 효과 조건 검사 후 실행이었음. 현행 `tables/Plain/SKILL_CONDITION_TEMPLET.json:9030-9034`는 공허조율자 11중첩, `9046-9050`은 웬디고 5중첩이었음. `mc.hit_stack_order=apply_first`를 기본, `legacy`를 기존 처리로 추가했음. 같은 피격 묶음에서 조건이 참조하는 무조건 자기 중첩 부여를 먼저 실행하고 나머지 조건을 검사했음. 중첩 해제 후 추가 발동을 실행해 재귀 시전 때 중첩을 재사용하지 않도록 했음. 두 규칙에 grade·note·source를 기록했음.
- `tools/build_simpack.py`의 입력 목록에 새 표를 추가했음. 요청대로 `sim/manifest.json`은 재생성하지 않았음. 브라우저 배포 시에는 별도 패키지 재생성이 필요함. `data/quick.json`, `tests/fixtures/reuse_baseline.json`, 골든도 재생성하지 않았음.

시험을 수행했음.

- `tests/buff_count_hit_order_test.py` 6건 통과했음. table/legacy의 0·1·2개 경계, 중첩을 한 효과로 세기, 해제 불가·만료·체크 효과, 자기/대상 개수별 피해, 웬디고 5회/6회, 공허조율자 11회/12회와 두 번째 주기, 소비 후 추가 발동을 확인했음.
- 구현에서 IsBuff 판정을 제거해 5개 실패, IsPositive 판정을 제거해 1개 실패, 선행 중첩 부여를 제거해 2개 실패를 확인한 뒤 원본 바이트로 복구했음.
- `tests/rules_test.py` 21건, `tests/enemy_cond_test.py` 3건 통과했음. 새 규칙 2개를 rules 시험의 키 스냅샷에 추가했음. `tests/golden_check.py`는 구원자 64·파티 150·스테이지 팀 10 일치했음. 기존 입력 해시 불일치 안내와 foe_spawn 로더의 ResourceWarning은 출력됐음.

각 샘플에 `python -X utf8 -I tools/ingame_check.py --runs 100 --only <샘플> --bs-real --myinfo E:/AI_mk2/starsavior-static-data/samples/myinfo_2026-10-23.json`을 변경 전후 실행했음(seed 7). `sim_taken`은 판당 평균 총 피해이며 전역 턴당 피해와 구분했음. 두 규칙을 함께 legacy로 지정했을 때 변경 전 클리어율·sim_taken이 네 샘플 모두 정확히 재현됐음.

| 샘플 | 클리어율 전→후 | sim_taken 전→후 | 전역 턴당 받은 피해 전→후 |
|---|---:|---:|---:|
| 18x-b | 91%→9% | 372,815→448,031 | 7,092→9,987 |
| 17x-b | 100%→82% | 336,996→392,862 | 6,811→7,916 |
| corr-a | 99%→96% | 367,478→384,554 | 8,558→8,900 |
| 37-36r | 0%→0% | 322,854→322,164 | 11,715→12,130 |

미확정: 동명 ‘파쇄’는 양성/음성 표 행이 공존하고 현재 효과 객체에는 원본 ID가 없어 기존 category로 폴백했음. 표에 없는 합성 효과 이름도 기존 분류로 폴백했음. 해독본은 2026-03 구조 자료이므로 최신 빌드의 동일성은 미검증이며 수치는 현행 표를 사용했음. 회랑 실측 실패와 시뮬 클리어 96%의 차이는 남았음.

## 추가: 성간 회랑 명중률·보스 처치 조건 (2026-10-23, fix-corridor)

`181db0e` 기준으로 조사했음. 비공개 표는 `E:/AI_mk2/starsavior-static-data/tables/`, 해독본은 `E:/AI_mk2/star-savior-decompiled/`에서 읽기만 했음. 아래 표·NKM 참조는 이 두 루트 기준임. 실측 노트는 비공개 `analysis/ingame_2026-10-23/notes/video_corridor/notes_corr_a.md`, `notes_corr_b.md`를 사용했음. 계수나 전투력 배율을 실측에 맞추지 않았음.

확정한 차이와 구현을 기록했음.

- **상시 명중률 누락**을 확인했음. 공허조율자의 기본 명중률은 `UNIT_STAT_TEMPLET2.json:10941-10953`의 `NKM_UNIT_MON_STRIKER_CLOISTER_BOSS_08.m_StatData.NST_RATE_HIT=10000`이었음. 여기에 `SKILL_LEVEL_GROUP_TEMPLET_2.json:2181-2190`의 그룹 1300344 `SkillLevelStatType=NST_RATE_HIT, SkillLevelStatRate=10000`이 더해졌음. `NKM/NKM.decompiled.cs:7413-7432`는 명중률−회피율로 명중을 판정했음. 엔진은 기본 명중 100%를 전제로 버프 차이를 계산했으나 `[상시] 명중률 +100%`를 합산하지 않았음. 이로 인해 회피 50%인 페이가 보스 공격을 피하고, 피해 감소·치명 회피에 더해 월영과 천문의 길까지 발생했음. `SKILL_TEMPLET_1.json:1371-1384`의 월영 `ReactConditionID=5020`, `Plain/SKILL_CONDITION_TEMPLET.json:1925-1929`의 `MyEffectiveHit.DamageResultType=[Evade]`를 확인했음. `mc.permanent_accuracy=data`로 상시 명중률을 합산했으며 `legacy`로 누락을 재현하게 했음. 강화 불가와 무관한 상시 수치로 처리했음.
- **보스 처치 뒤 잔존 졸을 계속 공격하는 차이**를 확인했음. `BATTLE_TEMPLET_CLOISTER.json:79366-79374`의 FLOOR 355는 `BattleMode=BM_BOSS_KILL`이었음. `NKM/NKM.decompiled.cs:7517-7582`는 보스 사망 이벤트 후 같은 편 생존자를 피해 없이 사망 처리하고 각 사망 이벤트를 실행했음. 엔진은 졸을 따로 처치해야 웨이브를 끝냈음. `mc.battle_end_mode=data`를 추가했으며 `legacy`는 종전 전멸 조건으로 남겼음. `tools/build_battle_end.py`에서 기존 배치 매칭과 모든 칸의 `IsBoss` 일치까지 확인한 3,423개 스테이지를 `data/battle_end.json`에 저장했음(회랑 1,754개). 원본 행·게임 ID는 저장하지 않았음. 이 차이는 준 피해 과대의 원인이었으나, 클리어율 낙관의 원인으로 혼동하지 않았음. 단독 적용하면 클리어율은 오히려 96%→98%였음.

`tools/corridor_audit.py`로 seed 7 한 판의 전역 TURN·웨이브·시전 경로·실제 피해·치명·회피를 기록했음. `analysis/corridor_audit/timeline_before.json`, `timeline_after.json`에 저장했음. 관측 훅을 추가하기 전후 요약값이 같음을 확인했음. 아래는 동일 입력·seed의 경로 비교이며, 실측 행동 순서를 강제로 재생한 것은 아님.

| 항목 | 실측 corr-a | 수정 전 한 판 | 수정 후 한 판 |
|---|---|---|---|
| 첫 보스 처치 / 다음 웨이브 | T14 / T15 | T15 / 졸을 T17까지 별도 처치 | T15 / 잔존 졸 즉시 제거 |
| 공허조율자 일반 행동 | T33 기본기 확인, 나머지 누락 가능 | 궁 T23, 특수 T28, 기본 T36·42 | 궁 T19, 특수 T25, 기본 T31·37·41 |
| 공허의 재결 반격 | T28~29·32·34 등 | T28·29·31·34·40·41·43 (7회) | T28·29·30·35·38·39·40 (7회) |
| 고통의 선율 EXTRA | T23·26 (최소 2회) | T26 (1회) | T24·40 (2회) |
| 페이 월영 | 약 3회, 정확치 불확실 | 6회 / 195,855 피해 | 2회 / 87,118 피해 |
| 페이 월식 일반 / 강제 협공 피해 | 분리 집계 없음 | 33,978 / 56,819 | 45,493 / 47,348 |
| 페이 청풍랑월 피해 | 분리 집계 없음 | 87,241 | 55,333 |
| 페이 합계 / 치명 타격 | 189,330 / 미판독 | 373,893 / 12 of 14 | 235,292 / 8 of 9 |
| 보스 공격을 페이가 회피 | 정확치 미판독 | T28·43, 월영 발생 | 0회 |
| 결과 | T36 전멸 | T44 클리어 | T43 전멸 |

후보별 대조를 수행했음.

- 반격은 아군의 공격 스킬 유효 타격에 반응했으며 협공·반응 스킬도 후보였음. `NKM:15219-15265`, `15340-15357`에서 일반·협공·반응 공격의 후보를 별도로 처리했고 `7857-7870`은 같은 행동 이력 내 이미 반격한 유닛을 제외했음. 따라서 «공격마다 무제한 반격»으로 바꾸지 않았음. 현재 엔진의 행동당 한 번을 유지했음. 평균 반격은 5.56→5.54회로 거의 같았음. 명중 누락으로 반격 한 번의 피해와 후속 월영이 달라지는 쪽이 확인된 원인이었음. 일반·협공·반응의 세부 예약 순서 근사는 남겼음.
- EXTRA는 `SE_TEMPLET_SKILL_2.json:8830-8869`의 피해 종료 중첩 부여→조건 55113→특수기 예약→중첩 제거, `Plain/SKILL_CONDITION_TEMPLET.json:9030-9034`의 11중첩을 확인했음. `NKM:15579-15615`는 타격 이벤트 전체 루프 뒤 `NSEAT_DAMAGE_END`를 한 번 실행했고 `16859-16865`는 대상 목록에 통지했음. 연출 다단히트 수를 11회에 중복 계산할 근거는 없었음. 협공·반응 시전도 각각 한 번 세며 11·22회에 추가 발동하는 시험을 추가했음. 기존 피격 중첩 규칙은 바꾸지 않았음. 평균 EXTRA 1.22→1.68회가 됐지만 T23·26의 간격은 재현하지 못했음.
- 페이 계수는 `DAMAGE_TEMPLET.json:278-287`의 `AtkFactor` 기본 6500·특수 9000·궁극 11500이 입력과 일치했음. 치명 확률 자체를 고칠 근거는 확인하지 못했음. 한 판 치명 수와 시전 수를 함께 기록했으며, 영상의 정확한 치명·월영 횟수가 없어 숫자만 맞추지 않았음.
- 은둔자는 실제 배치 `BattleScript/JSON_CLOISTER_MOON_BATTLE_03_355.json`에서 두 웨이브 각 2체였음. 시뮬도 각 2체였고 공허의 인도 계수 8000·게이지 +10%p, 속세 절단 계수 9500·속도 증가·공격력 증가 효과를 처리했음. 수정 전 한 판은 특수 T6·7·24·27, 기본 T12·13·30·32·38·39였음. 노트의 T7~8 특수·T12~13 기본과 대응했음. 별도의 행동 배율 오류는 확정하지 못했음.
- 서든데스는 회랑 1,900곳에 이미 연결됐음. FLOOR 355는 `SuddenDeathId=404`, `SUDDEN_DEATH_TEMPLET.json:139-143`의 `NoticeActiveType=LEVEL_UP_TURN`, `SUDDEN_DEATH_GROUP_TEMPLET.json:580-590`의 첫 단계 끝 119·다음 끝 129였음. T120부터 HP−10%·DEF−5%·주는 회복/보호막−10%가 적용됐음. T1의 119, T36의 84는 다음 서든데스 단계까지의 카운터로 설명됐음. 표에 별도 LimitTurn은 없었으며 T36·42에는 약화가 없었음. 120턴 즉시 패배로 구현하지 않았음.

100판·seed 7·`--bs-real`·내 정보 10/23으로 요청한 다섯 샘플을 수정 전후 실행했음. 실행 결과는 `analysis/corridor_audit/{before,after}_<샘플>.json`에 저장했음. 페이가 없는 편성은 `—`로 표시했음. `sim_taken`은 판당 총 피해임.

| 샘플 | 클리어율 전→후 | sim_dealt 전→후 | sim_taken 전→후 | 페이 피해 전→후 |
|---|---:|---:|---:|---:|
| corr-a | 96%→61% | 787,745→651,222 | 387,053→461,136 | 353,662→234,240 |
| corr-b | 96%→61% | 787,745→651,222 | 387,053→461,136 | 353,662→234,240 |
| 18x-b | 9%→9% | 517,772→517,772 | 448,031→448,031 | — |
| 17x-b | 82%→82% | 597,209→597,209 | 392,862→392,862 | — |
| 37-36r | 0%→0% | 380,057→354,382 | 322,164→318,761 | — |

원인 분리를 위해 corr-a에 규칙을 따로 적용했음.

| 규칙 | 클리어 | 준 / 받은 피해 | 페이 피해 | 전체 행동 |
|---|---:|---:|---:|---:|
| 둘 다 legacy | 96% | 787,745 / 387,053 | 353,662 | 43.27 |
| 명중률만 수정 | 59% | 765,681 / 494,618 | 288,703 | 50.25 |
| 보스 처치만 수정 | 98% | 651,623 / 371,569 | 291,045 | 36.41 |
| 둘 다 수정 | 61% | 651,222 / 461,136 | 234,240 | 43.09 |

회랑 턴당 받은 피해는 8,945→10,702가 됐으며 실측 12,499·13,004에는 아직 못 미쳤음. 페이 피해는 실측 약 189k보다 24% 높고, 클레어는 181,908→192,261로 늘었으나 실측 218~238k보다 낮았음. 37-36r는 실측 준 피해 376,743~379,989에 거의 맞던 값이 354,382로 줄어 더 멀어졌음. 받은 피해도 실측 382,405~388,934보다 부족한 방향으로 3,403 더 줄었음. 이를 개선으로 표시하지 않았음. 남은 후보는 공격·추가 발동 예약 시점, 첫 행동 순서, 생존 시간 및 피해 분배였음. 영상 누락과 해독본의 빌드 차이 때문에 세부 차이를 확정하지 못했음.

시험을 수행했음. `tests/corridor_test.py` 9건, 변경한 `tests/rules_test.py` 21건, `tests/golden_check.py` 구원자 64·파티 150·스테이지 팀 10 일치를 확인했음. 관련 `buff_count_hit_order_test.py` 6건, `revenge_test.py` 9건, `reaction_queue_test.py` 14건, `turn_limit_test.py` 5건도 통과했음. 상시 명중률 합산을 제거하자 새 시험 2건 실패, 보스 사망 전파를 막자 2건 실패했음. 각각 원본 바이트로 복원한 뒤 통과했음. 두 새 규칙을 모두 legacy로 설정하자 다섯 샘플의 전체 ingame_check 반환값이 수정 전과 정확히 같았음. 기존 골든 입력 해시 불일치 안내와 foe_spawn ResourceWarning은 그대로 출력됐음.

`tools/build_simpack.py` 입력 목록에 새 표를 추가했음. 요청대로 manifest·quick·reuse_baseline·골든·index.html을 재생성하거나 수정하지 않았으며, 브라우저 배포용 패키지 갱신은 수행하지 않았음. 커밋·푸시하지 않았음.
