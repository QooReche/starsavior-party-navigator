import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from battlesim import simulate
from battlesim.api import _norm_party
from battlesim.starsavior.data import get_db
from battlesim.mc import Battle
from battlesim.starsavior.guild_bfb import Controller

def strip(x):
    if isinstance(x,dict):
        return {k:strip(v) for k,v in x.items() if 'runtime' not in k and k not in ('elapsed_ms','ms','assumptions_used')}
    if isinstance(x,list): return [strip(v) for v in x]
    return x

events=[]
for method in ('on_wave','after_cast','pre_hit','post_hit','_appeal','_bouquet','_sup_after_cast','_sup_pre_hit','_sup_post_hit'):
    original=getattr(Controller,method)
    def wrap(self,*args,_fn=original,_name=method,**kw):
        result=_fn(self,*args,**kw)
        events.append([_name,self.b.global_turns,[(u.name,u.hp,u.gauge,dict(u.cd),[(n,e.stacks) for n,e in u.eff.items()]) for u in self.b.allies+self.b.foes]])
        return result
    setattr(Controller,method,wrap)

out={}
for sup in ('none','gust','focus','strike','mountain','fire'):
    for lv in (0,1,3,4,6,7,9,10,12):
        for tiers in ([0,0,0,0],[3,3,3,3]):
            events.clear()
            enc={'guild':{'seasonId':30111,'level':lv,'support':sup,'sets':tiers}}
            r=simulate({'units':['gwen','fei','professor-m','amora'],'leader':0},enc,{'seed':3,'n_runs':1,'build':'standard','timeline':True})
            blob=json.dumps([strip(r),events],ensure_ascii=False,sort_keys=True,default=str)
            out[f'{sup}|{lv}|{tiers}']=hashlib.sha256(blob.encode()).hexdigest()
expected=json.loads((Path(__file__).parent/'fixtures/guild_bfb_hooks_6c4d3b0.json').read_text(encoding='utf-8'))
assert out == expected, [k for k in out if out[k] != expected.get(k)]
print(len(out),'hook/timeline cases')
