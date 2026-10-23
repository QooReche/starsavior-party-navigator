"""'누군가 턴 종료 시 턴 수가 차감' 효과(mc.any_turn_clock): 주인이 못 움직여도 다른 유닛의 행동 끝에 풀리는지. 비공개 표 불필요."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.starsavior.foe import FoeDef, gloss, load_foe


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

    def test_fresh_effect_ticks_on_the_applying_action(self):
        b, slow, other, foe = setup()
        e = give(slow, '불협화음(해제불가)', harmful=True, dur=3)
        e.clock = 'any_turn'
        e.fresh = True
        b.act(other)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 2)
        b.act(other)
        self.assertEqual(slow.eff['불협화음(해제불가)'].dur, 1)

    def test_same_named_foe_effect_uses_own_skill_glossary(self):
        raw = load_foe()
        name = '강인도 피해 무효'
        for foe_name, skill_name, clock, remaining in (
                ('집행자 길레', '천체를 불사르는 재액', 'owner_turn', 2),
                ('올베로스', '칼무덤', 'any_turn', 4)):
            for enabled in (True, False):
                with self.subTest(foe=foe_name, enabled=enabled):
                    ui = next(i for i, u in enumerate(raw['u']) if u['n'] == foe_name)
                    fd = FoeDef(raw, ui, stats_override={'hp': 10**8, 'atk': 1})
                    b = battle([unit('ally', hp=10**8)], [fd],
                               mc=dict(toughness='off', any_turn_clock=enabled),
                               opts={'coop': False, 'nova': False})
                    foe, ally = b.foes[0], b.allies[0]
                    skill = next(s for s in fd.skills.values() if s.name == skill_name)
                    # 전역 사전이 반대 시계여도 적 자신의 설명이 우선해야 한다.
                    fallback = 'any_turn' if clock == 'owner_turn' else 'owner_turn'
                    with patch('battlesim.starsavior.foe.gloss', return_value={name: {'clock': fallback}}), \
                         patch.object(b, 'choose_skill', return_value=(skill, ally)):
                        b.act(foe)
                    expected_clock = clock if enabled else 'owner_turn'
                    expected_dur = remaining if enabled else (2 if clock == 'owner_turn' else 5)
                    self.assertEqual((foe.eff[name].clock, foe.eff[name].dur),
                                     (expected_clock, expected_dur))
                    b.act(ally)
                    self.assertEqual(foe.eff[name].dur, expected_dur - (expected_clock == 'any_turn'))

    def test_dot_death_ticks_survivors_once_without_double_ticking_domain(self):
        for side in (0, 1):
            for death in (True, False):
                with self.subTest(side=side, death=death):
                    b = battle([unit('a'), unit('b')], [unit('f'), unit('g')],
                               break_skill={'name': '행성 정화'}, turn_limit=1,
                               mc=dict(toughness='off'), opts={'coop': False, 'nova': False})
                    actor = (b.allies, b.foes)[side][0]
                    actor.gauge = 10000
                    actor.d.skills.clear()
                    if death:
                        actor.hp = 1
                        source = (b.foes, b.allies)[side][0]
                        bleed = give(actor, '출혈', src=source, harmful=True)
                        bleed.dot, bleed.inst = ('atk', .3), [[source, 3]]
                    survivors = [b.allies[1], b.foes[1]]
                    for v in survivors:
                        give(v, '불협화음(해제불가)', harmful=True, dur=1).clock = 'any_turn'
                        give(v, '타임 패러독스', harmful=True, dur=3).clock = 'any_turn'
                        give(v, '속도 감소', harmful=True, dur=3)
                    domain = give(b.allies[1], '마녀의 은총', dur=5)
                    domain.clock = 'global'
                    b.run()
                    self.assertEqual(actor.dead, death)
                    self.assertEqual(actor.actions, 1)
                    self.assertFalse(actor.acting)
                    for v in survivors:
                        self.assertNotIn('불협화음(해제불가)', v.eff)
                        self.assertEqual(v.eff['타임 패러독스'].dur, 2)
                        self.assertEqual(v.eff['속도 감소'].dur, 3)
                    self.assertEqual(domain.dur, 4)

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
