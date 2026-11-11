"""순수 Python 가속: 색인 무효화, 판/유닛 격리, 사건 문맥·합산 순서 보존."""
import copy
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim import mc
from battlesim.api import _CustomFoe
from battlesim.starsavior.parser import Line
from battlesim.starsavior.parser import _map_prop, _map_prop_raw
from battlesim.starsavior.cosmo_raid import Controller


def definition():
    return _CustomFoe(dict(name='test', hp=10000, atk=1000, spd=100,
                           skills=[dict(slot='기본기', dm=100)]), 0)


def line(kind, amount):
    ln = Line('[턴 시작 시] 자신에게 행동 게이지 %s%%p 증가' % amount, '패시브', 'passive')
    ln.kind = kind
    return ln


def battle():
    d = definition()
    d.lines = [line('own_ts', 10), line('own_te', 20), line('own_ts', 30)]
    return mc.Battle([d, d], [[d]], random.Random(1), timeline=True, semantic_cache={})


class AccelTest(unittest.TestCase):
    def test_put_eff_refresh_and_statless_markers(self):
        b = battle()
        u = b.allies[0]
        cached = u.mods()
        e = b.put_eff(u, 'marker', {}, dur=2, maxs=3, cat='marker')
        b.put_eff(u, 'marker', {}, dur=5, maxs=3, refresh_props=True)
        self.assertEqual((e.stacks, e.dur), (2, 5))
        self.assertIs(u.mods(), cached)
        b.put_eff(u, 'marker', {'생명력%': 20}, add=0, refresh_props=True)
        self.assertEqual(u.maxhp, u.maxhp0 * 1.4)
        u.hp = u.maxhp
        b.put_eff(u, 'marker', {}, add=0, refresh_props=True)
        self.assertEqual(u.hp, u.maxhp0)  # HP clips immediately, before mods is read.
        self.assertEqual(u.mods()['hpp_buff'], 0)

    def test_put_eff_cap_and_ordered_replacement(self):
        b = battle()
        u = b.allies[0]
        b.put_eff(u, 'first', {'받는 피해 감소': 1e18})
        props = {'받는 피해 감소': -1e18, '피해 감소': 100.0}
        b.put_eff(u, 'second', props)
        cached = u.mods()
        self.assertEqual(cached['red']['all'], 1.0)
        b.put_eff(u, 'second', props, dur=5)
        self.assertIs(u.mods(), cached)
        b.put_eff(u, 'second', dict(reversed(list(props.items()))), refresh_props=True)
        self.assertEqual(u.mods()['red']['all'].hex(), (0.0).hex())

    def test_add_effect_refresh_mutation_and_category(self):
        b = battle()
        u = b.allies[0]
        u.ban_refuse = False
        eff = dict(name='test', props={'공격력%': 25}, max=2, dur=2, times=1)
        b.add_effect(u, u, eff, None)
        self.assertEqual(u.mods()['atkp'], .25)
        b.add_effect(u, u, eff, None)
        self.assertEqual(u.mods()['atkp'], .5)
        eff['props']['공격력%'] = 50  # same dict identity, changed value
        b.add_effect(u, u, eff, None)
        self.assertEqual(u.mods()['atkp'], 1.0)
        b.put_eff(u, '강화 불가', {}, cat='debuff')
        self.assertEqual(u.mods()['atkp'], 0)
        b.allies[1].side = 1
        b.add_effect(b.allies[1], u, eff, None)  # buff -> debuff while suppressed
        self.assertEqual(u.mods()['atkp'], 1.0)

    def test_add_effect_marker_and_empty_refresh(self):
        b = battle()
        u = b.allies[0]
        cached = u.mods()
        marker = dict(name='test marker', props={}, max=3, dur=2, times=1, cast_marker=True)
        b.add_effect(u, u, marker, None)
        b.add_effect(u, u, marker, None)
        self.assertEqual(u.stack(marker['name']), 2)
        self.assertIs(u.mods(), cached)
        eff = dict(name='test HP', props={'생명력%': 50}, max=1, dur=2, times=1)
        b.add_effect(u, u, eff, None)
        cached = u.mods()
        b.add_effect(u, u, dict(eff, props={}, dur=5), None)
        self.assertIs(u.mods(), cached)  # empty input keeps existing props in add_effect
        self.assertEqual(u.eff[eff['name']].dur, 5)

    def test_timers_preserve_cache_until_removal_and_clip_hp(self):
        for clock in ('owner_turn', 'any_turn', 'global', 'shield'):
            with self.subTest(clock=clock):
                b = mc.Battle([definition()], [], random.Random(1), opts={'coop': False})
                u = b.allies[0]
                e = b.put_eff(u, 'timer', {'생명력%': 50}, dur=2)
                e.clock = 'owner_turn' if clock == 'shield' else clock
                b.break_skill_rule = dict(domain='timer')
                if clock == 'shield':
                    e.shield = 100
                tick = {'owner_turn': lambda: b._act_turn(u),
                        'any_turn': b._tick_any_turn,
                        'global': lambda: b._tick_break_domain('global'),
                        'shield': lambda: b._tick_shields(u)}[clock]
                cached = u.mods()
                u.hp = u.maxhp
                tick()
                self.assertEqual(e.dur, 1)
                self.assertIs(u.mods(), cached)
                tick()
                self.assertNotIn('timer', u.eff)
                self.assertEqual(u.hp, u.maxhp0)
                self.assertEqual(u.mods()['hpp_buff'], 0)
                if clock == 'owner_turn':
                    self.assertEqual(u.actions, 2)

    def test_owner_dot_stack_expiry_fresh_and_skip_tick(self):
        # This cache regression protects the legacy owner-turn duration path.
        b = mc.Battle([definition()], [], random.Random(1), opts={'coop': False},
                      mc={'dot_hot_lifetime': 'turn_end'})
        u = b.allies[0]
        e = b.put_eff(u, 'instances', {'생명력%': 25}, maxs=2, add=2)
        e.dot = ('atk', 0)
        e.inst = [[u, 1], [u, 2]]
        u.hp = u.maxhp
        e.fresh = True
        cached = u.mods()
        b._act_turn(u)
        self.assertFalse(e.fresh)
        self.assertIs(u.mods(), cached)
        e.skip_tick = True
        b._act_turn(u)
        self.assertFalse(e.skip_tick)
        self.assertIs(u.mods(), cached)
        b._act_turn(u)
        self.assertEqual(e.stacks, 1)
        self.assertEqual(u.hp, u.maxhp0 * 1.25)
        b._act_turn(u)
        self.assertNotIn(e.name, u.eff)
        self.assertEqual(u.hp, u.maxhp0)
        self.assertEqual(u.actions, 4)

    def test_cosmo_marker_and_modifier_stack_drop(self):
        for name, props, suppressed in [('marker', {}, False), ('HP', {'생명력%': 25}, False),
                                        ('강화 불가', {}, True)]:
            with self.subTest(name=name):
                b = battle()
                u = b.allies[0]
                u.ban_refuse = not suppressed
                controller = Controller(b)
                b.put_eff(u, 'buff', {'공격력%': 50})
                b.put_eff(u, name, props, maxs=2, add=2, cat='debuff')
                cached = u.mods()
                controller._set_stacks(u, name, 2)
                self.assertIs(u.mods(), cached)
                u.hp = u.maxhp
                controller._set_stacks(u, name, 1)
                if props:
                    self.assertEqual(u.hp, u.maxhp0 * 1.25)
                elif not suppressed:
                    self.assertIs(u.mods(), cached)
                controller._drop(u, name)
                self.assertNotIn(name, u.eff)
                self.assertEqual(u.hp, u.maxhp0)
                self.assertEqual(u.mods()['atkp'], .5)
                if suppressed:
                    b.put_eff(u, name, {}, cat='debuff')
                    self.assertEqual(u.mods()['atkp'], 0)
                    controller._set_stacks(u, name, 0)
                    self.assertEqual(u.mods()['atkp'], .5)

    def test_step_duration_reuse_and_replacement_invalidate(self):
        b = battle()
        u = b.allies[0]
        high = dict(name='상급 공격력 증가', props={'공격력%': 50}, max=1, dur=2, times=1)
        low = dict(high, name='공격력 증가', props={'공격력%': 10}, dur=5)
        b.add_effect(u, u, high, None)
        cached = u.mods()
        b.add_effect(u, u, low, None)
        self.assertIs(u.mods(), cached)
        self.assertEqual(u.eff[high['name']].dur, 5)
        self.assertTrue(u.eff[high['name']].skip_tick)
        # Synthetic same-group state: replacing a lower step must invalidate even
        # if the retained high-step effect is statless and already at its cap.
        b.put_eff(u, high['name'], {}, refresh_props=True)
        b.put_eff(u, low['name'], low['props'])
        self.assertEqual(u.mods()['atkp'], .1)
        b.add_effect(u, u, dict(high, props={}), None)
        self.assertEqual(u.mods()['atkp'], 0)

    def test_property_mapping_cache_is_pure_bounded_and_reused(self):
        _map_prop.cache_clear()
        names = ['공격력%', '속도', '생명력%', 'vs 태양 속성 피해 증가', '궁극기 피해 증가',
                 '선제 방어 확률', '선제 방어 무시 확률', 'unmapped']
        for name in names:
            self.assertEqual(_map_prop(name), _map_prop_raw(name))
            self.assertEqual(_map_prop(name), _map_prop_raw(name))
        self.assertEqual(_map_prop.cache_info().hits, len(names))
        for i in range(4100):
            _map_prop(str(i))
        self.assertLessEqual(_map_prop.cache_info().currsize, 4096)

    def test_index_order_and_reuse(self):
        b = battle()
        u = b.allies[0]
        expected = tuple(ln for ln in b.lines_of(u) if mc.line_kind(ln) == 'own_ts')
        self.assertEqual(len(expected), 2)
        with patch.object(b, 'lines_of', wraps=b.lines_of) as read:
            self.assertEqual(b.kind_lines(u, 'own_ts'), expected)
            for _ in range(3):
                self.assertEqual(b.kind_lines(u, 'own_ts'), expected)
                self.assertEqual(len(b.kind_lines(u, 'own_te')), 1)
                self.assertEqual(b.kind_lines(u, 'missing'), ())
            self.assertEqual(read.call_count, 1)

    def test_lines_replacement_same_length(self):
        b = battle()
        u = b.allies[0]
        before = b.kind_lines(u, 'own_ts')
        u.d.lines = [line('own_te', 50), line('own_ts', 60), line('own_te', 70)]
        after = b.kind_lines(u, 'own_ts')
        self.assertEqual(len(before), 2)
        self.assertEqual(after, (u.d.lines[1],))

    def test_lines_append(self):
        b = battle()
        u = b.allies[0]
        before = b.kind_lines(u, 'own_ts')
        added = line('own_ts', 40)
        u.d.lines.append(added)
        self.assertEqual(b.kind_lines(u, 'own_ts'), before + (added,))

    def test_definition_copy_rebuilds_even_with_shared_lines(self):
        b = battle()
        u = b.allies[0]
        before = b.kind_lines(u, 'own_ts')
        u.d = copy.copy(u.d)  # guild_bfb.on_wave처럼 lines 참조는 유지함.
        with patch.object(b, 'lines_of', wraps=b.lines_of) as read:
            self.assertEqual(b.kind_lines(u, 'own_ts'), before)
            self.assertEqual(read.call_count, 1)
        self.assertIs(u._kind_index[0], u.d)

    def test_index_unit_and_battle_isolation(self):
        b = battle()
        a, other = b.allies
        other.d = a.d
        b.kind_lines(a, 'own_ts')
        b.kind_lines(other, 'own_ts')
        self.assertIsNot(a._kind_index, other._kind_index)
        second = mc.Battle([a.d], [], random.Random(2), semantic_cache=b._semantic_cache)
        u = second.allies[0]
        self.assertIsNone(u._kind_index)
        second.kind_lines(u, 'own_ts')
        self.assertIsNot(a._kind_index, u._kind_index)

    def test_enemy_lines_and_cache_switch(self):
        b = battle()
        b.spawn_wave()
        u = b.foes[0]
        expected = b.kind_lines(u, 'own_ts')
        self.assertTrue(expected)
        b.enemy_lines = False
        self.assertEqual(b.kind_lines(u, 'own_ts'), ())
        b.enemy_lines = True
        self.assertEqual(b.kind_lines(u, 'own_ts'), expected)
        with patch.object(mc, 'ENGINE_CACHE', False), patch.object(b, 'lines_of', wraps=b.lines_of) as read:
            for _ in range(2):
                self.assertEqual(tuple(b.kind_lines(u, 'own_ts')), expected)
            self.assertEqual(read.call_count, 2)

    def test_mods_nested_maps_are_private_and_reset(self):
        b = battle()
        u, other = b.allies
        props = {'vs 태양 속성 피해 증가': 15, '기본기 피해 증가': 25, '받는 피해 감소': 35}
        b.put_eff(u, 'test', props)
        old = u.mods()
        for key in ('inc_vs', 'inc_slot', 'red'):
            self.assertTrue(old[key])
            self.assertEqual(other.mods()[key], {})
            self.assertIsNot(old[key], other.mods()[key])
        u.eff.clear()
        b.dirty(u)
        for key in ('inc_vs', 'inc_slot', 'red'):
            self.assertEqual(u.mods()[key], {})
            self.assertTrue(old[key])

    def test_mods_preserves_float_addition_order(self):
        b = battle()
        u = b.allies[0]
        # 결합/정렬하면 작은 항이 사라지는 경계값.
        values = (1e18, -1e18, 1.0)
        expected = 0.0
        for i, value in enumerate(values):
            b.put_eff(u, str(i), {'공격력%': value}, maxs=3, add=3)
            expected += value / 100.0 * 3
        self.assertNotEqual(expected, 0.0)
        self.assertEqual(u.mods()['atkp'].hex(), expected.hex())

    def test_string_caches_follow_text_changes_and_are_bounded(self):
        a = '[턴 시작 시] 자신에게 〈test〉 (2턴 / 피해 분담(수호) +30%)'
        b = a.replace('30%', '50%')
        for raw in (a, b):
            self.assertEqual(mc.paren_after_name(raw), mc.paren_after_name.__wrapped__(raw))
            self.assertEqual(mc._line_rest_raw(raw), mc._line_rest_raw.__wrapped__(raw))
        self.assertNotEqual(mc.paren_after_name(a), mc.paren_after_name(b))
        for i in range(4100):
            mc.paren_after_name(str(i))
            mc._line_rest_raw(str(i))
        self.assertLessEqual(mc.paren_after_name.cache_info().currsize, 4096)
        self.assertLessEqual(mc._line_rest_raw.cache_info().currsize, 4096)


if __name__ == '__main__':
    unittest.main(verbosity=2)
