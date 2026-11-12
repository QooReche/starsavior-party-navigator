"""Export display thresholds only; no private rows or engine data are copied."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(static):
    rows = json.loads((Path(static) / 'tables/STAT_GRADE_TEMPLET.json').read_text(encoding='utf-8'))['Data']
    types = ['JST_POWER', 'JST_HEALTH', 'JST_ENDURANCE', 'JST_FOCUS', 'JST_PROTECT']
    actual = list(dict.fromkeys(r['StatType'] for r in rows))
    assert set(actual) == set(types), actual
    stats = []
    for typ in types:
        values = []
        for r in rows:
            if r['StatType'] != typ:
                continue
            code = r['StatGrade'].removeprefix('SG_')
            # Upper ranks are image glyphs. SSG+ at 1250 conflicts with supplied
            # SG / SG+ screenshots: show numbers until the glyph is verified.
            label = code.replace('_PLUS', '+') if code.split('_')[0] in list('GFEDCBA') else ''
            values.append([r['StatValue'], label])
        stats.append(sorted(values))
    return {'stats': stats, 'source': 'STAT_GRADE_TEMPLET; Star.Templets:31071-31078 (26610546)',
            'unverified': '상위 등급 그림 글자: 1250의 SG/SG+ 제보와 내부 SSG+ 불일치. 숫자로 표시.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--static', required=True)
    args = ap.parse_args()
    (ROOT / 'data/archive_grades.json').write_text(json.dumps(build(args.static), ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
