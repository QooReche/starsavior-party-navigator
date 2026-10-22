# -*- coding: utf-8 -*-
"""게임 업데이트 후 최신 원본 자료를 내려받아 rawdata/ 를 갱신한다(요청은 필요한 만큼만).
  - 팬 데이터북(starsavior-databook.pages.dev): data/main.js -> tools/unwrap_ssd.py 로 rawdata/databook_main.json, data/foe.js -> rawdata/foe.js
  - 가이드 DB(starsavior-guide.github.io): app-core.js -> rawdata/guide_app-core.js (티어·주 사용 콘텐츠는 node tools/extract_guide_tier.js)
사용: python -X utf8 -I tools/fetch_sources.py [--dry]   (--dry 는 주소만 확인하고 내려받지 않음)
주의: 원본 사이트 구조가 바뀌면 정규식이 실패할 수 있다. 데이터북·가이드 DB 재사용은 사용자가 허락받은 것으로 확인됨(2026-10-19)."""
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
from battlesim.fileio import atomic_json, atomic_text
from tools.unwrap_ssd import unwrap
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
    main_js = get(main_url)
    # foe.js 버전 키는 main.js 의 window.__SSV={"foe":"…"} 에 있다(app.js 가 'data/'+key+'.js?v='+__SSV[key] 로 조립). 2026-10 확인
    mf = re.search(r'__SSV\s*=\s*\{[^}]*"foe"\s*:\s*"(\w+)"', main_js)
    if not DRY and not mf:
        sys.exit("main.js 에서 foe.js 버전 키(__SSV.foe)를 찾지 못함 — 사이트 구조 변경 확인 필요")
    foe_url = DB + "data/foe.js" + ("?v=" + mf.group(1) if mf else "")
    if not DRY:
        main_data = unwrap(main_js)
        if not all(k in main_data for k in ('units', 'dict', 'topics')):
            raise ValueError('main.js 필수 자료 누락')
        foe_js = get(foe_url)
        foe = unwrap(foe_js).get('foe', {})
        if not all(k in foe for k in ('u', 's', 'g')):
            raise ValueError('foe.js 필수 자료 누락')
    else:
        print("GET", main_url, "\nGET", foe_url)
    gh = get(GUIDE)
    gm = re.search(r'src="([^"]*app-core\.js[^"]*)"', gh)
    core_url = GUIDE + (gm.group(1).lstrip("./") if gm else "app-core.js")
    if not DRY:
        core_js = get(core_url)
        for name in ('GROWTH_PRIORITY', 'MAIN_CONTENTS'):
            if not re.search(r'const\s+' + name + r'\s*=\s*\{[\s\S]*?^};', core_js, re.M):
                raise ValueError('가이드 DB 구조 변경: ' + name)
        # 모든 수신·구조 확인이 끝난 뒤 각 파일을 교체함.
        atomic_json(os.path.join(RAW, 'databook_main.json'), main_data)
        atomic_text(os.path.join(RAW, 'foe.js'), foe_js)
        atomic_text(os.path.join(RAW, 'guide_app-core.js'), core_js)
    else:
        print("GET", core_url)
    print("다음: node tools/extract_guide_tier.js  ->  python -X utf8 -I tools/update.py")


if __name__ == "__main__":
    main()
