"""Direct A: synthetic accounts only; screenshots under _tmp/direct-a.

Runs production page and real power adapters. No simulation result is fabricated.
The recommendation regression runs the existing real Pyodide pipeline separately.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import quote
from test_page import test_server, seed, SYNTH, wait_myinfo, wait_sim_done
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/direct-a'
OUT.mkdir(parents=True,exist_ok=True)


def ready(browser,base,width=1280,info=SYNTH,query='',touch=False,setup=None):
    page=browser.new_page(viewport={'width':width,'height':1000},has_touch=touch)
    seed(page,info)
    if info:
        groups=list(json.loads((ROOT/'data/growth.json').read_text(encoding='utf-8'))['tactics'])
        page.add_init_script('''(() => {const s=localStorage.getItem('pn.myinfo');if(!s)return;const i=JSON.parse(s);
          for(const k of %s)i.tactics.groups[k]={level:0,attack:0,defense:0,hp:0};localStorage.setItem('pn.myinfo',JSON.stringify(i));})()'''%json.dumps(groups))
    page.errors=[]
    page.on('pageerror',lambda e:page.errors.append(str(e)))
    if setup:setup(page)
    page.goto(base+'/index.html'+query)
    page.wait_for_function('window._ready && !!QK.d')
    if info:wait_myinfo(page)
    page.wait_for_timeout(450)
    assert not page.errors,page.errors
    return page


def enter(page):
    page.locator('#start-screen [data-pn-mode=direct]').click()
    page.wait_for_function('DIRECT.slots && !!DIRECT.values')
    assert page.locator('#direct-panel').is_visible()
    assert page.locator('#out').is_hidden()


def pick_four(page,mobile=False):
    host='#direct-picker-dialog' if mobile else '#direct-picker-inline'
    if mobile:page.locator('#direct-picker-open').tap()
    for _ in range(4):
        b=page.locator(host+' [data-direct-action=pick]:enabled').first
        if mobile:b.tap()
        else:b.focus();page.keyboard.press('Enter')
    if mobile:
        assert page.locator('#direct-picker-dialog').is_visible(),'continuous picker unexpectedly closed'
        page.locator('[data-direct-action=close]').tap()
    assert page.evaluate('DIRECT.draft.slots.every(Boolean)')


def geometry(page,width):
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'horizontal overflow'
    boxes=page.locator('.direct-slot').evaluate_all('(xs)=>xs.map(x=>{const r=x.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width}})')
    assert len(boxes)==4 and len({round(b['y']) for b in boxes})==1,'board must stay one row'
    assert [int(v) for v in page.locator('.direct-slot').evaluate_all('(xs)=>xs.map(x=>x.dataset.directSlot)')]==[2,0,1,3]
    summary=page.locator('#direct-panel .result-summary').bounding_box()
    team=page.locator('#direct-panel .result-team').bounding_box()
    if width>=1200:
        assert summary['x']<team['x'] and 290<=summary['width']<=340
        assert abs(summary['y']-team['y'])<2
    else:assert summary['y']<team['y']


def home_and_navigation(browser,base,width):
    page=ready(browser,base,width)
    assert page.locator('#start-screen').is_visible()
    assert page.locator('#mode-strip').is_hidden()
    assert page.locator('#start-growth #assume-growth').count()==1
    assert page.locator('.mi-tabs button').count()==2
    a=page.locator('.start-reco').bounding_box();b=page.locator('.start-direct').bounding_box()
    assert (a['x']<b['x'] if width>=1200 else a['y']<b['y'])
    assert page.evaluate('!REQ && !RECO.timer && SIMQ.busy==null')
    page.screenshot(path=str(OUT/f'start-{width}.png'),full_page=True)
    count=page.evaluate('history.length');enter(page)
    assert page.evaluate('history.length')==count+1
    for name in ['reco','direct','reco','direct']:
        page.locator(f'#mode-strip [data-pn-mode={name}]').click()
        assert page.evaluate('history.length')==count+1
        assert page.evaluate('!REQ && !RECO.timer && SIMQ.busy==null')
    page.reload();page.wait_for_function('window._ready && DIRECT.slots')
    assert page.locator('#direct-panel').is_visible()
    page.go_back();page.wait_for_function("DIRECT.mode==='home'")
    assert page.locator('#start-screen').is_visible()
    page.locator('.start-direct h2').click()
    assert page.locator('#direct-panel').is_visible()
    page.locator('#mode-strip [data-pn-mode=home]').click()
    page.wait_for_function("DIRECT.mode==='home'")
    assert page.locator('#start-screen').is_visible()
    assert not page.errors,page.errors
    page.close()


def editor(browser,base,width,touch=False):
    page=ready(browser,base,width,touch=touch);enter(page)
    assert '4명 미만' in page.locator('#direct-state').inner_text()
    assert page.locator('#direct-run').is_disabled()
    pick_four(page,touch)
    before=page.evaluate('JSON.stringify(MI.info)')
    original=page.evaluate('structuredClone(DIRECT.draft)')
    power=page.locator('[data-direct-power="0"]').inner_text()
    toggle=page.locator('[data-direct-action=grown][data-slot="0"]')
    if touch:toggle.tap()
    else:toggle.focus();page.keyboard.press('Space')
    assert page.locator('[data-direct-power="0"]').inner_text()!=power
    assert page.locator('#direct-total').inner_text()==page.locator('#direct-summary-power').inner_text()
    assert page.evaluate('!REQ && SIMQ.busy==null'),'toggle started simulation'
    assert page.evaluate('JSON.stringify(MI.info)')==before
    # Exact same value shown by the recommendation overwrite adapter, with shared slot/priority data.
    assert page.evaluate('''() => {
      const d=DIRECT.draft,c=directContext();
      const r=MyInfoReco.overwrite(MI.info,R,MI.growth,c.content,{excluded:R.filter(s=>!d.slots.some(m=>m?.key===s.key&&m.grown)).map(s=>s.key),slots:DIRECT.slots,priority:D.journeyPriority});
      const ids=[...new Set([...r.info.star_link.slots.map(x=>x.id),...d.slots.filter(m=>m?.grown).map(m=>BYKEY[m.key].uid)])];
      const final=MyInfoReco.profile(StarLink.withSlots(r.info,ids),R,MI.growth,c.content);
      return d.slots.every((m,i)=>DIRECT.values.values[i].power===final.results[m.key].power);
    }''')
    for i in [0,3]:
        b=page.locator(f'[data-direct-action=slot][data-slot="{i}"]')
        if touch:b.tap()
        else:b.focus();page.keyboard.press('Enter')
    swapped=page.evaluate('DIRECT.draft')
    assert swapped['slots'][3]['key']==original['slots'][0]['key'] and swapped['slots'][3]['grown']
    assert swapped['leader']==original['leader']
    if touch:
        page.locator('[data-direct-action=slot][data-slot="1"]').tap()
        leader=page.locator('#direct-selection [data-direct-action=leader]')
    else:leader=page.locator('.direct-slot[data-direct-slot="1"] [data-direct-action=leader]')
    leader.focus();page.keyboard.press('Space')
    assert page.evaluate('DIRECT.draft.leader===DIRECT.draft.slots[1].key')
    order=page.evaluate('JSON.stringify(DIRECT.draft)')
    page.locator('#direct-arrange').click()
    assert page.evaluate('DIRECT.draft.leader')==swapped['slots'][1]['key']
    assert page.evaluate('(key)=>DIRECT.draft.slots.find(s=>s.key===key)?.grown',original['slots'][0]['key'])
    page.locator('#direct-undo').click()
    assert page.evaluate('JSON.stringify(DIRECT.draft)')==order
    page.locator('[data-direct-action=clear]').click()
    assert page.evaluate('DIRECT.draft.slots.every(s=>s===null)')
    page.locator('#direct-undo').click();assert page.evaluate('JSON.stringify(DIRECT.draft)')==order
    assert page.locator('#direct-undo').is_disabled()
    if touch:
        page.evaluate('DIRECT.selected=null;directPaint()')
        page.locator('[data-direct-action=slot][data-slot="2"]').tap()
        page.locator('#direct-selection [data-direct-action=remove]').tap()
    else:page.locator('.direct-slot [data-direct-action=remove][data-slot="2"]').click()
    assert '4명 미만' in page.locator('#direct-state').inner_text()
    page.locator('#direct-undo').click()
    assert page.evaluate('JSON.stringify(DIRECT.draft)')==order
    # Recommendation exclusion must not exclude manual picks.
    assert page.evaluate('''() => {const s=R.find(s=>MI.info.units.some(u=>u.id===s.uid)&&!DIRECT.draft.slots.some(m=>m?.key===s.key));
      EXCL.add(s.key);directPaint();return !document.querySelector('#direct-picker-inline [data-key="'+s.key+'"]').disabled;}''')
    geometry(page,width)
    page.screenshot(path=str(OUT/f'direct-{width}.png'),full_page=True)
    page.reload();page.wait_for_function('window._ready && !!DIRECT.values')
    assert page.evaluate('JSON.stringify(DIRECT.draft)')==order
    page.locator('#tab-info').click();assert page.locator('#direct-panel').is_hidden()
    page.locator('#tab-reco').click();assert page.locator('#direct-panel').is_visible()
    assert not page.errors,page.errors
    page.close()


def power_link_conditions(browser,base):
    page=ready(browser,base);enter(page);pick_four(page)
    applied=page.evaluate('''async() => {const i=structuredClone(MI.info);i.units.forEach(u=>u.level=100);i.star_link_level=200;
      i.star_link={unlocked:true,level:200,source:[],slots:[{index:0,id:i.units.at(-1).id}]};return await miApply(i);}''')
    assert applied,'modern synthetic account was rejected'
    page.wait_for_timeout(350)
    page.locator('[data-direct-action=grown][data-slot="0"]').click()
    basepower=page.locator('#direct-total').inner_text()
    before=page.evaluate('JSON.stringify(MI.info)')
    assert page.locator('#direct-starlink').count()==0
    page.locator('[data-direct-action=grown][data-slot="1"]').click()
    assert page.locator('#direct-total').inner_text()!=basepower
    assert '가상 등록' not in page.locator('#direct-state').inner_text()
    page.locator('[data-direct-action=grown][data-slot="1"]').click()
    assert page.locator('#direct-total').inner_text()==basepower
    assert page.evaluate('JSON.stringify(MI.info)')==before
    draft=page.evaluate('JSON.stringify(DIRECT.draft)')
    restriction=page.evaluate('''() => {for(let i=0;i<contents.length;i++){const r=CFG.restrict[contents[i].name];if(r){const tab=Object.keys(r)[0];if(tab)return {i,tab};}}}''')
    page.select_option('#content',str(restriction['i']))
    # The tab select is the existing hidden filter; stage search is the public control.
    page.fill('#q',restriction['tab'])
    page.wait_for_timeout(350)
    page.select_option('#stage',index=0)
    page.wait_for_timeout(400)
    assert page.locator('.direct-invalid').filter(has_text='속성 제한').count()>0
    assert page.evaluate('JSON.stringify(DIRECT.draft)')==draft
    assert page.evaluate('!REQ && SIMQ.busy==null')
    # Data loading errors stay errors rather than silently using standard stats.
    page.evaluate("MI.growth=null;DIRECT.slots=null;DIRECT.valueKey=null;DIRECT.error='성장표 오류';directPaint()")
    assert '성장표 오류' in page.locator('#direct-state').inner_text()
    assert page.locator('#direct-total').inner_text()=='—'
    assert not page.errors,page.errors
    page.close()


def pending_and_motion(browser,base):
    page=ready(browser,base)
    page.emulate_media(reduced_motion='reduce')
    page.locator('#start-screen [data-pn-mode=reco]').click()
    assert page.locator('#out').evaluate('(e)=>e.getAnimations().length')==0
    page.evaluate("RECO.sharedPending=true;condChanged();directNavigate('direct')")
    page.wait_for_timeout(600)
    assert page.evaluate('!RECO.timer && !REQ && SIMQ.busy==null'),'pending recommendation launched after mode change'
    page.locator('#mode-strip [data-pn-mode=home]').click();page.wait_for_function("DIRECT.mode==='home'")
    page.emulate_media(reduced_motion='no-preference')
    durations=page.evaluate('''() => {document.querySelector('#start-screen [data-pn-mode=direct]').click();
      return $('direct-panel').getAnimations().map(a=>a.effect.getTiming().duration);}''')
    assert 250 in durations
    page.close()


def background_recommendation(browser,base):
    page=ready(browser,base)
    page.locator('#start-screen [data-pn-mode=reco]').click()
    page.locator('#out [data-go]').click()
    page.wait_for_function('SIMQ.busy!=null')
    request=page.evaluate('SIMQ.requestId')
    page.locator('#mode-strip [data-pn-mode=direct]').click()
    page.wait_for_function('DIRECT.slots && !!DIRECT.values')
    pick_four(page)
    draft=page.evaluate('JSON.stringify(DIRECT.draft)')
    page.evaluate("window.directLiveButton=$('direct-board').querySelector('button');run(true)")
    assert page.evaluate("directLiveButton===$('direct-board').querySelector('button')"),'recommendation callback replaced live editor controls'
    assert page.evaluate('SIMQ.requestId')>=request
    wait_sim_done(page,timeout=180000)
    assert page.locator('#direct-panel').is_visible() and page.locator('#out').is_hidden()
    assert page.locator('#direct-recommend').is_hidden(),'completed recommendation should be reusable before the first direct run'
    assert page.evaluate('JSON.stringify(DIRECT.draft)')==draft
    assert page.evaluate("directLiveButton===$('direct-board').querySelector('button')")
    page.locator('#mode-strip [data-pn-mode=reco]').click()
    assert page.locator('#out .party[data-party="1"] .qbox').is_visible()
    page.locator('#mode-strip [data-pn-mode=direct]').click()
    assert page.evaluate('JSON.stringify(DIRECT.draft)')==draft
    assert not page.errors,page.errors
    page.close()


def no_info_and_restrictions(browser,base):
    page=ready(browser,base,360,info=None,touch=True)
    assert page.locator('#start-screen [data-miopen]').is_visible()
    page.locator('#start-screen [data-miopen]').tap();assert page.locator('#drawer').is_visible();page.locator('#dclose').click()
    enter(page);pick_four(page,True)
    assert '내 정보 없음' in page.locator('#direct-state').inner_text()
    assert page.locator('[data-direct-action=grown]:enabled').count()==0
    assert page.locator('#direct-total').inner_text()!='0'
    speed=page.evaluate('miNum(QK.d.sv[DIRECT.draft.slots[2].key][4])')
    page.locator('.direct-stats').first.locator('summary').tap()
    assert '속 '+speed in page.locator('.direct-stats').first.inner_text()
    assert 'dp=' in page.evaluate('shareUrl()')
    page.select_option('#content',page.evaluate("String(contents.findIndex(c=>c.key==='guild'))"))
    page.wait_for_function("$('direct-state').textContent.includes('아직 안 됨')")
    assert page.evaluate('DIRECT.draft.slots.every(Boolean)')
    page.close()


def shared(browser,base,mutate=False):
    # A local draft is deliberately different from the received draft.
    draft={'v':1,'slots':[{'key':k,'grown':False} for k in ['luna','smile','carnelia','asherah-voyager']], 'leader':'luna','brk':'auto'}
    local={**draft,'leader':'smile','starLink':True}
    def setup(page):
        seed(page,extra={'pn.direct.v1':json.dumps(local)})
        # seed() has a session guard; add this one directly before first document.
        page.add_init_script('localStorage.setItem("pn.direct.v1",'+json.dumps(json.dumps(local))+')')
        if mutate:
            src=(ROOT/'direct_ui.js').read_text(encoding='utf-8')
            old="DIRECT.mode=SHARE.pm||((SHARE.dp||SHARE.cd)?'direct':(SHARE.c||AUTO||/[#&]shared=/.test(location.hash))?'reco':'home');"
            assert old in src
            page.route('**/direct_ui.js',lambda route:route.fulfill(body=src.replace(old,"DIRECT.mode='home';"),content_type='text/javascript'))
    page=ready(browser,base,query='?c=op&auto=1&pm=direct&dp='+quote(json.dumps({**draft,'starLink':True})),setup=setup)
    try:
        assert page.locator('#start-screen').is_hidden(),'shared link displayed half start screen'
        assert page.locator('#direct-panel').is_visible()
        assert page.evaluate('DIRECT.draft')==draft,'legacy link field changed the restored draft'
        assert page.evaluate('!AUTO && !REQ && !RECO.sharedPending && !RECO.timer && SIMQ.busy==null')
        page.locator('[data-direct-action=grown][data-slot="0"]').click()
        assert page.evaluate('JSON.parse(localStorage.getItem("pn.direct.v1"))')==local
        page.locator('#mode-strip [data-pn-mode=reco]').click()
        assert page.evaluate('!REQ && !RECO.timer')
        page.reload();page.wait_for_function('window._ready && !!MI.growth')
        assert page.locator('#out').is_visible(),'explicit recommendation mode lost on shared-link reload'
        assert page.locator('#direct-panel').is_hidden()
        assert page.evaluate('!REQ && !RECO.timer && DIRECT.shared')
        assert page.evaluate('JSON.parse(localStorage.getItem("pn.direct.v1"))')==local
        assert not page.errors,page.errors
    finally:page.close()


def missing_from_link(browser,base):
    d={'v':1,'slots':[{'key':k,'grown':False} for k in ['luna','gille','carnelia','smile']], 'leader':'luna'}
    page=ready(browser,base,query='?pm=direct&dp='+quote(json.dumps(d)))
    assert page.locator('.direct-invalid').filter(has_text='미보유').count()>0
    assert page.locator('#direct-run').is_disabled()
    assert page.locator('#direct-picker-inline [data-key=gille]').count()==0
    page.locator('#direct-picker-inline [data-direct-unowned]').check()
    page.locator('#direct-picker-inline [data-key=gille]').click()
    assert '보유하지 않음 · 고를 수 없음' in page.locator('#direct-state').inner_text()
    page.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',action='store_true');args=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        cases=[('start/navigation 1280',lambda:home_and_navigation(browser,base,1280)),('start/navigation 360',lambda:home_and_navigation(browser,base,360)),
          ('keyboard editor + power 1280',lambda:editor(browser,base,1280)),('touch editor + power 360',lambda:editor(browser,base,360,True)),
          ('StarLink + restrictions + data error',lambda:power_link_conditions(browser,base)),('pending auto + reduced motion',lambda:pending_and_motion(browser,base)),
          ('real recommendation continues behind direct editor',lambda:background_recommendation(browser,base)),
          ('no info + unsupported',lambda:no_info_and_restrictions(browser,base)),('share session isolation',lambda:shared(browser,base)),('unowned link',lambda:missing_from_link(browser,base))]
        try:
            for name,fn in cases:fn();print('PASS',name,flush=True)
            if args.mutations:
                try:shared(browser,base,True)
                except AssertionError as e:
                    assert 'shared link displayed half start screen' in str(e),str(e)
                    print('PASS mutation detected: half start screen on shared link',flush=True)
                else:raise AssertionError('shared/start mutation survived')
        finally:browser.close()
    print(f'{len(cases)} E2E groups passed; captures: {OUT}')


if __name__=='__main__':main()
