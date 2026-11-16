"""Gwen upper-body art: generated keyframes, eye-only blinks, reproducible build.

Uses build2's 320px master normalization and 240px one-shot encoder.
"""
import argparse
import io
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from build2 import ROOT, OUT, R, cells, encode
from build3 import difference_mask, assert_eye_only
import cry6
import sleeve7
import face9
import sleeve11

HERE = Path(__file__).resolve().parent
MASTERS = HERE / 'masters5'
NAMES = ('st_cry', 'st_verdict', 'st_cheer', 'st_ok', 'st_point',
         'st_shy', 'st_sulk', 'st_wink', 'st_zap', 'st_welcome')
DURATIONS = [450, 220, 330]
LOCAL_MOTION = {
    'st_zap': [(43, 83), (83, 83), (83, 116), (43, 116)],
    'st_wink': [(163, 62), (194, 62), (194, 84), (163, 84)],
}


def import_sheet(path):
    raw = Image.open(path).convert('RGBA')
    assert raw.getchannel('A').getextrema() == (0, 255), path
    # Same alpha cleanup as art3; preserve antialiased silhouette.
    raw.putalpha(raw.getchannel('A').point(lambda a: 0 if a < 10 else 255 if a > 245 else a))
    parts = cells(raw, 3)
    boxes = [p.getchannel('A').point(lambda a: 255 if a > 100 else 0).getbbox() for p in parts]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    sheet = Image.new('RGBA', (960, 320))
    for i, part in enumerate(parts):
        part = part.crop(box)
        part.thumbnail((296, 296), R)
        sheet.alpha_composite(part, (i*320+(320-part.width)//2, 308-part.height))
    return sheet


def original_master_frames(name):
    with Image.open(MASTERS / (name+'.webp')) as im:
        frames = cells(im.convert('RGBA'), 3)
    return cry6.apply_sleeves(frames) if name == 'st_cry' else face9.apply(name, frames)


def master_frames(name):
    return sleeve7.apply(name, original_master_frames(name))


def save_master(sheet, path):
    budget = json.loads((HERE / 'budget.json').read_text(encoding='utf-8'))
    for quality in (90, 88, 86, 84, 82):
        buf = io.BytesIO()
        sheet.save(buf, format='WEBP', quality=quality, method=6)
        if len(buf.getvalue()) <= budget['file_bytes']:
            path.write_bytes(buf.getvalue())
            print(f'{path.name}: master quality={quality}, bytes={len(buf.getvalue())}')
            return
    raise AssertionError(f'Master exceeds budget: {path}')


def eye_specs():
    return json.loads((HERE / 'blink_masks5.json').read_text(encoding='utf-8'))


def eye_mask(name, size=320):
    mask = Image.new('L', (320, 320))
    for polygon in eye_specs()[name]['polygons']:
        ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=255)
    if size != 320:
        mask = mask.resize((size, size), R).point(lambda a: 255 if a else 0)
    return mask


def blink_master(name, sleeves=True):
    src, _, edited = master_frames(name) if sleeves else original_master_frames(name)
    dx, dy = eye_specs()[name].get('offset', [0, 0])
    aligned = Image.new('RGBA', src.size)
    aligned.alpha_composite(edited, (dx, dy))
    result = Image.composite(aligned, src, eye_mask(name))
    result.putalpha(src.getchannel('A'))
    assert_eye_only(src, result, eye_mask(name))
    return result


def blink_static(name):
    if name == 'st_shy':
        with Image.open(sleeve11.PATCHES/'st_shy_base_blink.png') as im:
            return sleeve11.repair(im.convert('RGBA'))
    with Image.open(OUT / (name+'.png')) as im:
        src = im.convert('RGBA')
    if name == 'st_cry':
        return cry6.preserve_static(src, blink=True)
    # Quantize the original palette for unchanged eye pixels after sleeve edits.
    edited = blink_master(name, sleeves=name not in sleeve7.NAMES).resize((240, 240), R)
    edited = edited.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                             dither=Image.Dither.NONE).convert('RGBA')
    dst = Image.composite(edited, src, eye_mask(name, 240))
    dst.putalpha(src.getchannel('A'))
    assert_eye_only(src, dst, eye_mask(name, 240))
    return dst


def motion_mask(name):
    mask = Image.new('L', (320, 320))
    ImageDraw.Draw(mask).polygon(LOCAL_MOTION[name], fill=255)
    return mask


def action_frames(name):
    src, action, _ = master_frames(name)
    if name in LOCAL_MOTION:
        action = Image.composite(action, src, motion_mask(name))
        if name == 'st_wink':
            action.putalpha(src.getchannel('A'))
    return [src, action, src.copy()]


