"""Synthetic account/worker: learned switch, progress, completion and direct import."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server, Ctx, open_page, settle, open_fold

ROOT = Path(__file__).resolve().parents[2]


def flow(browser, ctx):
    p = open_page(browser, ctx, raid_ui=True)
    p.select_option('#content', p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
    settle(p)
    p.evaluate("""() => {
      const S=D.cosmoRaid.search;
      const pool=CosmoSearch.poolAll(S,csProfile().results,R).slice(0,16);
      for(const r of R)if(!pool.some(x=>x.key===r.key))EXCL.add(r.key);
      S.workers.max=2;S.screen={firstRuns:1,runs:2,passFrac:.1,passMinMult:1};
      S.rerank={keep:30,runs:2};S.final.runs=2;S.combine={topTriples:3,show:3};
      Object.assign(S.learned,{S:160,m:2,K:60,M:2,A:20,overlapStarts:3,overlapKeep:2,minCorrelation:-1,missThreshold:1});
      window.learnedMessages=[];const search=CosmoSearch.search;
      CosmoSearch.search=cx=>search({...cx,onPhase:(m,t,i)=>{learnedMessages.push(m);cx.onPhase(m,t,i);}});
      window.Worker=class {terminate(){this.dead=true;}postMessage(m){setTimeout(()=>{
        if(this.dead)return;for(const t of m.teams){const v=10000+t.party.units.reduce((s,u)=>s+pool.findIndex(r=>r.key===u.key)*31,0);
          this.onmessage({data:{type:'team',id:m.id,key:t.key,result:{n:m.n_runs,prog:.8,progs:[.8],via:{},cosmo:{mean:v,top:v+100,n:m.n_runs,clear:.2,frac:.8}}}});}
        this.onmessage({data:{type:'done',id:m.id}});
      },80);}};renderCosmoSearch();
    }""")
    open_fold(p, 'cs-options')
    checkbox=p.locator('#cosmo-search [data-cs=learned]')
    assert not checkbox.is_checked()
    checkbox.check()
    assert p.evaluate('CSR.optLearned && !D.cosmoRaid.search.learned.value')
    p.select_option('#cosmo-search [data-cs=level]', '6')
    p.click('#cosmo-search [data-cs=start]')
    p.wait_for_function("CSR.phase==='run' && CSR.msg.includes('표본 학습')")
    assert '표본 학습' in p.locator('#cosmo-search [data-k=cs-prog]').inner_text()
    p.wait_for_function("CSR.phase==='done' || CSR.phase==='err'", timeout=120000)
    assert p.evaluate("CSR.phase==='done' && CSR.learned && CSR.rows[0].sum>0"), p.evaluate('CSR.msg')
    assert p.evaluate("learnedMessages.some(s=>s.includes('예측 채점'))")
    assert p.evaluate('new Set(CSR.rows[0].teams.flatMap(t=>t.keys)).size===12')
    assert p.locator('#cosmo-search [data-k=cs-best] [data-k=cs-team]').count()==3
    p.evaluate('window.learnedBest=CSR.rows[0]')
    p.locator('#cosmo-search [data-k=cs-best] [data-cs=edit]').click()
    assert p.locator('#cosmo-direct-panel').is_visible()
    assert p.evaluate('JSON.stringify(CDIRECT.state)===JSON.stringify(CosmoDirect.fromSearch(learnedBest,cdSeason()))')
    assert not ctx.errors, ctx.errors
    p.close()


if __name__ == '__main__':
    out=ROOT/'local/cosmo-learned-e2e'
    out.mkdir(parents=True,exist_ok=True)
    with test_server() as base, sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            flow(browser,Ctx(base,str(out)))
            print('PASS learned switch/progress/result/direct import')
        finally:
            browser.close()
