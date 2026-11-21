"""Audited PC fields missing from the old guild description adapter."""
import json
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
    return {slot: rules['react'][sk.name] for slot, sk in definition.trigger_skills.items()
            if sk.name in rules.get('react', {})}
