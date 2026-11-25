"""시즌 정의의 지원 SE 실행. BFB 보관 실행기는 종전 훅을 유지한다."""
import math


class Support:
    def __init__(self, battle, definition):
        self.b, self.d = battle, definition
        self.started = False
        self.temporary = {}

    def eligible(self, u):
        return self.d and u.side == 0 and not u.dead and (not self.d['role'] or u.role == self.d['role'])

    def start(self):
        if self.started: return
        self.started = True
        for u in self.b.allies: self.event('NSEAT_BATTLE_START', u)

    def clear(self, scope):
        for x, name, old in reversed(self.temporary.pop(scope, [])):
            x.eff.pop(name, None)
            if old is not None: x.eff[name] = old
            self.b.dirty(x)

    def event(self, phase, u, ctx=None, target=None, scope=None):
        if not self.eligible(u): return
        b = self.b
        sk = ctx.skill if ctx else None
        for e in self.d['effects']:
            if e['phase'] != phase: continue
            x = e['execution']; c = x['checks']
            if c.get('event') == 'OnMyAttack' and (not sk or not sk.is_attack): continue
            if c.get('event') == 'AfterMyNonAttack' and (not sk or sk.is_attack): continue
            if c.get('SkillIndex'):
                slots = {'NSI_SKILL_1_ATTACK':'기본기','NSI_SKILL_2_SPECIAL':'특수기','NSI_SKILL_3_HYPER':'궁극기'}
                if not sk or sk.slot != slots[c['SkillIndex']]: continue
            if c.get('SelfPositiveBuff') and not u.n_good(): continue
            if c.get('TargetNegativeBuff') and not any(v.n_harmful() for v in (ctx.targets if ctx else ())): continue
            if c.get('EnemyNegativeBuff') and (target is None or not target.n_harmful()): continue
            if c.get('IsNotTargetSuperArmor') and not any(v.sa <= 0 for v in (ctx.targets if ctx else ())): continue
            if x['hpOver'] is not None and u.hp * 10000 <= u.maxhp * x['hpOver']: continue
            if x['hpLess'] is not None and u.hp * 10000 >= u.maxhp * x['hpLess']: continue
            key = (id(u), 'guild:'+e['id'])
            # NKM:3534-3560·3604-3617: 주인의 턴 종료에서 차감.
            if b.recast.get(key, -math.inf) + x['cooldown'] > u.turn_ends: continue
            if e['chance'] < 10000 and b.R(u.side).random() >= e['chance'] / 10000: continue
            b.recast[key] = u.turn_ends
            if e['target'] == 'NSETT_SELF': targets = [u]
            elif e['target'] == 'NSETT_MYTEAM_ALL_NOT_SELF': targets = [v for v in b.alive(u.side) if v is not u]
            else:
                pool = b.alive(u.side)
                targets = [b.filter_pick(u, pool, x['filters'], ctx)] if pool else []
            for v in targets:
                op = x['op']
                if op == 'stat':
                    name = '길드 지원:' + e['id']
                    props = {k: val * (u.n_good() if x['buffCount'] else 1) for k,val in x['props'].items()}
                    # 0턴 비버프 수치는 해당 스킬/피격 문맥 종료까지 적용한다.
                    temporary = not x['permanent'] and not x['positive']
                    if temporary:
                        old = v.eff.pop(name, None)
                        self.temporary.setdefault(scope, []).append((v,name,old))
                    b.put_eff(v, name, props, dur=math.inf if x['permanent'] or temporary else e['duration'],
                              maxs=e['maxStacks'], src=u, cat='buff' if x['positive'] else 'marker', fixed=x['fixed'], dead_keep=x['permanent'])
                    # NKM:4494→2916→3070-3080. Start 상태에서 스탯 갱신 뒤 현재 HP를 최대치로 채움.
                    if phase == 'NSEAT_BATTLE_START': v.hp = v.maxhp
                elif op == 'cooldown':
                    for slot in ([x['slot']] if x.get('slot') else v.cd): v.cd[slot] = max(0,v.cd[slot]-x['value'])
                elif op == 'gauge': b.set_gauge(v,v.gauge+x['value'])
                elif op == 'nova': b.nova_add(v,x['value'])
                elif op == 'barrier':
                    from ..mc import Ctx
                    c2 = Ctx(u,u,sk); c2.target,c2.targets = v,[v]
                    b.run_special(u,None,c2,'스킬 대상에게 〈보호막〉 (%d턴) 보호막 = 자신 생명력×%g%%' % (e['duration'],x['value']))
                elif op == 'enforce':
                    def cast(v=v,x=x):
                        pool = b.alive(1-v.side)
                        if v.dead or not pool: return
                        target = b.filter_pick(v,pool,x['enforceFilters'])
                        return b.cast(v,v.d.skills[x['slot']],target=target,extra=True,via='enforce' if v is u else 'forced_coop',parent=ctx)
                    if not b._defer_extra(cast): cast()
                else: raise ValueError('미지원 길드 지원 실행: ' + op)
