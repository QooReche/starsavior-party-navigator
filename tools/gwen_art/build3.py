"""Build Gwen art 3 from approved masters, without a generation API."""
import argparse
import json
import io
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from build import ROOT, OUT, RESAMPLE
from build2 import encode, move_part
from build_ready import compact_master

HERE = Path(__file__).resolve().parent
BUDGET = json.loads((HERE / 'budget.json').read_text(encoding='utf-8'))
NAMES = ('cry', 'verdict', 'cheer', 'sulk', 'shy', 'doze', 'think',
         'magnify', 'stamp', 'board', 'coffee', 'stakeout', 'zap')
CONTINUOUS = ('think', 'magnify', 'stamp', 'board', 'coffee', 'stakeout', 'zap')
DURATIONS = [300, 200, 200, 300]
BLINK_NAMES = ('ready', 'welcome', 'investigate', 'files', 'report',
               'think', 'shy', 'sulk', 'verdict', 'cheer')
EYES = json.loads((HERE / 'blink_masks3.json').read_text(encoding='utf-8'))
PATCHES = HERE / 'blinks3'


def polygon_mask(points, size=(512, 512)):
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in points], fill=255)
    return mask


def eye_mask(name, size=512):
    mask = Image.new('L', (512,512))
    for points in EYES[name]:
        mask = ImageChops.lighter(mask, polygon_mask(points))
    if size != 512:
        # Include the complete Lanczos filter footprint; never touch pixels
        # outside this explicitly derived small UI eye mask.
        mask = mask.resize((size,size), RESAMPLE).point(lambda a: 255 if a else 0)
    return mask


def difference_mask(a, b):
    channels = ImageChops.difference(a, b).split()
    result = channels[0]
    for channel in channels[1:]:
        result = ImageChops.lighter(result, channel)
    return result.point(lambda a: 255 if a else 0)


def assert_eye_only(src, blink, mask):
    diff = difference_mask(src, blink)
    assert diff.getbbox(), 'Blink must differ from open eyes'
    assert not ImageChops.multiply(diff, ImageChops.invert(mask)).getbbox(), 'Blink changed pixels outside eye mask'
    assert src.getchannel('A').tobytes() == blink.getchannel('A').tobytes(), 'Blink alpha changed'


def import_blink(name, path):
    src = Image.open(OUT / (name+'_512.png')).convert('RGBA')
    edited = Image.open(path).convert('RGBA').resize((512,512), RESAMPLE)
    mask = eye_mask(name)
    layer = Image.new('RGBA', src.size)
    layer.paste(edited, (0,0), mask)
    # Binary patch alpha is also a portable, inspectable eye mask.
    layer.putalpha(mask)
    PATCHES.mkdir(exist_ok=True)
    layer.save(PATCHES / (name+'_eyes_512.png'), optimize=True)


def blink_master(name):
    src = Image.open(OUT / (name+'_512.png')).convert('RGBA')
    layer = Image.open(PATCHES / (name+'_eyes_512.png')).convert('RGBA')
    mask = eye_mask(name)
    assert layer.size == src.size == (512,512)
    assert layer.getchannel('A').tobytes() == mask.tobytes(), 'Eye patch escaped mask'
    dst = Image.composite(layer, src, mask)
    dst.putalpha(src.getchannel('A'))
    assert_eye_only(src, dst, mask)
    return dst


def blink_static(name):
    src = Image.open(OUT / (name+'.png')).convert('RGBA')
    master = blink_master(name).resize((160,160), RESAMPLE)
    # Quantize only the patch; global quantization would alter the original.
    edited = master.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                             dither=Image.Dither.NONE).convert('RGBA')
    dst = Image.composite(edited, src, eye_mask(name, 160))
    dst.putalpha(src.getchannel('A'))
    assert_eye_only(src, dst, eye_mask(name, 160))
    return dst


def floating_frames(src, box, offsets, opacity=(1,1,1,1)):
    part = src.crop(box)
    base = src.copy()
    base.paste((0,0,0,0), box)
    frames = []
    for (dx,dy), alpha in zip(offsets, opacity):
        pic = part.copy()
        pic.putalpha(pic.getchannel('A').point(lambda a: round(a*alpha)))
        frame = base.copy()
        frame.alpha_composite(pic, (box[0]+dx, box[1]+dy))
        frames.append(frame)
    frames[0] = src.copy()
    frames[-1] = src.copy()
    return frames


