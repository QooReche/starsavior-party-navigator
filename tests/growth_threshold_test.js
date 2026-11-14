// Public synthetic account; exercise actual overwrite, stat calculation and presentation.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),G=require('../growth_guide'),U=require('../ux_ui');
const growth=require('../data/growth.json'),raw=require('./fixtures/myinfo_synthetic.json');
const slots=require('../data/myinfo_slots.json'),grades=require('../data/archive_grades.json');
const spec=growth.assumed.units.luna,roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
const clone=structuredClone,plain=x=>JSON.parse(JSON.stringify(x));
function account(){
  const info=clone(raw);info.units=[];info.star_link={level:240,source:[],slots:[]};info.star_link_level=240;
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  const u=M.assume('luna',info,growth).unit;u.level=240;u.favor=30;u.skills.passive=2;
  info.units=[u];return info;
}
function check(m=M){
  function run(edit,content='op'){
    const info=account();edit(info.units[0],info);const original=JSON.stringify(info);
    const r=m.overwrite(info,roster,growth,content,{includeMissing:true,slots});
    assert.deepEqual(plain(r.errors),[]);assert.equal(JSON.stringify(info),original);
    assert.equal(r.info.units.length,1);assert.deepEqual(Object.keys(r.profile.units),['luna']);
    assert(r.profile.results.luna.power>0);assert.equal(r.info.units[0].skills.passive,info.units[0].skills.passive);
    const actual=S.final_stats(r.info.units[0],r.info,growth,S.rule_for_content(content));
    assert.deepEqual(plain(r.profile.results.luna),actual,'snapshot must feed the real calculator');
    return {r,u:r.info.units[0],old:info.units[0],info,fields:r.changes.luna?.changedFields||[]};
  }
  assert.deepEqual(run(()=>{}).fields,[],'above all thresholds: byte-for-byte unchanged');
  for(const [levels,after] of [[[7,7,7],[10,10,10]],[[7,7,8],[10,10,8]],[[10,10,1],[10,10,10]],[[6,8,8],[10,8,8]],[[8,8,8],[8,8,8]],[[8,9,10],[8,9,10]]]){
    const {u,fields}=run(u=>{[u.skills.basic,u.skills.special,u.skills.ultimate]=levels;});
    assert.deepEqual([u.skills.basic,u.skills.special,u.skills.ultimate],after,levels.join('/'));
    assert.equal(fields.includes('skills'),levels.some(v=>v<=7));
  }
  // Deliberately weak stats make the eligible preset win; enhancement alone must gate it.
  for(const [levels,raised] of [[[13,14,14,14,14,14],true],[[14,14,14,14,14,14],false],
    [[11,15,15,15,15,15],true],[[12,15,15,15,15,15],false],[[14,15,15,15,15,15],false]]){
    const {u,old,fields}=run(u=>u.equip.forEach((e,i)=>{e.enhance=levels[i];e.main.value=1;e.subs=[];}));
    assert.equal(fields.includes('equip'),raised,levels.join('/'));
    assert.deepEqual(plain(u.equip),raised?spec.equip:old.equip);
  }
  assert(run(u=>u.equip.pop()).fields.includes('equip'),'empty slot');
  assert(run(u=>{u.equip[5]=clone(u.equip[0]);u.equip.forEach(e=>{e.main.value=1;e.subs=[];});}).fields.includes('equip'),'duplicate slot is still a missing body part');
  const main=spec.journey.indexOf(Math.max(...spec.journey));
  // 스텔라 아카이브: 기준표 주력 칸이 950 미만이면 «기준표 기록으로 통째 교체»가 후보, 950 이상이면 후보 아님. 칸별로 섞지 않는다
  for(const [n,raised] of [[949,true],[950,false]]){
    const {u,old,fields}=run(u=>{u.gauntlet.journey=[100,100,100,100,100];u.gauntlet.journey[main]=n;});
    assert.equal(fields.includes('journey'),raised);
    assert.deepEqual(plain(u.gauntlet.journey),raised?spec.journey:old.gauntlet.journey);
  }
  // 후보여도 통째 교체가 지금 기록보다 못하면(다른 칸이 훨씬 높음) 그대로 둔다
  {const {u,old,fields}=run(u=>{u.gauntlet.journey=[1400,1400,1400,1400,1400];u.gauntlet.journey[main]=949;});
   assert(!fields.includes('journey'));assert.deepEqual(plain(u.gauntlet.journey),old.gauntlet.journey);}
  const noGauntlet=run(u=>delete u.gauntlet);
  assert.deepEqual(plain(noGauntlet.u.gauntlet.journey),spec.journey);
  assert(noGauntlet.fields.includes('potentials'));
  for(const [n,raised] of [[20,true],[21,false]]){
    const {u,fields,r,info}=run(u=>u.favor=n);
    assert.equal(u.favor,raised?30:n);assert.equal(fields.includes('favor'),raised);
    if(raised){const display=U.member(r.changes.luna,info,growth,'op',grades),field=display.fields.find(f=>f.field==='favor');
      assert.equal(field.short,'20→30');assert(field.delta>0);assert(U.todosHtml(display).includes('20→30'));}
  }
  const max=Math.min(10,Math.max(...Object.entries(growth.units[spec.uid].resonance_unlock).filter(([,lv])=>lv<=240).map(([n])=>+n)));
  for(const [n,raised] of [[max-1,true],[max,false]]){
    const {u,fields}=run(u=>u.resonance=n);assert.equal(u.resonance,max);assert.equal(fields.includes('resonance'),raised);
  }
  for(const [gap,raised] of [[9,false],[10,true]]){
    const {r,fields}=run(u=>u.level=240-gap);
    assert.equal(fields.includes('level'),raised);assert.equal(S.effective_level(r.info.units[0],r.info),raised?240:240-gap);
  }
  assert(!run((u,info)=>{u.level=1;info.star_link.source=[u.id];}).fields.includes('level'));
  assert(!run((u,info)=>{delete u.level;delete info.star_link;}).fields.includes('level'));
  const learned=run(u=>{u.gauntlet.potentials=[[spec.potential[0],1,0,0]];});
  assert(!learned.fields.includes('potentials'));
  const absent=run(u=>u.gauntlet.potentials=[]);assert(absent.fields.includes('potentials'));
  assert.equal(absent.u.gauntlet.potentials[0][1],1);
  const different=growth.assumed.special_ids.find(id=>id!==spec.potential[0]&&growth.assumed.combat_support.potentials[id]?.includes('1')&&growth.potentials[id]?.['1']);
  assert(different,'exercise a different learned special potential');
  assert(!run(u=>u.gauntlet.potentials=[[different,1,0,0]]).fields.includes('potentials'));
  const fixed=run(u=>{u.level=1;u.resonance=0;u.favor=20;},'cosmo');
  assert(!fixed.fields.includes('level'));assert(!fixed.fields.includes('resonance'));
  assert.deepEqual(plain(fixed.r.info.star_link),fixed.info.star_link);
  const html=U.todosHtml(U.member(fixed.r.changes.luna,fixed.info,growth,'cosmo',grades));
  assert(!html.includes('data-growth-field="level"'));assert(!html.includes('data-growth-field="resonance"'));
  const excluded=m.overwrite(account(),roster,growth,'op',{excluded:['luna'],includeMissing:true});
  assert.deepEqual(plain(excluded.changes),{});assert.equal(excluded.info.units.length,1);
}
function options(g=G){for(const owned of [undefined,true,false])for(const ao of [undefined,true,false]){
  assert.deepEqual(plain(g.options({growth:true,owned},{ao})),{growth:true,owned:false});
  assert.deepEqual(plain(g.options({growth:true,owned},{ag:false,ao})),{growth:false,owned:false});
}}
function signature(code=fs.readFileSync(require.resolve('../growth_ui'),'utf8')){
  const ctx={GrowthGuide:G,MyInfoReco:{...M},MI:{hash:'test',info:account(),growth},CFG:{restrict:{}},EXCL:new Set(),R:roster,
    document:{getElementById:()=>({checked:true})},miProfile:()=>M.profile(account(),roster,growth,'op'),
    breakOwned:()=>[],MM:'myinfo',SCROWN:0,SIMOPT:{},growthConditions:()=>({})};
  vm.createContext(ctx);vm.runInContext(code,ctx);ctx.growthConditions=()=>({});
  const args=[{key:'op',name:'op'},{tab:'tab',name:'stage'},{engine:'e',data:'d'}];
  assert.equal(ctx.growthTargets(...args).length,1);
  const before=ctx.growthSig(...args),cache=ctx.growthCacheTag();
  ctx.MyInfoReco.THRESHOLD_POLICY={...M.THRESHOLD_POLICY,skillMax:8};
  assert.notEqual(ctx.growthSig(...args),before);assert.notEqual(ctx.growthCacheTag(),cache);
  assert(!G.compatible(before,ctx.growthSig(...args)));
  ctx.MyInfoReco.THRESHOLD_POLICY=M.THRESHOLD_POLICY;ctx.MyInfoReco.OVERWRITE_VERSION='old';
  assert.notEqual(ctx.growthSig(...args),before);assert.notEqual(ctx.growthCacheTag(),cache);
}
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);
  const api=ctx.module.exports;return api.overwrite?{...api,overwrite:(...args)=>plain(api.overwrite(...args))}:api;}
