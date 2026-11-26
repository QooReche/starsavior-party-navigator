"""One fresh real-Pyodide search: cosmo, daily2, daily3 (run in that order).

ACCOUNT PRIVATE_DIR MODE; --environment-only records unmodified browser defaults.
No account normalization, worker override, replay or synthetic battle response.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from test_page import test_server
from playwright.sync_api import sync_playwright

RUN = r"""async ({info,mode})=>{
 await miGrowth();
 const env={cores:navigator.hardwareConcurrency,memGB:navigator.deviceMemory,mobile:csMobile()};
 const daily=mode!=='cosmo',G=daily?D.guild:D.cosmoRaid;
 const S=daily?structuredClone(G.search):CosmoSearch.searchSettings(G.search,G.search.learned.value);
 if(daily)S.preset='daily';
 const workers=CosmoSearch.workerCount(daily?S.daily:S,env);
 const results=MyInfoReco.profile(info,R,MI.growth,daily?'op':'cosmo').results;
 const breaks=Object.entries(MyInfoImport.mapBreak(info)||{}).filter(([n])=>CFG.breakSupported.includes(n)).map(([name,level])=>({name,level}));
 let active=0,maxWorkers=0,last=0,name='',phase;
 const phases=[],original=GuildSearch.runPhase,start=performance.now();
 const makeWorker=()=>{active++;maxWorkers=Math.max(maxWorkers,active);if(active>workers)throw Error('worker count mismatch');
  const w=SearchExecutor.createWorker();let closed=false;
  return {postMessage:m=>w.postMessage(m),set onmessage(f){w.onmessage=f},set onerror(f){w.onerror=f},terminate(){if(!closed){closed=true;active--;w.terminate()}}};};
 GuildSearch.runPhase=o=>{phase={index:phases.length,name,jobs:o.jobs.length,runs:o.runs,seed:o.seed,workers:o.workers};const row=phase,beg=performance.now();
  phases.push(row);recordP4({type:'phase',...row});
  const h=original({...o,onProgress:(d,n)=>{o.onProgress?.(d,n);if(performance.now()-last>60000){last=performance.now();recordP4({type:'progress',phase:row.index,done:d,total:n})}}});
  return {...h,promise:h.promise.then(r=>{row.seconds=(performance.now()-beg)/1000;recordP4({type:'phaseDone',...row});return r;})};};
 try{
  const common={S,results,roster:R,workers,makeWorker,breaks,base:location.origin+'/',onPhase:m=>name=m};
  let result;
  if(daily){
   const session=GuildDaily.createSession(makeWorker),cx={...common,G,env,session,nowMs:Date.parse('2026-11-26T12:00:00+09:00'),tiers:[0,0,0,0],stage:'guild'};
   try{result=await GuildDaily.search(cx);if(mode==='daily3'&&!result.partial)result=await GuildDaily.search({...cx,previous:result});}
   finally{session.close();}
  }else result=await CosmoSearch.search({...common,bosses:G.bosses.map(b=>b.key),bossName:csBoss,level:G.search.defaultLevel,mode:G.search.defaultMode,levelMax:G.levelMax,
    boundaries:Object.fromEntries(G.bosses.map(b=>[b.key,b.boundaries||[]])),stage:'코스모 게이트'});
  if(daily){if(result.partial||result.timeCapped||result.seals.used!==Number(mode.slice(-1)))throw Error('incomplete daily result');
   if(new Set(result.teams.flatMap(t=>t.keys)).size!==result.teams.length*4||new Set(result.teams.map(t=>t.sup)).size!==result.teams.length||result.teams.some(t=>!t.sup||t.sup==='none'))throw Error('bundle constraint failed');}
  if(!result.rows.length||active)throw Error('empty result or worker leak');
  delete result.growthOwned;
  return {seconds:(performance.now()-start)/1000,mode,env,workers,maxWorkers,active,phases,result,settings:S,transport:'actual browser Pyodide',resumed:false};
 }finally{GuildSearch.runPhase=original;}
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('account', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('mode', choices=['cosmo', 'daily2', 'daily3'])
    ap.add_argument('--environment-only', action='store_true')
    a = ap.parse_args()
    out = a.output.resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        ap.error('private output must be outside repository')
    out.mkdir(parents=True, exist_ok=True)
    if (out/'result.json').exists() or (out/'events.jsonl').exists():
        ap.error('fresh measurement only: output already used')
    tmp = ROOT/'local/p4-browser-temp'
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(tmp)
    tempfile.tempdir = str(tmp)
    info = json.loads(a.account.read_text(encoding='utf-8-sig'))
    files = ['index.html', 'guild_daily.js', 'cosmo_search.js', 'cosmo_learned.js', 'sim/manifest.json', 'sim_worker.js', 'tools/measure_guild_p4_browser.py']
    pins = dict(accountHash=hashlib.sha256(a.account.read_bytes()).hexdigest(),
                sources={f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files})
    with test_server() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 1000})
            page.set_default_timeout(120000)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(base+'/index.html?auto=0')
            page.wait_for_function('window._ready && !!QK.d')
            if a.environment_only:
                env = page.evaluate("""()=>{const env={cores:navigator.hardwareConcurrency,memGB:navigator.deviceMemory,mobile:csMobile()};
                  const workers=CosmoSearch.workerCount(D.guild.search.daily,env);return {env,workers,cosmoWorkers:csWorkers(),secondsPerGame:1/(workers>=8?125.34:workers>=4?103.42:workers>=2?70.19:39.95)}}""")
                (out/'environment.json').write_text(json.dumps(env, indent=2), encoding='utf8')
                print(json.dumps(env), flush=True)
                return
            (out/'pins.json').write_text(json.dumps(pins, indent=2), encoding='utf8')
            started = time.monotonic()
            with (out/'events.jsonl').open('w', encoding='utf8', buffering=1) as journal:
                def record(_source, event):
                    journal.write(json.dumps(event, ensure_ascii=False)+'\n')
                    (out/'progress.json').write_text(json.dumps(dict(event=event, wallSeconds=time.monotonic()-started), ensure_ascii=False), encoding='utf8')
                    print(json.dumps(event, ensure_ascii=False), flush=True)
                page.expose_binding('recordP4', record)
                result = page.evaluate(RUN, dict(info=info, mode=a.mode))
            assert not errors, errors
            assert pins['sources'] == {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
            result.update(pins=pins, browser=browser.version, errors=errors)
            (out/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
            print('complete', a.mode, round(result['seconds']/60, 3), 'minutes', flush=True)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
