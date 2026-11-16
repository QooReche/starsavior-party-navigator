"""Gwen art 4: reproducible alpha sprites from adopted masters and eye patches."""
import argparse
import io
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageOps
from build import ROOT, OUT, RESAMPLE
from build2 import encode, move_part
from build_ready import compact_master
from build3 import import_master, polygon_mask, difference_mask, assert_eye_only

HERE = Path(__file__).resolve().parent
BUDGET = json.loads((HERE/'budget.json').read_text(encoding='utf-8'))
NAMES = ('run','point','jump','guide2','present','train','charge','wait','peek','wake')
BLINK_NAMES = ('guide2','present','train','charge','wait','peek','wake')
CONTINUOUS = ('run','wait','charge')
DURATIONS = {n: [300,200,200,300] for n in NAMES}
DURATIONS.update(run=[200]*4, jump=[400,600])
FRAMES = HERE/'frames4'
PATCHES = HERE/'blinks4'
EYES = json.loads((HERE/'blink_masks4.json').read_text(encoding='utf-8'))


def load(path):
    with Image.open(path) as im:
        return im.convert('RGBA')


def save_master(src, path, floor=None):
    result = compact_master(src)
    for colors in (256,224,192,160,128):
        if colors < 256:
            result = src.quantize(colors=colors, method=Image.Quantize.FASTOCTREE,
                                  dither=Image.Dither.NONE)
        if floor is not None:
            actual = result.convert('RGBA').getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()[3]
            result = result.transform(result.size,Image.Transform.AFFINE,
                                      (1,0,0,0,1,actual-floor),
                                      resample=Image.Resampling.NEAREST,
                                      fillcolor=result.getpixel((0,0)))
        buf = io.BytesIO()
        result.save(buf, format='PNG', optimize=True)
        if len(buf.getvalue()) <= BUDGET['file_bytes']:
            path.write_bytes(buf.getvalue())
            return
    raise AssertionError(f'Master exceeds budget: {path}')


