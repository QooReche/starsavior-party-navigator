"""PC 26752678: 시간·횟수 필드 전수 대조(docs/timing_audit_1121.md)에서 고친 두 동작을 실제 전투 경로(cast → 피격 반응 → 효과 줄)로 확인.

1. mc.revive_se_reset — 부활(Resurrection → OBF_20318 → OBF_0597 → OBF_35004, NKM:5461·1218·1930·3493-3499)은
   SE 재발동 제한·전투당 1회 기록(OBF_16992)을 비운다.
2. mc.skill_cool_change — 스킬 쿨 감소/증가(BattleBuff NKM:5002-5011 → OBF_18296/OBF_19444 2043-2078 → OBF_32846/OBF_34909 3100-3133):
   효과 대상마다, 칸 지정 없으면 모든 칸, 증가는 최대 쿨 상한.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import battle, unit
from battlesim.mc import Ctx
from battlesim.starsavior.parser import Line

# 로자리아 고유 패시브(COND_COUNTERSIDE_ROSARIA_UNIQUE_PASSIVE_01_02, m_bNoReuse)
ONCE = '[피해 처리 후] (자신 HP 40% 이하) 자신에게 〈공격력 증가〉 (1턴 / 공격력% +30%) {전투당 1회}'
# 감시자 비틀린 시선류(SeCoolTurn 3) 대신 시험이 다루기 쉬운 자기 강화 + 재발동 제한
RECAST = '[피해 처리 후] (조건: 내가 피격될 때) 자신에게 〈방어력 증가〉 (1턴 / 방어력% +30%) {발동 후 3턴 재발동 불가}'
# 엘리사 궁극기
REVIVE = '[스킬 사용 후] 스킬 대상에게 부활(생명력 50%)'
# 코스모 힐데(지크프리트) 〈인내〉 / 괴리의 표상 〈심상 균열〉 / 루그 궁극기
SELF_ALL = '[피해 처리 후] (조건: 내가 피격될 때) 자신에게 스킬 쿨타임 1턴 감소'
ENEMY_ALL = '[피해 처리 후] (조건: 내가 피격될 때) 적 전체에게 스킬 쿨타임 1턴 감소'
ULT_UP = '[스킬 사용 후] 스킬 대상에게 궁극기 쿨타임 1턴 증가'

SKILLS = [dict(slot='기본기', dm=100), dict(slot='특수기', dm=100, cd=3), dict(slot='궁극기', dm=100, cd=4)]


def with_lines(u, *raws):
    for r in raws:
        u.lines.append(Line(r, '고유 패시브', 'passive'))
    return u


class ReviveSeResetTest(unittest.TestCase):
    def setup(self, mc=None):
        r = with_lines(unit('r', hp=10000, df=0), ONCE, RECAST)
        healer = unit('h')
        boss = unit('boss', atk=100)
        b = battle([r, healer], [boss], mc=mc)
        return b, b.allies[0], b.allies[1], b.side_units(1)[0]

    def hit(self, b, boss, r):
        r.eff.pop('공격력 증가', None)
        r.eff.pop('방어력 증가', None)
        r.hp = r.maxhp * 0.3          # HP 40% 이하
        b.dirty(r)
        b.cast(boss, boss.d.skills['기본기'], target=r)
        return '공격력 증가' in r.eff, '방어력 증가' in r.eff

    def revive(self, b, healer, r):
        b.kill(r, None)
        self.assertTrue(r.dead)
        ctx = Ctx(healer, healer, healer.d.skills['기본기'])   # «스킬 대상» 해석에 시전 스킬이 필요
        ctx.targets = [r]
        b.exec_line(healer, Line(REVIVE, '궁극기', 'ultimate'), ctx)
        self.assertFalse(r.dead)

    def run_case(self, mc=None):
        b, r, healer, boss = self.setup(mc)
        first = self.hit(b, boss, r)
        again = self.hit(b, boss, r)
        self.revive(b, healer, r)
        after = self.hit(b, boss, r)
        return b, first, again, after

    def test_client_resets_on_revive(self):
        b, first, again, after = self.run_case()
        self.assertEqual(first, (True, True))
        self.assertEqual(again, (False, False))     # 전투당 1회·재발동 제한 3턴
        self.assertEqual(after, (True, True))       # 부활하면 둘 다 다시 걸림
        self.assertGreater(b.rule_hits['revive_se_reset'], 0)


class SkillCoolChangeTest(unittest.TestCase):
    def setup(self, mc=None, boss_lines=(), ally_lines=()):
        a = with_lines(unit('a', skills=SKILLS), *ally_lines)
        boss = with_lines(unit('boss', hp=10 ** 7, skills=SKILLS), *boss_lines)
        b = battle([a], [boss], mc=mc)
        return b, b.allies[0], b.side_units(1)[0]

    def test_self_skill_cool_all_slots(self):
        b, a, boss = self.setup(boss_lines=[SELF_ALL])
        boss.cd.update({'특수기': 3, '궁극기': 4})
        b.cast(a, a.d.skills['기본기'], target=boss)
        self.assertEqual((boss.cd['특수기'], boss.cd['궁극기']), (2, 3))
        self.assertGreater(b.rule_hits['skill_cool_change'], 0)

    def test_enemy_all_targets_opponents(self):
        b, a, boss = self.setup(boss_lines=[ENEMY_ALL])
        boss.cd.update({'특수기': 3, '궁극기': 4})
        a.cd.update({'특수기': 2, '궁극기': 3})
        b.cast(a, a.d.skills['기본기'], target=boss)
        self.assertEqual((a.cd['특수기'], a.cd['궁극기']), (1, 2))       # 공격한 쪽(보스의 적) 쿨이 줄고
        self.assertEqual((boss.cd['특수기'], boss.cd['궁극기']), (3, 4))  # 보스 자신은 그대로

    def test_cool_up_capped_at_max(self):
        b, a, boss = self.setup(ally_lines=[ULT_UP])
        boss.cd.update({'궁극기': 4})        # 최대 쿨
        b.cast(a, a.d.skills['기본기'], target=boss)
        self.assertEqual(boss.cd['궁극기'], 4)
        boss.cd['궁극기'] = 2
        b.cast(a, a.d.skills['기본기'], target=boss)
        self.assertEqual(boss.cd['궁극기'], 3)


if __name__ == '__main__':
    unittest.main()
