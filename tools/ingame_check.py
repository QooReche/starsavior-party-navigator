# -*- coding: utf-8 -*-
"""인게임 실측(docs/ingame_samples.md)과 확률 엔진을 대조한다 — 「준 피해 ÷ 받은 피해」 비율·클리어 확률·아군 행동 수.

실측 판마다 사용자 능력치 화면 값(공·생·방·속도·치명 등)을 stats_override 로 넣고(화면이 없는 구원자는 남은 전투력 몫으로 표준 육성 배율),
재점화 버프는 전투력 보정 배율에 곱한다(api options.rekindle 과 같은 뜻). 규칙을 바꿔 보려면 --ov '{"basic_tough": 1}'.

사용: python -X utf8 -I tools/ingame_check.py [--runs 100] [--ov JSON] [--only 37-3] [--bs [LV]] [--bs-name 이름] [--bs-real] [--myinfo PATH]
--myinfo = 비공개 내정보를 제자리에서 읽어 콘텐츠 규칙으로 최종 능력치·전투력을 계산한다.
이 경로는 build=none, stats_final=true이며 표준 육성·전투력 재배분을 사용하지 않는다.
--bs [LEVEL] = 실측 장착 스킬 「큐브 과부하」 활성화(레벨 생략 시 Lv.5, `--bs 3` 처럼 지정 가능, 기본 미장착).
--bs-name = --bs 로 장착할 스킬 이름(기본 큐브 과부하). --bs-real = 샘플별 실제 장착(BS_REAL)을 씀(--bs 를 같이 주면 그쪽이 덮어씀).
운영 기본값: 36-36=heal, 37-2~37-5=auto. --ov '{"nova_policy":"auto"}' 로 전부 순수 오토 대조 가능.
nova_burst.total/by_unit은 전체 판 합계, uses·heal·healing은 판 평균(실제 HP 회복, 초과 회복 제외).
출력 dist = 판별 분포(결과 비율·행동 수 분위수·실측 TURN 위치 real_turn_pct·진 판의 보스 남은 생명력·먼저 쓰러진 구원자) — 「실측이 시뮬 분포 안인가」 판정용.
2026-10-21 결과: 37-2(잡몹) 실제 4.13 vs 시뮬 4.11 일치 / 37-3·36-36(큰 보스) 실제 1.82·1.88 vs 시뮬 0.49·0.84 — 보스전만 과대(설명 docs/ingame_samples.md)
"""
import json
import os
import sys
import argparse
from collections import defaultdict
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

