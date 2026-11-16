"""Notes-only sleeve repair over approved decoded pixels, with lossless PNG and visually faithful lossy motion."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PATCHES = HERE / 'patches8'
R = Image.Resampling.LANCZOS


def sleeve_mask(frame=0, size=240):
    polygons = json.loads((PATCHES/'sleeves.json').read_text(encoding='utf-8'))['frames'][frame % 2]
    mask = Image.new('L', (320, 320))
    for polygon in polygons:
        ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=255)
    # Include the resampling support, but keep every other original pixel exact.
    return mask.resize((size, size), R).point(lambda a: 255 if a else 0)


def repair(src, frame=0):
    with Image.open(PATCHES/'notes.webp') as im:
        patch = im.convert('RGBA').crop((frame % 2*320, 0, (frame % 2+1)*320, 320))
    # Composite at source resolution first to avoid a transparent fringe at the mask.
    base = src.resize((320, 320), R)
    patch = Image.composite(patch, base, sleeve_mask(frame, 320)).resize(src.size, R)
    result = Image.composite(patch, src, sleeve_mask(frame, src.width))
    result.putalpha(src.getchannel('A'))
    return result


def encode(out, duration, loop, static=True):
    if static:
        with Image.open(PATCHES/'notes_base.png') as im:
            repair(im.convert('RGBA')).save(out/'notes.png', optimize=True)
    frames = []
    with Image.open(PATCHES/'notes_base.webp') as im:
        for i in range(im.n_frames):
            im.seek(i)
            frames.append(repair(im.convert('RGBA'), i if i < 2 else 0))
    frames[0].save(out/'notes.webp', save_all=True, append_images=frames[1:],
                   duration=duration, loop=loop, lossless=False, quality=95, exact=True, method=6)
    budget = json.loads((HERE/'budget.json').read_text(encoding='utf-8'))
    assert (out/'notes.webp').stat().st_size <= budget['file_bytes']
    return frames
