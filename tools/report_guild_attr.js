// Ratios and intervals from independently saved fixed selections. No new selection.
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {comparison}=require('./evaluate_guild_time'),{privateDir,save}=require('./measure_guild_time');
const read=f=>JSON.parse(fs.readFileSync(f,'utf8'));
function report(dir,draws=4000){
 const names=['A','B','C','D'],search={},evaluated={},holdouts={};
 for(const n of names){search[n]=read(path.join(dir,n,'result.json'));holdouts[n]=read(path.join(dir,n+'-holdout','result.json'));evaluated[n]=holdouts[n].evaluated[n];assert.equal(evaluated[n].summary.n,1000);}
 for(const n of names){
  const a=search.A.pins,b=search[n].pins,x=holdouts.A.pins,y=holdouts[n].pins;
  for(const k of ['accountHash','profileHash','season','stage','tiers','breaks','sources'])assert.deepEqual(b[k],a[k],n+' search '+k);
  for(const k of ['accountHash','profileHash','engine','tool','seedStart','batches','runsPerBatch'])assert.deepEqual(y[k],x[k],n+' holdout '+k);
  const strip=s=>{s=structuredClone(s);delete s.newSearch;delete s.placement.baseline;delete s.placement.enabled;return s;};
  assert.deepEqual(strip(b.settings),strip(a.settings));
  assert.equal(b.settings.newSearch,['C','D'].includes(n));
  assert.equal(b.settings.placement.baseline,['B','D'].includes(n));
  assert.equal(b.settings.placement.enabled,['B','D'].includes(n));
 }
 const comparisons={};for(let i=0;i<names.length;i++)for(let j=i+1;j<names.length;j++)comparisons[names[i]+' -> '+names[j]]=comparison(evaluated[names[i]],evaluated[names[j]],draws);
 const rows=names.map(n=>({condition:n,timeRatio:search[n].seconds/search.A.seconds,timingValid:!search.A.resumed&&!search[n].resumed,
  summary:evaluated[n].summary,clearCI95:evaluated[n].clearCI95,comparisonToA:n==='A'?comparison(evaluated.A,evaluated.A,draws):comparisons['A -> '+n]}));
 // Equal requests prove the B switch is gated off; compare every request digest/result.
 const requests=n=>fs.readFileSync(path.join(dir,n,'events.jsonl'),'utf8').split('\n').flatMap(l=>{try{const e=JSON.parse(l);return e.type==='result'?[[e.id,e.result]]:[];}catch{return [];}}).sort((a,b)=>a[0].localeCompare(b[0]));
 const legacyPlacementIgnored=JSON.stringify(requests('A'))===JSON.stringify(requests('B'));
 assert(legacyPlacementIgnored,'legacy placement changed requests/results; revisit interpretation');
 assert.deepEqual(evaluated.A.scores,evaluated.B.scores);assert.deepEqual(evaluated.A.clears,evaluated.B.clears);
 const result={rows,comparisons,legacyPlacementIgnored,timeLimitRatio:1.3,
  limitation:'B is an inactive setting in the legacy path; D-C estimates the placement bundle only under newSearch. Timing is one fresh run per condition, no timing CI.'};
 save(path.join(dir,'report.json'),result);
 const f=(v,d=4)=>v.toFixed(d),ci=(v,scale=1)=>v.map(x=>f(x*scale)).join(' ~ ');
 const lines=['# 길드 탐색 스위치 분리 측정','', '| 조건 | 시간/A | 클리어 차이 %p [95%] | 평균 점수/A [95%] | 상위 20%/A [95%] |', '|---|---:|---|---|---|'];
 for(const r of rows){const {point:p,ci95:c}=r.comparisonToA;lines.push(`| ${r.condition} | ${f(r.timeRatio)}${r.timingValid?'':' (재개: 판정 제외)'} | ${f(p.clearDifference*100)} [${ci(c.clearDifference,100)}] | ${f(p.meanRatio)} [${ci(c.meanRatio)}] | ${f(p.topRatio)} [${ci(c.topRatio)}] |`);}
 lines.push('',result.limitation,'','## 조건 간 비교','',JSON.stringify(comparisons,null,2));
 fs.writeFileSync(path.join(dir,'report.md'),lines.join('\n')+'\n');
 console.log('Private report saved; A/B complete request and holdout equality verified.');return result;
}
module.exports={report};
if(require.main===module)report(privateDir(process.argv[2]));
