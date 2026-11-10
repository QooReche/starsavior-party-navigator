// Cheap replay only: surrogate grid against the complete first-stage simulations.
// This is a diagnostic, NOT an independent gold quality gate or wall-time benchmark.
const fs=require('node:fs'),zlib=require('node:zlib'),path=require('node:path');
const C=require('../cosmo_search.js'),G=require('../data/cosmo_raid.json');
const [out,size='30',repeat='0']=process.argv.slice(2);
const data=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(out,`${size}-top-baseline-${repeat}`,'phase-0.json.gz'))));
const results=Object.fromEntries(JSON.parse(fs.readFileSync(path.join(out,'catalog.json'),'utf8')).map(r=>[r.key,r]));
const rows=[];
for(const boss of G.season.bossOrder){
 const jobs=data.jobs.filter(j=>j.boss===boss), top=C.pickTop(jobs,data.res,'top',300), n=Math.max(900,Math.ceil(jobs.length*.1));
 for(const proxy of ['power','attack','defense','hp'])for(const ratio of [.2,.35,.5,.7]){
  const S=JSON.parse(JSON.stringify(G.search));Object.assign(S.speed.surrogate,{ratio,proxy:{[boss]:proxy}});
  const pick=C.surrogateSelect(S,jobs,results,20261110+G.season.bossOrder.indexOf(boss));
  const keys=new Set(pick.jobs.map(j=>C.idOf(j.keys)));
  rows.push({boss,proxy,ratio,selected:pick.jobs.length,recall300:top.filter(t=>keys.has(C.idOf(t.keys))).length/top.length,
    ...C.surrogateAudit(S,pick,data.res,'top',n)});
 }
}
fs.writeFileSync(path.join(out,`proxy-${size}-${repeat}.json`),JSON.stringify(rows,null,2));
console.log(JSON.stringify(rows,null,2));
