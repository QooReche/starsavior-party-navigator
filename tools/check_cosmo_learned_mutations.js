// In-memory source mutation: never edits the working tree implementation.
const {spawnSync}=require('node:child_process');
const mutations=[['M','for(const k of keys)per.get(k).put(e);',''],
 ['overlap','if(!c.overlapStarts||!c.overlapKeep)return;','return;'],
 ['audit','fallback:rho===null||rho<c.minCorrelation||core.length!==scores.length||samples.length!==expected||rate>c.missThreshold','fallback:false']];
for(const [name,from,to] of mutations){const code=`const fs=require('node:fs'),Module=require('node:module'),old=Module._extensions['.js'];Module._extensions['.js']=(m,f)=>{if(!f.endsWith('cosmo_learned.js'))return old(m,f);const s=fs.readFileSync(f,'utf8');if(!s.includes(${JSON.stringify(from)}))throw Error('mutation anchor missing');m._compile(s.replace(${JSON.stringify(from)},${JSON.stringify(to)}),f);};require('./tests/cosmo_learned_test.js');`;
 const p=spawnSync(process.execPath,['-e',code],{encoding:'utf8',timeout:120000});if(p.status===0||p.error||p.stderr.includes('mutation anchor missing'))throw Error('mutation not detected: '+name+' '+p.stderr);console.log('PASS mutation rejected: '+name+' '+p.stderr.split('\n')[0]);}
