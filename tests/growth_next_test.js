const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const G=require('../growth_guide'),S=require('../star_link');
const gs=fs.readFileSync(require.resolve('../growth_guide'),'utf8'),ss=fs.readFileSync(require.resolve('../star_link'),'utf8');
const ui=fs.readFileSync(require.resolve('../growth_ui'),'utf8');
const plain=x=>JSON.parse(JSON.stringify(x));
function load(code){const ctx={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,ctx);return ctx.module.exports;}
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
function rankMarkup(){
  const elements={'growth-priority':{hidden:true,innerHTML:''},'content':{value:0},'stage':{value:0}};
  const info={units:[1,2,3,4].map(id=>({id,level:1}))};
  const roster=[1,2,3,4].map(uid=>({uid,key:String(uid),name:'합성'+uid}));
  const ctx={GrowthGuide:G,R:roster,BYKEY:Object.fromEntries(roster.map(s=>[s.key,s])),esc:String};
  vm.createContext(ctx);vm.runInContext(ui,ctx);
  // Production renderer keeps top five visible, folds the remainder, and marks missing saviors.
  Object.assign(ctx,{$:id=>elements[id],MI:{info,growth:{}},QK:{d:{}},contents:[{key:'op'}],cur:[{}],D:{},
    growthEnabled:()=>true,growthSig:()=>'',growthConditions:()=>({}),seasonBlocked:()=>false,MyInfoReco:{hash:()=>''},
    LS:{get:()=>({h:{historyVersion:G.HISTORY_VERSION}})},GrowthGuide:{...G,grownPriority:()=>Array.from({length:7},(_,i)=>({key:String(i),source:i===3?'assumed':'owned',count:2,changedFields:['skills']}))}});
  vm.runInContext("GROW.historyEngine='test';growthRankPaint()",ctx);
  const html=elements['growth-priority'].innerHTML;
  assert.equal((html.split('<details>')[0].match(/data-k="growth-rank-row"/g)||[]).length,5);
  assert(html.includes('나머지 2명'));assert(html.includes('미보유'));assert(html.includes('2개 콘텐츠'));
}
function cardMarks(code=ui){
  const growth=require('../data/growth.json'),info=structuredClone(require('./fixtures/myinfo_synthetic.json'));
  const M=require('../myinfo_reco'),Ux=require('../ux_ui');
  const ctx={GrowthGuide:G,esc:String,Ux,MI:{info,growth},contents:[{key:'op'}],$:()=>({value:0}),D:{archiveGrades:require('../data/archive_grades.json')}};vm.createContext(ctx);vm.runInContext(code,ctx);
  const missing={...M.assume('hilde',{...info,units:[]},growth),overwrite:true};
  assert(ctx.growthBadge(missing).includes('미보유'));
  assert(!ctx.growthBadge(missing).includes('스타링크'));assert(!ctx.growthBadge(missing).includes('장비'));
  assert(ctx.growthCardMeta(missing).includes('미보유'));
  assert(ctx.growthTodoRow(missing,'힐데').includes('data-growth-field="equip"'));
  const owned={...M.assume('luna',info,growth),overwrite:true};
  assert(ctx.growthBadge(owned).includes('키워야 함'));
  assert(ctx.growthTodoRow(owned,'루나').includes('data-growth-field="skills"'));
  assert(ctx.growthTodoRow(owned,'루나').includes('장비 +15'));
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
  history();rankMarkup();cardMarks();recording();await unchanged();
  mutation('kinds not stage count',gs,"new Set(r.contents.map(c=>c.content.split('/')[0])).size","r.contents.length",s=>history(load(s)));
  mutation('same content tie',gs,'if(x!==y)return y-x;','if(false)return y-x;',s=>history(load(s)));
  mutation('no cross-content sum',gs,'if(a.count!==b.count)return b.count-a.count;',
    'if(a.contents&&b.contents)return b.contents.reduce((s,c)=>s+c.delta,0)-a.contents.reduce((s,c)=>s+c.delta,0);',s=>history(load(s)));
  mutation('conditions excluded',gs,"if(Object.hasOwn(current,ctx.kind)&&!conditionsMatch(ctx.conditions,current[ctx.kind],ctx.kind))continue;",'',s=>history(load(s)));
  mutation('different conditions retained',gs,"const next={...(storage.get('growth.history')||{})};","const next={};",s=>history(load(s)));
  mutation('shared not saved',gs,'if(shared)return false;','if(false)return false;',s=>history(load(s)));
  mutation('shared UI recording',ui,'GrowthGuide.save(LS,MI.shared,entry)','GrowthGuide.save(LS,false,entry)',recording);
  mutation('only supplementary members',ui,'const members=show?growthMembers(r):[]','const members=growthMembers(r)',recording);
  mutation('missing card fields',ui,"if(r.overwrite)return Ux.memberHtml", "if(r.source==='assumed')return '';if(r.overwrite)return Ux.memberHtml",cardMarks);
  mutation('matching content history',ui,'r.kind!==c.key||','',recording);
  // Isolated registration power and its label are covered by ux_ui_test.
  const outgoing='[...new Set(slots)]';assert(ss.includes(outgoing));
  await assert.rejects(()=>unchanged(load(ss.replace(outgoing,outgoing+'.sort((a,b)=>b-a)'))),{code:'ERR_ASSERTION'});
  console.log('MUTATION caught + restored: measured outgoing order');
  console.log('ALL OK growth next; 11 mutations; frozen main measured slot search');
})().catch(e=>{console.error(e);process.exitCode=1;});
