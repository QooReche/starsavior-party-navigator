"""PC 26752678 follow-up: victim-local damage and reaction target RNG."""
import copy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Battle, Ctx
from battlesim.rules import MC_OPTS
from battlesim.starsavior.foe import stage_waves
from battlesim.starsavior.parser import Line
from battlesim.starsavior import cosmo_raid


class FollowupTest(unittest.TestCase):
    @staticmethod
    def shield(b, owner, basis='자신', duration=3):
        ln = Line(f'[스킬 사용 후] 아군 전체에게 〈보호막〉 ({duration}턴) 보호막 = {basis} 생명력×25%', '특수기', 'active')
        b.run_line(owner, ln, Ctx(owner, owner, None))

    def test_barrier_basis_receive_and_signed_truncation(self):
        for basis in ('자신', '대상'):
            for give_rate, receive_rate, expected in [(50, 0, 378), (-10, 0, 227), (10, 20, 327)]:
                with self.subTest(basis=basis, give_rate=give_rate, receive_rate=receive_rate):
                    b = battle([unit('caster', hp=1011), unit('recipient', hp=2007)], [unit('foe')])
                    owner, target = b.allies
                    give(owner, 'give', {'주는 보호막량': give_rate})
                    give(target, 'give', {'주는 보호막량': 50})
                    give(target, 'receive', {'받는 보호막량': receive_rate})
                    self.shield(b, owner, basis)
                    # SELF: int(1011*.25)=252; signed bonus truncates toward zero.
                    # TARGET: recipient 2007 -> base501, GIVE50 + own RECEIVE.
                    want = expected if basis == '자신' else 501 + int(501 * (.5 + receive_rate / 100))
                    self.assertEqual(target.shield_total(), want)
                    self.assertGreater(b.rule_hits['barrier_formula' if basis == '자신' else 'foe_target_barrier'], 0)

    def test_zero_barrier_does_not_exist_or_refresh(self):
        for basis in ('자신', '대상'):
            b = battle([unit('caster', hp=1011)], [unit('foe')])
            a = b.allies[0]
            give(a, 'give', {'주는 보호막량': -100})
            self.shield(b, a, basis)
            self.assertFalse(a.has('보호막'))
            self.assertEqual(a.shield_total(), 0)
            self.assertTrue(cosmo_raid.Controller._no_shield(a, ['보호막']))
            old = give(a, '보호막', dur=1)
            old.shield = 77
            seq = old.seq
            self.shield(b, a, basis, duration=9)
            self.assertIs(a.eff['보호막'], old)
            self.assertEqual((old.shield, old.dur, old.seq), (77, 1, seq))
            self.assertEqual(a.shield_given, 0)

    def test_zero_barrier_mogulus_skill_start(self):
        waves, meta = cosmo_raid.build_waves('mogulus', 3, 0)
        b = battle([unit('caster', hp=100000)], waves[0], mc={'cosmo_raid_boss': 'on'})
        a, boss = b.allies[0], b.foes[0]
        give(a, 'give', {'주는 보호막량': -100})
        self.shield(b, a)
        b.cast(boss, boss.d.skills['기본기'], target=a)
        self.assertTrue(a.has('몰락한 사념(해제불가)'))
        self.assertEqual(a.spd(), 0)

    def test_barrier_legacy_preserved(self):
        b = battle([unit('caster', hp=1011)], [unit('foe')], mc={'barrier_formula': 'legacy'})
        a = b.allies[0]
        give(a, 'give', {'주는 보호막량': 50, '받는 보호막량': 20})
        self.shield(b, a)
        self.assertEqual(a.shield_total(), 379)
        a.eff.clear()
        give(a, 'give', {'주는 보호막량': -100})
        self.shield(b, a)
        self.assertTrue(a.has('보호막'))
        self.assertEqual(a.shield_total(), 0)

    def test_barrier_receive_from_recipient_stats(self):
        b = battle([unit('caster', hp=1011), unit('recipient')], [unit('foe')])
        owner, target = b.allies
        owner.fx['받는 보호막량'] = 100  # This is not the recipient's RECEIVE.
        target.fx['받는 보호막량'] = 20
        b.dirty(owner)
        b.dirty(target)
        self.shield(b, owner)
        self.assertEqual(target.shield_total(), 302)  # 252 + int(252*.2)
        self.assertEqual(owner.shield_total(), 504)

    def test_cohesion_each_victim_independent_of_primary(self):
        _, waves = stage_waves('oph', '고대 지하 유적', 'SECTOR 39-10')
        d = next(d for w in waves for d in w if d.name == '공허결집자')
        for primary in (0, 1):
            for marked in (0, 1):
                with self.subTest(primary=primary, marked=marked):
                    b = battle([unit('a'), unit('b')], [copy.deepcopy(d)])
                    boss = b.foes[0]
                    ln = next(l for l in boss.d.lines if '능력치 보정 피해 증가' in l.raw and '연쇄 피해' in l.raw)
                    give(b.allies[marked], '공허 포자', harmful=True)
                    ctx = Ctx(boss, boss, boss.d.skills['궁극기'])
                    ctx.target, ctx.targets = b.allies[primary], list(b.allies)
                    b.run_line(boss, ln, ctx)
                    self.assertEqual([ctx.local_by[a]['inc'] for a in b.allies],
                                     [.3 if i == marked else 0 for i in range(2)])
                    self.assertIsNone(ctx.local)
                    self.assertEqual([a.hp for a in b.allies], [a.maxhp for a in b.allies])
                    # The actual ultimate is single-target; the other unit's
                    # spore must not activate its condition either.
                    single = Ctx(boss, boss, boss.d.skills['궁극기'])
                    single.target = b.allies[primary]
                    single.targets = [single.target]
                    b.run_line(boss, ln, single)
                    self.assertEqual(single.inc, .3 if primary == marked else 0)

    def test_reaction_single_and_multiple_candidates(self):
        _, waves = stage_waves('guild', 'BFB', '길드 방어전 6단계')
        for count in (1, 2):
            b = battle([unit('a'), unit('b')], copy.deepcopy(waves[-1]))
            boss = next(u for u in b.foes if u.d.name == 'BFB')
            for a in b.allies[:count]:
                give(a, '신부 경쟁(해제불가)')
            sk = boss.d.trigger_skills['특수기']
            rng = b.R(boss.side)
            before = rng.getstate()
            # Isolate target selection from the cast's hit/crit/effect random draws.
            with patch.object(rng, 'choice', wraps=rng.choice) as choice, patch.object(b, 'cast', return_value='cast') as cast:
                self.assertEqual(b.trigger_cast(boss, sk), 'cast')
                self.assertIn(cast.call_args.kwargs['target'], b.allies[:count])
                self.assertEqual(choice.call_count, int(count > 1))
                self.assertEqual(rng.getstate() == before, count == 1)
            self.assertEqual(b.rule_hits['reaction_single_target_rng'], int(count == 1))

    def test_reaction_legacy_consumes_single_candidate(self):
        with patch.dict(MC_OPTS, reaction_single_target_rng='legacy'):
            _, waves = stage_waves('guild', 'BFB', '길드 방어전 6단계')
            b = battle([unit('a')], copy.deepcopy(waves[-1]))
        boss = next(u for u in b.foes if u.d.name == 'BFB')
        give(b.allies[0], '신부 경쟁(해제불가)')
        before = b.R(boss.side).getstate()
        with patch.object(b, 'cast', return_value='cast'):
            b.trigger_cast(boss, boss.d.trigger_skills['특수기'])
        self.assertNotEqual(before, b.R(boss.side).getstate())


def mutations():
    cases = [
        ('victim-local off', 'test_cohesion_each_victim_independent_of_primary',
         patch.object(Battle, 'run_per_target', lambda *a: None)),
        ('single RNG restored', 'test_reaction_single_and_multiple_candidates',
         patch.dict(MC_OPTS, reaction_single_target_rng='legacy')),
        ('old barrier formula', 'test_barrier_basis_receive_and_signed_truncation',
         patch.dict(MC_OPTS, barrier_formula='legacy')),
        ('zero shield retained', 'test_zero_barrier_does_not_exist_or_refresh',
         patch.dict(MC_OPTS, barrier_formula='legacy')),
        ('zero shield blocks Mogulus', 'test_zero_barrier_mogulus_skill_start',
         patch.dict(MC_OPTS, barrier_formula='legacy')),
        ('recipient stat omitted', 'test_barrier_receive_from_recipient_stats',
         patch.dict(MC_OPTS, barrier_formula='legacy')),
    ]
    for label, name, mutation in cases:
        with mutation:
            r = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([FollowupTest(name)]))
        assert r.failures and not r.errors, (label, r.failures, r.errors)
        print(label, ': assertion failure detected; restored')


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
