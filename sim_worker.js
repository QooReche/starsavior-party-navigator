// 브라우저 시뮬 작업자(Web Worker) — Pyodide 로 battlesim(파이썬 엔진)을 그대로 돌린다. 엔진은 한 벌(설계 docs/redesign_v1.md 2단계).
// 메시지: {type:"run", id, stage:"content/tab/name", teams:[{key, party:{units:[{key,stats_override}],leader}}], n_runs, seed}
// 응답: {type:"stage", id, msg} 진행 / {type:"team", id, key, result} 팀 하나 끝 / {type:"done", id} / {type:"error", id, msg}
// 취소·제한 시간은 화면 쪽이 worker.terminate() 로 처리한다(파이썬 인터럽트는 보안 헤더가 필요해서 쓰지 않음).
const PYODIDE="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
let py=null,ready=null;
async function boot(base){
 postMessage({type:"stage",msg:"계산 엔진 내려받는 중(처음 한 번, 약 10MB)"});
 importScripts(PYODIDE+"pyodide.js");
 const p=await loadPyodide({indexURL:PYODIDE});
 postMessage({type:"stage",msg:"전투 데이터 내려받는 중"});
 const man=await (await fetch(base+"sim/manifest.json",{cache:"no-cache"})).json();
 for(const f of man.files){
  const r=await fetch(base+f+"?v="+man.ver);if(!r.ok)throw new Error(f+" HTTP "+r.status);
  const buf=new Uint8Array(await r.arrayBuffer());
  const dir="/repo/"+f.split("/").slice(0,-1).join("/");p.FS.mkdirTree(dir);p.FS.writeFile("/repo/"+f,buf)}
 p.runPython(`
import os, sys, json
os.environ['PN_SRC'] = '/repo'
sys.path.insert(0, '/repo')
from battlesim import simulate
def _run(stage, party, n, seed):
    r = simulate(party, {'stage': stage}, {'n_runs': n, 'seed': seed})
    o = r['outcome']
    first = sorted(((v.get('first_death_p') or 0, k) for k, v in r['per_unit'].items()), reverse=True)
    return json.dumps(dict(clear=o['clear_p'], wipe=o['wipe_p'], timeout=o['timeout_p'], ci=o['ci95']['clear'], n=o['n_runs'],
                           ttk=o['ttk_median'], first=(first[0][1] if first and first[0][0] > 0 else None),
                           first_p=(first[0][0] if first else 0), gate=r['unsupported'].get('gate_ok', True)), ensure_ascii=False)
`);
 postMessage({type:"stage",msg:"준비 끝"});
 return {p,ver:man.ver}}
onmessage=async e=>{const m=e.data;
 try{
  if(!ready)ready=boot(m.base);
  const {p,ver}=await ready;py=p;
  if(m.type!=="run")return;
  const run=p.globals.get("_run");
  for(let i=0;i<m.teams.length;i++){const t=m.teams[i];
   postMessage({type:"stage",id:m.id,msg:`시뮬 ${i+1}/${m.teams.length}팀 (${m.n_runs}판)`});
   const js=run(m.stage,p.toPy(t.party),m.n_runs,m.seed);
   postMessage({type:"team",id:m.id,key:t.key,result:Object.assign(JSON.parse(js),{ver})})}
  postMessage({type:"done",id:m.id})
 }catch(err){postMessage({type:"error",id:m.id,msg:String(err&&err.message||err).slice(-400)})}};
