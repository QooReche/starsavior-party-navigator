// Synthetic accounts; no account captures. Exercise the actual stat/party/import paths.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),P=require('../direct_party'),S=require('../myinfo_stats'),I=require('../myinfo_import');
const L=require('../star_link');
const growth=structuredClone(require('../data/growth.json')),raw=require('./fixtures/myinfo_synthetic.json');
// The recommendation roster currently excludes R units: use one synthetic R template.
Object.values(growth.units).find(u=>u.grade==='SR').grade='R';
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
function account(grade,star,blossom=false,state=false){
  const spec=roster.find(r=>growth.units[r.uid].grade===grade);assert(spec,grade);
  const info=structuredClone(raw);info.units=[];info.star_link_level=200;
  info.star_link={level:200,source:[],slots:[],unlocked:true};
  const u=M.assume(spec.key,info,growth).unit;
  Object.assign(u,{level:40,star,blossom,resonance:0,skills:{basic:1,special:1,ultimate:1,passive:0}});
  info.units=[u];info.star_link.unlocked=state;
  if(state==null)delete info.star_link.unlocked;
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  return {info,u,key:spec.key};
}
function check(m=M,p=P){
  let count=0;
  for(const [grade,star,blossom,cap] of [['SSR',0,false,160],['SSR',1,false,160],['SSR',2,false,180],['SSR',3,false,200],['SR',3,false,160],['SR',2,true,180],['SR',3,true,200],['R',0,false,80]]){
    for(const state of [false,true,null]){
      const {info,u,key}=account(grade,star,blossom,state),frozen=JSON.stringify(info);
      const d=p.edit(p.empty(),{type:'put',key,slot:0}),ctx={info,roster,growth,content:'op'};
      const before=p.powers(d,ctx);d.slots[0].grown=true;const after=p.powers(d,ctx),a=m.assume(key,info,growth);
      assert.deepEqual(after.errors,[]);assert.equal(after.profile.units[key].star,star);
      assert.equal(after.profile.units[key].blossom,blossom);assert.equal(after.profile.units[key].skills.passive,0);
      if(star===0)assert.equal(a.unit.skills.passive,0);
      if(state===false){
        assert.equal(a.levelTarget,cap);assert.equal(a.unit.level,cap);assert.equal(a.targetInfo,info);
        assert.equal(after.profile.units[key].level,cap);assert.equal(after.prelink[key].target,cap);
        assert(after.values[0].power>before.values[0].power);assert.deepEqual(after.linked,[]);
        assert.match(after.prelink[key].text,/실제로는 Lv\./);
        assert.deepEqual(after.profile.results[key],S.final_stats(after.profile.units[key],info,growth,'normal'));
        assert.deepEqual(M.overwrite(info,roster,growth,'op').info.star_link,info.star_link,'no fake registration');
      }else if(state===true){assert.equal(a.levelTarget,200);assert.deepEqual(after.linked,[key]);assert(!after.prelink[key]);}
      else{assert.equal(a.levelTarget,null);assert.equal(a.unit.level,40);assert.deepEqual(after.levelUnknown,[key]);assert.deepEqual(after.linked,[]);}
      for(const content of ['cosmo','rush']){const fixed=p.powers(d,{...ctx,content});assert.deepEqual(fixed.prelink,{});assert.deepEqual(fixed.levelUnknown,[]);}
      assert.equal(JSON.stringify(info),frozen);count++;
    }
  }
  const {info,u,key}=account('SSR',3),d=p.edit(p.empty(),{type:'put',key,slot:0});d.slots[0].grown=true;
  for(const level of [19,20,59,60,99,100,139,140]){
    info.units=[u,...[2,3,4,5].map(id=>({...u,id,level}))];
    assert.equal(!!m.prelinkNote(u,info,growth).text.includes('필요할 수 있음'),level<140);
  }
  u.level=240;const a=m.assume(key,info,growth);assert.equal(a.unit.level,240);assert(m.prelinkNote(u,info,growth).aboveCap);assert.match(m.prelinkNote(u,info,growth).text,/Lv\.240/);
  // An inconsistent high account/link level must not inject enhancement bonuses.
  const plain=structuredClone(info);plain.star_link.level=plain.star_link_level=0;
  assert.deepEqual(S.final_stats(u,info,growth),S.final_stats(u,plain,growth));
  info.units=[];const unowned=m.assume(key,info,growth);assert.equal(unowned.unit.star,0);assert.equal(unowned.unit.level,160);
  assert(p.validate(d,{info,roster,growth,content:'op'}).errors.some(e=>e.code==='unowned'));
  return count;
}
const cases=check();
const src=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8');
for(const [from,to] of [["unit.star===2 ? 180","unit.star===2 ? 160"],["unit.blossom === true","false"]]){
  assert(src.includes(from));const ctx={module:{exports:{}},require:p=>require('../'+p)};
  vm.runInNewContext(src.replace(from,to),ctx);assert.throws(()=>check(ctx.module.exports),assert.AssertionError);
}
check();
(async()=>{
  for(const state of [false,true,null,undefined]){
    const {info}=account('SSR',2,false,state??null);if(state===null)info.star_link.unlocked=null;
    assert.equal(I.validate(info),'');
    assert.equal(L.availability(info),state===true?'':state===false?'스타링크 미개방':'다시 불러오기 필요');
    const shared=await I.fromHash('#myinfo='+await I.toHash(info));assert.deepEqual(shared,info);
    assert.deepEqual(JSON.parse(JSON.stringify(shared)),info,'storage roundtrip');
  }
  for(const value of [0,1,'false',[],{}]){const {info}=account('SR',0);info.star_link.unlocked=value;assert(I.validate(info));}
  for(const value of [0,'true',null]){const {info,u}=account('SR',0);u.blossom=value;assert(I.validate(info));}
  console.log(`PASS ${cases} unlock/rarity/break/blossom cases, max/4-person notes, fixed, passive, share/storage, 2 mutations`);
})().catch(e=>{console.error(e);process.exitCode=1;});
