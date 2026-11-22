"""«강제 탐색»(후보 전체 훑기) 연출 그림을 만듦 → assets/forced/. Pillow·numpy 필요.

python -X utf8 tools/build_forced_art.py                      # 오염 그웬(저장소 안 그림만 씀)
python -X utf8 tools/build_forced_art.py --gen-dir <폴더>     # + 레인 배경(lavistar_ruin_bg_1.png → scene.webp·scene_narrow.webp)
                                                              #   + 뒷모습(gwen_back_illust_1.png → gwen_back.webp)
python -X utf8 tools/build_forced_art.py --all-gwen           # 깜빡임 그림이 있는 SD 표정 전부(기본은 화면이 쓰는 4개)

원본(배경·뒷모습 그림)은 저장소 밖에 두고 결과물만 넣음. 출처·바꿔 끼우는 법은 docs/forced_art.md.
같은 입력이면 같은 결과가 나옴(난수 씨앗 = 표정 이름).
"""
import argparse
import math
import random
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'assets/ui_icons/gwen'
OUT = ROOT / 'assets/forced'
USED = ['charge', 'files', 'investigate', 'verdict']   # gwen_lane.js FORCED.arts 와 같아야 함(tests/forced_test.js 가 확인)
SIZE = 192                                              # 화면 72~96px 의 2배


def seed_of(name):
    return zlib.crc32(name.encode())


# ── 오염 그웬 ─────────────────────────────────────────────────────────────
def eye_mask(name, size):
    """눈 영역 = 같은 표정의 기본 그림과 깜빡임 그림이 다른 곳."""
    a = Image.open(SRC / f'{name}.png').convert('RGBA')
    b = Image.open(SRC / f'{name}_blink.png').convert('RGBA')
    diff = np.asarray(ImageChops.difference(a, b)).astype(int).sum(axis=2) > 60
    m = Image.fromarray((diff * 255).astype('uint8')).filter(ImageFilter.MaxFilter(3))
    return m.resize((size, size), Image.BILINEAR)


