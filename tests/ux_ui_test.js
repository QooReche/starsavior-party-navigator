const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const U=require('../ux_ui'),M=require('../myinfo_reco'),S=require('../myinfo_stats');
const growth=require('../data/growth.json'),grades=require('../data/archive_grades.json');
const view={...require('../data/myinfo_view.json'),itemSlots:require('../data/myinfo_slots.json')};
const roster=Object.entries(growth.assumed.units).map(([key,s])=>({key,uid:s.uid}));
function checkVerdict(u=U){for(const [p,expected] of [[0,'risk'],[.49999,'risk'],[.5,'shaky'],[.69999,'shaky'],[.7,'ok'],[.89999,'ok'],[.9,'safe'],[1,'safe']])assert.equal(u.verdict(p)[0],expected);}
function checkGrades(u=U){for(const [n,label] of [[1250,'SG'],[1150,''],[497,'A+'],[465,'A+'],[435,'A'],[373,'B+'],[367,'B+'],[181,'D+'],[148,'E+'],[66,'F']]){
  for(let i=0;i<5;i++)assert.equal(u.grade(n,i,grades),label,`grade ${n}/${i}`);
}assert.equal(u.archive(1250,0,grades),'SG 1,250','1,250(MAX) is shown as SG (user decision 11/13)');assert.equal(u.archive(1150,0,grades),'1,150','other upper glyphs stay numeric');
assert.equal(u.grade(1501,0,grades),'');}
function checkPower(u=U){const info=structuredClone(require('./fixtures/myinfo_synthetic.json'));
  for(const k of Object.keys(growth.tactics))info.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};
  info.star_link={level:240,source:[],slots:[]};info.star_link_level=240;
  for(const x of info.units){x.level=80;x.resonance=0;x.equip=[];x.skills={basic:1,special:1,ultimate:1,passive:1};x.gauntlet.journey=[66,148,373,181,435];x.gauntlet.potentials=[];}
  const original=JSON.stringify(info),snapshot=M.overwrite(info,roster,growth,'op',{includeMissing:false});
  assert.equal(snapshot.errors.length,0);const counts={};
  for(const a of Object.values(snapshot.changes)){
    const display=u.member(a,info,growth,'op',grades,view),old=info.units.find(x=>x.id===a.unit.id);
    assert(display.after>display.before);assert.equal(display.fields.length,a.changedFields.length);
    for(const f of display.fields){counts[f.field]=(counts[f.field]||0)+1;
      const unit=structuredClone(old);let account=info;
      if(f.field==='level')account=a.targetInfo;
      else if(['journey','potentials'].includes(f.field))unit.gauntlet[f.field]=structuredClone(a.unit.gauntlet[f.field]);
      else unit[f.field]=structuredClone(a.unit[f.field]);
      const expected=S.final_stats(unit,account,growth,'normal').power-S.final_stats(old,info,growth,'normal').power;
      assert.equal(f.delta,expected,f.field);assert(f.field==='skills'?f.short==='3종':f.short.includes('→'),f.field);assert(f.detail.length>0);
      assert.equal(u.memberHtml(display).includes(`data-growth-field="${f.field}"`),f.delta!==0);
    }
  }
  for(const f of Object.keys(U.labels))assert(counts[f]>0,`path not exercised: ${f}`);
  assert.equal(JSON.stringify(info),original);
  // Fixed-level content must not report a fictitious benefit for registration.
  const a=Object.values(snapshot.changes).find(a=>a.changedFields.includes('level'));
  const fixed=u.member(a,info,growth,'cosmo',grades,view);
  assert(!fixed.fields.some(f=>['level','resonance'].includes(f.field)));
  assert(!u.memberHtml(fixed).includes('data-growth-field="level"'));
  const missing=M.overwrite(info,roster,growth,'op',{includeMissing:true});
  assert(!Object.values(missing.changes).some(a=>a.source==='assumed'));
  const ma=M.assume('hilde',{...info,units:[]},growth),md=u.member(ma,{...info,units:[]},growth,'op',grades,view);
  assert.equal(md,null);assert.equal(u.memberHtml(md),'');assert.equal(u.todosHtml(md),'');
}
function checkChips(u=U){
  const fields=Object.entries(u.labels).map(([field,label],i)=>({field,label,short:'길고 복잡한 상세 → 목표',detail:'상세 정보',delta:i===3?0:100+i}));
  const m={before:100,after:200,fields,missing:false},html=u.todosHtml(m);
  assert.equal((html.match(/<button /g)||[]).length,6);
  assert(!html.includes('data-growth-field="resonance"'));
  assert.equal((html.match(/길고 복잡한/g)||[]).length,6,'every changed target belongs in compact chips');
  assert(html.includes('스타링크 길고 복잡한 상세 → 목표 <small>(+100)</small>'));
  assert(html.includes('장비 길고 복잡한 상세 → 목표 <small>(+101)</small>'));
  assert(!u.memberHtml(m,false).includes('<button'));
  assert.equal(u.todosHtml({...m,fields:[{...fields[0],delta:0}]}),'');
  assert.match(u.todosHtml({...m,fields:[{...fields[0],delta:null}],missing:true}),/자료 없음/);
  assert.match(u.todosHtml({...m,fields:[{...fields[0],delta:-20}]}),/−20/);
}
function checkSkills(u=U){
  const info=structuredClone(require('./fixtures/myinfo_synthetic.json'));
  const old=info.units[0];old.skills={basic:6,special:10,ultimate:1,passive:10};
  const target=structuredClone(old);target.skills={basic:10,special:10,ultimate:10,passive:10};
  function inspect(expected){
    const a={unit:target,changedFields:['skills'],changes:{skills:{before:old.skills,after:target.skills}}};
    const m=u.member(a,info,growth,'op',grades,view),f=m.fields[0];
    assert.equal(f.short,expected);assert(f.delta>0);
    assert.equal(f.detail.split('\n').length,3);
    for(const [key,label] of Object.entries({basic:'기본',special:'특수',ultimate:'궁'}))assert(f.detail.includes(`${label} ${old.skills[key]}→10`));
    assert(!f.detail.includes('패시브'));
    assert(u.todosHtml(m).includes(`>스킬 ${expected} <small>(+${u.num(f.delta)})</small>`));
  }
  inspect('기본 6→10 · 궁 1→10');
  old.skills.ultimate=10;inspect('기본 6→10');
  old.skills.special=1;old.skills.ultimate=1;inspect('3종');
  old.skills.passive=1;target.skills.passive=1;inspect('3종');
}
function checkTabState(u=U){
  const base={enabled:true,phase:'done',better:true,baseline:{clear:.4},best:{clear:.8}};
  const s=u.resultTabState(base);assert(s.show&&s.recommend);assert.equal(s.now,'클리어 40%');assert.equal(s.growth,'맞추면 80% ↑');
  for(const clear of [0,.4999,.5,1])assert.equal(u.resultTabState({...base,baseline:{clear}}).recommend,clear<.5);
  assert(!u.resultTabState({...base,baseline:null}).recommend);
  for(const changes of [{enabled:false},{better:false},{phase:'idle'}])assert(!u.resultTabState({...base,...changes}).show);
  const running=u.resultTabState({...base,phase:'running',better:false,message:'후보 확인 2/10'});
  assert(running.show);assert.equal(running.growth,'계산 중 · 후보 확인 2/10');
  const error=u.resultTabState({...base,phase:'error',better:false,errors:['worker failed']});
  assert(error.show);assert.equal(error.growth,'미완료 · 실패');
  for(const kind of ['guild','cosmo']){const state=u.resultTabState({...base,kind,baseline:{score:100,sum:100},best:{score:200,sum:200}});
    assert.equal(state.now,'점수 100점');assert.equal(state.growth,'맞추면 200점 ↑');assert(!state.recommend);}
}
function load(code){const c={module:{exports:{}},require:p=>require('../'+p)};vm.runInNewContext(code,c);return c.module.exports;}
const source=fs.readFileSync(require.resolve('../ux_ui'),'utf8');
function mutation(from,to,check){assert(source.includes(from));let caught=false;try{check(load(source.replace(from,to)));}catch(e){if(e.code==='ERR_ASSERTION')caught=true;else throw e;}assert(caught,`mutation survived: ${from}`);check(U);}
checkVerdict();checkGrades();checkPower();checkChips();checkSkills();checkTabState();
mutation('p>=.9','p>.9',checkVerdict);
mutation('value>=r[0]','value>r[0]+50',checkGrades);
mutation('delta=S.final_stats(unit,account,growth,rule).power-before;','delta=after-before;',checkPower);
mutation('a.changedFields.filter(f=>','a.changedFields.filter(f=>f!=="equip").filter(f=>',checkPower);
mutation('f.delta!==0','true',checkChips);
mutation("${esc(f.short)}", "", checkChips);
mutation("changed.length<=2","changed.length<2",checkSkills);
mutation("changed.map(line).join(' · ')","changed.slice(-1).map(line).join(' · ')",checkSkills);
mutation("Object.keys(skillNames).map(line)","changed.map(line)",checkSkills);
mutation("goal(baseline)<.5","goal(baseline)<=.5",checkTabState);
mutation("&&!!better","",checkTabState);
mutation("!!enabled&&","",checkTabState);
mutation("phase==='running'||phase==='error'||","",checkTabState);
console.log('PASS probability, grades, power, skill 1/2/3 targets, passive preserved, three details, tab states; 13 mutations caught');