def newspaper_frames(src):
    points = [(100,216),(191,229),(254,225),(318,230),(410,215),
              (402,263),(412,271),(409,310),(395,312),(382,351),
              (318,368),(190,368),(125,352),(118,312),(99,312),
              (98,270),(109,263)]
    mask = polygon_mask(points)
    part = src.copy()
    part.putalpha(ImageChops.multiply(src.getchannel('A'),mask))
    base = src.copy()
    base.putalpha(ImageChops.multiply(src.getchannel('A'), ImageChops.invert(mask)))
    # Extend the existing pixels immediately above the paper into the tiny
    # revealed gap. No newly drawn face/body, only the original boundary.
    for x in range(98,413):
        ys = [y for y in range(210,370) if mask.getpixel((x,y))]
        if ys:
            top = min(ys)
            for y in range(top,top+8):
                base.putpixel((x,y),src.getpixel((x,top-1)))
    frames = []
    for dy in (0,4,7,0):
        frame = base.copy()
        frame.alpha_composite(part,(0,dy))
        frames.append(frame if dy else src.copy())
    return frames


def spark_frames(src):
    frames = []
    for strength in (1,0.25,1.45,1):
        frame = src.copy()
        for y in range(235,250):
            for x in range(201,249):
                r,g,b,a = src.getpixel((x,y))
                if b > 180 and ((b > r+10 and g > r+7) or (r>215 and g>230 and b>245)):
                    target = (70,140,210) if strength<1 else (245,255,255)
                    amount = abs(strength-1)
                    frame.putpixel((x,y),tuple(round(v*(1-amount)+t*amount) for v,t in zip((r,g,b),target))+(a,))
        frames.append(frame)
    return frames


def action_frames(name, src):
    if name == 'think':
        return floating_frames(src,(358,27,410,91),[(0,0),(0,-2),(0,-4),(0,0)],(1,.65,.9,1))
    if name == 'coffee':
        return floating_frames(src,(85,177,128,260),[(0,0),(1,-4),(-1,-7),(0,0)],(1,.75,.5,1))
    if name == 'stakeout':
        return newspaper_frames(src)
    if name == 'zap':
        return spark_frames(src)
    spec = {
        'cry': ([(133,250),(193,250),(200,294),(217,322),(187,347),(136,315)], [0,3,-2,0], (210,322)),
        'verdict': ([(97,252),(196,251),(221,273),(223,322),(193,344),(97,337)], [0,-2,1,0], (223,300)),
        'cheer': ([(347,130),(419,130),(419,217),(332,277),(307,263),(349,198)], [0,3,-2,0], (320,266)),
        'sulk': ([(92,24),(412,24),(412,266),(340,281),(181,267),(92,275)], [0,.7,-.5,0], (256,266)),
        'shy': ([(218,278),(284,278),(290,316),(278,332),(220,332),(211,310)], [0,2,-1,0], (250,327)),
        'doze': ([(100,26),(407,26),(407,283),(327,284),(277,279),(228,279),(186,284),(100,283)], [0,2,3.5,0], (256,277)),
        'magnify': ([(55,310),(163,310),(183,349),(205,373),(207,416),(174,430),(137,409),(55,408)], [0,2,-1,0], (205,381)),
        'stamp': ([(179,284),(222,282),(239,308),(237,352),(184,352)], [0,3,-2,0], (220,284)),
        'board': ([(128,242),(183,240),(199,259),(190,290),(133,290)], [0,3,-2,0], (190,275)),
    }
    polygon, angles, pivot = spec[name]
    return move_part(src, polygon, angles, pivot)


def validate_outputs():
    for name in NAMES:
        for suffix, size in (('_512.png',512),('.png',160),('.webp',160)):
            path = OUT / (name+suffix)
            assert path.stat().st_size <= BUDGET['file_bytes'], path
            with Image.open(path) as im:
                assert im.size == (size,size), path
                assert im.convert('RGBA').getchannel('A').getextrema() == (0,255), path
                if suffix == '.webp':
                    assert im.n_frames == 4 and im.info['loop'] == int(name not in CONTINUOUS), name
                    frames, durations = [], []
                    for i in range(im.n_frames):
                        im.seek(i); im.load()
                        frames.append(im.convert('RGBA')); durations.append(im.info['duration'])
                    assert durations == DURATIONS, (name,durations)
                    assert any(difference_mask(frames[0],f).getbbox() for f in frames[1:]), name
    for name in BLINK_NAMES:
        with Image.open(OUT / (name+'_blink.png')) as im:
            assert im.size == (160,160) and im.n_frames == 1, name
            src = Image.open(OUT / (name+'.png')).convert('RGBA')
            assert_eye_only(src, im.convert('RGBA'), eye_mask(name,160))
            assert im.convert('RGBA').tobytes() == blink_static(name).tobytes(), name
    served = [p for p in OUT.iterdir() if p.suffix in ('.png','.webp') and not p.stem.endswith('_512')]
    assert all(p.stat().st_size <= BUDGET['file_bytes'] for p in served)
    assert sum(p.stat().st_size for p in served) <= BUDGET['served_bytes']
    assert sum((OUT/(n+s)).stat().st_size for n in NAMES for s in ('.png','.webp')) <= BUDGET['new_pairs_bytes']
    assert sum((OUT/(n+'_blink.png')).stat().st_size for n in BLINK_NAMES) <= BUDGET['blink_bytes']
    return {p.name:p.stat().st_size for p in sorted(served)}


