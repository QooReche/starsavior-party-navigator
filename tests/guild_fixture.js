// Test-only projection of the same module-backed source that build_party_html uses.
const path=require('node:path'),fs=require('node:fs');
const root=path.resolve(__dirname,'..');
function expand(v){
  if(Array.isArray(v))return v.map(expand);
  if(!v||typeof v!=='object')return v;
  const {$module,...rest}=v;
  return Object.fromEntries(Object.entries({...($module?read('data/boss_modules/'+$module+'.json'):{}),...rest}).map(([k,x])=>[k,expand(x)]));
}
function read(file){return JSON.parse(fs.readFileSync(path.join(root,file),'utf8'));}
module.exports=id=>expand(read('data/guild_seasons/'+id+'.json'));
