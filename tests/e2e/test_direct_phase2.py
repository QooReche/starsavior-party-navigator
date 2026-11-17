"""Phase 2 contracts, pointer interactions, actual StarLink simulation, and visual sheets.

Only synthetic accounts are used. All artifacts are excluded under _tmp/phase2.
"""
import argparse
import base64
import json
from pathlib import Path
from test_direct_party import ready, enter, pick_four, geometry
from test_direct_execution import fake
from test_page import test_server, FULL
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_tmp/phase2'
OUT.mkdir(parents=True,exist_ok=True)


def start(browser,base,width=1280,info=True,mutations=None):
    def setup(p):
        fake(p)
        for name,(old,new) in (mutations or {}).items():
            source=(ROOT/name).read_text(encoding='utf-8')
            assert old in source,name
            body=source.replace(old,new)
            def responder(body,kind):
                return lambda route:route.fulfill(body=body,content_type=kind)
            p.route('**/'+name,responder(body,'text/css' if name.endswith('.css') else 'application/javascript'))
    kw={'setup':setup,'touch':width==360}
    if not info:kw['info']=None
    p=ready(browser,base,width,**kw);enter(p);pick_four(p,width==360)
    p.evaluate("window.directDelay=12;$('direct-comparison').open=true;$('direct-with').open=true")
    return p


def finished(p):
    p.wait_for_function('!DIRECT.active&&!DIRECT.bundle?.running',timeout=120000)
    assert not p.errors,p.errors


def choice(p,mode):
    p.locator('#direct-with-reco').set_checked(mode>0)
    if mode:p.locator('#direct-with-growth').set_checked(mode==2)


def run(p,only=None):
    if only:p.evaluate('(kind)=>{void directRun(kind)}',only)
    else:p.locator('#direct-run').click()
    finished(p)


def bundle_contract(browser,base,width=1280):
    p=start(browser,base,width)
    # Unchecked recommendation must never start. Execution choices cannot stale direct results.
    run(p);assert p.evaluate("directPosts.every(m=>m.owner==='direct')")
    old=p.evaluate('DIRECT.rows.now.sig'),p.evaluate('DIRECT.revision')
    choice(p,1)
    assert p.evaluate('DIRECT.rows.now.sig===DIRECT.expected.now.sig')
    assert (p.evaluate('DIRECT.rows.now.sig'),p.evaluate('DIRECT.revision'))==old
    assert p.evaluate("!('withReco' in DirectParty.share(DIRECT.draft))&&!('growth' in JSON.parse(localStorage.getItem('pn.direct.with.v1')))")
    reports=int(p.locator('.gwen-lane-actor').get_attribute('data-announcements') or 0)
    p.evaluate("window.directDelay=100;void directRun()")
    p.wait_for_function("DIRECT.bundle.current==='reco'&&RECO.task&&!RECO.task.done")
    assert '82%' in p.locator('#direct-result-summary').inner_text()
    p.evaluate("directNavigate('reco')")
    assert p.locator('#out [data-bundle-progress]').is_visible(),'recommendation tab lost ongoing work'
    p.evaluate("directNavigate('direct')")
    p.screenshot(path=str(OUT/f'bundle-progress-{width}.png'),full_page=True)
    # Editing cancels only the direct row, preserves recommendation ownership, focus and search.
    p.evaluate("window.phase2Task=RECO.task;window.phase2Before=directPosts.length;directChange({type:'swap',a:0,b:1})")
    assert p.evaluate('RECO.task===phase2Task&&!RECO.task.cancelled'),'draft edit cancelled recommendation'
    if width>760:
        field=p.locator('#direct-picker-inline [data-direct-search]');field.fill('루');field.focus()
        p.wait_for_timeout(250)
        assert field.input_value()=='루' and field.evaluate('e=>document.activeElement===e')
    finished(p)
    assert int(p.locator('.gwen-lane-actor').get_attribute('data-announcements') or 0)-reports<=2,'more than two bundle reports'
    assert p.evaluate("DIRECT.bundle.steps.every(s=>s.status==='done')")
    assert p.evaluate("DIRECT.compare.result===SIMQ.res[simSig(cur[$('stage').value],LASTQ[1].rows[0])]")
    assert p.locator('[data-direct-row=now].direct-past').count()==1
    run(p);posts=p.evaluate('directPosts.length')
    p.locator('#direct-steps-toggle').click()
    assert '추천 탭 결과 사용' in p.locator('#direct-steps').inner_text()
    p.locator('[data-direct-action=compare-toggle][data-kind=reco]').click()
    p.locator('[data-direct-action=view-reco]').click();p.wait_for_timeout(250)
    assert p.evaluate('directPosts.length')==posts,'tab navigation recalculated recommendation'
    p.locator('#mode-strip [data-pn-mode=direct]').click()
    choice(p,2)
    assert p.evaluate("$('assume-growth').checked&&growthOptions().growth")
    assert p.locator('[data-direct-row=reco].direct-past').count()==1
    p.evaluate('window.directDelay=12');run(p)
    assert p.evaluate("GROW.phase==='done'&&DIRECT.growthCompare&&DIRECT.bundle.steps.every(s=>s.status==='done')")
    assert p.locator('[data-direct-row]').count()==4
    posts=p.evaluate('directPosts.length');run(p)
    assert p.evaluate('directPosts.length')==posts,'completed shared work was recomputed'
    p.locator('[data-direct-action=compare-toggle][data-kind=growth]').click()
    p.locator('[data-direct-action=view-growth]').click();p.wait_for_timeout(200)
    assert p.locator('#result-tab-growth').get_attribute('aria-selected')=='true'
    assert p.evaluate('directPosts.length')==posts
    p.evaluate("$('assume-growth').checked=false;$('assume-growth').dispatchEvent(new Event('change'))")
    assert not p.locator('#direct-with-growth').is_checked(),'growth controls diverged'
    p.locator('#mode-strip [data-pn-mode=direct]').click();choice(p,2);run(p)
    p.screenshot(path=str(OUT/f'bundle-complete-{width}.png'),full_page=True)
    choice(p,0);run(p)
    assert p.locator('#direct-steps').is_hidden(),'old bundle steps survived a direct-only run'
    geometry(p,width);assert not p.errors,p.errors;p.close()


