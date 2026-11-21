# -*- coding: utf-8 -*-
"""CLIENT_ 접두 추출본(rebuild T)을 옛 빌더가 읽는 static 형태(tables/…)로 펼친다.

build_foe_auto·build_foe_spawn 은 `<static>/tables/SE_TEMPLET_SKILL_1.json`·`BattleScript/`·
`Strings/STRING_COMMON_ko_en.json` 을 읽는다. 비공개 static-data `tables/` 는 26610546판이라
26752678 표로 같은 연결을 하려고 필요한 표만 주석을 벗겨 출력 폴더에 쓴다. 값은 바꾸지 않는다.
출력 폴더는 저장소 밖(비공개)에 둔다. 표 원문을 공개 저장소에 넣지 않는다.

사용: python -X utf8 -I tools/client_view.py --tables <rebuild>/T --out <비공개 폴더>
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tables import jsonc   # noqa: E402

NAMES = (['BUFF_TEMPLET', 'BLOSSOM_TEMPLET'] + ['UNIT_TEMPLET_BASE%d' % n for n in (1, 2, 3, 4)]
         + ['%s_%d' % (s, n) for s in ('SKILL_TEMPLET', 'SE_TEMPLET_SKILL', 'SKILL_LEVEL_GROUP_TEMPLET') for n in (1, 2)])


def materialize(tables, out):
    tables, out = Path(tables), Path(out)
    dst = out / 'tables'
    (dst / 'Plain').mkdir(parents=True, exist_ok=True)
    (dst / 'BattleScript').mkdir(exist_ok=True)
    (dst / 'Strings').mkdir(exist_ok=True)

    def put(src, path):
        path.write_text(json.dumps(jsonc(src), ensure_ascii=False), encoding='utf-8')

    for name in NAMES:
        put(tables / ('CLIENT_%s.json' % name), dst / ('%s.json' % name))
    for p in tables.glob('CLIENT_BATTLE_TEMPLET_*.json'):
        put(p, dst / p.name[len('CLIENT_'):])
    for name in ('AUTO_SKILL_TEMPLET', 'AUTO_SKILL_TARGET_TEMPLET'):
        put(tables / 'plain' / ('%s.json' % name), dst / 'Plain' / ('%s.json' % name))
    n = 0
    for p in (tables / 'plain').glob('JSON_*.json'):
        put(p, dst / 'BattleScript' / p.name)
        n += 1
    strings = {r['Key']: {'g': r.get('GroupName'), 'ko': r.get('Value'), 'en': r.get('Value_ENG')}
               for r in jsonc(tables / 'hard' / 'STRING_COMMON.json')['Data'] if r.get('Key')}
    (dst / 'Strings' / 'STRING_COMMON_ko_en.json').write_text(json.dumps(strings, ensure_ascii=False), encoding='utf-8')
    return dict(tables=len(NAMES), battle_scripts=n, strings=len(strings))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tables', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if ROOT in a.out.resolve().parents or a.out.resolve() == ROOT:
        raise SystemExit('출력 폴더는 저장소 밖이어야 함')
    print(materialize(a.tables, a.out))
