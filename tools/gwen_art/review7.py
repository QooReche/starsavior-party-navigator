"""480px sleeve audit of all 13 portraits, every WebP frame and blink."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import build5

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'_tmp/art7'
NAMES = ('confident', 'thoughtful', 'notes') + build5.NAMES


def row(name, folder, label):
    result = Image.new('RGB', (2400, 530), '#182238')
    draw = ImageDraw.Draw(result)
    draw.text((8, 5), name+' | '+label+' | 480px (2x); all sleeves, ALL WebP frames', fill='white')
    column = 0
    for suffix in ('.png', '.webp', '_blink.png'):
        path = folder/(name+suffix)
        if not path.exists():
            continue
        with Image.open(path) as im:
            for i in range(im.n_frames):
                im.seek(i)
                pic = im.convert('RGBA').resize((480, 480), Image.Resampling.LANCZOS)
                result.paste(pic, (column*480, 25), pic)
                draw.text((column*480+8, 510), suffix+(f' F{i}' if suffix=='.webp' else ''), fill='white')
                column += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after', action='store_true')
    args = parser.parse_args()
    rows = []
    for name in NAMES:
        before = row(name, WORK/'before', 'BEFORE')
        before.save(WORK/(name+'-before.png'))
        rows.append(before)
        if args.after:
            after = row(name, build5.OUT, 'AFTER')
            after.save(WORK/(name+'-after.png'))
            rows.append(after)
            pair = Image.new('RGB', (2400, 1060))
            pair.paste(before, (0, 0)); pair.paste(after, (0, 530))
            pair.save(WORK/(name+'-comparison.png'))
    sheet = Image.new('RGB', (2400, 530*len(rows)), '#182238')
    for i, pic in enumerate(rows):
        sheet.paste(pic, (0, i*530))
    path = ROOT/('_tmp/_art_sleeve7_after.png' if args.after else '_tmp/_art_sleeve7.png')
    sheet.save(path)
    print(path)


if __name__ == '__main__':
    main()
