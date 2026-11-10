# -*- coding: utf-8 -*-
"""cond_count_bind=holding: 「미보유」 키는 뒤따르는 「중첩수」의 대상이 아니다(루그 설중사우, 표 조건 52189~52191).
실행: python -X utf8 -I tests/cond_count_bind_test.py"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battlesim.mc import Battle, Ctx, Eff                       # noqa: E402
from battlesim.metrics import unit_def                          # noqa: E402
from battlesim.starsavior.foe import stage_waves                # noqa: E402

SEOLJUNG = '설중화(해제불가)'
GEUPGEUP = '급급여율령(해제불가)'


def _battle(**rules):
    _, waves = stage_waves('clo', '달 회랑', 'FLOOR 355')
    d = waves[0][0]
    b = Battle([unit_def('lugh')], [[d]], random.Random(3), mc=rules)
    b.spawn_wave()
    return b, b.allies[0], b.foes[0]


def _buff(u, name, stacks):
    e = Eff(name, {}, 99, float('inf'), u, False)
    e.stacks, e.fixed = stacks, True
    u.eff[name] = e


def _gauge_lines(a):
    return [l for l in a.d.lines
            if ('자신이 보유', SEOLJUNG) in l.params and ('자신이 미보유', GEUPGEUP) in l.params
            and any(k == '중첩수' for k, _ in l.params)]


class CondCountBindTest(unittest.TestCase):
    def test_lines_exist(self):
        b, a, foe = _battle()
        self.assertEqual(sorted(dict(l.params)['중첩수'] for l in _gauge_lines(a)), ['1', '2', '3'])

    def _fired(self, mode, stacks, with_geupgeup=False):
        b, a, foe = _battle(cond_count_bind=mode)
        a.eff.clear()
        _buff(a, SEOLJUNG, stacks)
        if with_geupgeup:
            _buff(a, GEUPGEUP, 1)
        ctx = Ctx(a, foe, a.d.skills['특수기'])
        return [dict(l.params)['중첩수'] for l in _gauge_lines(a) if b.cond_ok(a, l, ctx)]

    def test_holding_counts_the_held_buff(self):
        for stacks in (1, 2, 3):
            with self.subTest(stacks=stacks):
                self.assertEqual(self._fired('holding', stacks), [str(stacks)])

    def test_last_key_never_fires(self):
        for stacks in (1, 2, 3):
            with self.subTest(stacks=stacks):
                self.assertEqual(self._fired('last_key', stacks), [])

    def test_geupgeup_present_blocks_in_both_modes(self):
        for mode in ('holding', 'last_key'):
            self.assertEqual(self._fired(mode, 2, with_geupgeup=True), [])


if __name__ == '__main__':
    unittest.main()
