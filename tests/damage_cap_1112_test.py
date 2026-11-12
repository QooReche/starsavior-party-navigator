"""26610546: 순증감 상한, 양 진영·지속/수호 경로와 연쇄 제외 경계."""
import os
import sys
import unittest
from collections import Counter
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from simkit import battle, give, unit
from battlesim import simulate
from battlesim.mc import Battle, Ctx
from battlesim.rules import MC_RULES
import battlesim.rules as rules
import battlesim.engine as engine


def setup(mode='net', side=0, inc=25, red=75, guard=False):
    defenders = [unit('target', hp=10**8, df=0)]
    if guard:
        defenders.append(unit('guard', hp=10**8, df=3000))
    attackers = [unit('attacker', hp=10**8, df=0)]
    b = battle(attackers if side == 0 else defenders,
               defenders if side == 0 else attackers,
               mc={'dmg_cap_scope': mode, 'toughness': 'off'}, opts={'coop': False})
    a = (b.allies if side == 0 else b.foes)[0]
    v = (b.foes if side == 0 else b.allies)[0]
    give(a, 'increase', {'피해 증가': inc})
    give(v, 'reduce', {'피해 감소': red})
    if guard:
        g = (b.foes if side == 0 else b.allies)[1]
        give(g, 'share', {'피해 분담(수호)': 50, '피해 감소': 75})
    return b, a, v


