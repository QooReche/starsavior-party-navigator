"""Casebook mechanics: synthetic states and standard builds, never account inputs."""
import copy
import io
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.api import _norm_party
from battlesim.mc import Battle, Ctx, Unit
from battlesim.metrics import unit_def
from battlesim.starsavior import cosmo_raid as C
from battlesim.starsavior import guild_bfb as G
from battlesim.starsavior.data import get_db

FALL = '몰락한 사념(해제불가)'


def mogulus(level=0):
    waves, meta = C.build_waves('mogulus', 3, level)
    defs, _ = _norm_party({'units': ['asherah-order-striker', 'gille', 'haydee', 'ceres']},
                          get_db(), 'fixed', 'standard')
    defs = copy.deepcopy(defs)
    for d in defs:
        d.lines = []  # Isolate the boss effect from ally reactions.
    b = Battle(defs, waves, random.Random(71), mc={'cosmo_raid_boss': 'on'},
               opts={'coop': False, 'forced_coop': False, 'nova': False}, turn_limit=meta['turn_limit'])
    b.spawn_wave()
    return b, b.foes[0]


class CasebookMechanicsTest(unittest.TestCase):
    def test_mogulus_zero_speed_and_direct_gauge(self):
        b, boss = mogulus()
        a = b.allies[0]
        self.assertGreater(a.spd(), 0)
        b.cast(boss, boss.d.skills['기본기'], target=a)
        self.assertTrue(a.has(FALL))
        self.assertEqual(a.eff[FALL].dur, 3)
        self.assertEqual(a.spd(), 0)
        b.set_gauge(a, 3000)
        self.assertEqual(a.gauge, 3000)
        del a.eff[FALL]
        b.dirty(a)
        self.assertGreater(a.spd(), 0)

    def test_speed_floor(self):
        for minimum in (0,):
            for reduction, expected in ((-50, 50), (-100, minimum), (-300, minimum)):
                b = battle([unit('a')], [unit('f')])
                a = b.allies[0]
                give(a, '타임 패러독스', {'속도%': reduction})
                self.assertEqual(a.spd(), expected)
                b.set_gauge(a, 10000)
                self.assertEqual(b.pick_next([a]), (a, 0))

    def test_mogulus_fixed_speed_ignores_increases_and_global_expiry(self):
        b, boss = mogulus()
        a = b.allies[0]
        b.cast(boss, boss.d.skills['기본기'], target=a)
        give(a, '속도 증가', {'속도%': 200})
        a.leader = True
        self.assertEqual(a.eff[FALL].clock, 'any_turn')
        for remaining in (3, 2, 1):
            self.assertEqual(a.spd(), 0)
            self.assertEqual(a.eff[FALL].dur, remaining)
            b._tick_any_turn()
        self.assertFalse(a.has(FALL))
        self.assertGreater(a.spd(), 0)

    def test_mogulus_shield_at_skill_start(self):
        for slot in ('기본기', '궁극기'):
            for shield in (False, True):
                with self.subTest(slot=slot, shield=shield):
                    b, boss = mogulus()
                    a = b.allies[0]
                    if shield:
                        give(a, '보호막').shield = 1
                    b.cast(boss, boss.d.skills[slot], target=a)
                    self.assertEqual(a.has(FALL), not shield)
                    # The hit can consume the shield; the pre-hit decision stays fixed.
                    if shield:
                        self.assertEqual(a.shield_total(), 0)

    def test_mogulus_gauge_requires_marker_and_hit(self):
        for holder in (None, 0, 1):
            b, boss = mogulus()
            a = b.allies[0]
            if holder is not None:
                b.cast(boss, boss.d.skills['기본기'], target=b.allies[holder])
            boss.gauge = 0
            b.cast(a, a.d.skills['기본기'], target=boss)
            self.assertGreater(b.progress(), 0)
            self.assertEqual(boss.gauge, 2000 if holder is not None else 0)

    def test_bridal_stack_cap_and_attack(self):
        waves, _ = G.build_waves(0)
        b = Battle([unit('a', atk=1000)], waves, random.Random(1), mc={'guild_boss': 'on'})
        b.spawn_wave()
        for foe in list(b.foes):
            b.kill(foe, None)
        b.spawn_wave()
        a = b.allies[0]
        initial = b.atk_stat(a)
        for count in range(1, 13):
            b.gb.after_cast(a, a.d.skills['기본기'], Ctx(a, a, a.d.skills['기본기']), False)
            self.assertEqual(a.stack(G.B1), min(count, 10))
            self.assertAlmostEqual(b.atk_stat(a), initial * (1 + .03 * min(count, 10)))

    def test_ceres_gauge_delays_broken_target(self):
        b = battle([unit_def('ceres')], [unit('boss', hp=10**9, sa=50)],
                   opts={'coop': False, 'nova': False})
        a, foe = b.allies[0], b.foes[0]
        foe.broken, foe.sa, foe.gauge = True, 0, 9000
        give(a, '냉각', stacks=5).maxs = 5
        b.cast(a, a.d.skills['궁극기'], target=foe)
        self.assertGreater(b.progress(), 0)
        self.assertTrue(foe.broken)
        self.assertEqual(foe.gauge, 2000)
        self.assertFalse(a.has('냉각'))

    def test_gille_crush_gauge_and_speed_reduction(self):
        b = battle([unit_def('gille'), unit_def('asherah-order-striker'), unit('other')],
                   [unit('boss', hp=10**9, sa=50)], opts={'coop': False, 'nova': False})
        g, a, other = b.allies
        give(a, '파쇄', {'강인도 고정 피해': 1})
        b.cast(g, g.d.skills['궁극기'], target=b.foes[0])
        self.assertGreater(b.progress(), 0)
        self.assertEqual((g.gauge, a.gauge, other.gauge), (2000, 2000, 0))
        self.assertTrue(a.has('서곡(해제불가)'))
        self.assertTrue(b.foes[0].has('속도 감소'))
        self.assertEqual(b.foes[0].spd(), 80)

    def test_carmen_reaction_blocked_while_broken(self):
        for broken in (False, True):
            b = battle([unit_def('wedding-carmen'), unit('damage', hp=10**6, atk=10**5)],
                       [unit('foe', hp=10**9)], opts={'coop': False, 'nova': False})
            a, damage = b.allies
            b.fire(a, 'battle_start', Ctx(a, a, None))
            a.broken, a.cd['특수기'] = broken, 0
            damage.hp = damage.maxhp / 2
            b.cast(b.foes[0], b.foes[0].d.skills['기본기'], target=damage)
            self.assertEqual(damage.shield_total() > 0, not broken)
            # The independent passive still gives Carmen 30% while broken.
            self.assertEqual([a.gauge, damage.gauge], [3000, 0] if broken else [6000, 3000])

    def test_mogulus_challenge_strips_after_attack(self):
        b, boss = mogulus(18)
        a = b.allies[0]
        for name in list(a.eff):
            if a.eff[name].category == 'buff':
                del a.eff[name]
        shield = give(a, '보호막(해제불가)')
        shield.shield, shield.fixed = 10**9, True
        b.put_eff(a, '공격력 증가', {'공격력%': 30}, dur=3, src=a, cat='buff', fixed=False)
        b.cast(a, a.d.skills['기본기'], target=boss)
        self.assertTrue(a.has('공격력 증가'))
        b.cast(boss, boss.d.skills['기본기'], target=a)
        self.assertFalse(a.dead)
        self.assertFalse(a.has('공격력 증가'))
        self.assertEqual(b.gb.stats['strip'], 1)

    def test_gille_resistance_before_finale(self):
        for finale in (False, True):
            b = battle([unit_def('gille')], [unit('boss', hp=10**9, sa=50)],
                       opts={'coop': False, 'nova': False})
            a, foe = b.allies[0], b.foes[0]
            if finale:
                give(a, '피날레(해제불가)', dur=float('inf'))
            with patch.object(b, 'roll_hit', return_value=False) as judge:
                b.cast(a, a.d.skills['궁극기'], target=foe)
            self.assertEqual(foe.has('속도 감소'), finale)
            self.assertEqual(judge.call_count, int(not finale))

    def test_asherah_break_extra_turn_and_chain(self):
        for sa in (1, 50):
            b = battle([unit_def('asherah-order-striker')],
                       [unit('boss', hp=10**9, sa=sa, boss=True)], opts={'coop': False, 'nova': False})
            a, foe = b.allies[0], b.foes[0]
            a.acting = True
            give(a, '파쇄', {'강인도 고정 피해': 1})
            seen = []
            original = b.apply_damage
            def record(src, dst, damage, kind, **kw):
                seen.append((kind, damage))
                return original(src, dst, damage, kind, **kw)
            with patch.object(b, 'apply_damage', record):
                b.cast(a, a.d.skills['기본기'], target=foe)
                self.assertFalse(any(k == 'chain' for k, _ in seen))
                b.flush_chain_damage()
            self.assertGreater(b.progress(), 0)
            self.assertEqual(foe.broken, sa == 1)
            self.assertEqual(a.extra_turn, sa == 1)
            self.assertEqual(any(k == 'chain' and n > 0 for k, n in seen), sa == 1)

    def test_first_turn_nova_requires_force(self):
        for force in (0, 4):
            b = battle([unit_def('haydee')], [unit('foe', hp=10**9)],
                       opts={'coop': False, 'nova_policy': 'manual'})
            a = b.allies[0]
            self.assertEqual(b.team_nova, 0)
            b.team_nova = force
            ctx = b.cast(a, a.d.skills['기본기'])
            self.assertEqual(ctx.nb, force == 4)
            self.assertEqual(a.shield_total() > 0, force == 4)

    def test_amora_five_insight_cleanses_at_turn_start(self):
        for stacks in (4, 5):
            b = battle([unit_def('amora')], [unit('foe', hp=10**9)])
            a = b.allies[0]
            give(a, '통찰', stacks=stacks).maxs = 5
            give(a, '공격력 감소', {'공격력%': -30}, harmful=True)
            b.fire(a, 'own_ts', Ctx(a, a, None))
            self.assertEqual(a.has('공격력 감소'), stacks < 5)
            self.assertEqual(a.has('밤에 피는 꽃(해제불가)'), stacks == 5)

    def test_lydia_special_and_ultimate_slow_are_different(self):
        for slot, expected in (('특수기', 90), ('궁극기', 70)):
            b = battle([unit_def('lydia')], [unit('foe', hp=10**9, sa=100)],
                       opts={'coop': False, 'nova': False})
            a, foe = b.allies[0], b.foes[0]
            with patch.object(b, 'roll_hit', return_value=True), patch.object(b.rng, 'random', return_value=0):
                b.cast(a, a.d.skills[slot], target=foe)
            self.assertEqual(foe.spd(), expected)

    def test_waltz_ultimate_gauge_and_basic_healing(self):
        b = battle([unit_def('waltz-asherah'), unit('ally', hp=10**6)],
                   [unit('foe', hp=10**9)], opts={'coop': False, 'nova': False})
        a, ally = b.allies
        ally.hp = ally.maxhp / 2
        b.cast(a, a.d.skills['궁극기'])
        self.assertEqual([x.gauge for x in b.allies], [0, 1500])
        before = ally.hp
        b.cast(a, a.d.skills['기본기'], extra=True, via='coop')
        self.assertGreater(ally.hp, before)

    def test_maid_ceres_dust_extra_heals_and_cleanses(self):
        for dust in (4, 5):
            b = battle([unit_def('ceres-sun-supporter'), unit('ally', hp=10**6)],
                       [unit('foe', hp=10**9, sa=100)], opts={'coop': False, 'nova': False})
            a, ally = b.allies
            a.acting = True
            give(a, '먼지 포착(해제불가)', stacks=dust).maxs = 10
            give(ally, '공격력 감소', {'공격력%': -30}, harmful=True)
            ally.hp = 1
            b.cast(a, a.d.skills['기본기'])
            self.assertEqual(ally.hp > 1, dust == 5)
            self.assertEqual(ally.has('공격력 감소'), dust == 4)

    def test_tyria_real_paradox_stops_passive_gauge(self):
        old = C._DATA_FILE
        try:
            C.use_data(str(ROOT / 'tests/fixtures/cosmo_raid_1022.json'))
            waves, _ = C.build_waves('tyria', 3, 0)
            b = Battle([unit('a', hp=10**9), unit('b', hp=10**9)], waves, random.Random(4),
                       mc={'cosmo_raid_boss': 'on'}, opts={'coop': False, 'nova': False})
            b.spawn_wave()
            a, other = b.allies
            a.gauge, other.gauge = 8000, 1000
            boss = b.foes[0]
            ln = next(x for x in boss.d.lines if x.eff.get('name') == '타임 패러독스'
                      and x.eff['target'] == '행동 게이지가 가장 높은 적')
            b.cast(boss, boss.d.skills[ln.slot], target=other)
            self.assertTrue(a.has('타임 패러독스'))
            self.assertFalse(other.has('타임 패러독스'))
            self.assertEqual(a.spd(), 0)
            self.assertGreater(b.pick_next([a, other])[1], 0)
            self.assertIs(b.pick_next([a, other])[0], other)
        finally:
            C.use_data(old)

    def test_carnelia_debuff_gauge_and_challenge_are_separate(self):
        old = C._DATA_FILE
        try:
            C.use_data(str(ROOT / 'tests/fixtures/cosmo_raid_1022.json'))
            for level in (0, 18):
                for harmful in (False, True):
                    waves, _ = C.build_waves('carnelia', 3, level)
                    b = Battle([unit('attacker', hp=10**9)], waves, random.Random(1),
                               mc={'cosmo_raid_boss': 'on'}, opts={'coop': False, 'nova': False})
                    b.spawn_wave()
                    a, boss = b.allies[0], b.foes[0]
                    give(boss, '안식을 위한 기도(해제불가)', stacks=4).maxs = 4
                    if harmful:
                        give(a, '공격력 감소', {'공격력%': -30}, harmful=True)
                    boss.gauge = 0
                    b.cast(a, a.d.skills['기본기'], target=boss)
                    self.assertGreater(b.progress(), 0)
                    self.assertEqual(boss.gauge, (1500 + (1000 if level else 0)) * harmful)
        finally:
            C.use_data(old)


