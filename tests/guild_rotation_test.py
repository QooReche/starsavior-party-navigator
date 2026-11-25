"""시즌 정의→실제 전투/지원/점수 경계. 합성 입력만 사용하며 순차 실행함."""
import copy
import json
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'tests')]
from simkit import unit, battle
from battlesim import simulate
from battlesim.mc import Battle, Ctx
from battlesim.starsavior.guild import load, build_waves, base_points
from battlesim.starsavior.guild_support import Support


def support(sid, ident, role):
    definition = next(s for s in load(sid)['supports'] if s['id']==ident)
    b = battle([unit('owner',role=role,atk=10000,skills=[dict(slot='기본기',dm=100),dict(slot='특수기',dm=100,cd=3)]),
                unit('ally',atk=20000)], [unit('foe',hp=10**8,sa=10),unit('foe2',hp=10**8,sa=10)])
    return b,Support(b,definition),b.allies[0]


class GuildRotationTest(unittest.TestCase):
    def test_archives_and_version_gate(self):
        import guild_defense as gd
        for sid in range(30101,30112):
            g=load(sid)
            self.assertEqual(g['season']['id'],sid)
            self.assertEqual(g['provenance']['build'],'26752678')
            self.assertEqual(gd.validate(g),[])
            self.assertIn('dataVersion',gd.page_payload(g))
        self.assertEqual(load()['season']['id'],30111)
        with self.assertRaisesRegex(ValueError,'자료 버전'):
            build_waves({'seasonId':30101,'dataVersion':'wrong'})
        with self.assertRaisesRegex(ValueError,'보관되지 않은'):
            build_waves({'seasonId':30112})

    def test_boss_kill_actual_original_layout_and_mutation(self):
        for sid in (30101,30102,30104):
            waves,meta=build_waves({'seasonId':sid,'step':6})
            outcomes=[]
            for mode in (meta['battle_mode'],'all_kill'):
                b=Battle([unit(hp=10**9)], [waves[-1]],random.Random(3),battle_mode=mode)
                b.spawn_wave()
                boss=next(u for u in b.foes if u.d.boss)
                self.assertEqual(boss.d.game_slot,2)
                self.assertEqual(boss.cd['특수기'],0)
                self.assertEqual(boss.cd['궁극기'],0,'불타는 엔진의 웨이브 시작 초기화')
                b.kill(boss,b.allies[0])
                outcomes.append(all(u.dead for u in b.foes))
            self.assertEqual(outcomes,[True,False],'all_kill로 바꾸면 원래 배치 졸개가 남아야 함')

    def test_all_bosses_and_all_support_ids_smoke(self):
        # 서로 다른 보스·배치·지원으로 실제 경로를 실행한다.
        for sid in range(30101,30111):
            g=load(sid)
            for sup in ['none']+[str(s['id']) for s in g['supports']]:
                r=simulate(['gwen','fei','professor-m','amora'],{'guild':{'seasonId':sid,'support':sup}},
                           {'build':'standard','n_runs':1,'seed':3})
                self.assertGreater(r['outcome']['progress'],0,(sid,sup))
                self.assertEqual(r['unsupported']['static_count'],0,(sid,sup))
                self.assertEqual(r['unsupported']['runtime'],{},(sid,sup))
                self.assertGreater(r['guild']['base_scores'][0],g['steps'][-1]['base'])

    def test_support_promotions_use_season_values(self):
        for sid,ident,role,prop,value in ((30101,40032,'캐스터','cr',.5),(30102,40042,'어쌔신','cd',1),
                                         (30104,40112,'스트라이커','cd',.5),(30108,40242,'어쌔신','atkp',.5)):
            b,s,u=support(sid,ident,role)
            before=u.mods().get(prop,0)
            s.start()
            self.assertAlmostEqual(u.mods().get(prop,0)-before,value,msg=(sid,ident))
            # 역할 밖 아군에는 해당 지원이 걸리지 않음(스트라이커 지원은 제외).
            if role!='스트라이커':self.assertFalse(any(k.startswith('길드 지원:') for k in b.allies[1].eff))

    def test_support_target_set_and_mutation(self):
        for sid,ident,role in ((30102,40021,'레인저'),(30104,40131,'캐스터')):
            for reverse in (False,True):
                b,s,u=support(sid,ident,role)
                v=b.foes[1]
                b.put_eff(v,'연소',{},src=u,cat='debuff')
                v.sa=0;v.broken=True
                sk=copy.copy(u.d.skills['기본기']);sk.all=True
                ctx=Ctx(u,u,sk);ctx.targets=list(reversed(b.foes)) if reverse else b.foes[:];ctx.target=ctx.targets[0]
                s.event('NSEAT_SKILL_START',u,ctx,ctx.target,ctx)
                self.assertAlmostEqual(u.mods()['inc'] if ident==40021 else u.mods()['inc_break'],.3)
                s.clear(ctx)
                self.assertEqual(u.mods()['inc'] if ident==40021 else u.mods()['inc_break'],0)
                with patch.object(s,'event',return_value=None):
                    s.event('NSEAT_SKILL_START',u,ctx,ctx.target,ctx)
                    with self.assertRaises(AssertionError):
                        self.assertAlmostEqual(u.mods()['inc'] if ident==40021 else u.mods()['inc_break'],.3)

    def test_support_cooldown_and_revive(self):
        b,s,u=support(30101,40032,'캐스터')
        ctx=Ctx(u,u,u.d.skills['기본기']);ctx.target=b.foes[0];ctx.targets=[ctx.target]
        u.cd['특수기']=3
        s.event('NSEAT_SKILL_START',u,ctx,ctx.target,ctx)
        self.assertEqual(u.cd['특수기'],2)
        s.event('NSEAT_SKILL_START',u,ctx,ctx.target,ctx)
        self.assertEqual(u.cd['특수기'],2)
        b.kill(u,b.foes[0])
        revive=Ctx(b.allies[1],b.allies[1],b.allies[1].d.skills["기본기"]);revive.target=u;revive.targets=[u]
        b.run_special(b.allies[1],None,revive,'스킬 대상에게 부활(생명력 50%)')
        self.assertFalse(u.dead)
        s.event('NSEAT_SKILL_START',u,ctx,ctx.target,ctx)
        self.assertEqual(u.cd['특수기'],1)

    def test_support_auto_targets_and_enforce(self):
        b,s,u=support(30108,40161,'디펜더')
        s.start()
        low=b.allies[1];low.hp=100
        ctx=Ctx(u,u,u.d.skills['기본기']);ctx.targets=[b.foes[0]];ctx.target=ctx.targets[0]
        s.event('NSEAT_SKILL_END',u,ctx,ctx.target,ctx)
        self.assertEqual(low.shield_total(),u.maxhp*.08)
        self.assertEqual(u.shield_total(),0)
        b,s,u=support(30101,40061,'디펜더')
        ctx=Ctx(u,u,u.d.skills['기본기']);ctx.targets=[b.foes[0]];ctx.target=ctx.targets[0]
        calls=[]
        with patch.object(b,'cast',side_effect=lambda actor,sk,**kw:calls.append((actor,sk,kw))):
            s.event('NSEAT_SKILL_END',u,ctx,ctx.target,ctx)
            s.event('NSEAT_SKILL_END',u,ctx,ctx.target,ctx)
        self.assertEqual(len(calls),1)
        self.assertIs(calls[0][0],b.allies[1])
        self.assertEqual(calls[0][2]['via'],'forced_coop')
        self.assertIn(calls[0][2]['target'],b.foes)

    def test_battle_start_hp_support_fills_new_maximum(self):
        for sid,ident in ((30101,40061),(30108,40161)):
            b,s,u=support(sid,ident,'디펜더')
            before=u.maxhp;other=b.allies[1].hp
            s.start()
            self.assertEqual(u.maxhp,before*1.3)
            self.assertEqual(u.hp,u.maxhp)
            self.assertEqual(b.allies[1].hp,other)
            u.hp-=100
            s.start()
            self.assertEqual(u.hp,u.maxhp-100,'시작 이벤트는 한 번만 실행함')

    def test_support_hit_before_nullifier_and_mutation(self):
        from battlesim.starsavior.guild_common import Controller
        sid=next(sid for sid in range(30101,30111) if any(s['id']==40142 for s in load(sid)['supports']))
        heals=[]
        for enabled in (True,False):
            b,s,u=support(sid,40142,'어쌔신')
            controller=Controller.__new__(Controller);controller.b=b;controller.client_support=s;controller.bosses=[]
            b.gb=controller
            u.hp=100
            target=b.foes[0]
            b.put_eff(target,'스킬 피해 무효',{},src=target,cat='buff')
            if not enabled:controller.hit_start=lambda *a:None
            b.cast(u,u.d.skills['기본기'],target=target)
            self.assertEqual(target.taken,0)
            self.assertEqual(u.mods()['vampirism'],0,'시전 종료 뒤 임시 지원을 제거함')
            heals.append(u.hp-100)
        self.assertGreater(heals[0],0)
        self.assertEqual(heals[1],0)

    def test_worker_merge_preserves_real_scores(self):
        from battlesim.web import run_auto
        party={'units':['gwen','fei','professor-m','amora']}
        options={'guild':{'seasonId':30101},'build':'standard','raw_runs':True}
        one=json.loads(run_auto('guild/과거/6단계',party,2,3,options))
        first=json.loads(run_auto('guild/과거/6단계',party,1,3,options))
        second=json.loads(run_auto('guild/과거/6단계',party,1,3,dict(options,run_offset=1,merge_raw=first['raw'])))
        self.assertEqual(second['guild'],one['guild'])
        self.assertEqual(second['progs'],one['progs'])
        self.assertGreater(second['prog'],0)

    def test_base_score_per_boss_and_real_kills(self):
        b=battle([unit()], [unit('b1',hp=10000),unit('b2',hp=10000),unit('elite'),unit('mob')])
        for u in b.foes[:2]:u.d.boss=True
        b.foes[0].hp=9999;b.foes[1].hp=5000
        b.foes[2].d.grade='정예';b.foes[2].dead=True
        points=dict(base=10,bossKill=25000,kill=3,eliteKill=7)
        self.assertEqual(base_points(b,points),10+2+12500+7)
        b.foes[3].dead=True
        self.assertEqual(base_points(b,points),10+2+12500+7+3)


if __name__=='__main__':unittest.main()
