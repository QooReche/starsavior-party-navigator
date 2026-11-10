# -*- coding: utf-8 -*-
"""벨그라스 자기 피해·흡혈·쇠락 분류·속도: 단위/실전 경로와 legacy 대조."""
import copy
import math
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from simkit import unit, battle, give
from battlesim.mc import Battle, Ctx
from battlesim.api import _norm_party
from battlesim.starsavior import cosmo_raid as C
from battlesim.starsavior import build as B
from battlesim.starsavior.data import get_db
from battlesim.starsavior.foe import stage_waves
from tools.build_cosmo_raid import hyper_true_damage, Changed
from tools.runtime import static_path_or_none
from tools.tables import rows

PARTY = ['frey', 'emily', 'rosaria', 'fei']
LEGACY = dict(cosmo_hyper_true_target='enemy_all', damage_vampirism='off',
              cosmo_drain_category='debuff', cosmo_speed_floor=False)


def raid(level=8, count=4, mc=None, seed=3, standard=False, spawn=True):
    waves, meta = C.build_waves('belgras', 3, level)
    defs = (_norm_party({'units': PARTY}, get_db(), 'fixed', 'standard')[0] if standard else
            [unit('a%d' % i, hp=10**7, atk=1000, df=1000) for i in range(count)])
    b = Battle(defs, waves, random.Random(seed), mc=dict(cosmo_raid_boss='on', **(mc or {})),
               opts=dict(coop=False, forced_coop=False) if not standard else None,
               leader=1, turn_limit=meta['turn_limit'], battle_mode='boss_kill',
               break_skill={'name': '스타피어서', 'level': 4})
    if spawn:
        b.spawn_wave()
    return b


def rot(b, n):
    b.gb._put(b.gb.boss, C.ROT, {'방어력%': -1}, maxs=50, add=n)


class HyperTest(unittest.TestCase):
    def test_snapshot_once_per_cast_and_no_ally_true_damage(self):
        for count in (1, 4):
            for n in (0, 1, 11, 50):
                for defense in (0, 100000):
                    with self.subTest(count=count, n=n, defense=defense):
                        b = raid(count=count)
                        boss = b.gb.boss
                        boss.d.stats['def'] = defense
                        # 처단자 자동 보호막은 별도 경계 시험에서 검사한다.
                        for m in b.gb.minions.values():
                            b.gb._set_stacks(m, C.STACKS, 0)
                            b.gb.over[m] = 100
                        rot(b, n)
                        hp = boss.hp
                        seen = []
                        original = b.apply_damage
                        def spy(a, v, dmg, kind, shieldable=True):
                            seen.append((a, v, dmg, kind))
                            return original(a, v, dmg, kind, shieldable)
                        with patch.object(b, 'apply_damage', side_effect=spy):
                            b.cast(boss, boss.d.skills['궁극기'])
                            self.assertEqual(boss.hp, hp)
                            self.assertEqual(boss.stack(C.ROT), 0)
                            self.assertEqual(b.gb.pending_damage, [(boss, n * 5000)] if n else [])
                            b.gb.flush_damage()
                            b.gb.flush_damage()
                        true = [x for x in seen if x[3] == 'true']
                        self.assertEqual(true, [(None, boss, n * 5000, 'true')] if n else [])
                        self.assertEqual(hp - boss.hp, n * 5000)
                        self.assertEqual(b.gb.stats['true_damage_hits'], int(n > 0))
                        self.assertTrue(all(x[1] in b.allies for x in seen if x[3] == 'hit'))
                        self.assertTrue(all(a.dmg == 0 for a in b.allies))

    def test_shield_invincible_and_action_order(self):
        for invincible in (False, True):
            b = raid()
            boss = b.gb.boss
            rot(b, 11)
            if invincible:
                give(boss, '무적')
            hp = boss.hp
            b.choose_skill = lambda u: (boss.d.skills['궁극기'], None)
            original = b.fire
            checked = []
            def check(u, event, ctx):
                if u is boss and event == 'own_te':
                    self.assertEqual(b.gb.pending_damage, [])
                    self.assertEqual(b.gb.stats['true_damage_hits'], 1)
                    checked.append(True)
                return original(u, event, ctx)
            # 반응 큐에서 생긴 보호막도 예약 피해보다 먼저 적용되어야 한다.
            def reactions():
                self.assertEqual(b.gb.pending_damage, [(boss, 55000)])
                give(boss, '시험 보호막').shield = 20000
            with patch.object(b, 'fire', side_effect=check), patch.object(b, '_run_reactions', side_effect=reactions):
                b.act(boss)
            self.assertTrue(checked)
            # 궁극기 종료 때 처단자 보호막(보스 HP의 1%)도 먼저 붙는다.
            absorbed = 0 if invincible else min(55000, 20000 + math.floor(boss.maxhp * .01))
            self.assertEqual(b.gb.stats['self_damage_shield'], absorbed)
            self.assertEqual(hp - boss.hp, 0 if invincible else 55000 - absorbed)

    def test_snapshot_precedes_hits_and_death_clears_pending(self):
        b = raid()
        boss = b.gb.boss
        rot(b, 11)
        original = b.gb.post_hit
        def change_stacks(a, v):
            b.gb._set_stacks(boss, C.ROT, 50)
            return original(a, v)
        with patch.object(b.gb, 'post_hit', side_effect=change_stacks):
            b.cast(boss, boss.d.skills['궁극기'])
        self.assertEqual(b.gb.pending_damage, [(boss, 55000)])
        b.kill(boss, None)
        b.gb.flush_damage()
        self.assertEqual(b.gb.pending_damage, [])
        self.assertEqual(b.gb.stats['self_damage_hp'], 0)

    def test_legacy_enemy_all(self):
        b = raid(mc={'cosmo_hyper_true_target': 'enemy_all'})
        rot(b, 11)
        b.cast(b.gb.boss, b.gb.boss.d.skills['궁극기'])
        self.assertEqual(b.gb.stats['true_damage_hits'], 4)
        self.assertEqual(b.gb.pending_damage, [])
        self.assertTrue(all(a.taken >= 55000 for a in b.allies))