class DamageCapTest(unittest.TestCase):
    def test_default_and_legacy(self):
        rule = MC_RULES['dmg_cap_scope']
        self.assertEqual((rule['value'], rule['legacy']), ('net', 'reduce'))
        self.assertIn('reduce', rule['alt'])
        self.assertEqual(rule['grade'], 'code')
        self.assertIn('18148-18201', rule['source'])

    def test_final_sum_includes_critical_before_cap_and_separate_defense(self):
        # 증가·감소·치명, net / reduce의 최종 배율. 2진수로 정확한 경계값 사용.
        cases = [(25, 75, 0, .5, .75), (-25, 50, 0, .5, .25),
                 (0, 100, .75, .75, 1.25), (-75, 0, .5, .75, .75),
                 (0, 50, 0, .5, .5), (0, -25, 0, 1.25, 1.25)]
        for side in (0, 1):
            for inc, red, critical, net, legacy in cases:
                for mode, expected in [('net', net), ('reduce', legacy)]:
                    with self.subTest(side=side, mode=mode, inc=inc, red=red, critical=critical):
                        b, a, v = setup(mode, side, inc, red)
                        v.d.stats['def'] = 3000
                        ctx = Ctx(a, a, a.d.skills['기본기'])
                        dmg = b.final_dmg(a, v, 1000, ctx, bool(critical), critical, 0, 1, None)
                        self.assertEqual(dmg, 500 * expected)
                        clipped = mode == 'net' and 1 + inc / 100 - red / 100 + critical < .5
                        self.assertEqual(b.rule_hits['dmg_cap_scope'], int(clipped))

    def test_cast_both_directions(self):
        for side in (0, 1):
            for mode, expected in [('net', 925), ('reduce', 1387)]:
                b, a, v = setup(mode, side)
                b.cast(a, a.d.skills['기본기'], target=v)
                self.assertEqual(v.taken, expected)
                self.assertEqual(b.rule_hits['dmg_cap_scope'], 0)  # 경계에 닿았지만 잘리지 않음
                self.assertGreater(v.taken / v.maxhp, 0)
                if side == 0:
                    self.assertGreater(b.progress(), 0)

    def test_evade_local_reduction_element_counter_and_break_are_in_sum(self):
        b, a, v = setup(inc=0, red=25)
        a.element, v.element = '태양', '별'
        ctx = Ctx(a, a, a.d.skills['기본기'])
        v.last_slot = '기본기'
        hctx = Ctx(v, a, ctx.skill)
        hctx.evaded.add(v)
        hctx.local = {v: {'defp': 0, 'red': .25}}
        # 증가 .05(유리)+.1(카운터), 감소 .25+.25+.5(회피) -> 순합 -.85 -> -.5
        self.assertEqual(b.final_dmg(a, v, 1000, ctx, False, 0, 0, 1, hctx), 500)
        # 브레이크 −15%p, 피해 증가 +50%까지 합하면 1+.65−.85=.8
        give(a, 'more', {'피해 증가': 50})
        v.broken = True
        self.assertAlmostEqual(b.final_dmg(a, v, 1000, ctx, False, 0, 0, 1, hctx), 800, delta=1)

    def test_dot_both_directions_and_guard(self):
        for side in (0, 1):
            for guard in (False, True):
                for mode in ('net', 'reduce'):
                    b, a, v = setup(mode, side, guard=guard)
                    e = give(v, '연소', src=a, harmful=True)
                    e.dot, e.inst = ('atk', .4), [[a, 2]]
                    b._tick_dot_hot(v)
                    # 기본 740. 수호 시 370씩 분담 후 각각 방어·상한.
                    self.assertEqual(v.taken, (185 if guard else 370) if mode == 'net'
                                     else (277 if guard else 555))
                    if guard:
                        g = (b.foes if side == 0 else b.allies)[1]
                        self.assertEqual(g.taken, 92 if mode == 'net' else 138)
                        self.assertEqual(b.rule_hits['dot_guard'], 1)
                    self.assertEqual(b.rule_hits['dmg_cap_scope'], 0)
                    self.assertGreater(v.taken / v.maxhp, 0)
                    if side == 0:
                        self.assertGreater(b.progress(), 0)

    def test_skill_guard_recomputes_cap_for_each_receiver(self):
        b, a, v = setup(guard=True)
        g = b.foes[1]
        b.cast(a, a.d.skills['기본기'], target=v)
        self.assertEqual((v.taken, g.taken), (462, 231))
        self.assertEqual(b.rule_hits['dmg_cap_scope'], 0)
        self.assertGreater(b.progress(), 0)

    def test_hits_count_only_clipped_receivers_for_direct_and_dot(self):
        for dot in (False, True):
            b, a, v = setup(guard=True)
            give(b.foes[1], 'more reduction', {'피해 감소': 25})
            if dot:
                e = give(v, '연소', src=a, harmful=True)
                e.dot, e.inst = ('atk', .4), [[a, 2]]
                b._tick_dot_hot(v)
            else:
                b.cast(a, a.d.skills['기본기'], target=v)
            self.assertEqual(b.rule_hits['dmg_cap_scope'], 1)  # 수호자만 잘림
            self.assertGreater(b.progress(), 0)

    def test_chain_and_fixed_true_ignore_general_reduction_and_net_floor(self):
        for side in (0, 1):
            for mode in ('net', 'reduce'):
                b, a, v = setup(mode, side, inc=-75, red=90)
                ctx = Ctx(a, a, a.d.skills['기본기'])
                ctx.targets, ctx.target = [v], v
                b.chain(a, {'target': '적 전체', 'stat': 'atk', 'coef': 1}, ctx)
                self.assertEqual(v.taken, 462)  # 연쇄의 주는 증감에는 일반 피해 하한 없음
                v.eff.clear(); b.dirty(v)
                b.chain(a, {'target': '적 전체', 'stat': 'atk', 'coef': 1}, ctx)
                self.assertEqual(v.taken, 924)
                give(v, 'reduce', {'피해 감소': 90})
                b.fixed_true_damage(a, v, 1000)
                self.assertEqual(v.taken, 1924)
                self.assertEqual(b.rule_hits['dmg_cap_scope'], 0)

    def test_chain_penetration_and_defense_stay_separate(self):
        values = []
        for pen in (0, 100):
            b, a, v = setup(inc=25, red=90)
            v.d.stats['def'] = 3000
            give(a, 'penetrate', {'방어 관통': pen})
            b.chain(a, {'target': '적 전체', 'stat': 'atk', 'coef': 1}, None)
            values.append(v.taken)
        self.assertEqual(values, [1156, 1156])

    def test_zero_limit_disables_net_cap(self):
        b, a, v = setup(inc=-75, red=0)
        for cap in (0, -1):
            with patch.object(rules, 'DEC_CAP', cap):
                self.assertEqual(b.final_dmg(a, v, 1000, Ctx(a, a, a.d.skills['기본기']), False, 0, 0, 1, None), 250)
                self.assertEqual(b.rule_hits['dmg_cap_scope'], 0)

    def test_standard_stage_uses_changed_path_and_has_progress(self):
        # 기본 0진행도인 스테이지를 피하고, 공식 표준 육성에서 실제 상한 차이까지 확인.
        seen = Counter()
        original = Battle._damage_mult
        def spy(b, inc, dec, critical=0):
            mult = original(b, inc, dec, critical)
            seen['calls'] += 1
            seen['changed'] += abs(mult - (1 + inc - min(.5, dec) + critical)) > 1e-10
            return mult
        with patch.object(Battle, '_damage_mult', spy):
            r = simulate(['amora', 'bell', 'carmen', 'ceres'], {'stage': 'clo/태양 회랑/FLOOR 250'},
                         {'build': 'standard', 'n_runs': 20, 'seed': 3})
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertGreater(seen['calls'], 0)
        self.assertGreater(seen['changed'], 0)
        print('damage cap stage:', r['outcome']['progress'], dict(seen))


