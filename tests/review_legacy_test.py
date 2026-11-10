"""11/10 리뷰 R1/R2. --history: 93d300f 실제 엔진 비교, --mutations: 결함 재주입."""
import inspect
import io
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import textwrap
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import unit
from battlesim import mc as engine
from battlesim.rules import MC_RULES
from battlesim.starsavior.parser import Line


def historical(ref):
    source = subprocess.check_output(
        ['git', 'show', f'{ref}:battlesim/mc.py'], cwd=ROOT).decode('utf8')
    module = types.ModuleType(f'battlesim._review_{ref}')
    module.__package__ = 'battlesim'
    exec(compile(source, f'{ref}:battlesim/mc.py', 'exec'), module.__dict__)
    rules = json.loads(subprocess.check_output(
        ['git', 'show', f'{ref}:battlesim/rules/default.json'], cwd=ROOT))['mc']
    # 옛 키는 당시 기본값, 이후 추가된 키만 legacy로. 옛 결과 해시는 수정하지 않음.
    overrides = {key: rules.get(key, {}).get('value', row.get('legacy', row.get('value')))
                 for key, row in MC_RULES.items() if 'value' in row}
    return module.Battle, overrides


def state(b):
    return (b.result, b.progress(), b.timeline, b.rng.getstate(), b.team_nova,
            [(u.name, u.hp, u.gauge, u.extra_turn, u.dead, u.actions,
              u.dmg, u.taken, u.healed, dict(u.cd), dict(u.cast_count)) for u in b.allies + b.foes])


def purify_case(cls=engine.Battle, overrides=None, near_cap=False):
    b = cls([unit('a')], [[unit('f', hp=10**8)]], random.Random(7),
            mc=dict(overrides or {}, purify_nova_scope='main_only'),
            opts={'coop': False, 'nova': False}, timeline=True,
            break_skill={'name': '행성 정화'}, max_turns=3)
    b.spawn_wave()
    a, f = b.allies[0], b.foes[0]
    b.break_points = 3
    b._use_break_skill(a)
    b.team_nova = 0
    if near_cap:
        while len(b.timeline) < 2992:
            b.log(padding=True)
    b.cast(a, a.d.skills['기본기'], target=f)
    assert b.team_nova == 1 and f.taken > 0
    b.cast(a, a.d.skills['기본기'], extra=True, via='coop', target=f)
    assert b.team_nova == 1
    b.log(review_tail=True)
    b.run()
    assert b.progress() > 0
    return b


def wave_case(cls=engine.Battle, overrides=None, *, extra='clear', gauge='keep',
              carry='keep', reserved=False):
    b = cls([unit('a'), unit('dead')], [[unit('first')], [unit('second', hp=10**8)]],
            random.Random(7), mc=dict(overrides or {}, wave_extra_turn=extra,
            wave_ally_gauge=gauge, wave_carry=carry), opts={'coop': False}, timeline=True,
            max_turns=3)
    b.spawn_wave()
    a, dead = b.allies
    b.kill(dead, b.foes[0])
    a.extra_turn, a.gauge = reserved, 10000 if reserved else 4321
    dead.extra_turn, dead.gauge = True, 123
    b.spawn_wave()
    return b


class ReviewLegacyTest(unittest.TestCase):
    def test_purify_legacy_timeline_and_cap(self):
        for cap in (False, True):
            b = purify_case(near_cap=cap)
            self.assertFalse(any('purify_nova' in row for row in b.timeline))
            self.assertTrue(any('review_tail' in row for row in b.timeline))
            if cap:
                self.assertEqual(len(b.timeline), 3000)

    def test_wave_gauge_and_reservation_independent(self):
        for extra, gauge, carry, reserved in itertools.product(
                ('clear', 'keep'), ('keep', 'reset'), ('keep', 'client'), (False, True)):
            with self.subTest(extra=extra, gauge=gauge, carry=carry, reserved=reserved):
                b = wave_case(extra=extra, gauge=gauge, carry=carry, reserved=reserved)
                a, dead = b.allies
                retained = reserved and extra == 'keep'
                expected = 10000 if retained else (4321 if not reserved and gauge == 'keep' else 0)
                self.assertEqual((a.extra_turn, a.gauge), (retained, expected))
                self.assertEqual((dead.extra_turn, dead.gauge), (True, 123))
                self.assertEqual(b.rule_hits['wave_extra_turn'], int(reserved and extra == 'clear'))
                b.run()
                self.assertGreater(b.progress(), .5)

    def test_default_reset_before_wave_start(self):
        # 기본 clear/reset은 예약 없는 유닛도 이벤트 전에 0. 새 이벤트 게이지는 옛 후처리 유지.
        b = wave_case()
        a = b.allies[0]
        a.d.lines = [Line('[웨이브 시작 시] 자신에게 〈추가 턴〉', '고유 패시브', 'passive')]
        b.mc.update(wave_extra_turn='clear', wave_ally_gauge='reset')
        b.waves.append([unit('third')])
        seen = []
        original = b.run_line
        def observe(u, line, ctx):
            seen.append(u.gauge)
            return original(u, line, ctx)
        with patch.object(b, 'run_line', observe):
            b.spawn_wave()
        self.assertEqual(seen, [0])
        self.assertTrue(a.extra_turn)
        self.assertEqual(a.gauge, 0)  # 추가 턴의 10000 표시는 스케줄러가 붙임.


def compare_history():
    old, overrides = historical('93d300f')
    for cap in (False, True):
        a = purify_case(old, overrides, cap)
        b = purify_case(engine.Battle, overrides, cap)
        assert state(a) == state(b), ('purify', cap)
    count = 0
    for carry, gauge, reserved in itertools.product(('keep', 'client'), ('keep', 'reset'), (False, True)):
        # 예약 없는 아군은 새 clear를 켠 채로도 옛 gauge legacy를 재현해야 함.
        for extra in (('keep',) if reserved else ('keep', 'clear')):
            args = dict(extra=extra, gauge=gauge, carry=carry, reserved=reserved)
            a, b = wave_case(old, overrides, **args), wave_case(engine.Battle, overrides, **args)
            assert state(a) == state(b), args
            a.run()
            b.run()
            assert a.progress() > .5 and state(a) == state(b), args
            count += 1
    print(f'93d300f legacy: purify 2 + wave {count}, 상태·진행도·시간선·난수 일치')


def mutations():
    cases = [
        ('cast', "if purify == 'all_casts':", 'if True:', 'test_purify_legacy_timeline_and_cap'),
        ('spawn_wave', 'self._reset_wave_gauge()',
         'exec("for x in self.alive(0): x.gauge = 0.0")', 'test_wave_gauge_and_reservation_independent'),
        ('spawn_wave', 'self._reset_wave_gauge()', 'pass', 'test_default_reset_before_wave_start'),
    ]
    for method, before, after, test in cases:
        source = textwrap.dedent(inspect.getsource(getattr(engine.Battle, method)))
        assert before in source
        namespace = dict(engine.__dict__)
        exec(source.replace(before, after, 1), namespace)
        def run():
            return unittest.TextTestRunner(stream=io.StringIO()).run(ReviewLegacyTest(test))
        assert run().wasSuccessful(), test
        with patch.object(engine.Battle, method, namespace[method]):
            result = run()
        assert result.failures and not result.errors, (test, result.errors)
        print(test, '결함 주입 시 assertion 실패 확인')


if __name__ == '__main__':
    if '--history' in sys.argv:
        compare_history()
    elif '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
