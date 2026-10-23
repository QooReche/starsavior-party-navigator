# -*- coding: utf-8 -*-
"""적 반응(트리거) 스킬 5종 회귀: python -X utf8 -I tests/run_workspace_test.py tests/foe_react_test.py

지원 5종: 맹약 회수(공허맹약자)·앙코르(공허변주자)·소거(괴리의 표상)·태엽 폭탄 기폭(레디메이드 해피 68호)·월영(복제체 페이).
각각 발동/미발동(중첩 미만·대상 사망·기절·쿨), 예약 순서(본 행동→반격→반응), off 스위치."""
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from battlesim.api import _CustomFoe
from battlesim.mc import Battle, Eff
from battlesim.metrics import unit_def
from battlesim.starsavior.parser import Skill


def _foe(react_rules, skills=None, **kw):
    """react_rules: {칸: {timing, conds, target, ...}}, skills: active 스킬 목록"""
    spec = dict(name='react_boss', hp=10**8, atk=2000, **{'def': 1000}, spd=120, boss=True)
    spec.update(kw)
    if skills:
        spec['skills'] = skills
    d = _CustomFoe(spec, 0)
    d.react = dict(react_rules)
    for slot, rule in react_rules.items():
        is_atk = rule.get('is_attack', False)
        tg = '적 전체' if rule['target'] == 'all' else '적 단일'
        sk = Skill(dict(sl=slot, n='react_' + slot, ty='트리거', tg=tg,
                        act='공격' if is_atk else '비공격',
                        cf=[10000, 0, 0, 0] if is_atk else [0, 0, 0, 0],
                        all=(rule['target'] == 'all'), cd=rule.get('cd', 0), nv=0))
        sk.ab = rule.get('ab', 0)
        d.trigger_skills[slot] = sk
    return d


def _battle(foe_def, allies=('emily',), **mc_kw):
    defs = [unit_def(k) for k in allies]
    opts = dict(nova_policy='auto', coop=False)
    b = Battle(defs, [[foe_def]], random.Random(42), opts=opts,
               mc=mc_kw, timeline=True)
    b.spawn_wave()
    return b


def _set_buff(unit, name, harmful=False, dur=99, stacks=1):
    """유닛에 버프/디버프를 직접 설정."""
    e = Eff(name, {}, {}, dur, unit, harmful)
    e.stacks = stacks
    e.fixed = True
    unit.eff[name] = e


def _count_react_casts(b):
    """timeline 에서 via='reaction' 인 시전 횟수."""
    return sum(1 for e in (b.timeline or []) if isinstance(e, dict) and e.get('via') == 'reaction')


