const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const G=require('../gwen_lane'),U=require('../ux_ui');
function cooldown(g){const p=g.policy(()=>0);assert(p.event('put',0).speech);assert(!p.event('put',200).speech);
  assert(!p.event('put',4000).speech);assert(p.event('put',8000).speech);}
function priority(g){const p=g.policy(()=>0);p.event('work',0,{level:'work',duration:Infinity});assert.equal(p.event('put',10),null);
  assert(p.event('high',10,{level:'result',id:'one'}));assert.equal(p.event('high',11,{level:'result',id:'one'}),null);
  assert(p.event('error',11,{level:'error',duration:5000}));assert.equal(p.event('high',12,{level:'result',id:'two'}),null);}
function motion(g){const equal=(a,b)=>assert.deepEqual(JSON.parse(JSON.stringify(a)),b);for(const reduced of [true,false])for(const mobile of [true,false]){
  const r=g.travel(20,400,500,80,{run:true,reduced,mobile});assert(r.ms<=600);assert(r.x<=164);
  if(reduced)equal(r,{x:20,ms:0});else{assert.equal(r.x,mobile?92:164);assert.equal(r.ms,600);}
 }equal(g.travel(400,9999,500,80,{run:true}),{x:420,ms:1000/12});
 equal(g.travel(20,200,500,80,{quiet:true}),{x:20,ms:0});}
cooldown(G);priority(G);motion(G);
for(const [kind,choices] of Object.entries(G.CHOICES))for(const key of choices)assert(U.GWEN_SCENES[key],`${kind}: ${key}`);
for(const [key,lines] of Object.entries(G.SAY)){assert(lines.length>=1&&lines.length<=4,key);for(const line of lines)assert(!/단장(?!님)/.test(line));}
const p=G.policy(()=>0),history=[];for(let i=0;i<20;i++){const a=p.pick(G.CHOICES.high);assert(!history.slice(-2).includes(a));history.push(a);}
const clicks=G.policy(()=>0);assert.equal(clicks.poke(0).art,'shy');assert.equal(clicks.poke(100).art,'sulk');assert.equal(clicks.poke(200).art,'cry');
assert.equal(clicks.poke(10199),null);assert.equal(clicks.poke(10200).art,'shy');
const q=G.policy();assert.equal(q.event('put',0,{quiet:true}),null);assert(q.event('work',0,{quiet:true,level:'work'}));
const source=fs.readFileSync(require.resolve('../gwen_lane'),'utf8');
const healthy={module:{exports:{}}};vm.runInNewContext(source,healthy);cooldown(healthy.module.exports);priority(healthy.module.exports);motion(healthy.module.exports);
for(const [name,from,to,check] of [
 ['cooldown','now-s.lastReaction<4000','false',g=>{const p=g.policy();p.event('put',0);p.state.lastSpeech=-Infinity;assert(!p.event('put',10).speech)}],
 ['priority','priority<s.priority','priority>s.priority',priority],
 ['reduced-motion','if(reduced||quiet||home&&mobile)','if(quiet||home&&mobile)',motion],
 ['lane-boundary','Math.min(max,target)','target',motion],
]){assert(source.includes(from),name);const c={module:{exports:{}}};vm.runInNewContext(source.replace(from,to),c);
 assert.throws(()=>check(c.module.exports),assert.AssertionError,name);console.log('mutation caught:',name);}
console.log('PASS lane policy: assets, speech, last two, priorities, result once, three pokes/lock, quiet, movement; 4 mutations');