# 사용자 능력치 화면(2026-10-21, Lv.342·공명 10). cr/cd/eh/er 은 1/10000
REAL = {
    'white-pearl-luna': dict(atk=12314, hp=66887, spd=181, cr=6820, cd=7020, eh=17400, er=1500, **{'def': 5206}),
    'wedding-carmen': dict(atk=9972, hp=119367, spd=151, cr=880, cd=6470, eh=10620, er=3216, **{'def': 5811}),
    'cristelle': dict(atk=17903, hp=60168, spd=157, cr=5610, cd=8450, eh=16804, er=2380, **{'def': 4798}),
    # 2026-10-21 2차(파티 전투력 411,163 = 네 명 화면 전투력 합과 정확히 일치)
    'claire': dict(atk=16002, hp=65538, spd=187, cr=5720, cd=11900, eh=11012, er=2412, **{'def': 4915}),
    'professor-m': dict(atk=15196, hp=61258, spd=179, cr=8330, cd=6400, eh=14744, er=2540, **{'def': 5053}),
    'waltz-asherah': dict(atk=9909, hp=95464, spd=183, cr=8730, cd=9710, eh=12268, er=1308, **{'def': 5522}),
}
TEAM2 = ['claire', 'waltz-asherah', 'wedding-carmen', 'professor-m']      # 화면 카드 순서(후열 클레어, 전열 아세라·카르멘, 후열 프로페서M)
# 실측 판: (콘텐츠, 탭|스테이지, 화면 카드 순서[후열1, 전열1, 전열2, 후열2], 리더, 파티 전투력, 재점화 단계, 준 피해, 받은 피해, TURN, 결과)
SAMPLES = {
    '36-36': ('op', '아가논 시가지|SECTOR 36-36', ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], None,
              394578, 3, 990889, 527628, 38, 'clear'),
    '37-2': ('op', '모나스티르 광장|SECTOR 37-2', ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], 'wedding-carmen',
             394578, 0, 1104681, 267286, 52, 'clear'),
    '37-3': ('op', '모나스티르 광장|SECTOR 37-3', ['wedding-epindel', 'white-pearl-luna', 'wedding-carmen', 'cristelle'], 'wedding-carmen',
             394578, 0, 895585, 492422, 43, 'clear'),
    '37-4': ('op', '모나스티르 광장|SECTOR 37-4', TEAM2, 'wedding-carmen', 411163, 0, 346440, 53172, 13, 'clear'),
    '37-5': ('op', '모나스티르 광장|SECTOR 37-5', TEAM2, 'wedding-carmen', 411163, 0, 713329, 170878, 22, 'clear'),
    # 2026-10-23 장비 탐색(혹한의 습격 XVII, 권장 411,185): 에밀리(후)·프레이(전, 리더)·에데(전)·그웬(후), 오토, 브레이크 스킬 Lv.5.
    # 준 피해 = 104,384+416,393+70,328+16,189, 받은 피해 = 139,909+108,444+278,674+173,051. 65턴 이내 승리는 66/65로 실패. 쓰러진 구원자: 프레이·에데
    '17': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['emily', 'frey', 'haydee', 'gwen'], 'frey', 372610, 0, 607294, 700078, 66, 'clear'),
    # 같은 편성, 리더 에밀리: 준 피해 96,894+413,807+82,809+15,511, 받은 피해 143,408+118,794+256,474+229,524, TURN 69, 프레이·에데 쓰러짐
    '17e': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['emily', 'frey', 'haydee', 'gwen'], 'emily', 372610, 0, 609021, 748200, 69, 'clear'),
    # 페이지 추천 편성(프로페서M 후·에데 전·에밀리 전 리더·아모라 후, 전투력 411,935)으로 실제 플레이: 패배(전멸), TURN 37, 달성도 77%(보스 체력 604,347 중 137,167 남음)
    # 준 피해 21,787+114,201+33,316+297,876, 받은 피해 135,315+73,458+207,333+104,318. 회복 0(브레이크 스킬 컷신 +7,817 한 번은 통계에 안 잡힘). 쓰러진 순서: 에밀리·프로페서M(TURN 29 추정) → 에데(TURN 35) → 아모라(TURN 37)
    '17r': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['professor-m', 'haydee', 'emily', 'amora'], 'emily', 411935, 0, 467180, 520424, 37, 'fail'),
    # 2026-10-23 영상 2판(같은 편성, 권장 411,185, 팀 전투력 419,288, 재점화 0, 전원 Lv.344): 트리쉬(후, trish)·에데(전, haydee)·에밀리(전, 리더)·그웬(후), 오토
    # 브레이크 스킬 장착은 확실(컷신 확인), 종류는 큐브 과부하 추정·레벨 불명. 편성 화면은 사용자 확인 값
    # 판 A: 패배, TURN 45, 보스 잔여 HP 36,171(604,347 중). 준 피해 / 받은 피해: 트리쉬 256,865/72,931 · 그웬 218,835/86,261 · 에데 69,117/236,865 · 에밀리 23,359/115,133. 회복 0
    # 쓰러진 순서(추정, 근거 약함): 에밀리(TURN 20~26) -> 그웬(TURN 35) -> 에데(TURN 45), 트리쉬 최종 생존 불확실
    '17x-a': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['trish', 'haydee', 'emily', 'gwen'], 'emily', 419288, 0, 568176, 511190, 45, 'fail'),
    # 판 B: 승리, TURN 41, 쓰러진 구원자 0. 준 피해 / 받은 피해: 트리쉬 217,793/28,353 · 에데 62,399/148,100 · 에밀리 51,189/87,156 · 그웬 273,581/26,643. 회복 0
    # 준 피해 합이 보스 HP보다 615 많음(오버킬). 브레이크 스킬 컷신의 아군 +8,081 은 회복 열에 안 잡힘. 불확실: 브레이크 스킬 레벨
    '17x-b': ('equip', '혹한의 습격|혹한의 습격 XⅦ', ['trish', 'haydee', 'emily', 'gwen'], 'emily', 419288, 0, 604962, 290252, 41, 'clear'),
    # 2026-10-23 영상 2판(같은 편성, 혹한의 습격 XⅧ 권장 446,525, 팀 전투력 412,097, 재점화 0(장비 탐색), 전원 Lv.344, 오토, 브레이크 스킬 큐브 과부하 Lv5 배너·컷인 확인)
    # 편성(카드 순서): 아모라(후, amora)·에데(전, haydee)·에밀리(전, 리더)·그웬(후). 보스 시작 HP 652,064
    # 판 A: 패배, TURN 41, 달성도 79%. 준 피해 / 받은 피해: 아모라 260,728/107,296 · 그웬 199,583/90,900 · 에데 39,995/166,506 · 에밀리 21,268/127,173. 회복 0
    # 보스 잔여 130,490 은 652,064-521,574 계산값(직접 판독 아님). 브레이크 스킬 1회(T21~22), 컷인 아모라 +7,936 은 회복 열에 안 잡힘. 불확실: 쓰러진 순서(확정 못 함)
    '18x-a': ('equip', '혹한의 습격|혹한의 습격 XⅧ', ['amora', 'haydee', 'emily', 'gwen'], 'emily', 412097, 0, 521574, 491875, 41, 'fail'),
    # 판 B: 패배(전멸), TURN 43, 달성도 81%, 보스 최종 HP 121,753(준 피해 합과 정확히 일치). 준 / 받은: 아모라 238,121/82,738 · 그웬 206,241/93,747 · 에데 49,369/182,478 · 에밀리 36,580/103,588. 회복 0
    # 쓰러진 순서: 에밀리 TURN 36(확실) -> 나머지 TURN 41~43 연속(순서 불확실). 브레이크 스킬 1회(T22). 에밀리 준 피해 36,580 은 축소본 판독
    '18x-b': ('equip', '혹한의 습격|혹한의 습격 XⅧ', ['amora', 'haydee', 'emily', 'gwen'], 'emily', 412097, 0, 530311, 462551, 43, 'fail'),
    # 2026-10-24 영상 1판(혹한의 습격 XⅧ, 사이트 추천 편성, 팀 전투력 419,875, 전원 Lv.344, 오토, 브레이크 스킬 큐브 과부하 Lv6(배너·치트 매트릭스 연출), 재점화 0(장비 탐색; 카드 표기 5/3/없음/2))
    # 편성(카드 순서): 트리쉬(후, trish)·에데(전, haydee)·에밀리(전, 리더 왕관 확인)·그웬(후). 보스 시작 HP 652,064
    # 판 A: 패배(전멸), TURN 48, 보스 잔여 32,482(통계 합계로 계산, T48 카드 HP와 일치, 약 5%), 달성도 미확인. 준 / 받은 / 회복: 트리쉬 277,646/100,899/0 · 그웬 254,913/82,380/0 · 에데 35,016/172,992/0 · 에밀리 52,007/132,439/0
    # 쓰러진 순서: 에데 T35~36 -> 에밀리 T36~37(불확실) -> 트리쉬 T46~47 -> 그웬 T48. 큐브 과부하 3회(T14/T29/T43, 회복 통계 0), 보스 BREAK 3회(T13·T28·T42 부근)
    '18x2-a': ('equip', '혹한의 습격|혹한의 습격 XⅧ', ['trish', 'haydee', 'emily', 'gwen'], 'emily', 419875, 0, 619582, 488710, 48, 'fail'),
    # 판 B(2026-10-24 같은 편성·같은 조건, 편성 화면 왕관·카드 순서·전투력 419,875 동일 확인): 승리, TURN 52, 달성도 100%, 전투 승리·65턴·60턴 3조건 모두 달성(52/65, 52/60)
    # 준 / 받은 / 회복: 트리쉬 293,385/70,376/0 · 그웬 270,581/74,187/0 · 에데 54,474/191,583/0 · 에밀리 42,499/154,762/0. 준 피해 합이 보스 HP 652,064 보다 8,875 많음(오버킬)
    # 쓰러진 구원자: 에밀리 1명(T35~38, 불확실), 나머지 3명 생존. 큐브 과부하 3회(T14/T29/T40~41, 2·3회차 아군 회복 숫자 약 5.8~8.7k 가 화면에 보였으나 통계 회복 0), 보스 브레이크 최소 3회(T14·T28·T38, T40 부근 4회차 가능, 불확실)
    '18x2-b': ('equip', '혹한의 습격|혹한의 습격 XⅧ', ['trish', 'haydee', 'emily', 'gwen'], 'emily', 419875, 0, 660939, 490908, 52, 'clear'),
    # 2026-10-23 영상 판독(작전 SECTOR 37-36, 오토, 재점화 1단계, 권장 473,650): 에핀델(후, 블레싱 인 블룸)·아세라(전, 왈츠 오브 스타라이트)·아모라(전)·샤를(후, 리더, 하트 오브 모나스티르), 전원 Lv.344, 브레이크 스킬 Lv.3(종류 미확인)
    # 패배(전멸), TURN 25, 달성도 36%. 준 피해 42,735(샤를)+198,437(아모라)+74,129(에핀델)+61,442(아세라), 받은 피해 91,446+104,599+75,645+110,715, 아세라 회복 72,425. 준 피해엔 쫄(예언자) 피해 포함(보스 단독 분리 불가)
    # 보스 HP 724,190 -> TURN 20~23 시점 443,166. 불확실: 브레이크 스킬 종류, 사망 순서(아모라 TURN 19~20 추정), 개별 전투력·각인(영상에 없음). 영상 파티 전투력 419,809
    '37-36r': ('op', '모나스티르 광장|SECTOR 37-36', ['wedding-epindel', 'waltz-asherah', 'amora', 'bunny-charlotte'], 'bunny-charlotte', 419809, 1, 376743, 382405, 25, 'fail'),
    # 2026-10-23 두 번째 판(37-36r 과 같은 조건·편성, 영상 판독): 패배(전멸), TURN 23, 달성도 36%, 파티 전투력 419,809, 재점화 1단계, 브레이크 스킬 Lv.3(종류 불명)
    # 준 피해 / 받은 피해: 에핀델 113,872/75,956, 아세라 30,818/126,940(회복 68,114), 샤를 34,226/85,268, 아모라 201,073/100,770. 합계 준 379,989 받은 388,934
    # 불확실: 아모라 TURN 17 피해 약 48,800은 미관측(역산 추정, 누락 가능), 사망 순서, 브레이크 스킬 종류
    '37-36r2': ('op', '모나스티르 광장|SECTOR 37-36', ['wedding-epindel', 'waltz-asherah', 'amora', 'bunny-charlotte'], 'bunny-charlotte', 419809, 1, 379989, 388934, 23, 'fail'),
    # 2026-10-23 영상 판독(성간 회랑 = 달 회랑 FLOOR 355, 권장 349,185, 오토, 전원 Lv.344): 프로페서M(후, 리더)·카르멘(전, 웨딩)·페이(전)·클레어(후), 팀 전투력 394,126, 브레이크 스킬 스타피어서 Lv3(배너 아이콘)
    # 판 A: 패배(전멸), TURN 36, 달성도 92%, 2웨이브 보스 공허조율자 HP 9,738 남김. 준 / 받은 / 회복: 프로페서M 198,367/81,918/0 · 카르멘 25,412/142,715/131,390 · 클레어 237,995/117,270/0 · 페이 189,330/108,077/28,394
    # 쓰러진 순서: 프로페서M T29(확정) -> 카르멘(T29~31, 불확실) -> 클레어 T34 -> 페이 T36. 스타피어서 발동 장면은 영상에서 확인 못 함
    'corr-a': ('clo', '달 회랑|FLOOR 355', ['professor-m', 'wedding-carmen', 'fei', 'claire'], 'professor-m', 394126, 0, 651104, 449980, 36, 'fail'),
    # 판 B: 패배(전멸), TURN 42, 달성도 91%, 보스 HP 4,310 남김(T36·39 확인). 준 / 받은 / 회복: 프로페서M 178,234/73,878/0 · 클레어 217,700/87,792/0 · 카르멘 33,543/176,014/226,273 · 페이 188,607/208,486/28,289
    # 쓰러진 순서(추정): 프로페서M T23~24 -> 클레어 T29~30 -> 카르멘 T34~36 -> 페이 T42. 1웨이브 잔상의 감시자 T6 부근 처치
    'corr-b': ('clo', '달 회랑|FLOOR 355', ['professor-m', 'wedding-carmen', 'fei', 'claire'], 'professor-m', 394126, 0, 618084, 546170, 42, 'fail'),
    # 2026-10-24 영상 판독(성간 회랑 FLOOR 440 Lv3254, 권장 506,820, 오토, 전원 Lv.344, 재점화 0): 그웬(후, gwen)·힐데(전, hilde)·아모라(전, amora)·프로페서M(후, 리더), 팀 전투력 408,032
    # 브레이크 스킬 스타피어서 Lv3(배너 은발 남성 Lv.3, 아이콘 대조는 불확실). 보스 공허말살자, 1웨이브 처치 후 2웨이브(보스 HP 527,926 시작)
    # 판 A: 패배(전멸), TURN 41, 달성도 81%, 보스 약 15% 남김(수치 미확인, 판독 근사). 준 / 받은 / 회복: 힐데 26,685/208,389/28,404 · 그웬 242,397/76,185/0 · 아모라 309,536/77,941/0 · 프로페서M 222,401/73,492/0
    # 1웨이브 T16 처치. 4명 모두 T41 보스 「전장 파괴」 직후 전멸(개별 사망 순서·시점 불확실). 4초 간격 샘플이라 스킬 횟수·브레이크 스킬 발동은 확인 못 함
    'corr440-a': ('clo', '성간 회랑|FLOOR 440', ['gwen', 'hilde', 'amora', 'professor-m'], 'professor-m', 408032, 0, 801019, 436007, 41, 'fail'),
    # 판 B: 패배(전멸), TURN 44, 달성도 89%, 보스 잔여 HP 50,861. 준 / 받은 / 회복: 힐데 30,477/238,845/66,276 · 그웬 226,601/81,609/0 · 아모라 440,690/71,897/0 · 프로페서M 191,469/84,966/0
    # 1웨이브 T12 처치. T43 까지 4명 생존, 3명(그웬·프로페서M·힐데)이 T43~44 경계에 동시 사망 추정, 아모라가 마지막. 개별 순서 불확실
    'corr440-b': ('clo', '성간 회랑|FLOOR 440', ['gwen', 'hilde', 'amora', 'professor-m'], 'professor-m', 408032, 0, 889237, 477317, 44, 'fail'),
    # 2026-10-24 영상 판독(작전 SECTOR 37-36, 재점화 1(X1), 권장 473,650, 오토, 전원 Lv.344, 팀 전투력 400,989): 아모라(후)·카르멘(전, wedding-carmen)·에밀리(전, 리더)·프로페서M(후)
    # 리더 불일치: 사이트 화면은 카르멘 리더였으나 영상 편성 화면의 왕관은 에밀리(3번째 카드). 브레이크 스킬 큐브 과부하 Lv6(배너·발동 연출 일치, 레벨은 내 정보 10/24 보유값)
    # 판 A: 패배(전멸), TURN 40, 달성도 62%, 보스(공허조율자 724,190) 잔여 179,496. 준 / 받은 / 회복: 에밀리 96,279/158,421/0 · 아모라 335,169/143,654/0 · 카르멘 29,218/162,881/161,915 · 프로페서M 191,195/208,424/0
    # 사망 순서(불확실): 에밀리(T27~29 추정) -> 카르멘 T35 -> 아모라(T30~35 사이) -> 프로페서M T40. 큐브 과부하 T26 1회(회복 7,680/8,416x3), 보스 BREAK 4회(T2·T17·T25·T39). 2초 간격 샘플이라 시전 횟수는 최소치
    'op3736b-a': ('op', '모나스티르 광장|SECTOR 37-36', ['amora', 'wedding-carmen', 'emily', 'professor-m'], 'emily', 400989, 1, 651861, 673380, 40, 'fail'),
    # 판 B: 패배(전멸), TURN 46, 달성도 69%, 보스 잔여 67,671(달성도와 불일치, 이유 미확인). 준 / 받은 / 회복: 에밀리 49,472/140,439/0 · 아모라 389,616/97,610/0 · 카르멘 44,870/296,424/234,055 · 프로페서M 235,796/261,919/0
    # 사망 순서: 에밀리 T19~22 -> 아모라 T35~40 -> 카르멘 T41 -> 프로페서M T46. 큐브 과부하 T26 직후 1회(오메가 프로토콜 +6,519x3), 보스 BREAK T27 1회(T41 배너는 판독 불확실)
    'op3736b-b': ('op', '모나스티르 광장|SECTOR 37-36', ['amora', 'wedding-carmen', 'emily', 'professor-m'], 'emily', 400989, 1, 719754, 796392, 46, 'fail'),
    # 2026-10-24 09:53/09:57 영상 판독(같은 스테이지·같은 4명·같은 큐브 과부하 Lv6, 리더만 카르멘; 팀 전투력 401,457): 리더 카르멘(편성 화면 왕관 = 2번째 카드)
    # 판 C1: 패배(전멸), TURN 39, 달성도 62%, 보스 잔여 약 137k('?' 연출 중 표시, 724,190 기준 약 19%). 준 / 받은 / 회복: 에밀리 36,556/119,611/0 · 아모라 327,182/173,984/0 · 카르멘 59,427/212,192/192,780 · 프로페서M 226,244/169,493/0
    # 사망 순서(불확실): 에밀리 최초(T9~T27) -> 아모라 T33 추정 -> 카르멘 T37~38 추정 -> 프로페서M T39. 큐브 과부하 T27~28 1회(회복 6,503/6,531/6,531, 3명), 보스 브레이크 T27 1회(파랑), 수호의 기사 트리거 T17·T28. 2초 간격 샘플이라 시전 횟수는 최소치
    'op3736c-a': ('op', '모나스티르 광장|SECTOR 37-36', ['amora', 'wedding-carmen', 'emily', 'professor-m'], 'wedding-carmen', 401457, 1, 649409, 675280, 39, 'fail'),
    # 판 C2: 패배(전멸), TURN 44, 달성도 69%, 보스 잔여 109,749. 준 / 받은 / 회복: 에밀리 95,559/200,589/0 · 아모라 330,412/129,577/0 · 카르멘 52,361/223,496/195,778 · 프로페서M 243,082/248,048/0
    # 사망 순서(불확실): 에밀리 T23~25 추정 -> 아모라 T32~33 추정 -> 카르멘/프로페서M 순서 불확실 -> T44 전멸. 큐브 과부하 T26 1회(회복 약 9,105~9,109 x4), 보스 브레이크 T25 1회(파랑), 에밀리 EXTRA TURN T7, 수호의 기사 T37(최소)
    'op3736c-b': ('op', '모나스티르 광장|SECTOR 37-36', ['amora', 'wedding-carmen', 'emily', 'professor-m'], 'wedding-carmen', 401457, 1, 721414, 801710, 44, 'fail'),
    # 2026-10-24 16:47/16:51 영상 판독(사이트 1안 그대로, 같은 편성·리더 카르멘·큐브 과부하 Lv6; 팀 전투력 401,457). 큐브 과부하 1회(회복 6,531 x3 고정값 추정), 영역 아이콘 5->1 확인
    # 판 D1: 패배, TURN 35, 달성도 미촬영, 보스 잔여 171,645. 준 / 받은 / 회복: 에밀리 48,995/146,369/0 · 아모라 336,042/138,423/0 · 카르멘 43,730/166,690/156,205 · 프로페서M 197,399/162,523/0
    'op3736d-a': ('op', '모나스티르 광장|SECTOR 37-36', ['amora', 'wedding-carmen', 'emily', 'professor-m'], 'wedding-carmen', 401457, 1, 626166, 614005, 35, 'fail'),
    # 판 D2: 패배(전멸), TURN 34, 달성도 57%, 보스 잔여 약 189k(T33 값, 마지막 T34 피해 후는 미판독). 에밀리 36,469/125,678/0 · 아모라 374,418/135,350/0 · 카르멘 13,503/171,689/138,816 · 프로페서M 174,069/153,260/0
    'op3736d-b': ('op', '모나스티르 광장|SECTOR 37-36', ['amora', 'wedding-carmen', 'emily', 'professor-m'], 'wedding-carmen', 401457, 1, 598459, 585977, 34, 'fail'),
    # 2026-10-24 17:02/17:07 영상 판독(성간 회랑 FLOOR 450 Lv3352, 권장 522,010, 오토, 전원 Lv.344, 재점화 0): 에밀리(후)·카르멘(전, 웨딩)·힐데(전, 왕관 리더)·아모라(후), 팀 전투력 397,725.
    # 브레이크 스킬 슬롯 Lv6(큐브 과부하 추정)이나 **두 판 모두 미발동**(사용자: 우측 중앙 버튼을 눌러야 발동, 컷인·배경 전환·영역 아이콘 없음) -> BS_REAL 에 넣지 않음(스킬 없이 대조)
    # 판 E1: 패배, TURN 70, 달성도 미촬영, 웨이브 1/2 T41 처치·보스 약 65% 잔여. 준 / 받은 / 회복: 힐데 49,873/319,895/37,900 · 카르멘 46,352/171,805/315,408 · 에밀리 127,765/179,104/0 · 아모라 509,534/180,548/0
    'corr450-a': ('clo', '성간 회랑|FLOOR 450', ['emily', 'wedding-carmen', 'hilde', 'amora'], 'hilde', 397725, 0, 733524, 851352, 70, 'fail'),
    # 판 E2: 패배(전멸), TURN 64, 달성도 61%, 웨이브 1 T40 처치·보스 약 65~70% 잔여('?'). 힐데 51,569/291,022/56,850 · 카르멘 31,498/155,509/238,661 · 에밀리 163,864/188,094/0 · 아모라 475,463/167,725/0
    'corr450-b': ('clo', '성간 회랑|FLOOR 450', ['emily', 'wedding-carmen', 'hilde', 'amora'], 'hilde', 397725, 0, 722394, 802350, 64, 'fail'),
    # 2026-10-25 09:12 영상 판독(성간 회랑 FLOOR 350, 사이트 1안 그대로, 오토, 전원 Lv.345, 팀 전투력 404,110): 샤를(후, 하트 오브 모나스티르)·루나(전, 화이트 펄 트랩, 리더)·에핀델(전, 블레싱 인 블룸)·크리스텔(후)
    # 패배, TURN 44, 달성도 99%(보스 거의 잔여 없음), 웨이브 2/2. 브레이크 스킬 미발동(추천 스타피어서 Lv4 슬롯, 발동 장면·컷인 없음). 회복 0. 준 / 받은: 샤를 160,326/89,535 · 루나 98,937/72,399 · 에핀델 156,596/79,461 · 크리스텔 324,395/83,284 (마지막 자리 일부 불확실)
    'corr350-a': ('clo', '성간 회랑|FLOOR 350', ['bunny-charlotte', 'white-pearl-luna', 'wedding-epindel', 'cristelle'], 'white-pearl-luna', 404110, 0, 740254, 324679, 44, 'fail'),
    # 2026-10-25 09:22 영상 판독(성간 회랑 = 달 회랑 FLOOR 360 Lv2282, 사이트 1안 그대로, 오토, 전원 Lv.345, 권장 356,160, 팀 전투력 402,222): 프레이(후, 노블 프린세스, 리더 추정)·카르멘(전, 이터널 프로미스)·클레어(전, 플로리스 블루 로즈)·프로페서M(후)
    # 승리, TURN 36, 달성도 100%, 쓰러진 구원자 0, 웨이브 2/2(보스 공허멸시자 189초 처치). 브레이크 스킬 미발동(Lv.4 슬롯 1개, 컷인 없음 -> BS_REAL 에 안 넣음). BREAK! 연출 146초 1회. 통계 원해상도 확인: 준 / 받은 / 회복: 프레이 325,304/54,039/0 · 카르멘 31,571/60,298/150,988 · 클레어 165,325/57,742/0 · 프로페서M 189,884/13,894/0
    'corr360-a': ('clo', '달 회랑|FLOOR 360', ['bunny-frey', 'wedding-carmen', 'claire', 'professor-m'], 'bunny-frey', 402222, 0, 712084, 185973, 36, 'clear'),
}
# 보스 잔여 HP·달성도 같은 부가 실측: SAMPLES 튜플에는 못 넣고(형식 고정) 여기에 둔다 — 도구가 출력에 real_extra 로 붙인다
REAL_EXTRA = {'18x2-a': dict(boss_left_hp=32482, heal=0, boss_hp_start=652064, rekindle=0, boss_breaks=3, cube_overload_uses=3),
              '18x2-b': dict(achieve=1.0, boss_left_hp=0, heal=0, boss_hp_start=652064, rekindle=0, boss_breaks=3, cube_overload_uses=3),
              'corr440-a': dict(achieve=0.81, boss_left_frac=0.15, heal=28404, boss_hp_start=527926),
              'corr440-b': dict(achieve=0.89, boss_left_hp=50861, heal=66276, boss_hp_start=527926),
              'op3736b-a': dict(achieve=0.62, boss_left_hp=179496, heal=161915, boss_hp_start=724190, rekindle=1, boss_breaks=4, cube_overload_uses=1),
              'op3736b-b': dict(achieve=0.69, boss_left_hp=67671, heal=234055, boss_hp_start=724190, rekindle=1, boss_breaks=1, cube_overload_uses=1),
              'op3736c-a': dict(achieve=0.62, boss_left_hp=137334, heal=192780, boss_hp_start=724190, rekindle=1, boss_breaks=1, cube_overload_uses=1),
              'op3736c-b': dict(achieve=0.69, boss_left_hp=109749, heal=195778, boss_hp_start=724190, rekindle=1, boss_breaks=1, cube_overload_uses=1),
              'corr360-a': dict(achieve=1.0, heal=150988, rekindle=0),
              'corr450-a': dict(heal=353308, rekindle=0),
              'corr450-b': dict(achieve=0.61, heal=295511, rekindle=0),
              'op3736d-a': dict(boss_left_hp=171645, heal=156205, boss_hp_start=724190, rekindle=1, boss_breaks=1, cube_overload_uses=1),
              'op3736d-b': dict(achieve=0.57, boss_left_hp=188970, heal=138816, boss_hp_start=724190, rekindle=1, boss_breaks=1, cube_overload_uses=1)}
