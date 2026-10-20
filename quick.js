// 빠른 계산(재설계 v1 1단계) — battlesim/quick.py 를 그대로 옮긴 것. 둘을 같이 고친다(tests/quick_test.py 가 같은 입력·같은 결과를 대조).
// 재료 = data/quick.json(tools/build_quick_data.py), 계수 = quick.json params(tools/calibrate_quick.py).
(function(g){
 const MUL=1.06,MAX_ROUNDS=50,SAFE=0.5;
 const dr=d=>d>0?d/(d+3000.0):0.0;
 function penMult(pen,ratio){const r=Math.floor(ratio*10000);
  for(const [lo,hi,a,e] of pen)if(lo<=r&&r<hi)return [a/10000,e/10000];
  if(r>=9000)return [1.0,1.0];return [pen[0][2]/10000,pen[0][3]/10000]}
 function evaluate(keys,stage,sv,pen,params,growth,power,usePen){
  const p=Object.assign({A:1.0,B:1.0,H:0.0},params||{});growth=growth==null?1.0:growth;usePen=usePen!==false;
  const units=keys.map(k=>sv[k]);
  if(units.some(u=>u==null)||!stage||!stage.w||!stage.w.length)return {ok:false};
  let ref=0;for(const u of units)ref+=u[5];ref*=MUL;
  const bp=stage.bp||ref;const P=power?power:bp*growth;const k=P/ref;const ratio=bp?P/bp:1.0;
  const [pa,pe]=usePen?penMult(pen,ratio):[1.0,1.0];
  let hpMax=0;for(const u of units)hpMax+=u[2];hpMax*=k;
  let dsum=0;for(const u of units)dsum+=u[3];const teamDr=dr(dsum/units.length*k);
  const sOut=units.map(u=>u[6]*k*u[4]/100*p.A*pa);
  const xOut=units.map(u=>Math.max(0.0,(u[7]-u[6])/2)*k*u[4]/100*p.A*pa);
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
    hp-=dmg*1.85*(1-teamDr)*p.B*pe;
    if(hp<=0)return {ok:true,clear:false,rounds:rnd,left:0.0,k,power:P,ratio,why:"wipe"};
    hp=Math.min(hpMax,hp+heal)}}
  return {ok:true,clear:true,rounds:rnd,left:hp/hpMax,k,power:P,ratio,why:""}}
 function verdict(r){if(!r.ok)return "na";if(!r.clear)return "hard";return r.left>=SAFE?"safe":"tight"}
 // 육성이 늘면 집중 대상 순서가 바뀌어 결과가 단조롭지 않을 수 있어 이분 탐색 대신 사다리에서 «처음 성공»을 찾는다(quick.py 와 같게)
 const LADDER=[0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.15,1.3,1.5,1.75,2.0,2.5,3.0,3.5,4.0],FINE=10;
 const okOf=want=>want==="safe"?(r=>verdict(r)==="safe"):(r=>r.ok&&r.clear);
 function ladderStep(keys,stage,sv,pen,params,want,upto){want=want||"safe";const ok=okOf(want);
  const last=upto==null?LADDER.length-1:Math.min(upto,LADDER.length-1);
  for(let i=0;i<=last;i++)if(ok(evaluate(keys,stage,sv,pen,params,LADDER[i])))return i;
  return null}
 function needGrowth(keys,stage,sv,pen,params,want,step){want=want||"safe";const ok=okOf(want);
  const i=step==null?ladderStep(keys,stage,sv,pen,params,want):step;
  if(i==null)return null;if(i===0)return LADDER[0];
  const a=LADDER[i-1],b=LADDER[i];
  for(let j=1;j<FINE;j++){const g=a+(b-a)*j/FINE;if(ok(evaluate(keys,stage,sv,pen,params,g)))return g}
  return b}
 const Q={MUL,SAFE,LADDER,evaluate,verdict,ladderStep,needGrowth,penMult};
 if(typeof module!=="undefined"&&module.exports)module.exports=Q;else g.Quick=Q;
})(this);