def combinations(browser,base):
    for mode in [0,1,2]:
        for state in ['absent','complete','running']:
            p=start(browser,base);choice(p,mode)
            if state!='absent':
                p.evaluate("window.directDelay=30;directNavigate('reco');showReco()")
                p.wait_for_function('SIMQ.busy!=null')
                if state=='complete':
                    p.wait_for_function("directRecoReady()&&(!growthEnabled()||GROW.phase==='done')",timeout=120000)
                p.evaluate("directNavigate('direct')")
            before=p.evaluate('directPosts.length');run(p)
            if state=='complete' and mode:
                assert p.evaluate("directPosts.slice(%d).every(m=>m.owner==='direct')"%before),'cached comparison recalculated'
            if mode:
                assert p.evaluate("DIRECT.compare&&DIRECT.bundle.steps.every(s=>s.status==='done')"),p.evaluate('DIRECT.bundle.steps')
                if mode==2:assert p.evaluate("GROW.phase==='done'&&!!DIRECT.growthCompare")
            assert not p.errors,p.errors;p.close()
            print('PASS choices',mode,state,flush=True)


def cancellation(browser,base):
    for skip in ['reco','growth','all','condition']:
        p=start(browser,base);choice(p,2)
        p.evaluate('window.directDelay=80;void directRun()')
        p.wait_for_function("DIRECT.bundle.current==='reco'&&RECO.task&&!RECO.task.done")
        if skip in ['reco','growth']:p.locator(f'#direct-steps [data-direct-action=skip][data-kind={skip}]').click()
        elif skip=='all':p.locator('#direct-run').click()
        else:p.evaluate("$('stage').selectedIndex=1;condChanged()")
        finished(p)
        assert p.evaluate("!!DIRECT.rows.now.result"),'completed direct result was discarded'
        statuses=p.evaluate('Object.fromEntries(DIRECT.bundle.steps.map(s=>[s.kind,s.status]))')
        if skip=='reco':assert statuses['reco']==statuses['growth']=='skipped'
        if skip=='growth':assert statuses['reco']=='done' and statuses['growth']=='skipped'
        if skip in ['all','condition']:assert statuses['reco']==statuses['growth']=='cancelled'
        p.close()
    # Cancel only a joined bundle: an independently started recommendation keeps running.
    p=start(browser,base);choice(p,1);p.evaluate("window.directDelay=90;showReco();void directRun()")
    p.wait_for_function("DIRECT.bundle.steps.find(s=>s.kind==='reco')?.joined")
    p.locator('#direct-run').click()
    assert p.evaluate('SIMQ.busy!=null'),'cancelled independent recommendation tab request'
    p.close()


