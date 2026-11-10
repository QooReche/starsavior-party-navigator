# -*- coding: utf-8 -*-
"""마이크로 최적화의 비트 동일성·실제 경로·의도적 결함 검출 시험."""
import hashlib
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from battlesim import api, mc, simulate
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import Line, _map_prop
from cosmo_speed_reference import mode, old_dirty, old_line_kind

PARTIES = (
    ['wedding-carmen', 'bunny-charlotte', 'amora', 'tyria'],
    ['carmen', 'frey', 'ceres', 'bell'],
    ['luna', 'carnelia', 'gwen', 'smile'],
)


def bits(value):
    if isinstance(value, float):
        return value.hex()
    if isinstance(value, dict):
        return {k: bits(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [bits(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(bits(value), sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def run_case(party, boss, level, seed):
    states = []
    original = mc.Battle.run

    def traced(b):
        result = original(b)
        states.append((b.progress(), b.rng.getstate(), [
            [getattr(u, key) for key in ('hp', 'maxhp', 'gauge', 'dmg', 'taken', 'healed',
                                        'healed_raw', 'shield_given', 'actions', 'dead', 'cd')]
            for u in b.allies + b.all_foes]))
        return result

    with patch.object(mc.Battle, 'run', traced):
        r = simulate({'units': party, 'leader': 0},
                     {'cosmo_raid': {'boss': boss, 'step': 3, 'level': level}},
                     {'build': 'standard', 'seed': seed, 'n_runs': 1, 'timeline': True})
    r.pop('runtime_ms_per_run')
    assert r['outcome']['progress'] > 0, (party, boss, level, seed)
    assert r['timeline'] and len(r['timeline']) < 3000  # 기록 상한 때문에 비교가 잘리지 않음
    return (r['cosmo_raid']['score_runs'], bits(r['prog_runs']), digest(r['timeline']), digest(r), digest(states))


def unit():
    defs, _ = api._norm_party(['amora'], get_db(), 'fixed', 'standard')
    b = mc.Battle(defs, [], random.Random(1))
    return b, b.allies[0]


class CosmoSpeedTest(unittest.TestCase):
    def test_each_optimization_exact(self):
        """3팀 × 3보스 × 3난이도 × 3시드. 각 최적화 단독·동시 적용을 옛 경로와 비교."""
        cases = [(p, b, lv, seed) for p in PARTIES for b in ('belgras', 'tyria', 'carnelia')
                 for lv in (0, 6, 12) for seed in (1, 7, 29)]
        with mode('baseline'):
            api.clear_engine_caches()
            reference = [run_case(*c) for c in cases]
        for name in ('dirty', 'line', 'all'):
            with self.subTest(mode=name), mode(name):
                api.clear_engine_caches()
                mc._react_line_kind.cache_clear()
                self.assertEqual(reference, [run_case(*c) for c in cases])

    def test_dirty_clips_immediately_but_defers_mods(self):
        b, u = unit()
        b.put_eff(u, 'HP', {'생명력%': 30, '공격력%': 50})
        u.hp = u.maxhp
        u.eff['HP'].props['생명력%'] = -25
        b.dirty(u)
        self.assertIsNone(u._m, 'dirty가 전체 mods를 즉시 계산하면 실패')
        self.assertEqual(u.hp, float(int(u.maxhp0 * .75)))
        self.assertEqual(u.hp, u.maxhp)
        self.assertEqual(u.mods()['atkp'], .5)
        clipped = u.hp
        u.eff['HP'].props['생명력%'] = 40
        b.dirty(u)
        self.assertEqual(u.hp, clipped)  # 줄었다 늘어도 HP를 복원하지 않음

    def test_dirty_matches_full_mods_boundaries(self):
        # stage fx와 sd의 생명력%는 hpp_buff에 포함하지 않으며 sd_hp는 별도 가산함.
        for banned in (False, True):
            for refuse in (False, True):
                for enabled in ('off', 'on'):
                    b, u = unit()
                    b.mc['buff_maxhp'] = enabled
                    u.ban_refuse = refuse
                    u.fx = {'생명력%': 90}
                    u.sd = {'생명력%': 80}
                    u.sd_hp = -.17
                    for i, (val, stacks, cat) in enumerate(((30.1, 2, 'buff'), (-7.7, 3, 'debuff'), (200, 0, 'buff'))):
                        b.put_eff(u, str(i), {'생명력%': val}, maxs=3, add=stacks, cat=cat)
                    if banned:
                        b.put_eff(u, '강화 불가', {}, cat='debuff')
                    for value in (30.1, -999.9, 0, 77.7):
                        u.eff['0'].props['생명력%'] = value
                        u.hp = u.maxhp0 * 10
                        old_dirty(b, u)
                        expected = u.hp.hex()
                        u.hp = u.maxhp0 * 10
                        b.dirty(u)
                        self.assertEqual(u.hp.hex(), expected)
                    self.assertEqual(_map_prop('생명력%'), ('hpp', None))

    def test_reaction_cache_values_mutation_and_bound(self):
        mc._react_line_kind.cache_clear()
        ln = Line('턴 시작 시: 자신에게 공격력% +10%', '기본기', 'active')
        for trig in [k + ' 추가 조건' for k, _ in mc.REACT_TRIG] + ['', None, '알 수 없음']:
            for phase in ('피해 처리 직전', '피해 처리 후', '피격 시', '웨이브 시작 시', ''):
                for kind in ('unmodeled', 'battle_start', 'own_pre'):
                    ln.kind, ln.phase, ln.trig = kind, phase, trig
                    self.assertEqual(mc.line_kind(ln), old_line_kind(ln))
        for i in range(1024):
            mc._react_line_kind('', str(i))
        mc._react_line_kind('', '1023')
        self.assertLessEqual(mc._react_line_kind.cache_info().currsize, 512)
        self.assertGreater(mc._react_line_kind.cache_info().hits, 0)

    def test_corrupted_paths_are_detected(self):
        """동일성 검사에 쓰는 같은 assertion이 의도적 결함으로 실패하는지 확인."""
        args = (PARTIES[0], 'belgras', 0, 7)
        reference = run_case(*args)

        def broken_dirty(b, u):
            u._m = None
            u.hp = min(u.hp, 1.0)  # HP 절단 식 훼손

        for target, name, broken in ((mc.Battle, 'dirty', broken_dirty),
                                     (mc, '_react_line_kind', lambda phase, trig: 'unmodeled')):
            with self.subTest(path=name), patch.object(target, name, broken):
                with self.assertRaises(AssertionError):
                    self.assertEqual(reference, run_case(*args))


if __name__ == '__main__':
    unittest.main(verbosity=2)
