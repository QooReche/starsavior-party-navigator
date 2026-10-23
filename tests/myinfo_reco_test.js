// node tests/myinfo_reco_test.js [--mutations]
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco.js'),S=require('../myinfo_stats.js'),Q=require('../quick.js');
const info=require('./fixtures/myinfo_synthetic.json'),growth=require('../data/growth.json');
const roster=info.units.map(u=>({uid:u.id,key:String(u.id)}));
const tests={
  mapping(){for(const ck of ['op','clo'])assert.equal(S.rule_for_content(ck),'normal');
    for(const ck of ['cosmo','rush'])assert.equal(S.rule_for_content(ck),'fixed200');
    for(const ck of ['oph','daily','equip','cube'])assert.equal(S.rule_for_content(ck),'normal');
    assert.equal(S.rule_for_content('unmapped_content'),null);
    assert.deepEqual(M.profile(info,roster,growth,'unmapped_content').results,{});},
  judgment(){assert.deepEqual(M.judgment({clear:true,power:100000},2),{label:'오토 가능',extra:null});
    assert.deepEqual(M.judgment({clear:false,power:123456},1.3),{label:'오토 어려움',extra:37000});
    assert.equal(M.judgment({clear:false,power:10000},null).extra,null);
    assert.equal(M.judgment({clear:false,power:10000},1.01).extra,1000);},
  mixed(){const p=M.profile(info,roster,growth,'op'),t=M.team(['1001','absent'],p,k=>k+'@engine');
    assert.equal(t.assumed,1);assert.deepEqual(Object.keys(t.finals),['1001']);
    assert.equal(t.powers['1001@engine'],S.final_stats(info.units[0],info,growth).power);
    const sv={a:[0,100,1000,20,100,10000,100,100,''],b:[0,100,1000,20,100,10000,100,100,'']};
    const st={bp:20000,np:true,w:[[[1,0,100,0,0,0]]]};
    const result=Q.evaluate(['a','b'],st,sv,[],{},1.25,null,true,{a:7000});
    assert.equal(result.power,19500); // owned = 7000, assumed = 12500 (no duplicate growth)
    assert.equal(M.team(['absent'],p,k=>k).powers,null);},
  fixed(){const a=M.profile(info,roster,growth,'op'),b=M.profile(info,roster,growth,'cosmo');
    assert.notEqual(a.results['1001'].power,b.results['1001'].power);
    assert.equal(b.results['1001'].power,S.final_stats(info.units[0],info,growth,'fixed200').power);
    assert.equal(a.mismatch,true);},
  hash(){assert.equal(M.hash(info),M.hash(JSON.parse(JSON.stringify(info))));
    assert.notEqual(M.hash(info),M.hash({...info,exported_at:'changed'}));},
  sim(){const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
    const start=html.indexOf('function simParty('),end=html.indexOf('// 표시 상태',start);
    const profile=M.profile(info,roster,growth,'op'),keys=['1001','1002','1003','missing'];
    const finals=M.team(keys,profile,k=>k),sv=Object.fromEntries(keys.map(k=>[k,[0,100,1000,50,100,10000]]));
    const ctx=vm.createContext({arrangeOf:()=>({order:keys,lead:'1002'}),QK:{d:{sv}},Quick:Q,ekey:k=>k,
      contents:[{key:'op'}],$:()=>({value:0}),rkOf:()=>0,SIMQ:{n:100},MODE:'auto',miMode:()=>true,MI:{hash:'first'},teamBreak:()=>null});
    vm.runInContext(html.slice(start,end),ctx);ctx.t={combo:[],ek:keys,base:40000,b:finals};ctx.st={tab:'x',name:'y'};
    const party=JSON.parse(JSON.stringify(vm.runInContext('simParty(t)',ctx)));
    assert.equal(party.leader,0);assert.deepEqual(party.units[0],{key:'1002',build:'none',stats_override:profile.results['1002'].stats,stats_final:true,power:profile.results['1002'].power,myinfo_combat:profile.results['1002'].combat});
    assert.deepEqual(party.units[2],{key:'1001',build:'none',stats_override:profile.results['1001'].stats,stats_final:true,power:profile.results['1001'].power,myinfo_combat:profile.results['1001'].combat});
    assert.deepEqual(party.units[3],{key:'missing',stats_override:{atk:100,hp:1000,def:50}});
    const before=vm.runInContext('simSig(st,t)',ctx);ctx.MI.hash='second';assert.notEqual(vm.runInContext('simSig(st,t)',ctx),before);
    ctx.miMode=()=>false;assert.notEqual(vm.runInContext('simSig(st,t)',ctx),before);},
  sim_power(){const html=fs.readFileSync(require.resolve('../party_template.html'),'utf8');
    const keys=['1001','1002','1003','1005'],profile=M.profile(info,roster,growth,'op');
    const ctx=vm.createContext({arrangeOf:()=>({order:keys,lead:'1001'}),ekey:k=>k,Quick:Q,
      QK:{d:{sv:Object.fromEntries(keys.map(k=>[k,[0,100,1000,50,100,10000]]))}},
      t:{ek:keys,base:40000,b:M.team(keys,profile,k=>k)}});
    vm.runInContext(html.slice(html.indexOf('function simParty('),html.indexOf('const simSigB=')),ctx);
    assert.equal(vm.runInContext('simParty(t).units.reduce((n,u)=>n+u.power,0)',ctx),39000);}
};
let failed=0;for(const [name,test] of Object.entries(tests)){try{test();console.log('PASS',name)}catch(e){failed++;console.error('FAIL',name,e.message)}}
if(failed)process.exit(1);
if(process.argv.includes('--mutations')){
  const cases=[['mapping',S,'rule_for_content',()=>null],['judgment',M,'judgment',()=>({label:'wrong',extra:0})],
    ['mixed',M,'team',()=>({powers:null,finals:{},assumed:0})],['fixed',M,'profile',()=>({results:{'1001':{power:1}},mismatch:false})],
    ['hash',M,'hash',()=> 'constant'],['sim',M,'team',()=>({powers:null,finals:{},assumed:4})]];
  for(const [name,obj,key,bad] of cases){const original=obj[key];obj[key]=bad;let failed=false;
    try{tests[name]()}catch(e){failed=true}finally{obj[key]=original}
    assert(failed,'mutation survived: '+name);tests[name]();console.log('MUTATION caught + restored',name)}
}
console.log('ALL OK',Object.keys(tests).length);