def center(p,selector):
    loc=p.locator(selector);loc.scroll_into_view_if_needed();r=loc.bounding_box();return (r['x']+r['width']/2,r['y']+r['height']/2)


def drag(p,source,target,width=1280,cancel=False):
    p.locator('#direct-board').scroll_into_view_if_needed()
    a=center(p,source)
    if width==360:
        p.dispatch_event(source,'pointerdown',{'pointerId':51,'pointerType':'touch','isPrimary':True,'button':0,'clientX':a[0],'clientY':a[1]})
        p.wait_for_timeout(370)
    else:p.mouse.move(*a);p.mouse.down();p.mouse.move(a[0]+7,a[1])
    assert p.evaluate('!!DIRECT.drag?.active')
    before=p.evaluate('DIRECT.draft'),p.evaluate('DIRECT.revision')
    p.evaluate('directPaint();directRefresh()')
    assert p.evaluate('!!DIRECT.drag?.source.isConnected'),'background repaint detached dragged card'
    z=center(p,target)
    if width==360:p.dispatch_event('#direct-panel','pointermove',{'pointerId':51,'pointerType':'touch','isPrimary':True,'clientX':z[0],'clientY':z[1]})
    else:p.mouse.move(*z,steps=4)
    assert p.evaluate('DIRECT.drag.target!=null')
    p.screenshot(path=str(OUT/f'dragging-{width}.png'),full_page=True)
    assert p.evaluate('DIRECT.drag?.active'), 'drag cancelled during capture'
    # Full-page capture temporarily changes the scroll viewport; resume at the live target.
    z=center(p,target)
    if width==360:p.dispatch_event('#direct-panel','pointermove',{'pointerId':51,'pointerType':'touch','isPrimary':True,'clientX':z[0],'clientY':z[1]})
    else:p.mouse.move(*z)
    p.evaluate('window.phase2Drop={slot:DIRECT.drag.target?.slot,remove:DIRECT.drag.target?.remove,y:DIRECT.drag.y,scroll:scrollY}')
    if cancel:p.keyboard.press('Escape')
    if width==360:p.dispatch_event('#direct-panel','pointerup',{'pointerId':51,'pointerType':'touch','isPrimary':True,'clientX':z[0],'clientY':z[1]})
    else:p.mouse.up()
    assert p.evaluate('!DIRECT.drag')
    if cancel:assert (p.evaluate('DIRECT.draft'),p.evaluate('DIRECT.revision'))==before
    p.wait_for_timeout(720)


