"""Automatic result placement and actual screening callback; browser geometry + mutations."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server

ROOT = Path(__file__).resolve().parents[2]


def lane_audit(page, reduced=False):
    lane = page.locator('#reco-board-lane')
    lane.scroll_into_view_if_needed()
    actor = lane.locator('.gwen-lane-actor')
    assert actor.count() == 1, 'automatic work actor missing'
    page.wait_for_function('GwenLane.mount().state.phase==="work"')
    a, b = actor.bounding_box(), lane.bounding_box()
    assert b['x']-.5 <= a['x'] and a['x']+a['width'] <= b['x']+b['width']+.5, 'actor outside lane'
    assert b['y'] <= a['y'] and a['y']+a['height'] <= b['y']+b['height']+.5
    assert page.locator('#out .gwen-lane-actor').count() == 0
    if reduced:
        assert not page.evaluate('GwenLane.mount().state.moving')
        page.wait_for_function('document.querySelector("#reco-board-lane .gwen-lane-image").currentSrc.endsWith(".png")')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


def speech_audit(page):
    lane = page.locator('#reco-board-lane')
    lane.scroll_into_view_if_needed()
    # Force a long speech line and measure in one task so the controller cannot hide it between reads.
    a,b=lane.evaluate("""lane=>{const e=lane.querySelector('.gwen-lane-speech');e.hidden=false;
      e.textContent='끝까지 확인할 테니 나만 믿어! 단장님, 조금만 기다려!';
      return [e.getBoundingClientRect().toJSON(),lane.getBoundingClientRect().toJSON()]}""")
    assert a['height']>0, 'speech path not exercised'
    assert b['y'] <= a['y'] and a['bottom'] <= b['bottom'], 'speech clipped vertically'



def ready(page, base):
    page.goto(base+'/index.html?season=force&pm=reco', wait_until='networkidle')
    page.wait_for_function('window._ready && QK.d')
    page.evaluate('''() => {recoClearTimer();clearTimeout(_rt);SIMQ.auto=false;SIMQ.kick=false;localStorage.setItem('pn.simauto','0');
      REQ=true;RECO.standard=true;document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();run(true);
      window.autoStage=cur[$('stage').value];
    }''')


def screening(page):
    # Keep the production simScreen producer, sequence, callback and DOM updater.
    # Replace only dispatch/worker timing, delivering completed teams explicitly.
    page.evaluate('''() => {
      simWatch=()=>()=>{};scrPool=()=>[];simDispatch=(ws,keys,handlers)=>{window.autoJobs=keys;window.autoHandlers=handlers};
      SIMQ.kick=true; // Match the real recommendation button's requested run.
      if(!simScreen(1))throw Error('screening did not start');
      $('out').innerHTML=simProgress(autoStage);
      run(true); // A late data/condition repaint must retain this running stage.
    }''')
    speech_audit(page)
    page.evaluate('''() => {const n=Math.max(1,Math.ceil(autoJobs.length*.8));
      for(const key of autoJobs.slice(0,n))autoHandlers.team(key,{result:{clear:.5,prog:.7,progs:[.7],via:{}}},{_t:0});
    }''')
    values = page.locator('#out [role=progressbar]').evaluate('e=>[+e.ariaValueNow,+e.ariaValueMax,e.querySelector("i").style.width]')
    assert values[0] > 0 and values[1] > values[0], 'screening progress/aria not delivered'
    assert float(values[2].rstrip('%')) > 0, 'screening bar not delivered'
    page.wait_for_timeout(800)
    assert page.evaluate('GwenLane.mount().state.x') > 0, 'screening progress not delivered to lane'
    lane_audit(page)


def result_audit(page):
    page.evaluate('''() => {SIMQ.busy=null;SIMQ.screening=false;SIMQ.kick=false;
      for(const box of Object.values(LASTQ))for(const t of box.rows)
        SIMQ.res[simSig(autoStage,t)]={n:100,clear:.96,ci:[.91,.99],ta:35,ttk:35,frac:1,u:Object.fromEntries(t.keys.map(k=>[k,[.25,0]]))};
      run(true);
    }''')
    portrait = page.locator('#out .gwen-reaction')
    assert portrait.count() == 1, 'one automatic result portrait required'
    assert portrait.evaluate('e=>e.parentElement.classList.contains("result-summary")'), 'portrait outside summary'
    assert portrait.evaluate('e=>e===e.parentElement.lastElementChild'), 'portrait must follow verdict and simulation summary'
    assert page.locator('#reco-gwen-stage .gwen-lane-actor').count() == 0, 'duplicate result lane actor'
    page.evaluate("GwenLane.registerStage('reco',{resultExternal:true,board:$('reco-board-lane'),result:$('reco-result-lane'),banner:$('reco-lane-banner')})")
    assert page.locator('#reco-gwen-stage .gwen-lane-actor').count() == 0, 'result rebind restored lane actor'
    assert page.locator('#reco-lane-banner').is_visible(), 'completion banner missing'
    portrait.scroll_into_view_if_needed()
    page.wait_for_function('document.querySelector("#out .gwen-reaction img").dataset.gwenLoaded==="true"')
    assert abs(portrait.locator('img').bounding_box()['height']-(240 if page.viewport_size['width']>=1200 else 112))<1
    art = portrait.get_attribute('data-gwen-reaction')
    assert art in ['st_verdict','st_cheer','st_ok','st_reach']
    page.wait_for_timeout(2100)
    page.evaluate('run(true)')
    portrait.scroll_into_view_if_needed()
    page.wait_for_timeout(150)
    assert portrait.is_visible() and portrait.get_attribute('data-gwen-reaction') == art
    assert portrait.locator('img').get_attribute('data-gwen-playing') == 'false', 'result reaction replayed'
    page.evaluate('''() => {window.autoScore={score:100};$('out').innerHTML='<div class="result-summary">'+Ux.gwenReaction(undefined,autoScore)+'</div>';recoGwenShow(false,null,autoScore)}''')
    assert page.locator('#out .gwen-reaction').get_attribute('data-gwen-reaction') == 'st_point', 'score must be neutral'
    assert page.locator('#reco-gwen-stage .gwen-lane-actor').count() == 0
    page.evaluate("const q=$('gwen-quiet');q.checked=true;q.dispatchEvent(new Event('change'))")
    assert page.locator('#reco-gwen-stage .gwen-lane-actor').count() == 0, 'quiet restored result lane actor'
    page.evaluate('''() => {window.autoQuietPlayed=false;
      new MutationObserver(()=>{if(document.querySelector('#out .gwen-reaction img')?.dataset.gwenPlaying==='true')autoQuietPlayed=true})
        .observe($('out'),{subtree:true,attributes:true,attributeFilter:['data-gwen-playing']});
      window.autoQuietResult={clear:.9};$('out').innerHTML='<div class="result-summary">'+Ux.gwenReaction(.9,autoQuietResult)+'</div>';
    }''')
    portrait.scroll_into_view_if_needed()
    page.wait_for_function('document.querySelector("#out .gwen-reaction img").dataset.gwenLoaded==="true"')
    page.wait_for_timeout(500)
    assert not page.evaluate('autoQuietPlayed'), 'quiet result reaction played'
    assert portrait.locator('.gwen-bubble').count()==1 and not portrait.locator('.gwen-bubble').is_visible(), 'quiet result speech visible'


def run(browser, base, width=390, variant=None, audit=None):
    ctx = browser.new_context(viewport={'width':width,'height':950})
    if variant:
        file, old, new = variant
        source = (ROOT/file).read_text(encoding='utf-8')
        assert old in source, (file, old)
        ctx.route('**/'+file+'*', lambda r:r.fulfill(body=source.replace(old,new),content_type='text/html' if file.endswith('html') else 'text/css' if file.endswith('css') else 'application/javascript'))
    page=ctx.new_page()
    try:
        ready(page,base)
        if audit == 'result':
            result_audit(page)
        else:
            screening(page)
            if audit is None:result_audit(page)
    finally:ctx.close()


if __name__ == '__main__':
    with test_server() as base, sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in [390,1280]:
            run(browser,base,width);print('PASS auto result/screening/speech',width,flush=True)
        cases=[
            ('summary placement',('index.html','${simBar(p,rows,st,uniq>rows.length,shown)}${p===1?Ux.gwenReaction','</div><div>${simBar(p,rows,st,uniq>rows.length,shown)}${p===1?Ux.gwenReaction'),'result','portrait outside summary'),
            ('summary order',('index.html','${simBar(p,rows,st,uniq>rows.length,shown)}${p===1?Ux.gwenReaction(SIMQ.res[simSig(st,shown)]?.clear,SIMQ.res[simSig(st,shown)]):""}','${p===1?Ux.gwenReaction(SIMQ.res[simSig(st,shown)]?.clear,SIMQ.res[simSig(st,shown)]):""}${simBar(p,rows,st,uniq>rows.length,shown)}'),'result','portrait must follow verdict'),
            ('result actor',('index.html','resultExternal:true,','resultExternal:false,'),'result','duplicate result lane actor'),
            ('result rebind',('gwen_lane.js',"if(stages.get(mode)?.resultExternal&&current.phase==='result'){render(current);return;}",''),'result','result rebind restored lane actor'),
            ('quiet result stage',('gwen_lane.js',"if(stages.get(current.mode)?.resultExternal&&current.phase==='result'){render(current);return;}",''),'result','quiet restored result lane actor'),
            ('quiet result reaction',('ux_ui.js',"media.matches||(img.hasAttribute('data-gwen-managed')&&doc.documentElement.dataset.gwenQuiet==='true')","media.matches"),'result','quiet result reaction played'),
            ('quiet result speech',('ux_ui.js',"report?.done||report&&img.hasAttribute('data-gwen-managed')&&doc.documentElement.dataset.gwenQuiet==='true'","report?.done"),'result','quiet result speech visible'),
            ('screen callback',('index.html','const pv=document.querySelector(\'[data-k="progress"]\');if(pv)simProgressSync(pv,st)},','/* mutation: lost callback update */ },'),'screen','screening progress/aria not delivered'),
            ('lane progress',('index.html','recoGwenShow(true,all?done/all:0);','recoGwenShow(true,0);'),'screen','screening progress not delivered to lane'),
            ('speech padding',('direct.css','#direct-board-lane,#reco-board-lane{height:122px;padding-top:34px;','#direct-board-lane,#reco-board-lane{height:122px;padding-top:0;'),'screen','speech clipped vertically'),
        ]
        for name,variant,audit,message in cases:
            try:run(browser,base,variant=variant,audit=audit)
            except AssertionError as e:
                assert message in str(e),(name,str(e))
                print('CAUGHT',name,flush=True)
            else:raise AssertionError('mutation survived: '+name)
            run(browser,base,audit=audit)
        browser.close()
