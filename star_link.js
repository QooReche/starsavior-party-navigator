// Bounded, local slot exchange search. Content metrics are never added together.
(function(root){
  'use strict';
  const G=typeof module!=='undefined'&&module.exports?require('./growth_guide'):root.GrowthGuide;
  const LIMITS=Object.freeze({maxRuns:12000,maxMs:120000,maxSwaps:3,maxCandidates:8,maxPairs:24});
  function availability(info){
    const l=info?.star_link;
    if(!l||!Array.isArray(l.slots)||!Array.isArray(l.source)||!Number.isInteger(l.level)||l.level<1||
      info.units.some(u=>!Number.isInteger(u.level)||u.level<1))return '다시 불러오기 필요';
    const ids=l.slots.map(s=>s.id).filter(Boolean),owned=new Set(info.units.map(u=>u.id));
    if(ids.some(id=>!owned.has(id)||l.source.includes(id))||new Set(ids).size!==ids.length)return '확인 부족 · 슬롯 자료 확인 필요';
    return '';
  }
  function withSlots(info,ids){return {...info,star_link:{...info.star_link,
    slots:ids.map((id,i)=>({index:info.star_link.slots[i]?.index??i,id}))}};}
  function exchangeCandidates(info,slots,candidates,{keep=[],defer=[],emptyFirst=false,maxCandidates=LIMITS.maxCandidates}={}){
    const incoming=candidates.filter(id=>!slots.includes(id)&&!info.star_link.source.includes(id)).slice(0,maxCandidates);
    const outgoing=[...new Set(slots)].filter(id=>!keep.includes(id));
    if(emptyFirst)outgoing.sort((a,b)=>(a===0?-1:defer.includes(a)?1:0)-(b===0?-1:defer.includes(b)?1:0));
    return {incoming,outgoing};
  }
  function exchange(slots,add,remove){const next=slots.slice();next[next.indexOf(remove)]=add;return next;}
  // A registration plan, not a claim about the combat effect of removing a member.
  // Share the exact exchange candidates/slot indexing with the measured search.
  function growthPlan(info,required,team=[],current=[]){
    const unavailable=availability(info);if(unavailable)return {unavailable,swaps:[]};
    const initial=info.star_link.slots.map(s=>s.id),source=info.star_link.source;
    const incoming=[...new Set(required)].filter(id=>!source.includes(id)&&!initial.includes(id));
    const empty=initial.filter(id=>!id).length,shortage=Math.max(0,incoming.length-empty);
    if(!shortage)return {initial,slots:initial,empty,shortage,required:incoming,swaps:[],register:incoming,remaining:[],limited:false,pairs:0,runs:0};
    let slots=initial.slice(),pairs=0;const swaps=[];
    for(const add of incoming.slice(0,LIMITS.maxCandidates)){
      if(swaps.length>=LIMITS.maxSwaps||pairs>=LIMITS.maxPairs)break;
      const candidates=exchangeCandidates(info,slots,[add],{keep:[...team,...incoming],defer:current,emptyFirst:true});
      if(!candidates.incoming.length||!candidates.outgoing.length)continue;
      const remove=candidates.outgoing[0];pairs++;
      slots=exchange(slots,add,remove);swaps.push({in:add,out:remove,deferred:!!remove&&current.includes(remove)});
    }
    return {initial,slots,empty,shortage,required:incoming,swaps,pairs,runs:0,
      remaining:incoming.filter(id=>!slots.includes(id)),limited:incoming.some(id=>!slots.includes(id))};
  }
  function differences(metrics,base,contexts){return contexts.map(c=>({content:c.id,
    ...(metrics[c.id]&&base[c.id]?G.compare(metrics[c.id],base[c.id]):{delta:null,ci:null,confirmed:false})}));}
  const count=rows=>new Set(rows.filter(r=>r.confirmed).map(r=>r.content.split('/')[0])).size;
  function rank(a,b){const n=count(b)-count(a);if(n)return n;
    // Compare each content only against that same content, in stable ID order.
    const aa=new Map(a.map(r=>[r.content,r])),bb=new Map(b.map(r=>[r.content,r]));
    for(const id of [...new Set([...aa.keys(),...bb.keys()])].sort()){
      const d=(bb.get(id)?.delta??-Infinity)-(aa.get(id)?.delta??-Infinity);if(d)return d;}
    return 0;
  }
  async function search({info,contexts,candidates,evaluate,limits={},alive=()=>true,now=()=>Date.now(),progress=()=>{}}){
    const L={...LIMITS,...limits},start=now(),initial=info.star_link.slots.map(s=>s.id),cache=new Map();
    let runs=0,pairs=0,limited=candidates.length>L.maxCandidates,slots=initial.slice();
    const swaps=[],diagnostics=[];
    const within=()=>alive()&&now()-start<L.maxMs&&runs<L.maxRuns;
    const key=ids=>ids.slice().sort((a,b)=>a-b).join(',');
    async function assess(ids,focus,reference=slots){const sig=key(reference)+'>'+key(ids)+'|'+key(focus);if(cache.has(sig))return cache.get(sig);
      const metrics={},controls={};
      for(const c of contexts){if(!within()){limited=true;break;}
        const r=await evaluate({info:withSlots(info,ids),referenceInfo:withSlots(info,reference),context:c,focus,remaining:L.maxRuns-runs,deadline:start+L.maxMs});
        runs+=r?.runs||0;if(r?.metric)metrics[c.id]=r.metric;
        if(r?.paired)controls[c.id]=r.controlMetric||null;
        progress({runs,pairs,swaps:swaps.length});
      }
      const result={metrics,controls:Object.keys(controls).length?controls:null};cache.set(sig,result);return result;
    }
    let baseline=(await assess(slots,[])).metrics,current=baseline,first=null;
    if(Object.keys(baseline).length!==contexts.length||!contexts.length)limited=true;
    for(let step=0;step<L.maxSwaps&&within()&&contexts.length;step++){
      const {incoming,outgoing}=exchangeCandidates(info,slots,candidates,{maxCandidates:L.maxCandidates});
      let best=null;
      // Verify real two-unit changes; adding and removing independently is not additive.
      exchanges:for(const add of incoming)for(const remove of outgoing){
        if(!within()||pairs>=L.maxPairs){limited=true;break exchanges;}
        const next=exchange(slots,add,remove);pairs++;
        const {metrics,controls}=await assess(next,[add,remove].filter(Boolean)),rows=differences(metrics,controls||current,contexts);
        // A missing result or a confirmed regression cannot become a recommendation.
        const eligible=rows.every(r=>r.delta!=null&&r.ci[1]>=0)&&count(rows)>0;
        if(eligible&&(!best||rank(rows,best.rows)<0))best={in:add,out:remove,rows,metrics,baseline:controls||current,slots:next};
        // Diagnostics never take the budget needed for the first real exchange.
        // Keep at least half the run budget available to further pair validation.
        if(runs<L.maxRuns/2)for(const [kind,id] of [['in',add],['out',remove]]){
          if(!id || (kind==='in'&&!slots.includes(0)))continue;
          if(diagnostics.some(d=>d.step===step&&d.kind===kind&&d.id===id))continue;
          if(!within()||runs>=L.maxRuns/2)break;
          const ids=slots.slice();ids[slots.indexOf(kind==='in'?0:id)]=kind==='in'?id:0;
          const d=await assess(ids,id?[id]:[]);
          diagnostics.push({step,kind,id,rows:differences(d.metrics,d.controls||current,contexts)});
        }
      }
      if(!best)break;
      swaps.push({in:best.in,out:best.out,rows:best.rows});slots=best.slots;current=best.metrics;
      if(!first){first=best;baseline=best.baseline;}
      if(step===L.maxSwaps-1)limited=true;
    }
    // Several locally good exchanges still need a direct comparison with today's slots.
    // If the final paired comparison is incomplete, retain the first verified exchange.
    if(swaps.length>1){const final=within()?await assess(slots,swaps.flatMap(s=>[s.in,s.out]).filter(Boolean),initial):null;
      const rows=final&&differences(final.metrics,final.controls||baseline,contexts);
      if(rows&&rows.every(r=>r.delta!=null&&r.ci[1]>=0)&&count(rows)>0){current=final.metrics;baseline=final.controls||baseline;}
      else{limited=true;slots=first.slots;current=first.metrics;baseline=first.baseline;swaps.splice(1);}}
    // Unmeasured candidate diagnostics stay explicitly unknown.
    for(const [kind,ids] of [['in',candidates.filter(id=>!initial.includes(id)&&!info.star_link.source.includes(id))],['out',initial]])
      for(const id of new Set(ids.filter(Boolean)))if(!diagnostics.some(d=>d.kind===kind&&d.id===id))diagnostics.push({step:0,kind,id,
        note:kind==='in'&&!initial.includes(0)?'교환 필요':'',rows:differences({},baseline,contexts)});
    if(!within())limited=true;
    if(!alive())return null;
    return {initial,slots,swaps,diagnostics,baseline,metrics:current,rows:differences(current,baseline,contexts),
      runs,ms:now()-start,pairs,limited,scope:{contexts:contexts.length,candidates:Math.min(candidates.length,L.maxCandidates),...L}};
  }
  const api={LIMITS,availability,withSlots,exchangeCandidates,exchange,growthPlan,differences,count,rank,search};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.StarLink=api;
})(typeof window!=='undefined'?window:globalThis);
