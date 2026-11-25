"""길드 지원 SE를 공통 실행 값으로 변환. 알 수 없는 연결은 추출 시 거부한다.

26752678 Star.Templets:16241 (시즌 SpecialBuff/NormalBuff), NKM:16374-16466
(조건/확률→SE 실행). 수치는 SE, 속성·지속·중첩은 BUFF_TEMPLET에서 읽는다.
"""
from tools.build_foe_clash import SeConverter
from tools.build_foe_auto import filters

PROPS = {
    'NST_NV_RATE_ATK': '공격력%', 'NST_NV_RATE_HP': '생명력%', 'NST_NV_RATE_DEF': '방어력%',
    'NST_NV_RATE_TURN_SPEED': '속도%', 'NST_RATE_CRITICAL': '치명타 확률',
    'NST_RATE_CRITICAL_DAMAGE': '치명타 피해', 'NST_RATE_EFFECT_HIT': '효과 적중',
    'NST_RATE_EFFECT_EVADE': '효과 저항', 'NST_RATE_EVADE': '회피율',
    'NST_RATE_REVENGE_ATTACK': '반격 확률', 'NST_RATE_DAMAGE_UP': '피해 증가',
    'NST_RATE_DAMAGE_REDUCE': '받는 피해 감소', 'NST_RATE_DAMAGE_UP_BREAK': '브레이크 대상 피해 증가',
    'NST_RATE_HEAL_GIVE': '주는 회복량', 'NST_RATE_DAMAGE_VAMPIRISM': '피해 흡혈',
}
SLOTS = {'NSI_SKILL_1_ATTACK':'기본기', 'NSI_SKILL_2_SPECIAL':'특수기', 'NSI_SKILL_3_HYPER':'궁극기'}


def compile_effect(r, tb):
    b = tb.buff[r['m_BuffStrID']]
    phase = r['m_Condition']['m_ActiveType']
    if phase not in ('NSEAT_BATTLE_START','NSEAT_TURN_START','NSEAT_SKILL_START','NSEAT_SKILL_END','NSEAT_DAMAGE_START','NSEAT_HIT'):
        raise ValueError('미지원 길드 지원 시점: ' + phase)
    cond = r['m_Condition']
    if set(cond) - {'m_ActiveType','m_fActiveRate','m_fHPRateOver','m_fHPRateLess'}:
        raise ValueError('미지원 지원 발동 조건: ' + str(cond))
    checks = {}
    if r.get('SkillConditionId'):
        c = dict(tb.cond[r['SkillConditionId']]); c.pop('Id')
        if len(c) != 1: raise ValueError(c)
        head, body = next(iter(c.items()))
        if head not in ('OnMyAttack','AfterMyNonAttack','MyEffectiveDamageStart'): raise ValueError(c)
        checks['event'] = head
        for k,v in body.items():
            if k not in ('SkillIndex','TargetNegativeBuff','SelfPositiveBuff','EnemyNegativeBuff','IsNotTargetSuperArmor'):
                raise ValueError('미지원 지원 스킬 조건: ' + k)
            checks[k] = v
    e = dict(op='stat', checks=checks, hpOver=cond.get('m_fHPRateOver'), hpLess=cond.get('m_fHPRateLess'),
             cooldown=r.get('SeCoolTurn',0), permanent=bool(b.get('TurnInfinite')), positive=bool(b.get('IsBuff')),
             fixed=bool(b.get('CanNotDispel')), buffCount=bool(b.get('PositiveBuffCount')))
    target = r.get('m_BuffTargetType')
    if target not in ('NSETT_SELF','NSETT_MYTEAM_ALL_NOT_SELF','NSETT_AUTO_ALLY_ONE'): raise ValueError(target)
    if target == 'NSETT_AUTO_ALLY_ONE':
        e['filters'] = filters(tb.auto_target[r['AutoTargetId']], {})
    stats = SeConverter(tb).stats_of(r)
    e['props'] = {}
    for k,ty,v in stats:
        if ty != 'RATE' or k not in PROPS: raise ValueError('미지원 지원 스탯: ' + k)
        e['props'][PROPS[k]] = v / 100
    if b.get('SkillCoolturnDown'):
        e.update(op='cooldown', value=r['SkillCoolturnDownValue'])
        if b.get('SkillCoolturnType'): e['slot'] = SLOTS[b['SkillCoolturnType']]
    elif b.get('SpeedGaugeUp'): e.update(op='gauge', value=r['SpeedGaugeRate'])
    elif b.get('NovaForceUp'): e.update(op='nova', value=r['NovaForceValue'])
    elif b.get('EnforceSkill'):
        e.update(op='enforce', slot=SLOTS[r['EnforceSkillIndex']], enforceFilters=filters(tb.auto_target[r['EnforceAutoTargetId']],{}))
    elif b.get('Barrier'):
        if r['BarrierTargetType'] != 'NSETT_SELF' or r['BarrierStatType'] != 'NST_HP': raise ValueError(r['m_SEStrID'])
        e.update(op='barrier', value=r['BarrierRate']/100)
    elif not stats: raise ValueError('미해석 지원: ' + r['m_SEStrID'])
    return e
