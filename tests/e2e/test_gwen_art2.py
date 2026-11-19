"""Real result art, deferred loading, one-shot spacing, hidden tabs and reduced motion.

python -X utf8 tests/e2e/test_gwen_art2.py --shots --mutations
All accounts/results are synthetic. Captures stay uncommitted in _shot_art2_*.png.
"""
import argparse
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'_tmp')
from test_page import test_server
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def ready(page,base):
    page.goto(base+'/index.html?season=force&pm=reco',wait_until='networkidle')
    page.wait_for_function('window._ready')
    page.wait_for_timeout(700)


def fixture(page,html):
    page.evaluate('''html=>{recoClearTimer();SIMQ.auto=false;SIMQ.kick=false;
      $('out').hidden=false;$('out').innerHTML=html;$('out').scrollIntoView({block:'center'});}''',html)


def loaded(page,selector):
    pic=page.locator(selector)
    pic.scroll_into_view_if_needed()
    page.wait_for_function('(e)=>!!e.getAttribute("src")&&e.complete&&e.naturalWidth>0',arg=pic.element_handle())
    return pic


def playing(page,pic):
    page.wait_for_function('(e)=>e.dataset.gwenPlaying==="true"&&e.currentSrc.startsWith("blob:")',arg=pic.element_handle())
    pic.evaluate('(e)=>e.decode()')


def timer_audit(page):
    page.evaluate('''() => {window.__artRevoked=new Set();window.__artCreated=0;
      const revoke=URL.revokeObjectURL.bind(URL),create=URL.createObjectURL.bind(URL);
      URL.revokeObjectURL=u=>{__artRevoked.add(u);revoke(u)};
      URL.createObjectURL=b=>{__artCreated++;return create(b)};
    }''')
    fixture(page,page.evaluate('Ux.gwenWork("welcome")'))
    pic=loaded(page,'#out [data-gwen-art]')
    playing(page,pic)
    first=pic.get_attribute('src')
    page.clock.run_for(1200)
    assert pic.get_attribute('src').endswith('welcome.png'),'one-shot must rest on PNG'
    page.clock.run_for(3500)
    assert pic.get_attribute('src').endswith('welcome.png'),'minimum 4 second rest missing'
    page.clock.run_for(2500)
    playing(page,pic)
    assert pic.get_attribute('src')!=first,'replay must restart from a fresh blob URL'
    # Browser visibility is injected deterministically; dispatch the production event.
    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
    assert pic.get_attribute('src').endswith('.png')
    page.clock.run_for(15000)
    assert pic.get_attribute('src').endswith('.png'),'timer ran in a hidden document'
    page.evaluate('delete document.hidden;document.dispatchEvent(new Event("visibilitychange"))')
    playing(page,pic)
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function('(e)=>e.currentSrc.endsWith("welcome.png")',arg=pic.element_handle())
    page.clock.run_for(20000)
    assert pic.get_attribute('src').endswith('.png'),'reduced motion resumed'
    assert pic.evaluate('(e)=>getComputedStyle(e).animationName')=='none'
    page.emulate_media(reduced_motion='no-preference')
    playing(page,pic)
    page.evaluate('$("out").hidden=true')
    page.wait_for_function('(e)=>e.currentSrc.endsWith("welcome.png")',arg=pic.element_handle())
    page.clock.run_for(12000)
    assert pic.get_attribute('src').endswith('.png')
    page.evaluate('$("out").hidden=false')
    playing(page,pic)
    last=pic.get_attribute('src')
    created=page.evaluate('__artCreated')
    page.evaluate('$("out").innerHTML=""')
    assert page.evaluate('(u)=>__artRevoked.has(u)',last),'removed image retained a blob URL'
    page.clock.run_for(12000)
    assert page.evaluate('__artCreated')==created,'removed image replayed'


def deferred_audit(page,requests):
    page.emulate_media(reduced_motion='reduce')
    fixture(page,page.evaluate(''''<div id="deferred-art" hidden>'+Ux.gwenImage('notes')+'</div>' '''))
    page.wait_for_timeout(150)
    assert page.locator('#deferred-art img').get_attribute('src') is None
    assert not any('/notes.' in u for u in requests),'hidden asset was fetched'
    page.evaluate('$("deferred-art").hidden=false')
    pic=loaded(page,'#deferred-art img')
    assert pic.get_attribute('src').endswith('notes.png')
    assert not any('/notes.webp' in u for u in requests),'reduced motion downloaded animation'
    page.emulate_media(reduced_motion='no-preference')
    playing(page,pic)
    assert any('/notes.webp' in u for u in requests)


