const assert=require('node:assert/strict');
const View=require('../skill_view.js');
const all=require('../rawdata/databook_main.json').units;
const raw=all.filter(u=>u.v==='기본');
const data=require('../data/savior_skills.json');

// Compare every generated row with its public source (also run build_skills.py --check).
assert.equal(Object.keys(data).length,raw.length);
for(const unit of raw){
  assert.equal(data[unit.id].length,unit.sk.length);
  unit.sk.forEach((source,i)=>{
    const row=data[unit.id][i],s=View.normalize(row);
    for(const key of ['sl','n','ty','tg','cd','cdm','mx','d1'])assert.equal(row[key],source[key]);
    assert.equal(s.dx,source.dx||source.d1);
    assert.deepEqual(s.lv,source.lv.map(l=>l.slice(0,2)));
    assert.deepEqual(s.gl,(source.gl||[]).map(g=>[g.n||'',g.k||'',g.d||'']));
    assert(!('L' in row)&&!('ef' in row)&&!('dm' in row));
    assert.equal(View.select(row).level,source.mx);
    assert.equal(View.select(row).description,source.dx||source.d1);
    if(source.L?.cd?.length===source.mx){
      for(let level=1;level<=source.mx;level++)assert.equal(View.select(row,{[s.slot]:level}).cooldown,source.L.cd[level-1],`${unit.id} ${s.n} Lv${level}`);
    }
  });
}
const special=data['1001'].find(s=>s.sl==='특수기');
for(const [level,cd,next] of [[1,5,2],[5,5,6],[6,4,7],[9,4,10],[10,3,null]]){
  const s=View.select(special,{special:level});
  assert.equal(s.cooldown,cd);assert.equal(s.next?.[0]??null,next);
}
// Do not assume all reductions occur at Lv6, or collapse two reductions into one.
const custom={...special,cd:8,cdm:5,dx:'최대 설명',lv:[[1,'기본'],[3,'쿨타임 2턴 감소'],[8,'쿨타임 1턴 감소']]};
assert.equal(View.select(custom,{special:2}).cooldown,8);
assert.equal(View.select(custom,{special:3}).cooldown,6);
assert.equal(View.select(custom,{special:6}).cooldown,6);
assert.equal(View.select(custom,{special:8}).cooldown,5);
assert.equal(View.select(custom,{special:9}).description,custom.d1);
assert.equal(View.select(custom,{special:10}).description,'최대 설명');
assert.equal(View.select({...custom,lv:[]},{special:6}).cooldown,5);
assert.equal(View.select({...custom,cd:undefined}).cooldown,null);
assert.equal(View.select({...custom,cd:0,cdm:0}).cooldown,0);
assert.equal(View.select(custom,{special:99}).level,10);
assert.equal(View.select(custom,{special:0}).level,0);
assert.equal(View.select({...custom,sl:'변형 궁극기'},{ultimate:4}).level,4);
assert.equal(View.select(custom).own,false);
assert.equal(View.select(custom,{special:4}).own,true);
const variant=raw.find(u=>u.sk.length>4);
const html=View.render(data[variant.id]);
assert.equal((html.match(/class="skill-card"/g)||[]).length,4);
assert(html.includes('변형 스킬'));
const escaped=View.render([{...custom,n:'<img onerror="bad">',d1:'[용어] <script>',dx:'',gl:[['용어','강화','<img>']],lv:[[1,'<script>']]}],{special:1});
assert(!escaped.includes('<img'));assert(!escaped.includes('<script>'));
assert(escaped.includes('aria-expanded="false"'));assert(escaped.includes('&lt;img&gt;'));
assert.equal(raw.length,57);assert.equal(all.length-raw.length,8);
console.log('PASS: 57 public units, base/bloom separation, compact conversion, levels, cumulative cooldowns, descriptions, variants, escaping');
