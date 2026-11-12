const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const G=require('../growth_guide'),S=require('../star_link');
const gs=fs.readFileSync(require.resolve('../growth_guide'),'utf8'),ss=fs.readFileSync(require.resolve('../star_link'),'utf8');
const ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8'),slotUi=fs.readFileSync(require.resolve('../star_link_ui'),'utf8');
const plain=x=>JSON.parse(JSON.stringify(x));
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);return ctx.module.exports;}
function slots(s=S){
  const info={units:Array.from({length:12},(_,i)=>({id:i+1,level:1})),star_link:{level:240,source:[1],slots:[{index:8,id:2},{index:12,id:0},{index:42,id:3}]}};
  const before=JSON.stringify(info),plan=s.growthPlan(info,[4,5,1,4],[4,5],[2]);
  assert.equal(plan.shortage,1);assert.deepEqual(plain(plan.swaps),[{in:4,out:0,deferred:false},{in:5,out:3,deferred:false}]);
  assert(!plan.slots.includes(1));assert(plan.slots.includes(2),'current team is deferred');
  assert.deepEqual(s.withSlots(info,plan.slots).star_link.slots.map(s=>s.index),[8,12,42]);
  const enough=s.growthPlan(info,[4]);assert.equal(enough.shortage,0);assert.deepEqual(plain(enough.register),[4]);
  const protectedPlan=s.growthPlan(info,[4,5,6],[4,5,6],[2,3]);
  assert.equal(protectedPlan.shortage,2);assert.equal(protectedPlan.swaps[0].out,0);
  assert(protectedPlan.swaps.slice(1).every(x=>x.deferred));
  const kept=s.growthPlan(info,[4,5],[2,4,5],[3]);assert.equal(kept.swaps[1].out,3);assert(kept.swaps[1].deferred);
  const bounded=s.growthPlan(info,[4,5,6,7,8,9,10,11,12],[],[]);
  assert.equal(bounded.swaps.length,3);assert.equal(bounded.remaining.length,6);
  assert(bounded.pairs<=s.LIMITS.maxPairs&&bounded.runs<=s.LIMITS.maxRuns);
  assert(s.growthPlan({...info,star_link:null},[4]).unavailable);
  for(const blank of [0,null,undefined,'']){
    const sparse={...info,star_link:{...info.star_link,slots:[{index:8,id:2},{index:12,id:blank},{index:42,id:3}]}};
    const p=s.growthPlan(sparse,[4,5]);
    assert.equal(p.empty,1);assert.equal(p.shortage,1);
    assert.equal(p.swaps[0].out,blank,'fill every representation of an empty slot first');
    assert.equal(p.slots[1],4);assert.equal(p.swaps[1].out,2);
  }
  const large={...info,star_link:{...info.star_link,slots:[2,0,3,0,4,5].map((id,index)=>({id,index}))}};
  const capped=s.growthPlan(large,[6,7,8,9,10,11]);
  assert.equal(capped.shortage,4);assert.equal(capped.swaps.length,5,'two free registrations plus three replacements');
  assert.equal(capped.swaps.filter(x=>x.out).length,3);assert.deepEqual(plain(capped.remaining),[11]);assert(capped.limited);
  const missing=s.growthPlan(info,[99,4,99]);
  assert.deepEqual(plain(missing.required),[4]);assert.equal(missing.shortage,0);
  assert.deepEqual(plain(missing.register),[4]);assert.deepEqual(plain(missing.remaining),[]);
  const mixed=s.growthPlan(info,[99,4,5]);
  assert.equal(mixed.shortage,1);assert.deepEqual(plain(mixed.swaps.map(x=>x.in)),[4,5]);
  assert.equal(JSON.stringify(info),before);
}
function history(g=G){
  let data={};const store={get:k=>data[k],set:(k,v)=>(data[k]=plain(v),true)};
  const cond=mode=>({mode,rules:{},breaks:[{},{}]});
  const sig=(kind,mode='auto',account='test')=>g.signature({account,options:{growth:true},targets:[],preset:'test',content:[kind,'tab','stage',cond(mode)],excluded:[],engine:'e',data:'d'});
  let at=0;
  const entry=(content,keys,delta,mode='auto',source='owned')=>g.grownSummary({content,signature:sig(content.split('/')[0],mode),account:'test',version:'grown-v',at:++at,
    members:keys.map(key=>({key,source,changedFields:['skills','equip']})),delta,metric:content.startsWith('op')?'clear':'score',unit:content.startsWith('op')?'%p':'점'});
  const save=(...args)=>g.save(store,false,entry(...args));
  save('op/one',['a'],1);save('op/two',['a'],2);save('op/three',['z'],20);save('clo/one',['z'],1);
  save('guild/one',['b'],1000000);save('cosmo/one',['missing'],200,'auto','assumed');
  const current={op:cond('auto'),clo:cond('auto'),guild:cond('auto'),cosmo:cond('auto')};
  const rank=()=>plain(g.grownPriority(store.get('growth.history'),sig('op'),current));
  assert.equal(rank()[0].key,'z');assert.equal(rank().find(x=>x.key==='a').count,1,'stages are one content kind');
  assert(rank().find(x=>x.key==='missing').source==='assumed');
  assert(rank().findIndex(x=>x.key==='a')<rank().findIndex(x=>x.key==='b'),'never compare guild points against probability');
  // Tie within op: z has the larger op improvement, despite its name sorting last.
  save('clo/one',[],0);assert(rank().findIndex(x=>x.key==='z')<rank().findIndex(x=>x.key==='a'));
  const before=Object.keys(store.get('growth.history')).length;
  save('op/three',['new'],500,'manual');
  assert.equal(Object.keys(store.get('growth.history')).length,before+1,'different conditions retained');
  assert(!rank().some(x=>x.key==='new'),'different conditions excluded');
  current.op=cond('manual');assert(rank().some(x=>x.key==='new'));assert(!rank().some(x=>x.key==='a'));
  current.op=cond('auto');
  const snapshot=JSON.stringify(data);data=JSON.parse(snapshot);assert.deepEqual(rank(),plain(g.grownPriority(data['growth.history'],sig('op'),current)));
  g.save(store,true,entry('op/shared',['shared'],999));assert.equal(JSON.stringify(data),snapshot,'shared must not persist');
  data['growth.history'].legacy={signature:sig('op'),rows:[{key:'old',confirmed:true}],historyVersion:g.VERSION};
  assert(!rank().some(x=>x.key==='old'),'old causal summaries are excluded');
  save('op/three',[],0);assert(!rank().some(x=>x.key==='z'),'latest empty result clears this content');
  assert(Object.values(data['growth.history']).some(h=>h.rows.some(r=>r.key==='new')),'excluded record still stored');
  assert(!g.grownPriority(data['growth.history'],sig('op','auto','other'),current).length);
  assert(Object.values(data['growth.history']).every(h=>!JSON.stringify(h).includes('stats_final')));
}
function markup(code=slotUi){
  const elements={'growth-priority':{hidden:true,innerHTML:''},'content':{value:0},'stage':{value:0}};
  const info={units:[1,2,3,4].map(id=>({id,level:1})),star_link:{level:240,source:[],slots:[{index:3,id:1}]}};
  const roster=[1,2,3,4].map(uid=>({uid,key:String(uid),name:'합성'+uid}));
  const ctx={GrowthGuide:G,StarLink:S,MI:{info},R:roster,BYKEY:Object.fromEntries(roster.map(s=>[s.key,s])),esc:String,PICK:{},LASTQ:{1:{rows:[{keys:['1']}]}}};
  vm.createContext(ctx);vm.runInContext(ui,ctx);vm.runInContext(code,ctx);
  const r={kind:'op',team:{t:{keys:['2','3']}},snapshot:{changes:Object.fromEntries([2,3].map(id=>[String(id),{key:String(id),unit:{id},source:'owned',changedFields:['level'],levelTarget:240}]))}};
  const result=ctx.growthSlotMarkup(r,{key:'op'},{tab:'t',name:'s'});
  assert(result.chip.includes('슬롯 2칸 부족'));assert(result.detail.includes('합성1 빼고 합성2 넣기'));
  assert(result.detail.includes('지금 추천팀 · 후순위'));assert(result.detail.includes('교체 쿨다운 있음'));
  info.star_link.slots=[{index:0,id:0},{index:1,id:0}];assert(ctx.growthSlotMarkup(r,{key:'op'},{}).chip.includes('빈 슬롯에 등록'));
  // Synthetic assumed members cannot consume slots even if present in an overwritten profile.
  r.snapshot.changes['3'].source='assumed';info.star_link.slots=[{index:0,id:0}];
  const mixed=ctx.growthSlotMarkup(r,{key:'op'},{});
  assert(mixed.chip.includes('빈 슬롯에 등록'));assert(!mixed.detail.includes('합성3'));
  r.snapshot.changes['2'].source='assumed';
  assert.deepEqual(plain(ctx.growthSlotMarkup(r,{key:'op'},{})),{chip:'',detail:''});
  // Production renderer keeps top five visible, folds the remainder, and marks missing saviors.
  Object.assign(ctx,{$:id=>elements[id],MI:{info,growth:{}},QK:{d:{}},contents:[{key:'op'}],cur:[{}],D:{},
    growthEnabled:()=>true,growthSig:()=>'',growthConditions:()=>({}),MyInfoReco:{hash:()=>''},
    LS:{get:()=>({h:{historyVersion:G.HISTORY_VERSION}})},GrowthGuide:{...G,grownPriority:()=>Array.from({length:7},(_,i)=>({key:String(i),source:i===3?'assumed':'owned',count:2,changedFields:['skills']}))}});
  vm.runInContext("GROW.historyEngine='test';growthRankPaint()",ctx);
  const html=elements['growth-priority'].innerHTML;
  assert.equal((html.split('<details>')[0].match(/data-k="growth-rank-row"/g)||[]).length,5);
  assert(html.includes('나머지 2명'));assert(html.includes('미보유'));assert(html.includes('2개 콘텐츠'));
}
function missingCard(code=ui){
  const ctx={GrowthGuide:G,esc:String};vm.createContext(ctx);vm.runInContext(code,ctx);
  const missing={source:'assumed',overwrite:true,changedFields:['level','equip','skills'],changes:{level:{before:null,after:240}}};
  assert(ctx.growthBadge(missing).includes('미보유'));
  assert(!ctx.growthBadge(missing).includes('스타링크'));assert(!ctx.growthBadge(missing).includes('장비'));
  assert.equal(ctx.growthCardMeta(missing),'');
}
function recording(code=ui){
  let data={},writes=0;const ctx={GrowthGuide:G,MyInfoReco:{OVERWRITE_VERSION:'test'},MI:{hash:'synthetic',shared:false},
    LS:{get:k=>data[k],set:(k,v)=>{writes++;data[k]=plain(v);return true;}},D:{cosmoRaid:{season:'test'}},CSR:{optMode:'score'},growthRankPaint:()=>{}};
  vm.createContext(ctx);vm.runInContext(code,ctx);ctx.growthRankPaint=()=>{};
  vm.runInContext("GROW.sig='signature'",ctx);
  const result={kind:'op',best:{clear:.9},baseline:{clear:.2},team:{t:{keys:['a','b']}},snapshot:{changes:{
    a:{key:'a',source:'owned',changedFields:['skills'],unit:{id:1,privateMarker:'not persisted'}},
    b:{key:'b',source:'assumed',changedFields:['level','equip']},unused:{key:'unused',source:'owned',changedFields:['skills']}}}};
  const c={key:'op'},st={tab:'tab',name:'stage'};
  ctx.growthRecord(c,st,result,true);assert.equal(writes,1);
  const saved=Object.values(data['growth.history'])[0];assert.deepEqual(saved.rows.map(r=>r.key),['a','b']);
  assert.equal(saved.unit,'%p');assert(Math.abs(saved.delta-70)<1e-8);
  assert(!JSON.stringify(data).includes('privateMarker'));
  ctx.growthRecord(c,st,result,true);assert.equal(writes,1,'repaint does not duplicate writes');
  const original=JSON.stringify(data),session=vm.runInContext('JSON.stringify([GROW.history,GROW.recordTag])',ctx);
  for(const key of ['cosmo','clo','guild'])for(const show of [false,true]){
    ctx.growthRecord({key},st,result,show);
    assert.equal(writes,1,'stale content must not overwrite history');assert.equal(JSON.stringify(data),original);
    assert.equal(vm.runInContext('JSON.stringify([GROW.history,GROW.recordTag])',ctx),session);
  }
  const before=JSON.stringify(data);ctx.MI.shared=true;result.best.clear=.95;
  ctx.growthRecord(c,st,result,true);assert.equal(writes,1);assert.equal(JSON.stringify(data),before);
  assert.equal(vm.runInContext('Object.values(GROW.history)[0].delta',ctx),75,'shared result stays in memory');
  ctx.MI.shared=false;ctx.growthRecord(c,st,result,false);
  assert.equal(writes,2);assert.equal(Object.values(data['growth.history'])[0].rows.length,0,'no supplementary card means no ranked members');
}
async function unchanged(s=S){
  // Frozen main source, never HEAD. Missing Git/history is a hard failure, not a skip.
  const revision='9f119eb84fc2f270a47920a6f10427e38a6d2547:star_link.js';
  const original=fs.readFileSync(require.resolve('./fixtures/star_link_main.js'),'utf8');
  assert.equal(original.replace(/\r\n/g,'\n'),cp.execFileSync('git',['show',revision],{encoding:'utf8',cwd:require('node:path').join(__dirname,'..')}));
  const old=load(original);
  for(const initial of [[1,2],[0,2],[1,0]]){
    const info={units:[1,2,3,4].map(id=>({id,level:1})),star_link:{source:[],level:240,slots:initial.map((id,index)=>({id,index}))}};
    const args={info,contexts:[{id:'op/test'}],candidates:[3,4],now:()=>0,
      evaluate:async({info})=>({runs:100,metric:{clear:.01+info.star_link.slots.filter(s=>s.id>=3).length*.45,n:100}})};
    const actual=await s.search(args),expected=await old.search(args);
    assert(expected.swaps.length>0&&expected.pairs>0,'comparison must exercise real exchanges');
    assert.deepEqual(plain(actual),plain(expected),'existing measured search remains identical');
  }
}
function mutation(name,code,from,to,test){assert(code.includes(from),name);let caught=false;
  try{test(code.replaceAll(from,to));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}
  assert(caught,'mutation survived: '+name);console.log('MUTATION caught + restored:',name);
}
(async()=>{
  slots();history();markup();missingCard();recording();await unchanged();
  mutation('slot shortage',ss,'Math.max(0,incoming.length-empty)','0',s=>slots(load(s)));
  mutation('source excluded',ss,'!source.includes(id)&&!initial.includes(id)','!initial.includes(id)',s=>slots(load(s)));
  mutation('empty first',ss,'emptyFirst:true','emptyFirst:false',s=>slots(load(s)));
  mutation('current team deferred',ss,'defer:current','defer:[]',s=>slots(load(s)));
  mutation('grown member retained',ss,'keep:[...team,...incoming]','keep:[]',s=>slots(load(s)));
  mutation('kinds not stage count',gs,"new Set(r.contents.map(c=>c.content.split('/')[0])).size","r.contents.length",s=>history(load(s)));
  mutation('same content tie',gs,'if(x!==y)return y-x;','if(false)return y-x;',s=>history(load(s)));
  mutation('no cross-content sum',gs,'if(a.count!==b.count)return b.count-a.count;',
    'if(a.contents&&b.contents)return b.contents.reduce((s,c)=>s+c.delta,0)-a.contents.reduce((s,c)=>s+c.delta,0);',s=>history(load(s)));
  mutation('conditions excluded',gs,"if(Object.hasOwn(current,ctx.kind)&&!conditionsMatch(ctx.conditions,current[ctx.kind],ctx.kind))continue;",'',s=>history(load(s)));
  mutation('different conditions retained',gs,"const next={...(storage.get('growth.history')||{})};","const next={};",s=>history(load(s)));
  mutation('shared not saved',gs,'if(shared)return false;','if(false)return false;',s=>history(load(s)));
  mutation('slot chip',slotUi,"'슬롯 '+plan.shortage+'칸 부족'","'등록'",markup);
  mutation('shared UI recording',ui,'GrowthGuide.save(LS,MI.shared,entry)','GrowthGuide.save(LS,false,entry)',recording);
  mutation('only supplementary members',ui,'const members=show?growthMembers(r):[]','const members=growthMembers(r)',recording);
  mutation('empty variants',ss,'!id?-1','id===0?-1',s=>slots(load(s)));
  mutation('free registrations',ss,'if(remove)replacements++','replacements++',s=>slots(load(s)));
  mutation('owned registration only',ss,'owned.has(id)&&','',s=>slots(load(s)));
  mutation('missing slot markup',slotUi,"a.source==='owned'&&",'',markup);
  mutation('missing card fields',ui,"if(r.source==='assumed')return '';",'',missingCard);
  mutation('matching content history',ui,'r.kind!==c.key||','',recording);
  const outgoing='[...new Set(slots)].filter(id=>!keep.includes(id))';assert(ss.includes(outgoing));
  await assert.rejects(()=>unchanged(load(ss.replace(outgoing,outgoing+'.sort((a,b)=>b-a)'))),{code:'ERR_ASSERTION'});
  console.log('MUTATION caught + restored: measured outgoing order');
  console.log('ALL OK growth next; 21 mutations; frozen main measured slot search');
})().catch(e=>{console.error(e);process.exitCode=1;});
