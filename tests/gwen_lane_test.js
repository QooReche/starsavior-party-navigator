const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const G=require('../gwen_lane'),U=require('../ux_ui'),P=require('../gwen_policy');
function cooldown(g){const p=g.policy(()=>0);assert(p.event('put',0).speech);assert(!p.event('put',200).speech);
  assert(!p.event('put',4000).speech);assert(p.event('put',8000).speech);}
function priority(g){const p=g.policy(()=>0);p.event('work',0,{level:'work',duration:Infinity});assert.equal(p.event('put',10),null);
  assert(p.event('high',10,{level:'result',id:'one'}));assert.equal(p.event('high',11,{level:'result',id:'one'}),null);
  assert(p.event('error',11,{level:'error',duration:5000}));assert.equal(p.event('high',12,{level:'result',id:'two'}),null);}
function motion(g){const equal=(a,b)=>assert.deepEqual(JSON.parse(JSON.stringify(a)),b);for(const reduced of [true,false])for(const mobile of [true,false]){
  const r=g.travel(20,400,500,80,{run:true,reduced,mobile});assert(r.ms<=600);assert(r.x<=164);
  if(reduced)equal(r,{x:20,ms:0});else{assert.equal(r.x,mobile?92:164);assert.equal(r.ms,600);}
 }equal(g.travel(400,9999,500,80,{run:true}),{x:420,ms:1000/12});
 equal(g.travel(20,200,500,80,{quiet:true}),{x:20,ms:0});}
cooldown(G);priority(G);motion(G);
function playground(g){
 const p=g.playground(()=>.5),history=[];
 for(let i=0;i<12;i++){
  const a=p.next(i%2?600:0,600);assert.equal(a.target,i%2?0:600);
  assert(a.duration>=2000&&a.duration<=3000);assert(p.delay()>=3000&&p.delay()<=7000);
  p.next(0,600);p.next(600,600);const pose=p.pose();
  assert(!history.slice(-2).includes(pose));history.push(pose);
 }
 assert(g.playground(()=>.01).next(0,600).run);assert.equal(g.playground(()=>.01).pose(),'jump');
 assert(!p.next(0,600).run);
}
playground(G);
const silent=G.policy();silent.event('play',0,{level:'idle',candidates:['think'],silent:true});
assert(silent.event('put',100).speech,'silent playground consumed the edit speech cooldown');
for(const [kind,choices] of Object.entries(G.CHOICES))for(const key of choices)assert(U.GWEN_SCENES[key],`${kind}: ${key}`);
for(const [key,lines] of Object.entries(G.SAY)){assert(lines.length>=1&&lines.length<=4,key);for(const line of lines)assert(!/단장(?!님)/.test(line));}
const p=G.policy(()=>0),history=[];for(let i=0;i<20;i++){const a=p.pick(G.CHOICES.high);assert(!history.slice(-2).includes(a));history.push(a);}
const clicks=G.policy(()=>0);assert.equal(clicks.poke(0).art,'shy');assert.equal(clicks.poke(100).art,'sulk');assert.equal(clicks.poke(200).art,'cry');
assert.equal(clicks.poke(10199),null);assert.equal(clicks.poke(10200).art,'shy');
const q=G.policy();assert.equal(q.event('put',0,{quiet:true}),null);assert(q.event('work',0,{quiet:true,level:'work'}));
// st_reach 는 high·better 후보에 포함
assert(G.CHOICES.high.includes('st_reach'),'st_reach in high candidates');
assert(G.CHOICES.better.includes('st_reach'),'st_reach in better candidates');
assert(U.GWEN_SCENES.st_reach,'st_reach must exist in GWEN_SCENES');
// 정책 모듈(gwen_policy) 경유 배너: 하위 호환
assert.equal(G.bannerState,P.bannerState,'bannerState re-exported from policy');
assert.equal(G.bannerPicker,P.bannerPicker,'bannerPicker re-exported from policy');
assert.deepEqual(G.BANNER_COPY,P.BANNER_COPY,'BANNER_COPY re-exported from policy');
// bannerState: direct·reco 무대 모두 지원
assert.equal(P.bannerState({mode:'direct',phase:'result',count:4},false),'result');
assert.equal(P.bannerState({mode:'reco',phase:'result',count:4},false),'result');
assert.equal(P.bannerState({mode:'home',phase:'result',count:4},false),'');
// 결과 후보에 SD 변종 없음(항상 st_* 등신대)
assert(!G.CHOICES.highSD,'highSD removed — always st_*');
assert(!G.CHOICES.mediumSD,'mediumSD removed');
assert(!G.CHOICES.lowSD,'lowSD removed');
// 정책 모듈의 결과 후보 함수
for(const c of P.resultCandidates(.8,false,false))assert(U.GWEN_SCENES[c],`policy high candidate: ${c}`);
for(const c of P.resultCandidates(.3,false,false))assert(U.GWEN_SCENES[c],`policy medium candidate: ${c}`);
for(const c of P.resultCandidates(.01,false,false))assert(U.GWEN_SCENES[c],`policy low candidate: ${c}`);
for(const c of P.resultCandidates(null,true,false))assert(U.GWEN_SCENES[c],`policy better candidate: ${c}`);
assert(P.resultCandidates(.8,false,false).includes('st_reach'),'policy high includes st_reach');
assert(P.resultCandidates(null,true,false).includes('st_reach'),'policy better includes st_reach');
// 변이 검사: 고친 코드를 되돌려 시험이 실패하는지 확인
const source=fs.readFileSync(require.resolve('../gwen_lane'),'utf8');
const healthy={module:{exports:{}},require:p=>require(p.startsWith('./')?'../'+p.slice(2):p)};vm.runInNewContext(source,healthy);cooldown(healthy.module.exports);priority(healthy.module.exports);motion(healthy.module.exports);
for(const [name,from,to,check] of [
 ['cooldown','now-s.lastReaction<4000','false',g=>{const p=g.policy();p.event('put',0);p.state.lastSpeech=-Infinity;assert(!p.event('put',10).speech)}],
 ['priority','priority<s.priority','priority>s.priority',priority],
 ['reduced-motion','if(reduced||quiet||home&&mobile)','if(quiet||home&&mobile)',motion],
 ['lane-boundary','Math.min(max,target)','target',motion],
]){assert(source.includes(from),name);const c={module:{exports:{}},require:p=>require(p.startsWith('./')?'../'+p.slice(2):p)};vm.runInNewContext(source.replace(from,to),c);
 assert.throws(()=>check(c.module.exports),assert.AssertionError,name);console.log('mutation caught:',name);}
console.log('PASS lane policy: assets, speech, last two, priorities, result once, three pokes/lock, quiet, movement, st_reach, policy re-export, reco stage support; 4 mutations');
