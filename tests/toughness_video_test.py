"""ChgzulK7VI4 영상 관측 회귀. --legacy는 동일 관측을 db로 검사해 실패해야 한다.

python -X utf8 -I tests/toughness_video_test.py
python -X utf8 -I tests/toughness_video_test.py --legacy
버스트 궁 4와 다른 구원자 협공 0은 관측 확정이 아닌 후보 규칙 시험이다.
"""
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim.api import _norm_encounter, _norm_party
from battlesim.mc import Battle, Ctx, Eff
from battlesim.rules import MC_OPTS
from battlesim.starsavior.data import get_db

MODE = 'db' if '--legacy' in sys.argv else 'video'   # 기본 규칙은 db, 이 시험은 video 후보 규칙을 검증
if '--legacy' in sys.argv:
    sys.argv.remove('--legacy')

# key, slot, expected, measured repeats. 궁 4는 버스트 여부 미상이라 아래 별도 가설 시험.
OBSERVED = [
    ('bunny-charlotte', '기본기', 1, 3), ('bunny-charlotte', '특수기', 0, 1),
    ('bunny-charlotte', '궁극기', 3, 2),
    ('wedding-epindel', '기본기', 1, 4), ('wedding-epindel', '특수기', 2, 3),
    ('wedding-epindel', '궁극기', 2, 2),
    ('haydee', '기본기', 1, 4), ('haydee', '특수기', 0, 1),
    ('waltz-asherah', '기본기', 0, 1), ('waltz-asherah', '특수기', 1, 2),
    ('waltz-asherah', '궁극기', 0, 1),
]


def fixture(key, mode=MODE, **opts):
    defs, _ = _norm_party([key], get_db(), 'fixed', 'standard')
    waves = _norm_encounter({'stage': 'op/아가논 시가지/SECTOR 36-36'})[0]
    boss = next(d for d in waves[0] if d.boss)
    b = Battle(defs, [[boss]], random.Random(7), opts=dict(coop=False, **opts),
               mc=dict(toughness_elem=mode, rand_range=[1, 1]), enemy_lines=False, timeline=True)
    b.spawn_wave()
    a, f = b.allies[0], b.foes[0]
    a.acting = True
    return b, a, f


def give(u, name, props=None):
    u.eff[name] = Eff(name, props or {}, 1, 99, u, False)
    u.eff[name].stacks = 1
    u._m = None


