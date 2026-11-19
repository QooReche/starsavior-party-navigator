# -*- coding: utf-8 -*-
"""PC 26752678 U1–U7 facts/boundaries; no private tables needed to run.

Source row coverage and source locations: docs/marker_se_26752678.md.
Run with --mutations to verify the assertions reject broken implementations.
"""
import copy
import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path[:0] = [os.path.dirname(__file__), os.path.dirname(os.path.dirname(__file__))]
from simkit import battle, give, unit
from battlesim.mc import Ctx
from battlesim.api import simulate
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import UnitDef, Line
from battlesim.starsavior import marker_se as m


def setup(key, n=3, allies=(), mode='client'):
    b = battle([UnitDef(get_db(), key), *allies],
               [unit(str(i), hp=10**9, sa=1000) for i in range(n)],
               mc={m.RULE: mode}, opts={'coop': False, 'nova': False}, timeline=True)
    b.roll_hit = lambda *args: True
    return b, b.allies[0]


def context(a, slot, targets, src=None):
    c = Ctx(a, src or a, (src or a).d.skills[slot])
    c.targets, c.target = list(targets), targets[0] if targets else None
    return c


class MarkerSETest(unittest.TestCase):
    def test_u1_living_marker_set_and_no_reselection(self):
        b, a = setup('lyn', allies=[unit('star', element='별'), unit('moon', element='달')])
        star, moon = b.allies[1:]
        c = context(a, '궁극기', b.foes)
        b.run_own(a, c, 'own_pre')
        self.assertFalse(a.has(m.LYN))  # self deletion, SE10163015
        self.assertTrue(star.has(m.LYN))
        self.assertFalse(moon.has(m.LYN))
        star.eff.pop(m.LYN)
        b.run_own(a, c, 'own_post')
        self.assertFalse(star.has('치명타 피해 증가'))
        # Current marker ownership, not current element, selects the receiver.
        a.eff.pop('청풍(해제불가)', None)
        give(moon, m.LYN)
        b.run_own(a, c, 'own_post')
        self.assertTrue(moon.has('치명타 피해 증가'))

    def test_u2_no_prayer_all_living_not_only_revived(self):
        b, a = setup('elisa', allies=[unit('old'), unit('new'), unit('dead')])
        old, new, dead = b.allies[1:]
        dead.dead, dead.hp = True, 0
        give(old, m.PRAYER)
        c = context(a, '궁극기', [old])
        ln = next(x for x in b.lines_of(a) if x.slot == '궁극기' and x.eff.get('val') == 80)
        b.run_line(a, ln, c)
        self.assertEqual([x.gauge for x in b.allies], [8000, 0, 8000, 0])

    def test_u2_prayer_before_resurrection(self):
        b, a = setup('elisa', allies=[unit('dead'), unit('alive')])
        dead, alive = b.allies[1:]
        dead.dead, dead.hp = True, 0
        c = context(a, '궁극기', [dead])
        c.dead_targets.add(dead)
        b.run_own(a, c, 'own_post')
        self.assertFalse(dead.dead)
        self.assertEqual(dead.gauge, 8000)
        self.assertEqual(alive.gauge, 0)
        self.assertTrue(alive.has(m.PRAYER))
        self.assertFalse(dead.has(m.PRAYER))

    def test_u3_five_pairs_recheck_and_cleanup(self):
        for n in (1, 2, 3, 5, 6):
            b, a = setup('ceres', n)
            c = context(a, '특수기', b.foes[:1])  # never use actual hit count
            b.run_own(a, c, 'own_pre')
            self.assertEqual(a.stack(m.CERES_X), min(5, n))
            self.assertEqual(sum(x.has(m.CERES_Z) for x in b.foes), max(0, n-5))
            self.assertEqual(len([x for x in b.lines_of(a) if x.eff.get('native_target') == ('enemy_one_has', m.CERES_Z)]), 5)
            c.hit_targets = []
            b.run_own(a, c, 'own_post')
            self.assertEqual(a.gauge, 3500 * min(5, n))
            self.assertFalse(a.has(m.CERES_X))
            b._expire_checks(skill=True)
            self.assertFalse(any(x.has(m.CERES_Z) for x in b.foes))

    def test_u4_marker_moves_after_start_and_outside_skill_targets(self):
        b, a = setup('lydia')
        first, second, third = b.foes
        give(first, '미지의 주문', harmful=True)
        c = context(a, '특수기', [first])
        b.run_own(a, c, 'own_pre')
        self.assertTrue(first.has(m.LYDIA))
        first.eff.pop(m.LYDIA)
        give(second, m.LYDIA)
        give(third, '미지의 주문', harmful=True)  # newly applied state alone cannot select
        for x in b.foes:
            x.gauge = 5000
        b.run_own(a, c, 'own_post')
        self.assertEqual([x.gauge for x in b.foes], [5000, 3500, 5000])

    def test_u5_two_se_grants_and_after_active_cleanup(self):
        for slot, expected in (('기본기', 2), ('궁극기', 1)):
            b, a = setup('sunshine-cat-smile', 2)
            fresh, old = b.foes
            give(old, '물폭탄', harmful=True)
            c = context(a, slot, [fresh])
            # For this boundary the ultimate's target set is deliberately one
            # hit record: an old marker remains outside the skill receivers.
            events, original = [], b.exec_line
            def record(owner, ln, ctx):
                events.append((ln.src_kind, ln.eff.get('name'), ln.eff.get('kind')))
                return original(owner, ln, ctx)
            grants, add = [], b.add_effect
            def counted(owner, x, eff, ctx, **kw):
                if eff.get('name') == '물폭탄':
                    grants.append(x)
                return add(owner, x, eff, ctx, **kw)
            b.exec_line, b.add_effect = record, counted
            b.run_own(a, c, 'own_post')
            self.assertEqual(grants.count(fresh), expected)
            self.assertTrue(fresh.has('물폭탄'))
            self.assertFalse(old.has('물폭탄'))
            remove_i = next(i for i, x in enumerate(events) if x[1:] == ('물폭탄', 'remove'))
            self.assertTrue(all(i < remove_i for i, x in enumerate(events) if x[0] == 'active'))
            b._expire_checks(skill=True)
            self.assertFalse(any(x.has(m.FRESH) or x.has(m.OLD) for x in b.foes))

    def test_u5_failed_grants_do_not_delete_old_bomb(self):
        b, a = setup('sunshine-cat-smile', 2)
        fresh, old = b.foes
        give(old, '물폭탄', harmful=True)
        b.roll_hit = lambda *args: False
        c = context(a, '기본기', [fresh])
        b.run_own(a, c, 'own_post')
        self.assertFalse(fresh.has('물폭탄'))
        self.assertTrue(old.has('물폭탄'))

    def test_u5_aoe_condition_uses_any_record_and_preserves_receivers(self):
        b, a = setup('sunshine-cat-smile', 3)
        # Conditions may match another hit record, but NSETT_TARGET resolves
        # caster.TargetUid. A third unmarked record keeps NotTargetBuff true.
        give(b.foes[1], '물폭탄', harmful=True)
        b.run_own(a, context(a, '궁극기', b.foes), 'own_post')
        self.assertEqual([x.has('물폭탄') for x in b.foes], [True, False, False])
        self.assertTrue(b.foes[0].has(m.FRESH))

    def test_u6_named_shields_and_count_buff(self):
        b, a = setup('wedding-epindel', 4)
        give(b.foes[0], '보호막').shield = 0  # buff ID exists even with zero HP
        give(b.foes[1], 'arbitrary shield').shield = 10000
        give(b.foes[2], '공허 방패(해제불가)').shield = 1
        c = context(a, '궁극기', b.foes[:1])
        b.run_own(a, c, 'own_pre')
        self.assertEqual([x.has(m.WEDDING) for x in b.foes], [True, False, True, False])
        self.assertAlmostEqual(a.mods()['inc'], .3)
        self.assertEqual(a.n_good(), 0)
        b._expire_checks(skill=True)
        self.assertAlmostEqual(a.mods()['inc'], 0)

    def test_u6_all_three_level_rows_current_marker_set(self):
        for amount in (10, 15, 20):  # SE10563014 / 41 / 81
            b, a = setup('wedding-epindel', 2)
            ln = copy.copy(next(x for x in a.d.lines if x.slot == '궁극기' and x.eff['kind'] == 'gauge'))
            ln.eff = dict(ln.eff, val=-amount)
            a.d.lines = [ln]
            give(b.foes[1], m.WEDDING)
            for x in b.foes:
                x.gauge = 5000
            b.run_own(a, context(a, '궁극기', b.foes[:1]), 'own_post')
            self.assertEqual([x.gauge for x in b.foes], [5000, 5000 - amount*100])

    def test_u7_turn_marker_counter_and_lifetime(self):
        b, a = setup('lydia-moon-caster', 3, [unit('actor', skills=[dict(slot='기본기', dm=100, all=True)])])
        actor = b.allies[1]
        give(actor, '책임 전가(해제불가)')
        b.fire(a, 'ally_ts', Ctx(a, actor, None))
        self.assertTrue(actor.has(m.TURN))
        self.assertEqual(a.stack('퇴근 재촉(해제불가)'), 2)
        # Marker, not acting flag: an extra cast in the same global turn counts.
        actor.acting = False
        c = context(a, '기본기', b.foes[:1], actor)
        b.fire(a, 'ally_pre', c)
        self.assertEqual(a.stack(m.COUNT), 3)
        self.assertFalse(any(x.has(m.COUNT) for x in b.foes))
        b.fire(a, 'ally_post', c)
        self.assertEqual(a.stack('퇴근 재촉(해제불가)'), 5)
        self.assertEqual(a.gauge, 3000)
        self.assertFalse(a.has(m.COUNT))
        self.assertTrue(a.has(m.LOCK))
        b._expire_checks(skill=True)
        self.assertTrue(actor.has(m.TURN))
        b._tick_any_turn()
        self.assertFalse(actor.has(m.TURN))
        self.assertTrue(a.has(m.LOCK))
        b.fire(a, 'enemy_ts', Ctx(a, b.foes[0], None))
        self.assertFalse(a.has(m.LOCK))

    def test_u7_responsibility_without_turn_marker_does_not_count(self):
        b, a = setup('lydia-moon-caster', allies=[unit('actor')])
        actor = b.allies[1]
        actor.acting = True
        give(actor, '책임 전가(해제불가)')
        b.cast(actor, actor.d.skills['기본기'], target=b.foes[0])
        self.assertEqual(a.stack('퇴근 재촉(해제불가)'), 0)

    def test_hidden_counters_not_positive_or_negative_or_dispellable(self):
        for key, slot in (('ceres', '특수기'), ('wedding-epindel', '궁극기')):
            b, a = setup(key)
            give(b.foes[0], '보호막').shield = 10
            b.run_own(a, context(a, slot, b.foes), 'own_pre')
            self.assertEqual((a.n_good(), a.n_good(True), a.n_harmful()), (0, 0, 0))
            self.assertTrue(any(x in a.eff for x in m.HIDDEN))
            self.assertFalse(any(x.get('buff') in m.HIDDEN for x in b.timeline))
            present = {x for x in a.eff if x in m.HIDDEN}
            give(a, '공격력 증가', {'공격력%': 30})
            give(a, '속도 감소', {'속도%': -20}, harmful=True)
            for kind in ('강화', '약화'):
                ln = Line('[스킬 사용 후] 자신에게 (' + kind + '효과 해제) 효과 99개 해제', '궁극기', 'active')
                b.run_line(a, ln, context(a, slot, b.foes))
            self.assertFalse(a.has('공격력 증가') or a.has('속도 감소'))
            self.assertTrue(all(a.has(x) for x in present))

    def test_legacy_retains_replacements(self):
        for key in ('ceres', 'lydia-moon-caster'):
            b, a = setup(key, mode='legacy')
            self.assertTrue(any(x.eff.get('per_hit') for x in b.lines_of(a)))
            self.assertFalse(any(x.eff.get('native_se') for x in b.lines_of(a)))

    def test_other_savior_forms_unchanged_with_real_progress(self):
        encounter = {'waves': [[{'name': str(i), 'hp': 30000, 'atk': 500,
                                 'def': 1000, 'spd': 100} for i in range(3)]], 'max_turns': 20}
        for key in sorted(set(get_db().units) - m.KEYS):
            results = []
            for mode in ('legacy', 'client'):
                r = simulate([key], encounter, {'build': 'standard', 'n_runs': 1, 'seed': 19,
                              'rules_override': {m.RULE: mode}})
                self.assertGreater(r['outcome']['progress'], 0, key)
                results.append((r['outcome'], r['per_unit'], r['battle_stat']))
            self.assertEqual(*results, msg=key)


