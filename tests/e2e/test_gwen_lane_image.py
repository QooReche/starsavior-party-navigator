"""Lane pose swaps retain decoded pixels, including slow, failed and stale loads."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_page import test_server
from test_direct_party import ready, enter, pick_four
from test_direct_execution import fake
from test_case_banner import progress

ROOT = Path(__file__).resolve().parents[2]
IMG = '.gwen-lane-image'


def loaded(p):
    p.wait_for_function('''()=>{const i=document.querySelector('.gwen-lane-image');
      return i?.complete&&i.naturalWidth>0&&getComputedStyle(i).opacity==='1'}''')


def hold_decode(p):
    # Hold the real decode's completion, after the bytes arrive. Applies to both
    # the lane's candidate and the shared scene controller's probe image.
    p.evaluate('''()=>{
      const original=HTMLImageElement.prototype.decode;
      window.decodeWaiters=[];
      HTMLImageElement.prototype.decode=function(){
        const result=original.call(this);
        if(!this.src.endsWith('/surprised.png'))return result;
        return result.then(()=>new Promise((resolve,reject)=>decodeWaiters.push({resolve,reject})));
      };
      window.previousGwen=document.querySelector('.gwen-lane-image');
    }''')


def retained(p):
    frames=p.evaluate('''async()=>{
      const frames=[];
      for(let n=0;n<30;n++){
        await new Promise(requestAnimationFrame);
        const i=document.querySelector('.gwen-lane-image'),s=getComputedStyle(i);
        frames.push({same:i===previousGwen,complete:i.complete,width:i.naturalWidth,opacity:s.opacity,visibility:s.visibility});
      }
      return frames;
    }''')
    assert all(f['same'] and f['complete'] and f['width']>0 and f['opacity']=='1' and f['visibility']=='visible' for f in frames),frames


def contract(browser,base,mutation=False):
    def setup(p):
        fake(p)
        if mutation:
            source=(ROOT/'gwen_lane.js').read_text(encoding='utf-8')
            start=source.index('    function image(key)')
            end=source.index('    function positionSpeech',start)
            old='''    function image(key){if(key===art)return;art=key;actor.querySelector('button').innerHTML=root.Ux.gwenImage(key,'gwen-lane-image',80).replace('data-gwen-art=', 'data-gwen-managed="true" data-gwen-art=');
      actor.dataset.gwenExpression=key;actor.dataset.event=lastEvent;}
'''
            p.route('**/gwen_lane.js',lambda r:r.fulfill(body=source[:start]+old+source[end:],content_type='application/javascript'))
    p=ready(browser,base,setup=setup);enter(p);pick_four(p)
    p.locator('#direct-board-lane').scroll_into_view_if_needed()
    p.evaluate('window.holdDirect=true;void directRun()')
    p.wait_for_function('window.directWorkers?.some(w=>!w.dead&&w.req)')
    progress(p,55)
    p.wait_for_function('''()=>{const s=GwenLane.mount().state,a=document.querySelector('.gwen-lane-actor');
      return !s.moving&&Math.abs(s.x-.55*(a.parentElement.clientWidth-a.offsetWidth))<1}''')
    p.wait_for_timeout(250);loaded(p);hold_decode(p)
    p.evaluate("GwenLane.edit('skip')")
    p.wait_for_function('decodeWaiters.length>0')
    try:retained(p)
    except AssertionError:
        if not mutation:raise
        print('CAUGHT old innerHTML pose swap: decoded image removed',flush=True)
        p.close();return
    assert not mutation,'old innerHTML swap survived'
    p.evaluate('decodeWaiters.splice(0).forEach(w=>w.resolve())')
    p.wait_for_function("document.querySelector('.gwen-lane-image').dataset.gwenExpression==='surprised'")
    loaded(p)
    # A newer result wins even if the older pose finishes decoding last.
    p.evaluate("GwenLane.sync({mode:'direct',count:4,phase:'work',step:'again',progress:.55})")
    loaded(p)
    p.wait_for_function("document.querySelector('.gwen-lane-image').dataset.gwenExpression!=='surprised'")
    p.evaluate("previousGwen=document.querySelector('.gwen-lane-image');GwenLane.edit('skip')")
    p.wait_for_function('decodeWaiters.length>0')
    retained(p)
    p.evaluate("GwenLane.sync({mode:'direct',count:4,phase:'result',result:7301,clear:.9})")
    p.wait_for_function("document.querySelector('.gwen-lane-image').dataset.gwenExpression.startsWith('st_')")
    result_art=p.locator(IMG).get_attribute('data-gwen-expression')
    p.evaluate('decodeWaiters.splice(0).forEach(w=>w.resolve())')
    p.wait_for_timeout(250)
    assert p.locator(IMG).get_attribute('data-gwen-expression')==result_art
    # Failed candidates leave the preceding pixels intact as well.
    p.evaluate("GwenLane.sync({mode:'direct',count:4,phase:'work',step:'failure',progress:0})")
    p.wait_for_function("!document.querySelector('.gwen-lane-image').dataset.gwenExpression.startsWith('st_')")
    loaded(p)
    p.evaluate("previousGwen=document.querySelector('.gwen-lane-image');GwenLane.edit('skip')")
    p.wait_for_function('decodeWaiters.length>0')
    p.evaluate("decodeWaiters.splice(0).forEach(w=>w.reject(new Error('decode failure for test')))")
    retained(p)
    assert not p.errors,p.errors
    p.close();print('PASS lane decode delay / latest request / failure: 0 blank frames',flush=True)


if __name__=='__main__':
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        contract(browser,base)
        contract(browser,base,mutation=True)
        # Confirm the normal source again after the mutated response.
        contract(browser,base)
        browser.close()