def drawer_audit(page):
    pic=page.locator('#drawer .gwen-welcome')
    assert pic.get_attribute('src') is None,'visibility:hidden drawer fetched its art'
    page.locator('#mi-open-import').click()
    loaded(page,'#drawer .gwen-welcome');playing(page,pic)
    page.locator('#dclose').click()
    page.wait_for_function('(e)=>e.dataset.gwenPlaying==="false"',arg=pic.element_handle())
    assert pic.get_attribute('src').endswith('welcome.png')


def clipped_audit(page):
    fixture(page,page.evaluate(''''<div id="clip-art" style="height:1px;overflow:hidden"><div style="margin-top:30px">'+Ux.gwenImage('thoughtful')+'</div></div>' '''))
    page.wait_for_timeout(150)
    pic=page.locator('#clip-art img')
    assert pic.get_attribute('src') is None,'ancestor-clipped picture was loaded'
    page.evaluate('$("clip-art").style.height="200px"')
    loaded(page,'#clip-art img');playing(page,pic)


def edge_audit(page):
    fixture(page,page.evaluate(''''<div id="edge-art" style="position:fixed;top:100vh;left:0;width:160px;height:160px">'+Ux.gwenImage('thoughtful')+'</div>' '''))
    page.wait_for_timeout(150)
    pic=page.locator('#edge-art img')
    assert pic.get_attribute('src') is None
    page.evaluate('$("edge-art").style.top="calc(100vh - 20px)"')
    page.wait_for_function('(e)=>!!e.getAttribute("src")',arg=pic.element_handle())


def result_audit(page,probability,art,width,shots):
    page.evaluate('''p=>{recoClearTimer();SIMQ.busy=null;SIMQ.screening=false;SIMQ.auto=false;SIMQ.kick=false;
      localStorage.setItem('pn.simauto','0');REQ=true;RECO.standard=true;
      document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();run(true);
      const st=cur[$('stage').value];
      for(const box of Object.values(LASTQ))for(const t of box.rows){SIMQ.res[simSig(st,t)]={n:100,clear:p,ci:[Math.max(0,p-.02),Math.min(1,p+.02)],ta:35,ttk:35,frac:1,u:Object.fromEntries(t.keys.map(k=>[k,[.25,0]]))};}
      run(true);
    }''',probability)
    reaction=page.locator('#out .gwen-reaction')
    assert reaction.count()==1,'only the first party should carry a portrait'
    actual=reaction.get_attribute('data-gwen-reaction')
    assert actual in ({'confident':['st_verdict','st_cheer','st_ok','st_reach'],'thoughtful':['thoughtful','st_point'],'notes':['notes','st_cry']}[art])
    art=actual
    pic=loaded(page,'#out .gwen-reaction img')
    playing(page,pic)
    assert pic.get_attribute('data-gwen-motion').endswith(art+'.webp')
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function('(e)=>e.currentSrc.endsWith(e.dataset.gwenArt+".png")',arg=pic.element_handle())
    space=page.locator('.gwen-bubble-space').bounding_box()
    if width>=1200:
        assert space['width']>=220 and space['height']>=64
        assert space['y']+space['height']<=pic.bounding_box()['y']
        assert reaction.evaluate('(e)=>!!e.closest(".result-summary")')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('#out .result-team .gc').count()==4
    if shots:
        page.screenshot(path=str(ROOT/f'_shot_art2_{art}_{width}.png'),full_page=True)
    page.emulate_media(reduced_motion='no-preference')


def walk_audit(page):
    fixture(page,page.evaluate('Ux.gwenWork("long")'))
    pic=loaded(page,'#out img')
    assert pic.get_attribute('data-gwen-art')=='walk','walking sheet disconnected'
    assert pic.get_attribute('data-gwen-motion').endswith('/walk.webp'),'walking motion disconnected'
    # loaded() may return the decoded PNG while the animation is still decoding.
    # Walk alone uses a direct continuous WebP, never a one-shot blob URL.
    page.wait_for_function('(e)=>e.dataset.gwenPlaying==="true"&&e.currentSrc.endsWith("/walk.webp")',arg=pic.element_handle())
    assert pic.get_attribute('src').endswith('walk.webp'),'walking sheet disconnected'
    page.clock.run_for(1500)
    assert pic.get_attribute('src').endswith('walk.webp'),'walking loop stopped after one shot'
    assert pic.get_attribute('data-gwen-playing')=='true'
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function('(e)=>e.currentSrc.endsWith("walk.png")',arg=pic.element_handle())
    assert pic.evaluate('(e)=>getComputedStyle(e).animationName')=='none'
    page.emulate_media(reduced_motion='no-preference')


