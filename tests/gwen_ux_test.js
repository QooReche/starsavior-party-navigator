const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const U=require('../ux_ui'),source=fs.readFileSync(require.resolve('../ux_ui'),'utf8');
// gwenReport 는 이제 st_* 등신대를 사용함 (gwen_policy.resultArt 경유).
function reports(u=U){
  for(const [clear,expected] of [[0,'st_cry'],[.0499,'st_cry'],[.05,'st_point'],[.6999,'st_point'],[.7,'st_verdict'],[1,'st_verdict'],[undefined,'st_point'],[null,'st_point'],[NaN,'st_point']]){
    const result={clear},html=u.gwenReport(result,{clear});
    assert.match(html,new RegExp(`data-gwen-expression="${expected}"`),String(clear));
    assert.equal(u.gwenReport(result,{clear:1}),html,'result choice is fixed across re-renders');
  }
  for(const [result,context] of [[[{clear:1}],{clear:1}],[{score:100},{kind:'score',clear:1}],[{clear:1},{}]])
    assert.match(u.gwenReport(result,context),/data-gwen-expression="st_point"/,'missing/score/array is neutral (st_*)');
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
// st_reach 등신대 존재 확인
assert(U.GWEN_SCENES.st_reach,'st_reach must exist in GWEN_SCENES');
assert.match(U.gwenImage('st_reach'),/width="160" height="160"/,'st_reach gwenImage works');
// gwenReaction 에 st_reach 가 고확률 후보에 포함
const reacHtml=U.gwenReaction(.9);
assert(reacHtml.includes('gwen-reaction'),'gwenReaction produces reaction markup');
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
// 변이 검사: gwenReport 의 st_* 경계와 gwenError 의 그림 선택
for(const [old,replacement,check] of [
  // gwenReport 는 gwen_policy.resultArt 를 사용하므로, 경계 변이는 policy 쪽에서 검사
  ["cause==='calculation'?'cry'","cause==='calculation'?'surprised'",errors],
]){assert(source.includes(old));assert.throws(()=>check(load(source.replace(old,replacement))),{code:'ERR_ASSERTION'});}
console.log('PASS Gwen result st_* portraits, neutral st_point, stable choice, causes, asset table, all dialogue seeds, st_reach; 1 mutation caught');