class ExpectedDamageCapTest(unittest.TestCase):
    def make_sim(self, mode=None, red=.5, cr=.5):
        d = engine.DummyDef(atk=1000)
        d.stats.update(cr=cr * 10000, cd=5000)
        d.skills['기본기'].cf = [10000, 0, 0, 0]
        opts = dict(coop=False, break_p=0, dmg_reduction='sum_cap')
        if mode is not None:
            opts['dmg_cap_scope'] = mode
        s = engine.Sim([d], [dict(hp=10**8, **{'def': 3000})], opts=opts)
        s.enemies[0].deb['reduce'] = dict(stacks=1, dur=10, red={'all': red})
        return s, s.party[0], s.enemies[0]

    def test_direct_caps_each_critical_outcome_before_average(self):
        # 증가, 감소, 치명확률, net / reduce 배율. 확률 평균 먼저 제한하면 .625 대신 .5가 됨.
        cases = [(-.25, .5, .5, .625, .5), (.25, .75, .5, .75, 1),
                 (-.75, 0, 1, .75, .75), (0, 1, 1, .5, 1),
                 (0, .5, 0, .5, .5), (0, -.25, .5, 1.5, 1.5)]
        for inc, red, cr, net, reduce in cases:
            for mode, expected in [('net', net), ('reduce', reduce)]:
                with self.subTest(inc=inc, red=red, cr=cr, mode=mode):
                    s, a, e = self.make_sim(mode, red, cr)
                    ctx = engine.Ctx(a, a, a.d.skills['기본기'], False, 1)
                    ctx.inc = inc
                    s.deal_damage(a, ctx)
                    self.assertEqual(a.dmg, 925 * expected)  # 방어율 .5는 별도
                    self.assertGreater(e.maxhp - e.hp, 0)

    def test_dot_caps_both_live_and_snapshot_without_critical(self):
        for snapshot in ('live', 'snapshot'):
            for mode, expected in [('net', 462.5), ('reduce', 693.75)]:
                s, a, e = self.make_sim(mode, .75)
                s.opts['dot_snapshot'] = snapshot
                buff = engine.Buff('inc', {'피해 증가': 25}, 1, 10)
                buff.stacks = 1
                a.buffs['inc'] = buff
                e.deb['dot'] = dict(dot=True, src=a, coef=('atk', 1), base=1850,
                                    inc=.25, stacks=1, dur=2)
                s.act_enemy(e)
                self.assertEqual(a.dmg_src['dot'], expected)
                self.assertGreater(e.maxhp - e.hp, 0)

    def test_shared_mc_default_and_explicit_legacy(self):
        for mode in ('net', 'reduce'):
            with patch.dict(rules.MC_OPTS, dmg_cap_scope=mode):
                s, _, _ = self.make_sim()
                self.assertEqual(s._damage_mult(-.25, .5), .5 if mode == 'net' else .25)
                legacy, _, _ = self.make_sim('reduce')
                self.assertEqual(legacy._damage_mult(-.25, .5), .25)

    def test_disabled_cap_and_legacy_no_reduction(self):
        for cap in (0, -1):
            s, _, _ = self.make_sim('net')
            with patch.object(engine, 'DEC_CAP', cap):
                self.assertEqual(s._damage_mult(-.75, 0), .25)
        s, _, _ = self.make_sim('reduce')
        s.opts['dmg_reduction'] = 'none'
        with patch.object(engine, 'DEC_CAP', -1):
            self.assertEqual(s._damage_mult(-.75, 0), .25)


if __name__ == '__main__':
    unittest.main()
