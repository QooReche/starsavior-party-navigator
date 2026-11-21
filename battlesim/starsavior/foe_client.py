"""Audited PC fields missing from the old guild description adapter."""
import json
import copy
import re
from functools import lru_cache
from pathlib import Path
from .data import SRC


@lru_cache(maxsize=1)
def data():
    return json.loads((Path(SRC) / 'data/foe_client.json').read_text(encoding='utf-8'))


def attach(definition):
    d = data()
    rules = d['units'].get(definition.name, {})
    definition.client_sequential_events = rules.get('sequential_events', [])
    for name, info in d['buffs'].items():
        for ln in definition.lines:
            if ln.eff.get('name') == name:
                definition.effect_info.setdefault(name, {}).update(info, client_1121=True)
                ln.eff['client_1121'] = True
                if info.get('next_turn_catch'):
                    ln.eff['next_turn_catch'] = True
    definition.client_named_skills = {}
    for name, meta in rules.get('skills', {}).items():
        if name not in definition.client_cards:
            continue
        original, lines = definition.client_cards[name]
        sk = copy.copy(original)
        sk.slot = meta['slot']
        sk.client_1121 = True
        sk.client_auto = meta.get('auto', [])
        sk.client_reset_cd = meta['reset_cd']
        sk.semantic_lines = []
        for ln in lines:
            ln = copy.copy(ln)
            ln.slot = sk.slot
            normalize(ln, rules)
            sk.semantic_lines.append(ln)
        definition.client_named_skills[name] = sk
    for ln in definition.lines:
        normalize(ln, rules)
    for slot in list(definition.trigger_skills):
        sk = definition.trigger_skills[slot]
        if slot.startswith('변형 ') and sk.name in definition.client_named_skills:
            del definition.trigger_skills[slot]
    return {slot: rules['react'][sk.name] for slot, sk in definition.trigger_skills.items()
            if sk.name in rules.get('react', {})}


def normalize(ln, rules):
    if (rules.get('local_damage_only') is not None and '자신에게 능력치 보정 피해 증가' in ln.raw
            and '연쇄 피해 =' in ln.raw and '{이번 스킬에만 적용}' in ln.raw):
        ln.eff = dict(kind='local', stat='피해 증가', val=rules['local_damage_only'], requires_foe_client=True)
    change = re.search(r'스킬 교체: 「([^」]+)」 → 「([^」]+)」', ln.raw)
    if change and list(change.groups()) in rules.get('changes', []):
        ln.eff = dict(kind='foe_change_skill', before=change[1], after=change[2])
    if '정실 어필' in rules.get('skills', {}) and ln.raw == '[스킬 사용 후] 자신에게 (약화효과 해제) 행동 게이지 0%':
        # SE330018206 is DELETEDEBUFF. SpeedGaugeRate=0 is unused by this buff type.
        ln.eff = dict(kind='foe_cleanse')
