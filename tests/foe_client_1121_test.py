"""Old guild PC rules: exercise real definitions and mutation failures."""
import copy
import io
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import unit, battle
from battlesim.gauge import turn_key
from battlesim.mc import Battle, Ctx
from battlesim.starsavior.foe import stage_waves
from battlesim.starsavior.parser import Line
from battlesim.starsavior import foe_client


def guild(tab, mode='client'):
    _, waves = stage_waves('guild', tab, '길드 방어전 6단계')
    defs = copy.deepcopy(waves[-1])
    b = Battle([unit('dummy', hp=10**9, atk=10)], [defs], random.Random(3),
               mc={'foe_client_flow': mode}, opts={'coop': False, 'nova': False}, timeline=True)
    b.spawn_wave()
    return b


class FoeClientTest(unittest.TestCase):
    def test_catch_order(self):
        extra = turn_key(True, 0, 0, 0)
        first = turn_key(False, 10000, 0, 0, 10)
        second = turn_key(False, 20000, 200, 9000, 11)
        ordinary = turn_key(False, 30000, 1000, 9999)
        self.assertEqual(sorted([ordinary, second, first, extra]), [extra, first, second, ordinary])

    def test_shark_four_turns(self):
        b = guild('심해의 폭군')
        shark = next(u for u in b.foes if u.d.name == '심해의 폭군')
        self.assertEqual(shark.spd(), 0)
        for i in range(4):
            b.act(b.allies[0])
            self.assertEqual(shark.stack('굼뜬 이동(해제불가)'), i + 1)
        self.assertEqual(shark.gauge, 10000)
        # Gauge buffs cannot cancel the catch, even though natural/reset paths can.
        b.run_line(shark, Line('[스킬 사용 후] 자신에게 행동 게이지 50%p 감소', '기본기', 'active'), Ctx(shark, shark, None))
        self.assertEqual(shark.gauge, 10000)
        b.allies[0].gauge = 20000
        self.assertIs(min(b.alive(0) + b.alive(1), key=b._turn_key), shark)
        b.act(shark)
        self.assertGreater(shark.actions, 0)
        self.assertFalse(shark.has('굼뜬 이동(해제불가)'))
        self.assertFalse(shark.has('다음 턴'))
        for _ in range(4):
            b.act(b.allies[0])
        self.assertEqual(shark.gauge, 10000)
        b.act(shark)
        self.assertEqual(shark.actions, 2)

    def test_shien_reacts_and_gains_gauge(self):
        for slot, gain, name in [('기본기', 3000, '쌍성각이에요'), ('특수기', 5000, '화륜쌍추예요')]:
            b = guild('티엔')
            tien, shien = [next(u for u in b.foes if u.d.name == n) for n in ('티엔', '시엔')]
            self.assertEqual(shien.spd(), 0)
            self.assertTrue(any(e.armor_ban for e in shien.eff.values()))
            a = b.allies[0]
            a.d.skills['기본기'].ab = 2
            before = shien.sa
            b.tough_hit(a, shien, Ctx(a, a, a.d.skills['기본기']))
            self.assertEqual(shien.sa, before)
            self.assertGreater(b.rule_hits['superarmor_damage_ban'], 0)
            with patch.dict(b.mc, foe_client_flow='off'):
                b.tough_hit(a, shien, Ctx(a, a, a.d.skills['기본기']))
            self.assertEqual(shien.sa, before - 2)
            with patch.object(b, 'choose_skill', return_value=(tien.d.skills[slot], b.allies[0])):
                b.act(tien)
            self.assertEqual(shien.gauge, gain)
            self.assertTrue(any(e.get('skill_name') == name and e.get('via') == 'reaction' for e in b.timeline))
            # A real normal action remains possible despite speed zero.
            b.set_gauge(shien, 10000)
            self.assertEqual(b.pick_next([shien]), (shien, 0))
            b.act(shien)
            self.assertEqual(shien.actions, 1)

    def test_legacy_no_catch(self):
        b = guild('심해의 폭군', 'off')
        shark = next(u for u in b.foes if u.d.name == '심해의 폭군')
        for _ in range(4):
            b.act(b.allies[0])
        self.assertEqual(shark.gauge, 0)


def mutations():
    original = foe_client.attach

    def broken(d):
        rules = original(d)
        for ln in d.lines:
            ln.eff.pop('next_turn_catch', None)
        return {}

    # Remove the actual adapter fields, rather than changing a default assertion.
    with patch.object(foe_client, 'attach', broken):
        suite = unittest.TestSuite(FoeClientTest(n) for n in ('test_shark_four_turns', 'test_shien_reacts_and_gains_gauge'))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        assert len(result.failures) == 2 and not result.errors, (result.failures, result.errors)
    print('mutations: 2 assertion failures detected; restored')


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