class DrainSpeedTest(unittest.TestCase):
    def test_drain_limits_category_and_owner(self):
        b = raid()
        a, other = b.allies[:2]
        a.maxhp0 = a.hp = 20000
        b.dirty(a)
        sk = C._skill('기본기', '시험', 1, 0, 0, tg='적 단일')
        for n in range(1, 12):
            b.cast(a, sk, target=b.gb.boss)
            expected = math.floor(20000 * (1 - .05 * min(n, 10)))
            self.assertEqual(a.maxhp, expected)
            self.assertEqual(a.hp, a.maxhp)
            self.assertEqual(a.n_harmful(), 0)
            self.assertEqual(other.stack(C.CH_DRAIN), 0)
        e = a.eff[C.CH_DRAIN]
        self.assertTrue(e.fixed)
        self.assertEqual(e.dur, math.inf)
        a.hp = 1234
        b.cast(a, sk, target=b.gb.boss)
        self.assertEqual(a.hp, 1234)
        b._finish_action(a)
        self.assertEqual(a.stack(C.CH_DRAIN), 10)
        give(a, '공격력 감소', {'공격력%': -30}, harmful=True)
        self.assertEqual(a.n_harmful(), 1)

    def test_speed_levels_and_initial_cooldowns(self):
        for level in (8, 9):
            b = raid(level)
            boss = b.gb.boss
            self.assertEqual(boss.cd['특수기'], 0)
            self.assertEqual(boss.cd['궁극기'], 4)
            self.assertEqual(boss.gauge, 5000)
            self.assertEqual(boss.has(C.CH_SPEED), level == 9)
            for n in (0, 1, 34, 35):
                b.gb._drop(boss, C.ERO)
                b.gb._put(boss, C.ERO, {'속도%': 1}, maxs=35, add=n)
                self.assertEqual(boss.spd(), math.floor(180 * (1 + n / 100 + (.3 if level == 9 else 0)) + 1e-9))
            b.mc['cosmo_speed_floor'] = False
            b.gb._set_stacks(boss, C.ERO, 34)
            self.assertAlmostEqual(boss.spd(), 180 * (1.34 + (.3 if level == 9 else 0)))

    def test_thorn_gauge_only_single_attack(self):
        for thorn, all_, attack in ((False, False, True), (True, True, True), (True, False, False), (True, False, True)):
            b = raid()
            a, boss = b.allies[0], b.gb.boss
            if thorn:
                give(a, C.THORN)
            sk = C._skill('특수기', '시험', 1, 0, 0, all_=all_, attack=attack,
                          tg='적 전체' if all_ else '적 단일' if attack else '자신')
            b.cast(a, sk, target=boss if attack else None)
            self.assertEqual(boss.gauge - 5000, 2000 if thorn and attack and not all_ else 0)


