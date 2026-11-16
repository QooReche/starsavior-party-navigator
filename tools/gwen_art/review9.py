"""Actual-size expression review: old/new 120, 160, 240px plus action/blink."""
from pathlib import Path
from PIL import Image, ImageDraw
import build2
import face9


def main():
    sheet = Image.new('RGB', (1340, 1120), '#111b30')
    draw = ImageDraw.Draw(sheet)
    for n, name in enumerate(face9.NAMES):
        for after in (False, True):
            y = (n*2+int(after))*280
            draw.text((12, y+8), name + (' AFTER' if after else ' BEFORE'), fill='white')
            src = Image.open((build2.OUT/(name+'.png')) if after else
                             (face9.PATCHES/(name+'-before.png'))).convert('RGBA')
            x = 15
            for size in (120, 160, 240):
                pic = src.resize((size, size), build2.R)
                sheet.paste(pic, (x, y+265-size), pic)
                draw.text((x, y+267), f'{size}px', fill='white')
                x += size+20
            if after:
                with Image.open(build2.OUT/(name+'.webp')) as im:
                    for i in (0, 1):
                        im.seek(i); pic = im.convert('RGBA')
                        sheet.paste(pic, (x, y+25), pic)
                        draw.text((x, y+267), f'WebP F{i}', fill='white')
                        x += 250
                pic = Image.open(build2.OUT/(name+'_blink.png')).convert('RGBA')
                sheet.paste(pic, (x, y+25), pic)
                draw.text((x, y+267), 'blink', fill='white')
    path = build2.ROOT/'_tmp/_art9.png'
    path.parent.mkdir(exist_ok=True)
    sheet.save(path)
    print(path.relative_to(build2.ROOT))


if __name__ == '__main__':
    main()
