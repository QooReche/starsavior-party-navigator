"""Wide layout and Gwen roaming: real renderers, geometry, mutations, captures.

python -X utf8 tests/e2e/test_wide_gwen.py [--shots] [--video]
Synthetic account/results only; server owns an ephemeral port and closes in finally.
"""
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / '_tmp'
TMP.mkdir(exist_ok=True)
os.environ['TEMP'] = os.environ['TMP'] = str(TMP)
from test_page import test_server, seed, FULL, wait_myinfo
from playwright.sync_api import sync_playwright


def fits(page):
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'horizontal overflow'


def centered(page, selector, parent):
    a, b = page.locator(selector).bounding_box(), page.locator(parent).bounding_box()
    assert a and b
    assert abs(a['x'] + a['width']/2 - b['x'] - b['width']/2) < 2, (selector, a, b)


def wide(page, width):
    box = page.locator('main').bounding_box()
    assert abs(box['width'] - min(width, 1440)) < 2, box
    fits(page)


def mutation(page, css, audit):
    style = page.add_style_tag(content=css)
    try:
        try:
            audit()
        except AssertionError:
            pass
        else:
            raise AssertionError('mutation survived: '+css)
    finally:
        style.evaluate('(s)=>s.remove()')
    audit()


def pause_roam(page, time):
    page.locator('.gwen-roam:visible').evaluate('''(e,time)=>{
      for(const a of e.getAnimations({subtree:true})){a.pause();a.currentTime=time;}
    }''', time)


def loading_audit(page, reduced=False, scope='#out'):
    w = scope+' [data-gwen]'
    if not reduced:
        assert page.locator(w).get_attribute('class').split().count('gwen-roam') == 1
    centered(page, w+' .gwen-track', scope)
    centered(page, w+' .gwen-caption', scope)
    if page.locator(scope+' .pbar').count():
        centered(page, scope+' .pbar', scope)
    if reduced:
        for selector in ('.gwen-traveler', '.gwen-scene', '.gwen-worker'):
            assert page.locator(w+' '+selector).evaluate('(e)=>getComputedStyle(e).animationName') == 'none'
        centered(page, w+' .gwen-scene', w+' .gwen-track')
        assert page.locator(w+' img').evaluate('(i)=>i.currentSrc.endsWith(".png")')
    else:
        for selector in ('.gwen-traveler', '.gwen-scene', '.gwen-worker'):
            assert page.locator(w+' '+selector).evaluate('(e)=>getComputedStyle(e).animationName') != 'none'
        pause_roam(page, 1800)
        a = page.locator(w+' .gwen-scene').bounding_box()
        caption = page.locator(w+' .gwen-caption').bounding_box()
        pause_roam(page, 5000)
        b = page.locator(w+' .gwen-scene').bounding_box()
        assert b['x'] > a['x'] + 30, (a,b)
        assert caption == page.locator(w+' .gwen-caption').bounding_box(), 'caption moved'
        assert b['y']+b['height'] <= caption['y'], 'Gwen overlaps caption'
        pause_roam(page, 6600)
        assert page.locator(w+' .gwen-scene').evaluate('(e)=>getComputedStyle(e).transform').startswith('matrix(-1'), 'direction did not flip'
        c = page.locator(w+' .gwen-scene').bounding_box()
        pause_roam(page, 6900)
        assert c == page.locator(w+' .gwen-scene').bounding_box(), 'inspection pause missing'
    fits(page)


def result_audit(page, width):
    assert page.locator('#out .result-team .gc').count() == 4
    a, b = (page.locator('#out '+s).first.bounding_box() for s in ('.result-team', '.result-summary'))
    if width >= 1200:
        assert b['x'] + b['width'] <= a['x'], 'summary is not beside the cards (left of them since 0647248)'
        assert abs(a['y']-b['y'])<2
        assert len(page.locator('#out .alternatives').first.evaluate('(e)=>getComputedStyle(e).gridTemplateColumns').split()) == 2
        choices = page.locator('#out .alternatives>.qrow')
        first, second = choices.nth(0).bounding_box(), choices.nth(1).bounding_box()
        assert abs(first['y']-second['y']) < 1 and abs(first['height']-second['height']) < 1
        assert choices.evaluate_all('(rows)=>rows.every(e=>getComputedStyle(e).borderTopWidth==="0px")')
    else:
        assert b['y'] + b['height'] <= a['y'], 'mobile/tablet reading order changed'
    fits(page)


