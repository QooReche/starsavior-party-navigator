"""BFB 52204: 공개 standard·합성 HP로 실제 시전 경로와 빌더 변경 감지를 검사함."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from guild_bfb_test import battle, to_boss, test_compete_and_appeal, G, Ctx
from tools.build_guild_bfb import validate_kill_reset, Changed


class BridalKillTest(unittest.TestCase):
    def test_standard_encounter_reaches_kill_reset(self):
        # 실제 1단계·공개 standard·seed 1. HP/피해/보스 진입을 조작하지 않음.
        # wave_carry 는 옛 값으로 장면 고정(시험 대상은 처치 초기화 경로 — 새 기본값에선 seed 1 장면이 처치 초기화까지 안 감)
        b, _ = battle(level=1, seed=1, mc={'wave_carry': 'keep'})
        b.run()
        self.assertEqual(b.wave_i, 1)
        self.assertGreater(b.progress(), .5)
        self.assertGreater(b.rule_hits['guild_bridal_kill_reset'], 0)
        self.assertGreater(b.gb.boss.actions, 0)

    def test_actual_casts_and_cast_scope(self):
        for mode in ('client', 'off'):
            for marked, lethal, via in ((True, True, None), (True, True, 'enforce'),
                                        (False, True, None), (True, False, None)):
                with self.subTest(mode=mode, marked=marked, lethal=lethal, via=via):
                    b, _ = battle(mc={'guild_bridal_kill_reset': mode})
                    boss = to_boss(b)
                    gb, target = b.gb, b.alive(0)[0]
                    gb.count = 4
                    if marked:
                        gb._put(target, G.B1, {'공격력%': 3}, maxs=10)
                    target.hp = 1 if lethal else target.maxhp
                    b.final_dmg = lambda *args: 10
                    before = target.hp
                    b.cast(boss, boss.d.skills['기본기'], target=target, extra=via is not None, via=via)
                    self.assertLess(target.hp, before)
                    self.assertEqual(target.dead, lethal)
                    hit = mode == 'client' and marked and lethal
                    self.assertEqual(gb.count, 0 if hit else 4)
                    self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], int(hit))
                    if hit:
                        self.assertFalse(target.has(G.B1), '사망 청소 전 기록을 사용해야 함')
                        gb._compete()
                        survivor = next(v for v in b.alive(0) if v.has(G.B1))
                        self.assertEqual(gb.count, 1)
                        b.cast(boss, boss.d.skills['기본기'], target=survivor)
                        self.assertFalse(survivor.dead)
                        self.assertEqual(gb.count, 1)
                        self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], 1)

    def test_same_target_and_before_appeal(self):
        for mode in ('client', 'off'):
            b, _ = battle(mc={'guild_bridal_kill_reset': mode})
            boss = to_boss(b)
            gb = b.gb
            holder, other = b.alive(0)[:2]
            gb._put(holder, G.B1, {})
            gb.count = 4
            other.hp = 1
            b.final_dmg = lambda *args: 10
            sk = copy.copy(gb.cfg['alt']['hyper2'])
            sk.semantic_lines = []
            b.cast(boss, sk)  # 신부는 생존, 다른 광역 대상만 사망
            self.assertFalse(holder.dead)
            self.assertTrue(other.dead)
            self.assertEqual(gb.count, 4)
            self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], 0)
            holder.hp = 1
            gb._put(b.alive(0)[-1], G.B1, {})  # 생존한 다른 신부가 있어 어필 경로도 유효
            gb.count = 5
            b.cast(boss, boss.d.skills['기본기'], target=holder)
            self.assertTrue(holder.dead)
            self.assertEqual(gb.stats['appeal'], 0 if mode == 'client' else 1)
            self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], 1 if mode == 'client' else 0)

    def test_non_attack_death_does_not_reset(self):
        for kind in ('dot', 'chain', 'bskill'):
            b, _ = battle()
            boss = to_boss(b)
            gb, target = b.gb, b.alive(0)[0]
            gb._put(target, G.B1, {})
            gb.count = 4
            b.apply_damage(boss, target, target.hp + 1, kind)
            gb.after_cast(boss, boss.d.skills['기본기'], Ctx(boss, boss, boss.d.skills['기본기']), False)
            self.assertTrue(target.dead)
            self.assertEqual(gb.count, 4)
            self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], 0)

    def test_guard_death_does_not_reset(self):
        b, _ = battle()
        boss = to_boss(b)
        gb = b.gb
        target, guard = b.alive(0)[:2]
        gb._put(guard, G.B1, {})
        gb._put(guard, '시험 수호', {'피해 분담(수호)': 50})
        self.assertGreater(guard.mods()['guard'], 0)
        guard.hp = 1
        gb.count = 4
        b.final_dmg = lambda *args: 10
        b.cast(boss, boss.d.skills['기본기'], target=target)
        self.assertTrue(guard.dead)
        self.assertFalse(target.dead)
        self.assertEqual(gb.count, 4)
        self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], 0)

    def test_bad_mode(self):
        with self.assertRaises(ValueError):
            battle(mc={'guild_bridal_kill_reset': 'wrong'})

    def test_kill_in_shield_phase_keeps_catfight(self):
        b, boss, holder, maids = test_compete_and_appeal()
        self.assertTrue(b.gb.barrier())
        holder.hp = 1
        b.final_dmg = lambda *args: 10
        b.cast(boss, boss.d.skills['기본기'], target=holder)
        self.assertTrue(holder.dead)
        self.assertEqual(b.rule_hits['guild_bridal_kill_reset'], 1)
        self.assertEqual(b.gb.stats['shield_timeout'], 1)
        self.assertFalse(b.gb.anim)
        self.assertFalse(b.gb.barrier())
        self.assertTrue(all(not v.zero_stats for v in maids))

    def test_builder_guard(self):
        se = dict(SkillConditionId=52204, m_BuffTargetType='NSETT_SELF',
                  m_BuffStrID='BI_DELETE_SPECIFIC_BUFF', m_BuffLifeTurn=0, BuffDeleteCount=0,
                  DeleteSpecificBuffStrId='BI_AUTOMATON_MINIGUN_BOSS_7',
                  m_Condition=dict(m_ActiveType='NSEAT_SKILL_END', m_fActiveRate=10000))
        cond = dict(Id=52204, AfterMyAttack=dict(EliminateEnemy=True,
                    TargetBuffStrId=['BI_AUTOMATON_MINIGUN_BOSS_1']))
        validate_kill_reset(se, cond)
        for key, value in [('BuffDeleteCount', 1), ('DeleteSpecificBuffStrId', 'BOSS_1'),
                           ('m_BuffTargetType', 'NSETT_TARGET'), ('SkillConditionId', 4001),
                           ('m_Condition', {'m_ActiveType': 'NSEAT_HIT', 'm_fActiveRate': 10000})]:
            with self.subTest(key=key), self.assertRaises(Changed):
                validate_kill_reset(dict(se, **{key: value}), cond)
        for body in ({'EliminateEnemy': False, 'TargetBuffStrId': ['BI_AUTOMATON_MINIGUN_BOSS_1']},
                     {'EliminateEnemy': True, 'TargetBuffStrId': ['OTHER']},
                     dict(cond['AfterMyAttack'], IsNotEnforceSkill=True)):
            with self.assertRaises(Changed):
                validate_kill_reset(se, dict(Id=52204, AfterMyAttack=body))


if __name__ == '__main__':
    unittest.main()
