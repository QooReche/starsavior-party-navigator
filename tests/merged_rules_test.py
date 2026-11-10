"""11/10 D/E 병합 경계. 합성 전투로 각 경로를 직접 실행함."""
import io
import itertools
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, Ctx
from battlesim.starsavior.parser import Line


def effect(b, owner, target, text, phase='스킬 사용 후'):
    ctx = Ctx(owner, owner, owner.d.skills['기본기'])
    ctx.target, ctx.targets = target, [target]
    b.run_line(owner, Line('[' + phase + '] ' + text, '기본기', 'active'), ctx)


class MergedRulesTest(unittest.TestCase):
    def test_turn_start_buff_precedes_lethal_dot_and_expires(self):
        for order, fresh in itertools.product(('client', 'dot_first'), ('client', 'self')):
            with self.subTest(order=order, fresh=fresh):
                actor = unit('a')
                actor.lines = [Line('[턴 시작 시] 자신에게 〈무적〉 (1턴)', '고유 패시브', 'passive')]
                b = battle([actor], [unit('f', hp=10**8)],
                           mc=dict(turn_start_order=order, buff_fresh_scope=fresh), opts={'coop': False})
                a, f = b.allies[0], b.foes[0]
                a.hp = 1
                e = give(a, '연소', src=f, harmful=True, dur=1)
                e.dot, e.inst = ('atk', .2), [[f, 1]]
                b.act(a)
                self.assertEqual(a.dead, order == 'dot_first')
                self.assertFalse(a.acting)
                if order == 'client':
                    self.assertGreater(f.taken, 0)
                    self.assertGreater(b.rule_hits['turn_start_order'], 0)
                    self.assertEqual(a.has('무적'), fresh == 'self')
                    self.assertNotIn('연소', a.eff)

    def test_shield_clock_independent_of_general_fresh(self):
        for order, fresh, shield, phase in itertools.product(
                ('client', 'dot_first'), ('client', 'self'), ('turn_start', 'turn_end'),
                ('턴 시작 시', '스킬 사용 후')):
            with self.subTest(order=order, fresh=fresh, shield=shield, phase=phase):
                adef, otherdef = unit('a'), unit('other')
                if phase == '턴 시작 시':
                    adef.lines = [Line('[턴 시작 시] 자신에게 〈시험 보호막〉 (1턴) 보호막 = 자신 생명력×10%',
                                       '고유 패시브', 'passive')]
                else:
                    otherdef.lines = [Line('[스킬 사용 후] (조건: 아군 공격 후) 아군 전체에게 〈시험 보호막〉 (1턴) 보호막 = 자신 생명력×10%',
                                           '고유 패시브', 'passive')]
                b = battle([adef, otherdef], [unit('f', hp=10**8)],
                           mc=dict(turn_start_order=order, buff_fresh_scope=fresh, shield_tick=shield),
                           opts={'coop': False})
                a, other = b.allies
                b.act(a)
                self.assertGreater(a.shield_given + other.shield_given, 0)
                self.assertEqual(a.has('시험 보호막'), shield == 'turn_start' or phase == '스킬 사용 후')
                a.d.lines, other.d.lines = [], []
                b.act(a)
                self.assertNotIn('시험 보호막', a.eff)

    def test_revive_domain_spawn_and_dead_keep(self):
        for spawn, domain, keep, fresh in itertools.product(
                ('client', 'off'), ('client', 'none'), ('client', 'off'), ('client', 'self')):
            with self.subTest(spawn=spawn, domain=domain, keep=keep, fresh=fresh):
                b = battle([unit('a'), unit('other', role='서포터')], [unit('f', hp=10**8)],
                           mc=dict(revive_after_spawn=spawn, break_domain_revive=domain,
                                   dead_keep_dnp=keep, buff_fresh_scope=fresh),
                           break_skill={'name': '큐브 과부하'})
                a, other = b.allies
                b.break_points = 3
                b._use_break_skill(a)
                other.d.lines = [Line('[등장 후] 자신에게 〈등장 강화〉 (1턴 / 생명력% +20%)',
                                     '고유 패시브', 'passive')]
                give(other, '보존 약화', {'생명력%': -10}, harmful=True).dead_keep = True
                b.dirty(other)
                b.kill(other, b.foes[0])
                b._tick_break_domain(b.break_domain_clock)
                observed = []
                run_line = b.run_line
                def watch(owner, ln, ctx):
                    if owner is other and ln.phase == '등장 후':
                        observed.append(other.has('치트 매트릭스'))
                    return run_line(owner, ln, ctx)
                with patch.object(b, 'run_line', watch):
                    effect(b, a, other, '스킬 대상에게 부활(생명력 50%)')
                self.assertEqual(observed, [domain == 'client'] if spawn == 'client' else [])
                self.assertFalse(other.dead)
                self.assertEqual(other.has('보존 약화'), keep == 'client')
                self.assertEqual(other.has('등장 강화'), spawn == 'client')
                self.assertEqual(other.hp, 5000 + (1000 if spawn == 'client' else 0) - (500 if keep == 'client' else 0))
                self.assertNotIn('오메가 프로토콜', other.eff)
                self.assertEqual(other.has('치트 매트릭스'), domain == 'client')
                if domain == 'client':
                    self.assertEqual(other.eff['치트 매트릭스'].dur, b.break_domain_remaining)
                    self.assertFalse(other.eff['치트 매트릭스'].fresh)
                    self.assertGreater(b.rule_hits['break_domain_revive'], 0)

    def test_break_kill_new_wave_gauge_and_reservation(self):
        for gauge, extra, carry in itertools.product(
                ('client', 'exclude'), ('clear', 'keep'), ('keep', 'client')):
            with self.subTest(gauge=gauge, extra=extra, carry=carry):
                b = battle([unit('a')], [unit('first', hp=1)], break_skill={'name': '스타피어서'},
                           mc=dict(break_gauge_actor=gauge, wave_extra_turn=extra, wave_carry=carry),
                           opts={'coop': False})
                a = b.allies[0]
                a.gauge, a.extra_turn, b.break_points = 10000, True, 3
                b.act(a)
                self.assertTrue(b.foes[0].dead)
                self.assertEqual(b.break_skill_uses, 1)
                self.assertEqual(a.actions, 0)
                before = 2000 if gauge == 'client' else 10000
                self.assertEqual((a.gauge, a.extra_turn), (before, True))
                b.waves.append([unit('second', hp=10**8)])
                b.spawn_wave()
                self.assertEqual((a.gauge, a.extra_turn), (0, False) if extra == 'clear' else (before, True))
                b.act(a)
                self.assertEqual(a.actions, 1)
                self.assertGreater(b.foes[0].taken, 0)


