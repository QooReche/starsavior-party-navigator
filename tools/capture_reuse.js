// node tools/capture_reuse.js  →  stdout JSON  (baseline for reco_reuse_test.js)
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const Q  = require('../quick.js');
const ROOT = path.resolve(__dirname, '..');
const html  = fs.readFileSync(path.join(ROOT, 'party_template.html'), 'utf8');
const index = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const D     = JSON.parse(index.match(/const D=(\{.*?\});\s*\n/)[1]);
const qdata = Q.mergeSm(JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'quick.json'), 'utf8')));

// Remove fetch and window-side effects that need a browser
const prep = code =>
  code.replace(/fetch\(["']data\/quick\.json["'][\s\S]*?\}\);\s*\n/, '')
      .replace(/window\.PN_Q_SV=[^\n]*\n/, '')
      .replace(/if\(window\.renderPw\)[^\n]*\n?/g, '')
      .replace(/rerunNow\(\)/g, '');

const sec = (s, e) => html.slice(html.indexOf(s), html.indexOf(e, html.indexOf(s)));
const fakePromise = {then() { return fakePromise; }, catch() { return fakePromise; }};

const ctx = vm.createContext({
  D, CFG: D.cfg, R: D.roster,
  EL: {sun:'태양', moon:'달', star:'별', order:'질서', chaos:'혼돈'},
  Quick: Q, window: {Quick: Q},
  REKINDLE: [0, 0.03, 0.07, 0.12, 0.18, 0.25],
  GIMACT: [], SBACT: [], DMW: [0, 0.5],
  SIMQ: {res:{}, more:{}, scr:{}, n:100},
  LASTQ: {}, JOINT: null, MODE: 'auto',
  LS: {get:()=>null, set:()=>{}}, SHARE: {},
  miMode: ()=>false, miProfile: ()=>({results:{}}),
  MyInfoReco: {team:()=>({})}, rkOf: ()=>0,
  $: id => ({value: id==='grow' ? '1' : '0', selectedOptions:[{textContent:''}]}),
  location: {search: ''},
  ckey: party => party.map(x=>x.s.key).sort().join(','),
  // stubs for sim-result helpers (SIMQ.res is empty so these always return null/vd)
  simCls: r => {const c=r.clear!=null?r.clear:r.c; return c>=0.9?'safe':c>=0.5?'tight':'hard'},
  simMain: r => r,  // SIMQ.res always empty → r=undefined → falsy
  simSig:  (st,t) => t.keys.join(','),
  cmpArr:  (x,y) => {for(let i=0;i<x.length;i++){if(x[i]<y[i])return-1;if(x[i]>y[i])return 1}return 0},
  fetch: ()=>fakePromise, _qdata: qdata,
});

// Load sections – order matters
vm.runInContext(sec('let SBACT=', 'function synSummary('), ctx);
vm.runInContext(prep(sec('const PICK={};', 'function quickRank(')), ctx);
vm.runInContext('QK.d = _qdata; QK.err = null;', ctx);
vm.runInContext(sec('function quickRank(', 'function quickWeak('), ctx);
// qVd, qScore needed by jointPick (lines 785-790)
vm.runInContext(sec('function qVd(', 'function jointPick('), ctx);
vm.runInContext(sec('function jointPick(', 'function jointFirst('), ctx);
vm.runInContext('function buildCands(cands,defPen){return rankAll(cands,defPen).slice(0,10).map((x,i)=>({combo:x.combo,v:x.v,got:x.got,rank:i,key:ckey(x.combo)}))}', ctx);

// Deterministic sample
function sample(arr, n, seed) {
  const a = [...arr]; let s = seed >>> 0;
  for (let i = a.length - 1; i > 0; i--) {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    const j = s % (i + 1); [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n).sort();
}

const roster = D.roster.map(s => s.key);
const own40  = sample(roster, 40, 7);
const own24  = sample(roster, 24, 7);
// cosmo: use 24-member sample (avoids multi-minute enumeration on full roster)
const own24c = sample(roster, 24, 42);

const CASES = [
  {ck:'cosmo', needle:'길레 2단계',             own: own24c, label:'cosmo_24'},
  {ck:'rush',  needle:'매니저 그레고리 Ⅰ',       own: own40,  label:'rush_40'},
  {ck:'op',    needle:'SECTOR 1-1',             own: own24,  label:'op_24'},
];

const result = {};
for (const {ck, needle, own, label} of CASES) {
  try {
    ctx._own = own;
    result[label] = vm.runInContext(`(()=>{
      const c  = D.contents.find(c=>c.key===${JSON.stringify(ck)});
      const st = c.stages.find(s=>s.name.includes(${JSON.stringify(needle)}));
      const own = new Set(_own);
      const rsEl = (CFG.restrict[c.name]||{})[st.tab];
      GIMACT = gimTop(c,st); SBACT = st.sb||[];
      DMW = [Math.min(1,(st.n-1)/2), c.boss?CFG.damage.weightBoss:CFG.damage.weightMob];
      const defPen = CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty;
      const cands = D.roster.filter(s=>own.has(s.key)&&(!rsEl||s.el===rsEl))
                            .map(s=>{const[v,p]=score(s,st.w,c.main,c.boss);return{s,score:v,parts:p}});
      const qi  = quickIn(c,st);
      const bc  = buildCands(cands,defPen);
      const qr  = qi ? quickRank(rankAll(cands,defPen),qi) : null;
      const jp  = (c.parties||1)===2 && qi ? jointPick(c,st,own,defPen) : null;
      return {
        bc:  bc.map(x=>x.key),
        qr:  qr ? qr.slice(0,10).map(t=>({
               keys:   t.keys.slice().sort().join(','),
               vd:     t.vd,
               rounds: t.q.rounds,
               left:   t.q.left,
               ng:     t.ng??null,
               st:     t.st??null,
               src:    t.src??null,
             })) : null,
        jp: jp,
      };
    })()`, ctx);
  } catch(e) {
    result[label] = {error: e.message + '\n' + e.stack};
  }
}

process.stdout.write(JSON.stringify(result, null, 2) + '\n');
