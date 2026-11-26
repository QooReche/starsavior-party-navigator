// Freeze the reference markup at the task's starting HEAD, without normalization.
const assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const {loadModule,readSrc}=require('./helpers/page');
const U=require('../ui_shared'),C=require('../cosmo_search'),R=require('../recheck_ui');
const frozen=name=>execFileSync('git',['show','28b689a:'+name],{encoding:'utf8',maxBuffer:4*1024*1024});
const old=loadModule(frozen('cosmo_search.js')),oldR=loadModule(frozen('recheck_ui.js'));
let cases=0;
const same=(a,b)=>{assert.equal(a,b);cases++;};
const teams=[0,1,2].map((n)=>({boss:'boss'+n,order:['a','b','c','d'],leaderKey:'c',level:n===2?null:n,
  brk:n?'break<&>':'',brkTie:n===2,st:{top:n*1100.5,mean:n*900.5,clear:n*.4,frac:n*.3},
  unsupported:n===1?[{unit:'a',raw:'<effect>'}]:[]}));
for(const mode of ['top','mean'])for(const cards of [false,true])for(const summary of [false,true]){
  const cx={esc:U.esc,label:k=>k+'<&>',bossName:k=>k+'<&>',hasInfo:true,level:-1,mode,levelMax:2,learned:false,
    sig:'new',preEta:'약 1분',report:()=>'<i>report</i>',work:()=>'<i>work</i>',error:()=>'<i>error</i>'};
  if(cards)cx.team=t=>`<div class="rowcards cs-cards">${U.esc(t.boss)}</div>`;
  if(summary)cx.summary=(r,m,i)=>`<div class="summary">${r.sum}/${m}/${i}</div>`;
  const row={teams,sum:12345.5};
  same(C.table(row,mode,cx,2),old.table(row,mode,cx,2));
  for(const phase of ['idle','run','err','done']){
    const st={phase,mode,rows:[row,row],level:1,reqLevel:1,learned:false,sig:'old',msg:'<message>',done:1,total:2,
      probe:true,audit:[{boss:'boss0',expanded:true}],combineLimited:true,pool:12,combos:30,keep:2,triples:3,runs:100};
    same(C.html(st,cx),old.html(st,cx));
    if(phase==='done'){
      same(C.html({...st,rows:[]},cx),old.html({...st,rows:[]},cx));
      same(C.html({...st,learned:true},cx),old.html({...st,learned:true},cx));
      same(C.html({...st,halved:true,passed:10,firstRuns:8,screenRuns:32},cx),old.html({...st,halved:true,passed:10,firstRuns:8,screenRuns:32},cx));
    }
  }
  same(C.html({phase:'idle'},{...cx,hasInfo:false}),old.html({phase:'idle'},{...cx,hasInfo:false}));
}
// General recommendation also keeps its original markup when no daily overrides are passed.
for(const state of ['work','done','cancel','err'])for(const outcome of ['changed','same'])for(const reverted of [false,true]){
  const r={state,outcome,teams:2,stage:'screen',done:3,total:24,deep:true};
  const d={rows:[{label:'팀<&>',from:.4,to:.5}],story:'리더 바꿈',reverted,teams:2,view:'rule'};
  same(R.strip(r,d),oldR.strip(r,d));
}
// A changed shared chip must fail the byte comparison, so the oracle is live.
const mutant=loadModule(readSrc('ui_shared.js').replace('<span class="cs-lv">','<span class="changed">'));
const mutated=loadModule(readSrc('cosmo_search.js'),{require:name=>name==='./ui_shared.js'?mutant:require('../'+name)});
assert.notEqual(mutated.table({teams,sum:1},'top',{esc:U.esc,bossName:k=>k,team:()=>''}),old.table({teams,sum:1},'top',{esc:U.esc,bossName:k=>k,team:()=>''}));
console.log(`PASS ${cases} byte-identical cosmo/recheck outputs against 28b689a; shared-chip mutation caught`);
