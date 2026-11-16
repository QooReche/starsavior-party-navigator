// 브라우저 시뮬 작업자(Web Worker) — Pyodide 로 battlesim(파이썬 엔진)을 그대로 돌린다. 엔진은 한 벌(설계 docs/redesign_v1.md 2단계).
// 메시지: {type:"run", id, job, stage:"content/tab/name", teams:[{key, party:{units:[{key,stats_override}],leader}, options}], n_runs, seed, options}
// 응답: {type:"stage", id, job, msg} 진행 / {type:"team", id, job, key, result} 팀 하나 끝 / {type:"done", id, job} / {type:"error", id, job, msg}
//  job = 화면 대기열(simDispatch)이 단 작업 번호 — 그대로 되돌려 준다(화면은 맡긴 작업의 done 을 확인한 뒤에만 다음 작업을 보낸다)
// 작업자는 계산이 끝나도 살아서 다음 요청을 받는다 → 요청마다 만든 파이썬 객체(toPy)는 바로 해제하고, 함수 핸들은 한 번만 얻는다
// 취소·제한 시간은 화면 쪽이 worker.terminate() 로 처리한다(파이썬 인터럽트는 보안 헤더가 필요해서 쓰지 않음).
// Pyodide 0.26.4 는 외부 CDN 이 아니라 이 사이트의 lib/pyodide/ 에서 받는다(같은 주소 = 바깥 서버 의존 없음, 해시 lib/pyodide/SHA256SUMS)
const PYODIDE=new URL("lib/pyodide/",self.location.href).href;
let ready=null,fns=null;
async function boot(base,send=postMessage){
 send({type:"stage",msg:"계산 엔진 내려받는 중(처음 한 번)"});
 importScripts(PYODIDE+"pyodide.js");
 const p=await loadPyodide({indexURL:PYODIDE});
 send({type:"stage",msg:"전투 데이터 내려받는 중"});
 const response=await fetch(base+"sim/manifest.json",{cache:"no-cache"});
 if(!response.ok)throw new Error("manifest HTTP "+response.status);
 const man=await response.json();
 let next=0;
 async function download(){while(next<man.files.length){const f=man.files[next++];
  const r=await fetch(base+f+"?v="+man.ver);if(!r.ok)throw new Error(f+" HTTP "+r.status);
  const buf=new Uint8Array(await r.arrayBuffer());
  const dir="/repo/"+f.split("/").slice(0,-1).join("/");p.FS.mkdirTree(dir);p.FS.writeFile("/repo/"+f,buf)}}
 await Promise.all(Array.from({length:Math.min(5,man.files.length)},download));
 p.runPython(`
import os, sys
os.environ['PN_SRC'] = '/repo'
sys.path.insert(0, '/repo')
from battlesim.web import run_auto
`);
 send({type:"stage",msg:"준비 끝"});
 return {p,ver:man.ver}}
onmessage=async e=>{const m=e.data;
 const send=data=>postMessage({...data,id:m.id,requestId:m.requestId,owner:m.owner,revision:m.revision,job:m.job,jobId:m.jobId});
 try{
  if(!ready)ready=boot(m.base,send);
  const {p,ver}=await ready;
  if(m.type!=="run")return;
  if(!fns)fns={run:p.globals.get("run_auto")};   // battlesim/web.py — 오토 기준만(11/14 수동 모드 제거)
  const {run}=fns;
  for(let i=0;i<m.teams.length;i++){const t=m.teams[i];
   const opts=Object.assign({},m.options||{},t.options||{});
   if(m.options?.rules_override||t.options?.rules_override)opts.rules_override=Object.assign({},m.options?.rules_override,t.options?.rules_override);
   const ex=JSON.stringify(opts);
   send({type:"stage",msg:`시뮬 ${i+1}/${m.teams.length}팀 (${m.n_runs}판)`});
   const party=p.toPy(t.party);let res;
   // Observe completed battles only for DIRECT. The engine, RNG, aggregation and
   // recommendation call path stay unchanged. Restore the method even on failure.
   let completed=0;
   if(m.progress){p.globals.set('_pn_progress',()=>send({type:'stage',completed:++completed,total:m.n_runs,msg:'계산 중'}));
    p.runPython(`
from battlesim.api import Battle as _pn_battle
_pn_original_run = _pn_battle.run
def _pn_observed_run(self):
    result = _pn_original_run(self)
    _pn_progress()
    return result
_pn_battle.run = _pn_observed_run
`);}
   try{res=Object.assign(JSON.parse(run(m.stage,party,m.n_runs,m.seed,ex)),{ver});
   }finally{if(m.progress){p.runPython('_pn_battle.run = _pn_original_run');p.globals.delete('_pn_progress');}if(party&&party.destroy)party.destroy()}
   send({type:"team",key:t.key,result:res})}
  send({type:"done"})
 }catch(err){send({type:"error",msg:String(err&&err.message||err).slice(-400)})}};
