"""Compare before/excessive/three restrained face strengths at actual UI sizes.

Uses committed source/patches plus the rejected commit d6f096d; no private input.
"""
import io
import subprocess
from PIL import Image, ImageDraw
import build2
import build5
import face9
import sleeve7


def excessive(name):
    data = subprocess.check_output(
        ['git', '-c', 'safe.directory='+str(build2.ROOT), 'show',
         'd6f096d:assets/ui_icons/gwen/'+name+'.png'], cwd=build2.ROOT)
    return Image.open(io.BytesIO(data)).convert('RGBA')


def candidate(name, strength):
    frames = build2.cells(Image.open(build5.MASTERS/(name+'.webp')).convert('RGBA'), 3)
    edited = face9.apply(name, frames)
    mixed = [Image.blend(a, b, strength) for a, b in zip(frames, edited)]
    pic = sleeve7.apply(name, mixed)[0].resize((240,240), build2.R)
    alpha = pic.getchannel('A')
    pic = pic.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                       dither=Image.Dither.NONE).convert('RGBA')
    pic.putalpha(alpha)
    return face9.preserve_static(name, pic)


def main():
    root = build2.ROOT/'_tmp'
    (root/'art10').mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (1300,1220), '#111b30')
    draw = ImageDraw.Draw(sheet)
    motion = Image.new('RGB', (1000,560), '#111b30')
    md = ImageDraw.Draw(motion)
    for row, name in enumerate(face9.NAMES):
        before = Image.open(face9.PATCHES/(name+'-before.png')).convert('RGBA')
        final = Image.open(build2.OUT/(name+'.png')).convert('RGBA')
        choices = [('BEFORE',before), ('EXCESSIVE d6f096d',excessive(name)),
                   ('A 55%',candidate(name,.55)), ('B 78%',candidate(name,.78)),
                   ('C 100% NEW face - SELECTED',final)]
        y0 = row*610
        draw.text((10,y0+5), name+' | percentages refer to NEW restrained patch, not excessive art', fill='white')
        for col,(label,pic) in enumerate(choices):
            x = 10+col*258
            draw.text((x,y0+25),label,fill='#f7dc8b' if col==4 else 'white')
            y = y0+45
            for size in (120,160,240):
                thumb = pic.resize((size,size),build2.R)
                sheet.paste(thumb,(x,y),thumb)
                draw.text((x+size+2 if size<240 else x,y+size-12),str(size)+'px',fill='#ccddee')
                y += size+12
        frames = [('PNG',final)]
        with Image.open(build2.OUT/(name+'.webp')) as im:
            for i in (0,1):
                im.seek(i)
                frames.append(('WebP F'+str(i),im.convert('RGBA')))
        frames.append(('blink',Image.open(build2.OUT/(name+'_blink.png')).convert('RGBA')))
        for col,(label,pic) in enumerate(frames):
            motion.paste(pic,(col*250,row*280+25),pic)
            md.text((col*250,row*280+5),name+' '+label,fill='white')
    sheet.save(root/'_art10.png')
    motion.save(root/'art10/motion-blink.png')
    print('_tmp/_art10.png')


if __name__ == '__main__':
    main()
