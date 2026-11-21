"""PC 26752678: 생존자 회복·광역 수호 누적·공용 노바·예약 피해 분담."""
import inspect
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simkit import battle, unit, give
from battlesim import mc
from battlesim.api import assumptions_used
from battlesim.rules import MC_OPTS, MC_RULES, DEFAULT_OPTS
from battlesim.starsavior import cosmo_raid as C


def setup(name='행성 정화', foes=None, **kw):
    opts = dict(break_skill_scale='off', break_skill_level='off')
    return battle([unit('ally%d' % i) for i in range(4)],
                  foes or [unit('guard', df=3000), unit('less', df=0), unit('target', df=0)],
                  break_skill={'name': name, 'level': 1}, mc=opts, **kw)


def fire(b):
    b.break_points, b.break_skill_cd = 3, 0
    b._use_break_skill(next(u for u in b.allies if not u.dead))
    assert b.break_skill_uses > 0


class AllowlistBreakTest(unittest.TestCase):
    def test_defaults_and_assumptions(self):
        for key, legacy in [('add_damage_guard', 'off')]:
            self.assertEqual(MC_OPTS[key], 'client')
            self.assertEqual(MC_RULES[key]['legacy'], legacy)
            self.assertEqual(MC_RULES[key]['grade'], 'code')
        names = {r['rule'] for r in assumptions_used(MC_OPTS, DEFAULT_OPTS)}
        self.assertNotIn('mc.break_skill_residuals', names)
        self.assertNotIn('mc.add_damage_guard', names)

    def test_cube_alive_sum(self):
        for amount in [600]:
            b = setup('큐브 과부하')
            b.allies[-1].dead, b.allies[-1].hp = True, 0
            for u in b.allies[:-1]:
                u.hp = 100
            give(b.allies[0], '회복 증가', {'받는 회복량': 25})
            fire(b)
            self.assertEqual(b.allies[1].hp, 100 + amount)
            self.assertEqual(b.allies[0].hp, 100 + int(amount * 1.25))
            self.assertEqual(b.allies[-1].hp, 0)
            self.assertNotIn('치트 매트릭스', b.allies[-1].eff)

    def test_cube_current_hp_stat_level_and_rounding(self):
        b = setup('큐브 과부하')
        b.mc['break_skill_level'] = 'data'
        b.break_skill['level'] = 2
        give(b.allies[0], '최대 HP 증가', {'생명력%': 50})
        b.dirty(b.allies[0])
        b.allies[-1].dead = True
        b.allies[1].hp = 100
        give(b.allies[1], '회복 감소', {'받는 회복량': -33})
        fire(b)
        self.assertEqual(b.allies[1].hp, 100 + int(35000 * .021 * .67))

    def test_aoe_guard_last_aggregate_before_defense(self):
        b = setup()
        guard, less, target = b.foes
        give(guard, '수호', {'피해 분담(수호)': 60})
        give(less, '수호', {'피해 분담(수호)': 20})
        with patch.object(b, '_break_dmg', wraps=b._break_dmg) as calc:
            fire(b)
        self.assertEqual([(c.args[0].name, c.args[1]) for c in calc.call_args_list],
                         [('less', 400), ('target', 400), ('guard', 2200)])
        self.assertEqual([u.taken for u in b.foes], [1100, 400, 400])
        self.assertEqual(b.break_skill_dmg, 1900)
        self.assertEqual(b.rule_hits['break_skill_guard'], 2)

    def test_guard_one_random_draw_and_shield(self):
        b = setup()
        guard, less, target = b.foes
        give(guard, '수호', {'피해 분담(수호)': 50})
        give(guard, '보호막').shield = 100
        with patch.object(b, 'rand', side_effect=[.9, 1.0, 1.1]) as rand:
            fire(b)
        self.assertEqual(rand.call_count, 3)
        self.assertEqual([u.taken for u in b.foes], [1100, 450, 500])
        self.assertEqual(guard.hp, 9000)
        self.assertNotIn('보호막', guard.eff)

    def test_target_immunity_no_donation(self):
        for immune in ('무적', '스킬 피해 무효'):
            b = setup()
            guard, less, target = b.foes
            give(guard, '수호', {'피해 분담(수호)': 50})
            give(target, immune)
            fire(b)
            self.assertEqual(target.taken, 0)
            self.assertEqual(less.taken, 500)
            self.assertEqual(guard.taken, 750)
            self.assertEqual(b.rule_hits['break_skill_guard'], 1)

    def test_guard_nullifier_consumes_aggregate_once(self):
        b = setup()
        guard = b.foes[0]
        give(guard, '수호', {'피해 분담(수호)': 50})
        give(guard, '스킬 피해 무효')
        fire(b)
        self.assertEqual([u.taken for u in b.foes], [0, 500, 500])
        self.assertFalse(guard.has('스킬 피해 무효'))
        self.assertEqual(b.rule_hits['bskill_nullify'], 1)

    def test_guard_single_dead(self):
        b = setup(foes=[unit('only', df=0)])
        give(b.foes[0], '수호', {'피해 분담(수호)': 50})
        fire(b)
        self.assertEqual(b.foes[0].taken, 1000)
        self.assertEqual(b.rule_hits['break_skill_guard'], 0)
        for dead in [True]:
            b = setup()
            guard = b.foes[0]
            give(guard, '수호', {'피해 분담(수호)': 50})
            guard.dead = dead
            fire(b)
            self.assertEqual([u.taken for u in b.foes[1:]], [1000, 1000])
            self.assertEqual(b.rule_hits['break_skill_guard'], 0)

    def test_guard_changes_during_aoe_use_separate_shared_hit(self):
        b = setup()
        guard, less, target = b.foes
        give(guard, '수호', {'피해 분담(수호)': 60})
        give(less, '수호', {'피해 분담(수호)': 20})
        wake = b._hit_wake
        def remove_first_guard(v, hit):
            wake(v, hit)
            if v is less:
                guard.eff.pop('수호')
                b.dirty(guard)
        with patch.object(b, '_hit_wake', side_effect=remove_first_guard), patch.object(b, 'rand', return_value=1) as rand:
            fire(b)
        # 첫 수호자가 모은 600은 원래 마지막 타격에 남음. 이후 최대 수호자는 별도 몫을 받음.
        self.assertEqual([u.taken for u in b.foes], [640, 920, 800])
        self.assertEqual(b.break_skill_dmg, 2360)
        self.assertEqual(rand.call_count, 5)

    def test_nova_once_team_cap_and_shared_consumption(self):
        for name in ('특이점 관측', '차원 강습'):
            for initial, expected in [(0, 4), (10, 12)]:
                b = setup(name)
                b.team_nova = initial
                b.allies[0].dead = True  # 지급 대표 슬롯 사망도 팀 지급을 막지 않음
                fire(b)
                self.assertEqual(b.team_nova, expected)
                self.assertEqual([u.nova for u in b.allies], [0] * 4)
                b.nova_add(b.allies[1], -4)
                self.assertEqual(b.nova_of(b.allies[2]), expected - 4)
        b = setup('특이점 관측', opts={'nova_pool': 'unit'})
        b.allies[0].dead = True
        fire(b)
        self.assertEqual(b.team_nova, 0)
        self.assertEqual([u.nova for u in b.allies], [0, 4, 4, 4])

    def test_pending_damage_default_guard_and_nonconsuming_nullifier(self):
        for immune in (None, '무적', '스킬 피해 무효'):
            b = setup()
            guard, less, target = b.foes
            give(guard, '수호', {'피해 분담(수호)': 50})
            give(less, '수호', {'피해 분담(수호)': 25})
            if immune:
                give(target, immune)
            give(guard, '보호막').shield = 100
            controller = C.Controller(b)
            controller.pending_damage.append((target, 1000))
            controller.flush_damage()
            controller.flush_damage()
            self.assertEqual(guard.hp, 9600 if immune is None else 10000)
            self.assertEqual(target.taken, 0 if immune == '무적' else (500 if immune is None else 1000))
            self.assertEqual(less.taken, 0)
            self.assertEqual(b.rule_hits['add_damage_guard'], int(immune is None))
            self.assertEqual(target.has('스킬 피해 무효'), immune == '스킬 피해 무효')


