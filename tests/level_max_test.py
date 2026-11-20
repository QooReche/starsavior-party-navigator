"""PC 26752678: 이름별 중첩 상한과 실제 보스 정의 회귀."""
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simkit import battle, unit
from battlesim.starsavior import cosmo_raid as C
from battlesim import mc
from battlesim.starsavior.parser import Line
from battlesim.api import _norm_party_raw
from battlesim.starsavior.data import get_db
from battlesim.rules import MC_OPTS
from tools.build_buff_flags import extract, client_strings


def apply_boss(key, name, count, mode=None):
    waves, _ = C.build_waves(key, 3, 0)
    b = battle([unit('ally')], waves[0], mc={} if mode is None else {'level_max_source': mode})
    boss = next(u for u in b.foes if u.d.boss)
    line = next(l for l in boss.d.lines if l.eff.get('name') == name and l.eff['kind'] == 'buff')
    boss.eff.pop(name, None)
    for _ in range(count):
        b.add_effect(boss, boss, line.eff, None)
    return b, boss, boss.eff[name]


class LevelMaxTest(unittest.TestCase):
    def test_mogulus(self):
        _, boss, eff = apply_boss('mogulus', '보주의 축성', 3)
        self.assertEqual(eff.stacks, 3)
        self.assertAlmostEqual(boss.mods()['inc'], .15)

    def test_disparity(self):
        _, boss, eff = apply_boss('disparity', '기억의 증폭', 3)
        self.assertEqual(eff.stacks, 3)
        self.assertAlmostEqual(boss.mods()['inc'], .15)

    def test_explicit_cap(self):
        self.assertEqual(apply_boss('mogulus', '그릇된 의지', 5)[2].stacks, 3)

    def test_legacy(self):
        for key, name in [('mogulus', '보주의 축성'), ('disparity', '기억의 증폭')]:
            self.assertEqual(apply_boss(key, name, 3, 'legacy')[2].stacks, 1)

    def test_mutation_catches_both_bosses(self):
        with patch('battlesim.mc.level_max', return_value=1):
            for check in (self.test_mogulus, self.test_disparity):
                with self.assertRaises(AssertionError):
                    check()

    def test_builder_aliases_and_collisions(self):
        strings = client_strings([{'Key': 'a', 'Value': '무한'}, {'Keys': ['b', 'b2'], 'Value': '충돌'},
                                  {'Key': 'c', 'Value': '유한'}, {'Key': 'd', 'Value': '종류충돌'}])
        def row(key, cap=0, level=True):
            return {'m_BuffName': key, 'IsLevel': level, 'BuffLevelMax': cap}
        data = extract([row('a'), row('b'), row('b2', 3), row('c', 3), row('d'), row('d', -1, False)],
                       strings, lambda msg: None)
        self.assertEqual(data['level_max'], {'무한': 'inf', '유한': 3})

    def test_all_unlimited_names(self):
        names = ['파멸의 관성', '보주의 축성', '거듭된 파국', '고대의 힘', '기억의 증폭',
                 '끝나지 않는 사냥', '종막 예고', '끝없는 저주', '끝없는 성장']
        b = battle([unit()], [unit('foe')])
        u = b.allies[0]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(mc.level_max(name), float('inf'))
                line = Line('[스킬 사용 후] 자신에게 〈%s〉 (지속 무한 / 피해 증가 +5%%)' % name, '패시브', '패시브')
                for _ in range(20):
                    b.add_effect(u, u, line.eff, None)
                self.assertEqual(u.eff[name].stacks, 20)

    def test_explicit_override_and_report(self):
        b, u, _ = apply_boss('mogulus', '보주의 축성', 1)
        line = next(l for l in u.d.lines if l.eff.get('name') == '보주의 축성')
        with patch.dict(line.eff, {'max': 2}):
            u.eff.pop('보주의 축성')
            for _ in range(4):
                b.add_effect(u, u, line.eff, None)
            self.assertEqual(u.eff['보주의 축성'].stacks, 2)
            rows = mc._support_one(u.d, set())
            self.assertTrue(any(r['reason'].startswith('level_max:') for r in rows))

    def test_finite_fallback_unknown_and_suffix(self):
        self.assertEqual(mc.level_max('그릇된 의지'), 3)
        self.assertEqual(mc.level_max('보주의 축성(해제불가)'), float('inf'))
        self.assertIsNone(mc.level_max('없는 효과'))
        b, u, _ = apply_boss('mogulus', '그릇된 의지', 1)
        u.eff.pop('그릇된 의지')
        line = next(l for l in u.d.lines if l.eff.get('name') == '그릇된 의지')
        with patch.dict(line.eff, {'max': None}):
            for _ in range(5):
                b.add_effect(u, u, line.eff, None)
        self.assertEqual(u.eff['그릇된 의지'].stacks, 3)

    def test_support_report_unnamed_effect(self):
        defs, *_ = _norm_party_raw({'units': [{'key': 'muriel', 'build': 'standard'}]},
                                  get_db(), 'fixed', 'standard', MC_OPTS)
        self.assertTrue(any(l.eff['kind'] == 'extend' and l.eff.get('name') is None
                            for d in defs for l in mc.norm_lines_cached(d)))
        self.assertEqual(mc.support_report(defs), [])


if __name__ == '__main__':
    unittest.main()