# ================================================================ 태엽 폭탄 기폭 (가장 단순: 기본기 후 발동, cd 4)
class TestClockworkBomb(unittest.TestCase):
    """레디메이드 해피 68호: AfterMyAttack + 기본기 → 적 전체, cd 4"""

    def _foe(self):
        return _foe({'특수기': {'timing': 'after_attack', 'conds': [['skill_basic']], 'target': 'all', 'cd': 4, 'is_attack': True}})

    def test_fires_after_basic_attack(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        b.act(foe)
        self.assertGreater(_count_react_casts(b), 0, '기본기 뒤 반응 스킬이 발동해야 함')

    def test_not_fires_after_special(self):
        """특수기로 공격하면 skill_basic 조건 미충족."""
        d = self._foe()
        d.skills['특수기'] = Skill(dict(sl='특수기', n='폭발', ty='액티브', tg='적 전체',
                                       act='공격', cf=[15000, 0, 0, 0], all=True, cd=0, nv=0))
        b = _battle(d)
        foe = b.foes[0]
        b.cast(foe, foe.d.skills['특수기'])
        self.assertEqual(_count_react_casts(b), 0, '특수기 뒤에는 발동하지 않아야 함')

    def test_cooldown_prevents_second_fire(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        b.act(foe)   # 첫 발동
        first = _count_react_casts(b)
        self.assertGreater(first, 0)
        b.timeline.clear()
        b.act(foe)   # 쿨 4 — 아직 안 찰 것
        self.assertEqual(_count_react_casts(b), 0, '쿨타임 중에는 발동하면 안 됨')

    def test_off_switch_disables(self):
        b = _battle(self._foe(), foe_react='off')
        foe = b.foes[0]
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, 'foe_react=off 에서는 발동하면 안 됨')


# ================================================================ 소거 (self_has + self_not_has)
class TestErasure(unittest.TestCase):
    """괴리의 표상: AfterMyAttack + 잔재된 괴리 보유 + 체크용 버프 미보유 → react_target"""

    def _foe(self):
        return _foe({'특수기': {
            'timing': 'after_attack',
            'conds': [['self_has', ['잔재된 괴리(해제불가)']], ['self_not_has', ['트리거 스킬 발동 체크용 버프']]],
            'target': 'react_target', 'is_attack': True, 'ab': 2}})

    def test_fires_when_has_buff_no_check(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '잔재된 괴리(해제불가)')
        b.act(foe)
        self.assertGreater(_count_react_casts(b), 0)

    def test_not_fires_without_buff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0)

    def test_not_fires_with_check_buff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '잔재된 괴리(해제불가)')
        _set_buff(foe, '트리거 스킬 발동 체크용 버프')
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '체크용 버프가 있으면 발동하면 안 됨')

    def test_stunned_foe_does_not_react(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '잔재된 괴리(해제불가)')
        _set_buff(foe, '기절', harmful=True, dur=1)
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '기절 중에는 반응 불가')


# ================================================================ 앙코르 (self_stack_ge)
class TestEncore(unittest.TestCase):
    """공허변주자: AfterMyAttack + 기본기 + 악상 ≥2 → 적 전체, cd 1"""

    def _foe(self):
        return _foe({'특수기': {
            'timing': 'after_attack',
            'conds': [['skill_basic'], ['self_stack_ge', '악상(해제불가)', 2]],
            'target': 'all', 'cd': 1, 'is_attack': True}})

    def test_fires_at_stack_2(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '악상(해제불가)', stacks=2)
        b.act(foe)
        self.assertGreater(_count_react_casts(b), 0)

    def test_not_fires_at_stack_1(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '악상(해제불가)', stacks=1)
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '악상 1스택은 미달')


# ================================================================ 맹약 회수 (self_stack_eq + target_has + not_eliminate)
class TestCovenantRecall(unittest.TestCase):
    """공허맹약자: AfterMyAttack + 맹약결속 ==3 + 대상 피의 맹약 보유 + 대상 미처치 → react_target"""

    def _foe(self):
        return _foe({'궁극기': {
            'timing': 'after_attack',
            'conds': [['self_stack_eq', '맹약결속(해제불가)', 3],
                      ['target_has', ['피의 맹약(해제불가)']],
                      ['not_eliminate']],
            'target': 'react_target', 'is_attack': True}})

    def test_fires_all_conditions_met(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        ally = b.allies[0]
        _set_buff(foe, '맹약결속(해제불가)', stacks=3)
        _set_buff(ally, '피의 맹약(해제불가)', harmful=True)
        b.act(foe)
        self.assertGreater(_count_react_casts(b), 0)

    def test_not_fires_stack_mismatch(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        ally = b.allies[0]
        _set_buff(foe, '맹약결속(해제불가)', stacks=2)
        _set_buff(ally, '피의 맹약(해제불가)', harmful=True)
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '맹약결속 2스택은 미달(정확히 3 필요)')

    def test_not_fires_target_dead(self):
        """대상이 처치되면 not_eliminate + react_target 모두 거부."""
        b = _battle(self._foe())
        foe = b.foes[0]
        ally = b.allies[0]
        _set_buff(foe, '맹약결속(해제불가)', stacks=3)
        _set_buff(ally, '피의 맹약(해제불가)', harmful=True)
        ally.hp = 1  # 즉사하도록
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '대상 처치 시 발동하면 안 됨')

    def test_not_fires_target_no_debuff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '맹약결속(해제불가)', stacks=3)
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '피의 맹약 없으면 발동하면 안 됨')