class VampirismTest(unittest.TestCase):
    def setup_hit(self, count=1, mc=None):
        b = battle([unit(hp=20000)], [unit('v%d' % i, hp=1000000) for i in range(count)],
                   mc=mc, opts=dict(coop=False, forced_coop=False))
        a = b.allies[0]
        a.hp = 1000
        give(a, '흡혈', {'피해 흡혈': 15, '받는 회복량': 20, '주는 회복량': 300})
        return b, a, b.foes[0]

    def test_last_hit_sum_receive_floor_cap_and_sources(self):
        b, a, v = self.setup_hit()
        ctx = Ctx(a, a, a.d.skills['기본기'])
        b._vampirism_hit(a, v, ctx, 4000, last=False)
        self.assertEqual(a.hp, 1000)
        b._vampirism_hit(a, v, ctx, 6000)
        self.assertEqual(a.hp, 2800)
        self.assertEqual(b.rule_hits['damage_vampirism'], 1)
        self.assertEqual(ctx.vamp_damage, {})
        b._vampirism_hit(a, v, ctx, 11)
        self.assertEqual(a.hp, 2801)  # 1.98 버림
        a.hp = a.maxhp - 1
        b._vampirism_hit(a, v, ctx, 10000)
        self.assertEqual(a.hp, a.maxhp)
        self.assertEqual(b.rule_hits['damage_vampirism_heal'], 1802)
        a.eff.clear()
        a.d.stats['vampirism'] = 500
        a.d.passive['vampirism'] = .03
        give(a, '표 스탯', {'NST_RATE_DAMAGE_VAMPIRISM': 700})
        self.assertAlmostEqual(a.mods()['vampirism'], .15)

    def test_real_skill_targets_shield_overkill_and_exclusions(self):
        b, a, v = self.setup_hit(count=2)
        sk = C._skill('궁극기', '시험 전체 공격', 1, 0, 0, all_=True)
        give(v, '보호막').shield = 10000
        b.foes[1].hp = 1
        with patch.object(b, 'final_dmg', return_value=10000):
            b.cast(a, sk)
        self.assertEqual(a.hp, 4600)  # 보호막 10000 + HP 1인 대상의 동기화 피해 10000
        self.assertEqual(b.rule_hits['damage_vampirism'], 2)
        before = a.hp
        for kind in ('dot', 'chain', 'true', 'bskill'):
            b.apply_damage(a, v, 10000, kind)
        self.assertEqual(a.hp, before)

    def test_guard_is_not_an_extra_vampirism_target(self):
        b, a, v = self.setup_hit(count=2)
        give(b.foes[1], '수호', {'피해 분담(수호)': 50})
        ctx = Ctx(a, a, a.d.skills['기본기'])
        with patch.object(b, 'final_dmg', side_effect=lambda a, v, base, *args: base):
            b.strike(a, v, 10000, ctx, False, 0, 0, [])
        self.assertEqual(a.hp, 1900)
        self.assertEqual(b.rule_hits['damage_vampirism'], 1)

    def test_invincible_and_nullifier_keep_sync_value(self):
        for effect in ('무적', '스킬 피해 무효'):
            b, a, v = self.setup_hit(count=2)
            give(v, effect)
            give(b.foes[1], '수호', {'피해 분담(수호)': 50})
            hp = v.hp
            ctx = Ctx(a, a, a.d.skills['기본기'])
            with patch.object(b, 'final_dmg', side_effect=lambda a, v, base, *args: base):
                b.strike(a, v, 10000, ctx, False, 0, 0, [])
            self.assertEqual(v.hp, hp)
            self.assertEqual(a.hp, 2800)
            self.assertEqual(b.rule_hits['damage_vampirism'], 1)

    def test_no_heal_when_last_sync_damage_is_zero(self):
        b, a, v = self.setup_hit()
        ctx = Ctx(a, a, a.d.skills['기본기'])
        b._vampirism_hit(a, v, ctx, 10000, last=False)
        b._vampirism_hit(a, v, ctx, 0)
        self.assertEqual(a.hp, 1000)
        self.assertEqual(ctx.vamp_damage, {})

    def test_off_and_no_supplier(self):
        b, a, v = self.setup_hit(mc={'damage_vampirism': 'off'})
        with patch.object(b, 'final_dmg', return_value=10000):
            b.cast(a, a.d.skills['기본기'], target=v)
        self.assertEqual(a.hp, 1000)
        b.mc['damage_vampirism'] = 'client'
        a.eff.clear()
        b.dirty(a)
        b.cast(a, a.d.skills['기본기'], target=v)
        self.assertEqual(a.hp, 1000)

    def test_explicit_xx2_build_and_corridors(self):
        db = get_db()
        original = B.guide_entry
        def xx2(db, key, u):
            entry, source = original(db, key, u)
            return (dict(entry, potential='XX2') if key == 'fei' else entry), source
        plain = _norm_party(PARTY, db, 'fixed', 'standard')[0]
        self.assertEqual(plain[-1].stats.get('vampirism', 0), 0)
        # 공개 XX2 잠재력을 명시적으로 선택. 페이 이름으로 수치를 부여하지 않는다.
        with patch.object(B, 'guide_entry', side_effect=xx2):
            from battlesim.api import _norm_party_raw
            defs = _norm_party_raw(PARTY, db, 'fixed', 'standard')[0]
        self.assertEqual(defs[-1].build['potential'], 'XX2')
        self.assertEqual(defs[-1].stats['vampirism'], 1500)
        for tab, floor in (('달 회랑', 'FLOOR 100'), ('태양 회랑', 'FLOOR 200'), ('태양 회랑', 'FLOOR 250')):
            _, waves = stage_waves('clo', tab, floor)
            b = Battle(defs, waves, random.Random(4), leader=1).run()
            self.assertGreater(b.progress(), 0)
            self.assertGreater(b.rule_hits['damage_vampirism'], 0)
            if tab == '태양 회랑':  # 달 100은 페이가 피해를 받지 않을 수도 있음.
                self.assertGreater(b.rule_hits['damage_vampirism_heal'], 0)


