"""Local review sheets; official references are read-only and never committed."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'assets/ui_icons/gwen'
WORK = ROOT / '_tmp/art6'
NAMES = ('confident', 'thoughtful', 'notes', 'st_cry', 'st_verdict',
         'st_cheer', 'st_ok', 'st_point', 'st_shy', 'st_sulk', 'st_wink',
         'st_zap', 'st_welcome')
R = Image.Resampling.LANCZOS


def tile(sheet, path, label, index, cols=6, crop=None):
    x, y = (index % cols)*256, (index // cols)*280
    pic = Image.open(path).convert('RGBA')
    if crop:
        pic = pic.crop(crop)
    pic = ImageOps.contain(pic, (240, 240), R)
    sheet.paste(pic, (x+8+(240-pic.width)//2, y+24+(240-pic.height)//2), pic)
    ImageDraw.Draw(sheet).text((x+8, y+6), label, fill='white')


def before(ref):
    WORK.mkdir(parents=True, exist_ok=True)
    backup = WORK / 'before'
    backup.mkdir(exist_ok=True)
    # Never overwrite the pre-edit evidence on a later review run.
    for path in list(ART.glob('*.png')) + list(ART.glob('*.webp')):
        target = backup / path.name
        if not target.exists():
            target.write_bytes(path.read_bytes())
    for folder in ('masters2', 'masters5'):
        destination = backup / folder
        destination.mkdir(exist_ok=True)
        for path in (ROOT/'tools/gwen_art'/folder).glob('*.webp'):
            if not (destination/path.name).exists():
                (destination/path.name).write_bytes(path.read_bytes())
    manifest = WORK / 'before-sha256.json'
    if not manifest.exists():
        manifest.write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in backup.iterdir() if p.is_file()}, indent=2), encoding='utf-8')
    refs = [(ref/'official_cry_podium.png', 'official cry', (320, 0, 905, 610)),
            (ROOT/'assets/savior/gwen_art.webp', 'official card (portrait crop)', (128, 100, 271, 245)),
            (ref/'story_s_039120.jpg', 'story 039120', (95, 0, 505, 300)),
            (ref/'story_s_040560.jpg', 'story 040560', (95, 0, 505, 300)),
            (ref/'play_p_046.jpg', 'model 046', (350, 25, 560, 235)),
            (ref/'play_p_014.jpg', 'model 014', (180, 60, 430, 310)),
            (backup/'st_cry.png', 'PM style: st_cry', None)]
    items = refs + [(backup/(n+'.png'), n, None) for n in NAMES]
    sheet = Image.new('RGB', (1536, ((len(items)+5)//6)*280), '#172034')
    for i, (p, label, crop) in enumerate(items):
        tile(sheet, p, label, i, crop=crop)
    sheet.save(ROOT/'_tmp/_art_style6_before.png')
    sd = sorted(p for p in ART.glob('*.png') if not p.stem.startswith('st_')
                and p.stem not in NAMES and not p.stem.endswith(('_512', '_blink')))
    sheet = Image.new('RGB', (1536, ((len(sd)+5)//6)*280), '#172034')
    for i, p in enumerate(sd):
        source = ART/(p.stem+'_512.png')
        tile(sheet, source if source.exists() else p, p.stem, i)
    sheet.save(ROOT/'_tmp/_art_sd6_sleeves.png')
    detail = Image.new('RGB', (1600, ((len(sd)+4)//5)*240), '#28334b')
    for i, p in enumerate(sd):
        source = ART/(p.stem+'_512.png')
        pic = Image.open(source if source.exists() else p).convert('RGBA')
        if pic.size != (512, 512):
            pic = pic.resize((512, 512), R)
        pic = pic.crop((70, 200, 442, 420)).resize((310, 184), R)
        x, y = i % 5*320, i // 5*240
        detail.paste(pic, (x, y+25), pic)
        ImageDraw.Draw(detail).text((x+5, y+5), p.stem, fill='white')
    detail.save(WORK/'sd-sleeves-detail.png')
    print('SD count:', len(sd), [p.stem for p in sd])


def doya():
    sheet = Image.new('RGB', (810, 850), '#172034')
    for col, angle in enumerate((10, 18, 25)):
        pic = Image.open(WORK/f'generated/doya{angle}-1.png').convert('RGBA')
        pic = pic.crop(pic.getchannel('A').point(lambda a: 255 if a > 100 else 0).getbbox())
        for row, size in enumerate((120, 160, 240)):
            thumb = ImageOps.contain(pic, (size-12, size-12), R)
            x, y = col*270+(270-thumb.width)//2, row*280+30+(240-thumb.height)
            sheet.paste(thumb, (x, y), thumb)
            ImageDraw.Draw(sheet).text((col*270+10, row*280+8), f'{angle} deg prompt / {size}px', fill='white')
    sheet.save(ROOT/'_tmp/_art_doya6.png')


def after():
    sheet = Image.new('RGB', (1100, 280*len(NAMES)), '#172034')
    for row, name in enumerate(NAMES):
        y = row*280
        ImageDraw.Draw(sheet).text((8, y+8), name+' | before / after 120 / 160 / 240', fill='white')
        for path, x, size in [(WORK/'before'/(name+'.png'), 10, 240),
                              (ART/(name+'.png'), 280, 120),
                              (ART/(name+'.png'), 430, 160),
                              (ART/(name+'.png'), 620, 240)]:
            pic = Image.open(path).convert('RGBA').resize((size, size), R)
            sheet.paste(pic, (x, y+30+240-size), pic)
    sheet.save(ROOT/'_tmp/_art_style6_after.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-dir', type=Path)
    parser.add_argument('--after', action='store_true')
    parser.add_argument('--doya', action='store_true')
    args = parser.parse_args()
    if args.reference_dir:
        before(args.reference_dir)
    if args.after:
        after()
    if args.doya:
        doya()
    if not (args.reference_dir or args.after or args.doya):
        parser.error('Choose --reference-dir, --after or --doya')