# ================================================================ 월영 (hit timing + single_target)
class TestMoonShadow(unittest.TestCase):
    """복제체 페이: MyEffectiveHit + 풍호 보유 + 단일 대상 스킬 → react_target"""

    def _foe(self, all_attack=False):
        skills = [dict(slot='기본기', dm=100, all=all_attack)]
        return _foe({'특수기': {
            'timing': 'hit',
            'conds': [['self_has', ['풍호(해제불가)']], ['single_target']],
            'target': 'react_target', 'is_attack': True, 'ab': 2}},
            skills=skills)

    def test_fires_single_target_with_buff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        _set_buff(foe, '풍호(해제불가)')
        b.act(foe)
        self.assertGreater(_count_react_casts(b), 0)

    def test_not_fires_aoe_attack(self):
        b = _battle(self._foe(all_attack=True))
        foe = b.foes[0]
        _set_buff(foe, '풍호(해제불가)')
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '전체 공격에는 single_target 미충족')

    def test_not_fires_without_buff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0)


# ================================================================ 순서·스위치
class TestReactOrder(unittest.TestCase):
    def test_reaction_after_main_action(self):
        """타임라인에서 반응이 본 행동(기본기) 뒤."""
        foe = _foe({'특수기': {'timing': 'after_attack', 'conds': [['skill_basic']], 'target': 'all', 'cd': 0, 'is_attack': True}})
        b = _battle(foe)
        f = b.foes[0]
        b.act(f)
        reacts = [i for i, e in enumerate(b.timeline) if isinstance(e, dict) and e.get('via') == 'reaction']
        basics = [i for i, e in enumerate(b.timeline) if isinstance(e, dict) and e.get('skill') == '기본기' and e.get('side') == 1]
        self.assertTrue(reacts, '반응 시전이 있어야 함')
        self.assertTrue(basics, '기본기 시전이 있어야 함')
        self.assertGreater(min(reacts), min(basics), '반응은 본 행동(기본기) 뒤')

    def test_off_preserves_old_behavior(self):
        """foe_react=off 에서 반응 스킬이 0회 발동."""
        foe = _foe({'특수기': {'timing': 'after_attack', 'conds': [], 'target': 'all', 'is_attack': True}})
        b = _battle(foe, foe_react='off')
        b.act(b.foes[0])
        self.assertEqual(_count_react_casts(b), 0)


# ================================================================ on_my_attack (내 공격 시, 스트라이크 전)
class TestOnMyAttack(unittest.TestCase):
    """HAPPY68 류: OnMyAttack + 기본기 + 대상 약화 보유 → 적 전체"""

    def _foe(self):
        return _foe({'특수기': {
            'timing': 'on_my_attack',
            'conds': [['skill_basic'], ['target_neg_buff']],
            'target': 'all', 'is_attack': True}})

    def test_fires_basic_target_debuff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        ally = b.allies[0]
        _set_buff(ally, '속박', harmful=True, dur=3)
        b.act(foe)
        self.assertGreater(_count_react_casts(b), 0, '기본기 + 대상 약화 시 발동')

    def test_not_fires_no_debuff(self):
        b = _battle(self._foe())
        foe = b.foes[0]
        b.act(foe)
        self.assertEqual(_count_react_casts(b), 0, '대상 약화 없으면 미발동')

    def test_not_fires_special(self):
        """특수기로 공격 시 skill_basic 불충족."""
        d = self._foe()
        d.skills['특수기'] = Skill(dict(sl='특수기', n='폭발', ty='액티브', tg='적 전체',
                                       act='공격', cf=[15000, 0, 0, 0], all=True, cd=0, nv=0))
        b = _battle(d)
        ally = b.allies[0]
        _set_buff(ally, '속박', harmful=True)
        b.cast(b.foes[0], b.foes[0].d.skills['특수기'])
        self.assertEqual(_count_react_casts(b), 0)

    def test_off_switch(self):
        b = _battle(self._foe(), foe_react='off')
        ally = b.allies[0]
        _set_buff(ally, '속박', harmful=True)
        b.act(b.foes[0])
        self.assertEqual(_count_react_casts(b), 0)

    def test_legacy_switch_disables(self):
        b = _battle(self._foe(), foe_react_timing='legacy')
        ally = b.allies[0]
        _set_buff(ally, '속박', harmful=True)
        b.act(b.foes[0])
        self.assertEqual(_count_react_casts(b), 0, 'foe_react_timing=legacy 에서는 on_my_attack 미발동')


