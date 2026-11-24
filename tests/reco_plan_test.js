// node tests/reco_plan_test.js [--mutations] — 자동 추천 전체 진행·남은 시간(reco_plan.js): 물결 시간 모형·단계 순서·배우는 속도·표시 완화·막대.
// 기준 = 38-36 실측(11/24, 작업자 8, 총 190초: 예선1 16·예선2 10·본선 22·재조사 훑기 35·100판 39·200판 39·재측정 19초).
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const SRC=fs.readFileSync(path.join(__dirname,'..','reco_plan.js'),'utf8');
const load=src=>{const c={module:{exports:{}}};vm.runInNewContext(src,c);return c.module.exports;};
const dur=ms=>{const s=Math.ceil(ms/1000);if(s<60)return s+'초';const m=Math.floor(s/60),r=Math.round((s%60)/10)*10;return r>=60?(m+1)+'분':m+'분'+(r?' '+r+'초':'');};
function check(P){
  const W=8,rate={run:195,pre:135,scan:600};
  const plan=()=>[{id:'pre1',step:'후보 거르기',jobs:120,done:0,runs:8,chunk:1,kind:'pre'},{id:'pre2',step:'후보 거르기',jobs:20,done:0,runs:24,chunk:1,kind:'pre'},
    {id:'final',step:'상위 팀 확인',jobs:3,done:0,runs:100,chunk:1},{id:'rc1',step:'현장 재조사',jobs:72,done:0,runs:20,chunk:1},
    {id:'rc2',step:'현장 재조사',jobs:12,done:0,runs:100,chunk:1},{id:'rc3',step:'현장 재조사',jobs:12,done:0,runs:100,chunk:1},{id:'rc4',step:'현장 재조사',jobs:3,done:0,runs:100,chunk:1}];
  // 1) 물결: 12작업·작업자 8 = 2물결(39초), 3작업 = 1물결(작업자 3개만 씀), 묶음 34 × 10,626팀
  assert.equal(P.waves(12,1,W),2,'12작업 2물결');assert.equal(P.waves(3,1,W),1);assert.equal(P.waves(10626,34,W),40);
  assert.equal(P.stageMs({jobs:12,chunk:1,runs:100},W,195),39000);
  // 2) 시작 시점 전체 예상이 실측 190초의 ±15% 안(옛 표시는 «약 28초»)
  const r0=P.remain(plan(),{workers:W,rate,gap:2000,now:0});assert.equal(r0.cur,0);
  assert(r0.remain>190000*0.85&&r0.remain<190000*1.15,'시작 예상 '+r0.remain);
  // 3) 재조사가 남아 있으면 본선 끝에 «곧 끝남»이 아님(옛 표시: 54초에 «곧 끝남», 실제 136초 남음)
  const s3=plan();s3[0].done=120;s3[1].done=20;s3[2].done=3;
  const r3=P.remain(s3,{workers:W,rate,gap:2000,now:0});assert.equal(r3.cur,3);assert(r3.remain>100000,'재조사 몫 '+r3.remain);
  // 3-1) 할지 모르는 단계(p)는 그만큼만: 200판 이어 확인(39초)을 반으로
  const s31=plan();s31[5].p=0.5;assert.equal(r0.remain-P.remain(s31,{workers:W,rate,gap:2000,now:0}).remain,19500+1000,'p 0.5');
  // 4) 진행 중 단계는 흐른 시간만큼 줄고, 끝나지 않았으면 0이 되지 않음
  const s4=plan().slice(4);s4[0].at=0;const a=P.remain(s4,{workers:W,rate,gap:0,now:10000}).remain,b=P.remain(s4,{workers:W,rate,gap:0,now:60000}).remain;
  assert(a>b&&b>0,'진행 중 단계 '+a+' '+b);
  // 5) 글자: 5초 단위·곧 끝남·계산 중
  assert.equal(P.etaText(null,dur),'남은 시간 계산 중');assert.equal(P.etaText(3000,dur),'곧 끝남');assert.equal(P.etaText(41000,dur),'완료까지 약 45초');
  assert.equal(P.etaText(130000,dur),'완료까지 약 2분 10초');
  // 6) 추적: 단계를 처음 본 시각·끝난 단계로 속도를 배움(예선 pre·본선 run 따로), 막대는 뒤로 가지 않고 끝나기 전 99% 넘지 않음, 엔진 준비 중엔 시간 없음
  const t=P.tracker({}),o=(now,extra={})=>({key:'k',workers:W,busy:true,loading:false,now,fallback:{},...extra});
  let st=plan(),v=t.update(st,o(0,{loading:true}));assert.equal(v.remain,null);assert.equal(v.text,'계산 엔진 준비 중');
  v=t.update(st,o(1000));assert.equal(v.step,0);assert.equal(v.steps.length,3);const first=v.remain;assert(first>0);
  st=plan();st[0].done=120;v=t.update(st,o(17000));   // 예선1을 16초에 끝냄 → 판 속도 16000/(15물결×8판) ≈ 133ms 로 배움
  assert(Math.abs(t.learned().pre-16000/(15*8))<1,'배운 속도 '+t.learned().pre);assert.equal(t.learned().run,null,'예선 속도는 본선 속도와 따로');
  // 뒤 단계는 시작한 때부터 잼: 예선2(20작업×24판, 3물결)를 17→27초에 끝내면 10000/72 ≈ 139ms 와 섞임(처음 본 1초부터 재면 361ms)
  st=plan();st[0].done=120;v=t.update(st,o(18000));st=plan();st[0].done=120;st[1].done=20;v=t.update(st,o(28000));
  assert(t.learned().pre<150,'뒤 단계 시작 시각 '+t.learned().pre);
  let prev=v.frac;for(let now=18000;now<200000;now+=1000){st=plan();st[0].done=120;st[1].done=20;st[2].done=now>40000?3:0;v=t.update(st,o(now));
    assert(v.frac>=prev,'막대 뒤로 감');assert(v.frac<=0.99,'끝나기 전 99% 넘음');prev=v.frac;}
  // 7) 완화: 새 추정이 조금 흔들리면(±15%) 표시값은 흐른 시간만큼만 줄어듦, 크게 바뀌면 35%만 다가감
  const u=P.tracker({run:195}),base=[{id:'x',step:'s',jobs:16,done:0,runs:100,chunk:1}];
  const w1=u.update(base.map(s=>({...s})),o(0)).remain;const w2=u.update(base.map(s=>({...s})),o(1000)).remain;assert.equal(w1-w2,1000,'흐른 만큼만');
  const big=[...base.map(s=>({...s})),{id:'y',step:'t',jobs:16,done:0,runs:100,chunk:1}],w3=u.update(big,o(2000)).remain;
  assert(w3>w2-1000&&w3<w2-1000+(39000+2000)*0.36,'큰 변화는 35%만 '+w3);
  // 8) 다른 추천(key)이면 처음부터, 쉬는 동안(busy 아님)은 시간 안 셈
  assert.equal(t.update(null,o(0,{busy:false})),null);const n=t.update(plan(),o(5000,{key:'other'}));assert.equal(n.frac,0);
  // 9) 예선 단계가 끝나는 순간 «완료» 칸(id 다름)으로 바뀌어도 pre 속도를 배움(11/24 실측 learned.pre=null) — 판 하나 100ms 로 돌았다고 치면 그 값
  const q=P.tracker({}),pre=[{id:'pre1',step:'s',jobs:8,done:0,runs:10,chunk:1,kind:'pre'},{id:'final',step:'t',jobs:2,done:0,runs:100,chunk:1}];
  q.update(pre.map(s=>({...s})),o(0,{key:'q'}));
  q.update([{id:'pre',step:'s',jobs:1,done:1,runs:0,chunk:1,kind:'pre'},{...pre[1]}],o(1*10*100,{key:'q'}));   // W=8 → 8팀은 물결 1 × 10판 × 100ms
  assert.equal(Math.round(q.learned().pre),100,'사라진 예선 단계로 pre 를 배움: '+q.learned().pre);
}
check(load(SRC));
if(process.argv.includes('--mutations')){
  const muts=[
    ['물결 무시(연속 나눗셈)','return msgs?Math.ceil(msgs/Math.max(1,Math.min(W,msgs))):0;','return msgs/Math.max(1,Math.min(W,msgs));'],
    ['뒤 단계를 안 셈(재조사 누락)','else{const p=s.p??1;ms+=total*p;after+=p;}','else{after++;}'],
    ['확률 무시','else{const p=s.p??1;ms+=total*p;','else{const p=1;ms+=total*p;'],
    ['막대가 뒤로 감','frac=Math.max(frac,Math.min(0.99,','frac=(0,Math.min(0.99,'],
    ['끝나기 전 100%','Math.min(0.99,elapsed','Math.min(1,1+elapsed'],
    ['완화 없음','shown=Math.abs(target-d)<=Math.max(5000,d*0.15)?d:d+(target-d)*0.35;','shown=target;'],
    ['뒤 단계에 미리 시작 시각','if(m.at==null&&s===first&&!o.loading){','if(m.at==null&&s.done<s.jobs&&!o.loading){'],
    ['끝난 단계로 안 배움','teach(kindOf(s),now-m.at,','(()=>0)(s,now-m.at,'],
    ['사라진 단계로 안 배움','m.end=now;prevEnd=now;teach(kindOf(m.s),','m.end=now;prevEnd=now;(()=>0)(kindOf(m.s),'],
  ];
  for(const [name,a,b] of muts){assert(SRC.includes(a),'변이 자리 없음: '+name);let caught=false;try{check(load(SRC.replace(a,b)));}catch(e){caught=true;}
    assert(caught,'변이를 못 잡음: '+name);console.log('MUTATION caught: '+name);}
}
console.log('PASS reco_plan: 물결 시간·38-36 시작 예상 ±15%·재조사 몫·확률 단계·진행 중 단계·글자·속도 배우기·막대 단조·완화·다른 추천 초기화'+(process.argv.includes('--mutations')?'; 깨뜨리기 9건':''));
