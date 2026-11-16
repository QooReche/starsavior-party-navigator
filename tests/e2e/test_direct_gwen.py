"""C stage: bounded lanes and actual Pyodide growth effect. Synthetic fixtures only."""
import argparse
import json
import time
from pathlib import Path
from test_direct_party import ready, enter, pick_four, geometry
from test_direct_execution import fake, done
from test_page import test_server, FULL
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/direct-c'
OUT.mkdir(parents=True,exist_ok=True)
ACTOR='.gwen-lane-actor'


def shown(p):
    p.locator(ACTOR).scroll_into_view_if_needed()
    p.wait_for_function("document.querySelector('.gwen-lane-image')?.dataset.gwenLoaded==='true'")


def snapshot(p,name,width):
    shown(p)
    p.wait_for_function("Number(getComputedStyle(document.querySelector('.gwen-lane-image')).opacity)>.99")
    if getattr(p,'freeze_capture',False):p.clock.pause_at(p.evaluate('Date.now()+50')/1000)
    try:p.screenshot(path=str(OUT/f'{name}-{width}.png'),full_page=True)
    finally:
        if getattr(p,'freeze_capture',False):p.clock.resume()


def bounds(p):
    audit=p.evaluate('''() => {
      const a=document.querySelector('.gwen-lane-poke'),lane=a.closest('.gwen-lane'),r=a.getBoundingClientRect(),l=lane.getBoundingClientRect();
      const overlap=s=>[...document.querySelectorAll(s)].filter(e=>!e.closest('.gwen-lane')&&e.checkVisibility({checkVisibilityCSS:true,checkOpacity:true})).filter(e=>{
        const b=e.getBoundingClientRect();return r.left<b.right-.5&&r.right>b.left+.5&&r.top<b.bottom-.5&&r.bottom>b.top+.5;
      }).map(e=>e.id||e.outerHTML.slice(0,120));
      return {inside:r.left>=l.left-.5&&r.right<=l.right+.5&&r.top>=l.top-.5&&r.bottom<=l.bottom+.5,
        size:Math.min(r.width,r.height),overlap:overlap('button,input,select,summary,p,.direct-position'),
        actors:[...document.querySelectorAll('.gwen-lane-actor')].filter(e=>e.getClientRects().length).length};
    }''')
    assert audit['inside'],audit
    assert audit['size']>=63.99,audit
    assert not audit['overlap'],audit
    assert audit['actors']==1,audit
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')


def no_account(browser,base):
    p=ready(browser,base,info=None);enter(p)
    assert p.locator('#direct-state').inner_text().count('내 정보 없음 · 표준 육성 기준')==1
    p.locator('#mode-strip [data-pn-mode=reco]').click();p.locator('#mode-strip [data-pn-mode=direct]').click()
    shown(p);assert p.locator(ACTOR).count()==1,'mode return lost actor'
    p.close()


def ui(browser,base,width):
    def setup(p):fake(p);p.clock.install()
    p=ready(browser,base,width,setup=setup,touch=width==360);p.freeze_capture=True
    snapshot(p,'home',width);bounds(p)
    if width==1280:
        style=p.add_style_tag(content='.gwen-lane-actor{transform:translateX(-999px)!important}')
        try:
            try:bounds(p)
            except AssertionError:print('CAUGHT actual lane overflow',flush=True)
            else:raise AssertionError('outside-lane mutation survived')
        finally:style.evaluate('(s)=>s.remove()')
        bounds(p)
    enter(p)
    shown(p)
    # The editor path is exercised via actual edit actions (picker in a dialog on mobile).
    p.evaluate("directChange({type:'put',key:R.find(s=>MI.info.units.some(u=>u.id===s.uid)).key,slot:2})")
    p.wait_for_timeout(200)
    snapshot(p,'editing-run',width);bounds(p)
    p.evaluate("directChange({type:'clear'})")
    pick_four(p,width==360);shown(p)
    p.wait_for_timeout(700)
    snapshot(p,'complete',width);bounds(p);geometry(p,width)
    p.wait_for_timeout(1800)
    p.locator('[data-direct-action=grown][data-slot="0"]').click()
    snapshot(p,'growth',width);bounds(p)
    p.evaluate('window.directDelay=3500')
    p.locator('#direct-run').click()
    p.wait_for_function("GwenLane.mount().state.lane==='direct-progress-lane'")
    snapshot(p,'working',width);bounds(p)
    work=p.evaluate('GwenLane.mount().state.art')
    p.evaluate("GwenLane.edit('put',0)")
    assert p.evaluate('GwenLane.mount().state.art')==work,'edit overrode calculation'
    done(p);snapshot(p,'high',width);bounds(p)
    art=p.evaluate('GwenLane.mount().state.art')
    assert art in (['st_verdict','st_cheer','st_ok'] if width>=1200 else ['verdict','cheer','report'])
    count=p.locator(ACTOR).get_attribute('data-announcements')
    p.evaluate('directResultsPaint();directResultsPaint()')
    assert p.locator(ACTOR).get_attribute('data-announcements')==count,'result announced twice'
    if width==1280:
        p.set_viewport_size({'width':360,'height':1000});shown(p)
        assert p.evaluate('GwenLane.mount().state.art') in ['verdict','cheer','report']
        p.set_viewport_size({'width':1280,'height':1000});shown(p)
        assert p.evaluate('GwenLane.mount().state.art')==art
        assert p.locator(ACTOR).get_attribute('data-announcements')==count
    p.wait_for_timeout(2000)
    for i,kind in enumerate(['shy','sulk','cry'],1):
        p.locator('.gwen-lane-poke').click()
        assert p.evaluate('GwenLane.mount().state.art')==('st_' if width>=1200 else '')+kind
        snapshot(p,f'click-{i}',width)
        assert p.evaluate('GwenLane.mount().state.art')==('st_' if width>=1200 else '')+kind, 'capture missed short reaction'
    before=p.evaluate('GwenLane.mount().state.art');p.locator('.gwen-lane-poke').click()
    assert p.evaluate('GwenLane.mount().state.art')==before,'10-second poke lock missing'
    p.locator('#optbox > summary').click();p.locator('#gwen-quiet').check()
    shown(p);assert p.locator(ACTOR).is_visible(),'quiet mode hid result after poke'
    assert p.evaluate('GwenLane.mount().state.art')==art
    p.locator('#gwen-quiet').uncheck();p.locator('#optbox > summary').click()
    # New low result, same physical actor.
    p.evaluate('DIRECT.cache.clear();window.clearDirect=0;window.directDelay=100;directRun()')
    done(p);snapshot(p,'low',width);bounds(p)
    assert p.evaluate('GwenLane.mount().state.art') in (['st_cry','notes'] if width>=1200 else ['cry'])
    # Same payload re-execution can produce a new result object: announcement key must use result identity.
    assert not p.errors,p.errors
    p.close()


