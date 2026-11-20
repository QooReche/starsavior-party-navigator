"""Real search planners + controlled workers; one actor through progress/result/cancel."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server, FULL
from test_direct_party import ready
from test_cosmo_direct import account, OUT as ACCOUNT_OUT

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'local/gwen-search'
FAKE='''() => {
  window.stageQueue=[];window.stageAuto=false;window.stagePosts=[];
  for(const engine of [CosmoSearch,GuildPlanner]){
    const search=engine.search;
    engine.search=opts=>{
      const onPhase=opts.onPhase;let last;
      opts.onPhase=(...args)=>{last=args;onPhase(...args);};
      window.stageRepeatPhase=()=>onPhase(...last);
      return search(opts);
    };
  }
  window.stageStep=()=>{const f=stageQueue.shift();if(f)f();};
  window.stageFlush=()=>{stageAuto=true;const next=()=>{for(let i=0;i<100&&stageQueue.length;i++)stageStep();if(stageAuto)setTimeout(next,10);};next();};
  window.Worker=class {
    postMessage(m){stagePosts.push(m);const send=data=>this.onmessage?.({data:{id:m.id,...data}});
      for(const t of m.teams)stageQueue.push(()=>send({type:'team',key:t.key,result:{n:m.n_runs,clear:.8,prog:.9,progs:[.8,1],via:{},u:{},
        cosmo:{mean:10000,top:12000,n:m.n_runs,clear:.8,frac:.9}}}));
      stageQueue.push(()=>send({type:'done'}));
    }
    // Keep queued messages to exercise late replies after real cancellation.
    terminate(){this.dead=true;}
  };
  MI.brkLv={};
}'''


def flow(browser,base,width,kind):
    p=ready(browser,base,width,info=FULL if kind=='guild' else account(),query='?pm=reco&season=force')
    p.select_option('#content',p.evaluate('k=>String(contents.findIndex(c=>c.key===k))',kind))
    mode='cosmoSearch' if kind=='cosmo' else 'guildSearch'
    state='CSR' if kind=='cosmo' else 'GSR'
    panel='#cosmo-search' if kind=='cosmo' else '#guild-search'
    prefix='cs' if kind=='cosmo' else 'gs'
    def board():return p.locator(f'[data-gwen-slot="{mode}-board"]')
    def result():return p.locator(f'[data-gwen-slot="{mode}-result"]')
    try:
        p.evaluate(FAKE)
        if kind=='cosmo':
            p.evaluate('''() => {
              const S=D.cosmoRaid.search,pool=CosmoSearch.poolAll(S,csProfile().results,R).slice(0,12);
              if(pool.length!==12)throw Error('synthetic pool needs 12');
              for(const r of R)if(!pool.some(x=>x.key===r.key))EXCL.add(r.key);
              S.workers.max=1;S.screen={runs:1};S.rerank={keep:495,runs:2};S.final.runs=2;S.combine={topTriples:1,show:1};
              CSR.optLearned=false;CSR.optFast=false;CSR.optLevel=3;renderCosmoSearch();
            }''')
        else:
            p.evaluate('''() => {
              const S=D.guild.search;
              Object.assign(S,{poolSize:5,minPowerRatio:0,minRole:{},minFront:0,minDealer:0,screen2:{keep:5,runs:2},finalists:5});
              S.screen.runs=2;S.final.runs=2;S.final.levels=[4];S.final.supports=['fire'];renderGuildSearch(true);
            }''')
        start=f'{panel} [data-{prefix}=start]'
        p.locator(start).click()
        p.wait_for_function(f'stageQueue.length>0 || {state}.phase==="err"')
        assert p.evaluate('stageQueue.length>0'),p.evaluate(f'[{state}.phase,{state}.msg]')
        # A completed worker team must update both the existing N/M label and movement.
        p.evaluate(f'while({state}.done<Math.max(1,Math.floor({state}.total*.2))&&stageQueue.length)stageStep()')
        p.wait_for_function(f'{state}.done>0 && {state}.total>{state}.done')
        board().scroll_into_view_if_needed()
        p.wait_for_function(f'GwenLane.mount().state.mode==="{mode}" && GwenLane.mount().state.x>0')
        assert board().locator('.gwen-lane-actor').count()==1
        assert p.locator('.gwen-lane-actor').count()==1
        p.evaluate('window.stageActor=document.querySelector(".gwen-lane-actor")')
        p.screenshot(path=str(OUT/f'{kind}-work-{width}.png'))
        # Different bosses can emit identical phase text. Exercise the real page callback.
        p.evaluate('stageRepeatPhase()')
        assert p.evaluate(f'{state}.done')==0
        assert p.evaluate('GwenLane.mount().state.x')==0,'same-text phase retained previous position'
        p.evaluate(f'while({state}.done<Math.max(1,Math.floor({state}.total*.3))&&stageQueue.length)stageStep()')
        p.wait_for_function('GwenLane.mount().state.x>0')
        p.evaluate(f'''async () => {{
          const phase={state}.msg;
          while({state}.msg===phase){{
            if(stageQueue.length)stageStep();else await new Promise(r=>setTimeout(r,0));
          }}
        }}''')
        assert p.evaluate(f'{state}.done')==0
        assert p.evaluate('GwenLane.mount().state.x')==0,'next search phase retained previous position'
        p.evaluate(f'while({state}.done<Math.max(1,Math.floor({state}.total*.2))&&stageQueue.length)stageStep()')
        p.wait_for_function('GwenLane.mount().state.x>0')
        # Cancel, then deliver every queued obsolete reply before starting again.
        p.locator(f'{panel} [data-{prefix}=cancel]').click()
        p.evaluate('while(stageQueue.length)stageStep()')
        assert p.evaluate(f'{state}.phase')=='idle'
        assert p.locator(f'[data-gwen-slot="{mode}-board"] .gwen-lane-actor').count()==0
        p.locator(start).click()
        p.wait_for_function('stageQueue.length>0')
        p.evaluate('stageFlush()')
        p.wait_for_function(f'{state}.phase==="done" || {state}.phase==="err"',timeout=60000)
        assert p.evaluate(f'{state}.phase')=='done',p.evaluate(f'{state}.msg')
        assert p.evaluate(f'{state}.rows.length>0')
        result().scroll_into_view_if_needed()
        p.wait_for_function(f'document.querySelector(\'[data-gwen-slot="{mode}-result"] img\')?.naturalWidth>0')
        assert board().locator('.gwen-lane-actor').count()==0
        assert board().locator('.gwen-stage-banner').is_visible()
        assert board().locator('span[data-phrase=inquiry]').is_visible()
        assert result().locator('.gwen-lane-actor').count()==1
        assert p.locator('.gwen-lane-actor').count()==1
        assert p.evaluate('stageActor===document.querySelector(".gwen-lane-actor")')
        assert result().bounding_box()['y']<p.locator(f'{panel} [data-k={"cs-best" if kind=="cosmo" else "gs-best"}]').bounding_box()['y']
        p.wait_for_function(f'document.querySelector(\'[data-gwen-slot="{mode}-result"] img\')?.dataset.gwenPlaying==="false"')
        announcements=result().locator('.gwen-lane-actor').get_attribute('data-announcements')
        p.evaluate('renderCosmoSearch()' if kind=='cosmo' else 'renderGuildSearch(true)')
        assert result().locator('.gwen-lane-actor').get_attribute('data-announcements')==announcements
        p.evaluate("directNavigate('direct');directNavigate('reco')")
        assert result().locator('.gwen-lane-actor').count()==1
        assert result().locator('.gwen-lane-actor').get_attribute('data-announcements')==announcements
        assert p.locator('.gwen-lane-actor').count()==1
        p.screenshot(path=str(OUT/f'{kind}-result-{width}.png'))
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not p.errors,p.errors
    finally:
        p.evaluate('stageAuto=false')
        p.close()


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);ACCOUNT_OUT.mkdir(parents=True,exist_ok=True)
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in (1280,390):
                for kind in ('cosmo','guild'):
                    flow(browser,base,width,kind)
                    print(f'PASS {kind} {width}: progress, cancel, stale replies, result, rebind, navigation',flush=True)
        finally:browser.close()
