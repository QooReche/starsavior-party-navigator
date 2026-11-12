# -*- coding: utf-8 -*-
"""종류 태그 생성·클라 근거 대조. python -X utf8 -I tests/kinds_test.py"""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.fileio import read_json
from tools.update import build_kinds


class KindsTest(unittest.TestCase):
    def setUp(self):
        self.db = read_json(ROOT / 'rawdata/databook_main.json')
        self.extra = read_json(ROOT / 'data/kind_overrides.json')

    def test_generated_kinds(self):
        rows = build_kinds(self.db, self.extra)
        self.assertEqual(rows, read_json(ROOT / 'data/kinds.json'))
        self.assertEqual(len(rows), len({(r['name'], r['sub'], r['kind']) for r in rows}))

    def test_shifter_and_originals(self):
        rows = build_kinds(self.db, self.extra)
        for uid, expected in [(1061, ['C', 'S']), (1054, ['C']), (1001, []), (1020, ['C']), (1060, ['A'])]:
            unit = next(u for u in self.db['units'] if u['id'] == uid)
            found = [r for r in rows if (r['name'], r['sub']) == (unit['n'], unit['ti'])]
            self.assertEqual([r['kind'] for r in found], expected, uid)
            if uid == 1061:
                self.assertIn('UnitTagTypeGroup', found[1]['source'])

    def test_existing_kinds_preserved(self):
        expected = [dict(name=u['n'], sub=u['ti'], kind=t) for u in self.db['units']
                    if (t := self.db['rel']['u'].get(str(u['id']), {}).get('t')) in ('C', 'A')]
        rows = build_kinds(self.db, self.extra)
        self.assertEqual([r for r in rows if r['kind'] != 'S'], expected)
        self.assertEqual(build_kinds(self.db, {'units': {}}), expected)

    @unittest.skipUnless(os.environ.get('STARSAVIOR_STATIC'), 'STARSAVIOR_STATIC 없음')
    def test_shifter_source(self):
        tables = Path(os.environ['STARSAVIOR_STATIC']) / 'tables'
        ids = {str(u['m_UnitID']) for path in tables.glob('UNIT_TEMPLET_BASE*.json')
               for u in read_json(path)['Data']
               if any(t['UnitTagType'] == 'UOT_SHIFTER' for t in u.get('UnitTagTypeGroup', []))}
        self.assertEqual(ids, {uid for uid, row in self.extra['units'].items() if 'S' in row['kinds']})


if __name__ == '__main__':
    unittest.main()
