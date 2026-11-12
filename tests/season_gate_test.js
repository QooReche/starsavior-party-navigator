const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('season_gate.js','utf8');
function load(code){const ctx={module:{exports:{}},URLSearchParams};vm.runInNewContext(code,ctx);return ctx.module.exports;}
function audit(g){
  const season={start:'2026-11-01T04:00:00+09:00',end:'2026-11-05T04:00:00+09:00',settleEnd:'2026-11-12T04:00:00+09:00'};
  const s=Date.parse(season.start),e=Date.parse(season.end);
  assert.equal(g.time('2026-11-01'),Date.parse('2026-10-31T15:00:00Z'));
  for(const [now,phase,blocked] of [[s-1,'upcoming',true],[s,'active',false],[e-1,'active',false],[e,'ended',true],[e+7*86400000,'ended',true]]){
    const r=g.state(season,now);assert.equal(r.phase,phase);assert.equal(r.blocked,blocked);
    for(const query of ['?dev=1','?season=force']){const bypass=g.state(season,now,query);assert(!bypass.blocked);assert(bypass.bypass);assert.equal(bypass.phase,phase);}
  }
  for(const query of ['?dev=0','?dev=10','?season=forced','?auto=1'])assert(g.state(season,e,query).blocked);
  for(const unknown of [null,{}, {start:season.start}, {end:season.end}, {start:'bad',end:season.end},{start:season.end,end:season.start}]){
    const r=g.state(unknown,e);assert.equal(r.phase,'unknown');assert.equal(r.label,'기간 미확인');assert(!r.blocked);
  }
  assert.equal(g.state(season,e).message,'시즌 종료 — 새 시즌 자료 반영 전');
}
function mutation(name,from,to){assert(source.includes(from));assert.throws(()=>audit(load(source.replace(from,to))),{code:'ERR_ASSERTION'});console.log('MUTATION caught:',name);}
async function entryGuards(){
  const page=fs.readFileSync('party_template.html','utf8'),ui=fs.readFileSync('growth_ui.js','utf8');
  // The real entry guard must return before any account/worker setup is touched.
  for(const [code,start,end,args] of [
    [page,'async function guildSearchStart','$("guild-search").addEventListener', [{},{}]],
    [page,'async function cosmoSearchStart','$("cosmo-search").addEventListener', [{},{}]],
    [ui,'async function growthStart','function growthBaseline',[{key:'guild'},{}]],
    [page,'function showReco','function run(',[]],
    [page,'function runCore','$("out").addEventListener',[]]]){
    // Only evaluate the function declaration; stop at the first following top-level declaration/listener.
    let fn=code.slice(code.indexOf(start),code.indexOf(end,code.indexOf(start)));
    if(start==='function runCore')fn=fn.slice(0,fn.indexOf('\nfunction ',1));
    const name=start.split('function ')[1],ctx={seasonBlocked:()=>true,contents:[{key:'guild'}],$:()=>({value:0})};
    vm.createContext(ctx);vm.runInContext(fn,ctx);
    await ctx[name](...args);
    ctx.seasonBlocked=()=>false;
    await assert.rejects(async()=>ctx[name](...args),e=>e.name==='ReferenceError');
    console.log('MUTATION caught: removed gate at',name);
  }
}
(async()=>{
  audit(load(source));
  mutation('end boundary','now>=end','now>end');
  mutation('start boundary','now<start','now<=start');
  mutation('settlement blocked','time(season?.end)','time(season?.settleEnd)');
  mutation('unknown open','blocked:closed&&!bypass','blocked:!bypass');
  mutation('developer bypass',"q.get('dev')==='1'",'false');
  await entryGuards();console.log('ALL OK season gate');
})().catch(e=>{console.error(e);process.exitCode=1;});
