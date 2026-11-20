// Local-only benchmark: account-derived lists/rows stay at their external paths.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const C=require('../cosmo_search.js'),legacy=require('../tests/helpers/cosmo_triples_legacy.js');
const args=process.argv.slice(2),get=(key,fallback)=>{const i=args.indexOf('--'+key);return i<0?fallback:args[i+1];};
const input=get('lists');if(!input)throw Error('--lists <private lists JSON> required');
const root=fs.realpathSync(path.resolve(__dirname,'..')).toLowerCase();
function external(file){const p=fs.realpathSync(path.resolve(file));if(p.toLowerCase()===root||p.toLowerCase().startsWith(root+path.sep))throw Error('measurement inputs must be outside the worktree');return p;}
const lists=JSON.parse(fs.readFileSync(external(input),'utf8').replace(/^\uFEFF/,''));
function run(fn,limit=Number.MAX_SAFE_INTEGER){const budget={remaining:limit},start=performance.now(),rows=fn(lists,10,budget),ms=performance.now()-start;return {rows,checks:limit-budget.remaining-(budget.exhausted?1:0),ms,budget};}
const old=run(legacy),limited=run(legacy,2000000),fresh=run(C.bestTriples);
assert.deepEqual(fresh.rows,old.rows);
const times={old:[old.ms],new:[fresh.ms]};
for(let i=0;i<4;i++){times.old.push(run(legacy).ms);times.new.push(run(C.bestTriples).ms);}
const timing=xs=>({firstMs:xs[0],medianMs:xs.slice().sort((a,b)=>a-b)[Math.floor(xs.length/2)],maxMs:Math.max(...xs)});
let target=null;
if(get('rows')){
 const r=JSON.parse(fs.readFileSync(external(get('rows')),'utf8').replace(/^\uFEFF/,''));
 const rows=r.rows||r.result?.rows||r.candidates||[], t=rows.find(x=>x.sum===Number(get('target')));
 if(t){const same=(a,b)=>C.idOf(a.keys)===C.idOf(b.keys),key=x=>x.teams.map(e=>C.idOf(e.keys)).join('/');
  target={inLists:t.teams.map((e,i)=>lists[i].some(x=>same(e,x))),unlimitedRank:old.rows.findIndex(x=>key(x)===key(t))+1,limitedRank:limited.rows.findIndex(x=>key(x)===key(t))+1};
 }
}
console.log(JSON.stringify({sizes:lists.map(l=>l.length),old:{checks:old.checks,...timing(times.old)},new:{checks:fresh.checks,...timing(times.new)},equal:true,limit:{checks:limited.checks,exhausted:!!limited.budget.exhausted,position:limited.budget.position,rows:limited.rows.length},target},null,2));