def pointers(browser,base,width=1280):
    p=start(browser,base,width)
    a='[data-direct-action=slot][data-slot="0"]';b='[data-direct-action=slot][data-slot="3"]'
    p.evaluate("directChange({type:'leader',key:DIRECT.draft.slots[0].key})")
    p.evaluate("directChange({type:'grown',slot:0,value:true});window.phase2Edits=[];window.phase2Change=directChange;directChange=a=>{phase2Edits.push(a);phase2Change(a)};window.phase2Gwen=[];window.phase2Edit=GwenLane.edit;GwenLane.edit=(a,i)=>{phase2Gwen.push(a);phase2Edit(a,i)};void 0")
    initial=p.evaluate('DIRECT.draft')
    drag(p,a,b,width)
    actual=p.evaluate('DIRECT.draft')
    expected=p.evaluate('(d)=>DirectParty.edit(d,{type:"swap",a:0,b:3})',initial)
    assert actual==expected,{'actual':actual,'expected':expected,'edits':p.evaluate('phase2Edits'),'target':p.evaluate('phase2Drop')}
    assert p.evaluate("phase2Edits.length===1&&phase2Edits[0].type==='swap'&&phase2Gwen.length===1"),p.evaluate('({edits:phase2Edits,gwen:phase2Gwen})')
    assert '맞바꿈' in p.locator('#direct-state').inner_text()
    p.locator('#direct-undo').click();assert p.evaluate('DIRECT.draft')==initial
    drag(p,a,b,width,cancel=True);assert p.evaluate('DIRECT.draft')==initial
    drag(p,a,'#direct-drop-remove',width)
    assert p.evaluate('DIRECT.draft.slots[0]===null')
    p.locator('#direct-undo').click();assert p.evaluate('DIRECT.draft')==initial
    p.evaluate("directChange({type:'remove',slot:3})");before=p.evaluate('DIRECT.draft')
    drag(p,a,b,width)
    assert p.evaluate('DIRECT.draft')==p.evaluate('(d)=>DirectParty.edit(d,{type:"swap",a:0,b:3})',before)
    if width==1280:
        source='#direct-picker-inline [data-direct-action=pick]:enabled';key=p.locator(source).first.get_attribute('data-key')
        before=p.evaluate('DIRECT.draft');drag(p,source+' >> nth=0',a,width)
        assert p.evaluate('DIRECT.draft')==p.evaluate('(x)=>DirectParty.edit(x.d,{type:"put",key:x.k,slot:0})',{'d':before,'k':key})
    # Touch bounds and mouse threshold are numeric assertions, not screenshot-only claims.
    rects=p.locator('.direct-member,.direct-grow').evaluate_all('(xs)=>xs.map(x=>({w:x.getBoundingClientRect().width,h:x.getBoundingClientRect().height}))')
    assert all(x['w']>=64 and x['h']>=64 for x in rects),rects
    p.screenshot(path=str(OUT/f'editing-{width}.png'),full_page=True)
    geometry(p,width);assert not p.errors,p.errors;p.close()


def faces(browser,base,width):
    p=ready(browser,base,width,info=None);enter(p)
    keys=p.evaluate('R.map(s=>s.key)');assert len(keys)==59
    tiles=[]
    for offset in range(0,len(keys),4):
        batch=keys[offset:offset+4]
        p.evaluate('(ks)=>{DIRECT.draft=DirectParty.empty();ks.forEach((key,slot)=>DIRECT.draft=DirectParty.edit(DIRECT.draft,{type:"put",key,slot}));directPaint()}',batch)
        p.locator('#direct-board').scroll_into_view_if_needed()
        p.wait_for_function("[...document.querySelectorAll('.direct-member .art')].every(i=>i.complete&&i.naturalWidth>0)")
        for i,key in enumerate(batch):
            loc=p.locator(f'[data-direct-action=slot][data-slot="{i}"]')
            r=loc.bounding_box();assert abs(r['height']/r['width']-1.12)<.03,r
            tiles.append({'key':key,'url':'data:image/png;base64,'+base64.b64encode(loc.screenshot()).decode()})
    p.set_content('<canvas id="sheet"></canvas><style>body{margin:0}</style>')
    p.evaluate('''async tiles=>{
      const imgs=await Promise.all(tiles.map(t=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve(i);i.src=t.url})));
      const w=Math.max(...imgs.map(i=>i.width)),h=Math.max(...imgs.map(i=>i.height))+24,c=document.getElementById('sheet');
      c.width=8*(w+8);c.height=8*(h+8);const x=c.getContext('2d');x.fillStyle='#121827';x.fillRect(0,0,c.width,c.height);x.fillStyle='white';x.font='11px sans-serif';
      imgs.forEach((im,i)=>{const a=(i%8)*(w+8),b=Math.floor(i/8)*(h+8);x.drawImage(im,a,b);x.fillText(tiles[i].key,a+2,b+h-7)});
    }''',tiles)
    p.locator('#sheet').screenshot(path=str(OUT/f'faces-59-{width}.png'));p.close()


