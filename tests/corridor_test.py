"""Corridor regressions: permanent accuracy, boss-kill mode, hit accounting."""
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from p3_test import battle, give, unit
from battlesim.api import _norm_encounter
from battlesim.mc import Battle
from battlesim.metrics import unit_def
from battlesim.rules import MC_RULES
from battlesim.starsavior.foe import stage_waves, sudden_death, battle_end
from battlesim.starsavior.parser import Line


def tuner():
    return next(d for d in stage_waves('clo', '달 회랑', 'FLOOR 355')[1][-1] if d.boss)


class CorridorTest(unittest.TestCase):
    def test_tuner_accuracy_blocks_fei_evade_trigger(self):
        for mode, count in [('data', 0), ('legacy', 1)]:
            with self.subTest(mode=mode):
                b = battle([unit_def('fei')], [tuner()], mc={'permanent_accuracy': mode})
                fei, boss = b.allies[0], b.foes[0]
                fei.hp = fei.maxhp = boss.hp = boss.maxhp = 10 ** 9
                give(fei, '회피율 증가', {'회피율': 50})
                with patch.object(b.rng, 'random', return_value=.25):
                    ctx = b.cast(boss, boss.d.skills['기본기'], target=fei)
                self.assertEqual(fei in ctx.evaded, mode == 'legacy')
                self.assertEqual(fei.cast_count['특수기(추가)'], count)

    def test_accuracy_is_additive_and_not_blocked_or_double_counted(self):
        d = unit('accuracy')
        d.lines = [Line('[상시] 능력치: 공격력% +15%, 명중률 +100%', '패시브', 'passive')]
        for _ in range(2):
            b = battle([unit()], [d])
            boss = b.foes[0]
            give(boss, '강화 불가', harmful=True)
            give(boss, '명중 약화', {'명중률': -25}, harmful=True)
            self.assertEqual(boss.mods()['acc'], .75)
            b.dirty(boss)
            self.assertEqual(boss.mods()['acc'], .75)
        self.assertEqual(d.passive.get('acc', 0), 0)

    def test_accuracy_is_not_force_hit(self):
        b = battle([unit(hp=10 ** 9)], [tuner()])
        a, boss = b.allies[0], b.foes[0]
        give(a, '회피 시험', {'회피율': 150})
        with patch.object(b.rng, 'random', return_value=.25):
            ctx = b.cast(boss, boss.d.skills['기본기'], target=a)
        self.assertIn(a, ctx.evaded)
        give(boss, '필중')
        with patch.object(b.rng, 'random', return_value=.25):
            ctx = b.cast(boss, boss.d.skills['기본기'], target=a)
        self.assertNotIn(a, ctx.evaded)

    def test_boss_death_removes_minions_without_damage_and_fires_death(self):
        for mode, dead in [('data', True), ('legacy', False)]:
            b = battle([unit()], [unit('boss'), unit('minion')],
                       mc={'battle_end_mode': mode}, battle_mode='boss_kill')
            boss, minion = b.foes
            boss.d.boss = True
            with patch.object(b, 'fire', wraps=b.fire) as fire:
                b.apply_damage(b.allies[0], boss, 10 ** 6, 'skill')
            self.assertEqual(minion.dead, dead)
            self.assertEqual(minion.taken, 0)
            self.assertEqual(b.allies[0].dmg, boss.taken)
            self.assertEqual(any(c.args[0] is minion and c.args[1] == 'death_self'
                                 for c in fire.call_args_list), dead)

    def test_all_kill_and_nonboss_death_do_not_cascade(self):
        for mode in ('all_kill', 'boss_kill'):
            b = battle([unit()], [unit('boss'), unit('minion')], battle_mode=mode)
            boss, minion = b.foes
            boss.d.boss = True
            b.kill(minion, b.allies[0])
            self.assertFalse(boss.dead)
        b = battle([unit()], [unit('boss'), unit('minion')], battle_mode='all_kill')
        b.foes[0].d.boss = True
        b.kill(b.foes[0], b.allies[0])
        self.assertFalse(b.foes[1].dead)

    def test_boss_kill_advances_wave_then_clears(self):
        boss = unit('boss', hp=1)
        boss.boss = True
        b = Battle([unit(atk=10 ** 5)], [[boss, unit(hp=10 ** 9)], [boss, unit(hp=10 ** 9)]],
                   random.Random(7), battle_mode='boss_kill')
        b.pick_attack_target = lambda a, sk=None: b.foes[0] if a.side == 0 else b.allies[0]
        b.run()
        self.assertEqual(b.result, 'clear')
        self.assertEqual(b.wave_i, 1)
        self.assertEqual(b.allies[0].dmg, 2)
        self.assertEqual(sum(u.actions for u in b.allies), 2)

    def test_coop_and_reaction_hits_count_once_each_for_extra(self):
        b = battle([unit(hp=10 ** 9, atk=1)], [tuner()])
        a, boss = b.allies[0], b.foes[0]
        boss.hp = boss.maxhp = 10 ** 9
        for n in range(1, 23):
            b.cast(a, a.d.skills['기본기'], target=boss, extra=True,
                   via='coop' if n % 2 else 'reaction')
            self.assertEqual(boss.cast_count['특수기(추가)'], n // 11)
            self.assertEqual(boss.stack('절망의 선율'), n % 11)

    def test_stage_mode_and_sudden_boundary(self):
        waves, limit, _, _, meta = _norm_encounter({'stage': 'clo/달 회랑/FLOOR 355'})
        self.assertEqual(meta['battle_mode'], 'boss_kill')
        self.assertFalse(limit)  # 119 is a sudden-death boundary, not a turn limit.
        self.assertIn('clo|달 회랑|FLOOR 355', battle_end())
        sd = sudden_death()
        self.assertEqual(sum(k.startswith('clo|') for k in sd['stages']), 2100)   # 10/29 패치: 1900 -> 2100(새 층 200개도 서든데스 연결)
        b = Battle([unit()], waves, random.Random(7), sudden=sd['groups'][meta['sudden_death']])
        for turn, hp in [(36, 0), (42, 0), (119, 0), (120, -.1)]:
            b.global_turns = turn
            b._sudden_step()
            self.assertAlmostEqual(b.allies[0].sd_hp, hp)

    def test_metadata_and_package_input(self):
        from tools.build_simpack import files
        self.assertIn('data/battle_end.json', files())
        for key in ('permanent_accuracy', 'battle_end_mode'):
            self.assertEqual(MC_RULES[key]['legacy'], 'legacy')
            for field in ('grade', 'source', 'note'):
                self.assertTrue(MC_RULES[key][field])


if __name__ == '__main__':
    unittest.main()
