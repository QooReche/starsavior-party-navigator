"""Gwen art 2: crop generated sheets, preserve alpha, encode calm animations.

python -X utf8 tools/gwen_art/build2.py --import-dir _tmp/art2 --reference-dir <gwen_src>
Subsequent builds use the small, committed master sheets without generation.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageOps
import sleeve7
import sleeve8

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/ui_icons/gwen'
MASTERS = Path(__file__).parent / 'masters2'
NEW = {'walk': 4, 'confident': 2, 'thoughtful': 2, 'notes': 2}
R = Image.Resampling.LANCZOS
BUDGET = json.loads((Path(__file__).parent / 'budget.json').read_text(encoding='utf-8'))


def cells(src, count):
    return [src.crop((round(i*src.width/count), 0, round((i+1)*src.width/count), src.height)) for i in range(count)]


def import_sheet(path, count):
    parts = cells(Image.open(path).convert('RGBA'), count)
    boxes = [p.getchannel('A').point(lambda a: 255 if a > 100 else 0).getbbox() for p in parts]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    sheet = Image.new('RGBA', (320*count, 320))
    for i, p in enumerate(parts):
        p = p.crop(box)
        p.thumbnail((296, 296), R)
        sheet.alpha_composite(p, (320*i+(320-p.width)//2, 308-p.height))
    return sheet


def move_part(src, polygon, angles, pivot):
    mask = Image.new('L', src.size)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    part = src.copy()
    part.putalpha(ImageChops.multiply(src.getchannel('A'), mask))
    base = src.copy()
    base.putalpha(ImageChops.multiply(src.getchannel('A'), ImageChops.invert(mask)))
    frames = []
    for angle in angles:
        if not angle:
            frames.append(src.copy())
            continue
        frame = base.copy()
        frame.alpha_composite(part.rotate(angle, Image.Resampling.BICUBIC, center=pivot))
        frames.append(frame)
    return frames


def old_frames(name):
    src = Image.open(OUT / (name+'_512.png')).convert('RGBA')
    if name == 'welcome':
        return move_part(src, [(80,225),(175,225),(185,275),(213,300),(197,329),(155,312),(80,310)], [0, -9, 6, 0], (201,311))
    if name == 'report':
        return move_part(src, [(346,195),(450,195),(450,324),(335,324),(326,285)], [0, 4, -2, 0], (337,278))
    frames = []
    for x,y in [(0,0),(-3,-6),(3,-2),(0,0)]:
        frame = Image.new('RGBA', src.size)
        frame.alpha_composite(src,(x,y))
        frames.append(frame)
    return frames


def encode(name, frames, size, duration, loop, static=True):
    if name == 'notes':
        assert size == 240
        return sleeve8.encode(OUT, duration, loop, static)
    frames = [f.resize((size,size),R) for f in frames]
    if static:
        png=frames[0].quantize(colors=256,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA')
        png.putalpha(frames[0].getchannel('A'))
        png.save(OUT/(name+'.png'),optimize=True)
    path = OUT/(name+'.webp')
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=duration,loop=loop,quality=88,method=6)
    assert path.stat().st_size <= BUDGET['file_bytes'], path
    with Image.open(path) as im:
        assert 2 <= im.n_frames <= 4 and im.info['loop'] == loop
    return frames


def compare(frames, reference_dir):
    sheet = Image.new('RGB',(1440,1300),'#edf0f5')
    draw = ImageDraw.Draw(sheet)
    def tile(pic,x,y,w=220,h=250):
        pic=ImageOps.contain(pic.convert('RGBA'),(w,h),R)
        sheet.paste(pic,(x+(w-pic.width)//2,y+(h-pic.height)//2),pic)
    draw.text((20,15),'Official references / generated fan art — original face, hair, costume, proportions',fill='#192239')
    for i,name in enumerate(['22.png','23.webp','24.webp','25.png','28_sd_emote.webp']):
        pic=Image.open(reference_dir/name)
        if name=='28_sd_emote.webp':
            pic=pic.crop((470,95,970,565))  # Only the central official SD badge, not the scene.
        tile(pic,20+i*280,40,260,250)
        draw.text((20+i*280,295),name,fill='#192239')
    for i,name in enumerate(['investigate','files','report','surprised','welcome']):
        tile(Image.open(OUT/(name+'.png')),20+i*280,325,240,190)
        draw.text((20+i*280,520),'Approved SD / '+name,fill='#192239')
    for i,name in enumerate(NEW):
        x=20+i*355
        draw.text((x,565),name+' / first + action frames',fill='#192239')
        tile(frames[name][0],x,590,165,220)
        tile(frames[name][1],x+170,590,165,220)
        draw.rectangle((x,835,x+334,1080),fill='#131a2b')
        tile(frames[name][0],x+60,840,220,235)
    for i,name in enumerate(['report','surprised','welcome']):
        for j,frame in enumerate(frames[name]):
            tile(frame,20+i*470+j*110,1120,105,130)
        draw.text((20+i*470,1270),name+' / one-shot motion',fill='#192239')
    sheet.save(ROOT/'_art_compare2.png')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--import-dir',type=Path)
    ap.add_argument('--reference-dir',type=Path)
    args=ap.parse_args()
    MASTERS.mkdir(exist_ok=True)
    if args.import_dir:
        for name,count in NEW.items():
            import_sheet(args.import_dir/(name+'.png'),count).save(MASTERS/(name+'.webp'),quality=90,method=6)
    frames={}
    for name,count in NEW.items():
        src=Image.open(MASTERS/(name+'.webp')).convert('RGBA')
        parts=cells(src,count)
        parts=sleeve7.apply(name,parts)
        if name=='walk':
            frames[name]=encode(name,parts,160,[300]*4,0)
        else:
            frames[name]=encode(name,[parts[0],parts[1],parts[0]],240,[450,220,330],1)
    for name in ['report','surprised','welcome']:
        frames[name]=encode(name,old_frames(name),160,[240,200,200,360],1,static=False)
    served=[p for p in OUT.iterdir() if p.suffix in ('.png','.webp') and not p.stem.endswith('_512')]
    assert all(p.stat().st_size<=BUDGET['file_bytes'] for p in served)
    assert sum(p.stat().st_size for p in served)<=BUDGET['served_bytes']
    print(json.dumps({p.name:p.stat().st_size for p in served},indent=2))
    print('Served total:',sum(p.stat().st_size for p in served))
    if args.reference_dir:
        compare(frames,args.reference_dir)


if __name__=='__main__':
    main()
