"""Whole-table potential adapters. Publish derived effects/IDs/names, never raw rows."""
from tools.build_foe_clash import Tables, SeConverter, Unconvertible, PHASE, STAT_LABEL


# NKM (26610546): 8009,8321,9052,16055,18101-18137.
COMBAT_STATS = {
    'NST_RATE_CROSS_ATTACK': '협공 확률',
    'NST_RATE_REVENGE_ATTACK': '반격 확률',
    'NST_RATE_PREEMPTIVE_DEFEND': '선제 방어 확률',
    'NST_RATE_DAMAGE_VAMPIRISM': '피해 흡혈',
    **{f'NST_RATE_DAMAGE_{kind}_SKILL_{slot}': f'{name} 피해 {label}'
       for kind, label in [('UP', '증가'), ('REDUCE', '감소')]
       for slot, name in [('ATTACK', '기본기'), ('SPECIAL', '특수기'), ('HYPER', '궁극기')]},
}


class PotentialConverter(SeConverter):
    phases = {**PHASE, 'NSEAT_BATTLE_START': '전투 시작 시',
              'NSEAT_TURN_START': '턴 시작 시', 'NSEAT_TURN_END': '턴 종료 시'}
    stat_labels = {**STAT_LABEL, **COMBAT_STATS, 'NST_RATE_CRITICAL_DAMAGE': '치명타 피해',
                   'NST_TURN_SPEED': '속도'}

    def cond_text(self, cid, phase_type):
        row = self.tb.cond.get(cid, {})
        self.cond_buffs = []
        # Exact shapes only. New fields fail closed in the base converter.
        # NKM.Templets:42260-42278,42357,42736-42762,43317-43337,43419.
        if row == {'Id': cid, 'AfterMyAction': {'SkillIndex': 'NSI_SKILL_1_ATTACK'}}:
            return '내 행동 후 [사용 스킬: 기본기]'
        if row == {'Id': cid, 'AfterMyAttack': {'DamageResultType': ['CriticalHit']}}:
            return '내 공격 후 [결과: 치명타]'
        if row == {'Id': cid, 'AfterMyAttack': {'IsNotTargetSuperArmor': True}}:
            return '내 공격 후 [대상 강인도 없음: 예]'
        body = row.get('MyEffectiveHit', {})
        if (set(row) == {'Id', 'MyEffectiveHit'} and set(body) == {'SelfNegativeBuff', 'BuffCountOver'}
                and body['SelfNegativeBuff'] is True):
            return '내가 피격될 때 [자신 약화효과 보유: 예; 효과 개수 이상: %d]' % body['BuffCountOver']
        return super().cond_text(cid, phase_type)

    def props_text(self, stats):
        # BI_STAT_* SE VALUE overrides the numeric value of the buff's RATE stat;
        # its unit comes from the base stat (NKM.Templets:38622-38648;
        # Star.Templets:29275). RATE/VALUE both load the same integer.
        normalized = [(k, 'RATE' if k.startswith(('NST_RATE_', 'NST_NV_RATE_')) else kind, v)
                      for k, kind, v in stats]
        return super().props_text(normalized)


def catalog_tables(static):
    return Tables(static)


def names(load, tb):
    return {str(p['PotenId']): tb.ko(p['PotenName']) for p in load('SE_POTENTIAL_TEMPLET')}


def arcana_unique(load, tb):
    """Distinct from learned PotenId: unique promote is a journey bonus."""
    promotes = {r['PromoteId']: r for r in load('ARCANA_PROMOTE_TEMPLET')}
    groups = {}
    for r in load('ARCANA_PROMOTE_GROUP_TEMPLET'):
        groups.setdefault(r['PromoteGroupId'], set()).add(r['PromoteId'])
    out = {}
    known = {('PT_TRAINNING', 'TRAINING_INCREASE_VALUE_UP'), ('PT_TRAINNING_TAG', 'TRAINING_BONUS_TAG'),
             ('PT_TRAINNING', 'TRAINING_CONDITION_EFFICIENCY_UP'), ('PT_TRAINNING', 'TRAINING_VALUE_UP'),
             ('PT_REQUEST', 'REQUEST_REWARD_COIN_INCREASE'), ('PT_TRAINNING', 'TRAINING_BONUS_PP')}
    for u in load('ARCANA_UNIQUE_PROMOTE_TEMPLET'):
        uid = u['UniquePromoteId']
        p = promotes.get(uid, {})
        owners = [a for a in load('ARCANA_TEMPLET') if uid in groups.get(a['ArcanaPromoteGroupId'], set())]
        out[str(uid)] = dict(name=tb.ko(u['UniquePromoteTitle']),
                            arcanas={str(a['ArcanaId']): tb.ko(a['ArcanaName']) for a in owners},
                            status='journey' if owners and (p.get('PromoteActiveType'), p.get('PromoteValueType')) in known else 'unconfirmed')
    return out
