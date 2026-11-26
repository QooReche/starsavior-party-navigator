"""Real search planners + controlled workers; one actor through progress/result/cancel."""
import argparse
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
      for(const t of m.teams)stageQueue.push(()=>send({type:'team',key:t.key,result:{n:m.n_runs,clear:.8,prog:.9,progs:[.8,1],via:{},u:{},guild:{base_scores:Array(m.n_runs).fill(10000)},
        cosmo:{mean:10000,top:12000,n:m.n_runs,clear:.8,frac:.9}}}));
      stageQueue.push(()=>send({type:'done'}));
    }
    // Keep queued messages to exercise late replies after real cancellation.
    terminate(){this.dead=true;}
  };
  MI.brkLv={};
}'''


def flow(browser,base,width,kind,template=None):
    def setup(page):
        if template:page.route('**/index.html*',lambda r:r.fulfill(body=template,content_type='text/html'))
    p=ready(browser,base,width,info=FULL if kind=='guild' else account(),query='?pm=reco&season=force',setup=setup)
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
              CSR.optLearned=false;CSR.optLevel=3;renderCosmoSearch();
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
        jump=p.evaluate('''async () => {
          const box=()=>document.querySelector('.gwen-lane-actor').getBoundingClientRect().x,before=box();
          const was=GwenLane.mount().state.dir;stageRepeatPhase();
          return {before,after:box(),was,dir:GwenLane.mount().state.dir};
        }''')
        assert p.evaluate(f'{state}.done')==0
        # 단계 전환은 시작점 순간이동이 아니라 방향 반전(왕복): 화면상 위치가 그대로여야 함.
        assert abs(jump['after']-jump['before'])<=1,('same-text phase teleported',jump)
        assert jump['dir']==-jump['was'],('same-text phase did not reverse',jump)
        assert p.evaluate('document.querySelector(".gwen-lane-actor").dataset.direction')==('back' if jump['dir']<0 else 'forward')
        p.evaluate(f'while({state}.done<Math.max(1,Math.floor({state}.total*.3))&&stageQueue.length)stageStep()')
        p.wait_for_function('GwenLane.mount().state.x>0')
        jump=p.evaluate(f'''async () => {{
          const phase={state}.msg,box=()=>document.querySelector('.gwen-lane-actor').getBoundingClientRect().x;
          let before=box(),was=GwenLane.mount().state.dir;
          while({state}.msg===phase){{before=box();was=GwenLane.mount().state.dir;if(stageQueue.length)stageStep();else await new Promise(r=>setTimeout(r,0));}}
          return {{before,after:box(),was,dir:GwenLane.mount().state.dir}};
        }}''')
        assert p.evaluate(f'{state}.done')==0
        assert abs(jump['after']-jump['before'])<=1,('next search phase teleported',jump)
        assert jump['dir']==-jump['was'],('next search phase did not reverse',jump)
        p.evaluate(f'while({state}.done<Math.max(1,Math.floor({state}.total*.2))&&stageQueue.length)stageStep()')
        p.wait_for_function('GwenLane.mount().state.x>0')
        # Cancel, then deliver every queued obsolete reply before starting again.
        p.locator(f'{panel} [data-{prefix}=cancel]').click()
        p.evaluate('while(stageQueue.length)stageStep()')
        assert p.evaluate(f'{state}.phase')=='idle'
        assert p.locator(f'[data-gwen-slot="{mode}-board"] .gwen-lane-actor').count()==0
        # The result animation is consumed when its one-shot action starts (ux_ui.js show 'action' -> playedReports).
        p.evaluate(f'''() => {{window.resultPlayed=false;new MutationObserver(ms=>{{
          if(ms.some(m=>m.target.closest?.('[data-gwen-slot="{mode}-result"]')&&m.target.dataset.gwenPlaying==='true'))resultPlayed=true;
        }}).observe(document,{{subtree:true,attributes:true,attributeFilter:['data-gwen-playing']}});}}''')
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
        if kind=='cosmo':
            # 코스모: 그웬은 보스 카드 줄의 4번째 칸(합계 말풍선 옆), «수사 완료!» 는 카드 줄 바로 위
            assert p.evaluate('''() => {const r=document.querySelector('[data-gwen-slot="cosmoSearch-result"]'),say=document.querySelector('#cosmo-search [data-k=cs-best] .cg-summary .cg-say');
              return !!say&&say.contains(r)&&say.querySelector('.cg-say-bubble [data-k=cs-sum]')!=null}''')
            gap=p.evaluate('''() => {const b=document.querySelector('[data-gwen-slot="cosmoSearch-board"]').getBoundingClientRect(),c=document.querySelector('#cosmo-search .cg-summary').getBoundingClientRect(),
              r=document.querySelector('[data-gwen-slot="cosmoSearch-result"] img').getBoundingClientRect();return [c.top-b.bottom,b.height,r.top>=c.top-1&&r.bottom<=c.bottom+1]}''')
            assert 0<=gap[0]<=16 and gap[1]<=48 and gap[2],gap
        else:assert result().bounding_box()['y']<p.locator(f'{panel} [data-k=gs-best]').bounding_box()['y']
        # Wait until the one-shot action has actually started (or the art has no motion), then finished.
        # playing==="false" alone also held before the action began (common at 390px since f9ff4a2), so a
        # never-played animation was "replayed" on remount — a test race, not a product replay.
        p.wait_for_function(f'(i=>!!i&&(resultPlayed||!i.dataset.gwenMotion)&&i.dataset.gwenPlaying==="false")(document.querySelector(\'[data-gwen-slot="{mode}-result"] img\'))')
        announcements=result().locator('.gwen-lane-actor').get_attribute('data-announcements')
        p.evaluate('renderCosmoSearch()' if kind=='cosmo' else 'renderGuildSearch(true)')
        assert result().locator('.gwen-lane-actor').get_attribute('data-announcements')==announcements
        p.evaluate("directNavigate('direct');directNavigate('reco')")
        assert result().locator('.gwen-lane-actor').count()==1
        assert result().locator('.gwen-lane-actor').get_attribute('data-announcements')==announcements
        assert p.locator('.gwen-lane-actor').count()==1
        # Content changes destroy the component. Returning must retain both the
        # result object and the consumed announcement/animation, not just repaint.
        old_content=p.locator('#content').input_value()
        p.evaluate(f'window.savedSearchRows={state}.rows')
        p.select_option('#content',p.evaluate('String(contents.findIndex(c=>c.key==="op"))'))
        assert p.locator(f'[data-gwen-slot="{mode}-result"]').count()==0
        p.select_option('#content',old_content)
        assert p.evaluate(f'{state}.phase==="done" && {state}.rows===savedSearchRows'), 'content return lost completed search'
        result().scroll_into_view_if_needed()
        p.wait_for_function(f'document.querySelector(\'[data-gwen-slot="{mode}-result"] img\')?.naturalWidth>0')
        assert result().locator('.gwen-lane-actor').get_attribute('data-announcements')==announcements, 'remount repeated result announcement'
        p.wait_for_timeout(300)
        assert result().locator('img').get_attribute('data-gwen-playing')=='false', 'remount replayed result animation'
        p.screenshot(path=str(OUT/f'{kind}-result-{width}.png'))
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not p.errors,p.errors
    finally:
        p.evaluate('stageAuto=false')
        p.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',action='store_true');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);ACCOUNT_OUT.mkdir(parents=True,exist_ok=True)
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in (1280,390):
                for kind in ('cosmo','guild'):
                    flow(browser,base,width,kind)
                    print(f'PASS {kind} {width}: progress, cancel, stale replies, result, rebind, navigation',flush=True)
            if args.mutations:
                html=(ROOT/'index.html').read_text(encoding='utf-8')
                old='if(GSR.phase==="run"){GSR.phase="idle";GSR.id++}GwenStage.destroy'
                assert old in html
                try:flow(browser,base,1280,'guild',html.replace(old,'GSR.phase="idle";GSR.id++;GwenStage.destroy'))
                except AssertionError as e:
                    assert 'content return lost completed search' in str(e),str(e)
                    print('CAUGHT completed search reset on destroy',flush=True)
                else:raise AssertionError('destroy mutation survived')
                flow(browser,base,1280,'guild')
                print('PASS restored destroy/remount',flush=True)
        finally:browser.close()
