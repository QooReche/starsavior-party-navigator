"""Generated lower-sleeve repair over the approved art10 rendered frames."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
PATCHES = HERE / 'patches11'
R = Image.Resampling.LANCZOS


def sleeve_mask(frame=0, size=240, soft=False):
    spec = json.loads((PATCHES/'sleeves.json').read_text(encoding='utf-8'))
    mask = Image.new('L', (320, 320))
    for polygon in spec['frames'][frame % 2]:
        ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(spec['feather']))
    if not soft:
        mask = mask.point(lambda a: 255 if a else 0)
    if size != 320:
        mask = mask.resize((size, size), R)
        if not soft:
            mask = mask.point(lambda a: 255 if a else 0)
    return mask


def repair(src, frame=0):
    with Image.open(PATCHES/'st_shy.webp') as im:
        patch = im.convert('RGBA').crop((frame % 2*320, 0, (frame % 2+1)*320, 320))
    base = src.resize((320, 320), R)
    edited = Image.composite(patch, base, sleeve_mask(frame, 320, soft=True))
    edited = edited.resize(src.size, R)
    dst = Image.composite(edited, src, sleeve_mask(frame, src.width))
    dst.putalpha(src.getchannel('A'))
    return dst


def frames():
    result = []
    with Image.open(PATCHES/'st_shy_base.webp') as im:
        for i in range(im.n_frames):
            im.seek(i)
            result.append(repair(im.convert('RGBA'), i if i < 2 else 0))
    return result


def encode(out, blink=True):
    # The existing approved PNG and blink palette stays exact outside sleeves.
    for suffix in (('.png', '_blink.png') if blink else ('.png',)):
        with Image.open(PATCHES/('st_shy_base'+suffix)) as im:
            repair(im.convert('RGBA')).save(out/('st_shy'+suffix), optimize=True)
    edited = frames()
    edited[0].save(out/'st_shy.webp', save_all=True, append_images=edited[1:],
                   duration=[450, 220, 330], loop=1, quality=95, method=6, exact=True)
    budget = json.loads((HERE/'budget.json').read_text(encoding='utf-8'))
    assert (out/'st_shy.webp').stat().st_size <= budget['file_bytes']
