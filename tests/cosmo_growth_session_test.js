// Exercise real growth_ui orchestration with the synthetic cosmo_search harness.
'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm');
const {readSrc,cut}=require('./helpers/page');
const {setup,search}=require('./cosmo_session_test');
const source=cut(readSrc('growth_ui.js'),'async function growthStart(c,st){','function growthBaseline(');
async function check(code=source,retained=false){
  const h=setup(),{c,life}=h;
  let localSession;
  try{
    await search(c);
    const baseline=JSON.parse(JSON.stringify(c.CSR.rows[0]));
    if(!retained)c.csSessionRelease();
    const ownedSession=c.CSR.session,created=life.created;
    Object.assign(c,{GROW:{id:0,phase:'idle'},QK:{d:{}},GrowthGuide:{VERSION:1},
      growthEnabled:()=>true,growthSeasonReady:()=>true,growthSig:()=> 'same-input',
      MyInfoReco:{hash:()=> 'synthetic',OVERWRITE_VERSION:1,
        overwrite:()=>({profile:c.MI.profiles.cosmo,preset:'synthetic',changes:{}})}});
    const start=c.cosmoSearchStart;
    c.cosmoSearchStart=async(...args)=>{try{return await start(...args);}finally{localSession=args[0].session;}};
    vm.runInContext(code,c);
    await c.growthStart({key:'cosmo'},{});
    assert.equal(c.GROW.phase,'done',JSON.stringify(c.GROW.errors));
    assert(c.GROW.result.best.sum>0,'growth search actually evaluates positive results');
    assert.deepEqual(JSON.parse(JSON.stringify(c.GROW.result.best)),baseline,'cleanup preserves exact results');
    assert.equal(life.created-created,retained?0:1,'retained owner pool is reused');
    assert.equal(life.active,retained?1:0,'growth-only session is released on completion');
    if(retained)assert.equal(c.CSR.session,ownedSession);
    assert.equal(c.GROW.stop,null);
    h.close();assert.equal(life.active,0,'all workers remain reachable for cleanup');
  }finally{localSession?.close();h.close();}
}
async function main(){
  await check();await check(source,true);
  const cleanup='if(state.session!==owned.session)state.session?.close();';
  assert(source.includes(cleanup));
  await assert.rejects(()=>check(source.replace(cleanup,'')),/growth-only session is released/);
  await assert.rejects(()=>check(source.replace(cleanup,'state.session?.close();'),true),/growth-only session is released/);
  console.log('PASS cosmo growth session: detached cleanup, persistent owner reuse, exact results; 2 killed mutations');
}
if(require.main===module)main().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={check};
