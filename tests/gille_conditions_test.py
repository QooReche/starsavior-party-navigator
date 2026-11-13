"""목록 보유 조건·길레 승급. 합성 상태/표준 육성만 사용, --mutate로 결함 주입."""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim import simulate
from battlesim.mc import Battle, Ctx
from battlesim.metrics import unit_def
from battlesim.rules import MC_OPTS
from battlesim.starsavior.parser import Line

OVERTURE, RHAPSODY, FINALE = [n + '(해제불가)' for n in ('서곡', '광시곡', '피날레')]
MARKER = FINALE + ' 승급 체크용 버프'


def condition(key, names, count=''):
    return Line(f'[스킬 사용 후] (조건: 아군 행동 후 [{key}: {names}{count}]) 자신에게 행동 게이지 10%p 증가',
                '고유 패시브', 'passive')


class SourceBuffListTest(unittest.TestCase):
    def test_each_list_member_and_absent_source(self):
        for key in ('시전자가 보유', '턴 유닛이 보유'):
            b = battle([unit('owner'), unit('source')], [unit('foe')])
            owner, src = b.allies
            ctx = Ctx(owner, src, src.d.skills['기본기'])
            ln = condition(key, f'{OVERTURE}, {RHAPSODY}, {FINALE}')
            self.assertFalse(b.cond_ok(owner, ln, ctx))
            for name in (OVERTURE, RHAPSODY, FINALE):
                src.eff.clear()
                give(src, name)
                self.assertTrue(b.cond_ok(owner, ln, ctx), (key, name))
            ctx.src = None
            self.assertFalse(b.cond_ok(owner, ln, ctx))

    def test_stack_count_uses_matching_source_name_not_owner_or_sum(self):
        for key in ('시전자가 보유', '턴 유닛이 보유'):
            b = battle([unit('owner'), unit('source')], [unit('foe')])
            owner, src = b.allies
            give(owner, 'A', stacks=5)
            give(src, 'A', stacks=2)
            give(src, 'B', stacks=3)
            ctx = Ctx(owner, src, src.d.skills['기본기'])
            for count, expected in [('; 중첩수: 2', True), ('; 중첩수: 3', True),
                                    ('; 중첩수: 5', False), ('; 중첩수: 2; 중첩수: 3', False)]:
                self.assertEqual(b.cond_ok(owner, condition(key, 'A, B', count), ctx), expected, (key, count))
            # 앞의 자신이 보유 중첩수로 잘못 바인딩되는 것도 검사.
            ln = condition(key, 'A', '; 중첩수: 2')
            ln.params.insert(0, ('자신이 보유', 'A'))
            self.assertTrue(b.cond_ok(owner, ln, ctx))

    def test_single_name_and_literal_legacy(self):
        for key in ('시전자가 보유', '턴 유닛이 보유'):
            b = battle([unit('owner'), unit('source')], [unit('foe')], mc={'source_buff_list': 'literal'})
            owner, src = b.allies
            give(src, OVERTURE)
            ctx = Ctx(owner, src, src.d.skills['기본기'])
            self.assertTrue(b.cond_ok(owner, condition(key, OVERTURE), ctx))
            self.assertFalse(b.cond_ok(owner, condition(key, f'{OVERTURE}, {RHAPSODY}'), ctx))

    def test_ally_break_triggers_gille_special_once(self):
        b = battle([unit_def('gille'), unit_def('asherah-order-striker')],
                   [unit('foe', hp=10**8, sa=1)], opts={'coop': False, 'nova': False})
        gille, src = b.allies
        give(src, OVERTURE, dur=float('inf'))
        src.acting = True
        casts = []
        original = Battle.cast
        def record(b, u, sk, *args, **kw):
            if u is gille:
                casts.append((sk.slot, kw.get('extra', args[0] if args else False)))
            return original(b, u, sk, *args, **kw)
        with patch.object(Battle, 'cast', record):
            b.cast(src, src.d.skills['특수기'], target=b.foes[0])
        self.assertGreater(b.progress(), 0)
        self.assertTrue(b.foes[0].broken)
        self.assertEqual(casts, [('특수기', True)])
        self.assertTrue(gille.has('특수기 발동 제한 체크용 버프'))
        self.assertTrue(src.has(RHAPSODY))
        self.assertFalse(src.has(FINALE))


