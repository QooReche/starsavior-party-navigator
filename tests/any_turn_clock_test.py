"""'누군가 턴 종료 시 턴 수가 차감' 효과(mc.any_turn_clock): 주인이 못 움직여도 다른 유닛의 행동 끝에 풀리는지. 비공개 표 불필요."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.starsavior.foe import gloss


def setup(rule=True):
    b = battle([unit('slow', spd=100), unit('other', spd=100)], [unit('foe', hp=10**8)],
               mc=dict(toughness='off', any_turn_clock=rule), opts={'coop': False, 'nova': False})
    slow, other = b.allies
    return b, slow, other, b.foes[0]


class AnyTurnClockTest(unittest.TestCase):
    def test_any_turn_effect_ticks_on_other_units_turn_end(self):
        b, slow, other, foe = setup()
        e = give(slow, '불협화음(해제불가)', harmful=True, dur=3)
        e.clock = 'any_turn'
        b.act(other)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 2)
        b.act(foe)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 1)
        b.act(other)
        self.assertNotIn('불협화음(해제불가)', slow.eff)

    def test_any_turn_effect_on_foe_ticks_on_ally_turn(self):
        b, slow, other, foe = setup()
        e = give(foe, '타임 패러독스', harmful=True, dur=2)
        e.clock = 'any_turn'
        b.act(other)
        self.assertEqual(foe.eff['타임 패러독스'].dur, 1)

    def test_fresh_effect_skips_the_applying_action(self):
        b, slow, other, foe = setup()
        e = give(slow, '불협화음(해제불가)', harmful=True, dur=3)
        e.clock = 'any_turn'
        e.fresh = True
        b.act(other)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 3)
        b.act(other)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 2)

    def test_owner_turn_effect_unchanged_by_other_units(self):
        b, slow, other, foe = setup()
        give(slow, '속도 감소', harmful=True, dur=2)
        b.act(other)
        b.act(foe)
        self.assertEqual(slow.eff['속도 감소'].dur, 2)
        b.act(slow)
        self.assertEqual(slow.eff['속도 감소'].dur, 1)

    def test_rule_off_keeps_legacy_owner_clock(self):
        b, slow, other, foe = setup(rule=False)
        e = give(slow, '불협화음(해제불가)', harmful=True, dur=3)
        e.clock = 'any_turn'
        b.act(other)
        b.act(foe)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 3)

    def test_glossary_marks_global_turn_counting_effects(self):
        g = gloss()
        for name in ('불협화음(해제불가)', '몰락한 사념(해제불가)', '타임 패러독스', '철혈의 비늘갑'):
            self.assertEqual(g.get(name, {}).get('clock'), 'any_turn', name)
        self.assertNotIn('clock', g.get('속도 감소', {}))


if __name__ == '__main__':
    unittest.main()