def mutations():
    cases = [
        ('_use_break_skill', "heal_team = self.alive(0)", 'heal_team = self.allies', 'test_cube_alive_sum'),
        ('_break_guard', "return guard, share", 'return None, 0.0', 'test_aoe_guard_last_aggregate_before_defense'),
        ('_use_break_skill', 'pending += shared', 'pending += 0', 'test_aoe_guard_last_aggregate_before_defense'),
        ('_use_break_skill', 'targets.append(queued_guard)', 'targets.insert(0, queued_guard)', 'test_aoe_guard_last_aggregate_before_defense'),
        ('_use_break_skill', 'elif not guard.dead:', 'elif False and not guard.dead:', 'test_guard_changes_during_aoe_use_separate_shared_hit'),
        ('_use_break_skill', "and not v.on('스킬 피해 무효')", 'and True', 'test_target_immunity_no_donation'),
        ('_use_break_skill', 'self.nova_add(self.allies[0], nova)', 'self.nova_add(self.allies[0], nova * 4)', 'test_nova_once_team_cap_and_shared_consumption'),
        ('fixed_true_damage', "(client or self.mc['add_damage_guard'] == 'client')", 'False', 'test_pending_damage_default_guard_and_nonconsuming_nullifier'),
    ]
    for method, old, new, test in cases:
        fn = getattr(mc.Battle, method)
        src = textwrap.dedent(inspect.getsource(fn))
        assert old in src, (method, old)
        scope = {}
        exec(compile(src.replace(old, new, 1), '<mutation>', 'exec'), fn.__globals__, scope)
        with patch.object(mc.Battle, method, scope[method]):
            result = unittest.TestResult()
            AllowlistBreakTest(test).run(result)
        assert result.failures and not result.errors, (method, test, result.errors)
        print('검출:', method, test)
    print('변이 %d개 모두 assertion 실패 확인·원복' % len(cases))


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
