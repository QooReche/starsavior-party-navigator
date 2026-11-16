"""Local generated band repairs; keep approved pixels outside sleeve masks."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

PATCHES = Path(__file__).resolve().parent / 'patches7'
NAMES = ('st_point', 'st_sulk')
LEGACY_NAMES = ('thoughtful',)


def sleeve_mask(name, frame=0, size=320):
    specs = json.loads((PATCHES/'sleeves.json').read_text(encoding='utf-8'))
    mask = Image.new('L', (320, 320))
    polygon = specs[name][frame]
    if polygon:
        ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=255)
    if size != 320:
        mask = mask.resize((size, size), Image.Resampling.LANCZOS).point(lambda a: 255 if a else 0)
    return mask


def apply(name, frames):
    if name not in NAMES + LEGACY_NAMES:
        return frames
    with Image.open(PATCHES/(name+'.webp')) as im:
        sheet = im.convert('RGBA')
    result = []
    for i, src in enumerate(frames):
        patch = sheet.crop((i*320, 0, (i+1)*320, 320))
        dst = Image.composite(patch, src, sleeve_mask(name, i))
        dst.putalpha(src.getchannel('A'))
        result.append(dst)
    return result


def preserve_static(name, rendered, original_master):
    """Reproduce the pre-edit PNG palette, then replace only the sleeve."""
    src = original_master.resize((240, 240), Image.Resampling.LANCZOS)
    original = src.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                            dither=Image.Dither.NONE).convert('RGBA')
    original.putalpha(src.getchannel('A'))
    result = Image.composite(rendered, original, sleeve_mask(name, size=240))
    result.putalpha(original.getchannel('A'))
    return result
