'use strict';
const assert=require('node:assert/strict'),cp=require('node:child_process'),path=require('node:path');
const {battleScores}=require('../tools/evaluate_guild_time');
for(const season of [30112,30111]){
 const G=require('./guild_fixture')(season),id=17;
 const m={id,stage:'guild/test/7단계 EX',n_runs:2,seed:999999,teams:[{key:'contract',party:{units:['asherah-voyager','luna','carnelia','smile'].map(key=>({key,build:'standard'})),leader:0},options:{guild:{seasonId:season,dataVersion:G.dataVersion,level:0,sets:[0,0,0,0],support:'none'}}}]};
 const raw=cp.execFileSync('python',['-X','utf8','-I','tools/bench_cosmo_search.py','--worker'],{cwd:path.resolve(__dirname,'..'),input:JSON.stringify(m)+'\n',encoding:'utf8'});
 const rows=raw.trim().split('\n').map(JSON.parse);assert.deepEqual(rows.map(r=>r.type),['team','done'],raw);assert(rows.every(r=>r.id===id));
 const r=rows[0].result;assert.equal(r.progs.length,2);assert.equal(battleScores(G,{level:0},[0,0,0,0],r).length,2);
}
console.log('PASS native guild worker: request IDs, two seasons, per-battle score fields');
