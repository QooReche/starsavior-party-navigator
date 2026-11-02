"""강제 강화 추출·부여·피해 제한 회귀 시험."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from tools.build_buff_force import extract
from battlesim import mc
from battlesim.starsavior.parser import Line
from p5_test import battle, unit, give


class ForceBuffTest(unittest.TestCase):
    def test_extract_collision(self):
        rows = [dict(m_BuffStrID=str(i), m_BuffName=n, IsBuff=b, ForceApplyEffect=f)
                for i, (n, b, f) in enumerate([
                    ('yes', True, True), ('yes', True, True), ('no', True, False),
                    ('mixed', True, True), ('mixed', True, False),
                    ('category', True, True), ('category', False, True)])]
        warnings = []
        names = extract(rows, {n: {'ko': n} for n in ('yes', 'no', 'mixed', 'category')}, warnings.append)
        self.assertEqual(names, ['yes'])
        self.assertEqual(len(warnings), 2)

    def test_add_effect_modes(self):
        self.assertEqual(mc.MC_OPTS['buff_ban_force'], 'client')
        self.assertIn('조율(해제불가)', mc.FORCE_BUFF_NAMES)
        self.assertNotIn('불사', mc.FORCE_BUFF_NAMES)
        self.assertNotIn('칠흑의 잔향(해제불가)', mc.FORCE_BUFF_NAMES)
        self.assertNotIn('참극의 가시(해제불가)', mc.FORCE_BUFF_NAMES)  # 동명 충돌
        for mode in ('client', 'off'):
            b = battle([unit()], [unit()], mc={'buff_ban_force': mode})
            a = b.allies[0]
            give(a, '강화 불가', harmful=True)
            for name in ('조율(해제불가)', '공격력 증가'):
                eff = dict(name=name, dur=3, props={}, max=5, times=1)
                b.add_effect(a, a, eff, None)
            self.assertEqual(a.stack('조율(해제불가)'), int(mode == 'client'))
            self.assertNotIn('공격력 증가', a.eff)

    def test_shield_uses_same_exception(self):
        # 현재 표에 강제 보호막은 없음. 이름 분류를 주입해 보호막의 별도 경로도 검증한다.
        for mode in ('client', 'off'):
            b = battle([unit()], [unit()], mc={'buff_ban_force': mode})
            a = b.allies[0]
            give(a, '강화 불가', harmful=True)
            raw = '자신에게 〈보호막〉 (2턴) 보호막 = 자신 생명력×10%'
            line = Line('[스킬 사용 후] ' + raw, '특수기', 'active')
            with patch.object(mc, 'FORCE_BUFF_NAMES', frozenset({'보호막'})):
                b.run_special(a, line, mc.Ctx(a, a, a.d.skills['기본기']), raw)
            self.assertEqual('보호막' in a.eff, mode == 'client')
            if mode == 'client':
                self.assertGreater(a.eff['보호막'].shield, 0)

    def test_limit_new_and_existing(self):
        for mode in ('client', 'off'):
            for existing in (False, True):
                b = battle([unit()], [unit()], mc={'buff_ban_force': mode})
                a = b.allies[0]
                give(a, '바큇살')
                give(a, '강화 불가', harmful=True)
                old = {}
                if existing:
                    old = {n: give(a, n, dur=7) for n in ('불사', '칠흑의 잔향(해제불가)')}
                a.cd['특수기'] = 4
                damage, forced = b._limit_damage(a, a.hp * 2)
                self.assertEqual(forced, a.maxhp * .01)
                self.assertNotIn('바큇살', a.eff)
                self.assertEqual(a.cd['특수기'], 0)
                for name in ('불사', '칠흑의 잔향(해제불가)'):
                    self.assertEqual(name in a.eff, existing or mode == 'off')
                    if existing and mode == 'client':
                        self.assertIs(a.eff[name], old[name])
                        self.assertEqual(a.eff[name].dur, 7)
                if existing:
                    self.assertEqual(b._limit_damage(a, a.hp * 2), (a.hp - 1, None))


if __name__ == '__main__':
    unittest.main()