def import_sequence(name, path):
    raw = load(path)
    assert raw.getchannel('A').getextrema() == (0,255)
    columns, rows = (2,2) if name == 'run' else (2,1)
    parts = [raw.crop((x*raw.width//columns,y*raw.height//rows,
                      (x+1)*raw.width//columns,(y+1)*raw.height//rows))
             for y in range(rows) for x in range(columns)]
    for part in parts:
        part.putalpha(part.getchannel('A').point(lambda a: 0 if a<10 else 255 if a>245 else a))
    boxes = [p.getchannel('A').getbbox() for p in parts]
    # A single scale for the whole sequence; never fit individual poses.
    height = 450 if name == 'run' else 410
    scale = min(height/max(b[3]-b[1] for b in boxes),
                450/max(b[2]-b[0] for b in boxes))
    FRAMES.mkdir(exist_ok=True)
    for i,(part,box) in enumerate(zip(parts,boxes)):
        part = part.crop(box).resize((round((box[2]-box[0])*scale),
                                     round((box[3]-box[1])*scale)),RESAMPLE)
        floor = 440 if name == 'jump' and i == 0 else 482
        dst = Image.new('RGBA',(512,512))
        dst.alpha_composite(part,((512-part.width)//2,floor-part.height))
        path = OUT/(name+'_512.png') if i == 0 else FRAMES/f'{name}_{i}_512.png'
        save_master(dst,path,floor=floor)


def eye_mask(name, size=512):
    mask = Image.new('L',(512,512))
    for polygon in EYES[name]:
        mask = ImageChops.lighter(mask,polygon_mask(polygon))
    if size != 512:
        mask = mask.resize((size,size),RESAMPLE).point(lambda a:255 if a else 0)
    return mask


def import_blink(name, path):
    edited = load(path).resize((512,512),RESAMPLE)
    mask = eye_mask(name)
    patch = Image.new('RGBA',(512,512))
    patch.paste(edited,(0,0),mask)
    patch.putalpha(mask)
    PATCHES.mkdir(exist_ok=True)
    patch.save(PATCHES/(name+'_eyes_512.png'),optimize=True)


def blink_master(name):
    src = load(OUT/(name+'_512.png'))
    patch = load(PATCHES/(name+'_eyes_512.png'))
    mask = eye_mask(name)
    assert patch.size == src.size == (512,512)
    assert patch.getchannel('A').tobytes() == mask.tobytes(), 'Eye patch escaped mask'
    dst = Image.composite(patch,src,mask)
    dst.putalpha(src.getchannel('A'))
    assert_eye_only(src,dst,mask)
    return dst


def blink_static(name):
    src = load(OUT/(name+'.png'))
    edited = blink_master(name).resize((160,160),RESAMPLE)
    edited = edited.quantize(colors=256,method=Image.Quantize.FASTOCTREE,
                             dither=Image.Dither.NONE).convert('RGBA')
    dst = Image.composite(edited,src,eye_mask(name,160))
    dst.putalpha(src.getchannel('A'))
    assert_eye_only(src,dst,eye_mask(name,160))
    return dst


def translated(src, dy):
    dst = Image.new('RGBA',src.size)
    dst.alpha_composite(src,(0,dy))
    return dst


def action_frames(name, src=None):
    if src is None:
        src = load(OUT/(name+'_512.png'))
    if name in ('run','jump'):
        return [src]+[load(FRAMES/f'{name}_{i}_512.png')
                      for i in range(1,len(DURATIONS[name]))]
    if name == 'wake':
        return [blink_master(name),translated(src,-8),translated(src,-3),src]
    if name == 'wait':
        # Shins below knees, independent opposite swings; head and stool fixed.
        left = [(216,413),(244,413),(243,446),(242,470),(213,470),(211,450)]
        right = [(259,413),(288,413),(288,450),(287,474),(258,474),(257,450)]
        frames = move_part(src,left,[0,-8,8,0],(230,413))
        return [move_part(f,right,[a],(274,413))[0]
                for f,a in zip(frames,[0,8,-8,0])]
    if name == 'charge':
        frames = []
        for strength in (1,.3,1.5,1):
            frame = src.copy()
            for y in range(280,295):
                for x in range(245,274):
                    r,g,b,a = src.getpixel((x,y))
                    if a and b > 170 and g > r+7 and b > r+15:
                        target = (65,125,190) if strength < 1 else (230,250,255)
                        amount = abs(strength-1)
                        frame.putpixel((x,y),tuple(round(v*(1-amount)+t*amount)
                                       for v,t in zip((r,g,b),target))+(a,))
            frames.append(frame)
        return frames
    specs = {
        'point': ([(326,256),(419,246),(425,290),(332,304)], [0,-3,-5,0], (331,283)),
        'guide2': ([(96,268),(158,272),(180,295),(218,300),(211,332),(161,333),(96,313)], [0,-3,2,0], (215,311)),
        'present': ([(95,260),(160,260),(182,286),(226,290),(218,318),(165,321),(95,306)], [0,-4,-7,0], (222,300)),
        'train': ([(103,263),(180,260),(197,281),(202,303),(220,316),(211,345),(177,343),(130,318),(103,314)], [0,-8,-16,0], (214,325)),
        'peek': ([(101,31),(407,31),(407,288),(338,299),(266,284),(191,294),(101,284)], [0,1,2,0], (259,284)),
    }
    polygon,angles,pivot = specs[name]
    return move_part(src,polygon,angles,pivot)


def output_paths():
    return ([OUT/(n+s) for n in NAMES for s in ('_512.png','.png','.webp')]
            +[OUT/(n+'_blink.png') for n in BLINK_NAMES]
            +[FRAMES/f'{n}_{i}_512.png' for n in ('run','jump') for i in range(1,len(DURATIONS[n]))]
            +[PATCHES/(n+'_eyes_512.png') for n in BLINK_NAMES])


def raster_frames(name, frames):
    frames = [f.resize((160,160),RESAMPLE) for f in frames]
    if name == 'run':
        # Lanczos can move the half-opacity foot boundary by one UI pixel.
        # Align again at delivery resolution, without changing scale.
        frames = [translated(f,151-f.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()[3])
                  for f in frames]
    return frames


def validate_outputs():
    for path in output_paths():
        assert path.is_file(), path
        assert path.stat().st_size <= BUDGET['file_bytes'], path
        with Image.open(path) as im:
            size = 512 if path.stem.endswith('_512') else 160
            assert im.size == (size,size), path
            assert im.convert('RGBA').getchannel('A').getextrema() == (0,255), path
    for name in NAMES:
        with Image.open(OUT/(name+'.webp')) as im:
            assert im.n_frames == len(DURATIONS[name]), name
            assert im.info['loop'] == int(name not in CONTINUOUS), name
            frames,durations = [],[]
            for i in range(im.n_frames):
                im.seek(i); im.load()
                frames.append(im.convert('RGBA'));durations.append(im.info['duration'])
            assert durations == DURATIONS[name], (name,durations)
            assert any(difference_mask(frames[0],f).getbbox() for f in frames[1:]), name
            if name == 'run':
                floors = [f.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()[3] for f in frames]
                assert len(set(floors)) == 1, ('Run baseline drift',floors)
    for name in BLINK_NAMES:
        src = load(OUT/(name+'.png'))
        blink = load(OUT/(name+'_blink.png'))
        assert_eye_only(src,blink,eye_mask(name,160))
        assert blink.tobytes() == blink_static(name).tobytes(), name
    served = [p for p in OUT.iterdir() if p.suffix in ('.png','.webp') and not p.stem.endswith('_512')]
    assert sum(p.stat().st_size for p in served) <= BUDGET['served_bytes']
    assert all(p.stat().st_size <= BUDGET['file_bytes'] for p in served)
    assert sum((OUT/(n+s)).stat().st_size for n in NAMES for s in ('.png','.webp')) <= BUDGET['art4_pairs_bytes']
    assert sum((OUT/(n+'_blink.png')).stat().st_size for n in BLINK_NAMES) <= BUDGET['art4_blink_bytes']
    return {str(p.relative_to(ROOT)).replace('\\','/'):p.stat().st_size for p in output_paths()}


def compare():
    names = ('investigate','ready','walk')+NAMES
    sheet = Image.new('RGB',(1760,len(names)*195+20),'#111b30')
    draw = ImageDraw.Draw(sheet)
    for row,name in enumerate(names):
        y = row*195+12
        draw.text((8,y),name,fill='white')
        src = load(OUT/(name+'.png'))
        x = 95
        for size in (64,72,120,160):
            pic = src.resize((size,size),RESAMPLE)
            sheet.paste(pic,(x,y+12),pic)
            draw.text((x,y+176),f'{size}px',fill='#b8c8df');x += size+15
        if name in BLINK_NAMES:
            pic = load(OUT/(name+'_blink.png'))
            sheet.paste(pic,(585,y+12),pic)
            draw.text((585,y+176),'blink',fill='#b8c8df')
        pic = ImageOps.mirror(src)
        sheet.paste(pic,(755,y+12),pic)
        draw.text((755,y+176),'mirror',fill='#b8c8df')
        with Image.open(OUT/(name+'.webp')) as im:
            for i in range(im.n_frames):
                im.seek(i);im.load()
                pic = im.convert('RGBA').resize((160,160),RESAMPLE)
                x = 930+i*200
                sheet.paste(pic,(x,y+12),pic)
                draw.text((x,y+176),f'f{i+1} {im.info["duration"]}ms',fill='#b8c8df')
    target = ROOT/'_tmp/_art_compare4.png'
    target.parent.mkdir(parents=True,exist_ok=True)
    (ROOT/'_tmp/art4').mkdir(parents=True,exist_ok=True)
    sheet.save(target)
    for row,name in enumerate(names):
        sheet.crop((0,row*195,1760,(row+1)*195+12)).save(ROOT/f'_tmp/art4/compare-{name}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-dir',type=Path)
    parser.add_argument('--import-blinks',type=Path)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--compare',action='store_true')
    parser.add_argument('--masters-only',action='store_true')
    args = parser.parse_args()
    if args.import_dir:
        for name in NAMES:
            path = args.import_dir/(name+'.png')
            if name in ('run','jump'):
                import_sequence(name,path)
            else:
                import_master(path).save(OUT/(name+'_512.png'),optimize=True)
    if args.import_blinks:
        for name in BLINK_NAMES:
            import_blink(name,args.import_blinks/(name+'_blink_raw.png'))
    if args.masters_only:
        return
    if not args.check:
        for name in NAMES:
            src = load(OUT/(name+'_512.png'))
            frames = action_frames(name,src)
            encode(name,raster_frames(name,frames),160,DURATIONS[name],int(name not in CONTINUOUS),static=False)
            # The static wake is wide-eyed; its animation starts with closed eyes.
            pic = src.resize((160,160),RESAMPLE)
            png = pic.quantize(colors=256,method=Image.Quantize.FASTOCTREE,
                               dither=Image.Dither.NONE).convert('RGBA')
            png.putalpha(pic.getchannel('A'))
            png.save(OUT/(name+'.png'),optimize=True)
        for name in BLINK_NAMES:
            blink_static(name).save(OUT/(name+'_blink.png'),optimize=True)
    print(json.dumps(validate_outputs(),indent=2))
    if args.compare:
        compare()


if __name__ == '__main__':
    main()
