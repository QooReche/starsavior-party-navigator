# -*- coding: utf-8 -*-
"""오토 스킬 시도 순서(SkillOrderList) 회귀: python -X utf8 -I tests/skill_order_test.py

게임 코드 NKM.decompiled.cs 6378: 유닛 SkillOrderList 순서로 쓸 수 있는 첫 스킬. 기본 [궁극기, 특수기, 기본기].
에밀리 등 9명은 [특수기, 궁극기, 기본기](data/auto_skill.json order ← tools/build_auto_skill.py). 규칙 mc.skill_order(default = 옛 동작)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from p3_test import battle, unit   # noqa: E402
from battlesim import mc   # noqa: E402

SK = [dict(slot='기본기', dm=100), dict(slot='특수기', dm=150, cd=3), dict(slot='궁극기', dm=300, cd=5)]


class SkillOrderTest(unittest.TestCase):
    def pick(self, key, mode='data', ready=('특수기', '궁극기')):
        b = battle([unit(key, skills=SK)], [unit('f', hp=10 ** 7)], mc={'auto_skill': 'data', 'skill_order': mode})
        a = b.allies[0]
        a.key = key
        a.cd = {s: (0 if s in ready else 2) for s in ('특수기', '궁극기')}
        sk, _ = b.choose_skill(a)
        return sk.slot

    def test_data_has_nine_special_first(self):
        order = mc.auto_skill_order()
        self.assertEqual(len(order), 9)
        self.assertEqual(order['emily'], ['특수기', '궁극기', '기본기'])

    def test_emily_special_first(self):
        self.assertEqual(self.pick('emily'), '특수기')
        self.assertEqual(self.pick('emily@bloom'), '특수기')     # 개화 변형은 기본 키 순서

    def test_default_order_for_others(self):
        self.assertEqual(self.pick('amora'), '궁극기')

    def test_falls_through_when_on_cooldown(self):
        self.assertEqual(self.pick('emily', ready=('궁극기',)), '궁극기')
        self.assertEqual(self.pick('emily', ready=()), '기본기')

    def test_legacy_default(self):
        self.assertEqual(self.pick('emily', mode='default'), '궁극기')


if __name__ == '__main__':
    unittest.main(verbosity=1)