def mutations():
    cases = [
        ('turn_start_order', 'dot_first', 'test_turn_start_buff_precedes_lethal_dot_and_expires'),
        ('buff_fresh_scope', 'self', 'test_turn_start_buff_precedes_lethal_dot_and_expires'),
        ('shield_tick', 'turn_start', 'test_shield_clock_independent_of_general_fresh'),
        ('revive_after_spawn', 'off', 'test_revive_domain_spawn_and_dead_keep'),
        ('break_domain_revive', 'none', 'test_revive_domain_spawn_and_dead_keep'),
        ('dead_keep_dnp', 'off', 'test_revive_domain_spawn_and_dead_keep'),
        ('break_gauge_actor', 'exclude', 'test_break_kill_new_wave_gauge_and_reservation'),
        ('wave_extra_turn', 'keep', 'test_break_kill_new_wave_gauge_and_reservation'),
    ]
    original = Battle.__init__
    for key, value, method in cases:
        def force(self, *args, **kw):
            original(self, *args, **kw)
            self.mc = dict(self.mc, **{key: value})
        def run():
            return unittest.TextTestRunner(stream=io.StringIO()).run(MergedRulesTest(method))
        assert run().wasSuccessful(), method
        with patch.object(Battle, '__init__', force):
            result = run()
        assert result.failures and not result.errors, (key, result.errors)
        print(key, 'assertion failures:', len(result.failures))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
