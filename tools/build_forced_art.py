"""«강제 탐색»(후보 전체 훑기) 연출 그림을 만듦 → assets/forced/. Pillow 필요.

python -X utf8 tools/build_forced_art.py --gen-dir <폴더>
    레인 배경(lavistar_ruin_bg_1.png → scene.webp·scene_narrow.webp)
    뒷모습(gwen_back_illust_1.png → gwen_back.webp, 머리~허벅지만)
    신분증 사진(gwen_idcard_illust_1.png → gwen_idcard.webp)

원본 그림은 저장소 밖에 두고 결과물만 넣음. 출처·바꿔 끼우는 법은 docs/forced_art.md.
"""
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/forced'
NARROW = (0.17, 0.65)   # 좁은 화면용: 가로로 이 구간만(의자~광장)
BACK_KEEP = 0.62        # 뒷모습: 위에서 이 비율(머리~허벅지 중간)만 — 아래는 화면에서 띠 밖으로 잘리는 부분이라 넣지 않음
BACK_H = 520
IDCARD = 256


def build_scene(src):
    im = Image.open(src).convert('RGB')
    im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS).save(OUT / 'scene.webp', quality=72, method=6)
    x0, x1 = (round(im.width * t) for t in NARROW)
    part = im.crop((x0, 0, x1, im.height))
    part.resize((800, round(part.height * 800 / part.width)), Image.LANCZOS).save(OUT / 'scene_narrow.webp', quality=72, method=6)


def build_back(src):
    im = Image.open(src).convert('RGBA')
    im = im.crop(im.getbbox())
    im = im.crop((0, 0, im.width, round(im.height * BACK_KEEP)))
    im = im.crop(im.getbbox())
    im.resize((round(im.width * BACK_H / im.height), BACK_H), Image.LANCZOS).save(OUT / 'gwen_back.webp', quality=84, method=6)
    return im.width / im.height


def build_idcard(src):
    Image.open(src).convert('RGB').resize((IDCARD, IDCARD), Image.LANCZOS).save(OUT / 'gwen_idcard.webp', quality=82, method=6)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--gen-dir', type=Path, required=True)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    build_scene(args.gen_dir / 'lavistar_ruin_bg_1.png')
    ratio = build_back(args.gen_dir / 'gwen_back_illust_1.png')
    build_idcard(args.gen_dir / 'gwen_idcard_illust_1.png')
    files = sorted(p for p in OUT.rglob('*') if p.is_file())
    for p in files:
        print(f'{p.stat().st_size:8,d}  {p.relative_to(ROOT).as_posix()}')
    print(f'{sum(p.stat().st_size for p in files):8,d}  합계({len(files)}개)')
    print(f'gwen_back 가로÷세로 = {ratio:.4f} (forced.css .fx-gwen aspect-ratio)')


if __name__ == '__main__':
    main()
