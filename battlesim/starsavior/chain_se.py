"""Native grouping metadata for verified chain SE lines (PC 26752678)."""
from functools import lru_cache
import json
from pathlib import Path
from .data import SRC


@lru_cache(maxsize=1)
def _raw():
    return json.loads((Path(SRC) / 'data/chain_se.json').read_text(encoding='utf8'))


@lru_cache(maxsize=1)
def data():
    """구원자 연쇄(크리스텔·아세라). round2 범위."""
    return {key: {(slot, text): spec for slot, text, spec in rows} for key, rows in _raw()['units'].items()}


@lru_cache(maxsize=1)
def foes():
    """적 정의 연쇄(tools/build_chain_se.py build_foes)."""
    return {key: {(slot, text): spec for slot, text, spec in rows} for key, rows in _raw().get('foes', {}).items()}


def fixed(name):
    """엔진 고정 피해·응징 예약의 원형 BuffId(belgras_hyper, cosmo_punish)."""
    return _raw()['fixed'][name]


def spec(owner, line, foe=False):
    if line is None:
        return None
    hit = data().get(owner.key, {}).get((line.slot, line.raw))
    if hit is None and foe:
        hit = foes().get(owner.key, {}).get((line.slot, line.raw))
    return hit
