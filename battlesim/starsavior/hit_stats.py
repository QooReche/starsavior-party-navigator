"""PC base HIT/EVADE joined by exact public name and base-stat fingerprint."""
import hashlib
import json
from .. import datafile


def signature(name, base):
    return hashlib.sha256(json.dumps([name, base], ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()[:20]


def data():
    return datafile.load('hit_stats')['units']


def rates(raw, unit, variant):
    key = signature(unit['n'], unit['b'])
    # Custom raw fixtures may explicitly supply rates. Public definitions must
    # be verified by the builder; do not silently use another unit's stats.
    hit, evade = data().get(key, (unit.get('hit', 10000), unit.get('evade', 0)))
    for index, value in (variant or {}).get('a', []):
        stat = raw['ak'][index][1]
        if stat == 'NST_RATE_HIT': hit += value
        elif stat == 'NST_RATE_EVADE': evade += value
    return hit, evade
