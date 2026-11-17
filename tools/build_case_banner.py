"""Render original Korean detective titles; no client texture is redistributed.

Usage: python tools/build_case_banner.py <NotoSansKR-VF.ttf>
Noto Sans KR (SIL OFL 1.1), weight 900. See gwen_art/lane.md.
The shipped WebPs require no font or network requests at runtime.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    'investigation': ('조사 완료!', 'result'),
    'inquiry': ('수사 완료!', 'result'),
    'calculation': ('계산 완료!', 'result'),
    'error': ('수사 난항…', 'error'),
}


def render(font_path, text, kind):
    size = (960, 240)
    font = ImageFont.truetype(str(font_path), 135)
    font.set_variation_by_axes([900])
    mask = Image.new('L', size)
    d = ImageDraw.Draw(mask)
    box = d.textbbox((0, 0), text, font=font)
    xy = ((size[0] - (box[2]-box[0]))/2-box[0], (size[1]-(box[3]-box[1]))/2-box[1]-8)
    d.text(xy, text, font=font, fill=255)
    out = Image.new('RGBA', size)
    draw = ImageDraw.Draw(out)
    draw.text((xy[0]+3, xy[1]+9), text, font=font, fill='#15243e', stroke_width=13, stroke_fill='#15243e')
    draw.text(xy, text, font=font, fill='#fff9df', stroke_width=6, stroke_fill='#fff9df')
    top, bottom = ((255,255,241),(240,182,68)) if kind=='result' else ((216,224,234),(157,174,195))
    gradient = Image.new('RGBA', size)
    gd = ImageDraw.Draw(gradient)
    for y in range(size[1]):
        t = max(0, min(1, (y-55)/135))
        gd.line((0,y,size[0],y), fill=tuple(round(a+(b-a)*t) for a,b in zip(top,bottom))+(255,))
    out.paste(gradient, (0,0), mask)
    # Small forward lean; all pixels stay within the reserved canvas.
    out = out.transform(size, Image.Transform.AFFINE, (1,.10,-12,0,1,0), Image.Resampling.BICUBIC)
    return out.resize((640,160), Image.Resampling.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('font', type=Path)
    args = ap.parse_args()
    sizes = {}
    for name, (title, kind) in TITLES.items():
        target = ROOT / f'assets/ui_icons/case_banner_{name}.webp'
        render(args.font, title, kind).save(target, quality=90, method=6)
        sizes[target.name] = target.stat().st_size
        assert sizes[target.name] <= 80000
    budget = ROOT/'tools/gwen_art/budget.json'
    data = json.loads(budget.read_text(encoding='utf-8'))
    data['case_banner'] = {'file_bytes':80000, 'served_bytes':sum(sizes.values()), 'files':sizes}
    budget.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(sizes, indent=2))


if __name__ == '__main__':
    main()
