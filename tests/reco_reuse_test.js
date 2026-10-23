// node tests/reco_reuse_test.js
// Verifies buildCands, quickRank, jointPick results are identical before and after refactor.
// Expected values are fixed from the pre-refactor code (tools/capture_reuse.js).
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const Q = require('../quick.js');

const ROOT     = path.resolve(__dirname, '..');
const EXPECTED = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'reuse_baseline.json'), 'utf8'));
const html     = fs.readFileSync(path.join(ROOT, 'party_template.html'), 'utf8');
const D        = JSON.parse(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').match(/const D=(\{.*?\});\s*\n/)[1]);
const qdata    = Q.mergeSm(JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'quick.json'), 'utf8')));

const sec  = (s, e) => html.slice(html.indexOf(s), html.indexOf(e, html.indexOf(s)));
const prep = code => code
  .replace(/fetch\(["']data\/quick\.json["'][\s\S]*?\}\);\s*\n/, '')
  .replace(/window\.PN_Q_SV=[^\n]*\n/, '')
  .replace(/if\(window\.renderPw\)[^\n]*\n?/g, '')
  .replace(/rerunNow\(\)/g, '');

function buildCtx() {
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
    simCls:  r => { const c = r.clear != null ? r.clear : r.c; return c >= 0.9 ? 'safe' : c >= 0.5 ? 'tight' : 'hard'; },
    simMain: r => r,
    simSig:  (st, t) => t.keys.join(','),
    cmpArr:  (x, y) => { for (let i = 0; i < x.length; i++) { if (x[i] < y[i]) return -1; if (x[i] > y[i]) return 1; } return 0; },
    fetch: () => fakePromise, _qdata: qdata,
  });
  vm.runInContext(sec('let SBACT=', 'function synSummary('), ctx);
  vm.runInContext(prep(sec('const PICK={};', 'function quickRank(')), ctx);
  vm.runInContext('QK.d = _qdata; QK.err = null;', ctx);
  vm.runInContext(sec('function quickRank(', 'function quickWeak('), ctx);
  vm.runInContext(sec('function qVd(', 'function jointPick('), ctx);
  vm.runInContext(sec('function jointPick(', 'function jointFirst('), ctx);
  vm.runInContext('function buildCands(cands,defPen){return rankAll(cands,defPen).slice(0,10).map((x,i)=>({combo:x.combo,v:x.v,got:x.got,rank:i,key:ckey(x.combo)}))}', ctx);
  return ctx;
}

// Deterministic sample – must match capture_reuse.js
function sample(arr, n, seed) {
  const a = [...arr]; let s = seed >>> 0;
  for (let i = a.length - 1; i > 0; i--) {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    const j = s % (i + 1); [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n).sort();
}

const roster = D.roster.map(s => s.key);
const OWN = {
  cosmo_24: sample(roster, 24, 42),
  rush_40:  sample(roster, 40, 7),
  op_24:    sample(roster, 24, 7),
};
const NEEDLE = {cosmo_24:'길레 2단계', rush_40:'매니저 그레고리 Ⅰ', op_24:'SECTOR 1-1'};
const CK     = {cosmo_24:'cosmo',      rush_40:'rush',              op_24:'op'};

let failed = 0;

for (const [label, exp] of Object.entries(EXPECTED)) {
  const ctx  = buildCtx();
  ctx._own   = OWN[label];
  const ck   = CK[label];
  const needle = NEEDLE[label];

  const gotRaw = vm.runInContext(`(()=>{
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
  // Normalize vm-realm objects to plain JS (vm arrays have different prototypes)
  const got = JSON.parse(JSON.stringify(gotRaw));

  try {
    // buildCands order
    assert.deepEqual(got.bc, exp.bc, `${label} buildCands key order`);

    // quickRank order (keys, vd, rounds, left)
    if (exp.qr) {
      assert.ok(got.qr, `${label} quickRank should not be null`);
      assert.equal(got.qr.length, exp.qr.length, `${label} quickRank length`);
      for (let i = 0; i < exp.qr.length; i++) {
        assert.equal(got.qr[i].keys,   exp.qr[i].keys,   `${label} qr[${i}] keys`);
        assert.equal(got.qr[i].vd,     exp.qr[i].vd,     `${label} qr[${i}] vd`);
        assert.equal(got.qr[i].rounds, exp.qr[i].rounds, `${label} qr[${i}] rounds`);
        assert.ok(Math.abs(got.qr[i].left - exp.qr[i].left) < 1e-9, `${label} qr[${i}] left`);
      }
    } else {
      assert.equal(got.qr, null, `${label} quickRank should be null`);
    }

    // jointPick result (only cosmo_24 is non-null)
    assert.deepEqual(got.jp, exp.jp, `${label} jointPick result`);

    console.log(`PASS ${label}`);
  } catch(e) {
    failed++;
    console.error(`FAIL ${label}: ${e.message}`);
  }
}

// tie-span i-order test: verify combos with same approx-score keep creation index order
{
  const ctx = buildCtx();
  const own24 = OWN.op_24;
  ctx._own = own24;
  const allRankedRaw = vm.runInContext(`(()=>{
    const c  = D.contents.find(c=>c.key==='op');
    const st = c.stages.find(s=>s.name.includes('SECTOR 1-1'));
    const own = new Set(_own);
    GIMACT=gimTop(c,st); SBACT=st.sb||[];
    DMW=[Math.min(1,(st.n-1)/2),c.boss?CFG.damage.weightBoss:CFG.damage.weightMob];
    const defPen=CFG.defPenByContent[c.name]??CFG.weights.defenderPenalty;
    const cands=D.roster.filter(s=>own.has(s.key)).map(s=>{const[v,p]=score(s,st.w,c.main,c.boss);return{s,score:v,parts:p}});
    // full ranked list
    return topParties(cands,defPen,1e9).map((t,pos)=>({key:ckey(t.combo),v:t.v,i:t.i,pos}));
  })()`, ctx);
  const allRanked = JSON.parse(JSON.stringify(allRankedRaw));

  // Find groups of ties (same v to 9 decimal places)
  const groups = new Map();
  for (const t of allRanked) {
    const vk = t.v.toFixed(9);
    if (!groups.has(vk)) groups.set(vk, []);
    groups.get(vk).push(t);
  }
  let tieGroups = 0, iOrderOk = true;
  for (const [, grp] of groups) {
    if (grp.length < 2) continue;
    tieGroups++;
    for (let k = 1; k < grp.length; k++) {
      if (grp[k].i <= grp[k-1].i) { iOrderOk = false; break; }
    }
    if (!iOrderOk) break;
  }
  try {
    assert.ok(tieGroups > 0, 'expected tie groups in op_24');
    assert.ok(iOrderOk, 'i-order must be ascending within same-v group');
    console.log(`PASS tie-span i-order (${tieGroups} groups)`);
  } catch(e) {
    failed++;
    console.error(`FAIL tie-span: ${e.message}`);
  }
}

if (failed) process.exit(1);
console.log(`ALL OK (${Object.keys(EXPECTED).length + 1} checks)`);
