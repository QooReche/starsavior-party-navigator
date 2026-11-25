"""PC base HIT/EVADE joined by exact public name and base-stat fingerprint."""
import json
from .. import datafile
from ..fileio import short_hash


def signature(name, base):
    """이름 + 기본 능력치 지문(tools/build_hit_stats.py 가 같은 함수로 열쇠를 만든다)."""
    return short_hash(json.dumps([name, base], ensure_ascii=False, separators=(',', ':')), 20)


def data():
    return datafile.load('hit_stats')['units']


def rates(raw, unit, variant):
    key = signature(unit['n'], unit['b'])
    # Custom raw fixtures may explicitly supply rates. Public definitions must
    # be verified by the builder; do not silently use another unit's stats.
    mapped_hit, mapped_evade = data().get(key, (10000, 0))
    # 클라 직행 조각의 명시 값은 옛 데이터북 지문 매핑보다 우선한다.
    hit, evade = unit.get('hit', mapped_hit), unit.get('evade', mapped_evade)
    for index, value in (variant or {}).get('a', []):
        stat = raw['ak'][index][1]
        if stat == 'NST_RATE_HIT': hit += value
        elif stat == 'NST_RATE_EVADE': evade += value
    return hit, evade
