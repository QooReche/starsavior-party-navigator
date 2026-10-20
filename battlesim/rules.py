# -*- coding: utf-8 -*-
"""전투 규칙 상수·가정. 불확실하거나 바뀌기 쉬운 수치는 rules/default.json(항목마다 value·grade·note)에서 읽는다.

엔진은 `from .rules import BASE_MULT` 처럼 값을 복사해 쓰므로, 실행 중에 바꾸려면 쓰는 모듈(battlesim.engine)의 이름을 바꿔야 한다.
DEFAULT_OPTS 는 dict 하나를 공유하므로 이 모듈의 DEFAULT_OPTS 를 제자리에서 고치면 엔진에도 반영된다."""
import json
import os

RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rules')


def load_rules(profile='default'):
    with open(os.path.join(RULES_DIR, profile + '.json'), encoding='utf-8') as f:
        return json.load(f)


RULES = load_rules()
_F = {k: v['value'] for k, v in RULES['formula'].items()}
_O = {k: v['value'] for k, v in RULES['opts'].items()}

BASE_MULT = _F['BASE_MULT']            # 피해식 상수 (databook 계산기)
DEF_K = _F['DEF_K']                    # 방어율 = def/(def+3000) (PvE)
AOE_DIV = _F['AOE_DIV']                # 전체 대상 스킬은 /4 (대상 1명당)
TICK_PER_TURN = _F['TICK_PER_TURN']    # 속도 100 유닛이 1턴(=1라운드)에 한 번 행동하는 틱 수
INF_HP = 1e15
COOP_CAP = _F['COOP_CAP']              # stat.cap.NST_RATE_CROSS_ATTACK = 3000 (협공 확률 상한 30%)

ASSUMPTIONS = {
    'level': 'Lv200 고정, 공명 10단계 (코스모 게이트/플래시 포인트/랭크전 고정 조건). 각인(star)=0 기본, 인자로 0~7 변경.',
    'equipment': '장비/아르카나/잠재력 제외 (gear 훅으로 확장 가능).',
    'skill_level': '모든 스킬 최대 레벨 (ef 줄은 최대 레벨 기준, 쿨타임은 cdm(최대 레벨) 우선).',
    'damage_formula': '기본피해=(공격력x계수+생명력x계수+방어력x계수)x(1+속도/100x계수)x1.85, 전체공격 /4, x(1-방어율), x(1+증가합-감소합+치명확률x치명피해). 난수는 평균(1.0) 사용.',
    'enemy_ref': '지표용 기준 적: 방어력 1400(코스모 2단계 수준), 속도 100, 속성 없음(상성 0), 약화/브레이크 없음, HP 무한.',
    'single': '단일 시나리오 = 적 1체. 단일 스킬은 그 1체, 전체 스킬은 대상 1명당 cf/4 만 들어감.',
    'aoe': '광역 시나리오 = 적 3체(총합 피해). 단일 스킬은 1체만, 전체 스킬은 3체 각각 cf/4.',
    'turn': '1턴 = 속도 100 유닛이 1회 행동하는 기간(100틱). N턴 = N*100틱. 게이지 시작 0, 쿨타임 시작은 만충(cd 턴 후 첫 사용).',
    'ai': '스킬 선택은 궁극기 > 특수기 > 기본기 중 쿨타임이 찬 것 (자동 전투 가정).',
    'buff_duration': 'N턴 버프는 버프 보유자의 행동 N회 동안 유지 (자기가 건 버프는 건 행동 다음 행동부터 카운트).',
    'allies_solo': '개인 지표는 속성 없는 더미 딜러 3명(기본기/특수기/궁극기 순환, 속도 100)과 함께 계산: 아군 공격 트리거를 받되 버프는 주지 않음.',
    'conditions': '조건은 확률 가중(기대값). 스택은 실수 스택. 해석 못 한 조건 키는 0.5 가중(unknown_cond_p) 후 unmodeled 에 기록.',
    'debuff': '디버프 성공률 0.9 가정(효과 적중-저항 판정은 적 저항을 몰라 상수).',
    'not_modeled': '반응(피격/회피/수호) 트리거 스킬, 변형(교체) 스킬, 무작위 효과, 브레이크(강인도), 카운터(+10%), 힐/보호막, 협공(확률 스탯만 단순 반영), 적 공격/피해 감소.',
    'nova': '노바 포스는 구원자 개인 단위로 모아 4개면 다음 스킬 피해 +15% (팀 공용 여부는 미확인 추정).',
}

ELEM_BEATS = {'태양': '별', '별': '달', '달': '태양', '질서': '혼돈', '혼돈': '질서'}
ELEM_LOSES = {'태양': '달', '별': '태양', '달': '별'}   # 질서/혼돈은 서로 유리만 (불리 없음 추정)
FOE_ELEM = {'sun': '태양', 'moon': '달', 'star': '별', 'order': '질서', 'chaos': '혼돈'}
KNOWN_DOT = {'연소': ('atk', 0.20), '출혈': ('atk', 0.25), '빙결': ('atk', 0.15), '중독': ('hp', 0.05)}
# 키 순서는 원본 그대로 유지(damage_index.json _meta.opts 출력 순서가 같아야 함). enemy_element 는 시나리오 값이라 규칙 파일에 두지 않는다.
DEFAULT_OPTS = dict(
    unknown_cond_p=_O['unknown_cond_p'], debuff_success=_O['debuff_success'], inf_hp_frac=_O['inf_hp_frac'],
    break_p=_O['break_p'], kill_p_inf=_O['kill_p_inf'],
    no_debuff_p=_O['no_debuff_p'], nova=_O['nova'], coop=_O['coop'], forced_coop=_O['forced_coop'],
    init_cd_frac=_O['init_cd_frac'], enemy_element=None,
    enemy_def=_O['enemy_def'], enemy_spd=_O['enemy_spd'], ref_enemy_count=_O['ref_enemy_count'],
)
