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
from simkit import unit, battle, give
from battlesim.gauge import turn_key
from battlesim.mc import Battle, Ctx, line_kind, support_report
from battlesim.starsavior.foe import stage_waves
from battlesim.starsavior.parser import Line
from battlesim.starsavior import foe_client


def guild(tab, allies=1):
    _, waves = stage_waves('guild', tab, '길드 방어전 6단계')
    defs = copy.deepcopy(waves[-1])
    b = Battle([unit('dummy%d' % i, hp=10**9, atk=10) for i in range(allies)], [defs], random.Random(3),
               opts={'coop': False, 'nova': False}, timeline=True)
    b.spawn_wave()
    return b


class FoeClientTest(unittest.TestCase):
    def test_target_barrier(self):
        _, waves = stage_waves('cosmo', '벨그라스', '벨그라스 1단계')
        d = next(d for w in waves for d in w if d.name == '처단자')
        b = battle([unit('small', hp=10003), unit('large', hp=40007)],
                   [copy.deepcopy(d), unit('boss', boss=True, hp=100001), unit('minion', hp=5000)])
        owner, boss, minion = b.foes
        owner.eff.pop('응집된 생기(해제불가)', None)
        lines = [ln for ln in d.lines if '보호막 = 대상' in ln.raw]
        self.assertEqual(len(lines), 3)
        # No marker: both the enemy non-attack and single hit branches shield enemies.
        for event in ('foe_post_na', 'hit_self'):
            ln = next(l for l in lines if line_kind(l) == event)
            ctx = Ctx(owner, b.allies[0], b.allies[0].d.skills['기본기'])
            ctx.target, ctx.targets = owner, [owner]
            for a in b.allies:
                a.eff.clear()
            b.run_line(owner, ln, ctx)
            self.assertEqual([a.shield_total() for a in b.allies], [2500, 10001])
        give(owner, '응집된 생기(해제불가)')
        ln = next(l for l in lines if line_kind(l) == 'ally_post')
        ctx = Ctx(owner, boss, boss.d.skills['기본기'])
        b.run_line(owner, ln, ctx)
        self.assertEqual(boss.shield_total(), 1000)
        self.assertEqual(minion.shield_total(), 0)
        self.assertEqual(owner.shield_total(), 0)
        self.assertGreater(b.rule_hits['foe_target_barrier'], 0)

    def test_cohesion_target_local(self):
        _, waves = stage_waves('oph', '고대 지하 유적', 'SECTOR 39-10')
        d = next(d for w in waves for d in w if d.name == '공허결집자')
        b = battle([unit('spore'), unit('clean')], [copy.deepcopy(d)])
        boss = b.foes[0]
        ln = next(l for l in boss.d.lines if '능력치 보정 피해 증가' in l.raw and '연쇄 피해' in l.raw)
        give(b.allies[0], '공허 포자', harmful=True)
        ctx = Ctx(boss, boss, boss.d.skills['궁극기'])
        ctx.target, ctx.targets = b.allies[0], list(b.allies)
        b.run_line(boss, ln, ctx)
        self.assertEqual(ctx.local_by[b.allies[0]]['inc'], .3)
        self.assertEqual(ctx.local_by[b.allies[1]]['inc'], 0)
        self.assertEqual([a.hp for a in b.allies], [a.maxhp for a in b.allies])

    def test_projection_detainment(self):
        _, waves = stage_waves('oph', '버려진 요새', 'SECTOR 40-10')
        d = next(d for w in waves for d in w if d.name == '공허투영자')
        b = battle([unit('a')], [copy.deepcopy(d)])
        a = b.allies[0]
        self.assertTrue(a.has('억류(해제불가)'))
        a.gauge = 1000
        b.run_line(a, Line('[스킬 사용 후] 자신에게 행동 게이지 30%p 증가', '기본기', 'active'), Ctx(a, a, None))
        self.assertEqual(a.gauge, 1000)
        self.assertGreater(a.spd(), 0)
        self.assertFalse(any('억류' in r['raw'] for r in support_report([d])))

    def test_tien_upgrades_and_resets(self):
        b = guild('티엔')
        tien, shien = [next(u for u in b.foes if u.d.name == n) for n in ('티엔', '시엔')]
        for slot, expected in [('기본기', '백팔철선진·멸!'), ('특수기', '백팔철선진·극!')]:
            with patch.object(b, 'choose_skill', return_value=(tien.d.skills[slot], b.allies[0])):
                b.act(tien)
            self.assertIn('궁극기', tien.skill_overrides)
            self.assertEqual(tien.skill_overrides['궁극기'].name, expected)
        b.act(shien)
        self.assertTrue(any(e.get('skill_name') == '백팔철선진·극!' and e.get('via') == 'reaction' for e in b.timeline))
        # Same slot, proper variant effects: extreme strips buffs and applies ban.
        self.assertTrue(b.allies[0].has('강화 불가'))
        del tien.eff['결속(해제불가)']
        b.act(b.allies[0])
        self.assertEqual(tien.skill_overrides['궁극기'].name, '백팔철선진!')
        fresh = guild('티엔')
        self.assertFalse(fresh.foes[0].skill_overrides)

    def test_bfb_reaction_and_changes(self):
        b = guild('BFB')
        boss = next(u for u in b.foes if u.d.name == 'BFB')
        a = b.allies[0]
        give(a, '신부 경쟁(해제불가)', stacks=1)
        give(boss, '신부 경쟁 카운팅용 버프', stacks=5)
        give(boss, '공격력 감소', harmful=True)
        boss.cd['궁극기'] = 10
        with patch.object(b, 'choose_skill', return_value=(boss.d.skills['기본기'], a)):
            b.act(boss)
        self.assertTrue(any(e.get('skill_name') == '정실 어필' for e in b.timeline))
        self.assertIn('특수기', boss.skill_overrides)
        self.assertEqual(boss.skill_overrides['특수기'].name, '독점 선언')
        self.assertEqual(boss.cd['특수기'], 0)  # replacement's RESET_COOL_TURN
        self.assertFalse(boss.has('공격력 감소'))
        self.assertGreater(boss.shield_total(), 0)
        self.assertEqual(b.choose_skill(boss)[0].name, '독점 선언')
        give(boss, '정실 어필', stacks=4).maxs = 5
        with patch.object(b, 'choose_skill', return_value=(boss.skill_overrides['특수기'], a)):
            b.act(boss)
        self.assertTrue(any(e.get('skill_name') == '축복의 대피로연' for e in b.timeline))
        self.assertEqual(boss.skill_overrides['특수기'].name, '정실 어필')
        self.assertEqual(boss.skill_overrides['궁극기'].name, '황홀한 허니문')
        self.assertFalse(boss.has('정실 어필'))

    def test_bfb_retargets_after_kill(self):
        b = guild('BFB', allies=2)
        boss = next(u for u in b.foes if u.d.name == 'BFB')
        victim, survivor = b.allies
        victim.hp = 1
        give(survivor, '신부 경쟁(해제불가)')
        give(boss, '신부 경쟁 카운팅용 버프', stacks=5)
        boss.cd['궁극기'] = 10
        with patch.object(b, 'choose_skill', return_value=(boss.d.skills['기본기'], victim)):
            b.act(boss)
        self.assertTrue(victim.dead)
        reactions = [e for e in b.timeline if e.get('skill_name') == '정실 어필']
        self.assertEqual(len(reactions), 1)
        self.assertEqual(reactions[0]['targets'], ['dummy1'])
        self.assertGreater(boss.shield_total(), 0)

    def test_blocked_reaction_does_not_roll_target(self):
        b = guild('BFB', allies=2)
        boss = next(u for u in b.foes if u.d.name == 'BFB')
        give(b.allies[1], '신부 경쟁(해제불가)')
        boss.cd['특수기'] = 1
        before = b.R(boss.side).getstate()
        self.assertIsNone(b.trigger_cast(boss, boss.d.trigger_skills['특수기']))
        self.assertEqual(b.R(boss.side).getstate(), before)

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
        for raw in ('자신에게 행동 게이지를 0%로 설정', '자신에게 100% 확률로 행동 게이지 50%p 감소'):
            b.run_special(shark, None, Ctx(shark, shark, None), raw)
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
            with patch.object(b, 'choose_skill', return_value=(tien.d.skills[slot], b.allies[0])):
                b.act(tien)
            self.assertEqual(shien.gauge, gain)
            self.assertTrue(any(e.get('skill_name') == name and e.get('via') == 'reaction' for e in b.timeline))
            # A real normal action remains possible despite speed zero.
            b.set_gauge(shien, 10000)
            self.assertEqual(b.pick_next([shien]), (shien, 0))
            b.act(shien)
            self.assertEqual(shien.actions, 1)


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
    original_exec = Battle._exec_line

    def no_changes(b, owner, ln, ctx):
        if ln.eff['kind'] != 'foe_change_skill':
            return original_exec(b, owner, ln, ctx)

    with patch.object(Battle, '_exec_line', no_changes):
        suite = unittest.TestSuite(FoeClientTest(n) for n in ('test_tien_upgrades_and_resets', 'test_bfb_reaction_and_changes'))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        assert len(result.failures) == 2 and not result.errors, (result.failures, result.errors)
    print('mutations: 2 skill-change assertion failures detected; restored')
    for name, replacement in (
            ('test_target_barrier', patch.object(Battle, 'run_special', lambda *a, **kw: None)),
            ('test_cohesion_target_local', patch.object(Battle, 'run_per_target', lambda *a, **kw: None)),
            ('test_projection_detainment', patch.object(Battle, '_gauge_up_blocked', lambda *a, **kw: False))):
        with replacement:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([FoeClientTest(name)]))
            assert len(result.failures) == 1 and not result.errors, (result.failures, result.errors)
    print('mutations: 3 barrier/local/detainment assertion failures detected; restored')
    original_react = Battle._check_foe_react

    def no_retarget(b, owner, ctx, *args, **kwargs):
        if ctx.target is None or not ctx.target.dead:
            return original_react(b, owner, ctx, *args, **kwargs)

    with patch.object(Battle, '_check_foe_react', no_retarget):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([FoeClientTest('test_bfb_retargets_after_kill')]))
        assert len(result.failures) == 1 and not result.errors, (result.failures, result.errors)
    print('mutations: 1 dead-target retarget assertion failure detected; restored')


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