def timing(browser,base,width=1280):
    def setup(p):fake(p);p.clock.install()
    p=ready(browser,base,width,setup=setup);enter(p);shown(p)
    # Empty-slot reaction after 20 seconds, doze after 60 seconds of visible inactivity.
    p.clock.run_for(20500)
    assert p.evaluate('GwenLane.mount().state.art') in ['think','sulk','peek']
    p.clock.run_for(40500)
    p.wait_for_function("GwenLane.mount().state.art==='doze'",timeout=15000)
    snapshot(p,'doze',width)
    p.keyboard.press('Shift');assert p.evaluate('GwenLane.mount().state.art')=='wake'
    p.clock.run_for(1600)
    # Tab visibility pauses timers and a running WAAPI movement.
    p.evaluate("GwenLane.edit('put',3)")
    p.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
    state=p.evaluate('GwenLane.mount().state')
    p.clock.run_for(70000)
    assert p.evaluate('GwenLane.mount().state.clock')==state['clock']
    assert p.evaluate('GwenLane.mount().state.art')==state['art']
    p.evaluate('delete document.hidden;document.dispatchEvent(new Event("visibilitychange"))')
    p.emulate_media(reduced_motion='reduce')
    p.evaluate("GwenLane.edit('put',0)")
    assert not p.evaluate('GwenLane.mount().state.moving')
    x=p.evaluate('GwenLane.mount().state.x');p.clock.run_for(1000)
    assert p.evaluate('GwenLane.mount().state.x')==x
    # A genuinely offscreen lane must also stop its visible-time clock.
    p.set_viewport_size({'width':width,'height':300})
    p.evaluate('window.scrollTo(0,document.body.scrollHeight)');p.clock.run_for(100)
    off=p.evaluate('GwenLane.mount().state.clock');p.clock.run_for(5000)
    assert p.evaluate('GwenLane.mount().state.clock')==off
    p.set_viewport_size({'width':width,'height':1000});shown(p)
    p.locator('#optbox > summary').click();p.locator('#gwen-quiet').check()
    p.evaluate("GwenLane.edit('grown',0)")
    assert p.evaluate('GwenLane.mount().state.quiet')
    assert not p.evaluate('GwenLane.mount().state.moving')
    assert p.locator(ACTOR).is_hidden()
    p.evaluate("window.holdDirect=true;for(const s of R.filter(s=>MI.info.units.some(u=>u.id===s.uid)).slice(0,4))directChange({type:'put',key:s.key})")
    p.locator('#direct-run').click()
    p.wait_for_function("DIRECT.rows.now?.status==='running'");shown(p)
    assert p.locator(ACTOR).is_visible(),'quiet mode hid calculation'
    assert not p.evaluate('GwenLane.mount().state.moving')
    first=p.evaluate('GwenLane.mount().state.art');p.clock.run_for(19000)
    assert p.evaluate('GwenLane.mount().state.art')==first,'reduced cycle shorter than 20 seconds'
    p.clock.run_for(1500)
    assert p.evaluate('GwenLane.mount().state.art')!=first,'reduced cycle did not advance'
    p.locator('#direct-run').click()
    p.reload();p.wait_for_function('window._ready&&DIRECT.slots')
    assert p.locator('#gwen-quiet').is_checked()
    assert not p.errors,p.errors
    p.close()


