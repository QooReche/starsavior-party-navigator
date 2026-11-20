"""Actual page transport and persisted rear-row leader, using synthetic worker scores."""
from playwright.sync_api import sync_playwright
from test_direct_party import ready, enter, pick_four
from test_page import test_server

FAKE = """(() => {
window.layoutPosts=[];window.layoutDelay=10;
window.Worker=class {
 postMessage(m){layoutPosts.push(m);const send=x=>{if(!this.dead)this.onmessage({data:{id:m.id,requestId:m.requestId,job:m.job,jobId:m.jobId,owner:m.owner,revision:m.revision,...x}})};
 send({type:'stage',msg:'준비 끝'});
 setTimeout(async()=>{const ver=(await fetch('sim/manifest.json').then(r=>r.json())).ver;
 for(const t of m.teams){const keys=t.party.units.map(u=>u.key),best=keys.slice().sort().at(-1),score=keys[t.party.leader]===best?1:.2;
 send({type:'team',key:t.key,result:{ver,n:m.n_runs,clear:score,t60:score,prog:.8,progs:[.8],via:{},cosmo:{mean:score*100,top:score*100,clear:score,frac:.8}}});}
 send({type:'done'});},layoutDelay);
 }
 terminate(){this.dead=true;}
};})();"""


def flow(browser, base):
    p=ready(browser,base,setup=lambda p:p.add_init_script(FAKE))
    enter(p);pick_four(p)
    original=p.evaluate('JSON.stringify(DIRECT.draft)')
    p.locator('#direct-arrange').click()
    p.wait_for_function('layoutPosts.length===24 && !DIRECT.placement')
    assert p.evaluate("DIRECT.draft.leader===DIRECT.draft.slots.map(m=>m.key).sort().at(-1)")
    assert p.evaluate("DIRECT.draft.slots.findIndex(m=>m.key===DIRECT.draft.leader)>=2")
    assert p.evaluate('layoutPosts.every(m=>m.teams[0].party.units.every(u=>u.stats_final))')
    saved=p.evaluate('JSON.stringify(DIRECT.draft)')
    p.evaluate('layoutDelay=2000;layoutPosts=[]')
    p.locator('#direct-arrange').click();p.wait_for_function('!!DIRECT.placement')
    p.locator('#direct-arrange').click();p.wait_for_function('!DIRECT.placement')
    assert p.evaluate('JSON.stringify(DIRECT.draft)')==saved
    p.reload();p.wait_for_function('window._ready && DIRECT.slots')
    assert p.evaluate('JSON.stringify(DIRECT.draft)')==saved
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
    p.wait_for_function('CDIRECT.state && MI.growth')
    p.evaluate("""() => {layoutPosts=[];layoutDelay=10;const b=CDIRECT.state.active;
      const keys=R.filter(r=>MI.info.units.some(u=>u.id===r.uid)).slice(0,4).map(r=>r.key);
      keys.forEach((key,slot)=>cdChange({type:'draft',boss:b,action:{type:'put',key,slot}}));
    }""")
    p.locator('[data-cd-act=arrange]').click()
    p.wait_for_function('layoutPosts.length===24 && !CDIRECT.placement')
    assert p.evaluate("(()=>{const d=CDIRECT.state.teams[CDIRECT.state.active].draft;return d.leader===d.slots.map(m=>m.key).sort().at(-1)&&d.slots.findIndex(m=>m.key===d.leader)>=2})()")
    expected=p.evaluate('JSON.stringify(CosmoDirect.share(CDIRECT.state))')
    p.goto(p.evaluate('shareUrl()'));p.wait_for_function('window._ready && CDIRECT.state')
    assert p.evaluate('JSON.stringify(CosmoDirect.share(CDIRECT.state))')==expected
    assert not p.errors,p.errors
    p.close()


if __name__=='__main__':
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:flow(browser,base);print('PASS placement page: 24 actual jobs, final stats, rear leader, cancel, storage, cosmo share')
        finally:browser.close()
