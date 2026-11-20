// Supplement from the immutable pre-extraction commit, never from current implementation.
const fs=require('node:fs'),assert=require('node:assert/strict'),{runtime,normalize}=require('./search_freeze_test');
const file=require('node:path').join(__dirname,'fixtures/search_screen_6688d7a.json');
(async()=>{
 if(process.argv.includes('--capture'))fs.writeFileSync(file,JSON.stringify(normalize(await runtime({legacy:true,screen:true})),null,2)+'\n');
 const expected=JSON.parse(fs.readFileSync(file,'utf8')),actual=normalize(await runtime({screen:true}));
 assert.deepEqual(actual,expected);
 const mutated=structuredClone(actual);mutated.trace.find(m=>m.n_runs===24).teams[0].options.run_offset=0;
 assert.throws(()=>assert.deepEqual(mutated,expected));
 console.log('PASS immutable pre-extraction screen: 8/32 runs, raw merge, promotion/order, 2-party/direct/cache; offset mutation');
})().catch(e=>{console.error(e);process.exitCode=1;});
