"""공식 그림을 자르고 배경만 제거함. Pillow 필요, 그림 생성·색 보정 없음.

python -X utf8 tools/make_gwen_icons.py --source-dir <21.webp와 22.png 폴더>
원본은 저장소 밖에 두며 결과물만 assets/ui_icons에 저장함.
--preview _shot_icons.png 로 밝은/어두운 배경 미리보기도 만들 수 있음.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
# 21.webp의 차분한 SD 얼굴. 좌표는 (0, 1380, 125, 1490) 영역 기준.
# 흰 외곽선 바깥을 따라 손으로 지정한 배경 제거 마스크. 얼굴 내부 RGB는 보존함.
OUTLINE = [
    (18, 67), (20, 58), (23, 48), (27, 39), (33, 31), (41, 24),
    (48, 19), (54, 16), (62, 14), (72, 15), (82, 16), (92, 20),
    (100, 26), (106, 34), (111, 43), (114, 54), (115, 63),
    (114, 69), (111, 74), (110, 82), (108, 88), (106, 87),
    (103, 90), (98, 92), (88, 95), (91, 88), (84, 90),
    (77, 91), (68, 91), (59, 89), (64, 95), (59, 96),
    (51, 94), (48, 93), (49, 95), (45, 97), (41, 97),
    (36, 94), (32, 90), (33, 92), (31, 91), (27, 87),
    (24, 83), (24, 77), (21, 75), (19, 72),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--preview', type=Path)
    args = ap.parse_args()
    dest = ROOT / 'assets/ui_icons'
    dest.mkdir(parents=True, exist_ok=True)
    with Image.open(args.source_dir / '21.webp') as comic:
        if comic.size != (947, 2000):
            raise ValueError('21.webp 원본 크기가 달라 자르기 좌표 확인 필요')
        face = comic.convert('RGBA').crop((0, 1380, 125, 1490))
    mask = Image.new('L', face.size)
    ImageDraw.Draw(mask).polygon(OUTLINE, fill=255)
    face.putalpha(mask)
    face = face.crop(mask.getbbox())
    face.save(dest / 'gwen_sd.png', optimize=True)
    icons = []
    for size in (32, 72, 180, 512):
        icon = Image.new('RGBA', (size, size))
        # 512는 요청된 아이콘 규격에 맞춘 확대본이며 원본보다 세밀해지지는 않음.
        scale = (size - max(2, round(size / 36))) / max(face.size)
        small = face.resize(tuple(round(x * scale) for x in face.size), Image.Resampling.LANCZOS)
        icon.alpha_composite(small, ((size - small.width) // 2, (size - small.height) // 2))
        name = 'gwen_header_72.png' if size == 72 else f'gwen_favicon_{size}.png'
        icon.save(dest / name, optimize=True)
        icons.append((size, icon))
    with Image.open(args.source_dir / '22.png') as source:
        art = source.convert('RGBA')
        art.thumbnail((240, 240), Image.Resampling.LANCZOS)
    art_path = dest / 'gwen_card.webp'
    art.save(art_path, 'WEBP', lossless=True, method=6)
    if art_path.stat().st_size > 60 * 1024:
        raise ValueError('카드 축소본 60KB 초과')
    if args.preview:
        preview = args.preview.resolve()
        if not preview.is_relative_to(ROOT):
            raise ValueError('미리보기는 작업 폴더 안에만 저장 가능')
        sheet = Image.new('RGB', (860, 650), '#e6e9ef')
        draw = ImageDraw.Draw(sheet)
        draw.rectangle((0, 325, 860, 650), fill='#141820')
        for row, color in ((0, '#141820'), (325, '#e6e9ef')):
            x = 20
            for size, icon in icons:
                shown = icon.copy()
                shown.thumbnail((220, 220))
                sheet.paste(shown, (x, row + 40), shown)
                draw.text((x, row + 15), f'{size}px', fill=color)
                x += max(60, shown.width + 25)
            shown = art.copy()
            shown.thumbnail((150, 240))
            sheet.paste(shown, (715, row + 40), shown)
            draw.text((715, row + 15), 'card / 22.png', fill=color)
        sheet.save(preview)
    print('SD 32/72/180/512px; card %s, %d bytes' % (art.size, art_path.stat().st_size))


if __name__ == '__main__':
    main()
