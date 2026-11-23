// 자동 추천 끝의 자리·리더 비교(11/23): 바꿀지 판정(recoBetter/recoDecide)과 파이프라인 순서.
const assert=require('assert');
const P=require('../party_placement.js');
const Pipe=require('../recommend_pipeline.js');

// 판별 결과: 구간 [lo,hi) 판은 클리어(진행도 1), 나머지는 진행도 base. clear 는 progs 에서 셈(실제 웹 요약과 같은 관계)
const W=(lo,hi,base=0.6,n=200,t60)=>{const progs=Array.from({length:n},(_,i)=>i>=lo&&i<hi?1:base);
  return {clear:(hi-lo)/n,prog:progs.reduce((a,b)=>a+b,0)/n,progs,n,...(t60!=null?{t60}:{})};};
const P2=progs=>({clear:progs.filter(x=>x>=1).length/progs.length,prog:progs.reduce((a,b)=>a+b,0)/progs.length,progs,n:progs.length});

// 1) 운 범위 차이(+0.5%p, 200판 중 1판)는 바꾸지 않는다
assert.equal(P.recoBetter(W(0,101),W(0,100)),false);
// 1-1) +3%p 인데 서로 다른 판에서 이기고 진 것(짝 차이 흔들림 큼) → 안 바꿈. 여유폭(z)을 거의 없애면 바뀜(여유폭이 실제로 작동)
{const a=W(0,106),b=W(50,150);assert.equal(P.recoBetter(a,b),false);assert.equal(P.recoBetter(a,b,0.1),true);}
// 2) 클리어율이 확실히 높으면 바꾼다
assert.equal(P.recoBetter(W(0,160),W(0,100)),true);
// 2-1) 짝 비교: 같은 판에서 이기고 +6%p 만 더 이기면(나머지 판 결과 같음) 독립 표본식으로는 못 잡지만 짝 비교로 잡는다
{const a=W(0,112),b=W(0,100);assert.equal(P.recoBetter(a,b),true);
 const ind={...a,progs:undefined},inb={...b,progs:undefined};assert.equal(P.recoBetter(ind,inb),false,'판별 값이 없으면 독립 표본식(보수적)');}
// 3) 목표 지표가 조금이라도 나쁘면 진행도가 좋아도 바꾸지 않는다
assert.equal(P.recoBetter(W(0,98,0.95),W(0,100,0.5)),false);
// 4) 둘 다 클리어 0%: 짝 진행도 차이가 확실하면 바꾼다(45-36 리더 사례 +10점)
{const pa=Array.from({length:200},(_,i)=>0.36+(i%5)*0.01),pb=Array.from({length:200},(_,i)=>0.26+(i%7)*0.01);
 assert.equal(P.recoBetter(P2(pa),P2(pb)),true);
 // 차이가 1%p 이하면 바꾸지 않는다
 assert.equal(P.recoBetter(P2(pb.map(x=>x+0.005)),P2(pb)),false);}
// 5) 둘 다 100% 클리어면 동률 → 규칙 유지
assert.equal(P.recoBetter(W(0,200),W(0,200)),false);
// 6) 3별 목표(t60)가 첫 기준(판별 값이 없어 독립 표본식)
{const a=W(0,180,0.6,200,0.7),b=W(0,190,0.6,200,0.4);assert.equal(P.recoBetter(a,b),true);assert.equal(P.recoBetter(b,a),false);}
// 7) recoDecide: 규칙 자리가 1등이 아니어도 여유폭을 못 넘으면 규칙 자리
{const finals=[{key:'x',p:1},{key:'y',p:2},{key:'r',p:0,rule:true}];
 const r={x:W(0,104),y:W(0,80),r:W(0,100)};
 assert.equal(P.recoDecide(finals,r).key,'r');
 r.x=W(0,150);assert.equal(P.recoDecide(finals,r).key,'x');
 assert.throws(()=>P.recoDecide([{key:'x'}],{x:r.x}),/규칙 자리/);
 // recoStop(1단계): 1등이 규칙 자리면 멈춤, 약한 근거도 없으면 멈춤, 큰 차이면 계속
 assert.equal(P.recoStop(finals,{x:W(0,90),y:W(0,80),r:W(0,100)}),true);
 assert.equal(P.recoStop(finals,{x:W(0,101),y:W(0,80),r:W(0,100)}),true);
 assert.equal(P.recoStop(finals,{x:W(0,150),y:W(0,80),r:W(0,100)}),false);}

