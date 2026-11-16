"""Generated expression patches; preserve approved pixels outside the face."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

PATCHES = Path(__file__).resolve().parent / 'patches9'
NAMES = ('st_sulk', 'st_shy')


def face_mask(name, size=320, soft=False):
    spec = json.loads((PATCHES/'faces.json').read_text(encoding='utf-8'))[name]
    mask = Image.new('L', (320, 320))
    ImageDraw.Draw(mask).polygon([tuple(p) for p in spec['polygon']], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    if not soft:
        mask = mask.point(lambda a: 255 if a else 0)
    if size != 320:
        mask = mask.resize((size, size), Image.Resampling.LANCZOS).point(lambda a: 255 if a else 0)
    return mask


def apply(name, frames):
    if name not in NAMES:
        return frames
    with Image.open(PATCHES/(name+'.webp')) as im:
        sheet = im.convert('RGBA')
    result = []
    for i, src in enumerate(frames):
        patch = sheet.crop((i*320, 0, (i+1)*320, 320))
        dst = Image.composite(patch, src, face_mask(name, soft=True))
        # Natural cheeks: never expand the original face or hair silhouette.
        dst.putalpha(src.getchannel('A'))
        result.append(dst)
    return result


def preserve_static(name, rendered):
    """Keep the approved PNG palette and pixels outside the face footprint."""
    with Image.open(PATCHES/(name+'-before.png')) as im:
        original = im.convert('RGBA')
    result = Image.composite(rendered, original, face_mask(name, 240))
    return result
