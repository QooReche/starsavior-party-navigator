// Node 산출물도 UTF-8·LF로 완성한 임시 파일을 같은 디렉터리에서 교체함.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function atomicText(destination,text){
 fs.mkdirSync(path.dirname(destination),{recursive:true});
 const tmp=destination+'.'+crypto.randomUUID()+'.tmp';
 try{fs.writeFileSync(tmp,text.replace(/\r\n?/g,'\n'),{encoding:'utf8',flag:'wx'});fs.renameSync(tmp,destination)}
 finally{if(fs.existsSync(tmp))fs.unlinkSync(tmp)}
}
module.exports={atomicText};
