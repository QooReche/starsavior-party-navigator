# -*- coding: utf-8 -*-
"""브라우저 시뮬(sim_worker.js, Pyodide)이 받아 갈 파일 목록 sim/manifest.json 을 만든다.

파일 자체는 복사하지 않는다 — GitHub Pages 가 저장소 파일을 그대로 서비스하므로 경로와 버전(내용 해시)만 적는다.
엔진(battlesim/*.py)이나 rawdata 를 바꾸면 다시 돌릴 것(해시가 바뀌면 화면의 이전 시뮬 결과는 무효).

경량화(2026-11-22, docs/engine_diet_1122.md 1단계)
- 브라우저 진입점(web.run_auto → api → mc)이 import 하지 않는 metrics.py·quick.py 는 싣지 않는다(cli.py·__main__.py 와 같음).
- 규칙 파일은 축약본 battlesim/rules/default.min.json 을 싣는다: 항목마다 value·grade·kind 만, note 는 결과(api.assumptions_used)에
  실리는 가정 등급 항목만 남긴다(source·alt·legacy·나머지 note 제외). rules.load_rules 는 default.json 이 없을 때(브라우저) 이 파일을 읽는다.
  축약본은 이 스크립트가 default.json 에서 다시 만든다 — default.json 을 고치면 반드시 다시 돌릴 것(tests/diet_baseline_test.py 가 확인).

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
SLIM_RULES = 'battlesim/rules/default.min.json'
# 브라우저 진입점이 import 하지 않는 파이썬(묶음 제외). cli.py·__main__.py 는 명령줄 전용
EXCLUDE_PY = ('battlesim/cli.py', 'battlesim/__main__.py', 'battlesim/metrics.py', 'battlesim/quick.py')
FIXED = [SLIM_RULES, 'battlesim/rules/builds.json', 'rawdata/databook_main.json', 'rawdata/foe.js', 'data/foe_spawn.json',
         'rawdata/guide_app-core.js', 'data/synergy_tags.json', 'data/myinfo_combat.json', 'data/auto_skill.json', 'data/foe_auto.json',
         'data/sudden_death.json', 'data/stage_fx.json', 'data/battle_end.json', 'data/chain_damage.json', 'data/hit_stats.json', 'data/chain_se.json',
         'data/break_skill_levels.json', 'data/buff_count.json', 'data/buff_step.json', 'data/buff_force.json', 'data/buff_immune_pass.json', 'data/buff_global_turn.json',
         'data/foe_react.json', 'data/foe_client.json', 'data/foe_summon.json', 'data/foe_clash.json', 'data/buff_dead_keep.json', 'data/buff_flags.json',
         'data/guild_bfb.json', 'data/guild_defense.json', 'data/cosmo_raid.json', 'data/foe_cosmo_extra.json']


def files():
    py = sorted(p.replace(os.sep, '/') for p in glob.glob('battlesim/**/*.py', root_dir=ROOT, recursive=True)
                if '__pycache__' not in p)
    return [p for p in py if p not in EXCLUDE_PY] + FIXED


def slim_rules():
    """default.json -> 브라우저용 축약본(문자열). 키 순서·값은 그대로, 엔진·결과가 안 읽는 설명 필드만 뺀다."""
    from battlesim.api import ASSUMPTION_GRADES
    with open(os.path.join(ROOT, 'battlesim', 'rules', 'default.json'), encoding='utf-8') as f:
        full = json.load(f)

    def entry(v):
        out = {k: v[k] for k in ('value', 'grade', 'kind') if k in v}
        if v.get('grade') in ASSUMPTION_GRADES and 'note' in v:     # api.assumptions_used 가 결과에 싣는 note
            out['note'] = v['note']
        return out
    slim = {}
    for sec, items in full.items():
        if sec.startswith('_'):
            continue
        slim[sec] = {}
        for k, v in items.items():
            if k.startswith('_'):
                continue
            slim[sec][k] = {kk: entry(vv) for kk, vv in v.items()} if (sec == 'mc' and k == 'break_skills') else entry(v)
    return json.dumps(slim, ensure_ascii=False, separators=(',', ':')) + '\n'


def write_slim():
    dst = os.path.join(ROOT, *SLIM_RULES.split('/'))
    with atomic_open(dst) as f:
        f.write(slim_rules())


def main():
    write_slim()
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
