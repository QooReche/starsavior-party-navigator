const assert=require('node:assert/strict');
// Isolate learned candidate selection; full layout/audit behavior has dedicated tests.
const PlacementFixture=require('../party_placement.js');
PlacementFixture.variants=(keys,results)=>[PlacementFixture.baseline(keys,results)];
const L=require('../cosmo_learned.js'),C=require('../cosmo_search.js'),GS=require('../guild_search.js'),G=require('../data/cosmo_raid.json');
const roster=Array.from({length:16},(_,i)=>({key:'u'+i,cls:i%3?'캐스터':'서포터',el:i%2?'달':'태양'}));
const results=Object.fromEntries(roster.map((r,i)=>[r.key,{power:i?1000+i:1,stats:{atk:100+i}}]));
function settings(){const S=structuredClone(G.search);S.placement.auditTeams=0;Object.assign(S.learned,{value:true,S:180,m:3,K:70,M:2,A:40,overlapStarts:4,overlapKeep:3,minCorrelation:-1,missThreshold:1});S.rerank={keep:30,runs:2};S.screen={firstRuns:1,runs:2,passFrac:.1,passMinMult:1};S.final.runs=3;S.combine={topTriples:4,show:4};return S;}
const score=keys=>1000+keys.reduce((v,k)=>v+(k==='u0'?180:Number(k.slice(1))*7),0);
async function search(S,kind='linear',engine=C){const sent=[],phases=[];let made=0,closed=0,stop=false;
 try{const out=await engine.search({S,bosses:G.season.bossOrder,results,roster,level:6,mode:'mean',workers:2,stage:'cosmo',stale:()=>stop,
  onPhase:(msg,t,info)=>{phases.push({msg,t,info});if(kind==='cancel'&&msg.includes('예측 채점'))stop=true;},makeWorker(){made++;return {terminate(){closed++;},postMessage(m){sent.push(m);setImmediate(()=>{for(const t of m.teams){if(kind==='missing')continue;const v=kind==='ties'?1000:score(t.party.units.map(u=>u.key));this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{prog:.8,progs:[.8],via:{},n:m.n_runs,cosmo:{mean:v,top:v,clear:0,frac:.8,n:m.n_runs}}}});}this.onmessage({data:{type:'done',id:m.id}});});}};}});
 return {out,sent,phases};}finally{assert.equal(made,closed);}}
