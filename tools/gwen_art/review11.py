"""480px forearm review of all 13 portraits and the complete repaired set."""
from pathlib import Path
from PIL import Image, ImageDraw
import build5
import sleeve11

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'_tmp/art11'
NAMES = ('confident', 'thoughtful', 'notes') + build5.NAMES


def row(root, stem, label):
    sheet = Image.new('RGB', (2400, 520), '#c8c8c8')
    draw = ImageDraw.Draw(sheet)
    col = 0
    for suffix in ('.png', '.webp', '_blink.png'):
        path = root/(stem+suffix)
        if not path.exists():
            continue
        with Image.open(path) as im:
            for i in range(im.n_frames):
                im.seek(i)
                pic = im.convert('RGBA').resize((480, 480), Image.Resampling.LANCZOS)
                sheet.paste(pic, (col*480, 40), pic)
                draw.text((col*480+10, 10), label+' '+suffix+(f' F{i}' if suffix == '.webp' else ''), fill='black')
                col += 1
    return sheet


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        row(build5.OUT, name, name).save(WORK/(name+'-audit-after.png'))
    before = row(sleeve11.PATCHES, 'st_shy_base', 'st_shy BEFORE')
    after = row(build5.OUT, 'st_shy', 'st_shy AFTER')
    sheet = Image.new('RGB', (2400, 1040))
    sheet.paste(before, (0, 0))
    sheet.paste(after, (0, 520))
    sheet.save(ROOT/'_tmp/_art11.png')


if __name__ == '__main__':
    main()