SYNTH_SETUP='''() => {
 MI.info.units.forEach(u=>{u.level=200;u.star=5;u.resonance=10});
 MI.info=MyInfoReco.overwrite(MI.info,R,MI.growth,'clo',{slots:DIRECT.slots,priority:D.journeyPriority}).info;
 DIRECT.draft=DirectParty.empty();
 ['charlotte','scarlet','cristelle','serpang'].forEach(key=>DIRECT.draft=DirectParty.edit(DIRECT.draft,{type:'put',key}));
 DIRECT.draft.slots.slice(0,2).forEach(m=>{const u=MI.info.units.find(u=>u.id===BYKEY[m.key].uid);
   u.equip=[];u.skills.basic=3;u.skills.special=3;u.skills.ultimate=3;});
 MI.hash=MyInfoReco.hash(MI.info);DIRECT.valueKey=null;directPaint();
}'''


def real_growth(browser,base,mutant=False):
    def setup(p):
        if mutant:
            code=(ROOT/'direct_run.js').read_text(encoding='utf-8')
            old="make('grown',values.profile)"
            assert old in code
            p.route('**/direct_run.js',lambda route:route.fulfill(body=code.replace(old,"make('grown',original)"),content_type='application/javascript'))
    p=ready(browser,base,info=FULL,setup=setup);enter(p)
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='clo'))"))
    p.select_option('#stage',p.evaluate("String(cur.findIndex(s=>s.tab==='태양 회랑'&&s.name==='FLOOR 180'))"))
    p.evaluate(SYNTH_SETUP)
    original=p.evaluate('JSON.stringify(MI.info)')
    before=p.evaluate('DIRECT.values.values.map(v=>v.power)')
    for i in [0,1]:p.locator(f'[data-direct-action=grown][data-slot="{i}"]').click()
    after=p.evaluate('DIRECT.values.values.map(v=>v.power)')
    assert all(after[i]>before[i] for i in [0,1]) and before[2:]==after[2:]
    p.locator('#direct-run').click()
    p.wait_for_function("!DIRECT.active&&DIRECT.rows.now?.result&&DIRECT.rows.grown?.result",timeout=180000)
    data=p.evaluate("Object.fromEntries(['now','grown'].map(k=>[k,{result:DIRECT.rows[k].result,party:DIRECT.rows[k].snapshot.party}]))")
    assert p.evaluate('JSON.stringify(MI.info)')==original
    assert not p.errors,p.errors
    p.close()
    a,b=data['now'],data['grown']
    record={'stage':'clo/태양 회랑/FLOOR 180','runs':100,'before':before,'after':after,
            'now':a['result'],'grown':b['result'],'stats_changed':a['party']!=b['party']}
    (OUT/('growth-mutation.json' if mutant else 'growth-real.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    assert a['result']['prog']>0 and b['result']['prog']>0
    assert any(a['result'].get(k)!=b['result'].get(k) for k in ['prog','clear','ta','ttk']),'growth simulation had no effect'
    assert a['party']['units'][0]['stats_override']!=b['party']['units'][0]['stats_override']
    assert .1<b['result']['clear']<.9,'fixture must exercise an intermediate-clear stage'
    print('actual engine:',json.dumps({k:{x:record[k].get(x) for x in ['prog','clear','ta','power']} for k in ['now','grown']}),flush=True)


def video(browser,base):
    context=browser.new_context(viewport={'width':1280,'height':1000},record_video_dir=str(OUT/'video'),record_video_size={'width':1280,'height':1000})
    class Pages:
        def new_page(self,**kwargs):return context.new_page()
    p=ready(Pages(),base);enter(p)
    started=time.monotonic()
    for _ in range(4):
        p.locator('#direct-picker-inline [data-direct-action=pick]:enabled').first.click()
        p.locator('#direct-board-lane').scroll_into_view_if_needed();p.wait_for_timeout(600)
    p.wait_for_timeout(1800)
    p.locator('#direct-run').click();done(p)
    shown(p)
    p.wait_for_timeout(max(1500,int((15-(time.monotonic()-started))*1000)))
    assert not p.errors,p.errors
    recorded=p.video;context.close();recorded.save_as(str(OUT/'direct-put-run-result.webm'))
    print('saved actual-engine movement video',flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only',choices=['real','ui','timing']);ap.add_argument('--video',action='store_true');a=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        b=pw.chromium.launch()
        if a.video:video(b,base);b.close();return
        if a.only in [None,'ui']:
            no_account(b,base)
            for width in [360,1280,1600]:ui(b,base,width);print('UI',width,'passed',flush=True)
        if a.only in [None,'timing']:
            for width in [360,1280]:timing(b,base,width);print('timing',width,'passed',flush=True)
        if a.only in [None,'real']:
            real_growth(b,base)
            try:real_growth(b,base,True)
            except AssertionError as e:assert str(e)=='growth simulation had no effect';print('overwrite-removal mutation caught; production source unchanged',flush=True)
            else:raise AssertionError('overwrite-removal mutation survived')
        b.close()
    print('PASS Direct C E2E',flush=True)


if __name__=='__main__':main()
