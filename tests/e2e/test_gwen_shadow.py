"""Foot shadows follow the production actor without layout shifts or hit targets."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server
from test_direct_party import ready, enter, pick_four
from test_direct_execution import fake, done
from test_direct_gwen import bounds
from test_case_banner import progress
from test_gwen_lane_image import loaded

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/shadow'
OUT.mkdir(parents=True,exist_ok=True)


def shadow(p):
    return p.locator('.gwen-lane-actor').evaluate('''a=>{
      const s=getComputedStyle(a,'::before'),r=a.getBoundingClientRect(),i=a.querySelector('img');
      return {content:s.content,position:s.position,pointer:s.pointerEvents,background:s.backgroundImage,
        width:parseFloat(s.width),height:parseFloat(s.height),bottom:parseFloat(s.bottom),
        opacity:s.opacity,transform:s.transform,transition:s.transitionDuration,z:s.zIndex,
        imageZ:getComputedStyle(a.querySelector('button')).zIndex,
        actor:r.toJSON(),lane:a.parentElement.id,art:i?.dataset.gwenExpression,
        left:r.left+parseFloat(s.left),top:r.bottom-parseFloat(s.bottom)-parseFloat(s.height)};
    }''')


def present(p):
    s=shadow(p)
    assert s['content'] not in ['none','normal'],s
    assert s['position']=='absolute' and s['pointer']=='none',s
    assert 'radial-gradient' in s['background'] and '0.3)' in s['background'],s
    assert .55<=s['width']/s['actor']['width']<=.65,s
    assert .18<=s['height']/s['width']<=.22,s
    assert int(s['z'])<int(s['imageZ']),s
    bounds(p)
    return s


def pose(p,key):
    # Drive the real policy/display path with a deterministic candidate.
    # A new step reverses the work lane (gwen_lane.js pingpong); progress 0 would then walk Gwen to the
    # opposite end and replace the pose with 'walk'. progress:null = pose only, no progress walk.
    p.evaluate('''key=>{
      GwenLane.CHOICES.work.splice(0,GwenLane.CHOICES.work.length,key);
      GwenLane.sync({mode:'direct',count:4,phase:'work',step:key+Math.random(),progress:null});
    }''',key)
    p.wait_for_function('key=>document.querySelector(".gwen-lane-image")?.dataset.gwenExpression===key',arg=key)
    loaded(p)


def capture(p,name,width):
    loaded(p)
    p.screenshot(path=str(OUT/f'{name}-{width}.png'),full_page=True)


def contract(browser,base,width):
    p=ready(browser,base,width,setup=fake,touch=width==360)
    # Home may select a cropped portrait, so verify its omission and the SD path.
    p.evaluate("GwenLane.CHOICES.home.splice(0,3,'guide2');GwenLane.sync({mode:'home',phase:'idle',step:'shadow'})")
    # Mobile uses its own SD candidates; CHOICES.home only controls desktop.
    home_arts=['guide2'] if width>=1200 else ['guide2','welcome','present']
    p.wait_for_function("arts=>arts.includes(document.querySelector('.gwen-lane-image')?.dataset.gwenExpression)",arg=home_arts)
    loaded(p);present(p)
    if width==1280:capture(p,'home',width)
    enter(p);pick_four(p,width==360)
    p.locator('#direct-board-lane').scroll_into_view_if_needed()
    if width==1280:
        p.wait_for_function('GwenLane.mount().state.playing')
        present(p);capture(p,'idle-play',width)
        # Hide only the pseudo element, then prove the shared assertion fails.
        style=p.add_style_tag(content='.gwen-lane-actor::before{content:none!important}')
        try:present(p)
        except AssertionError:print('CAUGHT missing shadow',flush=True)
        else:raise AssertionError('missing shadow mutation survived')
        style.evaluate('e=>e.remove()');present(p)
    p.evaluate('window.holdDirect=true;void directRun()')
    p.wait_for_function('window.directWorkers?.some(w=>!w.dead&&w.req)')
    progress(p,55)
    p.wait_for_function('''()=>{const s=GwenLane.mount().state,a=document.querySelector('.gwen-lane-actor');
      return !s.moving&&Math.abs(s.x-.55*(a.parentElement.clientWidth-a.offsetWidth))<1}''')
    loaded(p);present(p);capture(p,'work',width)
    # Measure actual moving frames, without screenshots resizing the viewport.
    p.wait_for_timeout(550)
    p.evaluate('window.shadowShifts=[];window.shadowPO=new PerformanceObserver(l=>shadowShifts.push(...l.getEntries().map(e=>e.value)));shadowPO.observe({type:"layout-shift"})')
    progress(p,100)
    p.wait_for_function('GwenLane.mount().state.moving')
    first=present(p);p.wait_for_timeout(180);second=present(p)
    dx=second['actor']['x']-first['actor']['x']
    assert dx>1 and abs(second['left']-first['left']-dx)<.1,(first,second)
    pose(p,'ready');p.wait_for_timeout(250)
    landed=present(p)
    assert landed['opacity']=='1' and landed['transform']=='matrix(1, 0, 0, 1, 0, 0)',landed
    pose(p,'jump');p.wait_for_timeout(250)
    jumping=present(p)
    assert jumping['transform']=='matrix(0.7, 0, 0, 0.7, 0, 0)' and jumping['opacity']=='0.5',jumping
    assert jumping['transition']=='0.2s, 0.2s',jumping
    # jump.webp itself lands after 400ms, before its expression changes.
    p.wait_for_function("document.querySelector('.gwen-lane-image').dataset.gwenLanded==='true'")
    p.wait_for_timeout(230)
    touchdown=present(p)
    assert touchdown['art']=='jump' and touchdown['transform']==landed['transform'] and touchdown['opacity']=='1',touchdown
    # After the WebP finishes, its static PNG is airborne again.
    p.wait_for_function("document.querySelector('.gwen-lane-image').dataset.gwenPlaying==='false'")
    p.wait_for_timeout(230)
    assert shadow(p)['transform']==jumping['transform']
    pose(p,'ready');p.wait_for_timeout(250)
    assert shadow(p)['transform']==landed['transform']
    assert shadow(p)['opacity']=='1'
    assert p.evaluate('shadowShifts.reduce((a,b)=>a+b,0)')==0,p.evaluate('shadowShifts')
    p.evaluate('shadowPO.disconnect()')
    assert p.locator('#gwen-quiet').count()==0
    # Left result: cropped portraits omit the shadow, SD results retain it.
    p.evaluate('''window.holdDirect=false;window.directDelay=100;
      {const w=directWorkers.findLast(w=>!w.dead&&w.req);w.postMessage(w.req)}''')
    done(p)
    p.wait_for_function("document.querySelector('.gwen-lane-image')?.dataset.gwenExpression!== 'ready'")
    p.locator('#direct-result-lane').scroll_into_view_if_needed();loaded(p)
    if width>=1200:assert shadow(p)['content']=='none',shadow(p)
    else:present(p)
    assert not p.errors,p.errors
    p.close()
    return {'width':width,'movement':dx,'jump':jumping,'touchdown':touchdown,'landed':landed,'layoutShift':0}


if __name__=='__main__':
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        result=[contract(browser,base,w) for w in [1280,1600,360]]
        browser.close()
    (OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS shadows / follow / jump / motion preferences / portrait / CLS / 360 / mutation',flush=True)
