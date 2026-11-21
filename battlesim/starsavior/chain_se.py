"""Native grouping metadata for verified chain SE lines (PC 26752678)."""
from .. import datafile


def _raw():
    return datafile.load('chain_se')


@datafile.cached
def data():
    """구원자 연쇄(크리스텔·아세라). round2 범위."""
    return {key: {(slot, text): spec for slot, text, spec in rows} for key, rows in _raw()['units'].items()}


@datafile.cached
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
