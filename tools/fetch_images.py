# -*- coding: utf-8 -*-
"""가이드 DB 의 구원자 초상화/일러스트를 내려받아 줄여서 assets/savior/<key>_face.webp, <key>_art.webp 로 저장한다.
원본은 tools/raw/savior/ 에 두고(저장소 제외), 요청 사이에 간격을 둔다.
사용(cv2 필요, 가상환경은 저장소 밖): <venv>\\Scripts\\python.exe -X utf8 -I tools/fetch_images.py  (예: E:\\AI_mk2\\venv-img)"""
import os
import sys
import time
import urllib.parse
import urllib.request

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


def get(url, dst):
    if os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = urllib.parse.quote(url, safe=":/%")  # 파일명에 한글이 있는 경우(예: 프로페서M.webp)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        data = r.read()
    with open(dst, "wb") as f:
        f.write(data)
    time.sleep(0.3)


def shrink(src, dst, width, q):
    # 투명 배경(알파)을 살린다. IMREAD_COLOR 로 읽으면 투명 부분이 흰/검 계단 무늬로 깨진다(2026-10-20 수정)
    a = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if a.ndim == 2:
        a = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
    h, w = a.shape[:2]
    a = cv2.resize(a, (width, max(1, round(h * width / w))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".webp", a, [cv2.IMWRITE_WEBP_QUALITY, q])
    assert ok
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    buf.tofile(dst)
    return len(buf)


def main():
    roster = pr._json(pr.RECO)["saviors"]
    por, art = bp.image_urls(roster)
    tot = 0
    for s in roster:
        k = s["key"]
        for urls, suf, w, q in ((por, "face", FACE_PX, 85), (art, "art", ART_W, 80)):
            u = urls.get(k)
            if not u:
                print("없음", k, suf)
                continue
            raw = os.path.join(RAW, f"{k}_{suf}" + os.path.splitext(u)[1])
            get(u, raw)
            tot += shrink(raw, os.path.join(OUT, f"{k}_{suf}.webp"), w, q)
    print("저장", len(os.listdir(OUT)), "개", tot // 1024, "KB")


if __name__ == "__main__":
    main()