# 2026-10-21 사용자 확인: 36-36만 오토 선택 + 회복용 수동 버스트, 37구역은 순수 오토.
# 10/22 패치로 밸런스가 바뀐 스테이지의 패치 전 실측 — 지금 시뮬을 판정하는 근거로 쓰지 않는다(사용자 지시 2026-10-23).
# 기본 실행에서 빼고 --include-old 나 --only 로 부를 때만 돌린다. 적 수치가 그대로인 37-2~37-5(10/21)는 유효.
PRE_PATCH = {'36-36': '10/22 패치로 보스 공허순례자 공격력 46,880 -> 39,848(패치 전 10/21 실측·공략 영상)'}
# 샘플별 실제 장착 브레이크 스킬 (이름, 레벨) — 2026-10-23 정정. 37-36 = 행성 정화 Lv3(편성 화면·배너 아이콘 확인),
# 17x = 큐브 과부하 Lv5(사이트 추천, 장착 확실·레벨은 내 정보 보유값). 나머지는 미확인이라 지정 안 함.
BS_REAL = {'37-36r': ('행성 정화', 3), '37-36r2': ('행성 정화', 3), '17x-a': ('큐브 과부하', 5), '17x-b': ('큐브 과부하', 5),
           '18x-a': ('큐브 과부하', 5), '18x-b': ('큐브 과부하', 5), '18x2-a': ('큐브 과부하', 6), '18x2-b': ('큐브 과부하', 6), 'corr-a': ('스타피어서', 3), 'corr-b': ('스타피어서', 3),
           'corr440-a': ('스타피어서', 3), 'corr440-b': ('스타피어서', 3),
           'op3736b-a': ('큐브 과부하', 6), 'op3736b-b': ('큐브 과부하', 6),
           'op3736c-a': ('큐브 과부하', 6), 'op3736c-b': ('큐브 과부하', 6),
           'op3736d-a': ('큐브 과부하', 6), 'op3736d-b': ('큐브 과부하', 6)}