async function main(){const S=settings(),rows=C.poolAll(S,results,roster),all=GS.combos(S,rows);
 assert.deepEqual([...GS.iterateCombos(S,rows)],all);
 const sample=await L.sample(S,rows,19);assert(sample.length<=S.learned.S);for(const r of rows)assert(sample.filter(k=>k.includes(r.key)).length>=S.learned.m);
 assert.deepEqual(sample,await L.sample(S,rows,19));
 const enc=L.encoder(rows,results,roster),model=await L.train(enc,sample,sample.map(score),S.learned);
 assert(model.rho>.95,model.rho);assert(L.correlation(all.map(score),all.map(model.predict))>.95);
 const selection=await L.select(S,rows,model);for(const r of rows)assert([...selection.core.values()].filter(e=>e.keys.includes(r.key)).length>=S.learned.M);
 assert(selection.core.size<=S.learned.K+rows.length*S.learned.M);
 // Guarantees must add teams outside the global top K (weak-power support is still eligible).
 const tiny=settings();tiny.learned.K=1;tiny.learned.M=2;
 const sel=await L.select(tiny,rows,model);assert(sel.core.size>1,'M 제거 변이 검출');for(const r of rows)assert([...sel.core.values()].filter(e=>e.keys.includes(r.key)).length>=2);
 const ss=await Promise.all([0,1,2].map(()=>L.select(tiny,rows,model)));
 const budgetProbe=structuredClone(tiny);budgetProbe.retry.maxTripleChecks=1;budgetProbe.learned.maxOverlapChecks=123;
 let overlapBudget;
 await L.overlap(budgetProbe,rows,[model,model,model],structuredClone(ss),async(lists,n,budget)=>{overlapBudget=budget.remaining;return [];});
 assert.equal(overlapBudget,123,'학습 겹침 예산은 최종 조합 예산과 별도');
 await L.overlap(tiny,rows,[model,model,model],ss,C.bestTriples);assert(ss.some(s=>s.overlap.size>0),'겹침 후보 제거 변이 검출');
 const triples=C.bestTriples(ss.map(s=>[...s.core.values()].sort((a,b)=>b.score-a.score)),4);assert(triples.length>=4,'겹침 없는 여러 삼중');
 const aud=await L.auditSample(S,rows,selection,18);assert.equal(new Set(aud.teams.map(L.id)).size,aud.teams.length);assert(aud.teams.every(k=>!selection.core.has(L.id(k))));assert(aud.teams.length<=S.learned.A);
 assert(L.audit({...S.learned,missThreshold:.1},.9,[10,20],[30],1,100,1).fallback,'감사 복귀 제거 변이 검출');
 assert(L.audit({...S.learned,minCorrelation:.5},.1,[10,20],[0],1,100,1).fallback);
 assert(L.audit(S.learned,.9,[10,NaN],[0],1,100,1).fallback);
 const ranked=all.map(keys=>({keys,score:score(keys)})).sort((a,b)=>b.score-a.score),protectedId=L.id(ranked.at(-1).keys),kept=L.preserve(ranked,ranked.slice(0,1),2,new Set([protectedId]));
 assert(kept.some(e=>L.id(e.keys)===protectedId));for(const r of rows)assert(kept.filter(e=>e.keys.includes(r.key)).length>=2);
 const original=GS.combos;GS.combos=()=>{throw Error('learned must stream');};let r;try{r=await search(S);}finally{GS.combos=original;}
 assert(r.out.rows[0].sum>0&&new Set(r.out.rows[0].teams.flatMap(t=>t.keys)).size===12);assert(r.out.triples>=4);
 assert(r.phases.some(p=>p.msg.includes('표본 학습'))&&r.phases.some(p=>p.msg.includes('예측 채점')));
 const predicted=r.phases.find(p=>p.msg.includes('예측 채점'));assert(predicted.t> S.learned.S*3,'ETA에 미완료 보스·후보를 포함');
 const first=r.sent.filter(m=>m.seed===1).flatMap(m=>m.teams.map(t=>t.key));assert.equal(new Set(first).size,first.length,'표본 재사용');assert(first.length<3*all.length);
 assert(first.length<=3*Math.min(all.length,S.learned.S+S.learned.K+rows.length*S.learned.M+S.learned.A+S.learned.overlapStarts*(S.learned.overlapKeep+2)));
 const fallback=settings();fallback.learned.minCorrelation=1;const f=await search(fallback);assert(f.out.audit.every(a=>a.fallback));const fj=f.sent.filter(m=>m.seed===1).flatMap(m=>m.teams.map(t=>t.key));assert.equal(fj.length,3*all.length);assert.equal(new Set(fj).size,fj.length);
 assert(f.phases.some(p=>p.msg.includes('전수 확인')));
 const tied=await search(settings(),'ties');assert(tied.out.rows[0].sum===3000&&tied.out.audit.every(a=>a.fallback),'동점 상관 미정의는 전수 복귀');
 await assert.rejects(search(settings(),'missing'),/결과가 누락/);
 await assert.rejects(search(settings(),'cancel'),/취소/);
 const capped=settings();capped.retry.maxCandidatesPerBoss=2;await assert.rejects(search(capped),/정밀 후보 상한/);
 const off=settings();off.learned.value=false;const a=await search(off);delete off.learned;const b=await search(off);assert.deepEqual(a.out,b.out);assert.deepEqual(a.sent,b.sent,'꺼짐 시 기존 요청·결과 동일');
 if(process.argv.includes('--legacy-commit')){
   const {execFileSync}=require('node:child_process'),Module=require('node:module'),path=require('node:path');
   const old=new Module(path.resolve(__dirname,'../cosmo_search.legacy.js'),module);old.filename=path.resolve(__dirname,'../cosmo_search.legacy.js');old.paths=module.paths;
   old._compile(execFileSync('git',['show','ddb3842:cosmo_search.js'],{encoding:'utf8'}),old.filename);
   const baseline=await search(off,'linear',old.exports);assert.deepEqual(b.out,baseline.out);assert.deepEqual(b.sent,baseline.sent);console.log('PASS ddb3842 legacy requests/results identical');
 }
 assert.equal(G.search.learned.value,true);assert(C.plan(S,rows,0).total<C.plan({...S,learned:{value:false}},rows,0).total);
 console.log('PASS learned: ridge/CV, streaming, stratification, K/M/overlap/audit caps, fallback, reuse, multiple triples, legacy equality');}
main().catch(e=>{console.error(e);process.exitCode=1;});
