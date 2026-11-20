"""Synthetic account/worker: learned switch, progress, completion and direct import."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server, Ctx, open_page, settle, open_fold, wait_myinfo

ROOT = Path(__file__).resolve().parents[2]


def flow(browser, ctx, expanded=False):
    p = open_page(browser, ctx, raid_ui=True)
    p.select_option('#content', p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
    settle(p)
    open_fold(p, 'cs-options')
    assert p.locator('#cosmo-search [data-cs=learned]').is_checked()
    for enabled in (False, True):
        p.locator('#cosmo-search [data-cs=learned]').set_checked(enabled)
        assert p.evaluate("LS.get('cosmo.learned')") is enabled
        p.reload()
        wait_myinfo(p)
        p.select_option('#content', p.evaluate("String(contents.findIndex(c=>c.key==='cosmo'))"))
        settle(p)
        open_fold(p, 'cs-options')
        assert p.locator('#cosmo-search [data-cs=learned]').is_checked() is enabled
        assert p.evaluate('CSR.optLearned') is enabled
    p.evaluate("""() => {
      const S=D.cosmoRaid.search;
      const pool=CosmoSearch.poolAll(S,csProfile().results,R).slice(0,16);
      for(const r of R)if(!pool.some(x=>x.key===r.key))EXCL.add(r.key);
      S.workers.max=2;S.screen={firstRuns:1,runs:2,passFrac:.1,passMinMult:1};
      ownedSimBreaks=()=>[{name:'특이점 관측',level:3},{name:'큐브 과부하',level:5}];
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
    if expanded:
        p.evaluate('D.cosmoRaid.search.maxCombos=100;D.cosmoRaid.search.learned.minCorrelation=1')
    open_fold(p, 'cs-options')
    checkbox=p.locator('#cosmo-search [data-cs=learned]')
    assert checkbox.is_checked()
    checkbox.uncheck()
    assert p.evaluate('!CSR.optLearned && D.cosmoRaid.search.learned.value')
    checkbox.check()
    assert p.evaluate('CSR.optLearned && D.cosmoRaid.search.learned.value')
    p.select_option('#cosmo-search [data-cs=level]', '6')
    p.click('#cosmo-search [data-cs=start]')
    p.wait_for_function("CSR.phase==='run' && CSR.msg.includes('표본 학습')")
    assert '표본 학습' in p.locator('#cosmo-search [data-k=cs-prog]').inner_text()
    p.wait_for_function("CSR.phase==='done' || CSR.phase==='err'", timeout=120000)
    assert p.evaluate("CSR.phase==='done' && CSR.learned && CSR.rows[0].sum>0"), p.evaluate('CSR.msg')
    assert p.evaluate("learnedMessages.some(s=>s.includes('예측 채점'))")
    assert p.evaluate("D.cosmoRaid.bosses.every(b=>learnedMessages.some(s=>s.includes(b.name)))")
    assert p.evaluate("D.cosmoRaid.bosses.every(b=>learnedMessages.every(s=>!s.includes(b.key)))")
    assert p.evaluate("learnedMessages.some(s=>s.includes('예측 채점') && /[0-9],[0-9]{3}/.test(s))")
    if expanded:
        assert p.evaluate("learnedMessages.some(s=>s.includes('후보 확대 복귀')) && CSR.audit.every(a=>a.expanded)")
        assert p.locator('#cosmo-search [data-k=cs-expanded]').count()==3
        assert '이 보스는 예측 확인이 부족해 후보를 넓혀 찾았음' in p.locator('#cosmo-search [data-k=cs-expanded]').first.inner_text()
    assert p.evaluate('new Set(CSR.rows[0].teams.flatMap(t=>t.keys)).size===12')
    assert p.locator('#cosmo-search [data-k=cs-best] [data-k=cs-team]').count()==3
    assert p.evaluate('CSR.rows[0].teams.every(t=>t.brkTie===true && t.brk===null)')
    bars=p.locator('#cosmo-search [data-k=cs-best] [data-k=cs-team] .bbar')
    assert bars.count()==3
    assert all('브레이크 스킬: 점수 차이 없음(아무거나 장착 가능)' in text for text in bars.all_text_contents())
    p.evaluate('window.learnedBest=CSR.rows[0]')
    p.locator('#cosmo-search [data-k=cs-best] [data-cs=edit]').click()
    assert p.locator('#cosmo-direct-panel').is_visible()
    assert p.evaluate('JSON.stringify(CDIRECT.state)===JSON.stringify(CosmoDirect.fromSearch(learnedBest,cdSeason()))')
    assert p.evaluate('Object.values(CDIRECT.state.teams).every(t=>t.draft.brk===null)')
    assert not ctx.errors, ctx.errors
    p.close()


if __name__ == '__main__':
    out=ROOT/'local/cosmo-learned-e2e'
    out.mkdir(parents=True,exist_ok=True)
    with test_server() as base, sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            flow(browser,Ctx(base,str(out)))
            print('PASS learned default/switch/progress/result/direct import')
            flow(browser,Ctx(base,str(out)),expanded=True)
            print('PASS learned expanded fallback/notice/direct import')
        finally:
            browser.close()
