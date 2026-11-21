"""Build 26610546 G2 regressions, synthetic inputs and independent assertions."""
import itertools
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from survey_g1_test import setup, selected, mutations
from simkit import battle, unit, give
from battlesim.mc import Battle, Ctx
from battlesim.metrics import get_db
from battlesim.starsavior.myinfo_combat import select_skills


class SurveyG2(unittest.TestCase):
    def test_bloom_level(self):
        for key in ('besta@개화(SSR)', 'vera@개화(SSR)', 'bunny-scarlet@개화(SSR)'):
            with self.subTest(key=key):
                d = selected(key, passive=1)
                p = next(x for x in d.u['sk'] if x['sl'] == '고유 패시브')
                raw = next(x for x in get_db().units[key]['sk'] if x['sl'] == '고유 패시브')
                self.assertEqual(p.get('level'), 1)
                self.assertEqual(p['ef'], [raw['L']['ln'][i] for i in raw['L']['e'][raw['L']['ei'][0]]])
                self.assertNotEqual(p['ef'], raw['ef'])
                b = battle([d], [unit('foe')])
                self.assertGreater(b.rule_hits['bloom_passive_levels'], 0)

    def test_independent_caps_and_duration(self):
        b, a, v = setup('lugh')
        e = next(x.eff for x in b.lines_of(a) if x.eff.get('name') == '파사인')
        with patch.object(b, 'roll_hit', return_value=True):
            for dur in (1, 2, 3, 9):
                b.add_effect(a, v, dict(e, dur=dur), None)
        self.assertEqual(v.stack('파사인'), 3)
        self.assertEqual([it[1] for it in v.eff['파사인'].inst], [1, 2, 3])
        self.assertAlmostEqual(v.mods()['red']['기본기'], -0.15)
        # Action with no available skill still ages each instance independently.
        v.d.skills = {}
        b.act(v)
        self.assertEqual(v.stack('파사인'), 2)
        self.assertEqual([it[1] for it in v.eff['파사인'].inst], [1, 2])

    def test_independent_hot(self):
        b, a, v = setup('ceres-sun-supporter')
        ln = next(x for x in b.lines_of(a) if x.eff.get('name') == '상쾌한 기분(해제불가)')
        a.hp = a.maxhp * .1
        for dur in (1, 2, 2, 2, 2, 9):
            b.add_effect(a, a, dict(ln.eff, dur=dur), None, hot=.03)
        self.assertEqual(a.stack(ln.eff['name']), 5)
        before = a.hp
        b._tick_dot_hot(a)
        self.assertAlmostEqual(a.hp-before, 5 * int(a.maxhp*.03), delta=5)
        self.assertEqual(a.stack(ln.eff['name']), 4)

    def test_unlimited_dots(self):
        b, a, v = setup('cristelle')
        for name in ('출혈', '연소'):
            e = dict(name=name, props={}, dur=2, max=None, times=7, dot=('atk', .2))
            b.add_effect(a, v, e, None)
            self.assertEqual(v.stack(name), 7)

    def test_smile_special_no_move_or_refresh(self):
        for marked in (False, True):
            b, a, v = setup('sunshine-cat-smile')
            b.mc['marker_se_flow'] = 'legacy'  # this suite mutates the old replacement switches
            if marked:
                give(v, '물폭탄', harmful=True, dur=1)
            b.cast(a, a.d.trigger_skills['특수기'], target=v)
            self.assertEqual(v.eff['물폭탄'].dur if marked else v.stack('물폭탄'), 1 if marked else 0)
            b.cast(a, a.d.skills['기본기'], target=v)
            self.assertEqual(v.stack('물폭탄'), 1)
            self.assertEqual(v.eff['물폭탄'].dur, 3)

    def test_smile_crit_basic_only(self):
        b, a, v = setup('sunshine-cat-smile')
        b.mc['marker_se_flow'] = 'legacy'
        give(v, '물폭탄', harmful=True)
        for slot, expected in [('기본기', .2), ('특수기', 0), ('궁극기', 0)]:
            c = Ctx(a, a, a.d.skills.get(slot) or a.d.trigger_skills[slot])
            c.target, c.targets = v, [v]
            b.run_own(a, c, 'own_pre')
            self.assertAlmostEqual(c.local_by[v]['cd'] + c.cd, expected)

    def test_smile_new_target_retries_and_after_active_cleanup(self):
        for slot, outcomes, moved in [('기본기', [False, True], True),
                ('기본기', [False, False], False), ('궁극기', [False], False)]:
            b = battle([selected('sunshine-cat-smile')], [unit('new'), unit('old')])
            b.mc['marker_se_flow'] = 'legacy'
            a, new, old = b.allies[0], *b.foes
            give(old, '물폭탄', harmful=True)
            c = Ctx(a, a, a.d.skills[slot])
            c.target, c.targets = new, [new]
            at_active = []
            run = b.run_batch
            def observe(owner, lines, ctx):
                if any(x.src_kind != 'passive' for x in lines):
                    at_active.append(old.has('물폭탄'))
                return run(owner, lines, ctx)
            with patch.object(b, 'roll_hit', side_effect=itertools.chain(outcomes, itertools.repeat(False))) as roll, patch.object(b, 'run_batch', observe):
                b.run_own(a, c, 'own_post')
            self.assertEqual(roll.call_count, len(outcomes))
            self.assertEqual(new.has('물폭탄'), moved)
            self.assertEqual(old.has('물폭탄'), not moved)
            self.assertTrue(all(at_active), 'old marker is removed after active SEs')

    def test_scarlet_skipped_turn_keeps_roll(self):
        b, a, v = setup('scarlet')
        b.fire(a, 'own_ts', Ctx(a, a, None))
        balls = lambda: (a.stack('노멀볼(해제불가)'), a.stack('세븐볼(해제불가)'))
        first = balls()
        self.assertEqual(sum(first), 3)
        # End a skipped turn, then re-enter TURN_START: no second draw.
        b._finish_action(a)
        with patch.object(b.R(0), 'random', return_value=0):
            b.fire(a, 'own_ts', Ctx(a, a, None))
        self.assertEqual(balls(), first)
        self.assertEqual(a.stack('세븐볼 카운팅용 레벨 버프'), 1)
        b.cast(a, a.d.skills['기본기'], target=v)
        self.assertEqual(a.stack('세븐볼 카운팅용 레벨 버프'), 0)
        b.fire(a, 'own_ts', Ctx(a, a, None))
        self.assertEqual(sum(balls()), 3)

    def test_cristelle_all_elements(self):
        b = battle([selected('cristelle'), unit('sun', element='태양'), unit('moon', element='달')], [unit('foe')])
        a = b.allies[0]
        ln = next(x for x in b.lines_of(a) if x.slot == '특수기' and x.eff.get('name') == '점화' and x.eff['kind'] == 'buff')
        b.run_line(a, ln, Ctx(a, a, a.d.trigger_skills['특수기']))
        self.assertEqual([x.stack('점화') for x in b.allies], [0, 2, 2])

    def test_shield_counts_enemies(self):
        b, a, v = setup('wedding-epindel')
        b.mc['marker_se_flow'] = 'legacy'  # native uses shield template IDs and hidden marks
        for name in ('shield1', 'shield2'):
            give(v, name).shield = 100
        ln = next(x for x in b.lines_of(a) if x.eff.get('scope') == 'shield_all')
        c = Ctx(a, a, a.d.skills['궁극기'])
        b.run_line(a, ln, c)
        self.assertAlmostEqual(c.inc, ln.eff['val']/100)

    def test_gauge_before_lock(self):
        b = battle([selected('lydia-moon-caster'), unit('caster', skills=[dict(slot='기본기', dm=1)])], [unit('foe')])
        b.mc['marker_se_flow'] = 'legacy'  # native requires an actual TURN_START marker
        a, actor = b.allies
        actor.acting = True
        give(actor, '책임 전가(해제불가)')
        give(a, '퇴근 재촉(해제불가)', stacks=5)
        a.gauge = 0
        c = Ctx(actor, actor, actor.d.skills['기본기'])
        c.targets = list(b.foes)
        b.fire(a, 'ally_post', c)
        self.assertEqual(a.gauge, 3000)
        b.fire(a, 'ally_post', c)
        self.assertEqual(a.gauge, 3000)
        self.assertEqual(a.stack('메이드 리디아 패시브 행게 카운팅 버프'), 1)

    def test_damage_break_equal_boundary(self):
        b, a, v = setup('rosaria')
        a.hp = int(a.maxhp * .4)
        give(a, '대미지 브레이크')
        before = a.hp
        b.apply_damage(v, a, a.maxhp, 'skill')
        self.assertEqual(a.hp, before)
        self.assertFalse(a.dead)


CASES = {
 'smile_waterbomb_scope': ['test_smile_special_no_move_or_refresh', 'test_smile_crit_basic_only', 'test_smile_new_target_retries_and_after_active_cleanup'],
 'scarlet_pinball_marker': ['test_scarlet_skipped_turn_keeps_roll'],
 'cristelle_ignite_targets': ['test_cristelle_all_elements'],
 'gauge_lock_order': ['test_gauge_before_lock'],
}
if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations(SurveyG2, CASES)
    else:
        unittest.main()
