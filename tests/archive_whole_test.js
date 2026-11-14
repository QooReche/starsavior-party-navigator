// 스텔라 아카이브 육성 목표는 «기록 통째 교체»(11/14): 아카이브 5칸은 한 번의 여정 결과로 통째로 정해진다(한 칸 SG 는 현실적, 두 칸 동시 SG 는 어려움).
//  - 기준표 주력 칸이 950 미만이면(다른 칸이 1250 이어도) «기준표 5칸 배분으로 다시 만들기»가 후보
//  - 후보와 지금 기록 중 전투력이 높은 쪽 하나만 쓴다(장비 묶음과 같은 원칙, 같으면 지금 기록). 칸별로 큰 값을 섞지 않는다
//  - 채택되면 칩에 지금 주력 → 바뀌는 주력을 함께 보인다(이미 SG 인 칸을 버리는 추천임을 알게)
// 제보(가상 수치로 재현): 왈츠 아세라 힘 247·체력 1250·인내 761·집중 122·보호 97(합 2,477) — 종전엔 칸별 max 로 «힘 1250 + 체력 1250 …»(합 3,905)이라는
// 불가능한 기록으로 계산해 육성 결과가 부풀려졌다. 이 수치는 지금 기록의 전투력(46,374)이 기준표 기록(44,638)보다 높아 «그대로 둔다»가 된다(전투력 기준 — 장비 묶음과 같은 원칙).
// 공개 가상 픽스처만 쓴다. 실행: node tests/archive_whole_test.js
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const M=require('../myinfo_reco'),S=require('../myinfo_stats'),U=require('../ux_ui');
const growth=require('../data/growth.json'),grades=require('../data/archive_grades.json'),raw=require('./fixtures/myinfo_synthetic.json');
const view={...require('../data/myinfo_view.json'),itemSlots:require('../data/myinfo_slots.json')},slots=view.itemSlots;
const source=fs.readFileSync(require.resolve('../myinfo_reco'),'utf8'),KEY='waltz-asherah',spec=growth.assumed.units[KEY];
const roster=[{key:KEY,uid:spec.uid}],sum=a=>a.reduce((x,y)=>x+y,0),NAMES=['힘','체력','인내','집중','보호'];
const ASHERAH=[247,1250,761,122,97];
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);return ctx.module.exports;}
// 다른 항목은 모두 기준 이상(아카이브만 본다): 기준표 세팅으로 만든 뒤 아카이브만 바꾼다
function account(journey){const info=structuredClone(raw);info.units=[];info.star_link={level:240,source:[],slots:[]};info.star_link_level=240;
 for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
 const u=M.assume(KEY,info,growth).unit;u.level=240;u.favor=30;
 if(journey===null)delete u.gauntlet;else u.gauntlet.journey=journey.slice();
 info.units=[u];return info;}
const power=(info,journey,content='op')=>{const u=structuredClone(info.units[0]);u.gauntlet.journey=journey.slice();return S.final_stats(u,info,growth,S.rule_for_content(content)).power;};
function run(m,journey,content='op'){const info=account(journey),before=JSON.stringify(info),r=m.overwrite(info,roster,growth,content,{slots});
 assert.deepEqual(r.errors,[]);assert.equal(JSON.stringify(info),before,'원본 계정은 그대로');
 const a=r.changes[KEY],now=r.info.units[0].gauntlet.journey;
 return {info,r,a,now:Array.from(now),changed:!!a?.changedFields.includes('journey')};}

