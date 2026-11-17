"""JS growth payload -> real select_skills, with the original bug as a control."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.starsavior.data import get_db
from battlesim.starsavior.myinfo_combat import select_skills


class PassiveGrowthTests(unittest.TestCase):
    def test_current_assume_and_overwrite_reach_real_skill_selection(self):
        payload = json.loads(subprocess.check_output(
            ['node', 'tests/passive_growth_test.js', '--payload'], cwd=ROOT, text=True, encoding='utf-8'))
        db = get_db()
        key = payload['key']
        for state, enabled in [('current', False), ('before', True), ('after', False), ('overwrite', False)]:
            selected = select_skills(db.units[key], key, {'skills': payload[state]})
            passive = [s for s in selected['sk'] if s['sl'] == '고유 패시브']
            self.assertEqual(bool(passive), enabled, state)
            self.assertTrue(any(s['sl'] == '기본기' for s in selected['sk']))


if __name__ == '__main__':
    unittest.main()
