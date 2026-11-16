"""Rebuild official-style portraits with local sleeve repairs and original faces.

Default rebuild uses committed masters and art6/art7 sleeve patches, no generation API.
--import-dir accepts the selected normalized 320px master sheets.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
import build2
import build5
import sleeve7

HERE = Path(__file__).resolve().parent
LEGACY = ('confident', 'thoughtful', 'notes')


def build():
    for name in LEGACY:
        parts = build2.cells(Image.open(build2.MASTERS/(name+'.webp')).convert('RGBA'), 2)
        parts = sleeve7.apply(name, parts)
        build2.encode(name, [parts[0], parts[1], parts[0]], 240, [450, 220, 330], 1)
    build5.build()
    build5.validate_outputs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-dir', type=Path)
    args = parser.parse_args()
    if args.import_dir:
        for name in LEGACY + tuple(n for n in build5.NAMES if n != 'st_cry'):
            target = (build2.MASTERS if name in LEGACY else build5.MASTERS)/(name+'.webp')
            build5.save_master(Image.open(args.import_dir/(name+'.png')).convert('RGBA'), target)
    build()
    served = [p for p in build2.OUT.iterdir() if p.suffix in ('.png', '.webp') and not p.stem.endswith('_512')]
    print(json.dumps({'served_bytes': sum(p.stat().st_size for p in served),
                      'largest_served': max(p.stat().st_size for p in served)}, indent=2))


if __name__ == '__main__':
    main()