def exercise(page, base, width, shots):
    page.goto(base+'/index.html?season=force',wait_until='networkidle')
    page.wait_for_function('window._ready')
    page.wait_for_timeout(700)
    wide(page,width)
    def shot(name):
        if shots:
            page.screenshot(path=str(ROOT/f'_shot_wide_{width}_{name}.png'),full_page=True)
    shot('home')
    if width==1280:
        mutation(page,'main{max-width:960px!important}',lambda:wide(page,width))
    page.evaluate('''() => {SIMQ.auto=false;SIMQ.kick=false;localStorage.setItem('pn.simauto','0');
      REQ=true;RECO.standard=true;document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();run(true);
      window.__loadSt=cur[$('stage').value];SIMQ.busy=1;SIMQ.loaded=true;SIMQ.screening=false;
      growthControlPlace(true);$('out').innerHTML=simProgress(__loadSt);
    }''')
    loading_audit(page)
    shot('loading')
    if width==1280:
        mutation(page,'.gwen-work{align-items:flex-start!important}',lambda:loading_audit(page))
        mutation(page,'.gwen-roam .gwen-traveler{animation:none!important}',lambda:loading_audit(page))
    page.emulate_media(reduced_motion='reduce')
    loading_audit(page,True)
    if width==1280:
        mutation(page,'.gwen-roam .gwen-traveler{animation:gwen-roam 12s infinite!important}',lambda:loading_audit(page,True))
    page.emulate_media(reduced_motion='no-preference')
    # Files stay centered, while progress and cancellation nodes survive updates.
    page.evaluate('''() => {SIMQ.screening=true;SIMQ.scr[scrKey(__loadSt,1)]={got:3,left:80};
      simProgressSync(document.querySelector('[data-k=progress]'),__loadSt);
      window.__cancel=document.querySelector('[data-simcancel]');
    }''')
    assert page.locator('#out .gwen-roam').count()==0
    centered(page,'#out .gwen-scene','#out')
    page.evaluate('SIMQ.scr[scrKey(__loadSt,1)].got=4;simProgressSync(document.querySelector("[data-k=progress]"),__loadSt)')
    assert page.evaluate('__cancel===document.querySelector("[data-simcancel]")')
    # Render actual recommendation cards and verdicts, with documented synthetic results.
    page.evaluate('''() => {recoClearTimer();SIMQ.busy=null;SIMQ.screening=false;SIMQ.auto=false;SIMQ.kick=false;
      localStorage.setItem('pn.simauto','0');REQ=true;RECO.standard=true;
      document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();run(true);
      const st=cur[$('stage').value];
      for(const box of Object.values(LASTQ))for(const t of box.rows){SIMQ.res[simSig(st,t)]={n:100,clear:.96,ci:[.91,.99],ta:35,ttk:35,frac:1,u:Object.fromEntries(t.keys.map(k=>[k,[.25,0]]))};}
      run(true);
    }''')
    page.wait_for_timeout(2000)
    result_audit(page,width)
    shot('result')
    if width==1280:
        mutation(page,'.result-layout{display:block!important}',lambda:result_audit(page,width))
    # Guild and Cosmo use their production search renderers, independent of workers.
    for kind,state,renderer in [('guild','GSR','renderGuildSearch(true)'),('cosmo','CSR','renderCosmoSearch()')]:
        page.evaluate(f'''() => {{MI.info={{units:[]}};growthControlPlace(true);$('out').innerHTML='';$('content').value=contents.findIndex(c=>c.key==='{kind}');
          Object.assign({state},{{phase:'run',msg:'3단계: 상위 팀 확인 중',done:2,total:80,sig:{'gsSig()' if kind=='guild' else 'csSig()'}}});{renderer};}}''')
        loading_audit(page,scope='#'+kind+'-search')
        centered(page,f'#{kind}-search [data-{"gs" if kind=="guild" else "cs"}=cancel]','#'+kind+'-search')
        page.evaluate(f'''() => {{
          const order=R.slice(0,4).map(s=>s.key),stats={{top:10000,mean:9000,clear:.95,frac:.98,cap:.95}};
          {state}.phase='done';{state}.pool=12;{state}.combos=20;{state}.finalists=3;{state}.runs=100;
          {state}.rows={'[{order,level:5,sup:"none",score:10000,...stats}]' if kind=='guild' else '[{sum:30000,teams:D.cosmoRaid.bosses.map(b=>({boss:b.key,order,level:5,st:stats}))}]'};
          {renderer};
        }}''')
        cards=page.locator('#'+kind+'-search '+('.season-result>.rowcards' if kind=='guild' else '.cs-boss>.cs-cards')).first
        assert cards.locator('.gc').count()==4
        if width>=1200:
            side=page.locator('#'+kind+'-search '+('.season-result>.season-score' if kind=='guild' else '.cs-boss>.cs-bh')).first
            a,b=cards.bounding_box(),side.bounding_box()
            assert a['x']+a['width']<=b['x'],(kind,a,b)
        fits(page)
        page.evaluate(f'$("{kind}-search").hidden=true')
    # A full synthetic roster exercises the actual responsive card grid.
    page.goto(base+'/index.html',wait_until='networkidle')
    page.evaluate('(info)=>miApply(info,{shared:true})',__import__('json').loads(Path(FULL).read_text(encoding='utf-8')))
    wait_myinfo(page)
    page.evaluate('miTab(true)')
    page.wait_for_timeout(400)
    cols=page.locator('#mi-list .mi-grid').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length')
    assert cols==({360:2,1024:5,1280:7,1600:8,1920:8}[width]),cols
    wide(page,width)
    shot('mine')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shots',action='store_true')
    ap.add_argument('--video',action='store_true')
    args=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            for width in [1024,1280,1600,1920,360]:
                context=browser.new_context(viewport={'width':width,'height':950})
                try:
                    page=context.new_page();page.set_default_timeout(15000)
                    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                    exercise(page,base,width,args.shots)
                    assert not errors,errors
                    print(f'PASS {width}px: width, result, centered loading, roam/flip/pause, reduced motion, guild/cosmo, roster',flush=True)
                finally:
                    context.close()
            if args.video:
                context=browser.new_context(viewport={'width':1280,'height':850},record_video_dir=str(TMP/'roam-video'),record_video_size={'width':1280,'height':850})
                page=context.new_page()
                page.goto(base+'/index.html',wait_until='networkidle')
                page.wait_for_function('window._ready')
                page.evaluate('''() => {SIMQ.auto=false;SIMQ.kick=false;localStorage.setItem('pn.simauto','0');REQ=true;RECO.standard=true;document.querySelectorAll('#own input').forEach((x,i)=>x.checked=i<8);updCount();run(true);SIMQ.busy=1;SIMQ.loaded=true;growthControlPlace(true);$('out').innerHTML=simProgress(cur[$('stage').value]);$('out').scrollIntoView({block:'center'});}''')
                page.wait_for_timeout(12500)
                context.close();page.video.save_as(str(ROOT/'_shot_roam.webm'))
        finally:
            browser.close()


if __name__=='__main__':
    main()
