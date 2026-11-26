'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {stats}=require('./evaluate_guild_time'),{save,privateDir}=require('./measure_guild_time');
const read=f=>JSON.parse(fs.readFileSync(f,'utf8'));
const median=xs=>xs.slice().sort((a,b)=>a-b)[Math.floor(xs.length/2)];
function compare(a,b,draws=4000){
 assert.equal(a.length,b.length);assert(a.length>0);
 for(let i=0;i<a.length;i++)assert.equal(a[i].scores.length,b[i].scores.length);
 const summarize=rs=>stats(rs.flatMap(r=>r.scores),rs.flatMap(r=>r.clears),rs.flatMap(r=>r.caps));
 const delta=(x,y)=>({topRatio:y.top/x.top,meanRatio:y.mean/x.mean,capDifference:y.cap-x.cap,clearDifference:y.clear-x.clear});
 const point=delta(summarize(a),summarize(b)),boot=Object.fromEntries(Object.keys(point).map(k=>[k,[]]));
 let seed=20261126;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 for(let n=0;n<draws;n++){
  const aa=[],bb=[];
  for(let i=0;i<a.length;i++){
   const ids=Array.from({length:a[i].scores.length},()=>Math.floor(rand()*a[i].scores.length));
   const pick=r=>Object.fromEntries(['scores','clears','caps'].map(k=>[k,ids.map(j=>r[k][j])]));
   aa.push(pick(a[i]));bb.push(pick(b[i]));
  }
  const d=delta(summarize(aa),summarize(bb));for(const k of Object.keys(boot))boot[k].push(d[k]);
 }
 const ci95=Object.fromEntries(Object.entries(boot).map(([k,vs])=>{assert(vs.every(Number.isFinite),'undefined ratio');vs.sort((a,b)=>a-b);return [k,[vs[Math.floor(draws*.025)],vs[Math.ceil(draws*.975)-1]]];}));
 return {point,ci95,draws,method:'paired battles, stratified by fixed search replicate; conditional on selected teams'};
}
function accepted(c,timeRatio,timingValid){
 return timingValid&&c.ci95.topRatio[0]>=.995&&(c.ci95.capDifference[0]>0||c.ci95.meanRatio[0]>1)&&c.ci95.meanRatio[0]>=.98&&timeRatio<=1.1;
}
function report(dir){
 const experiment=read(path.join(dir,'experiment-pins.json')),rows=[];
 function load(season,offset,name){
  const p=path.join(dir,String(season),String(offset),name),s=read(path.join(p,'result.json')),h=read(path.join(p,'holdout/result.json'));
  assert.equal(s.pins.accountHash,experiment.accountHash);assert.equal(s.pins.season.id,season);assert.equal(s.pins.seedOffset,offset);assert.equal(s.pins.workers,2);
  assert.equal(h.pins.accountHash,s.pins.accountHash);assert.equal(h.pins.seasonHash,s.pins.seasonHash);assert.equal(h.pins.seedStart,20270101+offset);
  assert.equal(h.pins.batches*h.pins.runsPerBatch,1000);
  const e=h.evaluated[name];for(const k of ['scores','clears','caps'])assert.equal(e[k].length,1000);
  assert.deepEqual(e.selected,s.result.rows[0]);
  assert.equal(s.pins.settings.newSearch,name==='D');assert.equal(s.pins.settings.legacyBaseline,name==='E');
  return {s,h,e,timing:!s.resumed&&read(path.join(p,'timing.json')).backgroundQuiet};
 }
 for(const season of experiment.seasons){
  const a=experiment.offsets.map(o=>load(season,o,'A'));
  for(const name of ['A','E',...(season===30112&&experiment.withD?['D']:[])]){
   const offsets=name==='D'?[0]:experiment.offsets,base=name==='D'?[a[0]]:a,b=offsets.map(o=>load(season,o,name));
   for(let i=0;i<b.length;i++){
    for(const k of ['accountHash','profileHash','seasonHash','sources','tiers','breaks','stage'])assert.deepEqual(b[i].s.pins[k],base[i].s.pins[k]);
    const strip=s=>{s=structuredClone(s);delete s.legacyBaseline;delete s.newSearch;if(name==='D'){delete s.placement.baseline;delete s.placement.enabled;}return s;};
    assert.deepEqual(strip(b[i].s.pins.settings),strip(base[i].s.pins.settings));
    for(const k of ['profileHash','engine','tool','seedStart','batches','runsPerBatch'])assert.deepEqual(b[i].h.pins[k],base[i].h.pins[k]);
   }
   const c=compare(base.map(x=>x.e),b.map(x=>x.e)),timingValid=[...a,...b].every(x=>x.timing);
   const times=b.map(x=>x.s.seconds),aTimes=a.map(x=>x.s.seconds),timeRatio=median(times)/median(aTimes);
   const games=xs=>xs.reduce((n,x)=>n+x.s.submitted+1000,0),searchGames=xs=>xs.reduce((n,x)=>n+x.s.submitted,0);
   rows.push({season,condition:name,replicates:b.length,comparison:c,timingValid,timeRatio,maxTimeRatio:Math.max(...times)/Math.max(...aTimes),
    seconds:{median:median(times),max:Math.max(...times)},gamesRatio:games(b)/games(base),searchGamesRatio:searchGames(b)/searchGames(base),
    accepted:name==='E'?accepted(c,timeRatio,timingValid):null});
  }
 }
 const result={rows,accepted:rows.filter(r=>r.condition==='E').every(r=>r.accepted),accountCount:1,criteria:'docs/guild_time.md P0 pre-registration'};
 save(path.join(dir,'report.json'),result);
 const f=x=>x.toFixed(4),cell=(r,k,scale=1)=>`${f(r.comparison.point[k]*scale)} [${r.comparison.ci95[k].map(x=>f(x*scale)).join(', ')}]`;
 const lines=['| 시즌·조건 | 상위 20%/A [95%] | 상한 차이 %p [95%] | 평균/A [95%] | 클리어 차이 %p [95%] | 시간 중앙·최대/A | 총 판 수/A |','|---|---|---|---|---|---|---|'];
 for(const r of rows)lines.push(`| ${r.season} ${r.condition}${r.replicates===1?' (1회)':''} | ${cell(r,'topRatio')} | ${cell(r,'capDifference',100)} | ${cell(r,'meanRatio')} | ${cell(r,'clearDifference',100)} | ${f(r.timeRatio)} · ${f(r.maxTimeRatio)}${r.timingValid?'':' (무효)'} | ${f(r.gamesRatio)} |`);
 lines.push('',`E 채택 기준: ${result.accepted?'충족':'미충족'}. 총 판 수는 탐색+독립 평가. D 시간은 단회/A 3회 중앙·최대이며 판 수·품질은 A 오프셋 0 대비임.`);
 fs.writeFileSync(path.join(dir,'ratios.md'),lines.join('\n')+'\n');
 console.log('P0 private report complete');return result;
}
module.exports={compare,accepted};
if(require.main===module)report(privateDir(process.argv[2]));
