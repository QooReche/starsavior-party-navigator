'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const Daily=require('../guild_daily'),P=require('../party_placement'),{scenario}=require('./guild_daily_test');
function near(d=Daily){
 const a={score:100,mean:90,scoreSE:1,meanSE:1},b={score:98,mean:80,scoreSE:1,meanSE:1},c={score:95,mean:80,scoreSE:1,meanSE:1};
 assert.deepEqual(Array.from(d.closeFinalists([a,b,c])),[a,b]);
 assert.deepEqual(Array.from(d.closeFinalists([a,{...b,score:100,mean:85}])),[a]);
 assert(Math.abs(d.standardError([1,2,3])-Math.sqrt(1/3))<1e-12);
}
async function baseline(d=Daily){
 const s=await scenario({daily:d,seals:2,setup:f=>{Object.values(f.results).forEach((r,i)=>{r.stats.hp=1000+i*100;r.stats.spd=100+i;});}});
 const first=s.trace[0].teams[0],keys=first.party.units.map(u=>u.key),expected=P.baseline(keys,s.cx.results);
 assert.deepEqual(keys,expected.order);assert.equal(keys[first.party.leader],expected.leaderKey);
 assert(s.out.teams.every(t=>t.prog>0));
}
async function confirmation(d=Daily){
 const s=await scenario({daily:d,seals:2,scoreFn:(t,i)=>t.options.guild.step===7?5000+(i%2?100:-100):900,settings:S=>{S.daily.probe.teams=8;}});
 assert(s.phases.some(p=>p.label==='근접 결선 80판 확인'));
 assert(s.trace.filter(m=>m.label==='근접 결선 80판 확인').every(m=>m.n_runs===40&&m.teams.every(t=>t.options.run_offset===40)));
 assert(s.out.teams.every(t=>t.prog>0));
}
(async()=>{
 near();await baseline();await confirmation();
 const src=fs.readFileSync(require.resolve('../guild_daily'),'utf8');
 for(const [from,to,test] of [
  ['placement||P.baseline(keys,cx.results)','placement||GS.party(keys,cx.results,cls)',baseline],
  ['return first[metric]-r[metric]<=2*Math.hypot','return first[metric]-r[metric]<=0*Math.hypot',near],
  ['if(near.length<2||D.final.closeRuns<=D.final.runs)','if(true)',confirmation]
 ]){assert(src.includes(from));const ctx={module:{exports:{}},require:n=>require('../'+n),setTimeout,clearTimeout};vm.runInNewContext(src.replace(from,to),ctx);await assert.rejects(async()=>test(ctx.module.exports));}
 console.log('PASS daily P4: baseline, SE proximity, append 40→80, positive progress, 3 killed mutations');
})().catch(e=>{console.error(e);process.exitCode=1;});
