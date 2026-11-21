"""PC 26752678: IsUniqueID 버프 재부여는 새 객체를 더한다(작전 42-12 공허선도자 〈영혼 구속〉).

NKM:4331-4336 (UniqueIdStackMax 검사만, 옛 객체 유지), 4505-4518 (IsUniqueID면 옛 객체 제거 생략),
4520-4528 (새 객체 삽입). 표: CLIENT_BUFF_TEMPLET BI_BELLWETHER_MANE_1 IsUniqueID·TurnInfinite·NV_RATE_HP -1500.
"""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit
from battlesim.mc import Battle, Ctx, buff_flags
from battlesim.starsavior.parser import Line

SOUL = '[스킬 사용 후] 적 전체에게 〈영혼 구속〉 (지속 무한 / 생명력% -15%) {효과 적중 판정}'


class UniqueIdStackTest(unittest.TestCase):
    def apply(self, mc=None, times=2):
        b = battle([unit('a', hp=100000), unit('b', hp=100000)], [unit('boss')], mc=mc)
        boss = b.foes[0]
        ln = Line(SOUL, '특수기', 'active')
        with patch.object(Battle, 'roll_hit', lambda *a, **k: True):
            for _ in range(times):
                b.run_line(boss, ln, Ctx(boss, boss, None))
        return b

    def test_default_is_client(self):
        flags = buff_flags()['unique_id']
        self.assertEqual(flags['영혼 구속'], 'inf')
        # 기존 독립 상한 규칙과 같은 표 값(UniqueIdStackMax).
        self.assertEqual((flags['파사인'], flags['상쾌한 기분(해제불가)']), (3, 5))

    def test_soul_bind_objects_accumulate(self):
        b = self.apply(times=3)
        for a in b.allies:
            self.assertEqual(a.stack('영혼 구속'), 3)
            self.assertEqual(len(a.eff['영혼 구속'].inst), 3)
            self.assertEqual(a.maxhp, math.floor(a.maxhp0 * (1 - 0.45)))
            self.assertEqual(a.n_harmful(), 3)
        self.assertGreater(b.rule_hits['unique_id_stack'], 0)

    def test_dispel_counts_objects(self):
        b = self.apply(times=3)
        a = b.allies[0]
        b.run_line(a, Line('[스킬 사용 후] 아군 전체에게 (약화효과 해제) 효과 2개 해제', '궁극기', 'active'), Ctx(a, a, None))
        self.assertEqual(a.stack('영혼 구속'), 1)
        self.assertEqual(a.maxhp, math.floor(a.maxhp0 * (1 - 0.15)))
        # 개수 없는 해제(BuffDeleteCount 0 = 전부, NKM:4247)는 남은 객체를 모두 지운다.
        b.run_line(a, Line('[스킬 사용 후] 아군 전체에게 〈디버프 해제〉 (약화효과 해제)', '특수기', 'active'), Ctx(a, a, None))
        for x in b.allies:
            self.assertFalse(x.has('영혼 구속'))
            self.assertEqual(x.maxhp, x.maxhp0)

    def test_non_unique_name_unchanged(self):
        b = battle([unit('a', hp=100000)], [unit('boss')])
        boss = b.foes[0]
        ln = Line('[스킬 사용 후] 적 전체에게 〈방어력 감소〉 (2턴 / 방어력% -30%) {효과 적중 판정}', '궁극기', 'active')
        self.assertNotIn('방어력 감소', buff_flags()['unique_id'])
        with patch.object(Battle, 'roll_hit', lambda *a, **k: True):
            for _ in range(3):
                b.run_line(boss, ln, Ctx(boss, boss, None))
        self.assertEqual(b.allies[0].stack('방어력 감소'), 1)


class RandomBasicNotSelfTest(unittest.TestCase):
    """잠재력 «다른 아군 1명에게 25% 확률로 기본기 추가 발동»(POTEN_PASSIVE_4040101): AutoTargetId 5 = IsAllyOneNotSelf
    (NKM:7566-7568), 결과 0명이면 목록 유지(7758-7763), 단일 대상 난수는 2명 이상일 때만(7170-7175)."""

    def actors(self, n_allies, mc=None, trials=60):
        b = battle([unit('a%d' % i) for i in range(n_allies)], [unit('boss')], mc=mc)
        owner = b.allies[0]
        ln = Line('[스킬 사용 후] (조건: 내 공격 후 [사용 스킬: 기본기; 결과: 치명타; 내 턴: 예]) 다른 아군 1명에게 '
                  '25% 확률로 기본기 추가 발동 {발동 후 1턴 재발동 불가}', '잠재력', 'passive')
        ln.eff = dict(kind='random_ally_basic', chance=1.0)
        seen = []
        with patch.object(Battle, 'cast', lambda self, u, sk, **kw: seen.append(u.name)):
            for _ in range(trials):
                b._exec_line(owner, ln, Ctx(owner, owner, owner.d.skills['기본기']))
        return b, seen

    def test_client_excludes_caster(self):
        b, seen = self.actors(3)
        self.assertEqual(len(seen), 60)
        self.assertNotIn('a0', seen)
        self.assertEqual(set(seen), {'a1', 'a2'})
        self.assertGreater(b.rule_hits['random_basic_not_self'], 0)

    def test_alone_keeps_caster(self):
        _, seen = self.actors(1, trials=5)
        self.assertEqual(seen, ['a0'] * 5)


if __name__ == '__main__':
    unittest.main()
