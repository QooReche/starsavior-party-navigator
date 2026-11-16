const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const U=require('../ux_ui'),source=fs.readFileSync(require.resolve('../ux_ui'),'utf8');
function reports(u=U){
  for(const [clear,expected] of [[0,'cry'],[.0499,'cry'],[.05,'report'],[.6999,'report'],[.7,'verdict'],[1,'verdict'],[undefined,'report'],[null,'report'],[NaN,'report']]){
    const result={clear},html=u.gwenReport(result,{clear});
    assert.match(html,new RegExp(`data-gwen-expression="${expected}"`),String(clear));
    assert.equal(u.gwenReport(result,{clear:1}),html,'result choice is fixed across re-renders');
  }
  for(const [result,context] of [[[{clear:1}],{clear:1}],[{score:100},{kind:'score',clear:1}],[{clear:1},{}]])
    assert.match(u.gwenReport(result,context),/data-gwen-expression="report"/,'missing/score/array is neutral');
}
function errors(u=U){
  for(const [cause,art] of [['calculation','cry'],['few','sulk'],['empty','sulk'],['other','surprised']])assert.match(u.gwenError(cause),new RegExp(`data-gwen-expression="${art}"`));
  for(const cause of ['cancel','uncalculated','best'])assert.equal(u.gwenError(cause),'');
}
reports();errors();
for(const key of ['cry','verdict','cheer','sulk','shy','doze','think','magnify','stamp','board','coffee','stakeout','zap']){
  assert(U.GWEN_SCENES[key]);assert.match(U.gwenImage(key),/width="160" height="160"/);
  assert(!U.gwenImage(key).includes('undefined'));assert(U.GWEN_SAY[key].length>=5);
}
for(const key of Object.keys(U.GWEN_SAY)){
  const seen=new Set();
  for(let i=0;i<80;i++){
    const c={module:{exports:{}},require:p=>require('../'+p),document:{},Math:Object.assign(Object.create(Math),{random:()=>i/80})};
    vm.runInNewContext(source,c);seen.add(c.module.exports.gwenSay(key));
  }
  assert.equal(seen.size,U.GWEN_SAY[key].length,`gwenSeed must reach every ${key} line`);
  for(const line of U.GWEN_SAY[key])assert.doesNotMatch(line,/단장(?!님)/);
}
for(const mode of ['inspect','screen','long'])assert.equal(U.gwenWork(mode).includes(' gwen-roam'),mode==='long');
function load(code){const c={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,c);return c.module.exports;}
for(const [old,replacement,check] of [
  ["!Number.isFinite(p)?'report'","!Number.isFinite(p)?'cry'",reports],
  ["p<.05?'cry'","p<=.05?'cry'",reports],
  ["p>=.7?(gwenSeed","p>.7?(gwenSeed",reports],
  ["cause==='calculation'?'cry'","cause==='calculation'?'surprised'",errors],
]){assert(source.includes(old));assert.throws(()=>check(load(source.replace(old,replacement))),{code:'ERR_ASSERTION'});}
console.log('PASS Gwen result boundaries, neutral probability/score/array, stable choice, causes, asset table, all dialogue seeds; 4 mutations caught');
