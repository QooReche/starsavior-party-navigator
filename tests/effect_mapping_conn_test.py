"""효과 줄 ↔ 원형 SE 기계 대조(tools/effect_mapping_audit.py)와 확률 이번 스킬 보정(mc.local_chance); --mutations."""
import inspect
import io
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit   # noqa: E402
from battlesim.mc import Battle, Ctx   # noqa: E402
from battlesim.rules import MC_OPTS   # noqa: E402
from battlesim.starsavior.parser import Line   # noqa: E402
from tools import effect_mapping_audit as A   # noqa: E402

RAW = '[스킬 사용 시작 시] 자신에게 75% 확률로 능력치 보정 피해 증가 +30% {이번 스킬에만 적용}'


class FakeTables:
    buff = {'BI_X': {'EffectHitCheck': True}, 'BI_NOHIT': {'EffectHitCheck': False}}


class LocalChanceTest(unittest.TestCase):
    def run_local(self, mode, roll):
        b = battle([unit('a')], [unit('f')], mc={'local_chance': mode})
        a = b.allies[0]
        ctx = Ctx(a, a, a.d.skills['기본기'])
        ln = Line(RAW, '기본기', 'active')
        with patch.object(b.R(0), 'random', lambda: roll):
            b.run_line(a, ln, ctx)
        return ctx.inc, b.rule_hits['local_chance']

    def test_default(self):
        self.assertEqual(MC_OPTS['local_chance'], 'roll')

    def test_parser_keeps_expected_value_and_chance(self):
        eff = Line(RAW, '기본기', 'active').eff
        self.assertEqual((eff['val'], eff['chance']), (22.5, 0.75))
        self.assertNotIn('chance', Line(RAW.replace('75% 확률로 ', ''), '기본기', 'active').eff)

    def test_roll_applies_full_value_or_nothing(self):
        self.assertEqual(self.run_local('roll', 0.74), (0.30, 1))
        self.assertEqual(self.run_local('roll', 0.75), (0.0, 1))

    def test_legacy_expected(self):
        inc, hits = self.run_local('expected', 0.99)
        self.assertAlmostEqual(inc, 0.225)
        self.assertEqual(hits, 0)


class AuditCompareTest(unittest.TestCase):
    def test_chain_and_local_units(self):
        eff = dict(kind='chain', stat='atk', coef=0.5, damage_type='ADT_NORMAL')
        row = dict(AddDamageRate=5000, AddDamageTargetType='NSETT_SELF', AddDamageStatType='NST_ATK')
        self.assertEqual(A.compare(eff, row, FakeTables, {}), [])
        self.assertEqual(A.compare(dict(eff, coef=0.4), row, FakeTables, {})[0][0], '연쇄 계수')
        tough = Line('[스킬 사용 시작 시] 자신에게 능력치 보정 강인도 피해 +2 {이번 스킬에만 적용}', '기본기', 'active').eff
        self.assertEqual(A.compare(tough, dict(Stats=[{'NKM_STAT_TYPE_VALUE': 2}]), FakeTables, {}), [])
        local = Line(RAW, '기본기', 'active').eff
        ok = dict(Stats=[{'NKM_STAT_TYPE_RATE': 3000}], m_Condition={'m_fActiveRate': 7500})
        self.assertEqual(A.compare(local, ok, FakeTables, {}), [])
        self.assertEqual(A.compare(local, dict(ok, m_Condition={}), FakeTables, {})[0][0], '이번 스킬 보정 발동 확률')

    def test_hit_check_follows_client(self):
        eff = Line('[스킬 사용 후] 스킬 대상에게 〈공격력 감소〉 (1턴 / 공격력% -30%)', '기본기', 'active').eff
        enemy = dict(m_BuffStrID='BI_X', m_BuffTargetType='NSETT_TARGET', m_BuffLifeTurn=1)
        self.assertEqual(A.compare(eff, enemy, FakeTables, {})[0][0], '효과 적중 판정')
        # NKM:20238-20256: SE 명시 false 는 생략, 같은 편 대상은 판정 없이 적용.
        self.assertEqual(A.compare(eff, dict(enemy, EffectHitCheck=False), FakeTables, {}), [])
        self.assertEqual(A.compare(eff, dict(enemy, m_BuffTargetType='NSETT_MYTEAM_ALL'), FakeTables, {}), [])
        self.assertEqual(A.compare(eff, dict(enemy, m_BuffStrID='BI_NOHIT'), FakeTables, {}), [])

    def test_repeat_and_duration(self):
        eff = Line('[스킬 사용 후] 자신에게 〈냉각〉 (2턴 / 공격력% +1%) {최대 5중첩, 3회 부여}', '기본기', 'active').eff
        row = dict(m_BuffStrID='BI_X', m_BuffTargetType='NSETT_SELF', m_BuffLifeTurn=2, RepeatBuffCount=3)
        self.assertEqual(A.compare(eff, row, FakeTables, {}), [])
        self.assertEqual({m[0] for m in A.compare(eff, dict(row, m_BuffLifeTurn=1, RepeatBuffCount=2), FakeTables, {})},
                         {'지속 턴', '반복 부여'})

    def test_full_audit_matches_client(self):
        tables = os.environ.get('COSMO_TABLES')
        if not tables:
            self.skipTest('COSMO_TABLES 없음')
        from tools.client_view import materialize
        with tempfile.TemporaryDirectory() as tmp:
            materialize(tables, tmp)
            res = A.audit(tmp)
        self.assertEqual(res['forms'], 67)
        self.assertGreaterEqual(res['paired_lines'], 4200)
        # 짝지은 줄의 불일치는 엔진 내부 표지 이름 1건뿐(docs/allowlist_conn_1121.md).
        self.assertEqual(res['by_item'], {'버프 이름': 1})
        self.assertLessEqual(res['unpaired_lines'], 150)


def mutations():
    cases = [
        (Battle, '_exec_line', "self.mc['local_chance'] == 'roll'", 'False', LocalChanceTest, 'test_roll_applies_full_value_or_nothing'),
        (None, 'compare', "enemy_side and bool(eff.get('judge')) != hit", "bool(eff.get('judge')) != hit", AuditCompareTest,
         'test_hit_check_follows_client'),
        (None, 'compare', "mine = round(full * 100) if k == 'NKM_STAT_TYPE_RATE' else round(full)", 'mine = round(full * 100)',
         AuditCompareTest, 'test_chain_and_local_units'),
    ]
    for cls, name, old, new, case, test in cases:
        original = getattr(cls, name) if cls else getattr(A, name)
        source = textwrap.dedent(inspect.getsource(original))
        assert old in source, (name, old)
        ns = {}
        exec(source.replace(old, new), original.__globals__, ns)
        run = lambda: unittest.TextTestRunner(stream=io.StringIO()).run(case(test))   # noqa: E731
        assert run().wasSuccessful(), test
        with patch.object(cls if cls else A, name, ns[name]):
            result = run()
        assert result.failures and not result.errors, (test, result.errors)
        print(test, name, 'mutation rejected')


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main()
