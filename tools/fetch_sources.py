# -*- coding: utf-8 -*-
"""게임 업데이트 후 최신 원본 자료를 내려받아 rawdata/ 를 갱신한다(요청은 필요한 만큼만).
  - 팬 데이터북(starsavior-databook.pages.dev): data/main.js -> tools/unwrap_ssd.py 로 rawdata/databook_main.json, data/foe.js -> rawdata/foe.js
  - 가이드 DB(starsavior-guide.github.io): app-core.js -> rawdata/guide_app-core.js (티어·주 사용 콘텐츠는 node tools/extract_guide_tier.js)
사용: python -X utf8 -I tools/fetch_sources.py [--dry]   (--dry 는 주소만 확인하고 내려받지 않음)
주의: 원본 사이트 구조가 바뀌면 정규식이 실패할 수 있다. 데이터북·가이드 DB 재사용은 사용자가 허락받은 것으로 확인됨(2026-10-19)."""
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RAW = os.path.join(ROOT, "rawdata")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
DB = "https://starsavior-databook.pages.dev/"
GUIDE = "https://starsavior-guide.github.io/"
DRY = "--dry" in sys.argv


def get(url):
    print("GET", url)
    if DRY:
        return ""
    time.sleep(0.4)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8")


def main():
    html = get(DB)
    m = re.search(r'src="(data/main\.js[^"]*)"', html) or (None if DRY else sys.exit("databook index.html 에서 main.js 를 찾지 못함"))
    main_url = DB + (m.group(1) if m else "data/main.js")
    app = get(DB + "app.js") if not DRY else ""
    mf = re.search(r"data/foe\.js\?v=\w+", app)
    foe_url = DB + (mf.group(0) if mf else "data/foe.js")
    if not DRY:
        tmp = os.path.join(RAW, "_main.js")
        open(tmp, "w", encoding="utf-8", newline="\n").write(get(main_url))
        subprocess.run([sys.executable, "-X", "utf8", "-I", os.path.join(ROOT, "tools", "unwrap_ssd.py"), tmp], check=True)
        os.remove(tmp)
        open(os.path.join(RAW, "foe.js"), "w", encoding="utf-8", newline="\n").write(get(foe_url))
    else:
        print("GET", main_url, "\nGET", foe_url)
    gh = get(GUIDE)
    gm = re.search(r'src="([^"]*app-core\.js[^"]*)"', gh)
    core_url = GUIDE + (gm.group(1).lstrip("./") if gm else "app-core.js")
    if not DRY:
        open(os.path.join(RAW, "guide_app-core.js"), "w", encoding="utf-8", newline="\n").write(get(core_url))
    else:
        print("GET", core_url)
    print("다음: node tools/extract_guide_tier.js  ->  python -X utf8 -I tools/update.py")


if __name__ == "__main__":
    main()
