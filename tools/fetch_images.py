# -*- coding: utf-8 -*-
"""구원자 초상화/배경 일러스트를 assets/savior/<key>_face.webp, <key>_art.webp 로 저장한다.
일러스트는 데이터북의 배경 포함 그림 우선, 없으면 가이드 DB 그림으로 폴백한다.
원본은 tools/raw/savior/ 에 두고(저장소 제외), 요청 사이에 간격을 둔다.
사용(cv2 필요, 가상환경은 저장소 밖): <venv>\\Scripts\\python.exe -X utf8 -I tools/fetch_images.py
  --art-only --keys lydia-moon-caster gille asherah-order-striker  # 얼굴은 그대로
  --audit  # 현재 그림의 알파 비율 표(배경 유무와는 다름: 장식 가장자리도 투명함)
"""
import argparse
import hashlib
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import build_party_html as bp  # noqa: E402
import party_reco as pr  # noqa: E402

RAW = os.path.join(ROOT, "tools", "raw", "savior")
OUT = os.path.join(ROOT, "assets", "savior")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
FACE_PX, ART_W = 160, 420  # 얼굴: 정사각 가로 160, 일러스트: 가로 420(세로는 비율 유지)
# 2026-11-12 확인: https://starsavior-databook.pages.dev/app.js 의 pair(x).
# '일러스트' = img/ill/{id}.webp, '캐릭터만' = img/u/{id}.webp.
# ID/이름/별칭은 data/main.js 의 units와 대조함(신규 1020·1061 포함).
ILL_ROOT = "https://starsavior-databook.pages.dev/img/ill/"


def get(url, dst):
    if os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = urllib.parse.quote(url, safe=":/%")  # 파일명에 한글이 있는 경우(예: 프로페서M.webp)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            data = r.read()
    finally:
        time.sleep(0.4)  # 실패 후 폴백 요청에도 간격을 둔다. 병렬 다운로드하지 않음.
    with open(dst, "wb") as f:
        f.write(data)


def shrink(src, dst, width, q):
    # 투명 배경(알파)을 살린다. IMREAD_COLOR 로 읽으면 투명 부분이 흰/검 계단 무늬로 깨진다(2026-10-20 수정)
    a = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if a is None:
        raise ValueError(f"이미지 디코딩 실패: {src}")
    if a.ndim == 2:
        a = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
    h, w = a.shape[:2]
    a = cv2.resize(a, (width, max(1, round(h * width / w))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".webp", a, [cv2.IMWRITE_WEBP_QUALITY, q])
    assert ok
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    buf.tofile(dst)
    return len(buf)


def raw_path(key, suffix, url):
    # 출처를 바꿔도 이전 URL의 투명 원본을 재사용하지 않는다.
    token = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    ext = os.path.splitext(urllib.parse.urlsplit(url).path)[1]
    return os.path.join(RAW, f"{key}_{suffix}_{token}{ext}")


def save_image(key, suffix, urls, width, quality):
    for url in dict.fromkeys(u for u in urls if u):
        raw = raw_path(key, suffix, url)
        try:
            get(url, raw)
            size = shrink(raw, os.path.join(OUT, f"{key}_{suffix}.webp"), width, quality)
        except (urllib.error.URLError, TimeoutError, ValueError, cv2.error) as exc:
            print("폴백", key, suffix, url, str(exc))
            continue
        print("저장", key, suffix, url)
        return size
    raise RuntimeError(f"사용 가능한 이미지 없음: {key} {suffix}")


def audit(roster):
    print("| key | 이름 / 구분 | 크기 | 투명 픽셀(alpha < 250) |")
    print("|---|---|---|---:|")
    for s in roster:
        path = os.path.join(OUT, f"{s['key']}_art.webp")
        a = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED) if os.path.exists(path) else None
        size, ratio = "없음", "-"
        if a is not None:
            size = f"{a.shape[1]}×{a.shape[0]}"
            alpha = float(np.mean(a[:, :, 3] < 250)) if a.ndim == 3 and a.shape[2] == 4 else 0
            ratio = f"{alpha:.2%}"
        print(f"| {s['key']} | {s['name']} / {s['subtitle']} | {size} | {ratio} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--art-only", action="store_true")
    ap.add_argument("--keys", nargs="+")
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()
    roster = pr._json(pr.RECO)["saviors"]
    if args.keys:
        missing = set(args.keys) - {s["key"] for s in roster}
        if missing:
            ap.error("알 수 없는 key: " + ", ".join(sorted(missing)))
        roster = [s for s in roster if s["key"] in args.keys]
    if args.audit:
        audit(roster)
        return
    idx = pr._json(os.path.join(pr.DATA, "saviors_index.json"))
    por, art = bp.image_urls(roster, idx)
    resolve_uid = bp.uid_resolver(idx)
    tot = 0
    for s in roster:
        k = s["key"]
        if not args.art_only and por.get(k):
            tot += save_image(k, "face", [por[k]], FACE_PX, 85)
        uid = resolve_uid(k, s["name"])
        preferred = f"{ILL_ROOT}{uid}.webp" if uid else None
        tot += save_image(k, "art", [preferred, art.get(k)], ART_W, 80)
    print("저장", len(os.listdir(OUT)), "개", tot // 1024, "KB")


if __name__ == "__main__":
    main()