def exercise(page,base,width,shots,requests):
    ready(page,base)
    drawer_audit(page)
    clipped_audit(page)
    edge_audit(page)
    deferred_audit(page,requests)
    page.clock.install()
    timer_audit(page)
    assert sum('/welcome.webp' in u for u in requests)==1,'replays downloaded the same WebP again'
    walk_audit(page)
    if shots:
        page.screenshot(path=str(ROOT/f'_shot_art2_walk_{width}.png'))
    for p,art in [(.95,'confident'),(.3,'thoughtful'),(.01,'notes')]:
        result_audit(page,p,art,width,shots)
    # Actual roster empty state uses the retained files drawing once.
    page.evaluate('MI.info=null;miTab(true)')
    pic=loaded(page,'#mi-list [data-gwen-art]')
    assert pic.get_attribute('data-gwen-art')=='files'
    assert page.locator('#mi-list [data-gwen-art]').count()==1
    if shots:
        page.screenshot(path=str(ROOT/f'_shot_art2_empty_{width}.png'))
    page.evaluate('miTab(false)')
    for mode in ['report','error','welcome']:
        fixture(page,page.evaluate('(m)=>Ux.gwenWork(m)',mode))
        pic=loaded(page,'#out [data-gwen-art]');playing(page,pic)
        if shots:
            page.screenshot(path=str(ROOT/f'_shot_art2_{mode}_{width}.png'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--shots',action='store_true');ap.add_argument('--mutations',action='store_true');args=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in [1280,360,1600]:
                context=browser.new_context(viewport={'width':width,'height':950})
                context.add_init_script('Math.random=()=>.5')
                page=context.new_page();page.set_default_timeout(5000)
                requests=[];errors=[];page.on('request',lambda r:requests.append(r.url));page.on('pageerror',lambda e:errors.append(str(e)))
                try:
                    exercise(page,base,width,args.shots,requests)
                    assert not errors,errors
                    print(f'PASS art2 {width}: visible-only requests, interval/replay, hidden, reduce, real results, roster',flush=True)
                finally:
                    context.close()
            if args.mutations:
                source=(ROOT/'ux_ui.js').read_text(encoding='utf-8')
                variants=[('walk',"long:'walk'","long:'investigate'",walk_audit),
                          ('walk-loop',"walk:{file:'walk',loop:true}","walk:{file:'walk'}",walk_audit),
                          ('interval','rand(4000,4001)','0',timer_audit),
                          ('reduced',"root.matchMedia('(prefers-reduced-motion: reduce)')","({matches:false,addEventListener(){}})",timer_audit),
                          ('result',"if(result)return gwenReport(result,{clear:p,portrait:true});","if(result)return '';",lambda p:result_audit(p,.95,'confident',1280,False)),
                          ('drawer',"c.visibility==='hidden'",'false',drawer_audit),
                          ('clipping',"if(el!==img){","if(false){",clipped_audit),
                          ('cleanup','s.stop();observer.unobserve(img);states.delete(img);','observer.unobserve(img);states.delete(img);',timer_audit)]
                for name,old,new,audit in variants:
                    assert old in source
                    context=browser.new_context(viewport={'width':1280,'height':950})
                    context.add_init_script('Math.random=()=>.5')
                    body=source.replace(old,new)
                    context.route('**/ux_ui.js*',lambda route:route.fulfill(status=200,content_type='application/javascript',body=body))
                    page=context.new_page();page.set_default_timeout(1500)
                    try:
                        ready(page,base);page.clock.install()
                        try:
                            audit(page)
                        except (AssertionError,PlaywrightTimeout):
                            print('CAUGHT mutation '+name,flush=True)
                        else:
                            raise AssertionError('mutation survived: '+name)
                    finally:
                        context.close()
        finally:
            browser.close()


if __name__=='__main__':
    main()
