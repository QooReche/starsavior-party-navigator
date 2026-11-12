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
from battlesim.rules import MC_RULES   # noqa: E402
from battlesim.starsavior.foe import stage_waves   # noqa: E402
from tools.build_foe_auto import Unknown, unit_rules   # noqa: E402

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


class FoeSkillOrderTest(unittest.TestCase):
    def setup(self, **opts):
        _, waves = stage_waves('cube', '인터페이스', '인터페이스')
        d = next(d for w in waves for d in w if d.name == '복제체 샤를')
        b = battle([unit('a', hp=10 ** 7, atk=100000)], [d], mc=opts)
        f = b.foes[0]
        f.cd = {}
        return b, f

    def test_builder_translates_order_and_rejects_unknown(self):
        gu = dict(SkillOrderList=['NSI_SKILL_2_SPECIAL', 'NSI_SKILL_3_HYPER', 'NSI_SKILL_1_ATTACK'])
        self.assertEqual(unit_rules({'sk': []}, {}, gu, {}, {}, {}, {}, {})['order'],
                         ['특수기', '궁극기', '기본기'])
        self.assertNotIn('order', unit_rules({'sk': []}, {}, {}, {}, {}, {}, {}, {}))
        gu['SkillOrderList'] = ['NSI_UNKNOWN']
        with self.assertRaises(Unknown):
            unit_rules({'sk': []}, {}, gu, {}, {}, {}, {}, {})

    def test_cube_mapping_and_actual_cast(self):
        for mode, slot in (('data', '특수기'), ('default', '궁극기')):
            with self.subTest(mode=mode):
                b, f = self.setup(foe_skill_order=mode)
                self.assertEqual(f.key, 'foe:1563:388')
                self.assertEqual(f.d.skill_order, ['특수기', '궁극기', '기본기'])
                self.assertEqual(b.choose_skill(f)[0].slot, slot)
                b.act(f)
                self.assertEqual(f.cast_count[slot], 1)
                self.assertEqual(f.cast_count.get('궁극기' if slot == '특수기' else '특수기', 0), 0)
                # 선택 검사만 통과하고 전투가 전혀 진행되지 않는 시험을 막음.
                b.act(b.allies[0])
                self.assertGreater(b.progress(), 0)

    def test_cooldown_conditions_silence_and_missing_order(self):
        b, f = self.setup()
        f.cd['특수기'] = 2
        self.assertEqual(b.choose_skill(f)[0].slot, '궁극기')
        f.cd['궁극기'] = 2
        self.assertEqual(b.choose_skill(f)[0].slot, '기본기')
        f.cd = {}
        f.d.auto = {'특수기': {'rows': [{'c': [['self_has', ['없는 효과']]], 'f': []}]}}
        self.assertEqual(b.choose_skill(f)[0].slot, '궁극기')
        from p3_test import give
        give(f, '침묵', harmful=True)
        self.assertEqual(b.choose_skill(f)[0].slot, '기본기')
        b = battle([unit('a')], [unit('ordinary', skills=SK)])
        b.foes[0].cd = {}
        self.assertEqual(b.choose_skill(b.foes[0])[0].slot, '궁극기')

    def test_default_and_legacy_metadata(self):
        for key, value, legacy in (('foe_skill_order', 'data', 'default'), ('empty_attack', 'process', 'skip')):
            rule = MC_RULES[key]
            self.assertEqual(rule['value'], value)
            self.assertEqual(rule['legacy'], legacy)
            for field in ('alt', 'grade', 'note', 'source'):
                self.assertTrue(rule[field])


if __name__ == '__main__':
    unittest.main(verbosity=1)
