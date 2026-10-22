"""Publish only numeric item -> slot indices; never copy names or original rows."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--static', type=Path, default=Path(r'E:\AI_mk2\starsavior-static-data'))
    args = ap.parse_args()
    rows = json.loads((args.static / 'tables/EQUIP_ITEM_TEMPLET.json').read_text(encoding='utf8'))['Data']
    # Same order as public databook equip.adv.parts; names are never read here.
    slots = ['ET_WEAPON', 'ET_GLOVES', 'ET_ARMOR', 'ET_SHOES', 'ET_NECKLACE', 'ET_RING']
    result = {str(r['EquipItemId']): slots.index(r['EquipType']) for r in rows}
    (ROOT / 'data/myinfo_slots.json').write_text(json.dumps(result, separators=(',', ':')) + '\n', encoding='utf8')
    print('myinfo_slots.json:', len(result), 'numeric mappings')


if __name__ == '__main__':
    main()
