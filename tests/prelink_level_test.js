// Current exports cannot prove CT_SYNCHRO unlock: zero/null-converted level is unknown.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../direct_party'),M=require('../myinfo_reco'),S=require('../myinfo_stats'),L=require('../star_link');
const growth=require('../data/growth.json'),raw=require('./fixtures/myinfo_synthetic.json');
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
const plain=x=>JSON.parse(JSON.stringify(x));
function context(){const info=structuredClone(raw);
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  return {info,roster,growth,content:'op'};
}
function check(p=P){
  for(const mode of ['zero','missing-link','missing-source','missing-slots','missing-unit-level','legacy']){
    for(const star of [0,1,2,3]){
      const c=context(),u=c.info.units[0],key=roster.find(s=>s.uid===u.id).key;
      u.star=star;u.level=240; // Never lower a high imported own level, even when its effective level is unknown.
      if(mode==='zero'){c.info.star_link={level:0,source:[],slots:[]};c.info.star_link_level=0;}
      if(mode==='missing-link')delete c.info.star_link;
      if(mode==='missing-source')delete c.info.star_link.source;
      if(mode==='missing-slots')delete c.info.star_link.slots;
      if(mode==='missing-unit-level')delete u.level;
      if(mode==='legacy'){delete c.info.star_link;for(const u of c.info.units)delete u.level;}
      const frozen=JSON.stringify(c.info),level=S.effective_level(u,c.info);
      const d=p.edit(p.empty(),{type:'put',key,slot:0}),off=p.powers(d,c);d.slots[0].grown=true;
      const on=p.powers(d,c),a=M.assume(key,c.info,growth),over=M.overwrite(c.info,roster,growth,'op',{
        excluded:roster.filter(s=>s.key!==key).map(s=>s.key)});
      assert.deepEqual(plain(on.levelUnknown),[key],mode);
      assert.equal(off.levelUnknown.length,0);assert.deepEqual(plain(on.errors),over.errors,'legacy errors preserved');
      assert.equal(on.linked.length,0,'unknown data must not become a hypothetical registration');
      assert.equal(a.levelTarget,null);assert(a.levelUnknown);assert.equal(a.unit.level??null,u.level??null);
      assert.equal(S.effective_level(a.unit,a.targetInfo),level,'no level assumption');
      assert.equal(on.profile.units[key].level??null,u.level??null);
      assert.deepEqual(plain(on.values[0]),over.profile.results[key],'legacy calculation preserved');
      assert.equal(JSON.stringify(c.info),frozen,'import untouched');
      assert.throws(()=>M.assume(key,c.info,growth,{fields:['level']}),/다시 불러오기 필요/);
      for(const content of ['cosmo','rush'])assert.equal(p.powers(d,{...c,content}).levelUnknown.length,0);
      assert(!p.powers(d,{...c,info:null,standard:{}}).levelUnknown?.length);
    }
  }
  const c=context(),u=c.info.units[0],key=roster.find(s=>s.uid===u.id).key;
  c.info.star_link={unlocked:true,level:200,source:[],slots:[]};c.info.star_link_level=200;u.level=199;
  const d=p.edit(p.empty(),{type:'put',key,slot:0});d.slots[0].grown=true;
  const on=p.powers(d,c);assert.deepEqual(plain(on.levelUnknown),[]);assert.deepEqual(plain(on.linked),[key]);
  assert.equal(S.effective_level(on.profile.units[key],{...c.info,star_link:{level:200,source:[],slots:[{id:u.id}]}}),200);
  c.info.units=[];assert(p.validate(d,c).errors.some(e=>e.code==='unowned'),'unowned remains blocked');
}
check();
const source=fs.readFileSync(require.resolve('../direct_party'),'utf8');
const guard="||Stats.level_info(unit,info).source==='legacy'";assert(source.includes(guard));
const ctx={UiShared:require('../ui_shared'),MyInfoReco:M,MyInfoStats:S,StarLink:L};vm.runInNewContext(source.replace(guard,''),ctx);
assert.throws(()=>check(ctx.DirectParty),assert.AssertionError);check();
console.log('PASS unknown vs legacy fallback, 0..3 breaks/high own level, no fake registration, fixed/standard hidden, opened preserved; mutation caught/restored');
