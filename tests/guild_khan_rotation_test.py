"""26752678 칸 실제 정의: 중첩 경계·과열 행동 차단·클라 배치. legacy 변이도 검사함."""
import copy
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import unit
from battlesim.mc import Battle, Ctx, line_kind
from battlesim.starsavior.guild import build_waves
from battlesim import simulate

CLOCK = '오버클럭(해제불가)'
HEAT = '오버히트(해제불가)'


def battle(mode='client'):
    waves, meta = build_waves({'seasonId': 30101, 'step': 6})
    d = copy.deepcopy(next(d for d in waves[-1] if d.boss))
    b = Battle([unit('target%d' % i, hp=10**9, atk=1) for i in range(4)], [[d]], random.Random(3),
               opts={'coop': False, 'nova': False}, mc={'khan_passives': mode}, timeline=True,
               battle_mode=meta['battle_mode'])
    b.spawn_wave()
    return b, b.foes[0]


def stack(b, u, name, n):
    b.put_eff(u, name, {}, maxs=5, add=n, src=u, cat='debuff' if name == HEAT else 'buff', fixed=True)


class KhanTest(unittest.TestCase):
    def test_overclock_threshold(self):
        results = []
        for mode in ('client', 'snapshot'):
            b, boss = battle(mode)
            stack(b, boss, CLOCK, 4)
            stack(b, boss, HEAT, 3)
            boss.cd.update({'특수기': 99, '궁극기': 99})
            b._act_turn(boss)
            casts = [x for x in b.timeline if x.get('actor') == boss.name and x.get('skill_name') == '죽음의 손아귀']
            self.assertEqual(len(casts), 1 if mode == 'client' else 0, b.timeline)
            self.assertEqual(dict(b.unsup), {})
            results.append((boss.stack(CLOCK), boss.stack(HEAT), boss.gauge))
        self.assertEqual(results[0][:2], (0, 0), results)
        self.assertGreaterEqual(results[0][2], 2000, results)
        self.assertNotEqual(results[0], results[1], 'legacy로 꺼도 같은 시험은 무효')

    def test_overheat_threshold(self):
        values = []
        for mode in ('client', 'snapshot'):
            b, boss = battle(mode)
            stack(b, boss, HEAT, 4)
            stack(b, boss, CLOCK, 2)
            boss.gauge = 5000
            sk = copy.copy(b.allies[0].d.skills['기본기'])
            sk.all = True
            sk.tg = '적 전체'
            ctx = Ctx(boss, b.allies[0], sk)
            ctx.target, ctx.targets = boss, [boss]
            lines = [ln for ln in b.lines_of(boss) if line_kind(ln) == 'hit_self']
            self.assertGreater(len(lines), 4)
            b.run_batch(boss, lines, ctx)
            values.append((boss.stack(HEAT), boss.stack(CLOCK), boss.gauge, boss.has('과열 상태')))
        self.assertEqual(values[0], (0, 0, 0, True), values)
        self.assertNotEqual(values[0], values[1])

    def test_overheat_stun_and_debuff_stats(self):
        for mode, expect in (('client', True), ('snapshot', False)):
            b, boss = battle(mode)
            b.put_eff(boss, '과열 상태', {'피해 감소': -15}, dur=1, src=boss, cat='debuff')
            self.assertEqual(b.incapacitated(boss), expect)
            before = [u.hp for u in b.allies]
            b.cast(boss, boss.d.skills['궁극기'], extra=True, via='enforce')
            self.assertEqual([u.hp for u in b.allies] == before, expect)
            b._act_turn(boss)
            self.assertEqual([u.hp for u in b.allies] == before, expect)

    def test_real_seasons(self):
        for sid in (30101, 30102, 30104):
            w, meta = build_waves({'seasonId': sid, 'step': 6})
            self.assertEqual(meta['battle_mode'], 'boss_kill')
            self.assertEqual(meta['turn_limit'], 50)
            boss = next(d for d in w[-1] if d.boss)
            self.assertEqual(boss.spawn, 'S')
            self.assertIsNotNone(boss.game_slot)
            r = simulate(['gwen', 'fei', 'professor-m', 'amora'], {'guild': {'seasonId': sid, 'step': 6}},
                         {'build': 'standard', 'n_runs': 3, 'seed': 3})
            self.assertGreater(r['outcome']['progress'], 0)
            self.assertEqual(r['unsupported']['static'], [])
            self.assertEqual(r['unsupported']['runtime'], {})


if __name__ == '__main__':
    unittest.main()
