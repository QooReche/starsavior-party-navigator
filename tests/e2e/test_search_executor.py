"""Small real Pyodide golden and guild before/after benchmark; one browser, <=2 workers."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server
from test_direct_party import ready

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT/'tests/fixtures/search_pyodide_6688d7a.json'

REAL = """async () => {
 const requests=[], replies=[];
 const makeWorker=()=>{const w=new Worker('sim_worker.js'),post=w.postMessage.bind(w);
   w.postMessage=m=>{requests.push(m);post(m)};return w;};
 const party={units:['luna','smile','carnelia','bell'].map(key=>({key,build:'standard'})),leader:0};
 const h=GuildSearch.runPhase({makeWorker,jobs:[{key:'golden',party,options:{raw_runs:true}}],workers:1,runs:2,seed:20261121,
  stage:'clo/달 회랑/FLOOR 100',base:new URL('.',location.href).href,onResult:(key,r)=>replies.push([key,r])});
 const result=await h.promise;requests.forEach(m=>{delete m.base;delete m.id});
 return {requests,replies,result};
}"""

BENCH = """async allPhases => {
 const G=D.guild,S=structuredClone(G.search),keys=['luna','smile','carnelia','bell','emily'];
 const roster=R.filter(r=>keys.includes(r.key));if(roster.length!==5)throw Error('synthetic roster changed');
 const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:10000-i*100,stats:{hp:100000,atk:10000,def:2000,spd:120,cri:20,cdmg:50,acc:100,eva:0},combat:{}}]));
 Object.assign(S,{poolSize:5,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,excluded:[],banCoop:false,finalists:1});
 S.screen={...S.screen,runs:1};S.screen2={keep:2,runs:1};S.final={...S.final,levels:[0,2],supports:['none'],runs:1};
 const phases=[],workers=[],start=performance.now();let phase;
 const makeWorker=()=>{const raw=new Worker('sim_worker.js'),w={raw,busy:null,spans:[],born:performance.now()};workers.push(w);
  return {postMessage(m){w.busy=performance.now();raw.postMessage(m)},terminate(){w.end=performance.now();raw.terminate()},
   set onmessage(fn){raw.onmessage=e=>{if(e.data.type==='done'&&w.busy!=null){w.spans.push([w.busy,performance.now()]);w.busy=null}fn(e)}},
   set onerror(fn){raw.onerror=fn}};};
 const c=contents.find(c=>c.key==='guild'),st=c.stages[0];
 const oldBreakRuns=GuildSearch.BREAK_CHECK.runs;
 if(allPhases)GuildSearch.BREAK_CHECK.runs=1;
 let out;
 try{out=await GuildPlanner.search({S,G,V:GuildView,roster,results,tiers:[0,0,0,0],breaks:allPhases?[{name:'스타피어서',level:1}]:[],workers:2,makeWorker,
  stage:'guild/'+st.tab+'/'+st.name,base:new URL('.',location.href).href,
  onPhase(msg,jobs){const now=performance.now();if(phase)phase.end=now;phase={msg,jobs,start:now};phases.push(phase)}});
 }finally{GuildSearch.BREAK_CHECK.runs=oldBreakRuns;}
 const end=performance.now();phase.end=end;
 const timings=phases.map(p=>{const elapsed=p.end-p.start,busy=workers.reduce((sum,w)=>sum+w.spans.reduce((n,[a,b])=>n+Math.max(0,Math.min(b,p.end)-Math.max(a,p.start)),0),0);
  return {phase:p.msg,jobs:p.jobs,elapsedMs:elapsed,busyMs:busy,idleMs:Math.max(0,2*elapsed-busy)};});
 if(!out.rows.length||!out.rows.every(r=>r.prog>0))throw Error('no positive simulation');
 return {totalMs:end-start,workers:2,settings:S,keys:roster.map(r=>r.key),allPhases,breakRuns:allPhases?1:null,timings,out};
}"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--capture',action='store_true')
    ap.add_argument('--bench',type=Path)
    ap.add_argument('--legacy',action='store_true')
    ap.add_argument('--all-phases',action='store_true')
    a=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=ready(browser,base,info=None,query='?auto=0',setup=lambda p:p.add_init_script("Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>3});Object.defineProperty(navigator,'deviceMemory',{get:()=>2});"))
            if a.legacy:
                page.add_script_tag(content=subprocess.check_output(['git','show','6688d7a:guild_search.js'],cwd=ROOT,text=True,encoding='utf8'))
                page.add_script_tag(content=subprocess.check_output(['git','show','6688d7a:guild_planner.js'],cwd=ROOT,text=True,encoding='utf8'))
            if a.bench:
                result=page.evaluate(BENCH,a.all_phases)
                result['revision']='6688d7a' if a.legacy else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
                result['sourceHashes']={p:hashlib.sha256(subprocess.check_output(['git','show','6688d7a:'+p],cwd=ROOT) if a.legacy else (ROOT/p).read_bytes()).hexdigest() for p in ['guild_search.js','guild_planner.js']}
                if not a.legacy and (ROOT/'search_executor.js').exists():
                    result['sourceHashes']['search_executor.js']=hashlib.sha256((ROOT/'search_executor.js').read_bytes()).hexdigest()
                result['engine']=json.loads((ROOT/'sim/manifest.json').read_text(encoding='utf8'))['ver']
                a.bench.parent.mkdir(parents=True,exist_ok=True)
                a.bench.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
                print('PASS guild reduced real Pyodide benchmark',round(result['totalMs'],1),'ms',flush=True)
            else:
                result=page.evaluate(REAL)
                result['pins']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['sim/manifest.json','battlesim/rules/default.json']}
                assert result['result']['golden']['prog']>0
                if a.capture:
                    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip().startswith('6688d7a')
                    FIXTURE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
                else:
                    expected=json.loads(FIXTURE.read_text(encoding='utf8'))
                    assert result==expected,'real Pyodide complete request/raw result changed'
                print('PASS real Pyodide frozen request, complete raw result, positive progress',flush=True)
            assert not page.errors,page.errors
        finally:browser.close()

if __name__=='__main__':main()

