"""Build only the ready sprite; reuse the existing Gwen art pipeline.

python -B -X utf8 tools/gwen_art/build_ready.py --import-file <generated.png>
python -B -X utf8 tools/gwen_art/build_ready.py
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from build import NAMES, OUT, RESAMPLE, ROOT, master
from build2 import encode, move_part


def compact_master(src):
    # Give flat interior colors their own palette; reserve 64 entries for alpha
    # edges so transparency does not consume the interior's color budget.
    opaque = src.convert('RGB').quantize(
        colors=192, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    edge = src.copy()
    edge.putalpha(src.getchannel('A').point(lambda a: 0 if a >= 250 else a))
    edge = edge.quantize(colors=64, method=Image.Quantize.FASTOCTREE,
                         dither=Image.Dither.NONE)
    result = Image.new('P', src.size)
    result.putdata([
        o if a >= 250 else 192 + e
        for o, e, a in zip(opaque.get_flattened_data(), edge.get_flattened_data(),
                           src.getchannel('A').get_flattened_data())
    ])
    result.putpalette(opaque.getpalette('RGBA')[:192 * 4]
                      + edge.getpalette('RGBA')[:64 * 4], rawmode='RGBA')
    return result


def compare(frames):
    sheet = Image.new('RGB', (1320, 670), '#edf0f5')
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate((*NAMES, 'ready')):
        x = i * 220
        src = Image.open(OUT / (name + '_512.png')).convert('RGBA')
        draw.text((x + 16, 16), name, fill='#192239')
        pic = src.resize((220, 220), RESAMPLE)
        sheet.paste(pic, (x, 40), pic)
        draw.rectangle((x, 280, x + 219, 465), fill='#111b30')
        pic = src.resize((140, 140), RESAMPLE)
        sheet.paste(pic, (x + 40, 300), pic)
        draw.text((x + 16, 478), '140px / dark UI', fill='#192239')
    draw.text((16, 525), 'ready: one-shot hand gesture / 160px frames', fill='#192239')
    for i, frame in enumerate(frames):
        pic = frame.resize((120, 120), RESAMPLE)
        sheet.paste(pic, (440 + i * 140, 535), pic)
    path = ROOT / '_tmp/_art_ready_compare.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-file', type=Path)
    args = parser.parse_args()
    path = OUT / 'ready_512.png'
    if args.import_file:
        # Match the existing set's approximately 450px occupied height.
        raw = Image.open(args.import_file).convert('RGBA')
        raw.putalpha(raw.getchannel('A').point(
            lambda a: 0 if a < 10 else 255 if a > 245 else a))
        raw = raw.crop(raw.getchannel('A').getbbox())
        raw.thumbnail((450, 450), RESAMPLE)
        normalized = Image.new('RGBA', (464, 464))
        normalized.alpha_composite(raw, ((464 - raw.width) // 2, 10))
        temp = ROOT / '_tmp/ready_normalized.png'
        temp.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(temp)
        src = master(temp)
        # Indexed PNG retains transparency while meeting the master size budget.
        compact_master(src).save(path, optimize=True)
    src = Image.open(path).convert('RGBA')
    assert src.size == (512, 512)
    assert src.getchannel('A').getextrema() == (0, 255)
    # Coordinates are fitted to the approved generated ready master.
    polygon = [(80, 319), (158, 319), (185, 340), (180, 357),
               (165, 370), (155, 405), (80, 405)]
    frames = move_part(src, polygon, [0, -4, 3, 0], (166, 330))
    assert ImageChops.difference(frames[0], frames[1]).getbbox()
    assert frames[0].tobytes() == frames[-1].tobytes()
    served = encode('ready', frames, 160, [300, 200, 200, 300], 1)
    sizes = {}
    for name in ('ready_512.png', 'ready.png', 'ready.webp'):
        output = OUT / name
        assert output.stat().st_size <= 80000, output
        with Image.open(output) as im:
            assert im.convert('RGBA').getchannel('A').getextrema() == (0, 255)
            if name.endswith('.webp'):
                assert im.n_frames == 4 and im.info['loop'] == 1
                for i in range(im.n_frames):
                    im.seek(i)
                    im.load()
        sizes[name] = output.stat().st_size
    compare(served)
    print(json.dumps(sizes, indent=2))


if __name__ == '__main__':
    main()