def mutations():
    original_add = Battle.add_effect
    original_line = Battle.exec_line
    original_speed = Unit.spd
    original_cast = Battle.cast
    def no_extra_heal(b, owner, sk, *args, **kw):
        if not (owner.key == 'ceres-sun-supporter' and sk.slot == '특수기' and kw.get('extra')):
            return original_cast(b, owner, sk, *args, **kw)
    def no_cleanse(b, owner, ln, ctx):
        if ln.eff.get('name') != '디버프 해제':
            return original_line(b, owner, ln, ctx)
    def drop_fall(b, owner, target, eff, *args, **kw):
        if eff.get('name') != FALL:
            return original_add(b, owner, target, eff, *args, **kw)
    def no_gauge(b, target, value, **kw):
        return None
    def no_slow(b, owner, target, eff, *args, **kw):
        if eff.get('name') != '속도 감소':
            return original_add(b, owner, target, eff, *args, **kw)
    cases = [
        ('lost fall', 'test_mogulus_shield_at_skill_start', patch.object(Battle, 'add_effect', drop_fall)),
        ('boss gauge off', 'test_mogulus_gauge_requires_marker_and_hit', patch.object(Battle, 'set_gauge', no_gauge)),
        ('ceres gauge off', 'test_ceres_gauge_delays_broken_target', patch.object(Battle, 'set_gauge', no_gauge)),
        ('gille gauge off', 'test_gille_crush_gauge_and_speed_reduction', patch.object(Battle, 'set_gauge', no_gauge)),
        ('carmen broken ignored', 'test_carmen_reaction_blocked_while_broken', patch.object(Battle, 'no_react', lambda b, u: b.incapacitated(u))),
        ('strip off', 'test_mogulus_challenge_strips_after_attack', patch.object(Battle, '_dispel_n_ordered', lambda *a: None)),
        ('gille slow off', 'test_gille_resistance_before_finale', patch.object(Battle, 'add_effect', no_slow)),
        ('asherah chain off', 'test_asherah_break_extra_turn_and_chain', patch.object(Battle, 'chain', lambda *a: None)),
        ('carnelia gauge off', 'test_carnelia_debuff_gauge_and_challenge_are_separate', patch.object(Battle, 'set_gauge', no_gauge)),
        ('global expiry off', 'test_mogulus_fixed_speed_ignores_increases_and_global_expiry', patch.object(Battle, '_tick_any_turn', lambda *a: None)),
        ('speed floor legacy', 'test_speed_floor_and_legacy', patch.object(Unit, 'spd', lambda u: max(1, original_speed(u)))),
        ('amora cleanse off', 'test_amora_five_insight_cleanses_at_turn_start', patch.object(Battle, 'exec_line', no_cleanse)),
        ('lydia slow off', 'test_lydia_special_and_ultimate_slow_are_different', patch.object(Battle, 'add_effect', no_slow)),
        ('waltz gauge off', 'test_waltz_ultimate_gauge_and_basic_healing', patch.object(Battle, 'set_gauge', no_gauge)),
        ('maid extra off', 'test_maid_ceres_dust_extra_heals_and_cleanses', patch.object(Battle, 'cast', no_extra_heal)),
        ('tyria zero off', 'test_tyria_real_paradox_stops_passive_gauge', patch.object(Unit, 'spd', lambda u: max(1, original_speed(u)))),
        ('bridal stack off', 'test_bridal_stack_cap_and_attack', patch.object(G.Controller, '_compete', lambda *a: None)),
    ]
    for name, test, mutation in cases:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(CasebookMechanicsTest(test))
        if result.errors or not result.failures:
            raise AssertionError((name, result.errors, result.failures))
        print('detected:', name)


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main(verbosity=2)
