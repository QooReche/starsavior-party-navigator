// Replay measured battles through the untouched base-commit search implementation.
// This verifies policy/result equivalence, not timing. No golden files are written.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const {execFileSync}=require('node:child_process'),Module=require('node:module');
const crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),GS=require('../guild_search.js');
const [out='local/cosmo-rd',base='d675cd0']=process.argv.slice(2);
const show=file=>execFileSync('git',['show',base+':'+file],{cwd:root,encoding:'utf8',maxBuffer:32*1024*1024});
const legacy=new Module(path.join(root,'cosmo_search.legacy.js'),module);
legacy.filename=path.join(root,'cosmo_search.legacy.js');legacy.paths=module.paths;
legacy._compile(show('cosmo_search.js'),legacy.filename);
const C=legacy.exports,G=JSON.parse(show('data/cosmo_raid.json'));
const read=p=>JSON.parse(p.endsWith('.gz')?zlib.gunzipSync(fs.readFileSync(p)):fs.readFileSync(p,'utf8'));
const catalog=read(path.join(out,'catalog.json'));
const originalParty=GS.party;
GS.party=(...args)=>{const p=originalParty(...args);p.spec={units:p.order.map(key=>({key,build:'standard'})),leader:0};return p;};
(async()=>{
 for(const dir of fs.readdirSync(out).filter(d=>d.includes('-baseline-')&&fs.existsSync(path.join(out,d,'result.json')))){
  const report=read(path.join(out,dir,'result.json')),roster=catalog.slice(0,report.size);
  let phase=0;
  GS.runPhase=o=>{
   const p=read(path.join(out,dir,`phase-${phase++}.json.gz`));
   assert.equal(p.seed,100*report.repeat+o.seed);assert.equal(p.timing.runs,o.runs);
   assert.deepEqual(o.jobs.map(j=>[j.key,j.order]),p.jobs.map(j=>[j.key,j.order]));
   return {promise:Promise.resolve(p.res),cancel(){}};
  };
  const result=await C.search({S:G.search,bosses:G.season.bossOrder,mode:report.mode,level:6,
   results:Object.fromEntries(roster.map(r=>[r.key,r])),roster,workers:report.workers,
   makeWorker:()=>{throw Error('unexpected simulation');},stage:'cosmo',base:''});
  const hash=crypto.createHash('sha256').update(JSON.stringify(result)).digest('hex');
  assert.equal(hash,report.resultHash);assert.equal(phase,report.phases.length);
  console.log(JSON.stringify({dir,base,hash,identical:true}));
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