def real_starlink(browser,base,mutant=False):
    def setup(p):
        if mutant:
            code=(ROOT/'direct_party.js').read_text(encoding='utf-8')
            old='if(!ids.includes(unit.id))ids.push(unit.id);';assert old in code
            p.route('**/direct_party.js',lambda r:r.fulfill(body=code.replace(old,''),content_type='application/javascript'))
    p=ready(browser,base,info=FULL,setup=setup);enter(p)
    p.select_option('#content',p.evaluate("String(contents.findIndex(c=>c.key==='clo'))"))
    p.select_option('#stage',p.evaluate("String(cur.findIndex(s=>s.tab==='태양 회랑'&&s.name==='FLOOR 180'))"))
    p.evaluate('''() => {
      MI.info.units.forEach(u=>{u.level=200;u.star=5;u.resonance=10});
      MI.info.star_link={unlocked:true,level:200,source:[],slots:[]};
      MI.info=MyInfoReco.overwrite(MI.info,R,MI.growth,'clo',{slots:DIRECT.slots,priority:D.journeyPriority}).info;
      DIRECT.draft=DirectParty.empty();
      ['charlotte','scarlet','cristelle','serpang'].forEach((key,slot)=>DIRECT.draft=DirectParty.edit(DIRECT.draft,{type:'put',key,slot}));
      DIRECT.draft.slots.forEach(m=>MI.info.units.find(u=>u.id===BYKEY[m.key].uid).level=191);
      MI.hash=MyInfoReco.hash(MI.info);MI.profiles={};DIRECT.valueKey=null;directPaint();
    }''')
    account=p.evaluate('JSON.stringify(MI.info)')
    before=p.evaluate('DIRECT.values.values.map(v=>({power:v.power,stats:v.stats}))')
    if not mutant:
        for width in [1280,360]:
            p.set_viewport_size({'width':width,'height':1000});p.screenshot(path=str(OUT/f'starlink-before-{width}.png'),full_page=True)
    for i in range(4):p.locator(f'[data-direct-action=grown][data-slot="{i}"]').click()
    after=p.evaluate('DIRECT.values.values.map(v=>({power:v.power,stats:v.stats}))')
    if not mutant:
        assert all(a['power']>b['power'] and a['stats']!=b['stats'] for a,b in zip(after,before))
        assert p.evaluate('DIRECT.values.linked.length===4')
        for width in [360,1280]:
            p.set_viewport_size({'width':width,'height':1000});p.screenshot(path=str(OUT/f'starlink-after-{width}.png'),full_page=True)
    p.locator('#direct-run').click()
    p.wait_for_function("!DIRECT.active&&DIRECT.rows.now?.result&&DIRECT.rows.grown?.result",timeout=180000)
    data=p.evaluate("Object.fromEntries(['now','grown'].map(k=>[k,{result:DIRECT.rows[k].result,party:DIRECT.rows[k].snapshot.party}]))")
    assert p.evaluate('JSON.stringify(MI.info)')==account
    assert not p.errors,p.errors
    if not mutant:
        # A fully grown, already registered member has no further StarLink change on toggle.
        assert p.evaluate('''() => {const info=structuredClone(MI.info);info.star_link.slots=DIRECT.draft.slots.map((m,index)=>({index,id:BYKEY[m.key].uid}));
          const d=DirectParty.draft(DIRECT.draft),ctx={...directContext(),info,growth:MI.growth,slots:DIRECT.slots,priority:D.journeyPriority};
          d.slots.forEach(m=>m.grown=false);const a=DirectParty.powers(d,ctx);d.slots.forEach(m=>m.grown=true);const b=DirectParty.powers(d,ctx);
          return a.total===b.total&&JSON.stringify(a.values)===JSON.stringify(b.values)&&b.linked.length===0;}''')
    p.close()
    record={'before':before,'after':after,**data}
    (OUT/('starlink-mutant.json' if mutant else 'starlink-real.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    a,b=data['now'],data['grown'];assert a['result']['prog']>0 and b['result']['prog']>0
    assert a['party']!=b['party'] and any(a['result'].get(k)!=b['result'].get(k) for k in ['prog','clear','ta','ttk']),'StarLink execution effect missing'
    print('PASS actual StarLink',[(k,data[k]['result']['clear'],data[k]['result']['prog']) for k in data],flush=True)


def real_checks(browser,base):
    real_starlink(browser,base)
    try:real_starlink(browser,base,True)
    except AssertionError as e:
        assert str(e)=='StarLink execution effect missing',str(e)
        print('CAUGHT StarLink removal in actual engine; production files unchanged',flush=True)
    else:raise AssertionError('StarLink mutation survived')


def gestures(browser,base):
    p=start(browser,base);a='[data-direct-action=slot][data-slot="0"]'
    x,y=center(p,a);before=p.evaluate('DIRECT.draft')
    p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+5,y);assert not p.evaluate('!!DIRECT.drag?.active');p.mouse.up()
    assert p.evaluate('DIRECT.draft')==before and p.evaluate('DIRECT.selected')==0
    p.close()
    p=start(browser,base,360);cdp=p.context.new_cdp_session(p)
    def touch(kind,xy=None):cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':[] if xy is None else [{'x':xy[0],'y':xy[1],'id':1}]})
    x,y=center(p,a);before=p.evaluate('DIRECT.draft');touch('touchStart',(x,y));touch('touchMove',(x,y-25));p.wait_for_timeout(400)
    assert not p.evaluate('!!DIRECT.drag?.active');touch('touchEnd');assert p.evaluate('DIRECT.draft')==before
    x,y=center(p,a);z=center(p,'[data-direct-action=slot][data-slot="3"]')
    touch('touchStart',(x,y));p.wait_for_timeout(370);assert p.evaluate('!!DIRECT.drag?.active')
    touch('touchMove',z);p.wait_for_timeout(50)
    assert p.evaluate('!!DIRECT.drag?.active'),'native panning cancelled the long-press drag'
    touch('touchEnd');p.wait_for_timeout(700)
    assert p.evaluate('DIRECT.draft')==p.evaluate('(d)=>DirectParty.edit(d,{type:"swap",a:0,b:3})',before)
    p.close()


def review_regressions(browser,base):
    p=start(browser,base);choice(p,2);run(p)
    # A completed legacy result and a selected weaker alternative must acquire the same baseline.
    p.evaluate('''() => {const c=contents[$('content').value],st=cur[$('stage').value],rows=LASTQ[1].rows;
      SIMQ.res[simSig(st,rows[0])].clear=.9;SIMQ.res[simSig(st,rows[1])].clear=.4;
      PICK[c.key+'|'+st.tab+'|'+st.name+'|1']=rows[1].keys.slice().sort().join(',');
      GROW.result.best.clear=.7;delete GROW.result.baselineFirst;growthPaint();}''')
    assert p.evaluate('GROW.result.baseline.clear===.4')
    posts=p.evaluate('directPosts.length');run(p)
    p.evaluate('growthPaint()')
    assert p.evaluate('DIRECT.growthCompare.none&&GROW.result.baseline.clear===.9&&GROW.result.baselineFirst')
    assert p.evaluate('directPosts.length')==posts
    p.locator('[data-direct-action=compare-toggle][data-kind=growth]').click()
    assert '더 나은' in p.locator('[data-direct-row=growth]').inner_text()
    assert p.locator('#growth-result').get_attribute('data-state')=='none'
    p.evaluate("$('q').value='__phase2_missing_stage__';refreshStages()")
    assert not p.errors,p.errors
    assert p.locator('[data-direct-row=growth].direct-past').count()==1
    p.evaluate("$('q').value='';refreshStages()")
    for content in ['guild','cosmo']:
        p.evaluate("key=>{$('content').value=Object.keys(contents).find(k=>contents[k].key===key);refreshTabs();directPaint()}",content)
        assert p.locator('[data-direct-action=run-row]:enabled').count()==0
        posts=p.evaluate('directPosts.length')
        p.evaluate("void directRun('reco');void directRun('growth')")
        p.wait_for_timeout(150)
        assert p.evaluate('directPosts.length')==posts,'unsupported content bypassed validation'
    assert not p.errors,p.errors;p.close()
    p=start(browser,base,info=False);choice(p,1)
    assert p.locator('#direct-with-growth').is_disabled()
    controls=p.evaluate("[$('grow').value,[...document.querySelectorAll('#own input')].map(x=>x.checked)]")
    run(p)
    assert p.evaluate("[$('grow').value,[...document.querySelectorAll('#own input')].map(x=>x.checked)]")==controls
    p.locator('[data-direct-action=compare-toggle][data-kind=reco]').click()
    assert '표준 육성 기준' in p.locator('[data-direct-row=reco]').inner_text()
    assert not p.errors,p.errors;p.close()


def drag_safety(browser,base):
    p=start(browser,base);source='[data-direct-action=slot][data-slot="0"]'
    p.locator('#direct-picker-inline [data-direct-unowned]').check()
    for selector in ['#direct-picker-inline [data-direct-action=pick]:disabled','#direct-picker-inline [data-direct-action=unowned]']:
        p.dispatch_event(selector+' >> nth=0','pointerdown',{'pointerId':23,'pointerType':'mouse','isPrimary':True,'button':0,'clientX':10,'clientY':10})
        assert not p.evaluate('!!DIRECT.drag'),'ineligible candidate could drag'
    for cancel in ['outside','pointercancel','quiet','reduce']:
        before=p.evaluate('DIRECT.draft')
        if cancel=='quiet':p.evaluate("document.documentElement.dataset.gwenQuiet='true'")
        if cancel=='reduce':p.emulate_media(reduced_motion='reduce')
        x,y=center(p,source);p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+7,y)
        assert p.evaluate('!!DIRECT.drag?.active')
        if cancel=='outside':p.mouse.move(2,100);p.mouse.up()
        elif cancel=='pointercancel':p.dispatch_event('#direct-panel','pointercancel',{'pointerId':1});p.mouse.up()
        else:p.keyboard.press('Escape');assert p.locator('.direct-drag-ghost').count()==0;p.mouse.up()
        assert p.evaluate('DIRECT.draft')==before and not p.evaluate('!!DIRECT.drag')
        p.wait_for_timeout(720)
    p.close()


