"""Empty-board detective banners, using the real page and synthetic workers."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_direct_party import ready, enter, pick_four
from test_direct_execution import fake, done, FAKE
from test_direct_phase2 import start, choice, finished
from test_page import test_server
from test_direct_gwen import bounds

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/banner2'
OUT.mkdir(parents=True,exist_ok=True)
B='#direct-lane-banner'
TITLE=B+' .gwen-banner-title:not([hidden])'


def expect(p, state):
    p.wait_for_function('s=>{const b=document.querySelector("#direct-lane-banner");return s?(!b.hidden&&b.dataset.state===s):b.hidden}',arg=state)


def geometry(p):
    audit=p.locator(TITLE).evaluate('''e=>{
      const r=e.getBoundingClientRect(),l=e.closest('.gwen-lane').getBoundingClientRect();
      const hits=[...document.querySelectorAll('button,input,select,summary,p,.direct-position,.gwen-lane-actor')].filter(x=>x.checkVisibility({checkVisibilityCSS:true})&&!x.closest('#direct-lane-banner')).filter(x=>{
        const b=x.getBoundingClientRect();return r.left<b.right-.5&&r.right>b.left+.5&&r.top<b.bottom-.5&&r.bottom>b.top+.5;
      }).map(x=>x.id||x.className);
      return {inside:r.left>=l.left&&r.right<=l.right&&r.top>=l.top&&r.bottom<=l.bottom,hits};
    }''')
    assert audit['inside'] and not audit['hits'],audit
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')


def shot(p, name, width):
    p.locator('#direct-board-lane').scroll_into_view_if_needed()
    p.wait_for_timeout(450)
    if p.locator(B).is_visible():geometry(p)
    bounds(p)
    p.screenshot(path=str(OUT/f'{name}-{width}.png'),full_page=True)


def sync(p, **state):
    p.evaluate('s=>GwenLane.sync({mode:"direct",count:4,phase:"result",result:987,clear:.82,...s})',state)


def working(p):
    assert p.evaluate('GwenLane.mount().state.lane')=='direct-board-lane','work left the board lane'
    assert p.locator('#direct-board-lane > .gwen-lane-actor').count()==1
    assert p.locator('#direct-progress-lane .gwen-lane-actor').count()==0
    assert p.locator(B).is_hidden(),'work banner visible'
    assert not p.evaluate('GwenLane.mount().state.playing'),'idle play overrode work'


def left(p):
    assert p.locator('#direct-result-lane > .gwen-lane-actor').is_visible()
    assert p.locator('#direct-board-lane > .gwen-lane-actor').count()==0
    assert p.locator(B).evaluate('e=>e.getAnimations({subtree:true}).length')==0,'banner competed with Gwen for motion'


def progress(p,n):
    p.evaluate("""n=>{const w=directWorkers.findLast(w=>!w.dead&&w.req),m=w.req;
      w.onmessage({data:{id:m.id,requestId:m.requestId,job:m.job,jobId:m.jobId,owner:m.owner,revision:m.revision,type:'stage',msg:'계산 중',completed:n,total:100}});
    }""",n)


def contract(browser,base,width):
    def setup(p):p.add_init_script(FAKE.replace("window.failGrown&&m.teams[0].key==='grown'",'window.failCase'))
    p=ready(browser,base,width,setup=setup,touch=width==360)
    enter(p);expect(p,'')
    # Partial party can settle on the left but must never get a banner.
    sync(p,phase='idle',count=2);expect(p,'')
    p.evaluate('directResultsPaint()')
    pick_four(p,width==360);expect(p,'')
    p.locator('#direct-board-lane').scroll_into_view_if_needed()
    p.evaluate('window.holdDirect=true;void directRun()')
    working(p)
    assert p.locator('#direct-progress').is_visible()
    assert p.locator('#direct-progress-lane').count()==0
    p.wait_for_timeout(300)
    p.evaluate('window.workShifts=[];window.workObserver=new PerformanceObserver(l=>workShifts.push(...l.getEntries().map(e=>({value:e.value,sources:e.sources.map(s=>({node:s.node?.outerHTML.slice(0,180),before:s.previousRect,after:s.currentRect}))}))));workObserver.observe({type:"layout-shift"})')
    # Real worker progress messages drive the production row and Gwen controller.
    for n in [10,55,100]:
        previous=p.evaluate('GwenLane.mount().state.x')
        progress(p,n)
        p.wait_for_function('n=>{const s=GwenLane.mount().state,a=document.querySelector(".gwen-lane-actor"),l=a.parentElement;return !s.moving&&Math.abs(s.x-n/100*(l.clientWidth-a.offsetWidth))<1}',arg=n,timeout=30000)
        working(p);bounds(p)
        assert p.evaluate('GwenLane.mount().state.x')>previous
        assert p.locator('#direct-progress').evaluate('e=>e.value')==n
        assert f'계산 중 · {n}/100판' in p.locator('#direct-run-state').inner_text()
        if n==55:
            assert p.evaluate('workShifts.reduce((a,b)=>a+b.value,0)')==0,p.evaluate('workShifts')
            # Full-page screenshots temporarily resize Chromium's viewport.
            p.evaluate('workObserver.disconnect()')
            shot(p,'work',width)
            p.evaluate('workObserver.observe({type:"layout-shift"})')
    assert p.locator('.gwen-lane-poke').bounding_box()['width']==(120 if width>=1200 else 64)
    p.wait_for_timeout(250)
    assert p.evaluate('GwenLane.CHOICES.work.includes(GwenLane.mount().state.art)')
    p.evaluate("GwenLane.edit('skip')")
    working(p)
    assert p.evaluate('GwenLane.mount().state.art')=='surprised'
    frozen=p.evaluate('GwenLane.mount().state.x')
    p.wait_for_timeout(400)
    assert p.evaluate('GwenLane.mount().state.x')==frozen
    assert p.evaluate('workShifts.reduce((a,b)=>a+b.value,0)')==0,p.evaluate('workShifts')
    p.locator('#direct-run').click()
    p.evaluate('window.holdDirect=false;window.directDelay=100;void directRun()')
    done(p);expect(p,'result');left(p)
    p.wait_for_function('document.querySelector("#direct-lane-banner .gwen-banner-title:not([hidden])").dataset.imageReady==="true"')
    first=p.locator(B).get_attribute('data-phrase')
    assert p.locator(TITLE+' .gwen-banner-fallback').is_hidden()
    shot(p,'result',width)
    p.evaluate('directResultsPaint();directResultsPaint()')
    assert p.locator(B).get_attribute('data-phrase')==first
    assert p.locator(TITLE).evaluate('e=>e.getAnimations().length')==0
    p.evaluate('DIRECT.cache.clear();void directRun()');done(p);expect(p,'result')
    assert p.locator(B).get_attribute('data-phrase')!=first
    # Geometry remains fixed through pending image, decode and error.
    lane=p.locator('#direct-board-lane').bounding_box();board=p.locator('#direct-board').bounding_box()
    img=p.locator(TITLE+' img');fallback=p.locator(TITLE+' .gwen-banner-fallback')
    img.evaluate('e=>e.src="assets/missing-case-banner.webp"')
    p.wait_for_function('!document.querySelector("#direct-lane-banner .gwen-banner-title:not([hidden])").dataset.imageReady')
    assert fallback.is_visible() and fallback.inner_text() in ['조사 완료!','수사 완료!','계산 완료!']
    assert p.locator('#direct-board-lane').bounding_box()==lane
    assert p.locator('#direct-board').bounding_box()==board
    geometry(p)
    p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[1].key})")
    expect(p,'')
    p.wait_for_function('GwenLane.mount().state.lane==="direct-board-lane"')
    p.evaluate('window.failCase=true;void directRun()')
    p.wait_for_function('!DIRECT.active&&DIRECT.rows.now.status==="error"')
    expect(p,'error');left(p)
    if width==1280:shot(p,'error',width)
    # Same production controller handles intermediate bundle results.
    for step in ['now','reco','growth']:
        sync(p,bundleRunning=True,step=step);working(p)
    sync(p,bundleRunning=False);expect(p,'result')
    sync(p,stale=True);expect(p,'')
    sync(p,phase='error');expect(p,'error')
    sync(p,phase='work',progress=.8);working(p)
    p.locator('#direct-board-lane').scroll_into_view_if_needed()
    p.wait_for_function('GwenLane.mount().state.moving')
    p.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
    frozen=p.evaluate('GwenLane.mount().state')
    p.wait_for_timeout(500)
    assert p.evaluate('GwenLane.mount().state')==frozen
    assert p.locator('.gwen-lane-actor').evaluate('e=>e.getAnimations().every(a=>a.playState==="paused")')
    p.evaluate('delete document.hidden;document.dispatchEvent(new Event("visibilitychange"))')
    p.wait_for_function('GwenLane.mount().state.clock>'+str(frozen['clock']))
    p.set_viewport_size({'width':width,'height':250})
    p.evaluate('scrollTo(0,document.body.scrollHeight)')
    p.wait_for_timeout(200)
    frozen=p.evaluate('GwenLane.mount().state')
    p.wait_for_timeout(500)
    assert p.evaluate('GwenLane.mount().state')==frozen
    p.set_viewport_size({'width':width,'height':1000})
    p.locator('#direct-board-lane').scroll_into_view_if_needed()
    for quiet in [False,True]:
        if quiet:p.evaluate('const q=document.querySelector("#gwen-quiet");q.checked=true;q.dispatchEvent(new Event("change"))')
        else:p.emulate_media(reduced_motion='reduce')
        sync(p,phase='work',progress=1);working(p)
        x=p.evaluate('GwenLane.mount().state.x')
        p.wait_for_timeout(400)
        assert not p.evaluate('GwenLane.mount().state.moving')
        assert p.evaluate('GwenLane.mount().state.x')==x
        sync(p,result=999+int(quiet));expect(p,'result')
        assert p.locator(TITLE).evaluate('e=>getComputedStyle(e).animationName')=='none'
        p.emulate_media(reduced_motion='no-preference')
    assert not p.errors,p.errors
    p.close()
    print('PASS banner contract',width,flush=True)


def bundle(browser,base):
    p=start(browser,base);choice(p,2)
    p.evaluate('window.directDelay=80;void directRun()')
    for step in ['reco','growth']:
        p.wait_for_function('s=>DIRECT.bundle.current===s&&DIRECT.bundle.running',arg=step,timeout=120000)
        working(p)
    finished(p);expect(p,'result')
    assert p.evaluate('DIRECT.bundle.steps.every(s=>s.status==="done")')
    assert not p.errors,p.errors
    p.close();print('PASS real bundle progression',flush=True)


def delayed(browser,base):
    pending=[]
    p=ready(browser,base,setup=fake);enter(p);pick_four(p)
    p.route('**/case_banner_*.webp?delay',lambda r:pending.append(r))
    p.locator(B+' img').evaluate_all('xs=>xs.forEach(e=>{delete e.parentElement.dataset.imageReady;e.src+="?delay"})')
    p.wait_for_timeout(100)
    sync(p);expect(p,'result')
    assert p.locator(TITLE+' .gwen-banner-fallback').is_visible()
    assert pending
    before=p.locator('#direct-board').bounding_box()
    p.wait_for_timeout(500)
    p.evaluate('window.bannerShifts=[];new PerformanceObserver(l=>bannerShifts.push(...l.getEntries().map(e=>e.value))).observe({type:"layout-shift"})')
    for r in pending:r.fulfill(path=str(ROOT/'assets/ui_icons'/r.request.url.rsplit('/',1)[1].split('?')[0]),content_type='image/webp')
    p.wait_for_function('document.querySelector("#direct-lane-banner .gwen-banner-title:not([hidden])").dataset.imageReady==="true"')
    p.wait_for_timeout(200)
    assert p.locator(TITLE+' .gwen-banner-fallback').is_hidden()
    assert p.locator('#direct-board').bounding_box()==before
    assert p.evaluate('bannerShifts.reduce((a,b)=>a+b,0)')==0
    p.close();print('PASS delayed decode CLS 0',flush=True)


def mutations(browser,base):
    source=(ROOT/'gwen_lane.js').read_text(encoding='utf-8')
    cases=[('work lane',"return ['work',stage.board]", "return ['work',stage.result]",working),
           ('progress disabled',"if(target>x+.5)moveTo(target", "if(false)moveTo(target",None)]
    for name,old,new,check in cases:
        assert old in source
        def setup(p):
            fake(p)
            p.route('**/gwen_lane.js',lambda r:r.fulfill(body=source.replace(old,new),content_type='application/javascript'))
        p=ready(browser,base,setup=setup);enter(p);pick_four(p)
        p.evaluate('window.holdDirect=true;void directRun()')
        p.locator('#direct-board-lane').scroll_into_view_if_needed()
        try:
            if check:check(p)
            else:
                progress(p,50);p.wait_for_timeout(1500)
                assert p.evaluate('GwenLane.mount().state.x')>0,'progress did not move Gwen'
        except AssertionError as e:print('CAUGHT',name,str(e),flush=True)
        else:raise AssertionError('mutation survived: '+name)
        p.close()
        # Reload the unmodified production source and repeat the same assertion.
        p=ready(browser,base,setup=fake);enter(p);pick_four(p)
        p.evaluate('window.holdDirect=true;void directRun()')
        p.locator('#direct-board-lane').scroll_into_view_if_needed()
        working(p);progress(p,50)
        p.wait_for_function('GwenLane.mount().state.x>0')
        bounds(p);p.close()



if __name__=='__main__':
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in [1280,1600,360]:contract(browser,base,width)
        bundle(browser,base);delayed(browser,base);mutations(browser,base)
        browser.close()
    print('PASS case banners / reduced motion / hidden tab / fallback / mutations')