def build(names=NAMES, blink=True):
    for name in names:
        encode(name, action_frames(name), 240, DURATIONS, 1)
        if name in sleeve7.NAMES:
            with Image.open(OUT/(name+'.png')) as im:
                preserved = sleeve7.preserve_static(name, im.convert('RGBA'), original_master_frames(name)[0])
            preserved.save(OUT/(name+'.png'), optimize=True)
        if name == 'st_cry':
            with Image.open(OUT/(name+'.png')) as im:
                preserved = cry6.preserve_static(im.convert('RGBA'))
            preserved.save(OUT/(name+'.png'), optimize=True)
        if name in face9.NAMES:
            with Image.open(OUT/(name+'.png')) as im:
                preserved = face9.preserve_static(name, im.convert('RGBA'))
            preserved.save(OUT/(name+'.png'), optimize=True)
        if blink:
            blink_static(name).save(OUT / (name+'_blink.png'), optimize=True)
        if name == 'st_shy':
            sleeve11.encode(OUT, blink=blink)


def validate_outputs(names=NAMES):
    budget = json.loads((HERE / 'budget.json').read_text(encoding='utf-8'))
    sizes = {}
    for name in names:
        for suffix in ('.png', '.webp', '_blink.png'):
            path = OUT / (name+suffix)
            sizes[path.name] = path.stat().st_size
            assert sizes[path.name] <= budget['file_bytes'], path
            with Image.open(path) as im:
                assert im.size == (240, 240), path
                assert im.convert('RGBA').getchannel('A').getextrema() == (0, 255), path
                if suffix == '.webp':
                    assert im.n_frames == 3 and im.info['loop'] == 1, path
                    frames, times = [], []
                    for i in range(im.n_frames):
                        im.seek(i); im.load()
                        frames.append(im.convert('RGBA')); times.append(im.info['duration'])
                    assert times == DURATIONS, (path, times)
                    assert difference_mask(frames[0], frames[1]).getbbox(), path
                else:
                    assert im.n_frames == 1, path
        with Image.open(OUT/(name+'_blink.png')) as im:
            assert im.convert('RGBA').tobytes() == blink_static(name).tobytes(), name
    assert sum(sizes.values()) <= budget['art5']['served_bytes']
    served = [p for p in OUT.iterdir() if p.suffix in ('.png', '.webp') and not p.stem.endswith('_512')]
    assert sum(p.stat().st_size for p in served) <= budget['served_bytes']
    return sizes


def compare(names=NAMES):
    rows = ('confident', 'thoughtful', 'notes') + tuple(names)
    sheet = Image.new('RGB', (1540, 280*len(rows)), '#111b30')
    draw = ImageDraw.Draw(sheet)
    for row, name in enumerate(rows):
        y = row*280
        draw.text((8, y+8), name, fill='white')
        src = Image.open(OUT/(name+'.png')).convert('RGBA')
        x = 120
        for size in (120, 160, 240):
            pic = src.resize((size, size), R)
            sheet.paste(pic, (x, y+20+(240-size)), pic)
            draw.text((x, y+262), str(size)+'px', fill='#bac9e0')
            x += size+16
        with Image.open(OUT/(name+'.webp')) as im:
            for i in (0, 1):
                im.seek(i)
                pic = im.convert('RGBA')
                sheet.paste(pic, (x, y+20), pic)
                draw.text((x, y+262), 'action '+str(i+1), fill='#bac9e0')
                x += 256
        path = OUT/(name+'_blink.png')
        if path.exists():
            pic = Image.open(path).convert('RGBA')
            sheet.paste(pic, (x, y+20), pic)
            draw.text((x, y+262), 'blink / eye squeeze', fill='#bac9e0')
    target = ROOT/'_tmp/_art_compare5.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    (ROOT/'_tmp/art5').mkdir(parents=True, exist_ok=True)
    sheet.save(target)
    # Full-size row crops keep all actual display sizes inspectable.
    for row, name in enumerate(rows):
        sheet.crop((0, row*280, 1540, (row+1)*280)).save(ROOT/'_tmp/art5'/('compare_'+name+'.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-dir', type=Path)
    parser.add_argument('--names', nargs='+', choices=NAMES, default=list(NAMES))
    parser.add_argument('--no-blink', action='store_true', help='Pilot measurements before eye-mask authoring')
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.import_dir:
        MASTERS.mkdir(exist_ok=True)
        for name in args.names:
            save_master(import_sheet(args.import_dir/(name+'.png')), MASTERS/(name+'.webp'))
    if not args.check:
        build(args.names, blink=not args.no_blink)
    if not args.no_blink:
        print(json.dumps(validate_outputs(args.names), indent=2))
    if args.compare:
        compare(args.names)


if __name__ == '__main__':
    main()