def mutations(browser,base):
    def signature(p):
        run(p);p.evaluate('DIRECT.withReco=true;directPaint()')
        assert p.evaluate('DIRECT.rows.now.sig===DIRECT.expected.now.sig'),'execution choice entered signature'
    def owner(p):
        choice(p,1);p.evaluate('window.directDelay=80;void directRun()')
        p.wait_for_function("DIRECT.bundle.current==='reco'&&RECO.task&&!RECO.task.done")
        p.evaluate("directChange({type:'swap',a:0,b:1})")
        assert p.evaluate('!RECO.task.cancelled'),'edit killed recommendation'
    def baseline(p):
        choice(p,1);run(p)
        p.evaluate("window.growthBaseline=()=>({clear:.123,n:100});directCollectRecommendation()")
        assert p.evaluate("DIRECT.compare.result===SIMQ.res[simSig(cur[$('stage').value],LASTQ[1].rows[0])]")
    def options(p):
        p.evaluate("DIRECT.withReco=true;directBundleControls();$('direct-with-growth').checked=true;$('direct-with-growth').dispatchEvent(new Event('change'))")
        assert p.evaluate("$('assume-growth').checked===true&&growthOptions().growth===true"),'duplicated growth option'
    def crop(p):
        r=p.locator('[data-direct-action=slot][data-slot="0"]').bounding_box()
        assert abs(r['height']/r['width']-1.12)<.03,'fixed-height crop returned'
    def editing(p):
        p.evaluate("window.phase2Calls=0;window.oldChange=directChange;directChange=a=>{phase2Calls++;oldChange(a)};void 0")
        drag(p,'[data-direct-action=slot][data-slot="0"]','[data-direct-action=slot][data-slot="3"]')
        assert p.evaluate('phase2Calls===1'),'drag bypassed the shared editor'
    def deferred(p):
        a='[data-direct-action=slot][data-slot="0"]';x,y=center(p,a)
        p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+7,y);p.evaluate('directPaint()')
        assert p.evaluate('DIRECT.drag?.source.isConnected'),'repaint detached the drag source'
    def click(p):
        a='[data-direct-action=slot][data-slot="0"]';b='[data-direct-action=slot][data-slot="3"]'
        x,y=center(p,a);p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+7,y);p.mouse.move(*center(p,b));p.mouse.up()
        # Browser-generated follow-up click has been consumed; reset then inject the next exact sequence.
        p.wait_for_timeout(720);x,y=center(p,a)
        p.dispatch_event(a,'pointerdown',{'pointerId':91,'pointerType':'touch','isPrimary':True,'button':0,'clientX':x,'clientY':y})
        p.wait_for_timeout(370);z=center(p,b)
        p.dispatch_event('#direct-panel','pointermove',{'pointerId':91,'clientX':z[0],'clientY':z[1]})
        p.dispatch_event('#direct-panel','pointerup',{'pointerId':91})
        p.dispatch_event(b,'click')
        assert p.evaluate('DIRECT.selected===null'),'drag click selected the slot again'
    def empty_stage(p):
        choice(p,2);run(p)
        error=p.evaluate("() => {try{$('q').value='__phase2_missing_stage__';refreshStages();return '';}catch(e){return e.message;}}")
        assert not error,'missing stage caused an exception: '+error
    cases=[
      ('execution choice in signature','direct_run.js',('versions:{...DIRECT.versions,account:', 'versions:{...DIRECT.versions,withReco:DIRECT.withReco,account:'),signature),
      ('edit cancels recommendation','direct_run.js',("directCancel('입력이 바뀜');", "directCancel('입력이 바뀜');recoTaskCancel('입력이 바뀜');"),owner),
      ('selected growthBaseline','direct_run.js',('result=SIMQ.res[sig]','result=growthBaseline(c,st)'),baseline),
      ('second growth setting','direct_bundle.js',("$('assume-growth').checked=e.target.checked;", "DIRECT.otherGrowth=e.target.checked;"),options),
      ('crop reverted','direct.css',('aspect-ratio:1/1.12','aspect-ratio:auto;height:110px'),crop),
      ('separate drag edit path','direct_drag.js',('      directChange(action);','      DIRECT.draft=DirectParty.edit(DIRECT.draft,action);directPaint();'),editing),
      ('paint during drag','direct_ui.js',('if(DIRECT.drag){DIRECT.paintDeferred=true;return;}','if(false){DIRECT.paintDeferred=true;return;}'),deferred),
      ('follow-up drag click','direct_drag.js',('suppressUntil=Date.now()+700','suppressUntil=0'),click),
      ('empty-stage growth comparison','direct_run.js',('growthCompatible=!!gr&&!!st&&','growthCompatible=!!gr&&'),empty_stage),
    ]
    for name,file,change,check in cases:
        # A healthy route is evaluated first: a test that also fails normally proves nothing.
        p=start(browser,base);check(p);p.close()
        old,new=change
        if name=='execution choice in signature':
            # A normal invalidation must reach the modified signature, too.
            source=(ROOT/file).read_text(encoding='utf-8')
            new_source=source.replace(old,new).replace('[DIRECT.draft,MI.hash','[DIRECT.draft,DIRECT.withReco,MI.hash')
            change=(source,new_source)
        p=start(browser,base,mutations={file:change})
        try:check(p)
        except AssertionError:print('CAUGHT + restored:',name,flush=True)
        else:raise AssertionError('mutation survived: '+name)
        finally:p.close()


