"""26752678 벨그라스 일반 스테이지: 예약 피해와 시전별 침식 표지."""
import copy
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from simkit import unit, battle, give
from battlesim import api
from battlesim.mc import Battle, support_report
from battlesim.starsavior.foe import stage_waves
from battlesim.starsavior.parser import Skill
from battlesim.starsavior import belgras_se as S
from tools.runtime import static_path_or_none
from tools.tables import rows


def definition(step=3):
    return copy.deepcopy(next(d for w in stage_waves('cosmo', '벨그라스', f'벨그라스 {step}단계')[1]
                              for d in w if d.name == '벨그라스'))


def setup(count=1, mc=None):
    b = battle([unit(f'a{i}', hp=10**8, atk=1, df=10000) for i in range(count)],
               [definition()], mc=mc, opts=dict(coop=False, forced_coop=False))
    return b, b.foes[0]


def rot(boss, n):
    e = give(boss, S.ROT, stacks=n)
    e.maxs = 50


class StageSE(unittest.TestCase):
    def test_all_fifty_rows_and_scope_and_cache(self):
        for step in (1, 2, 3):
            d = definition(step)
            out = S.normalize(d, d.lines)
            fixed = [ln for ln in out if ln.eff['kind'] == 'belgras_fixed']
            self.assertEqual(len(fixed), 50)
            self.assertEqual(sorted(ln.eff['value'] for ln in fixed), list(range(5000, 250001, 5000)))
            self.assertEqual(support_report([d]), [])
            d.name = '다른 적'
            self.assertEqual(sum(ln.eff['kind'] == 'belgras_fixed' for ln in S.normalize(d, d.lines)), 50)
            d.boss_behaviors = {}
            self.assertIs(S.normalize(d, d.lines), d.lines)
        b, boss = setup()
        def count():
            return sum(ln.eff['kind'] == 'belgras_fixed' for ln in b.lines_of(boss))
        self.assertEqual(count(), 50)

    def test_exactly_one_queued_self_hit_and_cast_snapshot(self):
        for count in (1, 4):
            for n in (0, 1, 17, 49, 50):
                with self.subTest(count=count, n=n):
                    b, boss = setup(count)
                    rot(boss, n)
                    hp = boss.hp
                    b.cast(boss, boss.d.skills['궁극기'])
                    self.assertEqual(boss.hp, hp)
                    self.assertEqual(boss.stack(S.ROT), 0)
                    self.assertEqual(b._belgras_damage, [(boss, n * 5000)] if n else [])
                    rot(boss, 50)
                    with patch.object(b, 'fixed_true_damage', wraps=b.fixed_true_damage) as damage:
                        b.flush_add_damage()
                        b.flush_add_damage()
                    self.assertEqual(damage.call_count, int(n > 0))
                    if n:
                        self.assertIs(damage.call_args.args[1], boss)
                        self.assertEqual(damage.call_args.args[2], n * 5000)
                    self.assertEqual(hp - boss.hp, n * 5000)
                    self.assertTrue(all(a.dmg == 0 for a in b.allies))

    def test_reactions_before_damage_before_turn_end(self):
        b, boss = setup()
        rot(boss, 11)
        hp = boss.hp
        b.choose_skill = lambda u: (boss.d.skills['궁극기'], None)
        def reactions():
            self.assertEqual(boss.hp, hp)
            self.assertEqual(b._belgras_damage, [(boss, 55000)])
            give(boss, '시험 보호막').shield = 20000
        original = b.fire
        reached = []
        def fire(u, event, ctx):
            if u is boss and event == 'own_te':
                reached.append(True)
                self.assertEqual(b._belgras_damage, [])
                self.assertEqual(hp - boss.hp, 35000)
            return original(u, event, ctx)
        with patch.object(b, '_run_reactions', side_effect=reactions), patch.object(b, 'fire', side_effect=fire):
            b.act(boss)
        self.assertTrue(reached)

    def test_multiple_casts_keep_separate_snapshots(self):
        b, boss = setup()
        hp = boss.hp
        for n in (2, 7):
            rot(boss, n)
            b.cast(boss, boss.d.skills['궁극기'], extra=True)
        self.assertEqual(b._belgras_damage, [(boss, 10000), (boss, 35000)])
        b.flush_add_damage()
        self.assertEqual(hp - boss.hp, 45000)
        self.assertEqual(b.rule_hits['belgras_fixed_applied'], 2)

    def test_invincible_nullifier_and_dead_target(self):
        for protection in ('무적', '스킬 피해 무효', '사망'):
            with self.subTest(protection=protection):
                b, boss = setup()
                rot(boss, 50)
                b.cast(boss, boss.d.skills['궁극기'])
                if protection == '사망':
                    b.kill(boss, None)
                else:
                    give(boss, protection)
                hp = boss.hp
                b.flush_add_damage()
                self.assertEqual(hp - boss.hp, 250000 if protection == '스킬 피해 무효' else 0)
                self.assertEqual(b._belgras_damage, [])
                if protection == '스킬 피해 무효':
                    # DAMAGE_ADD is not DAMAGE_SKILL; the nullifier is not consumed.
                    self.assertTrue(boss.on(protection))

    def test_erosion_boundary_marker_for_attack_and_nonattack(self):
        for attack, all_, count, gain in ((True, False, 1, 1), (True, True, 17, 5), (False, False, 5, 5)):
            with self.subTest(attack=attack, all_=all_):
                b, boss = setup()
                a = b.allies[0]
                sk = Skill(dict(sl='기본기', n='시험', ty='액티브', act='공격' if attack else '비공격',
                                tg='적 전체' if all_ else '적 단일' if attack else '자신',
                                all=all_, cf=[1, 0, 0, 0], dm='공격력×1%'))
                give(boss, S.ERO, stacks=count)
                seen = []
                original = b.fire_foes
                def fire(actor, ctx, kind):
                    result = original(actor, ctx, kind)
                    if kind == 'foe_pre_any':
                        seen.append(boss.on(S.CHECK))
                        self.assertTrue(boss.on(S.CHECK))
                        self.assertEqual(boss.eff[S.CHECK].category, 'marker')
                    return result
                with patch.object(b, 'fire_foes', side_effect=fire):
                    b.cast(a, sk, target=boss if attack else a)
                self.assertEqual(seen, [True])
                self.assertEqual(boss.stack(S.ERO), 0)
                self.assertEqual(boss.stack(S.ROT), 0)
                self.assertFalse(boss.has(S.CHECK))
                b.cast(a, sk, target=boss if attack else a)
                self.assertEqual(boss.stack(S.ROT), gain)

    def test_marker_clears_before_coop_and_nested_casts_do_not_inherit(self):
        b, boss = setup(2)
        b.opts['coop'] = True
        a = b.allies[0]
        give(boss, S.ERO, stacks=1)
        reached = []
        def coop(actor, ctx):
            reached.append(True)
            self.assertFalse(boss.has(S.CHECK))
            b.cast(b.allies[1], b.allies[1].d.skills['기본기'], extra=True, target=boss)
        with patch.object(b, 'coop', side_effect=coop):
            b.cast(a, a.d.skills['기본기'], target=boss)
        self.assertTrue(reached)
        self.assertEqual(boss.stack(S.ROT), 1)
        self.assertFalse(boss.has(S.CHECK))

    def test_real_stage_reaches_both_paths(self):
        defs, _ = api._norm_party(['frey', 'emily', 'rosaria', 'fei'], api.get_db(), 'fixed', 'standard')
        _, waves = stage_waves('cosmo', '벨그라스', '벨그라스 3단계')
        b = Battle(defs, waves, random.Random(21), timeline=True).run()
        self.assertGreater(b.progress(), 0)
        self.assertGreater(b.rule_hits['belgras_fixed_queued'], 0)
        self.assertGreater(b.rule_hits['belgras_fixed_applied'], 0)
        self.assertGreater(b.rule_hits['belgras_action_marker'], 0)
        self.assertEqual(b._belgras_damage, [])

    def test_private_table_contract(self):
        static = static_path_or_none()
        if static is None:
            self.skipTest('STARSAVIOR_STATIC 없음')
        table = static / 'tables'
        effects = {x['m_SEID']: x for x in rows(table / 'SE_TEMPLET_SKILL_2.json')}
        conditions = {x['Id']: x for x in rows(table / 'Plain/SKILL_CONDITION_TEMPLET.json')}
        for n in range(1, 51):
            se = effects[930082300+n]
            self.assertEqual((se['m_BuffTargetType'], se['m_BuffStrID'], se['AddTrueDamageValue']),
                             ('NSETT_SELF', 'BI_ADD_TRUE_DAMAGE', n*5000))
            self.assertEqual(se['m_Condition']['m_ActiveType'], 'NSEAT_SKILL_START')
            self.assertEqual(conditions[se['SkillConditionId']]['OnMyAttack'],
                             dict(SkillIndex='NSI_SKILL_3_HYPER', SelfBuffStrId=['BI_CORRUPTED_TREE_BOSS_3'], SelfBuffLevelCount=n))
        marker = effects[930082510]
        self.assertEqual(marker['m_BuffLifeTurn'], 0)
        self.assertEqual(marker['m_BuffStrID'], 'BI_CORRUPTED_TREE_BOSS_6')
        self.assertEqual(conditions[marker['SkillConditionId']]['OnEnemyAction'],
                         dict(SelfBuffStrId=['BI_CORRUPTED_TREE_BOSS_2']))
        buff = next(x for x in rows(table / 'BUFF_TEMPLET.json') if x['m_BuffStrID'] == marker['m_BuffStrID'])
        self.assertEqual((buff['IsBuff'], buff['IsPositive'], buff['ForceApplyEffect']), (False, True, True))
        self.assertEqual(sum(effects[x]['RepeatBuffCount'] for x in range(930082503, 930082507)), 17)


if __name__ == '__main__':
    unittest.main()
