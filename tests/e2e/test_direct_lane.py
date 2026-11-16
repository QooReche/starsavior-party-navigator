"""Board playground, real image fallback and delayed background geometry."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_direct_party import ready, enter, pick_four
from test_direct_gwen import bounds, shown
from test_direct_execution import fake
from test_page import test_server

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_tmp/lane'
OUT.mkdir(parents=True, exist_ok=True)


def state(p):
    return p.evaluate('GwenLane.mount().state')


def still(p):
    p.wait_for_function("""()=>{const i=document.querySelector('.gwen-lane-image');
      return i.dataset.gwenPlaying==='false'&&i.src===new URL(i.dataset.gwenStatic,document.baseURI).href}""")


def advance(p, ms=650):
    # Finish genuine WAAPI segments, then advance the visible clock.
    p.evaluate("document.querySelector('.gwen-lane-actor').getAnimations().forEach(a=>a.finish())")
    p.clock.run_for(ms)


def setup(p, play_random=.5):
    fake(p)
    p.clock.install()
    p.add_init_script('''{let seed=13;Math.random=()=>((seed=(seed*1664525+1013904223)>>>0)/4294967296)}''')
    source=(ROOT/'gwen_lane.js').read_text(encoding='utf-8')
    # Isolate the planner's deterministic random stream from image decoding/blinks.
    assert 'play=playground()' in source
    source=source.replace('play=playground()', f'play=playground(()=>{play_random})')
    p.route('**/gwen_lane.js',lambda route:route.fulfill(body=source,content_type='application/javascript'))


def fallback(p):
    p.wait_for_function("[...document.querySelectorAll('.direct-member img.art')].every(i=>i.dataset.imageLoaded==='true')")
    assert p.locator('.direct-member .fallback:visible').count() == 0, 'loaded portrait leaked fallback'
    p.evaluate("{const e=document.createElement('div');e.id='fallback-probe';e.innerHTML=card({s:BYKEY[DIRECT.draft.slots[0].key]},'front');document.body.append(e)}")
    p.locator('#fallback-probe').scroll_into_view_if_needed()
    p.wait_for_function("document.querySelector('#fallback-probe img.art')?.dataset.imageLoaded==='true'")
    assert p.locator('#fallback-probe .fallback').is_hidden(), 'recommendation leaked fallback'
    for selector in ['.direct-member img.art', '#fallback-probe img.art']:
        p.locator(selector).first.evaluate("i=>i.src='assets/missing-lane-portrait.webp'")
    p.wait_for_function("!document.querySelector('#fallback-probe img.art')")
    assert p.locator('.direct-member .fallback:visible').count() == 1
    assert p.locator('#fallback-probe .fallback').is_visible(), 'failed portrait lost fallback'
    p.locator('#fallback-probe').evaluate('e=>e.remove()')


def contract(browser, base, width):
    p = ready(browser, base, width, setup=setup)
    enter(p);shown(p)
    lane = p.locator('#direct-board-lane')
    assert lane.bounding_box()['height'] == (162 if width >= 1200 else 122)
    assert p.locator('.gwen-lane-poke').bounding_box()['width'] == (120 if width >= 1200 else 80)
    seen = set(); positions = []; facing = set(); poses = []; last_pose = None
    for i in range(170):
        advance(p)
        s = state(p)
        if i in (75,150):p.keyboard.press('Shift')
        if s['playing']:
            seen.add(s['art']);positions.append(s['x'])
            facing.add(p.locator('.gwen-lane-poke').evaluate('e=>e.style.transform'))
            if s['moving']:last_pose=None
            if not s['moving'] and s['art'] in ['magnify','think','coffee','stamp','jump'] and s['art'] != last_pose:
                poses.append(s['art']);last_pose=s['art']
        bounds(p)
    maximum = lane.bounding_box()['width'] - p.locator('.gwen-lane-poke').bounding_box()['width']
    assert positions and min(positions)<1 and max(positions)>maximum-1, (width, positions)
    assert 'walk' in seen, seen
    assert 'scaleX(-1)' in facing and 'none' in facing, facing
    assert poses, seen
    pick_four(p);shown(p)
    assert not state(p)['playing']
    for _ in range(30):
        advance(p,100)
        if not state(p)['moving']:break
    p.clock.run_for(200)
    assert state(p)['art']=='jump', state(p)
    p.clock.run_for(1700)
    for action, wanted in [('leader','verdict'),('grown','train')]:
        p.evaluate('(a)=>GwenLane.edit(a,0)', action)
        assert not state(p)['playing']
        for _ in range(30):
            advance(p,100)
            if not state(p)['moving']:break
        p.clock.run_for(200)
        assert state(p)['art']==wanted, state(p)
        p.clock.run_for(1600)
    p.clock.run_for(7100)
    assert state(p)['playing']
    shown(p)
    p.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
    still(p)
    frozen=state(p);p.clock.run_for(15000)
    assert state(p)==frozen, (frozen,state(p))
    p.evaluate('delete document.hidden;document.dispatchEvent(new Event("visibilitychange"))')
    p.set_viewport_size({'width':width,'height':250})
    p.evaluate("scrollTo(0,scrollY+document.querySelector('#direct-board-lane').getBoundingClientRect().top-innerHeight+20)")
    p.wait_for_timeout(200)
    p.wait_for_function("document.querySelector('.gwen-lane-actor').dataset.lanePaused==='true'")
    still(p)
    partial=state(p);p.clock.run_for(5000)
    assert state(p)==partial, 'actor moved while only the empty top of its lane was visible'
    p.evaluate('scrollTo(0,document.body.scrollHeight)');p.wait_for_timeout(200)
    p.wait_for_function("document.querySelector('.gwen-lane-actor').dataset.lanePaused==='true'")
    frozen=state(p);p.clock.run_for(15000)
    assert state(p)==frozen, (frozen,state(p))
    p.set_viewport_size({'width':width,'height':1000});shown(p)
    p.emulate_media(reduced_motion='reduce');x=state(p)['x']
    p.clock.run_for(8000)
    assert not state(p)['moving'] and not state(p)['playing'] and state(p)['x']==x
    p.emulate_media(reduced_motion='no-preference')
    p.locator('#optbox > summary').click();p.locator('#gwen-quiet').check();shown(p)
    frozen=state(p);p.clock.run_for(10000)
    assert not state(p)['moving'] and state(p)['x']==frozen['x']
    still(p)
    assert p.locator('.gwen-lane-actor').is_visible()
    p.locator('#gwen-quiet').uncheck()
    p.evaluate('window.holdDirect=true;void directRun()')
    for _ in range(30):
        advance(p,100)
        if state(p)['lane']=='direct-progress-lane':break
    assert state(p)['lane']=='direct-progress-lane', state(p)
    p.clock.run_for(15000)
    assert not state(p)['playing']
    p.evaluate("GwenLane.edit('leader',0)")
    assert state(p)['lane']=='direct-progress-lane'
    p.locator('#direct-run').click()
    fallback(p)
    assert not p.errors, p.errors
    p.close()
    print('lane contract',width,sorted(seen),flush=True)
    # Samples can miss a pose preempted by a real input. Exact history exclusion
    # is tested against every pose() call in gwen_lane_test.js.
    return {'width':width,'height':162 if width>=1200 else 122,'seen':sorted(seen),'sampled_poses':poses}


def delayed(browser, base):
    pending=[]
    def route_setup(p):p.route('**/journey_lane.webp', lambda route:pending.append(route))
    p=ready(browser,base,setup=route_setup);enter(p);shown(p)
    before=p.locator('#direct-board-lane').bounding_box();board=p.locator('#direct-board').bounding_box()
    assert pending, 'background request not exercised'
    p.evaluate('window.laneShifts=[];new PerformanceObserver(l=>laneShifts.push(...l.getEntries().map(e=>e.value))).observe({type:"layout-shift"})')
    for route in pending:route.fulfill(path=str(ROOT/'assets/ui_icons/journey_lane.webp'),content_type='image/webp')
    p.wait_for_timeout(500)
    assert p.locator('#direct-board-lane').bounding_box()==before
    assert p.locator('#direct-board').bounding_box()==board
    assert p.evaluate('laneShifts.reduce((a,b)=>a+b,0)')==0
    p.close()


def partial_party_poke(browser, base):
    # Force the run/jump branch; normal contracts force walk/varied poses.
    p=ready(browser,base,setup=lambda p:setup(p,0));enter(p)
    p.locator('#direct-picker-inline [data-direct-action=pick]:enabled').first.click();shown(p)
    for _ in range(60):
        advance(p)
        if state(p)['playing']:break
    assert state(p)['playing'] and state(p)['lane']=='direct-board-lane'
    p.locator('.gwen-lane-poke').click()
    assert state(p)['lane']=='direct-board-lane', 'input teleported the partial-party actor away from the pointer'
    assert not state(p)['playing'] and state(p)['art']=='shy', state(p)
    seen=set()
    for _ in range(40):
        advance(p);bounds(p)
        if state(p)['playing']:seen.add(state(p)['art'])
    assert {'run','jump'}<=seen, seen
    p.close()


def mutations(browser, base):
    for name,css in [('overflow','.gwen-lane-actor{transform:translateX(-999px)!important}'),
                     ('fallback','.direct-member .fallback{visibility:visible!important}')]:
        p=ready(browser,base);enter(p);pick_four(p);shown(p);p.add_style_tag(content=css)
        try:
            if name=='overflow':bounds(p)
            else:fallback(p)
        except AssertionError as e:print('CAUGHT',name,str(e)[:140],flush=True)
        else:raise AssertionError(name+' mutation survived')
        p.close()


def capture(browser, base):
    for width in [1280,1600]:
        p=ready(browser,base,width);enter(p);pick_four(p)
        p.locator('#direct-board-lane').scroll_into_view_if_needed()
        p.mouse.move(0,0);p.wait_for_timeout(2200);shown(p);bounds(p)
        p.wait_for_function("[...document.querySelectorAll('.direct-member img.art')].every(i=>i.dataset.imageLoaded==='true')")
        p.screenshot(path=str(OUT/f'lane-{width}.png'),full_page=True);p.close()
    context=browser.new_context(viewport={'width':1280,'height':1000},record_video_dir=str(OUT/'video'),record_video_size={'width':1280,'height':1000})
    class Pages:
        def new_page(self,**kwargs):return context.new_page()
    p=ready(Pages(),base);enter(p)
    p.locator('#direct-board-lane').scroll_into_view_if_needed();p.mouse.move(0,0)
    p.wait_for_function('GwenLane.mount().state.playing')
    for _ in range(60):
        p.wait_for_timeout(200);bounds(p)
    video=p.video;context.close();video.save_as(str(OUT/'lane-idle.webm'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',action='store_true');a=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        if a.capture:capture(browser,base)
        else:
            results=[contract(browser,base,w) for w in [1280,1600,1100]]
            delayed(browser,base);partial_party_poke(browser,base);mutations(browser,base)
            (OUT/'checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        browser.close()
    print('PASS lane playground / fallback / background',flush=True)


if __name__=='__main__':main()
