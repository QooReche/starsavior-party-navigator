"""Full account guild policy with actual Pyodide workers; private append-only journal.

Run with the Playwright Python: ACCOUNT PRIVATE_DIR [--new].
No account normalization from synthetic e2e helpers is applied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from test_page import test_server
from test_direct_party import ready
from playwright.sync_api import sync_playwright

RUN = r"""async ({info,newSearch,previous,resumed}) => {
 await miGrowth();
 const G=D.guild,S=structuredClone(G.search),results=MyInfoReco.profile(info,R,MI.growth,'op').results;
 S.newSearch=newSearch;
 const c=contents.find(c=>c.key==='guild'),st=c.stages.find(s=>parseInt(s.name,10)===G.steps.find(s=>s.ex).step);
 const breaks=Object.entries(MyInfoImport.mapBreak(info)||{}).filter(([n])=>CFG.breakSupported.includes(n)).map(([name,level])=>({name,level}));
 const stage='guild/'+st.tab+'/'+st.name,tiers=[0,0,0,0],original=GuildSearch.runPhase,phases=[];
 let phase,name='',active=0,maxWorkers=0,last=0;
 const start=performance.now();
 const makeWorker=()=>{
  if(++active>2)throw Error('worker limit exceeded');maxWorkers=Math.max(active,maxWorkers);
  const raw=SearchExecutor.createWorker();let busy=null,assigned,closed=false;
  return {postMessage(m){busy=performance.now();assigned=phase;raw.postMessage(m)},
   terminate(){if(!closed){closed=true;active--;raw.terminate()}},
   set onmessage(fn){raw.onmessage=e=>{if(e.data.type==='done'&&busy!==null){assigned.busyMs+=performance.now()-busy;busy=null}fn(e)}},
   set onerror(fn){raw.onerror=fn}};
 };
 GuildSearch.runPhase=o=>{
  const begin=performance.now();phase={index:phases.length,name,jobs:o.jobs.length,runs:o.runs,seed:o.seed,busyMs:0,gapMs:begin-(phases.at(-1)?.endMs??start)};
  const record=phase,cached=previous[record.index]||{},missing=o.jobs.filter(j=>!cached[j.key]);record.cached=o.jobs.length-missing.length;
  phases.push(record);window.recordGuild({type:'phase',...record});
  const h=original({...o,jobs:missing,onResult:(key,r)=>{const result={prog:r.prog??0,clear:r.clear,n:r.n,via:r.via||{},progs:r.progs||null,cosmo:r.cosmo||null,...GuildSearch.unsupportedFields(r)};window.recordGuild({type:'result',phase:record.index,key,result});o.onResult?.(key,r)},
   onProgress:(done,total)=>{o.onProgress?.(done+record.cached,o.jobs.length);if(performance.now()-last>60000){last=performance.now();window.recordGuild({type:'progress',phase:record.index,done,total})}}});
  return {cancel:()=>h.cancel(),promise:h.promise.then(r=>{record.endMs=performance.now();record.elapsedMs=record.endMs-begin;record.idleMs=Math.max(0,2*record.elapsedMs-record.busyMs);window.recordGuild({type:'phaseDone',...record});return {...cached,...r}})};
 };
 try{
  const result=await GuildPlanner.search({S,G,V:GuildView,results,roster:R,tiers,breaks,stage,base:new URL('.',location.href).href,workers:2,makeWorker,onPhase:m=>name=m});
  delete result.growthOwned;
  return {seconds:(performance.now()-start)/1000,phases,result,settings:S,season:G.season,stage,tiers,breaks,maxWorkers,active,transport:'actual browser Pyodide',resumed};
 }finally{GuildSearch.runPhase=original;}
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('account', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--new', action='store_true')
    a = ap.parse_args()
    output = a.output.resolve()
    if output == ROOT or output.is_relative_to(ROOT):
        ap.error('private output must be outside repository')
    output.mkdir(parents=True, exist_ok=True)
    files = ['index.html', 'guild_planner.js', 'guild_search.js', 'search_executor.js',
             'cosmo_learned.js', 'party_placement.js', 'sim/manifest.json', 'sim_worker.js',
             'data/growth.json', 'tools/measure_guild_browser.py']
    pins = dict(accountHash=hashlib.sha256(a.account.read_bytes()).hexdigest(), newSearch=a.new,
                sources={f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files})
    pinfile = output/'pins.json'
    if pinfile.exists() and json.loads(pinfile.read_text(encoding='utf8')) != pins:
        ap.error('input/source mismatch: use a new output directory')
    if (output/'result.json').exists():
        print('existing complete browser measurement', flush=True)
        return
    previous = {}
    journal_path = output/'events.jsonl'
    resumed = journal_path.exists()
    if resumed:
        for line in journal_path.read_text(encoding='utf8').splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event['type'] == 'result':
                previous.setdefault(str(event['phase']), {})[event['key']] = event['result']
        with journal_path.open('a', encoding='utf8') as repair:
            repair.write('\n')
    pinfile.write_text(json.dumps(pins, indent=2), encoding='utf8')
    info = json.loads(a.account.read_text(encoding='utf-8-sig'))
    started = time.monotonic()
    with (output/'events.jsonl').open('a', encoding='utf8', buffering=1) as journal:
        def record(_source, event):
            journal.write(json.dumps(event, ensure_ascii=False)+'\n')
            if event['type'] != 'result':
                print(json.dumps(event, ensure_ascii=False), flush=True)
            if event['type'] == 'phaseDone':
                (output/'progress.json').write_text(json.dumps(dict(lastPhase=event, wallSeconds=time.monotonic()-started), ensure_ascii=False, indent=2), encoding='utf8')
        with test_server() as base, sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = ready(browser, base, info=None, query='?auto=0', setup=lambda p: p.add_init_script("Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>3});Object.defineProperty(navigator,'deviceMemory',{get:()=>2});"))
                page.expose_binding('recordGuild', record)
                result = page.evaluate(RUN, dict(info=info, newSearch=a.new, previous=previous, resumed=resumed))
                result.update(pins=pins, browser=browser.version)
                assert result['maxWorkers'] <= 2 and result['active'] == 0
                assert result['result']['rows'][0]['prog'] > 0
                assert not page.errors, page.errors
                temporary = output/'result.json.tmp'
                temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
                temporary.replace(output/'result.json')
                print('complete browser minutes', round(result['seconds']/60, 3), flush=True)
            finally:
                browser.close()


if __name__ == '__main__':
    main()
