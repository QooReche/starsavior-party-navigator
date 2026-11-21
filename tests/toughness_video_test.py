"""ChgzulK7VI4 영상 관측 회귀 중 기본 규칙(클라 강인도 식)에서도 성립하는 것만 남김.
옛 스위치 toughness_elem(video·db 모델)은 엔진 다이어트 4단계에서 지움 — 영상 모델 전용 시험(관측 표·협공 일반화)은 삭제.

python -X utf8 -I tests/toughness_video_test.py
"""
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim.api import _norm_encounter, _norm_party
from battlesim.mc import Battle, Ctx, Eff
from battlesim.starsavior.data import get_db

MODE = 'client'

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
               mc=dict(rand_range=[1, 1]), enemy_lines=False, timeline=True)
    b.spawn_wave()
    a, f = b.allies[0], b.foes[0]
    a.acting = True
    return b, a, f


def give(u, name, props=None):
    u.eff[name] = Eff(name, props or {}, 1, 99, u, False)
    u.eff[name].stacks = 1
    u._m = None


class VideoToughnessTest(unittest.TestCase):

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
            a.turn_ends += 1  # mc.se_cool_clock=client: 재발동 제한은 자기 턴 끝에 차감
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



if __name__ == '__main__':
    unittest.main(verbosity=2)