class IntegrationTest(unittest.TestCase):
    def test_level8_paths_reached(self):
        b = raid(standard=True, spawn=False).run()
        self.assertGreater(b.progress(), 0)
        for k in ('hyper', 'self_damage_queued', 'true_damage_hits', 'self_damage_hp', 'drain', 'thorn_gauge', 'rot_gain'):
            self.assertGreater(b.gb.stats[k], 0, k)
        self.assertEqual(b.gb.pending_damage, [])

    def test_private_hyper_contract(self):
        static = static_path_or_none()
        if static is None:
            self.skipTest('STARSAVIOR_STATIC 없음')
        table = static / 'tables'
        effects = [x for x in rows(table / 'SE_TEMPLET_SKILL_2.json')
                   if x.get('m_SEStrID', '').startswith('COND_MON_CORRUPTED_TREE_BOSS_COSMO_01_HYPER_')]
        conditions = {x['Id']: x for x in rows(table / 'Plain/SKILL_CONDITION_TEMPLET.json')}
        self.assertEqual(hyper_true_damage(effects, conditions), C.load()['belgras']['hyperTrueDamage'])
        for field, value in [('m_BuffTargetType', 'NSETT_ENEMY_ALL'), ('AddTrueDamageValue', 1),
                             ('m_Condition', {'m_ActiveType': 'NSEAT_SKILL_END', 'm_fActiveRate': 10000})]:
            wrong = copy.deepcopy(effects)
            wrong[0][field] = value
            with self.assertRaises(Changed):
                hyper_true_damage(wrong, conditions)
        wrong = copy.deepcopy(conditions)
        wrong[effects[0]['SkillConditionId']]['OnMyAttack']['SelfBuffLevelCount'] = 2
        with self.assertRaises(Changed):
            hyper_true_damage(effects, wrong)


if __name__ == '__main__':
    unittest.main()