NOVA_POLICY = {name: ('heal' if name == '36-36' else 'auto') for name in SAMPLES}

from tools.runtime import low_priority


def rebalance(spec, pw):
    """화면 능력치가 없는 구원자에게 «남은 전투력»(파티 전투력 − 화면 값 구원자들의 엔진 전투력)을 나눠 준다 — 공·생·방에 같은 배율
    (전투력 공식이 공·생·방에 선형이라 2번 반복이면 충분). codex 리뷰 2026-10-21: 안 하면 394,578 대신 398,170 으로 돌았다."""
    from battlesim.api import _norm_party, party_power
    from battlesim.starsavior.data import get_db
    db = get_db()
    fixed = [u for u in spec['units'] if u.get('stats_final')]
    free = [u for u in spec['units'] if not u.get('stats_final')]
    if not free:
        return
    target = pw - party_power(_norm_party({'units': fixed}, db, 'fixed', 'standard')[0])
    for _ in range(2):
        f = target / party_power(_norm_party({'units': free}, db, 'fixed', 'standard')[0])
        for u in free:
            so = u['stats_override']
            for k in ('atk', 'hp', 'def'):
                so[k] = round(so[k] * f)


def myinfo_party(content, order, lead, path):
    """Read the private input in place; return only derived simulation inputs."""
    from battlesim.starsavior.myinfo_stats import final_stats, rule_for_content
    rule = rule_for_content(content)
    if rule is None:
        raise ValueError('No myinfo rule for content: ' + content)
    with open(path, encoding='utf-8-sig') as f:
        info = json.load(f)
    if info.get('format') != 'ss-myinfo-v1':
        raise ValueError('Expected ss-myinfo-v1')
    with open(os.path.join(ROOT, 'data', 'growth.json'), encoding='utf-8') as f:
        growth = json.load(f)
    with open(os.path.join(ROOT, 'data', 'saviors_index.json'), encoding='utf-8') as f:
        index = json.load(f)
    ids = {v['key']: int(k) for k, v in index.items() if not k.startswith('_') and v.get('key')}
    from battlesim.starsavior.data import get_db    # 시뮬 DB 키가 가이드 색인 키와 다른 구원자(예: amora = source-1058)도 받는다
    for k, u in get_db().units.items():
        ids.setdefault(k, int(u['id']))
    owned = {u['id']: u for u in info['units']}
    so = [order[1], order[2], order[0], order[3]]
    units, diagnostics = [], {}
    for key in so:
        uid = ids.get(key)
        if uid not in owned or str(uid) not in growth['units']:
            raise ValueError('Missing myinfo/growth unit: ' + key)
        result = final_stats(owned[uid], info, growth, rule)
        units.append(dict(key=key, build='none', stats_override=result['stats'],
                          stats_final=True, power=result['power'], myinfo_combat=result['combat']))
        diagnostics[key] = dict(missing=result['missing'], build_mismatch=result.get('build_mismatch', False))
    return dict(units=units, leader=so.index(lead) if lead in so else None), dict(rule=rule, units=diagnostics)


