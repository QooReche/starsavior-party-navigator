"""11/12 데이터북 문구·참조와 격파/내 턴 경계 회귀 시험."""
import json
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tests')]
from simkit import battle, give, unit
from battlesim.mc import Ctx, support_report
from battlesim.metrics import unit_def
from battlesim.starsavior.data import get_db
from battlesim.starsavior.parser import Line
from battlesim.starsavior.foe import load_foe, FoeDef, foe_auto, foe_react


class Patch1112Test(unittest.TestCase):
    def test_roster_identity_and_public_outputs(self):
        def read(name):
            with open(os.path.join(ROOT, 'data', name+'.json'), encoding='utf-8') as f:
                return json.load(f)
        roster = {s['key']:s for s in read('savior_reco')['saviors']}
        tags = {s['key']:s for s in read('synergy_tags')['saviors']}
        pairs = read('synergy_pairs')
        for key, uid, element in [('gille',1020,'chaos'),('asherah-order-striker',1061,'order')]:
            self.assertEqual(roster[key]['element'],element)
            self.assertEqual(tags[key]['id'],uid)
            self.assertTrue(tags[key]['tags'])
            self.assertTrue(any(key in (p['a'],p['b']) for p in pairs))
            self.assertEqual(read('saviors_index')[str(uid)]['key'],key)
            self.assertEqual(get_db().units[key]['id'],uid)
            self.assertIn(key,read('quick')['sv'])
        asherahs = [s for s in roster.values() if s['name']=='아세라']
        self.assertEqual(len(asherahs),3)
        self.assertEqual(len({s['key'] for s in asherahs}),3)

    def test_explicit_cooldown_and_stack_consumption(self):
        b=battle([unit(skills=[dict(slot='기본기',dm=100),dict(slot='특수기',dm=100,cd=3),dict(slot='궁극기',dm=100,cd=5)])],[unit('f')])
        a=b.allies[0];ctx=Ctx(a,a,a.d.skills['기본기'])
        a.cd.update({'특수기':3,'궁극기':5})
        b.exec_line(a,Line('[스킬 사용 후] 자신에게 특수기 쿨타임 1턴 감소','기본기','active'),ctx)
        self.assertEqual((a.cd['특수기'],a.cd['궁극기']),(2,5))
        give(a,'먼지 포착(해제불가)',{'속도%':3},stacks=8)
        ln=Line("[스킬 사용 후] 자신에게 '먼지 포착(해제불가)' 5중첩 감소",'특수기','active')
        b.exec_line(a,ln,ctx)
        self.assertEqual(a.stack('먼지 포착(해제불가)'),3)
        b.exec_line(a,ln,ctx)
        self.assertFalse(a.has('먼지 포착(해제불가)'))

    def test_inclusive_hp_boundary(self):
        b=battle([unit()],[unit('f')]);a,f=b.allies[0],b.foes[0]
        ctx=Ctx(a,a,a.d.skills['기본기']);ctx.target=f;ctx.targets=[f]
        for suffix, good, bad in [('이하',.5,.5001),('이상',.5,.4999)]:
            ln=Line(f'[스킬 사용 후] (조건: 내 공격 후 [대상 HP% {suffix}: 5000]) 자신에게 행동 게이지 15%p 증가','기본기','active')
            f.hp=f.maxhp*good;self.assertTrue(b.cond_ok(a,ln,ctx))
            f.hp=f.maxhp*bad;self.assertFalse(b.cond_ok(a,ln,ctx))

    def test_new_target_text_applies_to_selected_ally(self):
        b=battle([unit('a',atk=5000),unit('low',atk=100),unit('high',atk=2000)],[unit('f')])
        a=b.allies[0];ctx=Ctx(a,a,a.d.skills['기본기'])
        ln=Line('[스킬 사용 후] 공격력이 가장 높은 다른 아군 1명에게 〈공격력 증가〉 (2턴 / 공격력% +30%)','기본기','active')
        b.exec_line(a,ln,ctx)
        self.assertEqual([x.has('공격력 증가') for x in b.allies],[False,False,True])
        b.allies[1].hp=100
        self.assertEqual(b.resolve(a,'생명력 비율이 가장 낮은 다른 아군 1명',ctx),[b.allies[1]])

    def test_ceres_own_turn_extra_is_live(self):
        ln=next(ln for ln in unit_def('ceres-sun-supporter').lines
                if ln.eff.get('consume') and ln.eff.get('name')=='먼지 포착(해제불가)')
        for mode,remaining in [('client',3),('main_only',8)]:
            b=battle([unit_def('ceres-sun-supporter')],[unit('f',hp=10**8)],mc={'own_turn_condition':mode})
            a=b.allies[0];a.acting=True
            ctx=Ctx(a,a,a.d.skills['특수기'],True);ctx.via='extra'
            ctx.parent=Ctx(a,a,a.d.skills['특수기'])
            give(a,'먼지 포착(해제불가)',{'속도%':3},stacks=8)
            b.run_batch(a,[ln],ctx)
            self.assertEqual(a.stack('먼지 포착(해제불가)'),remaining)
            a.acting=False
            self.assertFalse(b.cond_ok(a,ln,ctx))

    def test_new_units_and_ceres_support_report(self):
        for key in ('gille','ceres','ceres-sun-supporter'):
            self.assertEqual(support_report([unit_def(key)]),[],key)
        gaps=support_report([unit_def('asherah-order-striker')])
        self.assertEqual(len(gaps),1)
        self.assertIn('강인도 피해 감소',gaps[0]['reason'])

    def test_wedding_epindel_own_turn_extra_effects(self):
        # 실제 부케 토스의 내 턴 줄 3개: 추가 턴·공격력 증가·점화 소비.
        # 상태만 준비하고 추가 시전의 피해와 조건/효과 실행은 실제 엔진을 쓴다.
        for mode, expected in [('client', ['extra_turn', 'buff', 'remove']), ('main_only', [])]:
            with self.subTest(mode=mode):
                b = battle([unit_def('wedding-epindel')], [unit('f', hp=10**8)],
                           mc={'own_turn_condition': mode}, opts={'coop': False, 'nova': False})
                a = b.allies[0]
                a.acting = True
                give(a, '점화', {}, stacks=5).maxs = 5
                checked, executed = [], []
                original_cond, original_exec = b.cond_ok, b.exec_line
                def cond(owner, ln, ctx):
                    result = original_cond(owner, ln, ctx)
                    if owner is a and dict(ln.params).get('내 턴') == '예':
                        self.assertTrue(ctx.extra)
                        checked.append(result)
                    return result
                def execute(owner, ln, ctx):
                    if owner is a and dict(ln.params).get('내 턴') == '예':
                        executed.append(ln.eff['kind'])
                    return original_exec(owner, ln, ctx)
                with patch.object(b, 'cond_ok', cond), patch.object(b, 'exec_line', execute):
                    b.cast(a, a.d.skills['특수기'], extra=True, target=b.foes[0])
                self.assertGreater(b.progress(), 0)
                self.assertEqual(checked, [mode == 'client'] * 3)
                self.assertEqual(executed, expected)
                self.assertEqual(a.extra_turn, mode == 'client')
                self.assertEqual(a.has('공격력 증가'), mode == 'client')
                self.assertEqual(a.stack('점화'), 0 if mode == 'client' else 5)

    def test_own_turn_uses_owner_state_with_other_event_source(self):
        for mode in ('client', 'main_only'):
            b = battle([unit_def('wedding-epindel'), unit('partner')], [unit('f')],
                       mc={'own_turn_condition': mode})
            a, partner = b.allies
            give(a, '점화', {}, stacks=5).maxs = 5
            lines = [ln for ln in b.lines_of(a) if dict(ln.params).get('내 턴') == '예']
            self.assertEqual(len(lines), 3)
            for acting in (True, False):
                a.acting = acting
                for source in (a, partner):
                    for extra in (True, False):
                        ctx = Ctx(a, source, a.d.skills['특수기'], extra)
                        expected = acting and (mode == 'client' or (source is a and not extra))
                        self.assertEqual([b.cond_ok(a, ln, ctx) for ln in lines], [expected] * 3,
                                         (mode, acting, source.key, extra))

    def test_old_mislabelled_stack_grant_keeps_legacy_switch(self):
        for mode, stacks in [('on', 3), ('off', 13)]:
            b = battle([unit()], [unit('f')], mc={'level_buff_decrease': mode})
            a = b.allies[0]
            give(a, '먼지 포착(해제불가)', {'속도%': 3}, stacks=8).maxs = 25
            ln = Line('[스킬 사용 후] 자신에게 〈먼지 포착(해제불가)〉 (지속 무한 / 속도% +3%) {최대 25중첩, 5회 부여}', '특수기', 'active')
            b.exec_line(a, ln, Ctx(a, a, a.d.skills['기본기']))
            self.assertEqual(a.stack('먼지 포착(해제불가)'), stacks)

    def test_named_duration_extends_buff_and_keeps_legacy(self):
        for mode, duration in [('on', 5), ('off', 3)]:
            with self.subTest(mode=mode):
                b = battle([unit()], [unit('f')], mc={'effect_dur_extend': mode})
                a, f = b.allies[0], b.foes[0]
                selected = give(a, '공격력 증가', {'공격력%': 30})
                other = give(a, '속도 증가', {'속도%': 20})
                enemy = give(f, '공격력 증가', {'공격력%': 30})
                ln = Line("[스킬 사용 후] 자신에게 '공격력 증가' 지속 턴 +2", '기본기', 'active')
                self.assertEqual(ln.eff['kind'], 'extend')
                b.run_line(a, ln, Ctx(a, a, a.d.skills['기본기']))
                self.assertEqual(selected.dur, duration)
                self.assertEqual((other.dur, enemy.dur), (3, 3))

    def test_named_duration_does_not_extend_marker_or_missed_effect(self):
        b = battle([unit()], [unit('f')])
        a = b.allies[0]
        marker = give(a, '점화', {}, stacks=5)
        checked = give(a, '공격력 증가', {'공격력%': 30})
        checked.check = True
        for name in ('점화', '공격력 증가'):
            ln = Line(f"[스킬 사용 후] 자신에게 '{name}' 지속 턴 +1", '기본기', 'active')
            b.run_line(a, ln, Ctx(a, a, a.d.skills['기본기']))
        self.assertEqual((marker.dur, checked.dur), (3, 3))
        checked.check = False
        ln = Line("[스킬 사용 후] 자신에게 '공격력 증가' 지속 턴 +1 {효과 적중 판정}", '기본기', 'active')
        with patch.object(b, 'roll_hit', return_value=False) as hit:
            b.run_line(a, ln, Ctx(a, a, a.d.skills['기본기']))
        self.assertEqual(hit.call_count, 1)
        self.assertEqual(checked.dur, 3)

    def test_existing_named_burn_duration_lines_unchanged(self):
        # 원문 3건은 크리스텔 궁극기의 lv/ef/L 표현에 각각 실려 있다.
        def named_lines(value):
            if isinstance(value, dict):
                return [raw for child in value.values() for raw in named_lines(child)]
            if isinstance(value, list):
                return [raw for child in value for raw in named_lines(child)]
            return [value] if isinstance(value, str) and "'연소' 지속 턴" in value else []
        raws = named_lines(get_db().main)
        self.assertEqual(len(raws), 3)
        for raw in raws:
            for mode in ('on', 'off'):
                with self.subTest(raw=raw, mode=mode):
                    b = battle([unit()], [unit('f')], mc={'effect_dur_extend': mode})
                    a, f = b.allies[0], b.foes[0]
                    burn = give(f, '연소', harmful=True)
                    burn.inst = [[a, 2], [a, 3]]
                    other = give(f, '출혈', harmful=True)
                    good = give(f, '공격력 증가', {'공격력%': 30})
                    ln = Line(raw, '궁극기', 'active')
                    ctx = Ctx(a, a, a.d.skills['기본기'])
                    ctx.target, ctx.targets = f, [f]
                    with patch.object(b, 'roll_hit', return_value=True):
                        b.exec_line(a, ln, ctx)
                    self.assertEqual(burn.dur, 4)
                    self.assertEqual([x[1] for x in burn.inst], [3, 4])
                    self.assertEqual((other.dur, good.dur), (3, 3))

    def test_orthros_new_condition_and_damage_text(self):
        raw = load_foe()
        for name in ('고통을 내리는 머리', '서사시의 종막'):
            sk = next(s for s in raw['s'] if s['n'] == name)
            line = next(s for s in sk['ef'] if '피해 증가 +30%' in s)
            ln = Line(line, '기본기', 'active')
            self.assertEqual(ln.eff['kind'], 'local')
            self.assertEqual(ln.eff['val'], 30)
            b = battle([unit()], [unit('f')]); a, f = b.allies[0], b.foes[0]
            ctx = Ctx(a, a, a.d.skills['기본기']); ctx.target=f; ctx.targets=[f]
            give(f, '철거 모드', {})
            self.assertFalse(b.cond_ok(a, ln, ctx))
            give(f, '열 번째 과업(해제불가)', {})
            self.assertTrue(b.cond_ok(a, ln, ctx))

    def test_explicit_consumption_does_not_precede_extra_condition(self):
        b = battle([unit_def('gwen'), unit('partner')], [unit('f', hp=10**8)])
        a, partner = b.allies
        lines = [ln for ln in b.lines_of(a) if dict(ln.params).get('중첩수 이상') == '5']
        self.assertGreaterEqual(len(lines), 2)
        give(a, '전기 충격(해제불가)', {}, stacks=8).maxs = 10
        ctx = Ctx(a, partner, partner.d.skills['기본기']); ctx.targets = [b.foes[0]]
        with patch.object(b, 'cast') as cast:
            b.run_batch(a, lines, ctx)
            self.assertEqual(cast.call_count, 1)
        self.assertEqual(a.stack('전기 충격(해제불가)'), 3)

    def test_foe_described_target_keeps_off_tie_order(self):
        from battlesim.starsavior.foe import stage_waves
        _, waves = stage_waves('cosmo', '티리아', '티리아 3단계')
        for mode, expected in [('off', [0]), ('data', [0, 1])]:
            b = battle([unit('first'), unit('second')], [waves[0][0]], mc={'foe_auto': mode})
            f = b.foes[0]
            ln = next(ln for ln in b.lines_of(f) if '타임 패러독스' in ln.raw and ln.eff.get('kind') == 'buff')
            b._cur_line = ln
            b.allies[0].gauge = b.allies[1].gauge = 5000
            targets = b.resolve(f, ln.eff['target'], Ctx(f, f, f.d.skills['특수기']))
            self.assertEqual([x.pos for x in targets], expected)

    def test_foe_indices_match_own_skills(self):
        raw=load_foe()
        for key,row in foe_auto().items():
            _,ui,*xi=key.split(':')
            for ref in row.get('lines',{}):
                si,li=map(int,ref.split(':'))
                self.assertIn(si,raw['u'][int(ui)]['sk'],key)
                self.assertLess(li,len(raw['s'][si].get('ef',[])),key)
        for key,row in foe_react().items():
            _,ui,*xi=key.split(':')
            d=FoeDef(raw,int(ui),int(xi[0]) if xi else None)
            for slot in row:self.assertIn(slot,d.trigger_skills,key)

    def test_noa_sum_and_reduction_cap(self):
        b=battle([unit(df=0)],[unit('f',df=0)])
        a,f=b.allies[0],b.foes[0];ctx=Ctx(a,a,a.d.skills['기본기'])
        give(a,'증가',{'피해 증가':40});give(f,'감소',{'피해 감소':80})
        # 클라 식: 1 + .4 - min(.5,.8) = .9. 합친 뒤 제한하면 .6으로 달라짐.
        self.assertEqual(b.final_dmg(a,f,1000,ctx,False,0,0,1,None),899)
        give(a,'감소',{'피해 증가':-70})
        self.assertEqual(b.final_dmg(a,f,1000,ctx,False,0,0,1,None),200)
        before=f.taken
        b.chain(a,dict(target='적 전체',stat='atk',coef=1),ctx)
        first=f.taken-before
        f.eff.clear();b.dirty(f);before=f.taken
        b.chain(a,dict(target='적 전체',stat='atk',coef=1),ctx)
        self.assertGreater(first,0)
        self.assertEqual(f.taken-before,first)


if __name__=='__main__':
    unittest.main()
