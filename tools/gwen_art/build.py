"""Rebuild small assets from approved 512px RGBA masters; optionally import tool output.

python -X utf8 tools/gwen_art/build.py --import-dir _tmp/gwen_art --compare
python -X utf8 tools/gwen_art/build.py --compare
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/ui_icons/gwen'
NAMES = ('investigate', 'files', 'report', 'surprised', 'welcome')
RESAMPLE = Image.Resampling.LANCZOS


def master(path):
    src = Image.open(path).convert('RGBA')
    assert src.getchannel('A').getextrema() == (0, 255), 'Real alpha required'
    src.thumbnail((464, 464), RESAMPLE)
    dst = Image.new('RGBA', (512, 512))
    dst.alpha_composite(src, ((512-src.width)//2, (512-src.height)//2))
    return dst


def investigate_frames(src):
    # Tool output normalized to 464px with 24px padding. Only the exposed glass,
    # glove and outer sleeve move. Keep shoulder overlap to avoid a broken joint.
    points = [(0,160),(122,160),(122,259),(151,276),(182,279),(182,330),(0,330)]
    mask = Image.new('L', src.size)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    moving = src.copy()
    moving.putalpha(ImageChops.multiply(src.getchannel('A'), mask))
    base = src.copy()
    base.putalpha(ImageChops.multiply(src.getchannel('A'), ImageChops.invert(mask)))
    # Extend the existing sleeve texture under the moving joint, never repaint face.
    seam = src.crop((179,286,184,321))
    base.alpha_composite(seam.resize((12,35)), (174,286))
    frames = []
    for dx in (0,-2,-4,-2):
        frame = base.copy()
        frame.alpha_composite(moving, (dx,0))
        frames.append(frame)
    frames[0] = src.copy()
    return frames


def files_frames(src):
    # A paper leaf taken from the approved drawing opens over the folder. The
    # original face, body and hands remain pixel-identical in every 512px frame.
    leaf = src.crop((211,316,266,328))
    frames = []
    for height in (12,22,30,22):
        frame = src.copy()
        page = leaf.resize((55,height), RESAMPLE)
        frame.alpha_composite(page, (211,328-height))
        frames.append(frame)
    frames[0] = src.copy()
    return frames


def compare(masters):
    sheet = Image.new('RGB',(1200,660),'#edf0f5')
    draw = ImageDraw.Draw(sheet)
    ref = Image.open(ROOT/'assets/ui_icons/gwen_sd.png').convert('RGBA')
    ref.thumbnail((160,160),RESAMPLE)
    sheet.paste(ref,(20,75),ref)
    draw.text((20,20),'Official SD reference',fill='#192239')
    for i,name in enumerate(NAMES):
        x=200+i*200
        draw.text((x+10,20),name,fill='#192239')
        pic=masters[name].resize((200,200),RESAMPLE)
        sheet.paste(pic,(x,55),pic)
        draw.rectangle((x,275,x+199,480),fill='#111b30')
        pic=masters[name].resize((160,160),RESAMPLE)
        sheet.paste(pic,(x+20,295),pic)
        draw.text((x+10,490),'160px / dark UI',fill='#192239')
    for i,(name,fn) in enumerate((('investigate',investigate_frames),('files',files_frames))):
        for j,frame in enumerate(fn(masters[name])):
            pic=frame.resize((120,120),RESAMPLE)
            sheet.paste(pic,(200+i*500+j*120,530),pic)
    sheet.save(ROOT/'_art_compare.png')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--import-dir',type=Path)
    ap.add_argument('--compare',action='store_true')
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.import_dir:
        for name in NAMES:
            master(args.import_dir/(name+'.png')).save(OUT/(name+'_512.png'),optimize=True)
    masters={name:Image.open(OUT/(name+'_512.png')).convert('RGBA') for name in NAMES}
    for name,src in masters.items():
        assert src.size == (512,512)
        src.resize((160,160),RESAMPLE).save(OUT/(name+'.png'),optimize=True)
    for name,fn in (('investigate',investigate_frames),('files',files_frames)):
        frames=[f.resize((160,160),RESAMPLE) for f in fn(masters[name])]
        path=OUT/(name+'.webp')
        frames[0].save(path,save_all=True,append_images=frames[1:],duration=[320,220,320,220],loop=0,lossless=True,method=6)
        assert path.stat().st_size<=80000
        with Image.open(path) as im:
            assert 2<=im.n_frames<=4 and im.info['loop']==0
    if args.compare:
        compare(masters)
    for p in sorted(OUT.glob('*')):
        print(f'{p.name}: {p.stat().st_size:,} bytes')


if __name__=='__main__':
    main()