def turn_comparison(dealt, taken, turn, sim_dealt, sim_taken, ally, enemy):
    """TURN is all selected unit turns, excluding out-of-turn skill casts.

    The real ally share is unknown. Its estimate uses the simulation's share;
    this is a diagnostic assumption, not an observed action count.
    """
    total = ally + enemy
    share = ally / total if total else 0.0
    estimated = turn * share
    real_rate = dealt / estimated if estimated else None
    sim_rate = sim_dealt / ally if ally else None
    return dict(sim_total_actions=round(total, 3),
                sim_total_actions_vs_turn=total / turn if turn else None,
                sim_total_actions_minus_turn=total - turn,
                sim_ally_action_share=share, real_estimated_ally_actions=estimated,
                real_taken_per_global_turn=taken / turn if turn else None,
                sim_taken_per_global_turn=sim_taken / total if total else None,
                real_estimated_dealt_per_ally_action=real_rate,
                sim_dealt_per_ally_action=sim_rate,
                estimated_ally_damage_ratio=real_rate / sim_rate if sim_rate else None)


def run(name, runs=100, ov=None, seed=7, bs=False, myinfo=None, bs_name='큐브 과부하', bs_real=False):
    import gen_quick_calib as G
    from battlesim import quick, simulate
    ck, sk, order, lead, pw, rk, dealt, taken, turn, res = SAMPLES[name]
    diagnostics = None
    if myinfo is not None:
        spec, diagnostics = myinfo_party(ck, order, lead, myinfo)
    else:
        q, pen = quick.load(ROOT)
        st = q['st'][ck][sk]
        spec = G.party_spec(q, order, lead, list(order), pw / st['bp'], st)
        for u in spec['units']:
            if u['key'] in REAL:
                u['stats_override'] = dict(REAL[u['key']])
                u['stats_final'] = True      # 화면 값 = 최종값(상시 패시브 % 재적용 안 함)
        rebalance(spec, pw)
    opt = dict(G.SIMOPT, n_runs=runs, seed=seed, rekindle=rk)
    if bs:
        opt['break_skill'] = {'name': bs_name, 'level': 5 if bs is True else int(bs)}
    elif bs_real and name in BS_REAL:
        opt['break_skill'] = {'name': BS_REAL[name][0], 'level': BS_REAL[name][1]}
    opt['rules_override'] = dict(opt['rules_override'], nova_policy=NOVA_POLICY[name])
    opt['rules_override'].update(ov or {})  # --ov가 실측 운영 기본값보다 우선
    tab, nm = sk.split('|', 1)
    if myinfo is not None:
        opt['build'] = 'none'
    from battlesim import api
    measured = defaultdict(float)
    enemy_skills = defaultdict(lambda: defaultdict(int))
    per_battle = []     # 판별 결과·전체 행동 수·보스 남은 생명력·먼저 쓰러진 구원자(분포 판정용)

    class MeasuredBattle(api.Battle):
        def apply_damage(self, a, v, dmg, kind, **kw):
            # 넘친 피해(오버킬): 엔진 집계(dmg·taken)는 빼지만 게임 결과 화면은 넣는다(18x2-b 준 피해 = 보스 HP + 8,875).
            # 집계 의미는 그대로 두고 대조용으로만 따로 센다. 다른 감사 도구가 Battle.apply_damage 를 바꿔 끼우므로 인자는 그대로 넘긴다
            if v.dead or dmg <= 0:
                return super().apply_damage(a, v, dmg, kind, **kw)
            taken0 = v.taken
            died = super().apply_damage(a, v, dmg, kind, **kw)
            if died:
                # 넘친 양 = 들어온 피해 - 실제 집계 증가분(사망 정리로 지워지는 보호막에 영향받지 않게 taken 증가분으로)
                over = max(0.0, dmg - (v.taken - taken0))
                if v.side == 0:
                    measured['overkill_taken'] += over          # 받은 피해 합(t)은 출처와 무관하게 v.taken 이라 전부
                elif a is not None and a.side == 0:
                    measured['overkill_dealt'] += over          # 준 피해 합(d)은 구원자 a.dmg 만(브레이크 피해 a=None 제외)
            return died

        def act(self, u):
            r = super().act(u)
            order = self.__dict__.setdefault('_down', [])
            for v in self.allies:
                if v.dead and v.name not in order:
                    order.append(v.name)
            return r

        def run(self):
            super().run()
            bosses = [u for u in self.all_foes if u.d.boss and not u.summoned]
            boss_left = sum(max(0.0, u.hp) for u in bosses) / sum(u.maxhp for u in bosses) if bosses else None
            down = self.__dict__.get('_down', [])
            per_battle.append(dict(result=self.result, actions=sum(u.actions for u in self.allies) + sum(u.actions for u in self.all_foes),
                                   boss_left=boss_left, progress=self.progress(), first_down=down[0] if down else None))
            measured['ally'] += sum(u.actions for u in self.allies)
            measured['boss'] += sum(u.actions for u in self.all_foes if u.d.boss)
            measured['enemy'] += sum(u.actions for u in self.all_foes)
            for u in self.all_foes:
                for slot, count in u.cast_count.items():
                    enemy_skills[u.name][slot] += count
            return self

    with patch.object(api, 'Battle', MeasuredBattle):
        r = simulate(spec, {'stage': '%s/%s/%s' % (ck, tab, nm)}, opt)
    d = sum(v['dmg'] for v in r['per_unit'].values())
    t = sum(v['dmg_taken'] for v in r['per_unit'].values())
    acts = measured['ally'] / runs
    ok_d, ok_t = measured['overkill_dealt'] / runs, measured['overkill_taken'] / runs
    return dict(stage=name, runs=runs, seed=seed, real_ratio=round(dealt / taken, 2), sim_ratio=round(d / max(1.0, t), 2), sim_clear=r['outcome']['clear_p'],
                **turn_comparison(dealt, taken, turn, d, t, acts, measured['enemy'] / runs),
                real=res, real_turn=turn, real_extra=REAL_EXTRA.get(name), sim_ally_actions=round(acts, 1), foe_breaks=r['breaks']['foe'], ally_breaks=r['breaks']['ally'],
                sim_boss_actions=round(measured['boss'] / runs, 2), sim_enemy_actions=round(measured['enemy'] / runs, 2),
                enemy_skills={k: {s: round(n / runs, 3) for s, n in v.items()} for k, v in enemy_skills.items()},
                sim_dealt=d, sim_taken=t, party_power=r['party']['power'], myinfo=diagnostics,
                party_penalty=r['party']['penalty'],
                per_unit={k: {f: v[f] for f in ('dmg', 'dmg_taken', 'actions')} for k, v in r['per_unit'].items()},
                break_skill=r['break_skill'], nova_policy=opt['rules_override']['nova_policy'],
                nova_burst=r['nova_burst'], heal=sum(v['heal'] for v in r['per_unit'].values()),
                healing={nm: dict(heal=v['heal'], shield=v['shield']) for nm, v in r['per_unit'].items()},
                dist=distribution(per_battle, res, turn),
                # 오버킬 포함 대조(게임 결과 화면 기준). 받은 피해 쪽 포함은 준 피해 쪽 증거에서의 대칭 가정(assumed)
                sim_overkill_dealt=round(ok_d), sim_overkill_taken=round(ok_t),
                dealt_ratio_with_overkill=round((d + ok_d) / dealt, 3) if dealt else None,
                taken_ratio_with_overkill=round((t + ok_t) / taken, 3) if taken else None)


