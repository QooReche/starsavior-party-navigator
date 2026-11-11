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
