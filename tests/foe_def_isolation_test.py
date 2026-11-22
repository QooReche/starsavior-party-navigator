"""적 정의 공유 보호(최종 리뷰 엔진 갈래 «잠재 위험»): Unit 은 적 정의의 stats·passive 사전을 유닛마다 따로 가진다.

적 정의(FoeDef·FoeBase)는 판·팀 사이에 공유된다. Battle 의 «등장 후 능력치» 처리(적 전용 perm 줄)는 u.d.passive·u.d.spd_base 를
제자리에서 고치므로, 한 유닛의 보정이 원본 정의나 다른 유닛(다음 판·다른 팀)으로 새면 안 됨. 이미 정규화된 정의(_compound_normalized)를
넘겨도 같음. 비공개 표 불필요.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, unit  # noqa: E402
from battlesim.mc import Unit  # noqa: E402
from battlesim.starsavior.foe_base import FoeBase  # noqa: E402
from battlesim.starsavior.mc_semantics import normalized_definition  # noqa: E402


def foe():
    return FoeBase('t_foe', '시험 적', role='공격형', element='fire', boss=False, attack_kind='single',
                   stats={'atk': 1000, 'hp': 10**6, 'def': 100, 'spd': 100, 'cr': 0, 'cd': 1.5, 'eh': 0, 'er': 0}, skills={})


class FoeDefIsolationTest(unittest.TestCase):
    def check(self, d):
        b = battle([unit('a', spd=100)], [unit('f', hp=10**8)], opts={'coop': False, 'nova': False})
        stats0, passive0 = dict(d.stats), dict(d.passive)
        u1, u2 = Unit(d, 1, 0, b), Unit(d, 1, 1, b)
        self.assertIsNot(u1.d.stats, u2.d.stats)
        self.assertIsNot(u1.d.passive, u2.d.passive)
        # Battle 의 적 perm 처리와 같은 제자리 수정
        u1.d.stats['spd'] = 1
        u1.d.passive['spdp'] += -10.0
        u1.d.spd_base = 1
        self.assertEqual(dict(d.stats), stats0)
        self.assertEqual(dict(d.passive), passive0)
        self.assertEqual(u2.d.stats['spd'], 100)
        self.assertEqual(u2.d.passive['spdp'], passive0.get('spdp', 0.0))
        self.assertEqual(u2.d.spd_base, 100)
        self.assertEqual(Unit(d, 1, 2, b).d.passive['spdp'], passive0.get('spdp', 0.0))

    def test_raw_definition(self):
        self.check(foe())

    def test_already_normalized_definition(self):
        d = normalized_definition(foe())
        self.assertTrue(d._compound_normalized)
        self.check(d)


if __name__ == '__main__':
    unittest.main()