def _q(xs, ps=(0.1, 0.5, 0.9)):
    """분위수(최근접 순위). 빈 목록은 None."""
    if not xs:
        return None
    xs = sorted(xs)
    return [round(xs[min(len(xs) - 1, int(p * len(xs)))], 3) for p in ps]


def distribution(per_battle, real_result, real_turn):
    """판별 분포: 결과 비율, 전체 행동 수(TURN 대응) 분위수, 보스 남은 생명력, 먼저 쓰러진 구원자 비율.
    real_turn_pct = 실측과 같은 결과(클리어/실패) 판들 중 행동 수가 실측 TURN 이하인 비율 — 0.05 미만·0.95 초과면 실측이 시뮬 분포 바깥."""
    n = len(per_battle)
    res = defaultdict(int)
    for b in per_battle:
        res[b['result']] += 1
    won = real_result == 'clear'
    same = [b for b in per_battle if (b['result'] == 'clear') == won]
    first = defaultdict(int)
    for b in per_battle:
        if b['first_down']:
            first[b['first_down']] += 1
    lost = [b for b in per_battle if b['result'] != 'clear']
    return dict(n=n, result={k: round(v / n, 3) for k, v in res.items()} if n else {},
                actions_q10_50_90=_q([b['actions'] for b in per_battle]),
                same_result_runs=len(same),
                real_turn_pct=round(sum(1 for b in same if b['actions'] <= real_turn) / len(same), 3) if same else None,
                boss_left_q10_50_90_when_lost=_q([b['boss_left'] for b in lost if b['boss_left'] is not None]),
                progress_q10_50_90_when_lost=_q([b['progress'] for b in lost]),
                no_death_rate=round(sum(1 for b in per_battle if not b['first_down']) / n, 3) if n else None,
                first_down={k: round(v / n, 3) for k, v in sorted(first.items(), key=lambda kv: -kv[1])})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=100)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--ov', type=json.loads)
    p.add_argument('--only', choices=SAMPLES)
    p.add_argument('--bs', nargs='?', const=True, default=False, type=int, metavar='LEVEL', help='큐브 과부하 레벨(생략 시 5)')
    p.add_argument('--bs-name', default='큐브 과부하', help='--bs 로 장착할 브레이크 스킬 이름')
    p.add_argument('--bs-real', action='store_true', help='샘플별 실제 장착(BS_REAL) 사용')
    p.add_argument('--myinfo', metavar='PATH', help='Private ss-myinfo-v1 file (no default)')
    p.add_argument('--include-old', action='store_true', help='패치 전 실측(PRE_PATCH)도 돌린다')
    args = p.parse_args()
    if args.runs < 1:
        p.error('--runs must be positive')
    low_priority()
    for name in SAMPLES:
        if args.only and name != args.only:
            continue
        if name in PRE_PATCH and not args.only and not args.include_old:
            continue
        out = run(name, args.runs, args.ov, args.seed, args.bs, args.myinfo, args.bs_name, args.bs_real)
        if name in PRE_PATCH:
            out['pre_patch'] = PRE_PATCH[name]
        print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