def corrupt(name):
    rnd = random.Random(seed_of(name))
    big = SRC / f'{name}_512.png'
    im = Image.open(big if big.exists() else SRC / f'{name}.png').convert('RGBA').resize((SIZE, SIZE), Image.LANCZOS)
    px = np.asarray(im).astype(float) / 255
    rgb, alpha = px[..., :3], px[..., 3]
    lum = (rgb * [0.299, 0.587, 0.114]).sum(axis=2, keepdims=True)
    # 몸: 채도 낮춤 + 보라/검붉은 톤, 아래로 갈수록 어둡게
    body = lum * 0.72 + rgb * 0.28
    body = body * [0.86, 0.62, 0.92] + [0.05, 0.0, 0.07]
    fall = np.linspace(1.0, 0.72, SIZE)[:, None, None]
    body = np.clip(body * fall, 0, 1)
    # 눈: 홍채(노랑·주황)를 적색으로, 흰자는 어둡게
    eyes = np.asarray(eye_mask(name, SIZE)).astype(float) / 255
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    iris = eyes * np.clip((r - b) * 2.2, 0, 1) * (r > 0.45)
    white = eyes * (lum[..., 0] > 0.8) * (1 - np.clip(iris * 3, 0, 1))
    red = np.stack([np.clip(0.75 + lum[..., 0] * 0.4, 0, 1), lum[..., 0] * 0.16, lum[..., 0] * 0.2], axis=2)
    body = body * (1 - iris[..., None]) + red * iris[..., None]
    body = body * (1 - white[..., None] * 0.75) + np.array([0.16, 0.02, 0.08]) * white[..., None] * 0.75
    # 가장자리 침식: 윤곽 근처의 얼룩(검게 + 일부는 뚫림)
    a_img = Image.fromarray((alpha * 255).astype('uint8'))
    inner = np.asarray(a_img.filter(ImageFilter.GaussianBlur(7))).astype(float) / 255
    edge = np.clip((1 - inner) * 2.4, 0, 1) * (alpha > 0.5)
    rs = np.random.RandomState(seed_of(name) & 0x7fffffff)
    blot = rs.rand(SIZE // 6 + 1, SIZE // 6 + 1)
    blot = np.asarray(Image.fromarray((blot * 255).astype('uint8')).resize((SIZE, SIZE), Image.BICUBIC)).astype(float) / 255
    stain = np.clip((blot - 0.42) * 3.2, 0, 1) * edge
    body = body * (1 - stain[..., None] * 0.9) + np.array([0.07, 0.0, 0.05]) * stain[..., None] * 0.9
    hole = np.clip((blot - 0.7) * 6, 0, 1) * edge
    alpha = alpha * (1 - hole * 0.95)
    out = Image.fromarray((np.dstack([body, alpha]) * 255).astype('uint8'), 'RGBA')
    # 균열: 검붉은 꺾은선 몇 줄(몸 안에서만)
    crack = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(crack)
    for _ in range(4):
        x, y = rnd.uniform(SIZE * .25, SIZE * .75), rnd.uniform(SIZE * .35, SIZE * .9)
        ang = rnd.uniform(0, math.tau)
        pts = [(x, y)]
        for _ in range(rnd.randint(3, 5)):
            ang += rnd.uniform(-.9, .9)
            x, y = x + math.cos(ang) * rnd.uniform(6, 13), y + math.sin(ang) * rnd.uniform(6, 13)
            pts.append((x, y))
        d.line(pts, fill=(255, 60, 96, 150), width=2)
        d.line(pts, fill=(30, 0, 14, 235), width=1)
    crack.putalpha(ImageChops.multiply(crack.getchannel('A'), out.getchannel('A')))
    out.alpha_composite(crack)
    # 약한 글리치 줄: 가로 띠 몇 개를 옆으로 밀고 붉은 채널만 따로 어긋냄
    arr = np.asarray(out).copy()
    for _ in range(3):
        y0 = rnd.randint(int(SIZE * .2), int(SIZE * .9))
        h, dx = rnd.randint(2, 4), rnd.choice([-5, -3, 3, 5])
        arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], dx, axis=1)
        arr[y0:y0 + h, :, 0] = np.roll(arr[y0:y0 + h, :, 0], dx // 2 + 1, axis=1)
    out = Image.fromarray(arr, 'RGBA')
    # 눈빛 층(따로 저장 → CSS 가 투명도만 부드럽게 바꿈. 그림 2장 교대가 아님)
    glow_a = Image.fromarray((np.clip(iris * 1.6, 0, 1) * 255).astype('uint8'))
    wide = glow_a.filter(ImageFilter.GaussianBlur(5)).point(lambda v: min(255, int(v * 2.4)))
    core = glow_a.filter(ImageFilter.GaussianBlur(1.2))
    glow = Image.new('RGBA', (SIZE, SIZE), (255, 40, 72, 0))
    glow.putalpha(wide)
    hot = Image.new('RGBA', (SIZE, SIZE), (255, 190, 180, 0))
    hot.putalpha(core.point(lambda v: int(v * .8)))
    glow.alpha_composite(hot)
    return out, glow, float(iris.sum())


def build_gwen(names):
    (OUT / 'gwen').mkdir(parents=True, exist_ok=True)
    for name in names:
        body, glow, found = corrupt(name)
        if found < 20:
            raise SystemExit(f'{name}: 눈 영역을 못 찾음(깜빡임 그림과 차이 없음)')
        body.save(OUT / 'gwen' / f'{name}.webp', quality=82, method=6)
        glow.save(OUT / 'gwen' / f'{name}_eyes.webp', quality=70, method=6)


# ── 레인 배경(한 장) · 뒷모습 인물: 크기만 줄임 — 정식 그림이 오면 같은 이름으로 다시 만들면 끝 ──────────
NARROW = (0.17, 0.65)   # 좁은 화면용: 가로로 이 구간만(의자~광장)


def build_scene(src):
    im = Image.open(src).convert('RGB')
    im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS).save(OUT / 'scene.webp', quality=72, method=6)
    x0, x1 = (round(im.width * t) for t in NARROW)
    part = im.crop((x0, 0, x1, im.height))
    part.resize((800, round(part.height * 800 / part.width)), Image.LANCZOS).save(OUT / 'scene_narrow.webp', quality=72, method=6)


def build_back(src):
    im = Image.open(src).convert('RGBA')
    im = im.crop(im.getbbox())
    hgt = 520
    im.resize((round(im.width * hgt / im.height), hgt), Image.LANCZOS).save(OUT / 'gwen_back.webp', quality=84, method=6)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--gen-dir', type=Path)
    ap.add_argument('--all-gwen', action='store_true')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name[:-10] for p in SRC.glob('*_blink.png') if not p.name.startswith('st_')) if args.all_gwen else USED
    build_gwen(names)
    if args.gen_dir:
        build_scene(args.gen_dir / 'lavistar_ruin_bg_1.png')
        build_back(args.gen_dir / 'gwen_back_illust_1.png')
    files = sorted(p for p in OUT.rglob('*') if p.is_file())
    for p in files:
        print(f'{p.stat().st_size:8,d}  {p.relative_to(ROOT).as_posix()}')
    print(f'{sum(p.stat().st_size for p in files):8,d}  합계({len(files)}개)')


if __name__ == '__main__':
    main()
