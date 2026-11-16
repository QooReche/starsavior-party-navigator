"""Create the 480px notes before/after sheet from committed originals."""
from pathlib import Path
from PIL import Image, ImageDraw
import sleeve8

ROOT = Path(__file__).resolve().parents[2]


def main():
    sheet = Image.new('RGB', (1920, 1020), '#e5e7eb')
    draw = ImageDraw.Draw(sheet)
    for row, (root, stem) in enumerate(((sleeve8.PATCHES, 'notes_base'),
                                       (ROOT/'assets/ui_icons/gwen', 'notes'))):
        with Image.open(root/(stem+'.png')) as im:
            pictures = [im.convert('RGBA')]
        with Image.open(root/(stem+'.webp')) as im:
            for i in range(im.n_frames):
                im.seek(i)
                pictures.append(im.convert('RGBA'))
        for col, pic in enumerate(pictures):
            pic = pic.resize((480, 480), Image.Resampling.LANCZOS)
            sheet.paste(pic, (col*480, row*510+30), pic)
            label = ('BEFORE ' if row == 0 else 'AFTER ') + ['PNG', 'WebP F0', 'WebP F1 / BLINK', 'WebP F2'][col]
            draw.text((col*480+12, row*510+8), label, fill='#111')
    (ROOT/'_tmp').mkdir(exist_ok=True)
    sheet.save(ROOT/'_tmp/_art_sleeve8_notes.png')


if __name__ == '__main__':
    main()