class VideoToughnessTest(unittest.TestCase):
    def test_observed_skills(self):
        for key, slot, expected, repeats in OBSERVED:
            with self.subTest(key=key, slot=slot):
                b, a, f = fixture(key)
                for _ in range(repeats):
                    f.sa, f.broken = 18, False
                    a.actions += 1
                    b.cast(a, a.d.skills[slot], target=f)
                    self.assertEqual(18 - f.sa, expected)

    def test_ab_and_effect_data(self):
        expected = {
            'waltz-asherah': [None, 1, None], 'bunny-charlotte': [None, None, 2],
            'wedding-epindel': [None, 1, 1], 'haydee': [None, None, 2],
        }
        for key, ab in expected.items():
            b, a, f = fixture(key)
            self.assertEqual([a.d.skills[s].raw.get('ab') for s in ('기본기', '특수기', '궁극기')], ab)
            self.assertFalse(any('강인도' in ln.raw for ln in b.lines_of(a)))
            self.assertEqual(f.element, '별')
            self.assertEqual(f.sa_max, 18)

    def test_bunny_extra_separate(self):
        b, a, f = fixture('bunny-charlotte')
        b.cast(a, a.d.skills['특수기'])  # 실제 럭키 토큰 부여 줄 사용
        for _ in range(3):
            f.sa = 18
            a.actions += 1
            b.cast(a, a.d.skills['기본기'], target=f)
            self.assertEqual(18 - f.sa, 2)
        self.assertEqual(a.cast_count['기본기(추가)'], 3)

    def test_asherah_coop_seven(self):
        b, a, f = fixture('waltz-asherah')
        hp = f.hp
        for _ in range(7):
            b.cast(a, a.d.skills['기본기'], extra=True, target=f, via='coop')
        self.assertEqual(f.sa, 18)
        self.assertLess(f.hp, hp)  # 피해가 들어가도 강인도는 0

    def test_coop_generalization_candidate(self):
        # 아세라 외/강제 협공은 영상 미측정. 추가 발동과 구분되는 경로를 검사.
        for via in ('coop', 'forced_coop', 'extra'):
            b, a, f = fixture('wedding-epindel')
            b.cast(a, a.d.skills['기본기'], extra=True, target=f, via=via)
            self.assertEqual(18 - f.sa, 1 if via == 'extra' else 0)

    def test_burst_explains_four_conditionally(self):
        # 3/4/3 재현의 충분조건일 뿐, 영상에서 버스트를 썼다는 증거는 아니다.
        got = []
        for burst in (False, True, False):
            b, a, f = fixture('bunny-charlotte', nova_policy='manual' if burst else 'auto')
            b.team_nova = 4
            ctx = b.cast(a, a.d.skills['궁극기'], target=f)
            self.assertEqual(ctx.nb, burst)
            got.append(18 - f.sa)
        self.assertEqual(got, [3, 4, 3])

    def test_once_per_cast_target(self):
        b, a, f = fixture('wedding-epindel')
        c = Ctx(a, a, a.d.skills['특수기'])
        c.targets, c.target = [f], f
        for _ in range(4):
            b.deal(a, c)
        self.assertEqual(18 - f.sa, 2)
        # 별도 시전 Ctx에는 제한이 전파되지 않는다.
        b.cast(a, a.d.skills['특수기'], extra=True, target=f)
        self.assertEqual(18 - f.sa, 4)
        # 전체 공격의 다른 대상도 각각 한 번.
        c.tough_targets.clear()
        other = type(f)(f.d, 1, 1, b)
        c.targets = [f, other]
        b.deal(a, c)
        self.assertEqual((f.sa, other.sa), (12, 16))

    def test_no_tough_on_evade_nullify_immunity_or_break(self):
        for effect in ('회피', '스킬 피해 무효', '강인도 피해 무효', 'broken'):
            b, a, f = fixture('wedding-epindel')
            if effect == 'broken':
                f.broken = True
            else:
                give(f, effect, {'회피율': 100} if effect == '회피' else {})
            b.cast(a, a.d.skills['기본기'], target=f)
            self.assertEqual(f.sa, 18, effect)

    def test_break_and_recover(self):
        b, a, f = fixture('wedding-epindel')
        f.gauge = 7000
        # 개별 스킬 검증용 9회; 영상의 미제공 전체 행동 순서를 재구성한 것이 아님.
        for _ in range(9):
            b.cast(a, a.d.skills['특수기'], target=f)
        self.assertEqual((f.sa, f.broken, f.breaks, f.gauge), (0, True, 1, 0))
        b.act(f)
        self.assertEqual((f.sa, f.broken, f.actions), (18, False, 1))

    def test_enemy_rule_kept(self):
        results = []
        for mode in ('db', 'video'):
            b, a, f = fixture('haydee', mode)
            c = Ctx(f, f, f.d.skills['기본기'])
            c.nb = True  # 적은 video 버스트 보정 대상이 아님
            start = a.sa
            b.tough_hit(f, a, c)
            results.append(start - a.sa)
        self.assertEqual(results[0], results[1])

    def test_legacy_counterexample(self):
        reductions = []
        for mode in ('db', 'video'):
            b, a, f = fixture('haydee', mode)
            b.cast(a, a.d.skills['기본기'], target=f)
            reductions.append(18 - f.sa)
        self.assertEqual(reductions, [0, 1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
