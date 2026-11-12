"""Sequential real Pyodide comparison and one production-policy full search."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'local/measure_1112'
OLD = ROOT / 'local/measure_1112_old'
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests/e2e'), str(ROOT)]
import bench_cosmo_workers as bench
import test_page
from measure_cosmo_1112 import summary
from playwright.sync_api import sync_playwright


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def prepare(root):
    source = (root / 'sim_worker.js').read_text(encoding='utf-8')
    old = 'postMessage({type:"done",id:m.id})'
    assert source.count(old) == 1
    source = source.replace(old, 'postMessage({type:"done",id:m.id,heapBytes:p._module.HEAPU8.length})')
    source = source.replace('new URL("lib/pyodide/",self.location.href)', 'new URL("/lib/pyodide/",self.location.href)')
    (root / 'local').mkdir(exist_ok=True)
    (root / 'local/cosmo-worker-observe.js').write_text(source, encoding='utf-8')
    (root / 'local/cosmo-workers.html').write_text('<!doctype html><meta charset="utf-8"><title>Measurement</title>', encoding='utf-8')


def page_at(browser, base):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(4 * 3600 * 1000)
    page.goto(base + '/local/cosmo-workers.html')
    assert page.evaluate('document.characterSet') == 'UTF-8'
    for file in ('guild_search.js', 'cosmo_search.js'):
        page.add_script_tag(url=base + '/' + file)
    return context, page


WARM = """async()=>{const w=new Worker('/local/cosmo-worker-observe.js');try{await new Promise((ok,no)=>{
 w.onmessage=e=>{if(e.data.type==='done')ok();if(e.data.type==='error')no(Error(e.data.msg));};
 w.onerror=no;w.postMessage({type:'run',id:0,base:location.origin+'/',teams:[]});});}finally{w.terminate();}}"""


FULL = """async({catalog,G})=>{
 const GS=GuildSearch,C=CosmoSearch,S=G.search,roster=catalog.slice(0,30);
 const results=Object.fromEntries(roster.map(r=>[r.key,r]));
 const env={cores:navigator.hardwareConcurrency,memGB:navigator.deviceMemory,mobile:false};
 const workers=C.workerCount(S,env),boots=[],heaps=[],phases=[];
 let created=0,closed=0,phase=-1,plan;
 const party=GS.party,runPhase=GS.runPhase;
 GS.party=(...args)=>{const p=party(...args);p.spec={units:p.order.map(key=>({key,build:'standard'})),leader:0};return p;};
 const makeWorker=()=>{created++;const w=new Worker('/local/cosmo-worker-observe.js'),start=performance.now();let handler;
  w.onmessage=e=>{if(e.data.type==='stage'&&e.data.msg==='준비 끝')boots.push({phase,ms:performance.now()-start});
   if(e.data.type==='done'&&e.data.heapBytes)heaps.push({phase,bytes:e.data.heapBytes});handler?.(e);};
  return {set onmessage(f){handler=f;},set onerror(f){w.onerror=f;},postMessage:m=>w.postMessage(m),terminate(){closed++;w.terminate();}};};
 GS.runPhase=o=>{const start=performance.now(),index=++phase,h=runPhase(o);
  console.log('MEASURE '+JSON.stringify({startPhase:index,teams:o.jobs.length,runs:o.runs,workers:o.workers,chunk:o.chunk}));
  return {cancel:()=>h.cancel(),promise:h.promise.then(res=>{
   if(Object.keys(res).length!==o.jobs.length||Object.values(res).some(r=>r.n!==o.runs||!r.cosmo))throw Error('incomplete full phase');
   const positive=Object.values(res).filter(r=>r.prog>0).length;if(!positive)throw Error('zero progress phase');
   const row={phase:index,seconds:(performance.now()-start)/1000,teams:o.jobs.length,runs:o.runs,games:o.jobs.length*o.runs,positive};
   phases.push(row);console.log('MEASURE '+JSON.stringify(row));return res;})};};
 const start=performance.now();
 try{const result=await C.search({S,bosses:G.season.bossOrder,mode:'top',level:6,results,roster,workers,makeWorker,
   stage:'cosmo',base:location.origin+'/',onPlan:p=>{plan=p;console.log('MEASURE '+JSON.stringify({plan:p,workers,env}));},
   onProgress:(done,total)=>{if(done%5000===0)console.log('MEASURE '+JSON.stringify({phase,done,total,seconds:(performance.now()-start)/1000}));}});
  if(!result.rows.length||created!==closed)throw Error('empty result or worker leak');
  return {seconds:(performance.now()-start)/1000,workers,env,plan,created,closed,boots,heaps,phases,result};
 }finally{GS.party=party;GS.runPhase=runPhase;}
}"""


def compare(browser, rows):
    samples, pairs, expected = [], [], {}
    for i in range(10):
        arm_times = {'A': [], 'B': []}
        for visit, label in enumerate('ABBA' if i % 2 == 0 else 'BAAB'):
            root = OLD if label == 'A' else ROOT
            test_page.ROOT = str(root)
            prepare(root)
            with test_page.test_server() as base:
                context, page = page_at(browser, base)
                try:
                    page.evaluate(WARM)
                    for repeat in range(1):
                        r = page.evaluate(bench.MEASURE, dict(workers=1, reuse=True, catalog=rows))
                        assert r['created'] == r['closed'] == 1 and r['boots'] and r['heaps']
                        packed = json.dumps(r.pop('outputs'), sort_keys=True, separators=(',', ':'))
                        r.update(pair=i+1, label=label, repeat=repeat, visit=visit, sha256=hashlib.sha256(packed.encode()).hexdigest())
                        expected.setdefault(label, r['sha256'])
                        assert expected[label] == r['sha256']
                        samples.append(r)
                        arm_times[label].append(r['seconds'])
                        save('browser-raw.json', dict(browser=browser.version, samples=samples))
                        print(json.dumps({k:v for k,v in r.items() if k not in ('heaps','boots')}), flush=True)
                finally:
                    context.close()
            # All workers closed before changing revision.
        pairs.append({label:statistics.mean(v) for label,v in arm_times.items()})
    save('browser-summary.json', dict(browser=browser.version, pairs=pairs, summary=summary(pairs), hashes=expected))


def full(browser, rows):
    # Import the already installed base-interpreter psutil; same CPython ABI as this venv.
    sys.path.append(str(Path(sys.base_prefix) / 'Lib/site-packages'))
    import psutil
    prepare(ROOT)
    test_page.ROOT = str(ROOT)
    G = json.loads((ROOT / 'data/cosmo_raid.json').read_text(encoding='utf-8'))
    with test_page.test_server() as base:
        # CDP gives this browser's PID, then psutil follows only its descendants.
        cdp = browser.new_browser_cdp_session()
        info = cdp.send('SystemInfo.getProcessInfo')['processInfo']
        pid = next(int(p['id']) for p in info if p['type'] == 'browser')
        parent = psutil.Process(pid)
        stop = threading.Event()
        memory = []
        def monitor():
            start = time.perf_counter()
            while not stop.is_set():
                rss = private = count = 0
                for p in [parent] + parent.children(recursive=True):
                    try:
                        m = p.memory_info()
                        rss += m.rss
                        private += m.private
                        count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                memory.append(dict(seconds=time.perf_counter()-start,rss=rss,private=private,processes=count,
                                   available=psutil.virtual_memory().available))
                stop.wait(.5)
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        context = None
        try:
            start = time.perf_counter()
            context, page = page_at(browser, base)
            page.on('console', lambda m: print(m.text, flush=True) if m.text.startswith('MEASURE ') else None)
            page_load = time.perf_counter()-start
            r = page.evaluate(FULL, dict(catalog=rows,G=G))
            r.update(browser=browser.version,page_load_s=page_load,browser_launch_s=BROWSER_LAUNCH_S)
            packed=json.dumps(r.pop('result'),sort_keys=True,separators=(',',':'),ensure_ascii=False)
            (OUT / 'full-result.json').write_text(packed,encoding='utf-8')
            r['sha256']=hashlib.sha256(packed.encode()).hexdigest()
            save('full.json',r)
            print(json.dumps({k:v for k,v in r.items() if k not in ('heaps','boots')}),flush=True)
        finally:
            stop.set()
            thread.join(timeout=5)
            save('full-memory.json',dict(interval_s=.5,samples=memory,peak_rss=max(m['rss'] for m in memory),
                 peak_private=max(m['private'] for m in memory),min_available=min(m['available'] for m in memory)))
            if context: context.close()


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('task',choices=['compare','full'])
    a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    catalog_path=OUT/'catalog.json'
    if not catalog_path.exists():
        # Freeze the pre-acceleration roster so newer units cannot enter one arm only.
        code='import sys,json;sys.path.insert(0,sys.argv[1]);from tools.bench_cosmo_search import catalog;print(json.dumps(catalog(),ensure_ascii=False))'
        raw=subprocess.check_output([sys.executable,'-X','utf8','-I','-c',code,str(OLD)],cwd=OLD)
        save('catalog.json',json.loads(raw))
    rows=json.loads(catalog_path.read_text(encoding='utf-8'))
    with sync_playwright() as pw:
        launch_start=time.perf_counter()
        browser=pw.chromium.launch(headless=True)
        BROWSER_LAUNCH_S=time.perf_counter()-launch_start
        try:
            globals()[a.task](browser, rows)
        finally:
            browser.close()
