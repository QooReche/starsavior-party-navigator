# -*- coding: utf-8 -*-
"""브라우저 시뮬(sim_worker.js, Pyodide)이 받아 갈 파일 목록 sim/manifest.json 을 만든다.

파일 자체는 복사하지 않는다 — GitHub Pages 가 저장소 파일을 그대로 서비스하므로 경로와 버전(내용 해시)만 적는다.
엔진(battlesim/*.py)이나 rawdata 를 바꾸면 다시 돌릴 것(해시가 바뀌면 화면의 이전 시뮬 결과는 무효).

사용: python -X utf8 -I tools/build_simpack.py
"""
import sys
import glob
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(ROOT))
from battlesim.fileio import atomic_open
FIXED = ['battlesim/rules/default.json', 'battlesim/rules/builds.json', 'rawdata/databook_main.json', 'rawdata/foe.js', 'data/foe_spawn.json',
         'rawdata/guide_app-core.js', 'data/synergy_tags.json', 'data/myinfo_combat.json', 'data/auto_skill.json', 'data/foe_auto.json',
         'data/sudden_death.json',
         'data/break_skill_levels.json',
         'data/foe_react.json']


def files():
    py = sorted(p.replace(os.sep, '/') for p in glob.glob('battlesim/**/*.py', root_dir=ROOT, recursive=True)
                if '__pycache__' not in p and not p.endswith(('cli.py', '__main__.py')))
    return py + FIXED


def main():
    fs = files()
    # GitHub Pages(Jekyll)는 _ 로 시작하는 파일(__init__.py)을 숨긴다 -> 저장소 루트 .nojekyll 필수(2026-10-20 라이브에서 404 로 확인)
    if any(os.path.basename(p).startswith('_') for p in fs) and not os.path.exists(os.path.join(ROOT, '.nojekyll')):
        raise SystemExit('.nojekyll 이 없으면 Pages 가 __init__.py 를 404 로 낸다 — 저장소 루트에 빈 .nojekyll 을 만드세요')
    h = hashlib.sha256()
    sizes = 0
    for p in fs:
        with open(os.path.join(ROOT, p), 'rb') as f:
            b = f.read()
        h.update(p.encode() + b'\0' + b)
        sizes += len(b)
    out = dict(_note='브라우저 시뮬 파일 목록(tools/build_simpack.py). ver = 경로+내용 해시', ver=h.hexdigest()[:12], files=fs, bytes=sizes)
    os.makedirs(os.path.join(ROOT, 'sim'), exist_ok=True)
    dst = os.path.join(ROOT, 'sim', 'manifest.json')

    with atomic_open(dst) as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print('저장', dst, '파일', len(fs), '크기', sizes, 'ver', out['ver'])


if __name__ == '__main__':
    main()
