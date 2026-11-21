"""Native grouping metadata for verified chain SE lines (PC 26752678)."""
from functools import lru_cache
import json
from pathlib import Path
from .data import SRC


@lru_cache(maxsize=1)
def data():
    raw = json.loads((Path(SRC) / 'data/chain_se.json').read_text(encoding='utf8'))['units']
    return {key: {(slot, text): spec for slot, text, spec in rows} for key, rows in raw.items()}


def spec(owner, line):
    if line is None:
        return None
    return data().get(owner.key, {}).get((line.slot, line.raw))