const source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8');
check();check(load(source));options();signature();
const mutations=[
  ['skill boundary','(old.skills?.[k]||0)<=THRESHOLD_POLICY.skillMax','(old.skills?.[k]||0)<THRESHOLD_POLICY.skillMax'],
  ['skill per-skill raise','<=THRESHOLD_POLICY.skillMax?Math.max','<=99?Math.max'],
  ['equipment total boundary','<THRESHOLD_POLICY.equipSum','<=THRESHOLD_POLICY.equipSum'],
  ['equipment slot boundary','<THRESHOLD_POLICY.equipMin','<=THRESHOLD_POLICY.equipMin'],
  ['archive boundary','<THRESHOLD_POLICY.archiveMain','<=THRESHOLD_POLICY.archiveMain'],
  ['favor boundary','<=THRESHOLD_POLICY.favorMax','<THRESHOLD_POLICY.favorMax'],
  ['link boundary','>=THRESHOLD_POLICY.linkGap','>THRESHOLD_POLICY.linkGap'],
  ['resonance disabled',"fields.push('resonance')","void 0"],
  ['passive overwritten','u.skills={...old.skills,','u.skills={...old.skills,passive:4,'],
  ['missing included','||!out.units[s.key]',''],
  ['potential disabled',"fields.push('potentials')","void 0"],
  ['fixed content','const fixed=Stats.rule_for_content(content)===\'fixed200\'','const fixed=false'],
];
for(const [name,from,to] of mutations){assert(source.includes(from),name+' anchor');
  assert.throws(()=>check(load(source.replace(from,to))),{code:'ERR_ASSERTION'},name+' mutation must fail');
  console.log('MUTATION caught (isolated source):',name);
}
const guide=fs.readFileSync(require.resolve('../growth_guide'),'utf8');
assert.throws(()=>options(load(guide.replace('owned:false','owned:(shared.ao??saved.owned)!==false'))),{code:'ERR_ASSERTION'});
console.log('PASS threshold boundaries, real stats, ownership, options, signatures; 13 mutations caught');
