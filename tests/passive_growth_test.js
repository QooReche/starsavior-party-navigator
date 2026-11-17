// Synthetic accounts only. Exercise the actual assume/overwrite/stat payloads.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),growth=require('../data/growth.json');
const raw=require('./fixtures/myinfo_synthetic.json'),source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8');
const plain=x=>JSON.parse(JSON.stringify(x));
const guard='if (unit.star === 0) unit.skills.passive = 0;';
assert(source.includes(guard));
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);return ctx.module.exports;}
const old=load(source.replace(guard,''));
function account(key){
  const info=structuredClone(raw);info.units=[];info.star_link_level=240;info.star_link={level:240,source:[],slots:[]};
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  const u=M.assume(key,info,growth).unit;u.level=80;u.star=0;u.skills={basic:1,special:1,ultimate:1,passive:0};
  info.units=[u];return info;
}
function check(m=M){
  for(const key of Object.keys(growth.assumed.units)){
    const info=account(key),before=JSON.stringify(info),a=m.assume(key,info,growth);
    assert.equal(a.unit.star,0);assert.equal(a.unit.skills.passive,0,key);
    assert.equal(S.final_stats(a.unit,a.targetInfo,growth).combat.skills.passive,0);
    assert.equal(JSON.stringify(info),before,'import must stay unchanged');
    info.units[0].star=1;
    assert.deepEqual(plain(m.assume(key,info,growth).unit.skills),growth.assumed.units[key].skills);
    info.units=[];
    assert.equal(m.assume(key,info,growth).unit.skills.passive,0,'unowned starts at break 0');
  }
}
check();assert.throws(()=>check(old),assert.AssertionError);check();
const changes=[];
for(const key of Object.keys(growth.assumed.units)){
  const info=account(key),roster=[{key,uid:info.units[0].id}];
  for(const content of ['op','cosmo','rush'])
    assert.deepEqual(plain(M.overwrite(info,roster,growth,content)),plain(old.overwrite(info,roster,growth,content)),key+'/'+content);
  const before=old.assume(key,info,growth),after=M.assume(key,info,growth);
  const a=S.final_stats(before.unit,before.targetInfo,growth).power,b=S.final_stats(after.unit,after.targetInfo,growth).power;
  changes.push({key,before:a,after:b,delta:b-a});
}
const key='asherah-voyager',info=account(key);
const result={key,current:info.units[0].skills,before:old.assume(key,info,growth).unit.skills,
  after:M.assume(key,info,growth).unit.skills,overwrite:M.overwrite(info,[{key,uid:info.units[0].id}],growth,'op').info.units[0].skills,
  summary:{units:changes.length,changed:changes.filter(x=>x.delta!==0).length,
    minDelta:Math.min(...changes.map(x=>x.delta)),maxDelta:Math.max(...changes.map(x=>x.delta)),
    overwriteChanged:0},changes};
if(process.argv.includes('--payload'))console.log(JSON.stringify(result));
else console.log('PASS passive 0 preserved, break 1/unowned, mutation caught/restored, overwrite parity',result.summary);