# ================================================================ after_ally_attack (아군 공격 뒤)
def _battle_two_foes(boss_def, minion_skills=None, allies=('emily',), **mc_kw):
    """보스 + 졸개로 구성된 2인 적 전투. minion_skills: 졸개에 줄 추가 스킬 dict."""
    from battlesim.api import _CustomFoe
    defs = [unit_def(k) for k in allies]
    minion_spec = dict(name='minion', hp=10**6, atk=1000, **{'def': 500}, spd=100)
    minion_d = _CustomFoe(minion_spec, 1)
    if minion_skills:
        for slot, sk in minion_skills.items():
            minion_d.skills[slot] = sk
    opts = dict(nova_policy='auto', coop=False)
    b = Battle(defs, [[boss_def, minion_d]], random.Random(42), opts=opts,
               mc=mc_kw, timeline=True)
    b.spawn_wave()
    return b


class TestAfterAllyAttack(unittest.TestCase):
    """WHITEDRAGON 류: AfterAllyAttack + IncludeSelf=false + skill_hyper → 적 전체"""

    def _boss(self, include_self=False):
        return _foe({'궁극기': {
            'timing': 'after_ally_attack',
            'conds': [['include_self', include_self], ['skill_hyper']],
            'target': 'all', 'is_attack': True}})

    def test_fires_when_ally_uses_hyper(self):
        """졸개가 궁극기를 쓰면 보스의 after_ally_attack 발동."""
        hyper_sk = Skill(dict(sl='궁극기', n='화염', ty='액티브', tg='적 단일',
                              act='공격', cf=[20000, 0, 0, 0], all=False, cd=0, nv=0))
        b = _battle_two_foes(self._boss(), minion_skills={'궁극기': hyper_sk})
        minion = b.foes[1]
        b.act(minion)
        self.assertGreater(_count_react_casts(b), 0, '아군(졸개)이 궁극기 사용 후 보스 반응 발동')

    def test_not_fires_include_self_false(self):
        """IncludeSelf=false 면 자기 궁극기에는 반응 안 함."""
        boss = self._boss(include_self=False)
        boss.skills['궁극기'] = Skill(dict(sl='궁극기', n='용의 숨결', ty='액티브', tg='적 전체',
                                           act='공격', cf=[30000, 0, 0, 0], all=True, cd=0, nv=0))
        b = _battle_two_foes(boss)
        b.act(b.foes[0])   # 보스 자신이 궁극기
        self.assertEqual(_count_react_casts(b), 0, 'IncludeSelf=false: 자기 궁극기에 반응 안 함')

    def test_not_fires_wrong_skill(self):
        """졸개가 기본기를 쓰면 skill_hyper 미충족."""
        b = _battle_two_foes(self._boss())
        minion = b.foes[1]
        b.act(minion)   # 기본기
        self.assertEqual(_count_react_casts(b), 0, '기본기는 skill_hyper 미충족')

    def test_legacy_switch_disables(self):
        hyper_sk = Skill(dict(sl='궁극기', n='화염', ty='액티브', tg='적 단일',
                              act='공격', cf=[20000, 0, 0, 0], all=False, cd=0, nv=0))
        b = _battle_two_foes(self._boss(), minion_skills={'궁극기': hyper_sk}, foe_react_timing='legacy')
        minion = b.foes[1]
        b.act(minion)
        self.assertEqual(_count_react_casts(b), 0, 'legacy 에서는 after_ally_attack 미발동')