def video(browser,base):
    context=browser.new_context(viewport={'width':1280,'height':1000},record_video_dir=str(OUT/'video'),record_video_size={'width':1280,'height':1000})
    class Pages:
        def new_page(self,**kwargs):return context.new_page()
    p=start(Pages(),base)
    p.locator('#direct-board').scroll_into_view_if_needed();p.wait_for_timeout(800)
    drag(p,'[data-direct-action=slot][data-slot="0"]','[data-direct-action=slot][data-slot="3"]')
    p.wait_for_timeout(1000);drag(p,'[data-direct-action=slot][data-slot="1"]','#direct-drop-remove')
    p.wait_for_timeout(1000);p.locator('#direct-undo').click();p.wait_for_timeout(1000)
    recorded=p.video;context.close();recorded.save_as(str(OUT/'drag-and-undo.webm'))



def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only',choices=['bundle','choices','cancel','pointer','gestures','review','safety','faces','real','mutations','video']);a=ap.parse_args()
    with test_server() as base,sync_playwright() as pw:
        browser=pw.chromium.launch()
        cases={'bundle':lambda:[bundle_contract(browser,base,w) for w in [1280,360]],'choices':lambda:combinations(browser,base),
               'cancel':lambda:cancellation(browser,base),'pointer':lambda:[pointers(browser,base,w) for w in [1280,360]],
               'gestures':lambda:gestures(browser,base),'review':lambda:review_regressions(browser,base),'safety':lambda:drag_safety(browser,base),'faces':lambda:[faces(browser,base,w) for w in [1280,360]],'real':lambda:real_checks(browser,base),
               'mutations':lambda:mutations(browser,base),'video':lambda:video(browser,base)}
        for name,fn in cases.items():
            if a.only and a.only!=name:continue
            if not a.only and name=='video':continue
            fn();print('PASS phase2',name,flush=True)
        browser.close()


if __name__=='__main__':main()
