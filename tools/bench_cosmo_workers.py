"""Real Chromium/Pyodide worker lifecycle and 1/2/4/8 throughput curve.

Run with the Playwright Python. Fixed public-standard battles; no account input.
This is a four-phase workload, not the full large-pool search.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from test_page import test_server
from playwright.sync_api import sync_playwright

MEASURE = """async ({workers,reuse,catalog}) => {
 const GS=GuildSearch,C=CosmoSearch,all=catalog.slice(0,30);
 const results=Object.fromEntries(all.map(r=>[r.key,r])),cls=Object.fromEntries(all.map(r=>[r.key,r.cls]));
 const combos=C.shuffled(GS.combos({minFront:1,minDealer:1},all),891);
 if(combos.length<96)throw Error('empty workload: '+JSON.stringify({charset:document.characterSet,front:GS.FRONT,roles:all.map(r=>r.cls)}));
 const bosses=['belgras','tyria','carnelia'];
 const jobs=combos.slice(0,96).map((keys,i)=>{
  const p=GS.party(keys,results,cls);
  return {key:bosses[i%3]+'|'+C.idOf(keys),party:{units:p.order.map(key=>({key,build:'standard'})),leader:0},
   options:{cosmo_raid:{boss:bosses[i%3],step:3,level:6},cosmo_top_q:.2}};
 });
 let created=0,closed=0,phase=-1;const boots=[],heaps=[];
 const make=()=>{
  created++;const w=new Worker('/local/cosmo-worker-observe.js'),started=performance.now();let handler=null;
  w.onmessage=e=>{if(e.data.type==='stage'&&e.data.msg==='준비 끝')boots.push({phase,ms:performance.now()-started});
   if(e.data.type==='done'&&e.data.heapBytes)heaps.push({phase,bytes:e.data.heapBytes});handler?.(e);};
  return {set onmessage(f){handler=f;},set onerror(f){w.onerror=f;},postMessage:m=>w.postMessage(m),terminate(){closed++;w.terminate();}};
 };
 const pool=reuse?GS.workerPool(make):null,phases=[],outputs=[];
 const counts=[96,48,12,9],runs=[1,1,20,40],seeds=[1,4,3,2];
 try{for(phase=0;phase<4;phase++){
  const start=performance.now();
  const h=GS.runPhase({makeWorker:make,pool,workers,jobs:jobs.slice(0,counts[phase]),runs:runs[phase],seed:seeds[phase],
    stage:'cosmo',base:location.origin+'/',chunk:1});
  const res=await h.promise;
  if(Object.keys(res).length!==counts[phase]||Object.values(res).some(r=>r.n!==runs[phase]||!r.cosmo||!(r.prog>0)))
    throw Error('incomplete/zero-progress battle workload in phase '+phase);
  outputs.push(Object.fromEntries(Object.entries(res).sort(([a],[b])=>a<b?-1:1)));
  const seconds=(performance.now()-start)/1000;
  phases.push({phase,seconds,games:counts[phase]*runs[phase],gamesPerSecond:counts[phase]*runs[phase]/seconds});
 }}finally{pool?.close();}
 return {workers,reuse,created,closed,boots,heaps,phases,outputs,seconds:phases.reduce((s,p)=>s+p.seconds,0)};
}"""


def summarize(samples):
    summary = {}
    for workers in sorted({r['workers'] for r in samples}):
        groups = {}
        for reuse in (False, True):
            rows = [r for r in samples if r['workers'] == workers and r['reuse'] == reuse]
            if not rows:
                continue
            seconds = [r['seconds'] for r in rows]
            # Phases 1..3 reuse initialized workers; finite-job tail remains included.
            warm = [sum(p['games'] for p in r['phases'][1:]) /
                    sum(p['seconds'] for p in r['phases'][1:]) for r in rows]
            groups['reuse' if reuse else 'legacy'] = dict(
                repeats=len(rows), seconds_mean=statistics.mean(seconds),
                seconds_sd=statistics.stdev(seconds) if len(seconds) > 1 else None,
                games_per_second=statistics.mean(sum(p['games'] for p in r['phases']) / r['seconds'] for r in rows),
                later_games_per_second=statistics.mean(warm),
                boot_ms_mean=statistics.mean(b['ms'] for r in rows for b in r['boots']),
                heap_max_bytes=max((h['bytes'] for r in rows for h in r['heaps']), default=None))
        if 'legacy' in groups and 'reuse' in groups:
            groups['speedup'] = groups['legacy']['seconds_mean'] / groups['reuse']['seconds_mean']
        summary[workers] = groups
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', default='local/cosmo-workers.json')
    ap.add_argument('--catalog', default='local/cosmo-rd/catalog.json')
    ap.add_argument('--repeats', type=int, default=3)
    a = ap.parse_args()
    catalog = json.loads(Path(a.catalog).read_text(encoding='utf-8'))
    # Observation-only local copy. Avoid request interception (which disables HTTP cache).
    source = (ROOT / 'sim_worker.js').read_text(encoding='utf-8')
    old = 'postMessage({type:"done",id:m.id})'
    assert source.count(old) == 1
    observed = source.replace(old, 'postMessage({type:"done",id:m.id,heapBytes:p._module.HEAPU8.length})')
    observed = observed.replace('new URL("lib/pyodide/",self.location.href)', 'new URL("/lib/pyodide/",self.location.href)')
    (ROOT / 'local').mkdir(exist_ok=True)
    (ROOT / 'local/cosmo-worker-observe.js').write_text(observed, encoding='utf-8')
    (ROOT / 'local/cosmo-workers.html').write_text('<!doctype html><meta charset="utf-8"><title>Cosmo worker benchmark</title>', encoding='utf-8')
    samples = []
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(base + '/local/cosmo-workers.html')
            assert page.evaluate('document.characterSet') == 'UTF-8'
            page.add_script_tag(url=base+'/ui_shared.js')
            page.add_script_tag(url=base+'/guild_search.js')
            page.add_script_tag(url=base+'/cosmo_search.js')
            # Warm HTTP and OS caches once, not included in measurements.
            page.evaluate("""async()=>{const w=new Worker('/local/cosmo-worker-observe.js');try{await new Promise((ok,no)=>{
              w.onmessage=e=>{if(e.data.type==='done')ok();if(e.data.type==='error')no(Error(e.data.msg));};
              w.onerror=no;w.postMessage({type:'run',id:0,base:location.origin+'/',teams:[]});});}finally{w.terminate();}}""")
            expected = None
            for workers in [1, 2, 4, 8]:
                for repeat in range(a.repeats):
                    for reuse in ([False, True] if repeat % 2 == 0 else [True, False]):
                        r = page.evaluate(MEASURE, dict(workers=workers, reuse=reuse, catalog=catalog))
                        assert r['created'] > 0 and r['boots'] and r['heaps'], 'no actual workers observed'
                        packed = json.dumps(r.pop('outputs'), sort_keys=True, separators=(',', ':'))
                        r['sha256'] = hashlib.sha256(packed.encode()).hexdigest()
                        if expected is None:
                            expected = r['sha256']
                        assert r['sha256'] == expected, 'result changed with worker count/reuse'
                        assert r['created'] == r['closed']
                        r['repeat'] = repeat
                        samples.append(r)
                        print(json.dumps(r), flush=True)
                        Path(a.output).write_text(json.dumps(dict(browser=browser.version, samples=samples,
                                                                 summary=summarize(samples)), indent=2), encoding='utf-8')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
