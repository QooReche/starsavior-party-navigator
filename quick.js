// 빠른 계산(재설계 v1 1단계) — battlesim/quick.py 를 그대로 옮긴 것. 둘을 같이 고친다(tests/quick_test.py 가 같은 입력·같은 결과를 대조).
// 재료 = data/quick.json(tools/build_quick_data.py), 계수 = quick.json params(tools/calibrate_quick.py).
(function(g){
 const MUL=1.0,MAX_ROUNDS=50,SAFE=0.5;
 const dr=d=>d>0?d/(d+3000.0):0.0;
 function penMult(pen,ratio){const r=Math.floor(ratio*10000+1e-6);
  for(const [lo,hi,a,e] of pen)if(lo<=r&&r<hi)return [a/10000,e/10000];
  if(r>=9000)return [1.0,1.0];return [pen[0][2]/10000,pen[0][3]/10000]}
 // powers = {구원자 key: 전투력}(선택), scale = 모든 구원자 전투력 배수 — quick.py evaluate 와 같은 뜻
 function evaluate(keys,stage,sv,pen,params,growth,power,usePen,powers,scale){
  const p=Object.assign({A:1.0,B:1.0,H:0.0},params||{});growth=growth||1.0;usePen=usePen!==false;scale=scale==null?1.0:scale;
  const units=keys.map(k=>sv[k]);
  if(units.some(u=>u==null)||!stage||!stage.w||!stage.w.length)return {ok:false};
  let rs=0;for(const u of units)rs+=u[5];const ref=rs*MUL;
  const bp=stage.bp||ref;const base=power?power:bp*growth;
  const pi=units.map((u,i)=>((powers&&powers[keys[i]])||base*u[5]/rs)*scale);
  let P=0;for(const x of pi)P+=x;
  const ks=units.map((u,i)=>pi[i]/(u[5]*MUL));
  const k=P/ref;const ratio=bp?P/bp:1.0;
  const [pa,pe]=usePen&&!stage.np?penMult(pen,ratio):[1.0,1.0];
  let hpMax=0;units.forEach((u,i)=>{hpMax+=u[2]*ks[i]});
  let dsum=0;units.forEach((u,i)=>{dsum+=u[3]*ks[i]});const teamDr=dr(dsum/units.length);
  const sOut=units.map((u,i)=>u[6]*ks[i]*p.A*pa);
  const xOut=units.map((u,i)=>Math.max(0.0,(u[7]-u[6])/2)*ks[i]*p.A*pa);
  const healers=units.filter(u=>u[8].includes("h")||u[8].includes("s")).length;
  const heal=healers*p.H*hpMax;
  let hp=hpMax;const limit=stage.lt||MAX_ROUNDS;let rnd=0;
  for(const wave of stage.w){
   const foes=wave.map(e=>[e[0],e[1],e[2],e[3],e[4],e[5]]);
   while(foes.some(f=>f[0]>0)){
    rnd++;
    if(rnd>limit)return {ok:true,clear:false,rounds:limit,left:Math.max(0.0,hp/hpMax),k,power:P,ratio,why:"time"};
    const alive=foes.filter(f=>f[0]>0);const boss=alive.filter(f=>f[5]);
    let focus=boss.length?boss[0]:alive.reduce((m,f)=>f[0]<m[0]?f:m,alive[0]);
    for(let i=0;i<units.length;i++){
     focus[0]-=sOut[i]*(1-dr(focus[1]));
     if(xOut[i])for(const f of alive)if(f!==focus)f[0]-=xOut[i]*(1-dr(f[1]))}
    let dmg=0;for(const f of foes)if(f[0]>0)dmg+=(f[3]+f[4])*f[2]/100;
    hp-=dmg*1.85*(1-teamDr)*p.B*pe*(stage.m||1.0);
    if(hp<=0)return {ok:true,clear:false,rounds:rnd,left:0.0,k,power:P,ratio,why:"wipe"};
    hp=Math.min(hpMax,hp+heal)}}
  return {ok:true,clear:true,rounds:rnd,left:hp/hpMax,k,power:P,ratio,why:""}}
 function verdict(r){if(!r.ok)return "na";if(!r.clear)return "hard";return r.left>=SAFE?"safe":"tight"}
 // 육성이 늘면 집중 대상 순서가 바뀌어 결과가 단조롭지 않을 수 있어 이분 탐색 대신 사다리에서 «처음 성공»을 찾는다(quick.py 와 같게)
 const LADDER=[0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.15,1.3,1.5,1.75,2.0,2.5,3.0,3.5,4.0],FINE=10;
 const okOf=want=>want==="safe"?(r=>verdict(r)==="safe"):(r=>r.ok&&r.clear);
 // base = {growth, power, powers} = 지금 가정. 사다리는 그 가정에 곱하는 배수
 const ev=(keys,stage,sv,pen,params,b,x)=>evaluate(keys,stage,sv,pen,params,(b&&b.growth)||1.0,b&&b.power,true,b&&b.powers,x);
 function ladderStep(keys,stage,sv,pen,params,want,upto,base){want=want||"safe";const ok=okOf(want);
  const last=upto==null?LADDER.length-1:Math.min(upto,LADDER.length-1);
  for(let i=0;i<=last;i++)if(ok(ev(keys,stage,sv,pen,params,base,LADDER[i])))return i;
  return null}
 function needGrowth(keys,stage,sv,pen,params,want,step,base){want=want||"safe";const ok=okOf(want);
  const i=step==null?ladderStep(keys,stage,sv,pen,params,want,null,base):step;
  if(i==null)return null;if(i===0)return LADDER[0];
  const a=LADDER[i-1],b=LADDER[i];
  for(let j=1;j<FINE;j++){const g=a+(b-a)*j/FINE;if(ok(ev(keys,stage,sv,pen,params,base,g)))return g}
  return b}
 // 스테이지별 난이도 보정(sm)을 st 에 m 으로 넣는다 — quick.py merge_sm 과 같게(화면·시험 모두 이걸 쓴다)
 function mergeSm(q){for(const [ck,d] of Object.entries(q.sm||{}))for(const [sk,m] of Object.entries(d))if(q.st[ck]&&q.st[ck][sk])q.st[ck][sk].m=m;return q}
 const Q={MUL,SAFE,LADDER,evaluate,verdict,ladderStep,needGrowth,penMult,mergeSm};
 if(typeof module!=="undefined"&&module.exports)module.exports=Q;else g.Quick=Q;
})(this);
