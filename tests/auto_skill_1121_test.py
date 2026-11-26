# -*- coding: utf-8 -*-
"""오토 스킬 사용 교정(2026-11-21, docs/auto_skill_1121.md). python -X utf8 -I tests/auto_skill_1121_test.py

1. 오토 회복 조건 AllyHpRateLessThan의 float32 경계·임계 0(PC 26935738 NKM:7484-7500,2191-2198).
2. 오토(nova_policy=auto)는 노바 버스트를 쓰지 않음 — 클라 확정이라 assumptions_used에서 빠지고,
   사람 운영 대체 정책(manual/heal)을 고르면 assumed로 보고함.
3. 비공개 디컴파일이 있으면 근거 줄의 핵심 표지를 확인함(없으면 그 시험만 건너뜀).
"""
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim import api
from battlesim.api import _CustomFoe
from battlesim.mc import Battle, _float32_bp
from battlesim.metrics import unit_def
from battlesim.rules import DEFAULT_OPTS, MC_OPTS

# float64로는 int(9377/12501×10000)=7500(75% 이하), 클라 float32로는 7501(초과).
EDGE_HP, EDGE_MAX = 9377, 12501


def battle(**mc):
    foe = _CustomFoe(dict(name='target', hp=10**8, atk=1, **{'def': 1000}, spd=1), 0)
    b = Battle([unit_def('frey'), unit_def('gwen')], [[foe]], random.Random(3),
               opts={'coop': False}, mc=mc or None)
    b.spawn_wave()
    return b


class AutoCondHpTest(unittest.TestCase):
    def test_edge_value_is_real(self):
        self.assertEqual(int(EDGE_HP / EDGE_MAX * 10000), 7500)
        self.assertEqual(_float32_bp(EDGE_HP, EDGE_MAX), 7501)

    def _set(self, b, hp, maxhp):
        for u in b.allies:
            u.maxhp, u.hp = maxhp, maxhp
        b.allies[1].hp = hp

    def test_client_float32_boundary(self):
        b = battle()
        self._set(b, EDGE_HP, EDGE_MAX)
        self.assertFalse(b.auto_cond_ok(b.allies[0], ['ally_hp_le_bp', 7500]))
        self.assertGreater(b.rule_hits['auto_cond_hp_float32'], 0)
        # 같은 상태에서 프레이 특수기(규칙 2) 조건이 거짓이므로 오토는 회복 대신 다른 스킬을 고른다.
        frey = b.allies[0]
        sk, _ = b.choose_skill(frey)
        self.assertNotEqual(sk.slot, '특수기')
        self._set(b, EDGE_HP - 1, EDGE_MAX)
        self.assertTrue(b.auto_cond_ok(frey, ['ally_hp_le_bp', 7500]))
        sk, target = b.choose_skill(frey)
        self.assertEqual((sk.slot, target), ('궁극기', None))   # 궁극기(아군 전체) 먼저, 같은 조건

    def test_zero_threshold_is_false(self):
        b = battle()
        self._set(b, 1, 10**6)   # int(비율×10000) = 0
        self.assertFalse(b.auto_cond_ok(b.allies[0], ['ally_hp_le_bp', 0]))


class NovaPolicyTest(unittest.TestCase):
    def test_auto_default_not_assumption(self):
        self.assertEqual(DEFAULT_OPTS['nova_policy'], 'auto')
        rules = {x['rule'] for x in api.assumptions_used(MC_OPTS, DEFAULT_OPTS)}
        self.assertNotIn('opts.nova_policy', rules)

    def test_manual_or_heal_reported_as_assumed(self):
        for policy in ('manual', 'heal'):
            out = api.assumptions_used(MC_OPTS, dict(DEFAULT_OPTS, nova_policy=policy))
            row = [x for x in out if x['rule'] == 'opts.nova_policy']
            self.assertEqual(len(row), 1, policy)
            self.assertEqual((row[0]['value'], row[0]['grade']), (policy, 'assumed'))

    def test_auto_never_bursts(self):
        foe = _CustomFoe(dict(name='target', hp=10**8, atk=1, **{'def': 1000}, spd=1), 0)
        b = Battle([unit_def('gwen'), unit_def('frey')], [[foe]], random.Random(5),
                   opts={'coop': False, 'nova_policy': 'auto'})
        b.spawn_wave()
        b.team_nova = 12
        for u in b.allies:
            u.nova = 12
        gwen = b.allies[0]
        for slot in ('궁극기', '특수기', '기본기'):
            self.assertFalse(b.cast(gwen, gwen.d.skills[slot]).nb)
        self.assertEqual(sum(b.nova_bursts.values()), 0)


def _static():
    root = os.environ.get('STARSAVIOR_STATIC')
    return os.path.join(root, 'decompiled') if root else None


@unittest.skipUnless(_static() and os.path.isdir(_static() or ''), 'STARSAVIOR_STATIC 미설정')
class ClientEvidenceTest(unittest.TestCase):
    """근거 줄 번호가 디컴파일 갱신으로 밀리면 실패해 문서·규칙 source를 같이 고치게 한다."""

    def _lines(self, asm):
        path = os.path.join(_static(), asm, asm + '.decompiled.cs')
        with open(path, encoding='utf-8') as f:
            return f.read().split('\n')

    def test_nkm_lines(self):
        nkm = self._lines('NKM')
        self.assertIn('AllyHpRateLessThan', nkm[7491 - 1])
        self.assertIn('10000f', nkm[7495 - 1])
        self.assertIn('NST_ACTIVE', nkm[7107 - 1])
        level_up = [i + 1 for i, s in enumerate(nkm) if s.strip().endswith('.OBF_21608.OBF_22416();')]
        self.assertEqual(level_up, [14456])   # 노바 버스트 레벨 증가는 요청 처리기 한 곳뿐
        self.assertIn('OBF_33134(OBF_3346, OBF_0173: true)', nkm[13088 - 1])

    def test_nkc_lines(self):
        nkc = self._lines('NKC')
        self.assertIn('NBIT_NOVA_BURST', nkc[153985 - 1])
        self.assertIn('TS_WAIT_SKILL_INPUT', nkc[153985 - 1])
        self.assertIn('new OBF_33043()', nkc[27288 - 1])
        self.assertIn('TS_IDLE', nkc[27009 - 1])


if __name__ == '__main__':
    unittest.main()