def mutations():
    original_targets = m.targets
    def no_marker_targets(b, a, ln, ctx):
        if ln.eff.get('native_target') == ('ally_has', m.LYN):
            return [x for x in b.alive(a.side) if x is not a and x.element == '별']
        return original_targets(b, a, ln, ctx)
    def prechecked(b, a, lines, ctx):
        if not any(x.eff.get('native_se') for x in lines):
            return False
        ready = [x for x in lines if b.line_ok(a, x, ctx)]
        for x in ready:
            b.exec_line(a, x, ctx)
        return True
    def revive_only(b, a, ln, ctx):
        if ln.eff.get('native_target') == ('ally_not_has', m.PRAYER):
            return [x for x in ctx.dead_targets if not x.dead]
        return original_targets(b, a, ln, ctx)
    def current_state(b, a, ln, ctx):
        if ln.eff.get('native_target') == ('enemy_has', m.LYDIA):
            return [x for x in ctx.targets if x.has('미지의 주문')]
        return original_targets(b, a, ln, ctx)
    def shield_hp(b, a, ln, ctx):
        if ln.eff.get('native_target') == ('enemy_shield', None):
            return [x for x in b.alive(1-a.side) if x.shield_total() > 0]
        return original_targets(b, a, ln, ctx)
    cases = [
        ('hidden grant removed', 'test_u1_living_marker_set_and_no_reselection', patch.object(m, 'apply_hidden', return_value=True)),
        ('fallback reselection', 'test_u1_living_marker_set_and_no_reselection', patch.object(m, 'targets', no_marker_targets)),
        ('revived receiver only', 'test_u2_no_prayer_all_living_not_only_revived', patch.object(m, 'targets', revive_only)),
        ('batch condition snapshot', 'test_u3_five_pairs_recheck_and_cleanup', patch.object(m, 'run_batch', prechecked)),
        ('marker expiry disabled', 'test_u3_five_pairs_recheck_and_cleanup', patch('battlesim.mc.Battle._expire_checks', return_value=None)),
        ('state instead of marker', 'test_u4_marker_moves_after_start_and_outside_skill_targets', patch.object(m, 'targets', current_state)),
        ('cleanup before active SE', 'test_u5_two_se_grants_and_after_active_cleanup', patch('battlesim.mc.after_active_se', return_value=False)),
        ('shield HP instead of ID', 'test_u6_named_shields_and_count_buff', patch.object(m, 'targets', shield_hp)),
        ('turn expiry disabled', 'test_u7_turn_marker_counter_and_lifetime', patch('battlesim.mc.Battle._tick_any_turn', return_value=None)),
    ]
    for name, test, mutation in cases:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(MarkerSETest(test))
        if result.wasSuccessful() or result.errors:
            raise AssertionError('mutation did not fail by assertion: ' + name + str(result.errors))
        print('KILLED', name)


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
