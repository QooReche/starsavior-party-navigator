"""26752678 칸 실제 정의: 중첩 경계·과열 행동 차단·클라 배치. legacy 변이도 검사함."""
import copy
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from simkit import unit
from battlesim.mc import Battle, Ctx, line_kind
from battlesim.starsavior.guild import build_waves
from battlesim import simulate

CLOCK = '오버클럭(해제불가)'
HEAT = '오버히트(해제불가)'


def battle(mode='client'):
    waves, meta = build_waves({'seasonId': 30101, 'step': 6})
    d = copy.deepcopy(next(d for d in waves[-1] if d.boss))
    b = Battle([unit('target%d' % i, hp=10**9, atk=1) for i in range(4)], [[d]], random.Random(3),
               opts={'coop': False, 'nova': False}, mc={'khan_passives': mode}, timeline=True,
               battle_mode=meta['battle_mode'])
    b.spawn_wave()
    return b, b.foes[0]


def stack(b, u, name, n):
    b.put_eff(u, name, {}, maxs=5, add=n, src=u, cat='debuff' if name == HEAT else 'buff', fixed=True)


class KhanTest(unittest.TestCase):
    def test_legacy_enforce_boundary(self):
        from battlesim.starsavior.foe import FoeDef,load_foe
        from tools.build_foe_auto import unit_rules
        for mode in ('client','snapshot'):
            b,boss=battle(mode)
            ln=next(ln for ln in b.lines_of(boss) if ln.eff['kind']=='extra_cast')
            self.assertEqual(b.self_enforce_spec(boss,ln) is not None,mode=='client')
            boss.d=FoeDef(load_foe(),55,9)
            self.assertIsNotNone(b.self_enforce_spec(boss,ln),'기존 변형의 legacy 규칙은 유지함')
        # 패치에서 확정 SE가 확률형으로 바뀌면 추출을 중단해야 함.
        raw={'s':[{'ef':['[스킬 사용 후] 자신에게 〈속도 증가〉 (2턴)']}]}
        se={'skill':[{'m_BuffTargetType':'NSETT_SELF','m_SEStrID':'test',
                     'm_Condition':{'m_fActiveRate':10000},'m_fBuffActiveRate':5000}]}
        with self.assertRaisesRegex(ValueError,'칸 효과 확률 변경'):
            unit_rules({'n':'카본펑크 칸','sk':[0]},raw,{'m_listSkill':['skill']},{},{},{},se,{})

    def test_enforce_target_and_delete_before_extra(self):
        for enabled in (True,False):
            b,boss=battle()
            stack(b,boss,CLOCK,4);stack(b,boss,HEAT,3)
            boss.cd.update({'특수기':99,'궁극기':99})
            cast,pick=b.cast,b.filter_pick
            seen=[]
            def wrapped(actor,sk,**kw):
                if actor is boss:
                    if kw.get('extra'):
                        seen.append((kw.get('target'),boss.stack(CLOCK),boss.stack(HEAT)))
                    else:kw['target']=b.allies[0]
                return cast(actor,sk,**kw)
            if not enabled:b.self_enforce_spec=lambda *args:None
            with patch.object(b,'cast',side_effect=wrapped),patch.object(b,'filter_pick',side_effect=lambda u,p,f,*args: p[-1] if f==[] else pick(u,p,f,*args)):
                b._act_turn(boss)
            self.assertEqual(len(seen),1)
            self.assertIs(seen[0][0],b.allies[-1] if enabled else b.allies[0])
            self.assertEqual(seen[0][1:],(0,0),'추가 궁극기 실행 전에 두 중첩이 삭제되어야 함')

    def test_se_rng_and_immunity_order(self):
        class Rng:
            def __init__(self):self.calls=0
            def random(self):self.calls+=1;return 0.0
        for mode in ('client','snapshot'):
            b,boss=battle(mode)
            for name,slot,count in ((CLOCK,'패시브',0),('공격력 감소','특수기',8),('연소','궁극기',2)):
                ln=next(ln for ln in b.lines_of(boss) if ln.slot==slot and ln.eff.get('name')==name)
                ctx=Ctx(boss,boss,boss.d.skills['기본기' if slot=='패시브' else slot])
                ctx.target,ctx.targets=b.allies[0],[b.allies[0]]
                rng=Rng()
                with patch.object(b,'R',return_value=rng):b.run_line(boss,ln,ctx)
                expected=count if mode=='client' else (1 if name==CLOCK else 8 if slot=='특수기' else 4)
                self.assertEqual(rng.calls,expected,(mode,name))
            target=b.allies[0]
            b.put_eff(target,'면역',{},src=target,cat='buff')
            ln=next(ln for ln in b.lines_of(boss) if ln.slot=='궁극기' and ln.eff.get('name')=='연소')
            rng=Rng();before=target.stack('연소')
            with patch.object(b,'R',return_value=rng),patch.object(b,'roll_hit',wraps=b.roll_hit) as hit:
                b.run_line(boss,ln,ctx)
                self.assertEqual(hit.call_count,2 if mode=='client' else 0)
            self.assertEqual(target.stack('연소'),before)

    def test_overheat_increases_received_damage(self):
        damages=[]
        for overheat in (False,True):
            b,boss=battle();b.mc['rand_range']=[1,1]
            a=b.allies[0];a.d.stats['atk']=100000;a.d.stats['cr']=0
            if overheat:b.put_eff(boss,'과열 상태',{'피해 감소':-15},dur=1,src=boss,cat='debuff')
            ctx=Ctx(a,a,a.d.skills['기본기']);ctx.target,ctx.targets=boss,[boss]
            hp=boss.hp;b.deal(a,ctx);damages.append(hp-boss.hp)
        self.assertGreater(damages[0],0)
        self.assertAlmostEqual(damages[1]/damages[0],1.15,delta=.001)

    def test_overclock_threshold(self):
        results = []
        for mode in ('client', 'snapshot'):
            b, boss = battle(mode)
            stack(b, boss, CLOCK, 4)
            stack(b, boss, HEAT, 3)
            boss.cd.update({'특수기': 99, '궁극기': 99})
            b._act_turn(boss)
            casts = [x for x in b.timeline if x.get('actor') == boss.name and x.get('skill_name') == '죽음의 손아귀']
            self.assertEqual(len(casts), 1 if mode == 'client' else 0, b.timeline)
            self.assertEqual(dict(b.unsup), {})
            results.append((boss.stack(CLOCK), boss.stack(HEAT), boss.gauge))
        self.assertEqual(results[0][:2], (0, 0), results)
        self.assertGreaterEqual(results[0][2], 2000, results)
        self.assertNotEqual(results[0], results[1], 'legacy로 꺼도 같은 시험은 무효')

    def test_overheat_threshold(self):
        values = []
        for mode in ('client', 'snapshot'):
            b, boss = battle(mode)
            stack(b, boss, HEAT, 4)
            stack(b, boss, CLOCK, 2)
            boss.gauge = 5000
            sk = copy.copy(b.allies[0].d.skills['기본기'])
            sk.all = True
            sk.tg = '적 전체'
            ctx = Ctx(boss, b.allies[0], sk)
            ctx.target, ctx.targets = boss, [boss]
            lines = [ln for ln in b.lines_of(boss) if line_kind(ln) == 'hit_self']
            self.assertGreater(len(lines), 4)
            b.run_batch(boss, lines, ctx)
            values.append((boss.stack(HEAT), boss.stack(CLOCK), boss.gauge, boss.has('과열 상태')))
        self.assertEqual(values[0], (0, 0, 0, True), values)
        self.assertNotEqual(values[0], values[1])

    def test_overheat_stun_and_debuff_stats(self):
        for mode, expect in (('client', True), ('snapshot', False)):
            b, boss = battle(mode)
            b.put_eff(boss, '과열 상태', {'피해 감소': -15}, dur=1, src=boss, cat='debuff')
            self.assertEqual(b.incapacitated(boss), expect)
            before = [u.hp for u in b.allies]
            b.cast(boss, boss.d.skills['궁극기'], extra=True, via='enforce')
            self.assertEqual([u.hp for u in b.allies] == before, expect)
            b._act_turn(boss)
            self.assertEqual([u.hp for u in b.allies] == before, expect)

    def test_real_seasons(self):
        for sid in (30101, 30102, 30104):
            w, meta = build_waves({'seasonId': sid, 'step': 6})
            self.assertEqual(meta['battle_mode'], 'boss_kill')
            self.assertEqual(meta['turn_limit'], 50)
            boss = next(d for d in w[-1] if d.boss)
            self.assertEqual(boss.spawn, 'S')
            self.assertIsNotNone(boss.game_slot)
            r = simulate(['gwen', 'fei', 'professor-m', 'amora'], {'guild': {'seasonId': sid, 'step': 6}},
                         {'build': 'standard', 'n_runs': 3, 'seed': 3})
            self.assertGreater(r['outcome']['progress'], 0)
            self.assertEqual(r['unsupported']['static'], [])
            self.assertEqual(r['unsupported']['runtime'], {})


if __name__ == '__main__':
    unittest.main()
