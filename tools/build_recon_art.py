"""«현장 재조사»(자동 추천 끝의 자리·리더 비교) 연출 그림을 만듦 → assets/recon/. Pillow 필요.

python -X utf8 tools/build_recon_art.py --src <recon_office_bg_1.png>
    사무실 배경(2172×724) → office.webp(1800×600) · office_narrow.webp(좁은 화면 자르기)
    재조사 SD 그웬 3종(assets/ui_icons/gwen/recon_*_512.png, 저장소 안) → gwen_look/pin/nod.webp(240px)

원본 배경은 저장소 밖에 두고 결과물만 넣음(build_forced_art.py 와 같은 방식). 그림 좌표(보드 빈 칸·창밖 고리·바닥)는
recheck.css 의 --rc-* 값이 정본이며, 좁은 화면 값은 NARROW 구간으로 환산한 것임 — 이 구간을 바꾸면 recheck.css 도 같이 고칠 것.
"""
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/recon'
GWEN = ROOT / 'assets/ui_icons/gwen'
NARROW = (0.27, 0.87)   # 좁은 화면(≤520px): 가로로 이 구간만 — 보드 빈 칸(32~37%)·창밖 고리(63~78%)가 함께 들어오게
WIDE_W, NARROW_W, GWEN_PX = 1800, 720, 240
QUALITY = 70            # 두 장 합계 150KB 안(재조사에 처음 들어갈 때만 받음)
BUDGET = 150_000


def build_office(src):
    im = Image.open(src).convert('RGB')
    wide = im.resize((WIDE_W, round(im.height * WIDE_W / im.width)), Image.LANCZOS)
    wide.save(OUT / 'office.webp', quality=QUALITY, method=6)
    x0, x1 = (round(im.width * t) for t in NARROW)
    part = im.crop((x0, 0, x1, im.height))
    part = part.resize((NARROW_W, round(part.height * NARROW_W / part.width)), Image.LANCZOS)
    part.save(OUT / 'office_narrow.webp', quality=QUALITY, method=6)
    return part.width / part.height


def build_gwen():
    for pose in ('look', 'pin', 'nod'):
        im = Image.open(GWEN / f'recon_{pose}_512.png').convert('RGBA')
        im.resize((GWEN_PX, GWEN_PX), Image.LANCZOS).save(OUT / f'gwen_{pose}.webp', quality=86, method=6)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', type=Path, required=True, help='사무실 원본 recon_office_bg_1.png')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ratio = build_office(args.src)
    build_gwen()
    files = sorted(p for p in OUT.iterdir() if p.is_file())
    for p in files:
        print(f'{p.stat().st_size:8,d}  {p.relative_to(ROOT).as_posix()}')
    office = sum((OUT / f).stat().st_size for f in ('office.webp', 'office_narrow.webp'))
    print(f'{office:8,d}  배경 두 장 합계(한도 {BUDGET:,d})')
    print(f'office_narrow 가로÷세로 = {ratio:.4f} (recheck.css --rc-ar)')
    if office > BUDGET:
        raise SystemExit('배경 두 장이 한도를 넘음 — QUALITY 를 낮출 것')


if __name__ == '__main__':
    main()
