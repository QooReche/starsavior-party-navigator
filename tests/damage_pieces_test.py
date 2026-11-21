# -*- coding: utf-8 -*-
"""피해식 조각(battlesim/statcalc.py def_rate·def_rate_pen·elem_adv, 설계 fable_unify 5단계 B1·B2)이 옛 식과 부동소수까지 같다.

  python -X utf8 -I tests/damage_pieces_test.py
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from battlesim import statcalc as S   # noqa: E402
from battlesim.rules import DEF_K, ELEM_BEATS, ELEM_LOSES, ELEM_HIT   # noqa: E402


class Pieces(unittest.TestCase):
    def test_same_as_inline(self):
        rnd = random.Random(7)
        for _ in range(20000):
            de = rnd.choice([0, 1, rnd.uniform(0, 20000), rnd.randint(0, 30000)])
            pen = rnd.choice([0.0, 1.0, 1.5, -0.2, rnd.uniform(0, 1.3)])
            dr = de / (de + DEF_K)
            self.assertEqual(S.def_rate(de), dr)
            self.assertEqual(S.def_rate_pen(dr, pen), max(0.0, dr - dr * min(1.0, pen)))
            self.assertEqual(S.def_rate_pen(dr, pen, cap=False), max(0.0, dr - dr * pen))

    def test_elem(self):
        els = list(ELEM_BEATS) + [None]
        for a in els:
            for v in els:
                old = 0.05 if ELEM_BEATS.get(a) == v else -0.05 if ELEM_LOSES.get(a) == v else 0.0
                self.assertEqual(S.elem_adv(a, v), old)
                for inc in (0.0, 0.1, -0.3, 0.123456789):
                    x = inc
                    if ELEM_BEATS.get(a) == v:
                        x += 0.05
                    elif ELEM_LOSES.get(a) == v:
                        x -= 0.05
                    y = inc
                    adv = S.elem_adv(a, v)
                    if adv:
                        y += adv
                    self.assertEqual(x, y)
                self.assertEqual(S.elem_adv(a, v, ELEM_HIT), old / 0.05 * ELEM_HIT if old else 0.0)


if __name__ == '__main__':
    unittest.main()