function check(m=M,ux=U){
 const main=spec.journey.indexOf(Math.max(...spec.journey));
 assert.equal(NAMES[main],'힘','시험 전제: 기준표 주력 칸 = 힘');assert.equal(spec.journey[main],1250);
 assert.equal(spec.journey.filter(v=>v>=950).length,1,'시험 전제: 기준표도 SG 는 한 칸뿐');
 // 1) 제보 수치: 다른 칸(체력)이 1250 이어도 기준표 주력(힘)이 950 미만이면 통째 교체 후보. 결과는 «지금 기록 그대로» 또는 «기준표 그대로» 둘 중 하나
 {const x=run(m,ASHERAH),keep=power(x.info,ASHERAH),swap=power(x.info,spec.journey);
  assert(JSON.stringify(x.now)===JSON.stringify(ASHERAH)||JSON.stringify(x.now)===JSON.stringify(spec.journey),'칸별로 섞인 기록: '+x.now);
  assert(x.now.filter(v=>v>=1250).length<=1,'SG 두 칸짜리 기록은 만들지 않는다: '+x.now);
  assert(sum(x.now)<=Math.max(sum(ASHERAH),sum(spec.journey)),'합이 두 기록 어느 쪽보다도 큼(섞음): '+sum(x.now));
  assert.notEqual(swap,keep,'시험 전제: 두 기록의 전투력이 다름');
  assert.equal(x.changed,swap>keep,'전투력이 높은 쪽 하나');assert.deepEqual(x.now,swap>keep?spec.journey:ASHERAH);
  if(x.changed){assert.equal(sum(x.now),sum(spec.journey),'교체하면 합 = 기준표 합');assert.deepEqual(x.a.changes.journey,{before:ASHERAH,after:spec.journey});
   // 칩: 통째 교체임과 지금 주력 → 바뀌는 주력
   const d=ux.member(x.a,x.info,growth,'op',grades,view),f=d.fields.find(f=>f.field==='journey');
   assert.equal(f.label,'스텔라 아카이브 기록 다시 만들기');assert.equal(f.short,'(주력 체력 SG → 힘 SG)');
   assert.match(f.detail,/기록 전체를 다시 만드는/);assert.match(f.detail,/지금보다 내려가는 칸: 체력·인내/);assert.match(f.detail,/체력 SG 1,250 → /);
   assert.equal(f.delta,swap-keep,'칩의 전투력 차이 = 통째 교체의 차이');
   assert.match(ux.todosHtml(d),/스텔라 아카이브 기록 다시 만들기 \(주력 체력 SG → 힘 SG\)/);
   assert.equal(x.r.profile.results[KEY].power,swap,'육성 계정의 전투력 = 통째 교체한 기록의 전투력(섞은 기록이 아님)');}
  else assert.equal(x.r.profile.results?.[KEY]?.power??keep,keep);}
 // 1-b) 주력을 다른 칸(체력)에 찍었지만 기록 전체가 기준표보다 약한 경우: 통째 교체를 채택하고, 칩에 «주력 체력 … → 힘 SG»(지금 주력을 버리는 추천임)를 보인다
 {const other=[247,1000,300,122,97],x=run(m,other),keep=power(x.info,other),swap=power(x.info,spec.journey);
  assert(swap>keep,'시험 전제: 기준표 기록이 더 강함');assert(x.changed);assert.deepEqual(x.now,spec.journey);assert.equal(sum(x.now),sum(spec.journey),'교체하면 합 = 기준표 합');
  assert.deepEqual(x.a.changes.journey,{before:other,after:spec.journey});
  const d=ux.member(x.a,x.info,growth,'op',grades,view),f=d.fields.find(f=>f.field==='journey'),g=ux.grade(1000,1,grades)||'1,000';
  assert.equal(f.label,'스텔라 아카이브 기록 다시 만들기');assert.equal(f.short,`(주력 체력 ${g} → 힘 SG)`);
  assert.match(f.detail,/기록 전체를 다시 만드는/);assert.match(f.detail,/지금보다 내려가는 칸: 체력/);
  assert.equal(f.delta,swap-keep,'칩의 전투력 차이 = 통째 교체의 차이');
  assert.match(ux.todosHtml(d),/스텔라 아카이브 기록 다시 만들기 \(주력 체력 .+ → 힘 SG\)/);
  assert.equal(x.r.profile.results[KEY].power,swap,'육성 계정의 전투력 = 통째 교체한 기록의 전투력(섞은 기록이 아님)');}
 // 2) 교체가 더 나쁘면 지금 기록 유지: 주력(힘)만 낮고 나머지가 기준표보다 훨씬 높은 기록
 {const strong=[900,1250,1250,1250,1250],x=run(m,strong);
  assert(power(x.info,spec.journey)<power(x.info,strong),'시험 전제');assert(!x.changed);assert.deepEqual(x.now,strong);assert.equal(x.a,undefined,'바꿀 항목 없음');}
 // 3) 전부 낮은 기록: 기준표로 통째 교체, 합 = 기준표 합
 {const weak=[100,400,300,100,50],x=run(m,weak);
  assert(x.changed);assert.deepEqual(x.now,spec.journey);assert.equal(sum(x.now),sum(spec.journey));
  const f=U.member(x.a,x.info,growth,'op',grades,view).fields.find(f=>f.field==='journey');assert.match(f.short,/^\(주력 체력 .+ → 힘 SG\)$/);}
 // 4) 기준표 주력 칸이 이미 950 이상이면 후보가 아니다(다른 칸이 0 이어도)
 for(const j of [[950,0,0,0,0],[1250,1250,0,0,0]]){const x=run(m,j);assert(!x.changed,'주력 950 이상은 그대로: '+j);assert.deepEqual(x.now,j);}
 {const x=run(m,[949,0,0,0,0]);assert(x.changed);assert.deepEqual(x.now,spec.journey);}
 // 5) 같은 전투력이면 지금 기록(순서·값 그대로)
 {const same=spec.journey.slice(),x=run(m,same);assert(!x.changed);assert.deepEqual(x.now,same);}
 // 6) 아카이브가 아예 없으면 기준표 그대로
 {const info=account(null),r=m.overwrite(info,roster,growth,'op',{slots});assert.deepEqual(r.errors,[]);
  assert.deepEqual(Array.from(r.info.units[0].gauntlet.journey),spec.journey);assert(r.changes[KEY].changedFields.includes('journey'));}
 // 7) 플래시 포인트(Lv200 고정)도 같은 원칙
 {const x=run(m,ASHERAH,'rush'),keep=power(x.info,ASHERAH,'rush'),swap=power(x.info,spec.journey,'rush');assert.deepEqual(x.now,swap>keep?spec.journey:ASHERAH);}
 assert.equal(m.OVERWRITE_VERSION,'grown-account-v5');assert.equal(m.THRESHOLD_POLICY.archiveWhole,true);assert.equal(m.THRESHOLD_POLICY.archiveMain,950);
}
check();console.log('PASS 스텔라 아카이브 통째 교체: 제보 수치·교체가 나쁘면 유지·전부 낮으면 교체(합 = 기준표)·주력 950 이상 제외·동률 유지·칩 문구');
// 결함 주입: 되돌리면 실패해야 한다
const rep=(a,b)=>{assert(source.includes(a),'주입 대상 없음: '+a);return source.replace(a,b)};
const KEEP="if(!(power(u)>power(kept)))u.gauntlet.journey=clone(old.gauntlet.journey);";
const mutants={
 '칸별 max 섞기(옛 동작)':[rep(KEEP,"u.gauntlet.journey=u.gauntlet.journey.map((v,i)=>Math.max(v,old.gauntlet.journey[i]||0));"),U],
 '언제나 기준표로 교체':[rep(KEEP,""),U],
 '언제나 지금 기록 유지':[rep(KEEP,"u.gauntlet.journey=clone(old.gauntlet.journey);"),U],
 '동률이면 교체':[rep("if(!(power(u)>power(kept)))","if(!(power(u)>=power(kept)))"),U],
 '주력 문턱 없이 언제나 후보':[rep("(old.gauntlet.journey?.[main]||0)<THRESHOLD_POLICY.archiveMain","true"),U],
 '어느 칸이든 950 이상이면 후보 아님(뺀 규칙)':[rep("(old.gauntlet.journey?.[main]||0)<THRESHOLD_POLICY.archiveMain","!old.gauntlet.journey.some(v=>v>=THRESHOLD_POLICY.archiveMain)"),U],
 '칩에 지금 주력을 안 보임':[source,load(fs.readFileSync(require.resolve('../ux_ui'),'utf8').replace("mb==null?'없음':names[mb]+' '+g(b,mb)","'없음'"))],
 '칩 이름이 옛 «스텔라 아카이브»':[source,load(fs.readFileSync(require.resolve('../ux_ui'),'utf8').replace("f==='journey'?'스텔라 아카이브 기록 다시 만들기':labels[f]","labels[f]"))]};
for(const [name,[code,ux]] of Object.entries(mutants)){let caught=false;try{check(code===source?M:load(code),ux)}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e}
 assert(caught,'결함 주입이 통과해 버림: '+name);console.log('MUTATION caught:',name)}
console.log('ALL OK archive whole record; '+Object.keys(mutants).length+' mutations');
