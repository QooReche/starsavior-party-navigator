"""Build 26610546 passive selection and per-cast M events; synthetic inputs only.

Sources: SE_TEMPLET_SKILL_1:24928-25019,41916-42282,9743-10074,
35607-35791; SKILL_LEVEL_GROUP_TEMPLET_1:19457-19504,31984-32031,
8184-8231,27643-27690; NKM.decompiled.cs:15602-15644,16135-16170.
"""
import os
import copy
import sys
import unittest
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from simkit import battle, give, unit
from battlesim.api import _norm_party
from battlesim.mc import Ctx
from battlesim.starsavior.data import get_db


def definition(key, level):
    # Mutation restores the previous maximum-level fallback instead of input selection.
    spec = {'key': key, 'myinfo_combat': {'skills': {
        'basic': 1, 'special': 1, 'ultimate': 1, 'passive': level}}}
    if os.environ.get('PASSIVE_LEVEL_MUTATION'):
        spec.pop('myinfo_combat')
    return copy.deepcopy(_norm_party([spec], get_db(), 'fixed')[0][0])


class PassiveLevelsTest(unittest.TestCase):
    def test_all_four_levels(self):
        for level in range(1, 5):
            with self.subTest(level=level):
                m = definition('professor-m', level)
                cooling = [ln.eff for ln in m.lines if ln.slot == '고유 패시브'
                           and ln.eff.get('name') == '냉각']
                self.assertEqual([e['chance'] for e in cooling], [(.5, .5, .75, 1)[level-1], 1])
                a = definition('asherah-order-striker', level)
                chains = [ln.eff for ln in a.lines if ln.slot == '고유 패시브' and ln.eff['kind'] == 'chain']
                self.assertEqual([e['coef'] for e in chains],
                                 [[.2, .2, 1, 1], [.2, .2, 1, 1], [.25, .25, 1.25, 1.25], [.3, .3, 1.5, 1.5]][level-1])
                self.assertTrue(all(e['damage_type'] == 'ADT_STAT_TRUE' for e in chains))
                lyn = definition('lyn', level)
                attack = [ln.eff['val'] for ln in lyn.lines if ln.slot == '고유 패시브'
                          and ln.eff.get('stat') == '공격력%' and ln.eff['kind'] == 'local']
                self.assertEqual(attack, [n * (2, 2, 3, 4)[level-1] for n in range(1, 6)])
                c = definition('wedding-carmen', level)
                gauge = [ln.eff['val'] for ln in c.lines if ln.slot == '고유 패시브' and ln.eff['kind'] == 'gauge']
                self.assertEqual(gauge, [(18, 18, 24, 30)[level-1]])
                for d, prop in [(m, 'atkp'), (a, 'atkp'), (lyn, 'atkp'), (c, 'hpp')]:
                    self.assertAlmostEqual(d.passive[prop], (0, .05, .1, .15)[level-1])

    def setup_cast(self, marked=False, element='태양'):
        b = battle([definition('professor-m', 4), definition('asherah-order-striker', 4)],
                   [unit('dummy', hp=10**9, element=element)],
                   mc={'toughness': 'off'}, opts={'coop': False, 'nova': False})
        m, a = b.allies
        if marked:
            give(a, '표본 행동 분석')
        return b, m, a

    def test_multihit_skill_and_following_turn_each_notify_once(self):
        for marked in (False, True):
            with self.subTest(marked=marked):
                b, m, a = self.setup_cast(marked)
                for slot in ('궁극기', '특수기'):
                    # Each invocation is a separate skill, as on an additional turn.
                    before = m.gauge, m.stack('냉각')
                    self.assertIsNotNone(b.cast(a, a.d.skills[slot], target=b.foes[0]))
                    self.assertEqual(m.gauge - before[0], 800 if marked else 400)
                    self.assertEqual(m.stack('냉각') - before[1], 2 if marked else 1)

    def test_real_coop_path_notifies_once(self):
        b, m, a = self.setup_cast(True)
        # M's basic marks the eligible ally and reserves its forced cooperation.
        before = m.gauge, m.stack('냉각')
        ctx = b.cast(m, m.d.skills['기본기'], target=b.foes[0])
        b.coop(m, ctx)
        self.assertEqual(a.cast_count['기본기(추가)'], 1)
        self.assertEqual(m.gauge - before[0], 800)
        self.assertEqual(m.stack('냉각') - before[1], 3)  # M basic supplies one; ally supplies two.

    def test_stat_true_damage_does_not_notify(self):
        b, m, a = self.setup_cast(True)
        ctx = Ctx(a, a, a.d.skills['특수기'])
        ctx.targets = ctx.hit_targets = [b.foes[0]]
        ctx.target = b.foes[0]
        eff = next(ln.eff for ln in a.d.lines if ln.eff['kind'] == 'chain'
                   and ln.eff.get('target') == '스킬 대상')
        before = b.foes[0].hp
        b.chain(a, eff, ctx)
        self.assertLess(b.foes[0].hp, before)
        self.assertEqual((m.gauge, m.stack('냉각')), (0, 0))

    def test_own_cooperation_does_not_supply_passive(self):
        b, m, a = self.setup_cast()
        # Omit the basic's own resource effect so only its notification is measured.
        b.cast(m, m.d.skills['기본기'], extra=True, target=b.foes[0], via='coop', skip_lines=True)
        self.assertEqual(m.cast_count['기본기(추가)'], 1)
        self.assertEqual((m.gauge, m.stack('냉각')), (0, 0))

    def test_cooling_damage_only_against_sun_and_consumed_at_end(self):
        for element in ('태양', '달'):
            damage = []
            for stacks in (0, 5):
                b, m, a = self.setup_cast(element=element)
                m.d.stats['cr'] = 0
                if stacks:
                    give(m, '냉각', props={'vs 태양 속성 피해 증가': 1}, stacks=stacks)
                    b.dirty(m)
                self.assertAlmostEqual(m.mods()['inc_vs'].get('태양', 0), stacks / 100)
                before = b.foes[0].hp
                b.cast(m, m.d.trigger_skills['특수기'], extra=True, target=b.foes[0], via='trigger')
                damage.append(before - b.foes[0].hp)
                self.assertEqual(m.stack('냉각'), 0)
            # Moon -> Sun already adds +5% advantage; cooling adds another +5 points.
            expected = 1.10 / 1.05 if element == '태양' else 1
            self.assertAlmostEqual(damage[1] / damage[0], expected, delta=2 / damage[0])


if __name__ == '__main__':
    unittest.main()
