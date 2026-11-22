"""클라 추가 피해 큐(chain_timing 스위치는 11/22 삭제 — 항상 client_queue): 적 연쇄 원형 연결과 연쇄·고정 피해·응징 통합 큐(PC 26752678); --mutations."""
import inspect
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, give, unit   # noqa: E402
from battlesim.mc import Battle, Ctx   # noqa: E402
from battlesim.rules import MC_OPTS   # noqa: E402
from battlesim.starsavior import chain_se   # noqa: E402
from battlesim.starsavior import cosmo_raid as C   # noqa: E402
from battlesim.starsavior.parser import Line   # noqa: E402

FOE_KEY, FOE_SLOT = 'foe:106:0', '기본기'
FOE_RAW = '[스킬 사용 후] 스킬 대상에게 연쇄 피해 = 자신 공격력×50% (×1.85, 방어력 적용)'


class ChainQueueTest(unittest.TestCase):
    def setup_foe(self):
        b = battle([unit('ally', df=0, hp=10**6)], [unit('foe', df=0)],
                   opts={'coop': False, 'nova': False})
        a, f = b.allies[0], b.foes[0]
        f.key = f.d.key = FOE_KEY
        ln = Line(FOE_RAW, FOE_SLOT, 'active')
        f.d.lines = [ln]
        ctx = Ctx(f, f, f.d.skills['기본기'])
        ctx.target, ctx.targets = a, [a]
        return b, a, f, ln, ctx

    def test_mapping_rows_are_clean(self):
        doc = json.loads((ROOT / 'data/chain_se.json').read_text(encoding='utf8'))
        self.assertEqual(chain_se.foes()[FOE_KEY][(FOE_SLOT, FOE_RAW)], {'buff': 2510, 'retarget': False})
        self.assertFalse([k for k in doc['report'] if k.startswith('원형 불일치') or '다른 BuffId' in k])
        self.assertEqual(doc['fixed'], {'belgras_hyper': 2509, 'cosmo_punish': 2510, 'cosmo_no_shield_chain': 2510})
        self.assertGreaterEqual(sum(len(v) for v in doc['foes'].values()), 300)

    def test_generated_mapping_matches_client(self):
        tables = os.environ.get('COSMO_TABLES')
        if not tables:
            self.skipTest('COSMO_TABLES 없음')
        from tools.build_chain_se import build_fixed, build_foes
        from tools.client_view import materialize
        doc = json.loads((ROOT / 'data/chain_se.json').read_text(encoding='utf8'))
        with tempfile.TemporaryDirectory() as tmp:
            materialize(tables, tmp)
            foes, report = build_foes(tmp)
        self.assertEqual(foes, doc['foes'])
        self.assertEqual(report, doc['report'])
        self.assertEqual(build_fixed(tables), doc['fixed'])

    def test_foe_chain_is_queued_then_applied(self):
        b, a, f, ln, ctx = self.setup_foe()
        b.run_line(f, ln, ctx)
        self.assertEqual(a.taken, 0)
        self.assertEqual([r[0] for r in b._chain_damage], [2510])
        b.flush_add_damage()
        self.assertGreater(a.taken, 0)
        self.assertEqual(b.rule_hits['chain_timing_applied'], 1)
        self.assertFalse(b._chain_damage or b._add_order)

    def test_one_queue_orders_fixed_and_chain_groups(self):
        b = battle([unit('a')], [unit('boss', hp=10**6), unit('two', hp=10**6)])
        a = b.allies[0]
        boss, two = b.foes
        b._belgras_damage.append((boss, 100)); b.queue_add('belgras', b._belgras_damage[-1])
        for bid, v, amt in ((10172, boss, 7), (2510, boss, 3), (2510, two, 4), (2500, two, 9)):
            b._chain_damage.append((bid, a, v, amt, True, False, (amt, 1)))
            b.queue_add('chain', b._chain_damage[-1])
        seen = []
        with patch.object(b, '_apply_chain_amount', lambda o, t, amt, *r: seen.append(amt)), \
                patch.object(b, '_belgras_one', lambda t, amt: seen.append(amt)):
            b.flush_add_damage()
        # 2510 묶음(대상 2) → 대상 1인 묶음은 BuffId 오름차순 2500, 2509(벨그라스), 10172.
        self.assertEqual(seen, [3, 4, 9, 100, 7])
        self.assertFalse(b._chain_damage or b._belgras_damage or b._add_order)

    def test_dead_at_start_and_retarget(self):
        b = battle([unit('a')], [unit('x', hp=10**6), unit('y', hp=10**6), unit('z', hp=10**6)])
        a = b.allies[0]
        x, y, z = b.foes
        b.kill(z, a)
        rows = [(1, a, x, 5, True, False, (5, 1)), (1, a, y, 6, True, False, (6, 1)),
                (2, a, x, 7, True, True, (7, 1)), (3, a, x, 8, True, False, (8, 1)),
                (4, a, z, 9, True, True, (9, 1))]
        for r in rows:
            b._chain_damage.append(r); b.queue_add('chain', r)
        seen = []

        def record(owner, target, amount, *rest):
            seen.append((target.name, amount))
            if amount == 6:
                b.kill(x, a)        # 앞 묶음 처리 도중 사망
        with patch.object(b, '_apply_chain_amount', record):
            b.flush_add_damage()
        # 재선택 SE(2)는 같은 편 생존자 y로, 재선택 없는 SE(3)는 건너뜀, 시작 때 죽은 z(4)는 재선택도 안 함.
        self.assertEqual(seen, [('x', 5), ('y', 6), ('y', 7)])
        self.assertEqual(b.rule_hits['chain_timing_retarget'], 1)

    def test_retarget_recomputes_with_new_target(self):
        # 도중 사망 경로: 첫 항목이 x를 죽인 뒤 같은 x 대상 재선택 항목의 값은 새 대상 기준으로 다시 계산.
        b = battle([unit('a', atk=1000)], [unit('x', hp=10**6), unit('y', hp=10**6, df=0)])
        a = b.allies[0]
        x, y = b.foes
        rows = [(1, a, x, 1, True, False, (1, 1)), (2, a, x, 999999, False, True, (1000.0, 0.5))]
        for r in rows:
            b._chain_damage.append(r); b.queue_add('chain', r)
        calls = []
        orig = b._apply_chain_amount

        def kill_first(owner, target, amount, *r):
            calls.append((target.name, amount))
            if amount == 1:
                b.kill(x, a)
                return None
            return orig(owner, target, amount, *r)
        with patch.object(b, '_apply_chain_amount', kill_first):
            b.flush_add_damage()
        expect = b._chain_amount(a, y, 1000.0, 0.5, None, a.mods(), False)
        self.assertEqual(calls, [('x', 1), ('y', expect)])

    def cosmo(self, boss):
        from battlesim.api import _norm_party
        from battlesim.starsavior.data import get_db
        from cosmo_fixture import use_1022
        use_1022()   # 시즌 1022 fixture(벨그라스·카넬리아 모델 회귀, cosmo_raid_test 와 같음)
        waves, meta = C.build_waves(boss, 3, 18)
        defs, _ = _norm_party({'units': ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria']}, get_db(), 'fixed', 'standard')
        b = Battle(defs, waves, random.Random(1), mc=dict(MC_OPTS, cosmo_raid_boss='on'),
                   leader=0, turn_limit=meta['turn_limit'], battle_mode='boss_kill')
        b.spawn_wave()
        return b

    def test_cosmo_punish_uses_shared_queue(self):
        b = self.cosmo('카넬리아')
        boss = b.gb.boss
        for u in b.allies:
            give(u, '공격력 감소', {'공격력%': -30}, src=boss, harmful=True)
        b.cast(boss, boss.d.skills['궁극기'])
        punish = [r for r in b._chain_damage if r[0] == chain_se.fixed('cosmo_punish')]
        self.assertEqual(len(punish), len(b.allies))
        kinds = []
        orig = b.apply_damage
        b.apply_damage = lambda a, v, dmg, kind, **kw: (kinds.append(kind), orig(a, v, dmg, kind, **kw))[1]
        b.flush_add_damage()
        self.assertEqual(b.gb.stats['punish'], len(b.allies))
        self.assertGreaterEqual(kinds.count('chain'), len(b.allies))
        self.assertFalse(b._chain_damage)

    def test_cosmo_fixed_damage_joins_queue(self):
        b = self.cosmo('벨그라스')
        boss = b.gb.boss
        b.gb.pending_damage.append((boss, 5000)); b.queue_add('cosmo_fixed', b.gb.pending_damage[-1])
        a = b.allies[0]
        b._chain_damage.append((2510, a, boss, 1, True, False, (1, 1))); b.queue_add('chain', b._chain_damage[-1])
        order = []
        with patch.object(b.gb, 'apply_pending', lambda t, d: order.append(('fixed', d))), \
                patch.object(b, '_apply_chain_amount', lambda o, t, amt, *r: order.append(('chain', amt))):
            b.flush_add_damage()
        self.assertEqual(order, [('fixed', 5000), ('chain', 1)])   # 둘 다 대상 1: BuffId 2509 < 2510
        self.assertEqual(b.gb.pending_damage, [])

    def test_cosmo_no_shield_chain_joins_punish_group(self):
        # SE9402501(EX SET_25) = BI_ADD_DAMAGE_1 2510, 응징 SE9403101 과 같은 BuffId → 같은 큐·같은 묶음(NKM:6253-6257)
        names = ['보호막', '보호막(해제불가)']
        b = self.cosmo('카넬리아')
        boss = b.gb.boss
        b.gb.fx['no_shield_chain'] = {'atkRate': 30.0, 'names': names}
        kinds = []
        orig = b.apply_damage
        b.apply_damage = lambda a, v, dmg, kind, **kw: (kinds.append(kind), orig(a, v, dmg, kind, **kw))[1]
        b.cast(boss, boss.d.skills['기본기'])
        self.assertEqual(b.gb.stats['no_shield_chain'], 1)
        self.assertNotIn('chain', kinds)                      # 시전 중 즉시 넣지 않음
        alive = b.alive(0)
        self.assertEqual([(r[0], r[2]) for r in b._chain_damage], [(2510, v) for v in alive])
        b.queue_punish(boss, alive[:1], 0.3, None)            # 응징 1건 뒤에 등록
        order = []
        with patch.object(b, '_apply_chain_amount', lambda o, t, amt, *r: order.append(t)):
            b.flush_add_damage()
        self.assertEqual(order, alive + alive[:1])             # 한 묶음(대상 수 = 생존 아군 수), 등록순
        self.assertFalse(b._chain_damage or b._add_order)

    def test_dot_death_turn_still_flushes_queue(self):
        # NKM:13919-13935: 차례 유닛이 행동 불가·사망이어도 OBF_2606 → OBF_4586(추가 피해) 처리
        b, a, f, ln, ctx = self.setup_foe()
        b.run_line(f, ln, ctx)
        self.assertEqual(a.taken, 0)
        with patch.object(b, '_tick_dot_hot', lambda u: b.kill(u, None) if u is f else None):
            b.act(f)
        self.assertTrue(f.dead)
        self.assertGreater(a.taken, 0)
        self.assertEqual(b.rule_hits['add_damage_dead_turn'], 1)
        self.assertFalse(b._chain_damage or b._add_order)

    def test_turn_flushes_unified_queue(self):
        b, a, f, ln, ctx = self.setup_foe()
        with patch.object(b, 'flush_add_damage', wraps=b.flush_add_damage) as fl:
            b.act(f)
        self.assertTrue(fl.called)
        self.assertGreater(a.taken, 0)


def mutations():
    cases = [
        (Battle, 'flush_add_damage', '(-len({r[3] for r in groups[k]}), k)', '(k, 0)', 'test_one_queue_orders_fixed_and_chain_groups'),
        (Battle, 'flush_add_damage', 'if target in dead_at_start:', 'if False:', 'test_dead_at_start_and_retarget'),
        (Battle, 'flush_add_damage', 'self.alive(target.side) if retarget else []', '[]', 'test_dead_at_start_and_retarget'),
        (Battle, 'flush_add_damage', 'amount = self._chain_amount(owner, target, val, coef, None, owner.mods(), true)', 'pass',
         'test_retarget_recomputes_with_new_target'),
        (Battle, 'chain', "foe=True", 'foe=False', 'test_foe_chain_is_queued_then_applied'),
        (Battle, '_add_entries', "out.append((kind, e, chain_se.fixed('belgras_hyper'), e[0]))",
         "out.append((kind, e, 99999, e[0]))", 'test_cosmo_fixed_damage_joins_queue'),
        (C.Controller, 'skill_start', 'self.b.queue_punish(', 'None and self.b.queue_punish(', 'test_cosmo_punish_uses_shared_queue'),
        (Battle, '_act_turn', 'self.flush_add_damage()', 'pass', 'test_turn_flushes_unified_queue'),
        (C.Controller, 'after_cast', "b.queue_punish(boss, b.alive(0), coef, ctx, se='cosmo_no_shield_chain')", 'pass',
         'test_cosmo_no_shield_chain_joins_punish_group'),
        (Battle, '_dead_turn_add_damage', 'self.flush_add_damage()', 'pass', 'test_dot_death_turn_still_flushes_queue'),
    ]
    for cls, method, old, new, test in cases:
        original = getattr(cls, method)
        source = textwrap.dedent(inspect.getsource(original))
        assert old in source, (method, old)
        ns = {}
        exec(source.replace(old, new), original.__globals__, ns)
        run = lambda: unittest.TextTestRunner(stream=io.StringIO()).run(ChainQueueTest(test))   # noqa: E731
        assert run().wasSuccessful(), test
        with patch.object(cls, method, ns[method]):
            result = run()
        assert result.failures and not result.errors, (test, method, result.errors)
        print(test, method, 'mutation rejected')


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
