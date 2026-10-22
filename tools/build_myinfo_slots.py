"""Publish only numeric item -> slot indices; never copy names or original rows."""
import sys
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.runtime import static_path, low_priority
from battlesim.fileio import atomic_text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path)
    args = ap.parse_args()
    try:
        args.static = static_path(args.static)
    except ValueError as ex:
        ap.error(str(ex))
    low_priority()
    rows = json.loads((args.static / 'tables/EQUIP_ITEM_TEMPLET.json').read_text(encoding='utf8'))['Data']
    # Same order as public databook equip.adv.parts; names are never read here.
    slots = ['ET_WEAPON', 'ET_GLOVES', 'ET_ARMOR', 'ET_SHOES', 'ET_NECKLACE', 'ET_RING']
    result = {str(r['EquipItemId']): slots.index(r['EquipType']) for r in rows}
    atomic_text(ROOT / 'data/myinfo_slots.json', json.dumps(result, separators=(',', ':')) + '\n')
    print('myinfo_slots.json:', len(result), 'numeric mappings')


if __name__ == '__main__':
    main()
