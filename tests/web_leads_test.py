"""Community leads checked against native buff-object semantics; public fixtures only."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p5_test import battle, unit, give
from battlesim.mc import Ctx, MC_OPTS
from battlesim.api import power_pen
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import UnitDef
from myinfo_combat_test import definition
from tools.ingame_check import low_priority
from tools.web_leads_audit import measure


def dot(b, source, target, name='연소', times=1, duration=2):
    b.add_effect(source, target, dict(name=name, props={}, max=5, dur=duration,
                                     times=times, judge=False), Ctx(source, source, None))


def cristelle_cast(slot, burns=0, legacy=False, extra_debuffs=0):
    d = definition('cristelle', skills=dict(basic=10, ultimate=10, passive=4))
    d.stats['cr'] = 0
    b = battle([d], [unit('target', hp=10**9, df=0)],
               mc={'debuff_instance_count': False} if legacy else {},
               opts={'coop': False, 'nova': False})
    a, v = b.allies[0], b.foes[0]
    if burns:
        dot(b, a, v, times=burns)
    for i in range(extra_debuffs):
        give(v, 'debuff ' + str(i), harmful=True)
    pieces = []
    original = b.apply_damage
    def record(src, target, damage, kind, **kw):
        pieces.append((kind, damage))
        return original(src, target, damage, kind, **kw)
    with patch.object(b, 'apply_damage', record):
        b.cast(a, a.d.skills[slot], target=v)
    return b, pieces


class DebuffObjectsTest(unittest.TestCase):
    def test_same_name_dots_from_two_casters_count_separately(self):
        b = battle([unit('one'), unit('two')], [unit('target', hp=10**9)])
        a, other = b.allies
        v = b.foes[0]
        dot(b, a, v, times=2)
        dot(b, other, v, times=1)
        dot(b, a, v, '출혈', times=2)
        give(v, '방어력 감소', harmful=True)
        give(v, '공격력 감소', harmful=True)
        give(v, '속도 감소', harmful=True)
        self.assertEqual(v.n_harmful(), 8)
        self.assertEqual([x[0] for x in v.eff['연소'].inst], [a, a, other])

    def test_level_stacks_markers_and_gauge_are_not_extra_objects(self):
        b = battle([unit('one')], [unit('target')])
        a, v = b.allies[0], b.foes[0]
        give(v, 'level debuff', harmful=True, stacks=5)
        give(v, 'buff', stacks=5)
        give(v, 'marker', harmful=True).check = True
        v.gauge = 8000
        self.assertEqual(v.n_harmful(), 1)
        v.gauge -= 2000
        self.assertEqual(v.n_harmful(), 1)
        dot(b, a, v, '빙결', times=2)
        dot(b, a, v, '중독', times=2)
        self.assertEqual(v.n_harmful(), 5)

    def test_expired_instances_stop_counting(self):
        b = battle([unit('one', hp=10**9), unit('two')], [unit('target', hp=10**9)],
                   opts={'coop': False})
        a, other = b.allies
        v = b.foes[0]
        dot(b, a, v, times=2, duration=1)
        dot(b, other, v, times=2, duration=2)
        b.act(v)
        self.assertEqual(v.n_harmful(), 2)
        b.act(v)
        self.assertEqual(v.n_harmful(), 0)

    def test_cristelle_ultimate_counts_instances_and_caps_at_five(self):
        for burns, other, expected in [(0, 0, 0), (1, 0, 1), (2, 0, 2), (4, 0, 4), (5, 3, 5)]:
            with self.subTest(burns=burns, other=other):
                _, pieces = cristelle_cast('궁극기', burns, extra_debuffs=other)
                self.assertEqual(sum(k == 'chain' for k, _ in pieces), expected)

    def test_legacy_counts_names_and_keeps_old_damage(self):
        _, one = cristelle_cast('궁극기', 1, legacy=True)
        _, five = cristelle_cast('궁극기', 5, legacy=True)
        self.assertEqual(one, five)
        self.assertEqual(sum(k == 'chain' for k, _ in five), 1)


class LeadContractsTest(unittest.TestCase):
    def test_basic_chain_is_one_conditional_hit_and_gauge_is_thirty(self):
        for burns, expected in [(0, 0), (1, 1), (5, 1)]:
            b, pieces = cristelle_cast('기본기', burns)
            self.assertEqual(sum(k == 'chain' for k, _ in pieces), expected)
            self.assertEqual(b.allies[0].gauge, 3000)

    def test_ultimate_extends_only_burn_not_every_debuff(self):
        b = battle([UnitDef(get_db(), 'cristelle')], [unit('v', hp=10**9)],
                   opts={'coop': False, 'nova': False})
        a, v = b.allies[0], b.foes[0]
        dot(b, a, v, times=2)
        dot(b, a, v, '출혈')
        give(v, '방어력 감소', harmful=True, dur=2)
        b.roll_hit = lambda *args: True
        b.cast(a, a.d.skills['궁극기'], target=v)
        self.assertEqual([n for _, n in v.eff['연소'].inst], [3, 3])
        self.assertEqual(v.eff['출혈'].inst[0][1], 2)
        self.assertEqual(v.eff['방어력 감소'].dur, 2)

    def test_carmen_selected_level_gauge_matches_local_table(self):
        for level, gauge in [(1, 1500), (4, 2000), (8, 3000), (10, 3000)]:
            d = definition('wedding-carmen', skills=dict(special=level, passive=4))
            b = battle([d, unit('ally')], [unit('foe')], opts={'coop': False})
            a, v = b.allies
            b.cast(a, a.d.trigger_skills['특수기'], extra=True, target=v, via='reaction')
            self.assertEqual((a.gauge, v.gauge), (gauge, gauge))

    def test_ignition_adds_one_percent_per_stack_only_against_star(self):
        damage = {}
        for elem in ('별', '달'):
            for stacks in (0, 5):
                b = battle([UnitDef(get_db(), 'cristelle')], [unit('v', hp=10**9, df=0, element=elem)],
                           opts={'coop': False, 'nova': False})
                a, v = b.allies[0], b.foes[0]
                give(a, '점화', {'vs 별 속성 피해 증가': 1}, stacks=stacks)
                c = Ctx(a, a, a.d.skills['기본기'])
                damage[elem, stacks] = b.final_dmg(a, v, 10000, c, False, 0, 0, 1, None)
        self.assertEqual(damage['별', 5] - damage['별', 0], 500)
        self.assertEqual(damage['달', 5], damage['달', 0])

    def test_crit_counter_and_nova_are_additive(self):
        b = battle([unit('a')], [unit('v', df=0)])
        a, v = b.allies[0], b.foes[0]
        c = Ctx(a, a, a.d.skills['기본기'])
        c.inc = .15
        v.last_slot = '기본기'
        self.assertEqual(b.final_dmg(a, v, 10000, c, True, .8, 0, 1, None), 20500)

    def test_power_penalty_uses_current_table(self):
        self.assertEqual(power_pen(864, 1000, get_db()), (86.4, .959, 1.041))

    def test_audit_includes_main_hit_and_preserves_result(self):
        from tools.ingame_check import run
        r = measure('36-36', 2, 7, None, False)
        self.assertEqual(r['summary'], run('36-36', 2, {}, 7, True, None))
        self.assertGreater(r['cristelle']['damage_per_cast']['궁극기'], 0)
        # A single un-debuffed cast has no chain: it must still be measured.
        def fake_run(*args):
            b, _ = cristelle_cast('궁극기', 0)
            return {'damage': b.allies[0].dmg}
        with patch('tools.web_leads_audit.run', fake_run):
            single = measure('36-36', 1, 7, None, False)
        self.assertEqual(single['cristelle']['damage_per_cast']['궁극기'], single['summary']['damage'])


if __name__ == '__main__':
    low_priority()
    if '--mutations' in sys.argv:
        with patch.dict(MC_OPTS, debuff_instance_count=False):
            result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(DebuffObjectsTest))
        caught = {getattr(test, 'test_case', test)._testMethodName for test, _ in result.failures}
        expected = {'test_same_name_dots_from_two_casters_count_separately',
                    'test_level_stacks_markers_and_gauge_are_not_extra_objects',
                    'test_expired_instances_stop_counting',
                    'test_cristelle_ultimate_counts_instances_and_caps_at_five'}
        print('Legacy omission detected:', caught == expected and not result.errors)
        sys.exit(0 if caught == expected and not result.errors else 1)
    unittest.main(verbosity=2)
