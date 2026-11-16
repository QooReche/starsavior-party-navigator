"""Apply generated sleeve patches while preserving approved cry pixels elsewhere."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PATCHES = HERE/'patches6'


def sleeve_mask(frame=0, size=320):
    specs = json.loads((PATCHES/'cry_sleeves.json').read_text(encoding='utf-8'))
    mask = Image.new('L', (320, 320))
    for poly in specs[str(frame)]:
        ImageDraw.Draw(mask).polygon([tuple(p) for p in poly], fill=255)
    if size != 320:
        mask = mask.resize((size, size), Image.Resampling.LANCZOS).point(lambda a: 255 if a else 0)
    return mask


def apply_sleeves(frames):
    sheet = Image.open(PATCHES/'cry_sleeves.webp').convert('RGBA')
    output = []
    for i, src in enumerate(frames):
        patch = sheet.crop((i*320, 0, (i+1)*320, 320))
        dst = Image.composite(patch, src, sleeve_mask(i))
        dst.putalpha(src.getchannel('A'))
        output.append(dst)
    return output


def preserve_static(rendered, blink=False):
    original = Image.open(PATCHES/('cry_blink.png' if blink else 'cry_base.png')).convert('RGBA')
    result = Image.composite(rendered, original, sleeve_mask(0, 240))
    result.putalpha(original.getchannel('A'))
    return result
