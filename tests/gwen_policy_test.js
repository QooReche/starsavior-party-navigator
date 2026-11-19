const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../gwen_policy'),U=require('../ux_ui');

// --- resultCandidates: 레인 결과 후보(항상 st_*) ---
const high=P.resultCandidates(.8,false,false);
assert(high.every(c=>U.GWEN_SCENES[c]),`all high candidates in GWEN_SCENES: ${high}`);
assert(high.includes('st_reach'),'high includes st_reach');
assert(high.includes('st_verdict'));
const medium=P.resultCandidates(.3,false,false);
assert(medium.every(c=>U.GWEN_SCENES[c]));
const low=P.resultCandidates(.01,false,false);
assert(low.every(c=>U.GWEN_SCENES[c]));
assert(low.includes('st_cry'));
const better=P.resultCandidates(null,true,false);
assert(better.includes('st_wink'));assert(better.includes('st_reach'));
const recoHigher=P.resultCandidates(null,false,true);
assert(recoHigher.includes('st_point'));

// --- resultCandidatesSD: 작은 인라인 문맥(SD 유지) ---
const sdHigh=P.resultCandidatesSD(.8,false,false);
assert(sdHigh.every(c=>U.GWEN_SCENES[c]));
assert(!sdHigh.some(c=>c.startsWith('st_')),'SD candidates must not include st_*');
const sdLow=P.resultCandidatesSD(.01,false,false);
assert(sdLow.includes('cry'));

// --- resultArt: 결과 그림 한 장 선택 ---
// portrait=true(레인): st_* 사용
assert.equal(P.resultArt(.8,{seed:.1,portrait:true}),'st_verdict');
assert.equal(P.resultArt(.01,{portrait:true}),'st_cry');
assert(P.resultArt(.8,{seed:.9,portrait:true}).startsWith('st_'));
// portrait=false(인라인): SD 사용
assert(!P.resultArt(.8,{seed:.1,portrait:false}).startsWith('st_'));
// 점수형·비유효: 중립
assert.equal(P.resultArt(undefined,{kind:'score',portrait:true}),'st_point');
assert.equal(P.resultArt(NaN,{portrait:true}),'st_point');
assert.equal(P.resultArt(undefined,{kind:'score',portrait:false}),'report');

// --- bannerState ---
assert.equal(P.bannerState({mode:'direct',phase:'result',count:4},false),'result');
assert.equal(P.bannerState({mode:'reco',phase:'result',count:4},false),'result');
assert.equal(P.bannerState({mode:'reco',phase:'error',count:4},false),'error');
assert.equal(P.bannerState({mode:'reco',phase:'work',count:4},false),'');
assert.equal(P.bannerState({mode:'home',phase:'result',count:4},false),'');
assert.equal(P.bannerState({mode:'direct',phase:'result',count:4},true),'','onBoard hides banner');
assert.equal(P.bannerState({mode:'direct',phase:'result',bundleRunning:true},false),'');
assert.equal(P.bannerState({mode:'direct',phase:'result',stale:true},false),'');

// --- bannerPicker ---
for(const random of [()=>0,()=>.499,()=>.999]){
  const pick=P.bannerPicker(random);let previous;
  for(let id=1;id<30;id++){
    assert.equal(pick('work'),'');
    const now=pick('result',id);assert.notEqual(now,previous);
    assert.equal(pick('result',id),now);
    assert.equal(pick('error'),'error');previous=now;
  }
}

// --- bannerMarkup ---
const markup=P.bannerMarkup();
for(const key of ['investigation','inquiry','calculation','error']){
  assert(markup.includes(`data-phrase="${key}"`),`banner markup includes ${key}`);
  assert(markup.includes(P.BANNER_COPY[key]),`banner markup includes copy for ${key}`);
}

// 경계 양쪽·점수/비유효의 우선순위를 실제 소스 변이로 검사함.
function boundaries(p){
  for(const [clear,art] of [[0,'st_cry'],[.0499,'st_cry'],[.05,'st_point'],[.6999,'st_point'],[.7,'st_verdict'],[1,'st_verdict'],[undefined,'st_point'],[null,'st_point'],[NaN,'st_point']]){
    assert.equal(p.resultArt(clear,{seed:0}),art,String(clear));
    assert(p.resultCandidates(clear).includes(art),String(clear)+' lane candidate');
  }
  assert.equal(p.resultArt(1,{kind:'score',seed:0}),'st_point','score overrides clear');
}
boundaries(P);
const source=fs.readFileSync(require.resolve('../gwen_policy'),'utf8');
for(const [name,from,to] of [
  ['high boundary','if(clear>=.7){','if(clear>.7){'],
  ['low boundary',"if(clear<.05)return 'st_cry'", "if(clear<=.05)return 'st_cry'"],
  ['nonfinite/score neutrality',"if(kind==='score'||!Number.isFinite(clear))return portrait?'st_point':'report'","if(kind==='score'||!Number.isFinite(clear))return portrait?'st_cry':'cry'"],
]){assert(source.includes(from));const c={module:{exports:{}}};vm.runInNewContext(source.replace(from,to),c);
  assert.throws(()=>boundaries(c.module.exports),{code:'ERR_ASSERTION'},name);console.log('MUTATION caught + restored (isolated VM):',name);}

console.log('PASS gwen_policy: resultCandidates, resultCandidatesSD, resultArt, bannerState (direct+reco), bannerPicker, bannerMarkup; 3 boundary mutations');