# ================================================================ damage_result (피해 결과 조건)
class TestDamageResult(unittest.TestCase):
    """DamageResultType 조건: 회피/치명타/일반 판정.
    ctx.evaded·crit_targets 를 직접 설정해 _check_foe_react 의 조건 판정을 검증한다
    (난수에 의존하지 않음 — 엔진이 deal() 중 설정하는 집합을 그대로 주입)."""

    def _foe_evade(self):
        """MyEffectiveHit + DamageResultType=[Evade] → react_target"""
        return _foe({'특수기': {
            'timing': 'hit',
            'conds': [['damage_result', ['Evade']]],
            'target': 'react_target', 'is_attack': True}})

    def _foe_crit(self):
        """MyEffectiveHit + DamageResultType=[CriticalHit] → react_target"""
        return _foe({'특수기': {
            'timing': 'hit',
            'conds': [['damage_result', ['CriticalHit']]],
            'target': 'react_target', 'is_attack': True}})

    def _foe_normal(self):
        """MyEffectiveHit + DamageResultType=[NormalHit] → react_target"""
        return _foe({'특수기': {
            'timing': 'hit',
            'conds': [['damage_result', ['NormalHit']]],
            'target': 'react_target', 'is_attack': True}})

    def _inject(self, foe_def, evaded=False, crit=False):
        """배틀을 만들고 ctx 를 직접 구성해 _check_foe_react 를 호출한다."""
        from battlesim.mc import Ctx
        b = _battle(foe_def)
        foe = b.foes[0]
        ally = b.allies[0]
        sk = foe.d.skills['기본기']
        ctx = Ctx(foe, foe, sk)
        ctx.targets = [ally]
        ctx.target = ally
        ctx.hit_targets = [ally]
        ctx.evaded = {ally} if evaded else set()
        ctx.crit_targets = {ally} if crit else set()
        b._react_q = None    # 대기열 없이 바로 실행
        b._check_foe_react(foe, ctx, timing_filter=None)
        return b

    def test_fires_on_evade(self):
        b = self._inject(self._foe_evade(), evaded=True)
        self.assertGreater(_count_react_casts(b), 0, '회피 시 Evade 조건 충족 → 발동')

    def test_not_fires_on_crit_when_evade_required(self):
        """치명타이면 Evade 조건 미충족."""
        b = self._inject(self._foe_evade(), crit=True)
        self.assertEqual(_count_react_casts(b), 0, '치명타는 Evade 조건 미충족')

    def test_not_fires_on_normal_when_evade_required(self):
        b = self._inject(self._foe_evade(), evaded=False, crit=False)
        self.assertEqual(_count_react_casts(b), 0, '일반 타격은 Evade 조건 미충족')

    def test_fires_on_crit(self):
        b = self._inject(self._foe_crit(), crit=True)
        self.assertGreater(_count_react_casts(b), 0, '치명타 시 CriticalHit 조건 충족 → 발동')

    def test_not_fires_on_evade_when_crit_required(self):
        b = self._inject(self._foe_crit(), evaded=True)
        self.assertEqual(_count_react_casts(b), 0, '회피는 CriticalHit 조건 미충족')

    def test_fires_on_normal(self):
        b = self._inject(self._foe_normal(), evaded=False, crit=False)
        self.assertGreater(_count_react_casts(b), 0, '일반 타격 시 NormalHit 조건 충족 → 발동')

    def test_not_fires_on_evade_when_normal_required(self):
        b = self._inject(self._foe_normal(), evaded=True)
        self.assertEqual(_count_react_casts(b), 0, '회피는 NormalHit 조건 미충족')


if __name__ == '__main__':
    unittest.main()
