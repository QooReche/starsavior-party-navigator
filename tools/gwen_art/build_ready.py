"""Build only the ready sprite; reuse the existing Gwen art pipeline.

python -B -X utf8 tools/gwen_art/build_ready.py --import-file <generated.png>
python -B -X utf8 tools/gwen_art/build_ready.py
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from build import NAMES, OUT, RESAMPLE, ROOT, master
from build2 import encode

DURATIONS = [300, 200, 200, 300]


def ready_frames(src):
    # Only the exposed wrist/glove extends toward screen right. The left edge
    # stays anchored to the sleeve; hair, face and body stay pixel-identical.
    box = (354, 254, 440, 316)
    hand = src.crop(box)
    frames = []
    for dx in (0, 5, 9, 0):
        frame = src.copy()
        if dx:
            frame.paste((0, 0, 0, 0), box)
            frame.alpha_composite(
                hand.resize((hand.width + dx, hand.height), RESAMPLE), box[:2])
        frames.append(frame)
    return frames


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
    sheet = Image.new('RGB', (1320, 790), '#edf0f5')
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate((*NAMES, 'ready')):
        x = i * 220
        src = Image.open(OUT / (name + '_512.png')).convert('RGBA')
        draw.text((x + 16, 16), name, fill='#192239')
        pic = src.resize((220, 220), RESAMPLE)
        sheet.paste(pic, (x, 40), pic)
        draw.rectangle((x, 280, x + 219, 465), fill='#111b30')
        pic = src.resize((160, 160), RESAMPLE)
        sheet.paste(pic, (x + 30, 290), pic)
        draw.text((x + 16, 478), '160px / dark UI', fill='#192239')
    draw.text((16, 515), '160px layout: Gwen points to the button on SCREEN RIGHT', fill='#192239')
    draw.rectangle((10, 545, 440, 775), fill='#111b30')
    pic = Image.open(OUT / 'ready.png').convert('RGBA')
    sheet.paste(pic, (25, 565), pic)
    draw.rounded_rectangle((190, 629, 410, 675), radius=8,
                           fill='#3158a0', outline='#86a7eb', width=2)
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 18)
    draw.text((300, 652), '추천 편성 보기', font=font, anchor='mm', fill='white')
    for i, frame in enumerate(frames):
        x = 460 + i * 210
        draw.rectangle((x, 545, x + 199, 775), fill='#111b30')
        sheet.paste(frame, (x + 20, 565), frame)
        draw.text((x + 20, 747), f'{i + 1}: {DURATIONS[i]}ms', fill='white')
    path = ROOT / '_tmp/_art_ready2_compare.png'
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
    frames = ready_frames(src)
    assert ImageChops.difference(frames[0], frames[1]).getbbox()
    assert frames[0].tobytes() == frames[-1].tobytes()
    for frame in frames:
        assert frame.crop((0, 0, 354, 512)).tobytes() == src.crop((0, 0, 354, 512)).tobytes()
        assert frame.getchannel('A').getbbox()[2] < 488, 'Fingertip needs margin'
    encode('ready', frames, 160, DURATIONS, 1)
    served = []
    sizes = {}
    for name in ('ready_512.png', 'ready.png', 'ready.webp'):
        output = OUT / name
        assert output.stat().st_size <= 80000, output
        with Image.open(output) as im:
            assert im.convert('RGBA').getchannel('A').getextrema() == (0, 255)
            if name.endswith('.webp'):
                assert im.n_frames == 4 and im.info['loop'] == 1
                durations = []
                for i in range(im.n_frames):
                    im.seek(i)
                    im.load()
                    durations.append(im.info['duration'])
                    served.append(im.convert('RGBA'))
                assert durations == DURATIONS, durations
        sizes[name] = output.stat().st_size
    assert sizes['ready.png'] + sizes['ready.webp'] <= 35000, sizes
    total = sum(p.stat().st_size for p in OUT.iterdir()
                if p.suffix in ('.png', '.webp') and not p.stem.endswith('_512'))
    assert total <= 640000, total
    compare(served)
    print(json.dumps(sizes, indent=2))
    print('Served art total:', total)


if __name__ == '__main__':
    main()
