const assert=require('node:assert/strict'),fs=require('node:fs');
const G=require('../gwen_lane'),P=require('../gwen_policy');
const base={mode:'direct',phase:'idle',count:4};
for(const phase of ['idle','work','result','error']){
  assert.equal(G.bannerState({...base,phase},true),'','actor must hide banner');
  assert.equal(G.bannerState({...base,phase},false),['idle','work'].includes(phase)?'':phase);
  assert.equal(G.bannerState({...base,mode:'home',phase},false),'');
}
// reco 무대도 배너 표시
for(const phase of ['idle','work','result','error']){
  assert.equal(P.bannerState({...base,mode:'reco',phase},false),['idle','work'].includes(phase)?'':phase);
}
for(const count of [0,1,2,3,4])assert.equal(G.bannerState({...base,count},false),'');
assert.equal(G.bannerState({...base,phase:'result',stale:true},false),'');
for(const phase of ['work','result'])assert.equal(G.bannerState({...base,phase,bundleRunning:true},false),'');
for(const random of [()=>0,()=>.499,()=>.999]){
  const pick=G.bannerPicker(random);let previous;
  for(let id=1;id<30;id++){
    const work=pick('work');assert.equal(work,'');
    assert.equal(pick('work'),work);
    const now=pick('result',id);assert.notEqual(now,previous);
    assert.equal(pick('result',id),now);pick('');assert.equal(pick('result',id),now);
    assert.equal(pick('error'),'error');previous=now;
  }
}
const pick=G.bannerPicker(()=>0),first=pick('result',1);pick('result',2);
assert.equal(pick('result',1),first,'return to earlier report keeps phrase');
const budget=JSON.parse(fs.readFileSync('tools/gwen_art/budget.json','utf8')).case_banner;
let total=0;
for(const [file,bytes] of Object.entries(budget.files)){
  const actual=fs.statSync('assets/ui_icons/'+file).size;
  assert.equal(actual,bytes);assert(actual<=80000);total+=actual;
}
assert.equal(total,budget.served_bytes);
const html=fs.readFileSync('party_template.html','utf8');
assert.equal(Object.keys(budget.files).length,4);
for(const key of ['working','searching']){
  assert(!fs.existsSync(`assets/ui_icons/case_banner_${key}.webp`));
  assert(!html.includes(`data-phrase="${key}"`));
}
assert(!html.includes('direct-progress-lane'));
assert(!fs.readFileSync('direct.css','utf8').includes('gwen-banner-dot'));
assert(!fs.readFileSync('direct.css','utf8').includes('gwen-banner-pop'));
for(const key of ['magnify','think','board','coffee','stakeout','stamp'])assert(G.CHOICES.work.includes(key));
for(const [key,text] of Object.entries(G.BANNER_COPY))assert(html.includes(`data-phrase="${key}" hidden><span class="gwen-banner-fallback">${text}</span>`));
console.log('PASS case banner states / nonrepeat / stable reports / copy / budgets');
