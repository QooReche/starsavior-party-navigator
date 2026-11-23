"""Build three coat-off office Gwen stills; no screen integration or animation.

python -B -X utf8 tools/gwen_art/build_recon.py --import-dir <generated PNG folder>
python -B -X utf8 tools/gwen_art/build_recon.py
"""
import argparse
from pathlib import Path

from PIL import Image

from build import OUT, RESAMPLE
from build2 import BUDGET
from build_ready import compact_master

NAMES = ('recon_look', 'recon_pin', 'recon_nod')


def import_master(path):
    raw = Image.open(path).convert('RGBA')
    assert raw.getchannel('A').getextrema() == (0, 255), 'Real alpha required'
    # Same cleanup thresholds as ready/forced art; preserve soft edge alpha.
    raw.putalpha(raw.getchannel('A').point(
        lambda a: 0 if a < 10 else 255 if a > 245 else a))
    raw = raw.crop(raw.getchannel('A').getbbox())
    raw.thumbnail((450, 450), RESAMPLE)
    master = Image.new('RGBA', (512, 512))
    master.alpha_composite(raw, ((512 - raw.width) // 2, 482 - raw.height))
    return compact_master(master)


def validate(path, size):
    with Image.open(path) as image:
        assert image.size == (size, size) and image.n_frames == 1, path
        alpha = image.convert('RGBA').getchannel('A')
        assert alpha.getextrema() == (0, 255), path
        assert any(0 < a < 255 for a in alpha.get_flattened_data()), path
        x0, y0, x1, y1 = alpha.getbbox()
        assert 0 < x0 < x1 < size and 0 < y0 < y1 < size, path
    assert path.stat().st_size <= BUDGET['file_bytes'], path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-dir', type=Path)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        master_path = OUT / (name + '_512.png')
        if args.import_dir:
            import_master(args.import_dir / (name + '.png')).save(
                master_path, optimize=True)
        validate(master_path, 512)
        small = Image.open(master_path).convert('RGBA').resize((160, 160), RESAMPLE)
        # Existing 160px still encoding: quantize RGB, retain original alpha.
        png = small.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                             dither=Image.Dither.NONE).convert('RGBA')
        png.putalpha(small.getchannel('A'))
        path = OUT / (name + '.png')
        png.save(path, optimize=True)
        validate(path, 160)
        print(f'{name}: master {master_path.stat().st_size:,} B / still {path.stat().st_size:,} B')
    served = sum(p.stat().st_size for p in OUT.iterdir()
                 if p.suffix in ('.png', '.webp') and not p.stem.endswith('_512'))
    assert served <= BUDGET['served_bytes'], served
    print(f'Served art total: {served:,} / {BUDGET["served_bytes"]:,} B')


if __name__ == '__main__':
    main()
