// Synthetic contract; mutations execute the actual changed module source in memory.
const assert=require('node:assert/strict'),fs=require('node:fs'),Module=require('node:module'),path=require('node:path');
const file=path.resolve(__dirname,'../tools/learned_reco_measure.js'),source=fs.readFileSync(file,'utf8');
function load(text){const m=new Module(file,module);m.filename=file;m.paths=module.paths;m._compile(text,file);return m.exports;}
async function check(M){
 const c={minCorrelation:.4,missThreshold:.1};
 assert.equal(M.fallbackRequired(c,.39,0),true);
 assert.equal(M.fallbackRequired(c,.8,.11),true);
 assert.equal(M.fallbackRequired(c,null,0),true);
 assert.equal(M.fallbackRequired(c,.4,.1),false);
 const winner={keys:['fixed'],party:{units:['fixed']}},better={keys:['diagnostic'],party:{units:['diagnostic']}},seen=[];
 const r=await M.fixedEvaluation(winner,[better],async t=>{seen.push(t.keys[0]);return {prog:t.keys[0]==='fixed'?.2:.9};});
 winner.keys[0]='mutated';
 assert.equal(r.winner.keys[0],'fixed');assert.equal(r.result.prog,.2);
 assert.equal(r.diagnostics[0].result.prog,.9);assert.deepEqual(seen,['fixed','diagnostic']);
}
async function integration(M){
 const vm=require('node:vm'),html=fs.readFileSync(path.resolve(__dirname,'../party_template.html'),'utf8'),rt=fs.readFileSync(path.resolve(__dirname,'../recommend_runtime.js'),'utf8');
 const ctx=vm.createContext({UiShared:require('../ui_shared.js')});
 const cut=(s,a,b)=>{const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i);return s.slice(i,j);};
 for(const [a,b] of [['function partySyn(','// 추천 정책 버전'],['const LEAD_TAGS=','const BRSEL='],['const ckey=','// 관문 순위'],
   ['function breakChoice(','function breakChip('],['function simParty(','const simSigB='],['function quickRows(','function quickBox('],
   ['const SCR_ROUNDS=','const scrKey='],['const scrCmp=','function scrNote('],['function recoScreenSequence(','function simWaiting(']])vm.runInContext(cut(html,a,b),ctx);
 vm.runInContext(cut(rt,'const RECO_ARR_SCREEN=','function recoArrangeKick('),ctx);
 const names=['simParty','place','leaderPick','partySyn','arrangeRule','arrangeOf','arrGet','arrSet','pickBreak','breakChoice','teamBreak',
   'scrPick','scrFullKeys','scrFullInit','scrFullRank','scrRoundN','scrPrior','scrLegOpt','scrCmp','scrDone','scrOrder','scrShort','scrClose','recoScreenSequence','quickRows','recoArrange','recoArrangeRevert'];
 const sources=Object.fromEntries(names.map(n=>[n,vm.runInContext(n+'.toString()',ctx)]));
 const constants=JSON.parse(vm.runInContext('JSON.stringify({SCR_ROUNDS,SCR_FULL,RECO_ARR_SCREEN,RECO_ARR_KEEP,RECO_ARR_CHECK,RECO_ARR_FINAL,RECO_ARR_SEED,LEAD_TAGS})',ctx));
 const keys=['a','b','c','d','e','f'],cands=keys.map(key=>({s:{key,cls:'서포터',el:'sun'},score:0}));
 const combos=require('../guild_search.js').combos({newSearch:true},cands.map(x=>x.s));
 const input={id:'synthetic',c:{key:'op',name:'synthetic'},st:{tab:'test',name:'test'},sources,constants,cands,qt:combos.map(keys=>({keys,vd:'hard',v:0})),
   pool:keys,initial:combos.slice(0,4).map(x=>x.join(',')),qi:{growth:1,power:null,qs:{bp:400}},profile:null,options:{},breaks:[],levels:{},selected:{},shared:{},sessionBreak:{},bloom:{},parity:[],
   unitQuick:Object.fromEntries(keys.map(k=>[k,[0,100,100,100,100,100]]))};
 const D={cfg:{breakSkills:{},synergy:{typeWeight:{},confWeight:{}}},syn:[]};
 const S=structuredClone(require('../data/cosmo_raid.json').search);Object.assign(S.learned,{S:6,m:0,M:0,A:4});
 const trace=[];
 async function ev(jobs){trace.push(structuredClone(jobs));return jobs.map(j=>{const n=j.runs+(j.options.run_offset||0),clear=n>1?1:0,prog=clear?1:.5;
   return {n,clear,prog,ttk:20,via:{},progs:Array(n).fill(prog),raw:JSON.stringify(Array.from({length:n},()=>[clear?'clear':'wipe',20,20,prog]))};});}
 const f=await M.run(input,D,S,'F',7,ev),ft=trace.splice(0);
 const c=await M.run(input,D,S,'C',7,ev);
 assert(c.fallback);assert.deepEqual(c.screen,f.screen);assert.deepEqual(c.winner,f.winner);
 assert.deepEqual(trace.slice(-ft.length),ft,'Fallback must restore every F request including seed/order/offset/options');
 const learning=trace.slice(0,-ft.length).flat().reduce((n,j)=>n+j.runs,0);
 assert(learning>0);assert.equal(c.searchGames,f.searchGames+learning,'Fallback charges all learning plus exact F');
 assert(f.result.prog>0);
}
(async()=>{
 await check(load(source));
 await integration(load(source));
 for(const [before,after] of [
   ['rho<c.minCorrelation','rho>c.minCorrelation'],
   ['rate>c.missThreshold','rate<c.missThreshold'],
   ['return {winner:frozen,result,diagnostics};','return {winner:diagnostics[0].team,result:diagnostics[0].result,diagnostics};']]){
   assert(source.includes(before));let failed=false;
   try{await check(load(source.replace(before,after)));}catch(e){if(e instanceof assert.AssertionError)failed=true;else throw e;}
   assert(failed,'Mutation survived: '+before);
 }
 let rejected=false;const needle='if(audit.fallback){sc=full();';assert(source.includes(needle));
 try{await integration(load(source.replace(needle,'if(audit.fallback){seed++;sc=full();')));}catch(e){if(e instanceof assert.AssertionError)rejected=true;else throw e;}
 assert(rejected,'Fallback seed mutation survived');
 console.log('OK fallback boundaries + exact F replay + winner lock; 4 mutations rejected');
})().catch(e=>{console.error(e);process.exitCode=1;});