class GillePromotionTest(unittest.TestCase):
    def make_battle(self, **mc):
        return battle([unit_def('gille'), unit('rhapsody'), unit('none'), unit('finale')],
                      [unit('foe', hp=10**9, sa=999)], mc=mc, opts={'coop': False, 'nova': False})

    def test_no_marker_requires_two_specials(self):
        b = self.make_battle()
        gille = b.allies[0]
        give(gille, OVERTURE, dur=float('inf'))
        gille.acting = True
        b.cast(gille, gille.d.skills['특수기'], target=b.foes[0])
        self.assertGreater(b.progress(), 0)
        self.assertTrue(gille.has(RHAPSODY))
        self.assertFalse(any(u.has(FINALE) or u.has(MARKER) for u in b.allies))
        b.cast(gille, gille.d.skills['특수기'], target=b.foes[0])
        self.assertTrue(gille.has(FINALE))
        self.assertFalse(gille.has(RHAPSODY))
        self.assertFalse(any(u.has(FINALE) for u in b.allies[1:]))
        self.assertGreater(b.rule_hits['gille_promotion_target'], 0)

    def test_mixed_stages_use_cast_start_marker(self):
        b = self.make_battle()
        gille, rhapsody, empty, finale = b.allies
        for u, name in ((gille, OVERTURE), (rhapsody, RHAPSODY), (finale, FINALE)):
            give(u, name, dur=float('inf'))
        b.cast(gille, gille.d.skills['특수기'], target=b.foes[0])
        self.assertTrue(gille.has(RHAPSODY))
        self.assertFalse(gille.has(FINALE))
        self.assertTrue(rhapsody.has(FINALE))
        self.assertTrue(finale.has(FINALE))
        self.assertFalse(any(empty.has(n) for n in (OVERTURE, RHAPSODY, FINALE)))

    def test_legacy_reproduces_premature_finale(self):
        b = self.make_battle(gille_promotion_target='fallback')
        gille = b.allies[0]
        give(gille, OVERTURE, dur=float('inf'))
        b.cast(gille, gille.d.skills['특수기'], target=b.foes[0])
        self.assertTrue(any(u.has(FINALE) for u in b.allies))

    def test_standard_battle_reaches_both_steps(self):
        team = ['asherah-order-striker', 'gille', 'fei', 'amora']
        seen = []
        original = Battle.cast
        def record(b, u, sk, *args, **kw):
            before = [v for v in b.allies if v.has(OVERTURE)] if u.key == 'gille' and sk.slot == '특수기' else []
            result = original(b, u, sk, *args, **kw)
            if u.key == 'gille' and sk.slot == '특수기':
                seen.append((len(before), all(v.has(RHAPSODY) and not v.has(FINALE) for v in before),
                             any(v.has(FINALE) for v in b.allies)))
            return result
        with patch.object(Battle, 'cast', record):
            r = simulate(dict(units=team, leader=0), dict(stage='clo/태양 회랑/FLOOR 200'),
                         dict(build='standard', n_runs=1, seed=7))
        self.assertGreater(r['outcome']['progress'], 0)
        self.assertGreaterEqual(len(seen), 2)
        self.assertGreater(seen[0][0], 0)
        self.assertTrue(seen[0][1])
        self.assertFalse(seen[0][2])
        self.assertTrue(seen[1][2])


def mutations():
    original = Battle.exec_line
    def drop_extra(b, owner, ln, ctx):
        if ln.eff['kind'] != 'extra_cast':
            return original(b, owner, ln, ctx)
    cases = [
        ('literal caster/turn lists', SourceBuffListTest('test_each_list_member_and_absent_source'),
         patch.dict(MC_OPTS, source_buff_list='literal')),
        ('lost ally trigger', SourceBuffListTest('test_ally_break_triggers_gille_special_once'),
         patch.dict(MC_OPTS, source_buff_list='literal')),
        ('promotion fallback', GillePromotionTest('test_no_marker_requires_two_specials'),
         patch.dict(MC_OPTS, gille_promotion_target='fallback')),
        ('disabled extra casts', SourceBuffListTest('test_ally_break_triggers_gille_special_once'),
         patch.object(Battle, 'exec_line', drop_extra)),
    ]
    for name, test, mutation in cases:
        with mutation:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(test)
        if result.errors or not result.failures:
            raise AssertionError(f'{name}: expected assertion failure, got {result}')
        print('detected:', name)


if __name__ == '__main__':
    if '--mutate' in sys.argv:
        mutations()
    else:
        unittest.main()
