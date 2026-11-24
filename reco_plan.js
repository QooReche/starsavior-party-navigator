// 자동 추천 «전체 진행»·남은 시간(11/24). DOM·화면 상태를 모르는 순수 계산 — 단계 목록은 화면이 지금 상태에서 다시 만들어 넘긴다(party_template.html recoPlanStages).
// 왜 새로 뒀나: 옛 남은 시간은 단계마다 따로(예선 scrEta·본선 eta) 셌고 현장 재조사는 아예 안 셌다 — 38-36 실측(작업자 8, 총 190초)에서
//  예선 중 «약 20~30초»(실제 160~186초), 54초에 «곧 끝남» 뒤 136초를 더 돌았다. 여기서는 끝날 때까지의 모든 단계를 한 번에 센다.
// 시간 모형: 한 단계 = 물결 수 × 작업 하나의 판 수 × 판 속도. 물결 = ceil(메시지 수 ÷ 쓰는 작업자 수), 메시지 = ceil(작업 ÷ 묶음 크기).
//  판 속도(작업자 하나가 한 판에 쓰는 ms)는 끝난 단계의 실제 시간으로 배우고(판 수 가중 평균), 진행 중 단계는 한 물결이 끝난 뒤의 처리량으로 고친다.
//  종류마다 따로 배운다: run = 본선·재조사(100판·20판), pre = 예선(8·24판 이어 돌리기 — 같은 팀을 이어 돌려 판이 가볍다, 실측 약 0.7배),
//  scan = 1판 훑기(팀마다 붙는 고정비가 큼). 단계 사이 틈(화면 다시 계산·작업 준비)도 배운다.
//  모르는 앞일: 할지 안 할지 모르는 단계는 확률 p 만큼만 센다(재조사를 할지 = 본선 전 짐작). 재조사 안의 200판 이어 확인·재측정은 늘 센다(p 1):
//  11/24 실측(작업자 2, 38-36)에서 둘 다 돌았고 반만 세면 약 70초 모자라 «곧 끝남» 뒤에도 오래 돎 — 건너뛰면 일찍 끝나는 쪽이 낫다.
//  늘어난 계획은 숨기지 않는다(단조 감소 강제 없음).
// 표시: 전체 막대 = 경과 ÷ (경과 + 남은 시간), 뒤로 가지 않게 하고 실제로 끝나기 전에는 99%에서 멈춤. 남은 시간 글자는 흔들리지 않게 완화하고 5·10초 단위로.
(function(root){
  'use strict';
  const DEF={run:200,pre:140,scan:50,gap:2000};   // 처음 쓰는 기기의 가정(ms): 판 하나(본선·예선)·1판 훑기 팀 하나(작업자 8개 10,626팀 40~75초, docs/fullscreen_measure_1121.md)·단계 사이 틈
  const KINDS=['run','pre','scan'],kindOf=s=>KINDS.includes(s.kind)?s.kind:'run';
  const waves=(jobs,chunk,W)=>{const msgs=Math.ceil(Math.max(0,jobs)/Math.max(1,chunk||1));return msgs?Math.ceil(msgs/Math.max(1,Math.min(W,msgs))):0;};
  // 단계 하나의 예상 시간(ms) — 남은 작업이 아니라 단계 전체
  const stageMs=(s,W,rate)=>waves(s.jobs,s.chunk,W)*Math.max(1,s.chunk||1)*s.runs*rate;
  const rateOf=(s,r)=>r[kindOf(s)]??r.run;
  // 남은 시간(순수). stages = [{id,step,jobs,done,runs,chunk,kind,p,at}] (p = 아직 시작 안 한 단계가 실제로 돌 확률, 기본 1) (at = 이 단계를 처음 본 시각, 진행 중 단계만 의미 있음)
  // env = {workers, rate:{run,pre,scan}, gap, now}. 반환 {remain(ms), cur(진행 중 단계 번호, 없으면 -1)}
  function remain(stages,env){
    const W=Math.max(1,env.workers||1),now=env.now;let ms=0,cur=-1,after=0;
    stages.forEach((s,i)=>{if(s.done>=s.jobs)return;const rate=rateOf(s,env.rate),total=stageMs(s,W,rate);
      if(cur<0){cur=i;const one=Math.max(1,s.chunk||1)*s.runs*rate,left=s.at!=null?total-(now-s.at):total;
        ms+=Math.max(left,s.done<s.jobs?one*0.15:0);}
      else{const p=s.p??1;ms+=total*p;after+=p;}});
    return {remain:ms+after*(env.gap||0),cur};
  }
  // 글자: 5초 단위(1분 미만)·10초 단위(그 위, durText 가 맡음)
  function etaText(ms,durText){
    if(ms==null)return '남은 시간 계산 중';if(ms<5000)return '곧 끝남';
    return '완료까지 약 '+(ms<60000?Math.ceil(ms/5000)*5+'초':durText(ms));
  }
  // 한 번의 자동 추천(같은 key) 동안 쓰는 상태: 배운 속도·단계를 처음 본 시각·경과·표시값
  function tracker(prior={}){
    const learn={gap:prior.gap||null,w:{}};for(const k of KINDS){learn[k]=prior[k]||null;learn.w[k]=prior[k]?300:0;}
    let key=null,seen={},elapsed=0,last=0,shown=null,shownAt=0,frac=0,prevEnd=0;
    function reset(k){key=k;seen={};elapsed=0;last=0;shown=null;shownAt=0;frac=0;prevEnd=0;}
    function teach(kind,ms,runs){if(!(ms>0&&runs>0))return;const r=ms/runs,w=learn.w[kind];
      learn[kind]=learn[kind]?(learn[kind]*w+r*runs)/(w+runs):r;learn.w[kind]=Math.min(w+runs,20000);}
    // stages 는 지금 상태에서 만든 전체 목록. o = {key, workers, busy, loading, now, fallback:{run,scan}}
    function update(stages,o){
      const now=o.now;if(o.key!==key)reset(o.key);
      if(!o.busy||!stages){last=0;return null;}
      if(last)elapsed+=Math.min(now-last,5000);last=now;
      const W=Math.max(1,o.workers||1);
      // 진행 중 단계(앞에서 첫 번째로 안 끝난 단계)에만 시작 시각을 달고, 끝난 단계는 실제 시간으로 속도를 배움(한 번만).
      //  뒤 단계에 미리 시각을 달면 시작 전 기다린 시간까지 그 단계 시간으로 쳐서 속도가 몇 배로 부풂(11/24 실측: «약 12분»)
      const first=stages.find(s=>s.done<s.jobs);
      // 목록에서 사라진 진행 단계도 끝난 것으로 배움: 예선은 끝나는 순간 단계들이 «완료» 칸 하나(id 다름)로 바뀌어
      //  done>=jobs 로 끝을 볼 기회가 없음 → pre 속도를 한 번도 못 배웠음(11/24 실측 learned.pre=null). 사라지기 직전 모양(m.s)으로 판 수를 셈
      const ids=new Set(stages.map(s=>s.id));
      for(const id in seen){const m=seen[id];if(ids.has(id)||m.at==null||m.end!=null||!m.s)continue;
        m.end=now;prevEnd=now;teach(kindOf(m.s),now-m.at,waves(m.s.jobs,m.s.chunk,W)*Math.max(1,m.s.chunk||1)*m.s.runs);}
      for(const s of stages){const m=seen[s.id]||(seen[s.id]={});m.s={kind:s.kind,jobs:s.jobs,chunk:s.chunk,runs:s.runs};
        if(m.at==null&&s===first&&!o.loading){m.at=now;if(prevEnd&&learn.gap!=null)learn.gap=learn.gap*0.6+Math.min(now-prevEnd,15000)*0.4;else if(prevEnd)learn.gap=Math.min(now-prevEnd,15000);}
        if(m.at!=null&&m.end==null&&s.done>=s.jobs){m.end=now;prevEnd=now;teach(kindOf(s),now-m.at,waves(s.jobs,s.chunk,W)*Math.max(1,s.chunk||1)*s.runs);}
        s.at=m.at;}
      // 진행 중 단계: 한 물결이 끝났으면 그 처리량으로 이번 단계 속도를 고침
      const live=first,rate={};for(const k of KINDS)rate[k]=learn[k]||o.fallback?.[k]||DEF[k];
      //  (작업이 끝난 그 순간에만 잼 — 물결 사이에는 끝나는 작업이 없어 처리량이 실제보다 낮아 보임)
      if(live&&live.at!=null){const m=seen[live.id],w=Math.min(W,Math.ceil(live.jobs/Math.max(1,live.chunk||1)));
        if(live.done!==m.rd){m.rd=live.done;m.r=live.done>=w*Math.max(1,live.chunk||1)?(now-live.at)*w/(live.done*live.runs):null;}
        const k=kindOf(live);if(m.r)rate[k]=learn[k]?(rate[k]+m.r)/2:m.r;}
      const steps=[...new Set(stages.map(s=>s.step))],curStage=live||null,step=curStage?steps.indexOf(curStage.step):steps.length-1;
      if(o.loading||!live)return {steps,step,remain:null,frac,text:o.loading?'계산 엔진 준비 중':'마무리 중'};
      const target=remain(stages,{workers:W,rate,gap:learn.gap??DEF.gap,now}).remain;
      // 완화: 지난 표시값을 흐른 시간만큼 줄인 값과 새 추정이 15%·5초 안이면 그대로 흘려보내고, 아니면 35%만 다가감
      if(shown==null)shown=target;else{const d=Math.max(0,shown-(now-shownAt));shown=Math.abs(target-d)<=Math.max(5000,d*0.15)?d:d+(target-d)*0.35;}
      shownAt=now;
      frac=Math.max(frac,Math.min(0.99,elapsed/Math.max(1,elapsed+shown)));
      return {steps,step,remain:shown,frac,text:null};
    }
    return {update,reset,learned:()=>({run:learn.run,pre:learn.pre,scan:learn.scan,gap:learn.gap})};
  }
  const api={DEF,waves,stageMs,remain,etaText,tracker};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.RecoPlan=api;
})(typeof globalThis!=='undefined'?globalThis:this);