def import_master(path):
    raw = Image.open(path).convert('RGBA')
    assert raw.getchannel('A').getextrema() == (0, 255), path
    raw.putalpha(raw.getchannel('A').point(lambda a: 0 if a < 10 else 255 if a > 245 else a))
    raw = raw.crop(raw.getchannel('A').getbbox())
    raw.thumbnail((450, 450), RESAMPLE)
    dst = Image.new('RGBA', (512, 512))
    dst.alpha_composite(raw, ((512-raw.width)//2, 482-raw.height))
    result = compact_master(dst)
    for colors in (256, 224, 192, 160, 128):
        if colors < 256:
            result = dst.quantize(colors=colors, method=Image.Quantize.FASTOCTREE,
                                  dither=Image.Dither.NONE)
        buf = io.BytesIO()
        result.save(buf, format='PNG', optimize=True)
        if len(buf.getvalue()) <= BUDGET['file_bytes']:
            return result
    raise AssertionError(f'Master exceeds file budget: {path}')


def compare():
    names = ('ready', 'welcome', 'investigate', 'files', 'report', 'surprised', 'walk') + NAMES
    sheet = Image.new('RGB', (1160, len(names)*190+30), '#111b30')
    draw = ImageDraw.Draw(sheet)
    for row, name in enumerate(names):
        y = row*190+20
        draw.text((8, y), name, fill='white')
        src = Image.open(OUT / (name+'.png')).convert('RGBA')
        x = 110
        for size in (64, 72, 120, 160):
            pic = src.resize((size, size), RESAMPLE)
            sheet.paste(pic, (x, y+12), pic)
            draw.text((x, y+174), str(size)+'px', fill='#b8c8df')
            x += size+18
        blink = OUT / (name+'_blink.png')
        if blink.exists():
            pic = Image.open(blink).convert('RGBA')
            sheet.paste(pic, (640, y+12), pic)
            draw.text((640, y+174), 'blink 160', fill='#b8c8df')
        webp = OUT / (name+'.webp')
        if webp.exists():
            with Image.open(webp) as im:
                im.seek(min(2, im.n_frames-1))
                pic = im.convert('RGBA').resize((160,160), RESAMPLE)
                sheet.paste(pic, (830, y+12), pic)
                draw.text((830, y+174), 'motion frame 3', fill='#b8c8df')
    path = ROOT / '_tmp/_art_compare3.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-dir', type=Path)
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--masters-only', action='store_true')
    parser.add_argument('--import-blinks', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.import_dir:
        for name in NAMES:
            path = OUT / (name+'_512.png')
            import_master(args.import_dir / (name+'.png')).save(path, optimize=True)
            assert path.stat().st_size <= BUDGET['file_bytes'], path
    if args.masters_only:
        for name in NAMES:
            src = Image.open(OUT / (name+'_512.png')).convert('RGBA')
            src.resize((160,160),RESAMPLE).save(OUT / (name+'.png'),optimize=True)
    elif not args.check:
        for name in NAMES:
            src = Image.open(OUT / (name+'_512.png')).convert('RGBA')
            frames = action_frames(name,src)
            assert frames[0].tobytes() == frames[-1].tobytes() == src.tobytes(), name
            encode(name,frames,160,DURATIONS,int(name not in CONTINUOUS))
        if args.import_blinks:
            for name in BLINK_NAMES:
                import_blink(name,args.import_blinks/(name+'_blink_raw.png'))
        for name in BLINK_NAMES:
            blink_static(name).save(OUT/(name+'_blink.png'),optimize=True)
    if not args.masters_only:
        sizes = validate_outputs()
        print(json.dumps(sizes,indent=2))
        print('Served total:',sum(sizes.values()))
    if args.compare:
        compare()


if __name__ == '__main__':
    main()
