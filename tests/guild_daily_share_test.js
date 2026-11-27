// A daily share/auto entry must never reserve or launch the legacy recommendation.
const assert=require('node:assert/strict'),vm=require('node:vm');
const {readSrc,cut}=require('./helpers/page');
const page=readSrc('party_template.html');
function check(src=page){
  for(const auto of [false,true])for(const shared of [false,true]){
    let work=0;
    const elements={content:{value:0},stage:{value:0},out:{innerHTML:'old'},'control-home':{append(){}}};
    const c={D:{guild:{search:{preset:'daily'}}},contents:[{key:'guild'}],DIRECT:{mode:'reco'},$:id=>elements[id],
      MI:{info:{}},RECO:{timer:null,revision:0,sharedPending:shared},AUTO:auto,REQ:false,SIMQ:{},LASTQ:{},_rt:null,
      cur:[{}],recoClearTimer(){c.RECO.timer=null;},clearTimeout(){},setTimeout(){work++;return 1;},simInvalidate(){},
      seasonBlocked:()=>false,directRefresh(){},seasonPaint(){},growthControlPlace(){},SCORE_CONTROLS:{},GRAPH_WRAP:{},renderChip(){},renderMi(){},
      raidUi:()=>false,runCore(){work++;},guildGwenClaim(){work++;}};
    vm.createContext(c);
    vm.runInContext(cut(src,'const guildDailyUi=','function refreshTabs')+cut(src,'function condChanged()','function miEmpty')+
      cut(src,'function showReco()','function recoCandidates'),c);
    c.condChanged();c.showReco();
    assert.equal(work,0);assert.equal(c.RECO.timer,null);assert.equal(c.REQ,false);assert.equal(elements.out.innerHTML,'');
  }
}
check();
assert.throws(()=>check(page.replace("&&!guildDailyUi(contents[$('content').value])&&(AUTO",'&&(AUTO')));
console.log('PASS daily share/auto reservation and execution guards; reservation mutation killed');