// 8) 파이프라인: final → arrange → (plan) → final 순서, arrange 없으면 종전과 같음
(async()=>{
  for(const withArrange of [false,true]){
    const log=[],box={all:[1,2,3],rows:[{}],total:1};
    const env={parties:1,screened:false,live:()=>true,plan:()=>box,screenState:()=>({done:true}),screen:async()=>{},
      more:()=>{},result:()=>({clear:1}),goal:r=>r.clear,first:()=>'ok',
      final:async()=>{log.push('final');}};
    if(withArrange)env.arrange=async()=>{log.push('arrange');};
    assert.equal(await Pipe.recommendation(env),'ok');
    assert.deepEqual(log,withArrange?['final','arrange','final']:['final']);
  }
  // 9) 공통 race: 규칙 자리(incumbent)는 예선 꼴찌여도 결선에 들어가고, 결선은 같은 시드(seed+1)·같은 판 수, decide 가 고른다
  {const calls=[],jobs=['a','b','c','d','r'].map(k=>({key:k,p:k})),inc={key:'r',p:'r',rule:true};
   const score={a:.9,b:.8,c:.7,d:.6,r:.1},fin={a:W(0,104),b:W(0,80),c:W(0,60),r:W(0,100)};
   const run=async(js,n,seed)=>{calls.push([js.map(j=>j.key),n,seed]);return Object.fromEntries(js.map(j=>[j.key,n===20?W(0,Math.round(score[j.key]*20),.5,20):fin[j.key]]));};
   const out=await P.race({jobs,run,compare:P.recoCompare,valid:r=>Number.isFinite(r?.clear),runs:200,screenRuns:20,keep:3,seed:7001,incumbent:inc,decide:P.recoDecide});
   assert.deepEqual(calls,[[['a','b','c','d','r'],20,7001],[['a','b','c','r'],200,7002]]);
   assert.equal(out.pick.key,'r','+2%p 는 여유폭 안 → 규칙 자리 유지');
   fin.a=W(0,160);assert.equal((await P.race({jobs,run,compare:P.recoCompare,valid:r=>Number.isFinite(r?.clear),runs:200,screenRuns:20,keep:3,seed:7001,incumbent:inc,decide:P.recoDecide})).pick.key,'a');
   // 옵션 없이 부르면 종전 race 와 같다(결선 = 예선 상위 keep 개, pick = 결선 1등)
   calls.length=0;const old=await P.race({jobs,run,compare:P.recoCompare,valid:r=>Number.isFinite(r?.clear),runs:200,screenRuns:20,keep:2,seed:3});
   assert.deepEqual(calls[1],[['a','b'],200,4]);assert.equal(old.pick.key,'a');}
  // 10) 결선 2단계: 1단계(100판)에서 멈춘 팀은 이어 돌리지 않고 규칙 자리, 계속하는 팀만 같은 시드로 이어서(prior) 200판
  {const calls=[],mk=k=>({key:k,p:k});
   const g1={jobs:['a1','b1','r1'].map(mk),incumbent:{key:'r1',p:'r1',rule:true}},g2={jobs:['a2','b2','r2'].map(mk),incumbent:{key:'r2',p:'r2',rule:true}};
   const at={100:{a1:W(0,50,.6,100),b1:W(0,40,.6,100),r1:W(0,50,.6,100),a2:W(0,80,.6,100),b2:W(0,40,.6,100),r2:W(0,50,.6,100)},
             200:{a2:W(0,160),b2:W(0,80),r2:W(0,100)}};
   const run=async(js,n,seed,prior)=>{calls.push([js.map(j=>j.key),n,seed,!!prior]);
     return Object.fromEntries(js.map(j=>[j.key,n===20?W(0,10,.5,20):prior?at[200][j.key]:at[100][j.key]]));};
   const out=await P.raceMany({groups:[g1,g2],run,compare:P.recoCompare,valid:r=>Number.isFinite(r?.clear),runs:200,screenRuns:20,keep:2,seed:7001,
     decide:P.recoDecide,checkRuns:100,stop:P.recoStop});
   assert.deepEqual(calls.map(c=>[c[0].length,c[1],c[2],c[3]]),[[6,20,7001,false],[6,100,7002,false],[3,100,7002,true]]);
   assert.deepEqual(calls[2][0].sort(),['a2','b2','r2']);
   assert.equal(out[0].stopped,true);assert.equal(out[0].pick.key,'r1');
   assert.equal(out[1].stopped,false);assert.equal(out[1].pick.key,'a2');}
  console.log('reco_arrange_test ok');
})().catch(e=>{console.error(e);process.exit(1);});
