"""G3 native revival, conditional vampirism, and SKILL_END cleanse."""
import copy
import io
import itertools
import inspect
import math
import textwrap
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'tests')]
from survey_g1_test import setup, mutations
from myinfo_combat_test import definition
from simkit import battle, unit, give
from battlesim.mc import Battle, Ctx, support_report
from battlesim.starsavior.parser import Line
from battlesim.starsavior.myinfo_combat import combat_data
from battlesim.api import _UNIT_CACHE


def vampire():
    d = definition('asherah-order-striker', [(11026, 1)])
    b = battle([d], [unit('first', hp=10**8, sa=99), unit('second', hp=10**8, sa=99)],
               opts=dict(coop=False, nova=False))
    a = b.allies[0]
    a.hp = 1
    return b, a


class SurveyG3(unittest.TestCase):
    def test_revive_restores_toughness_and_break(self):
        for remaining, broken, spawn in [(0, True, 'client'), (1, False, 'client')]:
            b = battle([unit('reviver', skills=[dict(slot='특수기', dm=0, tg='아군 1명')]), unit('dead', sa=7)], [unit('foe')])
            a, dead = b.allies
            dead.dead, dead.hp, dead.sa, dead.broken = True, 0, remaining, broken
            dead.d.lines.append(Line('[등장 후] 자신에게 〈등장 시험〉 (1턴)', '고유 패시브', 'passive'))
            ln = Line('[스킬 사용 후] 스킬 대상에게 부활(생명력 30%)', '특수기', 'active')
            c = Ctx(a, a, a.d.skills['특수기'])
            c.target, c.targets = dead, [dead]
            entered = []
            original = b.run_line
            def observe(owner, line, ctx):
                if line.phase == '등장 후':
                    entered.append((owner.sa, owner.broken))
                    owner.sa, owner.broken = 2, True
                return original(owner, line, ctx)
            with patch.object(b, 'run_line', observe):
                b.run_line(a, ln, c)
            self.assertEqual(entered, [(remaining, broken)] if spawn == 'client' else [])
            self.assertFalse(dead.dead)
            self.assertEqual(dead.sa, 7)
            self.assertFalse(dead.broken)
            self.assertGreater(b.rule_hits['revive_toughness'], 0)

    def test_conditional_vampirism_slots_and_crit(self):
        for slot in ('기본기', '특수기', '궁극기'):
            for crit in (False, True):
                b, a = vampire()
                c = Ctx(a, a, a.d.skills[slot])
                c.target, c.targets = b.foes[0], [b.foes[0]]
                c.cr = 1 if crit else 0
                with patch.object(b.R(0), 'random', return_value=.9):
                    b.deal(a, c)
                expected = math.floor(a.dmg*.2) if crit and slot != '기본기' else 0
                self.assertGreater(a.dmg, 0)
                self.assertEqual(a.hp-1, expected, (slot, crit))

    def test_conditional_vampirism_any_target_and_no_leak(self):
        b, a = vampire()
        a.hp = 1
        c = Ctx(a, a, a.d.skills['궁극기'])
        c.target, c.targets, c.cr = b.foes[0], list(b.foes), .5
        damage = []
        original = b._vampirism_hit
        def observe(actor, target, ctx, amount, last=True):
            damage.append(amount)
            return original(actor, target, ctx, amount, last)
        with patch.object(b.R(0), 'random', side_effect=itertools.chain([.9, .1], itertools.repeat(.9))), patch.object(b, '_vampirism_hit', observe):
            b.deal(a, c)
        self.assertEqual(len(c.crit_targets), 1)
        self.assertEqual(a.hp-1, sum(math.floor(x*.2) for x in damage))
        self.assertGreater(a.hp-1, math.floor(damage[-1]*.2), 'noncritical first target also heals')
        before = a.hp
        for slot in ('기본기', '특수기'):
            c = Ctx(a, a, a.d.skills[slot])
            c.target, c.targets = b.foes[0], [b.foes[0]]
            with patch.object(b.R(0), 'random', return_value=.99):
                b.deal(a, c)
        self.assertEqual(a.hp, before)

    def test_conditional_vampirism_additive_and_heal_received(self):
        b, a = vampire()
        give(a, 'synthetic rates', {'피해 흡혈': 10, '받는 회복량': -50})
        c = Ctx(a, a, a.d.skills['특수기'])
        c.target, c.targets, c.force_crit = b.foes[0], [b.foes[0]], True
        b.deal(a, c)
        self.assertEqual(a.hp-1, math.floor(a.dmg * .3 * .5))

    def test_11026_is_supported(self):
        _UNIT_CACHE.clear()
        d = definition('asherah-order-striker', [(11026, 1)])
        self.assertFalse(any('11026' in x['raw'] for x in support_report([d])))
        rates = [x.eff for x in d.lines if x.eff['kind'] == 'hit_vampirism']
        self.assertEqual({x['slot']: x['rate'] for x in rates}, {'특수기': .2, '궁극기': .2})

    def test_carmen_heals_before_cleanse(self):
        b, a, _ = setup('wedding-carmen', ultimate=1, passive=0)
        a.hp = a.maxhp * .1
        give(a, '회복 불가', {'받는 회복량': -100}, harmful=True)
        before = a.hp
        b.cast(a, a.d.skills['궁극기'])
        self.assertEqual(a.hp, before)
        self.assertFalse(a.has('회복 불가'))
        self.assertGreater(b.rule_hits['heal_cleanse_skill_end'], 0)


CASES = {}   # 옛 스위치 변이는 엔진 다이어트 4단계에서 스위치를 지워 뺌
if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations(SurveyG3, CASES)
        row = copy.deepcopy(combat_data()['potentials']['11026']['1'])
        row.pop('hit_vampirism')
        with patch.dict(combat_data()['potentials']['11026'], {'1': row}):
            r = unittest.TextTestRunner(stream=io.StringIO()).run(SurveyG3('test_11026_is_supported'))
        _UNIT_CACHE.clear()
        assert not r.wasSuccessful() and not r.errors, r.errors
        print('KILLED 11026 derived adapter')
        source = inspect.getsource(Battle.run_special)
        block = "                    x.sa, x.broken = x.sa_max, False\n                    self.rule_hits['revive_toughness'] += 1\n"
        assert source.count(block) == 1
        source = source.replace(block, '').replace('                    x.dead = False\n', '                    x.dead = False\n' + block)
        ns = dict(Battle.run_special.__globals__)
        exec(textwrap.dedent(source), ns)
        with patch.object(Battle, 'run_special', ns['run_special']):
            r = unittest.TextTestRunner(stream=io.StringIO()).run(SurveyG3('test_revive_restores_toughness_and_break'))
        assert not r.wasSuccessful() and not r.errors, r.errors
        print('KILLED toughness restore before AFTER_SPAWN')
    else:
        unittest.main()
